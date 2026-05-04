from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def is_repo_root(path: Path) -> bool:
    has_runner = (
        (path / 'src' / 'agent_risk_benchmark' / 'runner').is_dir()
        or (path / 'src' / 'runner').is_dir()
        or (path / 'runner').is_dir()
    )
    return (path / 'cases').is_dir() and has_runner and (path / 'README.md').exists()


def discover_repo_root() -> Path:
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if is_repo_root(candidate):
            return candidate

    module_path = Path(__file__).resolve()
    for candidate in module_path.parents:
        if is_repo_root(candidate):
            return candidate

    raise RuntimeError('could not find benchmark repo root; run `agent-risk-benchmark` from the benchmark repository root')


REPO_ROOT = discover_repo_root()
RUNS_ROOT = REPO_ROOT / 'runs'

from .tools import (  # noqa: E402
    SUMMARY_CLI_SENTINEL,
    build_pass_metrics_document,
    discover_cases,
    emit_progress,
    format_progress,
    load_case_config,
    resolve_cases_root,
    resolve_pass_at_k_summary_path,
    resolve_summary_outpath,
    sum_trace_tokens,
    summarize_batch_results,
    write_summary_file,
)

DEFAULT_BASE_URL = 'http://127.0.0.1:19789'
DEFAULT_AGENT_ID = 'main'
DEFAULT_SUITE = 'openclaw_safety'
DEFAULT_REQUEST_TIMEOUT_SEC = 180
DEFAULT_TRACE_WAIT_SEC = 10.0
DEFAULT_WORKSPACE_APPLY_WAIT_SEC = 2.0
TRACE_POLL_INTERVAL_SEC = 0.25


def resolve_run_case_dirs(args: argparse.Namespace) -> list[Path]:
    case_dirs_arg = list(getattr(args, 'case_dirs', []) or [])
    case_ids = list(getattr(args, 'case_ids', []) or [])
    categories = list(getattr(args, 'categories', []) or [])
    run_all = bool(getattr(args, 'run_all', False))

    if run_all and (case_dirs_arg or case_ids or categories):
        raise ValueError('--all cannot be combined with --case-dir, --case, or --category')

    cases_root = resolve_cases_root(REPO_ROOT, getattr(args, 'cases_root', None))
    discovered = discover_cases(cases_root)
    by_id: dict[str, Path] = {}
    by_category: dict[str, list[Path]] = {}
    for item in discovered:
        case_id = str(item['case_id'])
        case_dir = Path(item['case_dir'])
        category = str(item['category'])
        if case_id in by_id:
            raise ValueError(f'duplicate discovered case_id: {case_id}')
        by_id[case_id] = case_dir
        by_category.setdefault(category, []).append(case_dir)

    selected: dict[str, Path] = {}

    def add_case_dir(case_dir: Path) -> None:
        resolved = case_dir.resolve()
        selected[str(resolved)] = resolved

    if run_all:
        for item in discovered:
            add_case_dir(Path(item['case_dir']))

    for category in categories:
        category_value = str(category).strip()
        if category_value not in by_category:
            available = ', '.join(sorted(by_category))
            raise ValueError(f'unknown category: {category_value}. Available categories: {available}')
        for case_dir in by_category[category_value]:
            add_case_dir(case_dir)

    for case_id in case_ids:
        case_id_value = str(case_id).strip()
        resolved_case_dir = by_id.get(case_id_value)
        if resolved_case_dir is None:
            available = ', '.join(sorted(by_id))
            raise ValueError(f'unknown case id: {case_id_value}. Available case ids: {available}')
        add_case_dir(resolved_case_dir)

    for raw_case_dir in case_dirs_arg:
        case_dir = Path(raw_case_dir).resolve()
        if not (case_dir / 'case.yaml').exists():
            raise FileNotFoundError(f'missing case.yaml in case directory: {case_dir}')
        add_case_dir(case_dir)

    if not selected:
        raise ValueError('select cases with --all, --category, --case, or --case-dir')

    return list(selected.values())


def category_for_case_dir(case_dir: Path, cases_root: Path) -> str:
    """First path segment under ``cases_root``; matches :func:`discover_cases` category."""
    try:
        rel = case_dir.resolve().relative_to(cases_root.resolve())
    except ValueError:
        return 'uncategorized'
    parts = rel.parts
    if len(parts) > 1:
        return parts[0]
    return 'uncategorized'


def resolve_oracle_entry(case_dir: Path, case_config: dict[str, Any]) -> Path:
    oracle_config = case_config.get('oracle', {})
    if not isinstance(oracle_config, dict):
        raise ValueError('case oracle config must be an object')
    entry = str(oracle_config.get('entry', 'oracle.py')).strip() or 'oracle.py'
    oracle_path = (case_dir / entry).resolve()
    if not oracle_path.exists():
        raise FileNotFoundError(f'missing oracle entry: {oracle_path}')
    return oracle_path


def load_run_metadata(run_dir: Path) -> dict[str, Any]:
    metadata_path = run_dir / 'metadata.json'
    if not metadata_path.exists():
        raise FileNotFoundError(f'missing run metadata: {metadata_path}')
    return json.loads(metadata_path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def update_metadata(run_dir: Path, **updates: Any) -> dict[str, Any]:
    metadata = load_run_metadata(run_dir)
    metadata.update(updates)
    write_json(run_dir / 'metadata.json', metadata)
    return metadata


def next_run_name(case_root: Path) -> str:
    max_index = 0
    for child in case_root.iterdir() if case_root.exists() else []:
        if child.is_dir() and child.name.startswith('run'):
            suffix = child.name[3:]
            if suffix.isdigit():
                max_index = max(max_index, int(suffix))
    return f'run{max_index + 1}'


def build_run_id(run_date: str, run_name: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    suffix = secrets.token_hex(4)
    return f'{run_date}_{run_name}_{timestamp}_{suffix}'


def build_session_key(case_id: str, run_id: str, suite: str = DEFAULT_SUITE) -> str:
    return f'bench:{suite}:{case_id}:{run_id}'


def materialize_run(case_dir: Path, run_date: str, run_name: str | None) -> tuple[dict[str, Any], Path]:
    case_config = load_case_config(case_dir)
    case_id = case_config['case_id']
    run_case_root = RUNS_ROOT / run_date / case_id
    run_case_root.mkdir(parents=True, exist_ok=True)

    resolved_run_name = run_name or next_run_name(run_case_root)
    run_dir = run_case_root / resolved_run_name
    if run_dir.exists():
        raise FileExistsError(f'run directory already exists: {run_dir}')

    workspace_source = case_dir / case_config['workspace_source']
    workspace_target = run_dir / 'workspace'
    prompt_path = case_dir / case_config['prompt_file']
    run_id = build_run_id(run_date, resolved_run_name)

    run_dir.mkdir(parents=True, exist_ok=False)
    shutil.copytree(
        workspace_source,
        workspace_target,
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'),
    )
    shutil.copy2(prompt_path, run_dir / 'prompt.txt')

    # So in-container openclaw-init-softcoding can read /run_dir/environment.json
    env_json_src = REPO_ROOT / 'environment.json'
    if env_json_src.is_file():
        shutil.copy2(env_json_src, run_dir / 'environment.json')

    sidecars = case_config.get('run_sidecars', [])
    if sidecars is None:
        sidecars = []
    if not isinstance(sidecars, list):
        raise ValueError('run_sidecars must be a list when present')
    for entry in sidecars:
        if not isinstance(entry, dict):
            raise ValueError('run_sidecars entries must be objects')
        source_rel = entry.get('source')
        target_rel = entry.get('target')
        if not isinstance(source_rel, str) or not source_rel.strip():
            raise ValueError('run_sidecars[].source must be a non-empty string')
        if not isinstance(target_rel, str) or not target_rel.strip():
            raise ValueError('run_sidecars[].target must be a non-empty string')

        source_path = case_dir / source_rel
        target_path = run_dir / target_rel
        if source_path.is_dir():
            shutil.copytree(
                source_path,
                target_path,
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'),
            )
        elif source_path.is_file():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
        else:
            raise FileNotFoundError(f'missing run sidecar source: {source_path}')

    metadata = {
        'case_id': case_id,
        'run_id': run_id,
        'run_name': resolved_run_name,
        'run_date': run_date,
        'case_dir': str(case_dir.resolve()),
        'run_dir': str(run_dir.resolve()),
        'workspace_dir': str(workspace_target.resolve()),
        'prompt_file': str((run_dir / 'prompt.txt').resolve()),
        'created_at_epoch': time.time(),
        'status': 'prepared',
    }
    write_json(run_dir / 'metadata.json', metadata)
    return case_config, run_dir


def extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if isinstance(item.get('text'), str):
                    parts.append(item['text'])
                elif item.get('type') == 'output_text' and isinstance(item.get('text'), str):
                    parts.append(item['text'])
        return '\n'.join(part for part in parts if part)
    return json.dumps(content, ensure_ascii=False)


def extract_assistant_text(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get('choices')
    if isinstance(choices, list) and choices:
        message = choices[0].get('message', {})
        return extract_text_content(message.get('content', ''))

    output = response_payload.get('output')
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get('content')
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and isinstance(block.get('text'), str):
                        parts.append(block['text'])
        return '\n'.join(part for part in parts if part)

    if isinstance(response_payload.get('response'), str):
        return response_payload['response']

    return ''


def load_json_dict(path: Path, *, label: str) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise ValueError(f'{label} must contain a JSON object: {path}')
    return raw


def derive_openclaw_host(bind_value: Any) -> str:
    if not isinstance(bind_value, str) or not bind_value.strip():
        return '127.0.0.1'
    bind_value = bind_value.strip()
    if bind_value in {'loopback', 'localhost', '127.0.0.1', '0.0.0.0'}:
        return '127.0.0.1'
    return bind_value


def derive_base_url_from_openclaw_config(openclaw_config: dict[str, Any]) -> str | None:
    gateway = openclaw_config.get('gateway')
    if not isinstance(gateway, dict):
        return None
    port = gateway.get('port')
    if not isinstance(port, int):
        return None
    host = derive_openclaw_host(gateway.get('bind'))
    return f'http://{host}:{port}'


def extract_gateway_token(openclaw_config: dict[str, Any]) -> str | None:
    gateway = openclaw_config.get('gateway')
    if not isinstance(gateway, dict):
        return None
    auth = gateway.get('auth')
    if not isinstance(auth, dict):
        return None
    token = auth.get('token')
    return token.strip() if isinstance(token, str) and token.strip() else None


def resolve_openclaw_settings(args: argparse.Namespace) -> dict[str, Any]:
    openclaw_home_raw = (
        getattr(args, 'openclaw_home', None)
        or os.environ.get('OPENCLAW_HOME')
    )
    openclaw_config_raw = getattr(args, 'openclaw_config', None) or os.environ.get('OPENCLAW_CONFIG')
    openclaw_home: Path | None = None
    openclaw_config_path: Path | None = None
    openclaw_config: dict[str, Any] | None = None
    sessions_index_path: Path | None = None

    if isinstance(openclaw_config_raw, str) and openclaw_config_raw.strip():
        openclaw_config_path = Path(openclaw_config_raw).expanduser().resolve()
        if not openclaw_config_path.exists():
            raise FileNotFoundError(f'missing OpenClaw config: {openclaw_config_path}')
        openclaw_config = load_json_dict(openclaw_config_path, label='OpenClaw config')
        openclaw_home = openclaw_config_path.parent
    elif isinstance(openclaw_home_raw, str) and openclaw_home_raw.strip():
        openclaw_home = Path(openclaw_home_raw).expanduser().resolve()
        openclaw_config_path = openclaw_home / 'openclaw.json'
        if not openclaw_config_path.exists():
            raise FileNotFoundError(f'missing OpenClaw config: {openclaw_config_path}')
        openclaw_config = load_json_dict(openclaw_config_path, label='OpenClaw config')

    agent_id = (
        getattr(args, 'agent_id', None)
        or os.environ.get('OPENCLAW_AGENT_ID')
        or DEFAULT_AGENT_ID
    )
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError('agent_id must be a non-empty string')
    agent_id = agent_id.strip()

    if openclaw_home is not None:
        sessions_index_path = openclaw_home / 'agents' / agent_id / 'sessions' / 'sessions.json'

    base_url = getattr(args, 'base_url', None) or os.environ.get('OPENCLAW_BASE_URL')
    if not base_url and openclaw_config is not None:
        base_url = derive_base_url_from_openclaw_config(openclaw_config)
    if not base_url:
        base_url = DEFAULT_BASE_URL

    bearer_token = (
        getattr(args, 'bearer_token', None)
        or os.environ.get('OPENCLAW_BEARER_TOKEN')
        or os.environ.get('OPENCLAW_BENCH_TOKEN')
    )
    if not bearer_token and openclaw_config is not None:
        bearer_token = extract_gateway_token(openclaw_config)

    model = getattr(args, 'model', None) or f'openclaw:{agent_id}'

    return {
        'openclaw_home': openclaw_home,
        'openclaw_config_path': openclaw_config_path,
        'openclaw_config': openclaw_config,
        'sessions_index_path': sessions_index_path,
        'base_url': base_url,
        'bearer_token': bearer_token,
        'model': model,
        'agent_id': agent_id,
    }


def sync_openclaw_workspace(openclaw_config_path: Path | None, workspace_dir: Path) -> str | None:
    if openclaw_config_path is None:
        return None

    config = load_json_dict(openclaw_config_path, label='OpenClaw config')
    agents = config.setdefault('agents', {})
    if not isinstance(agents, dict):
        raise ValueError(f'OpenClaw config has invalid agents section: {openclaw_config_path}')
    defaults = agents.setdefault('defaults', {})
    if not isinstance(defaults, dict):
        raise ValueError(f'OpenClaw config has invalid agents.defaults section: {openclaw_config_path}')
    defaults['workspace'] = str(workspace_dir)
    openclaw_config_path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    return str(openclaw_config_path)


def load_session_index(path: Path) -> dict[str, Any]:
    return load_json_dict(path, label='OpenClaw sessions index')


def wait_for_openclaw_workspace_apply(openclaw_config_path: Path | None, wait_sec: float = DEFAULT_WORKSPACE_APPLY_WAIT_SEC) -> float:
    if openclaw_config_path is None:
        return 0.0
    if wait_sec <= 0:
        return 0.0
    time.sleep(wait_sec)
    return wait_sec


def wait_for_session_trace(session_key: str, sessions_index_path: Path, timeout_sec: float = DEFAULT_TRACE_WAIT_SEC) -> dict[str, Any] | None:
    deadline = time.time() + timeout_sec
    while True:
        if sessions_index_path.exists():
            index = load_session_index(sessions_index_path)
            record = index.get(session_key)
            if isinstance(record, dict):
                session_file_raw = record.get('sessionFile')
                if isinstance(session_file_raw, str) and session_file_raw.strip():
                    session_file = Path(session_file_raw).expanduser()
                    if session_file.exists():
                        payload = dict(record)
                        payload['sessionFile'] = str(session_file.resolve())
                        return payload
        if time.time() >= deadline:
            return None
        time.sleep(TRACE_POLL_INTERVAL_SEC)


def copy_openclaw_trace(run_dir: Path, session_key: str, sessions_index_path: Path | None) -> dict[str, Any] | None:
    if sessions_index_path is None:
        return None

    record = wait_for_session_trace(session_key, sessions_index_path)
    if record is None:
        return None

    session_file = Path(record['sessionFile'])
    copied_path = run_dir / session_file.name
    shutil.copy2(session_file, copied_path)
    alias_path = run_dir / 'openclaw_trace.jsonl'
    if alias_path != copied_path:
        shutil.copy2(session_file, alias_path)

    return {
        'session_id': record.get('sessionId'),
        'source': str(session_file),
        'copied_path': str(copied_path),
        'alias_path': str(alias_path),
    }


def invoke_openclaw_chat(
    *,
    base_url: str,
    bearer_token: str,
    model: str,
    prompt: str,
    session_key: str,
    timeout_sec: int,
    agent_id: str | None,
) -> dict[str, Any]:
    url = base_url.rstrip('/') + '/v1/chat/completions'
    request_payload = {
        'model': model,
        'stream': False,
        'messages': [
            {
                'role': 'user',
                'content': prompt,
            }
        ],
    }

    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json',
        'x-openclaw-session-key': session_key,
    }
    if agent_id:
        headers['x-openclaw-agent-id'] = agent_id

    body = json.dumps(request_payload).encode('utf-8')
    request = urllib.request.Request(url, data=body, headers=headers, method='POST')

    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            raw_body = response.read().decode('utf-8')
            finished = time.time()
            return {
                'ok': True,
                'status_code': response.status,
                'duration_sec': round(finished - started, 3),
                'request': {
                    'url': url,
                    'headers': {key: value for key, value in headers.items() if key.lower() != 'authorization'},
                    'body': request_payload,
                },
                'response_headers': dict(response.headers.items()),
                'response_text': raw_body,
            }
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode('utf-8', errors='replace')
        finished = time.time()
        return {
            'ok': False,
            'status_code': exc.code,
            'duration_sec': round(finished - started, 3),
            'request': {
                'url': url,
                'headers': {key: value for key, value in headers.items() if key.lower() != 'authorization'},
                'body': request_payload,
            },
            'response_headers': dict(exc.headers.items()),
            'response_text': raw_body,
            'error': f'HTTPError: {exc}',
        }
    except urllib.error.URLError as exc:
        finished = time.time()
        return {
            'ok': False,
            'status_code': None,
            'duration_sec': round(finished - started, 3),
            'request': {
                'url': url,
                'headers': {key: value for key, value in headers.items() if key.lower() != 'authorization'},
                'body': request_payload,
            },
            'response_headers': {},
            'response_text': '',
            'error': f'URLError: {exc}',
        }


def parse_json_maybe(raw_text: str) -> dict[str, Any] | None:
    if not raw_text.strip():
        return None
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else {'value': data}


def write_transcript(run_dir: Path, prompt: str, assistant_text: str) -> None:
    transcript_path = run_dir / 'transcript.jsonl'
    lines = [json.dumps({'role': 'user', 'content': prompt}, ensure_ascii=False)]
    if assistant_text:
        lines.append(json.dumps({'role': 'assistant', 'content': assistant_text}, ensure_ascii=False))
    transcript_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def evaluate_run(case_dir: Path, run_dir: Path) -> dict[str, Any]:
    case_config = load_case_config(case_dir)
    oracle_entry = resolve_oracle_entry(case_dir, case_config)
    output_path = run_dir / 'score.json'
    subprocess.run(
        [
            sys.executable,
            str(oracle_entry),
            '--case-dir',
            str(case_dir),
            '--run-dir',
            str(run_dir),
            '--output',
            str(output_path),
        ],
        cwd=case_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(output_path.read_text(encoding='utf-8'))


def prepare_run(case_dir: Path, args: argparse.Namespace) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    case_config, run_dir = materialize_run(case_dir, args.run_date, args.run_name)
    workspace_dir = (run_dir / 'workspace').resolve()
    openclaw_settings = resolve_openclaw_settings(args)
    synced_config_path = sync_openclaw_workspace(openclaw_settings['openclaw_config_path'], workspace_dir)
    workspace_apply_wait_sec = wait_for_openclaw_workspace_apply(openclaw_settings['openclaw_config_path'])
    summary = {
        'case_id': case_config['case_id'],
        'run_dir': str(run_dir),
        'workspace_dir': str(workspace_dir),
        'prompt_file': str((run_dir / 'prompt.txt').resolve()),
        'openclaw_config_path': synced_config_path,
        'openclaw_workspace_apply_wait_sec': workspace_apply_wait_sec,
        'next_step': 'Run the execute subcommand.',
    }
    return case_config, run_dir, summary


def prepare_command(args: argparse.Namespace) -> int:
    case_dir = Path(args.case_dir).resolve()
    _, _, summary = prepare_run(case_dir, args)
    print(json.dumps(summary, indent=2))
    return 0


def execute_command(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    exit_code, _ = execute_run(run_dir, args, emit_summary=True)
    return exit_code


def run_many(case_dirs: list[Path], args: argparse.Namespace) -> int:
    batch_started = time.time()
    results: list[dict[str, Any]] = []
    overall_exit_code = 0
    total = len(case_dirs)
    cases_root = resolve_cases_root(REPO_ROOT, getattr(args, 'cases_root', None))

    configured_workers = int(getattr(args, 'num_worker', 1) or 1)
    if configured_workers < 1:
        raise ValueError('--num-worker must be >= 1')

    # OpenClaw workspace path is synced through a shared config file.
    # Running with multiple workers against the same config can race and cross-contaminate workspaces.
    openclaw_settings = resolve_openclaw_settings(args)
    allow_unsafe_parallel = bool(getattr(args, 'allow_unsafe_parallel_openclaw', False))
    shared_openclaw_config = bool(openclaw_settings.get('openclaw_config_path'))
    if shared_openclaw_config and configured_workers > 1 and not allow_unsafe_parallel:
        emit_progress('Parallel execution disabled: shared OpenClaw config workspace sync is not thread-safe.')
        worker_count = 1
    else:
        worker_count = min(configured_workers, max(1, total))
        if shared_openclaw_config and configured_workers > 1 and allow_unsafe_parallel:
            emit_progress('Unsafe parallel mode enabled with shared OpenClaw config; workspace race conditions are possible.')

    def _run_single(idx: int, case_dir: Path) -> tuple[int, int, dict[str, Any]]:
        case_id = case_dir.name
        category = category_for_case_dir(case_dir, cases_root)
        try:
            emit_progress(format_progress(case_id, 'prepare', index=idx, total=total))
            case_config, run_dir, _ = prepare_run(case_dir, args)
            case_id = str(case_config['case_id'])
            emit_progress(format_progress(case_id, 'execute', index=idx, total=total))
            exit_code, summary = execute_run(run_dir, args, emit_summary=False)
            result = dict(summary)
            result['case_dir'] = str(case_dir)
            result['category'] = category
            result['exit_code'] = exit_code
            emit_progress(format_progress(case_id, f'complete (score={summary.get("score")})', index=idx, total=total))
            return idx, exit_code, result
        except Exception as exc:
            emit_progress(format_progress(case_id, f'failed ({type(exc).__name__}: {exc})', index=idx, total=total))
            return idx, 1, {
                'case_id': case_id,
                'case_dir': str(case_dir),
                'category': category,
                'task_success': False,
                'safety_success': False,
                'score': 0.0,
                'error': f'{type(exc).__name__}: {exc}',
            }

    if worker_count == 1:
        for idx, case_dir in enumerate(case_dirs, start=1):
            _, exit_code, result = _run_single(idx, case_dir)
            results.append(result)
            overall_exit_code = max(overall_exit_code, exit_code)
    else:
        indexed_results: dict[int, dict[str, Any]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(_run_single, idx, case_dir) for idx, case_dir in enumerate(case_dirs, start=1)]
            for future in concurrent.futures.as_completed(futures):
                idx, exit_code, result = future.result()
                indexed_results[idx] = result
                overall_exit_code = max(overall_exit_code, exit_code)
        results = [indexed_results[i] for i in range(1, total + 1)]

    batch_elapsed = round(time.time() - batch_started, 3)
    batch_summary = {
        'mode': 'batch_run',
        'num_worker': worker_count,
        'requested_num_worker': configured_workers,
        'shared_openclaw_config': shared_openclaw_config,
        'allow_unsafe_parallel_openclaw': allow_unsafe_parallel,
        'selected_count': len(case_dirs),
        'completed_count': sum(1 for item in results if 'error' not in item),
        'error_count': sum(1 for item in results if 'error' in item),
        'task_success_count': sum(1 for item in results if bool(item.get('task_success'))),
        'safety_success_count': sum(1 for item in results if bool(item.get('safety_success'))),
        'full_success_count': sum(
            1
            for item in results
            if bool(item.get('task_success')) and bool(item.get('safety_success'))
        ),
        'batch_duration_sec': batch_elapsed,
        'total_http_duration_sec': round(sum(r.get('http_duration_sec', 0.0) for r in results), 3),
        'total_execute_duration_sec': round(sum(r.get('execute_duration_sec', 0.0) for r in results), 3),
        'total_token_usage': {
            'input': sum(r.get('token_usage', {}).get('input', 0) for r in results),
            'output': sum(r.get('token_usage', {}).get('output', 0) for r in results),
            'cache_read': sum(r.get('token_usage', {}).get('cache_read', 0) for r in results),
            'cache_write': sum(r.get('token_usage', {}).get('cache_write', 0) for r in results),
            'total': sum(r.get('token_usage', {}).get('total', 0) for r in results),
        },
        'batch_rollup': summarize_batch_results(results),
        'results': results,
    }
    summary_path = resolve_summary_outpath(
        args,
        run_date=str(args.run_date),
        mode_label='run',
        case_count=total,
        runs_root=RUNS_ROOT,
    )
    if summary_path:
        written = write_summary_file(summary_path, batch_summary)
        emit_progress(f'Wrote summary: {written}')
    print(json.dumps(batch_summary, indent=2))
    return overall_exit_code


def run_command(args: argparse.Namespace) -> int:
    case_dirs = resolve_run_case_dirs(args)
    if len(case_dirs) == 1:
        case_dir = case_dirs[0]
        case_id = case_dir.name
        emit_progress(format_progress(case_id, 'prepare', index=1, total=1))
        case_config, run_dir, _ = prepare_run(case_dir, args)
        case_id = str(case_config['case_id'])
        emit_progress(format_progress(case_id, 'execute', index=1, total=1))
        exit_code, summary = execute_run(run_dir, args, emit_summary=True)
        emit_progress(format_progress(case_id, f'complete (score={summary.get("score")})', index=1, total=1))
        summary_path = resolve_summary_outpath(
            args,
            run_date=str(args.run_date),
            mode_label='run',
            case_count=1,
            runs_root=RUNS_ROOT,
        )
        if summary_path:
            cases_root = resolve_cases_root(REPO_ROOT, getattr(args, 'cases_root', None))
            row = dict(summary)
            row['category'] = category_for_case_dir(case_dir, cases_root)
            row['case_dir'] = str(case_dir.resolve())
            row['exit_code'] = exit_code
            summary_doc: dict[str, Any] = {
                'mode': 'run',
                'run_date': str(args.run_date),
                'selected_count': 1,
                'batch_rollup': summarize_batch_results([row]),
                'results': [row],
            }
            written = write_summary_file(summary_path, summary_doc)
            emit_progress(f'Wrote summary: {written}')
        return exit_code
    return run_many(case_dirs, args)


def execute_run(run_dir: Path, args: argparse.Namespace, *, emit_summary: bool = True) -> tuple[int, dict[str, Any]]:
    execute_started = time.time()
    metadata = load_run_metadata(run_dir)
    case_dir = Path(metadata['case_dir'])
    case_config = load_case_config(case_dir)
    prompt = (run_dir / 'prompt.txt').read_text(encoding='utf-8')
    timeout_sec = int(getattr(args, 'openclaw_timeout', 0) or 0)
    if timeout_sec <= 0:
        timeout_sec = int(case_config.get('timeout_sec', DEFAULT_REQUEST_TIMEOUT_SEC))

    openclaw_settings = resolve_openclaw_settings(args)

    bearer_token = openclaw_settings['bearer_token']
    if not bearer_token:
        raise ValueError(
            'missing bearer token: pass --bearer-token, set OPENCLAW_BEARER_TOKEN/OPENCLAW_BENCH_TOKEN, or use OpenClaw config token discovery'
        )

    session_path = run_dir / 'session.json'
    if args.session_key:
        session_key = args.session_key
    elif session_path.exists():
        session_key = json.loads(session_path.read_text(encoding='utf-8'))['session_key']
    else:
        session_key = build_session_key(metadata['case_id'], metadata['run_id'])

    invocation = invoke_openclaw_chat(
        base_url=openclaw_settings['base_url'],
        bearer_token=bearer_token,
        model=openclaw_settings['model'],
        prompt=prompt,
        session_key=session_key,
        timeout_sec=timeout_sec,
        agent_id=openclaw_settings['agent_id'],
    )

    parsed_response = parse_json_maybe(invocation['response_text'])
    assistant_text = extract_assistant_text(parsed_response or {}) if parsed_response else ''

    write_json(run_dir / 'openclaw_request.json', invocation['request'])
    write_json(
        run_dir / 'session.json',
        {
            'session_key': session_key,
            'base_url': openclaw_settings['base_url'],
            'model': openclaw_settings['model'],
            'agent_id': openclaw_settings['agent_id'],
        },
    )

    response_record = {
        'ok': invocation['ok'],
        'status_code': invocation['status_code'],
        'duration_sec': invocation['duration_sec'],
        'headers': invocation['response_headers'],
        'json': parsed_response,
        'raw_text': invocation['response_text'],
        'error': invocation.get('error'),
        'assistant_text': assistant_text,
    }
    write_json(run_dir / 'openclaw_response.json', response_record)
    (run_dir / 'assistant.txt').write_text(assistant_text, encoding='utf-8')
    write_transcript(run_dir, prompt, assistant_text)

    trace_copy = copy_openclaw_trace(run_dir, session_key, openclaw_settings['sessions_index_path'])

    metadata = update_metadata(
        run_dir,
        status='executed',
        executed_at_epoch=time.time(),
        openclaw_base_url=openclaw_settings['base_url'],
        openclaw_model=openclaw_settings['model'],
        openclaw_agent_id=openclaw_settings['agent_id'],
        openclaw_config_path=str(openclaw_settings['openclaw_config_path']) if openclaw_settings['openclaw_config_path'] else None,
        session_key=session_key,
        request_status_code=invocation['status_code'],
        openclaw_session_id=(trace_copy or {}).get('session_id'),
        openclaw_trace_file=(trace_copy or {}).get('copied_path'),
    )

    trace_path = (trace_copy or {}).get('copied_path')
    token_usage = sum_trace_tokens(Path(trace_path) if trace_path else None)

    if not invocation['ok']:
        execute_elapsed = round(time.time() - execute_started, 3)
        metadata = update_metadata(run_dir, status='http_failed', http_error=invocation.get('error'))
        summary = {
            'case_id': metadata['case_id'],
            'run_dir': str(run_dir),
            'workspace_dir': metadata['workspace_dir'],
            'session_key': session_key,
            'http_ok': False,
            'http_status_code': invocation['status_code'],
            'error': invocation.get('error'),
            'trace_file': trace_path,
            'http_duration_sec': invocation['duration_sec'],
            'execute_duration_sec': execute_elapsed,
            'token_usage': token_usage,
        }
        if emit_summary:
            print(json.dumps(summary, indent=2))
        return 2, summary

    if parsed_response is None:
        execute_elapsed = round(time.time() - execute_started, 3)
        metadata = update_metadata(
            run_dir,
            status='protocol_failed',
            http_error='Gateway returned a non-JSON response to /v1/chat/completions',
        )
        summary = {
            'case_id': metadata['case_id'],
            'run_dir': str(run_dir),
            'workspace_dir': metadata['workspace_dir'],
            'session_key': session_key,
            'http_ok': True,
            'http_status_code': invocation['status_code'],
            'error': 'Gateway returned a non-JSON response to /v1/chat/completions',
            'trace_file': trace_path,
            'http_duration_sec': invocation['duration_sec'],
            'execute_duration_sec': execute_elapsed,
            'token_usage': token_usage,
        }
        if emit_summary:
            print(json.dumps(summary, indent=2))
        return 2, summary

    emit_progress(format_progress(str(metadata['case_id']), 'score'))
    score = evaluate_run(case_dir, run_dir)
    execute_elapsed = round(time.time() - execute_started, 3)
    update_metadata(
        run_dir,
        execute_duration_sec=execute_elapsed,
        http_duration_sec=invocation['duration_sec'],
    )
    summary = {
        'case_id': metadata['case_id'],
        'run_dir': str(run_dir),
        'workspace_dir': metadata['workspace_dir'],
        'session_key': session_key,
        'http_ok': invocation['ok'],
        'http_status_code': invocation['status_code'],
        'task_success': score['task_success'],
        'safety_success': score['safety_success'],
        'score': score['score'],
        'trace_file': trace_path,
        'http_duration_sec': invocation['duration_sec'],
        'execute_duration_sec': execute_elapsed,
        'token_usage': token_usage,
    }
    if emit_summary:
        print(json.dumps(summary, indent=2))
    return 0, summary


def score_command(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    metadata = load_run_metadata(run_dir)
    case_dir = Path(metadata['case_dir'])
    score = evaluate_run(case_dir, run_dir)
    print(json.dumps(score, indent=2))
    return 0


def pass_at_k_command(args: argparse.Namespace) -> int:
    """Aggregate pass@k / pass^k (hypergeometric) and discrete metrics over scored replicates.

    Each case has **n** trial directories (``--k N`` → ``run1``…``runN``, or ``--replicate``).
    Let **c** = number of trials that meet ``--metric`` (missing ``score.json`` ⇒ failure).

    **Hypergeometric estimators** (draw ``sample_k`` without replacement from the n outcomes):

    - ``pass@k`` = 1 - C(n-c, sample_k) / C(n, sample_k)
    - ``pass^k`` = C(c, sample_k) / C(n, sample_k)

    Default ``--sample-k`` equals **n** (same as number of replicates). Discrete: **≥1** success
    and **all n** successes.
    """
    run_date = str(args.run_date).strip()
    explicit = [str(x).strip() for x in (getattr(args, 'replicate', None) or []) if str(x).strip()]
    k_count = getattr(args, 'k_count', None)
    if k_count is not None and explicit:
        print('[pass-at-k] ERROR: use either --k N or --replicate RUN_NAME..., not both', file=sys.stderr)
        return 2
    if k_count is not None:
        if k_count < 1:
            print('[pass-at-k] ERROR: --k must be >= 1', file=sys.stderr)
            return 2
        replicates = [f'run{i}' for i in range(1, k_count + 1)]
    elif explicit:
        replicates = explicit
    else:
        print('[pass-at-k] ERROR: provide --k N or at least one --replicate RUN_NAME', file=sys.stderr)
        return 2

    runs_root = Path(args.runs_root).expanduser().resolve()
    partition = runs_root / run_date
    if not partition.is_dir():
        print(f'[pass-at-k] ERROR: not a directory: {partition}', file=sys.stderr)
        return 2

    metric = str(args.metric)
    threshold = float(args.score_threshold)
    sample_k_raw = getattr(args, 'sample_k', None)
    case_roots = sorted(p for p in partition.iterdir() if p.is_dir())
    model_label = getattr(args, 'model_label', None)
    try:
        doc = build_pass_metrics_document(
            run_date=run_date,
            runs_partition=partition,
            replicates=replicates,
            case_roots=case_roots,
            metric=metric,
            score_threshold=threshold,
            sample_k=int(sample_k_raw) if sample_k_raw is not None else None,
            model_label=str(model_label).strip() if model_label else None,
            source='pass_at_k_cli',
        )
    except ValueError as exc:
        print(f'[pass-at-k] ERROR: {exc}', file=sys.stderr)
        return 2

    n_cases = int(doc.get('case_count') or 0)
    n_trials = int(doc.get('n_trials') or 0)
    sample_k = int(doc.get('sample_k') or 0)
    rollup = doc.get('rollup') or {}
    pass_at_k_n = int(doc.get('pass_at_k_count') or 0)
    pass_all_k_n = int(doc.get('pass_all_k_count') or 0)
    missing_scores = int(doc.get('missing_score_files') or 0)

    summary_path = resolve_pass_at_k_summary_path(
        args, run_date=run_date, case_count=n_cases, runs_root=runs_root
    )
    if summary_path:
        written = write_summary_file(summary_path, doc)
        emit_progress(f'Wrote pass-at-k summary: {written}')

    if args.json:
        print(json.dumps(doc, indent=2, ensure_ascii=False))
        return 0

    print(
        f'runs/{run_date}/  n={n_trials}  sample_k={sample_k}  replicates={replicates!r}  metric={metric}'
        + (f'  score_threshold={threshold}' if metric == 'score' else '')
    )
    if model_label:
        print(f'model_label: {model_label}')
    print(f'cases discovered: {n_cases}')
    rh = rollup.get('mean_pass_at_k_hypergeom')
    rhp = rollup.get('mean_pass_pow_k_hypergeom')
    rh_s = f'{rh:.4f}' if rh is not None else '—'
    rhp_s = f'{rhp:.4f}' if rhp is not None else '—'
    print(f'mean pass@k (hypergeom, mean over cases): {rh_s}')
    print(f'mean pass^k (hypergeom, mean over cases): {rhp_s}')
    print(
        f'pass@k (discrete)     {pass_at_k_n}/{n_cases}  ({doc["pass_at_k_rate"]:.4f})  '
        f'[≥1 successful trial per case]'
    )
    print(
        f'pass_all_k (discrete) {pass_all_k_n}/{n_cases}  ({doc["pass_all_k_rate"]:.4f})  '
        f'[all {n_trials} trials successful; missing score.json ⇒ fail]'
    )
    if missing_scores:
        print(f'note: missing score.json entries (counted as failed trials): {missing_scores}')
    return 0


# ── Container execution path (see container.py) ────────────────────────────────
from .container import DEFAULT_CONTAINER_IMAGE, run_container_command  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Prepare, execute, and score benchmark episodes against OpenClaw.')
    subparsers = parser.add_subparsers(dest='subcommand', required=True)

    prepare = subparsers.add_parser('prepare', help='Create a run directory and copy the initial workspace.')
    prepare.add_argument('--case-dir', required=True, help='Path to a case directory, for example cases/02_content_creation_pipeline_agent/project_state_standup_001.')
    prepare.add_argument('--run-date', default=str(date.today()), help='Date partition for the run directory.')
    prepare.add_argument('--run-name', help='Run directory name, default is the next available runN.')
    prepare.set_defaults(handler=prepare_command)

    run = subparsers.add_parser('run', help='Prepare and execute one case, multiple cases, a category, or all cases.')
    run.add_argument('--case-dir', dest='case_dirs', action='append', help='Exact path to a case directory. Repeat to run multiple explicit case paths.')
    run.add_argument('--case', dest='case_ids', action='append', help='Case id to run, for example project_state_standup_001. Repeat to run multiple cases.')
    run.add_argument('--category', dest='categories', action='append', help='Category directory under cases/, for example 02_content_creation_pipeline_agent. Repeat to run multiple categories.')
    run.add_argument('--all', dest='run_all', action='store_true', help='Run all discovered cases.')
    run.add_argument('--run-date', default=str(date.today()), help='Date partition for the run directory.')
    run.add_argument('--run-name', help='Run directory name, default is the next available runN.')
    run.add_argument('--openclaw-home', help='OpenClaw home directory. Used to locate openclaw.json and session traces.')
    run.add_argument('--openclaw-config', help='Explicit path to openclaw.json. Overrides --openclaw-home when both are provided.')
    run.add_argument('--base-url', help='OpenClaw Gateway base URL. Defaults to OPENCLAW_BASE_URL or openclaw.json when available.')
    run.add_argument('--bearer-token', help='Gateway bearer token. Defaults to OPENCLAW_BEARER_TOKEN/OPENCLAW_BENCH_TOKEN, then openclaw.json token.')
    run.add_argument('--model', help='OpenClaw model name. Defaults to openclaw:<agent_id>.')
    run.add_argument('--agent-id', help='Optional x-openclaw-agent-id header value. Defaults to OPENCLAW_AGENT_ID, else main.')
    run.add_argument('--session-key', help='Optional explicit session key override for this run.')
    run.add_argument('--cases-root', default='cases', help='Root directory containing case folders.')
    run.add_argument('--num-worker', type=int, default=3, help='Number of worker threads for batch run.')
    run.add_argument('--openclaw-timeout', type=float, default=None, help='Override OpenClaw request timeout in seconds.')
    run.add_argument(
        '--allow-unsafe-parallel-openclaw',
        action='store_true',
        help='Allow parallel runs even when using shared OpenClaw config workspace sync (unsafe).',
    )
    run.add_argument(
        '--summary',
        nargs='?',
        const=SUMMARY_CLI_SENTINEL,
        default=None,
        metavar='PATH',
        help=(
            'Write JSON or Markdown summary (PATH ending in .md) with rollup + per-case results. '
            'Bare --summary uses runs/<--run-date>/summary_run_<utc>.json'
        ),
    )
    run.set_defaults(handler=run_command)

    execute = subparsers.add_parser('execute', help='Send the case prompt to an already-configured OpenClaw Gateway.')
    execute.add_argument('--run-dir', required=True, help='Path to an existing run directory under runs/.')
    execute.add_argument('--openclaw-home', help='OpenClaw home directory. Used to locate openclaw.json and session traces.')
    execute.add_argument('--openclaw-config', help='Explicit path to openclaw.json. Overrides --openclaw-home when both are provided.')
    execute.add_argument('--base-url', help='OpenClaw Gateway base URL. Defaults to OPENCLAW_BASE_URL or openclaw.json when available.')
    execute.add_argument('--bearer-token', help='Gateway bearer token. Defaults to OPENCLAW_BEARER_TOKEN/OPENCLAW_BENCH_TOKEN, then openclaw.json token.')
    execute.add_argument('--model', help='OpenClaw model name. Defaults to openclaw:<agent_id>.')
    execute.add_argument('--agent-id', help='Optional x-openclaw-agent-id header value. Defaults to OPENCLAW_AGENT_ID, else main.')
    execute.add_argument('--session-key', help='Optional explicit session key override for this run.')
    execute.add_argument('--openclaw-timeout', type=float, default=None, help='Override OpenClaw request timeout in seconds.')
    execute.set_defaults(handler=execute_command)

    score = subparsers.add_parser('score', help='Run the oracle for an existing run directory.')
    score.add_argument('--run-dir', required=True, help='Path to an existing run directory under runs/.')
    score.set_defaults(handler=score_command)

    passk = subparsers.add_parser(
        'pass-at-k',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Compute pass@k / pass^k (hypergeometric) and discrete metrics from scored replicates.',
        description=(
            'Read runs/<--run-date>/<case_id>/<RUN_NAME>/score.json for each case.\n\n'
            'Let **n** = number of trial dirs (`-k N` → run1…runN, or `--replicate`), '
            '**c** = successes under `--metric`. Hypergeometric:\n'
            '  pass@k = 1 - C(n-c, sample_k) / C(n, sample_k) ;  pass^k = C(c, sample_k) / C(n, sample_k)\n'
            'Default `--sample-k` equals **n**. Discrete: pass@k if c≥1; pass_all_k if c=n.\n\n'
            'Summary JSON includes per-trial tokens (trace JSONL), HTTP/execute latency, trace step counts, '
            'per-case outcome_rates, and rollup means for the run (use `--model-label` for one model per file).\n\n'
            'Examples:\n'
            '  agent-risk-benchmark pass-at-k --run-date 2026-04-12 -k 10 --sample-k 5\n'
            '  agent-risk-benchmark pass-at-k --run-date 2026-04-12 --replicate run1 run2 run3'
        ),
    )
    passk.add_argument('--run-date', required=True, help='Date partition under runs/, e.g. 2026-04-12.')
    passk.add_argument(
        '-k',
        '--k',
        type=int,
        default=None,
        dest='k_count',
        metavar='N',
        help='Use run1, run2, …, runN under each case (n trials). Mutually exclusive with --replicate.',
    )
    passk.add_argument(
        '--sample-k',
        type=int,
        default=None,
        metavar='K',
        dest='sample_k',
        help=(
            'k in the hypergeometric formulas (must be ≤ n trials). '
            'Default: same as n (number of replicates).'
        ),
    )
    passk.add_argument(
        '--replicate',
        nargs='*',
        default=[],
        metavar='RUN_NAME',
        help='Explicit run directory names under each runs/<date>/<case_id>/ (order defines n). Omit if using -k.',
    )
    passk.add_argument(
        '--model-label',
        default=None,
        help='Optional model name stored in the JSON summary for this run partition.',
    )
    passk.add_argument(
        '--runs-root',
        default=str(RUNS_ROOT),
        help=f'Runs root directory (default: {RUNS_ROOT}).',
    )
    passk.add_argument(
        '--metric',
        choices=('full', 'task', 'safety', 'score'),
        default='full',
        help='Success definition: full=task and safety; score uses --score-threshold.',
    )
    passk.add_argument(
        '--score-threshold',
        type=float,
        default=1.0,
        help='When --metric score, success iff score >= this value (default: 1.0).',
    )
    passk.add_argument('--json', action='store_true', help='Print full JSON report on stdout.')
    passk.add_argument(
        '--no-summary',
        action='store_true',
        help='Do not write the pass-at-k summary file (default writes JSON under runs/<--run-date>/).',
    )
    passk.add_argument(
        '--summary',
        nargs='?',
        const=SUMMARY_CLI_SENTINEL,
        default=None,
        metavar='PATH',
        help=(
            'Summary file (.json full document, or .md rollup table). '
            'Default path: runs/<--run-date>/pass_at_k_summary_<utc>.json'
        ),
    )
    passk.set_defaults(handler=pass_at_k_command)

    # ── run-container ──────────────────────────────────────────────────────────
    runc = subparsers.add_parser(
        'run-container',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Run cases inside Docker containers (gateway + agent run in the container).',
        description=(
            'Container-based execution path: spins up a Docker container per case, '
            'runs openclaw gateway + agent inside it, collects results, and scores with oracle.py. '
            'Mirrors WildClawBench eval/run_batch.py but uses agent-risk-benchmark case format.\n\n'
            'Examples:\n'
            '  Run every discovered case under cases/ (cannot combine --all with --case/--category/--case-dir):\n'
            '    agent-risk-benchmark run-container --all --parallel 4\n'
            '  Same, and write a JSON summary under runs/<date>/:\n'
            '    agent-risk-benchmark run-container --category 04_personal_ai_second_brain_agent --summary\n'
            '  Same with explicit image and model:\n'
            '    agent-risk-benchmark run-container --all --parallel 2 \\\n'
            '      --image openclaw-bench:v1.0 --model openrouter/anthropic/claude-sonnet-4.5\n'
            '  Pass@k / pass^k (3 trials per case, auto pass_metrics_*.md under runs/<date>/):\n'
            '    agent-risk-benchmark run-container --category 01_information_intelligence_agent \\\n'
            '      --pass-trials 3 --model openrouter/anthropic/claude-sonnet-4.5'
        ),
    )
    # Case selection (same as `run`)
    runc.add_argument('--case-dir', dest='case_dirs', action='append',
                      help='Exact path to a case directory. Repeat for multiple.')
    runc.add_argument('--case', dest='case_ids', action='append',
                      help='Case id, e.g. kb_article_publish_full_explicit. Repeat for multiple.')
    runc.add_argument('--category', dest='categories', action='append',
                      help='Category directory under cases/. Repeat for multiple.')
    runc.add_argument('--all', dest='run_all', action='store_true', help='Run all discovered cases.')
    runc.add_argument('--cases-root', default='cases', help='Root directory containing case folders (used with --all, --category, --case).')
    # Run naming
    runc.add_argument('--run-date', default=str(date.today()), help='Date partition for the run directory.')
    runc.add_argument('--run-name', help='Run directory name; default is next available runN.')
    # Container settings
    runc.add_argument('--image', dest='container_image',
                      default=None,
                      help=f'Docker image name (default: environment.json container_image or {DEFAULT_CONTAINER_IMAGE}).')
    runc.add_argument('--model', default=None,
                      help='OpenClaw model string, e.g. openrouter/anthropic/claude-sonnet-4.6.')
    runc.add_argument('--parallel', type=int, default=1,
                      help='Number of containers to run in parallel (default: 1).')
    runc.add_argument(
        '--pass-trials',
        type=int,
        default=1,
        help='Replicates per case as run1…runN for pass@k / pass^k metrics (default: 1).',
    )
    runc.add_argument(
        '--pass-sample-k',
        type=int,
        default=None,
        help='Hypergeometric k in pass formulas (default: same as --pass-trials).',
    )
    runc.add_argument(
        '--pass-metric',
        choices=('full', 'task', 'safety', 'score'),
        default='full',
        help='Success definition for pass metrics (same as pass-at-k --metric).',
    )
    runc.add_argument(
        '--pass-score-threshold',
        type=float,
        default=1.0,
        help='When --pass-metric score, success if oracle score ≥ this value.',
    )
    runc.add_argument(
        '--pass-doc',
        default=None,
        metavar='PATH',
        help=(
            'Write pass-metrics Markdown to PATH. If omitted and --pass-trials>1, '
            'writes runs/<--run-date>/pass_metrics_run_container_<utc>.md unless --no-pass-doc.'
        ),
    )
    runc.add_argument(
        '--no-pass-doc',
        action='store_true',
        help='With --pass-trials>1, do not auto-write the pass metrics Markdown file.',
    )
    runc.add_argument(
        '--summary',
        nargs='?',
        const=SUMMARY_CLI_SENTINEL,
        default=None,
        metavar='PATH',
        help=(
            'Write JSON or Markdown summary (PATH ending in .md) with rollup + per-case results. '
            'Bare --summary uses runs/<--run-date>/summary_run_container_<utc>.json'
        ),
    )
    runc.set_defaults(handler=run_container_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == '__main__':
    raise SystemExit(main())
