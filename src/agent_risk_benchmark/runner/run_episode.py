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

import yaml


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
DEFAULT_BASE_URL = 'http://127.0.0.1:19789'
DEFAULT_AGENT_ID = 'main'
DEFAULT_SUITE = 'openclaw_safety'
DEFAULT_REQUEST_TIMEOUT_SEC = 180
DEFAULT_TRACE_WAIT_SEC = 10.0
DEFAULT_WORKSPACE_APPLY_WAIT_SEC = 2.0
TRACE_POLL_INTERVAL_SEC = 0.25


def emit_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def format_progress(case_id: str, phase: str, *, index: int | None = None, total: int | None = None) -> str:
    if index is not None and total is not None:
        return f'[{index}/{total}] {case_id}: {phase}'
    return f'{case_id}: {phase}'


def load_case_config(case_dir: Path) -> dict[str, Any]:
    return yaml.safe_load((case_dir / 'case.yaml').read_text(encoding='utf-8'))


def discover_cases(cases_root: Path) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    for case_file in sorted(cases_root.rglob('case.yaml')) if cases_root.exists() else []:
        case_dir = case_file.parent
        if case_dir.name.startswith('.') or case_dir.name == '__pycache__':
            continue

        case_config = load_case_config(case_dir)
        case_id = str(case_config.get('case_id', '')).strip()
        if not case_id:
            raise ValueError(f'missing case_id in {case_file}')

        rel_parts = case_dir.relative_to(cases_root).parts
        category = rel_parts[0] if len(rel_parts) > 1 else 'uncategorized'
        discovered.append(
            {
                'case_id': case_id,
                'category': category,
                'case_dir': case_dir.resolve(),
            }
        )
    return discovered


def resolve_cases_root(cases_root_arg: str | None) -> Path:
    raw = (cases_root_arg or 'cases').strip()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (REPO_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists():
        raise FileNotFoundError(f'cases root not found: {candidate}')
    if not candidate.is_dir():
        raise ValueError(f'cases root is not a directory: {candidate}')
    return candidate


def resolve_run_case_dirs(args: argparse.Namespace) -> list[Path]:
    case_dirs_arg = list(getattr(args, 'case_dirs', []) or [])
    case_ids = list(getattr(args, 'case_ids', []) or [])
    categories = list(getattr(args, 'categories', []) or [])
    run_all = bool(getattr(args, 'run_all', False))

    if run_all and (case_dirs_arg or case_ids or categories):
        raise ValueError('--all cannot be combined with --case-dir, --case, or --category')

    cases_root = resolve_cases_root(getattr(args, 'cases_root', None))
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


def sum_trace_tokens(trace_path: Path | None) -> dict[str, int]:
    """Sum token usage across all turns recorded in an openclaw trace JSONL file.

    Each turn may carry a ``usage`` object at the top level or inside ``message``.
    Recognised keys: ``input``, ``output``, ``cacheRead``, ``cacheWrite``, ``totalTokens``.
    Returns a dict with snake_case keys: input / output / cache_read / cache_write / total.
    """
    totals: dict[str, int] = {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0, 'total': 0}
    if trace_path is None or not Path(trace_path).exists():
        return totals
    for raw in Path(trace_path).read_text(encoding='utf-8').splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            continue
        usage = record.get('usage')
        if not isinstance(usage, dict):
            msg = record.get('message')
            usage = msg.get('usage') if isinstance(msg, dict) else None
        if not isinstance(usage, dict):
            continue
        totals['input'] += int(usage.get('input', 0))
        totals['output'] += int(usage.get('output', 0))
        totals['cache_read'] += int(usage.get('cacheRead', 0))
        totals['cache_write'] += int(usage.get('cacheWrite', 0))
        totals['total'] += int(usage.get('totalTokens', 0))
    return totals


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
        category = case_dir.parent.name
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
        'results': results,
    }
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


# ── Container execution path ───────────────────────────────────────────────────
# mirrors WildClawBench's eval/run_batch.py but adapted to agent-risk-benchmark's
# case format (case.yaml / workspace-exp / oracle.py).

from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402

CONTAINER_WORKSPACE      = '/root/.openclaw/workspace'
CONTAINER_AGENT_SESSION  = 'bench-run'
DEFAULT_CONTAINER_IMAGE  = 'openclaw-bench:v1.0'


def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(['docker', *args], capture_output=True, text=True, check=check)


def container_start(name: str, workspace_dir: Path, run_dir: Path, image: str, env_vars: dict[str, str]) -> None:
    """Start a detached container.

    Mounts:
      workspace_dir → CONTAINER_WORKSPACE  (rw) so openclaw reads/writes host files directly
      run_dir       → /run_dir             (rw) for direct result sharing
    """
    env_args: list[str] = []
    for k, v in env_vars.items():
        env_args += ['-e', f'{k}={v}']
    # Clear any proxy env vars baked into the image so that the agent can reach
    # external APIs directly (the image may carry https_proxy that points to a
    # host-side proxy unreachable from inside the container).
    no_proxy_args = [
        '-e', 'http_proxy=',
        '-e', 'https_proxy=',
        '-e', 'HTTP_PROXY=',
        '-e', 'HTTPS_PROXY=',
        '-e', 'no_proxy=',
        '-e', 'NO_PROXY=',
    ]
    r = subprocess.run(
        ['docker', 'run', '-d', '--name', name,
         *no_proxy_args,
         *env_args,
         '-v', f'{workspace_dir}:{CONTAINER_WORKSPACE}',
         '-v', f'{run_dir}:/run_dir',
         image, '/bin/bash', '-c', 'tail -f /dev/null'],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f'Container start failed:\n{r.stderr}')


def container_exec(name: str, bash_cmd: str, *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['docker', 'exec', name, '/bin/bash', '-c', bash_cmd],
        capture_output=True, text=True, check=check,
    )


def container_exec_background(name: str, bash_cmd: str, log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open('w', encoding='utf-8')
    proc = subprocess.Popen(
        ['docker', 'exec', name, '/bin/bash', '-c',
         f'cd {CONTAINER_WORKSPACE} && {bash_cmd}'],
        stdout=log_file, stderr=subprocess.STDOUT, encoding='utf-8',
    )
    proc._log_file = log_file  # type: ignore[attr-defined]
    return proc


def container_cp_from(name: str, container_path: str, host_path: Path) -> bool:
    r = subprocess.run(
        ['docker', 'cp', f'{name}:{container_path}', str(host_path)],
        capture_output=True, text=True,
    )
    return r.returncode == 0


def container_cp_to(name: str, host_path: Path, container_path: str) -> bool:
    r = subprocess.run(
        ['docker', 'cp', f'{host_path}/.', f'{name}:{container_path}'],
        capture_output=True, text=True,
    )
    return r.returncode == 0


def container_rm(name: str) -> None:
    subprocess.run(['docker', 'rm', '-f', name], capture_output=True)


def container_setup_workspace(name: str) -> None:
    """Ensure the mounted workspace is writable (host dir is already mounted at CONTAINER_WORKSPACE)."""
    container_exec(name, f'chmod -R u+w {CONTAINER_WORKSPACE}')


def container_set_model(name: str, model: str) -> None:
    container_exec(name, f"openclaw models set '{model}'")


def container_run_case(
    case_dir: Path,
    run_dir: Path,
    *,
    image: str,
    model: str | None,
    model_api_key: str = '',
    run_idx: int,
    run_total: int,
) -> dict[str, Any]:
    """
    Full container lifecycle for one case:
      prepare → start container (run_dir mounted as /run_dir) →
      docker-cp workspace in → gateway → agent → collect → score → cleanup.

    API keys are injected at runtime via env-var prefixes on the gateway command
    so that no credentials need to be baked into the Docker image.
    `model_api_key` is exported as both MOONSHOT_API_KEY and OPENROUTER_API_KEY
    so it works regardless of which provider the model string resolves to.

    Returns a result dict matching the existing run_command output schema.
    """
    case_config = load_case_config(case_dir)
    case_id     = str(case_config['case_id'])
    timeout_sec = int(case_config.get('timeout_sec', DEFAULT_REQUEST_TIMEOUT_SEC))
    prompt      = (run_dir / 'prompt.txt').read_text(encoding='utf-8')
    workspace_dir = run_dir / 'workspace'

    # Container name is per-case only (no run suffix) so that any leftover
    # container from a previous interrupted run is always replaced on next run.
    task_id = f'risk-bench-{case_id}'[:63]
    task_id = task_id.replace('_', '-')

    # Each container runs its OWN openclaw gateway internally.
    # No host gateway involvement → full isolation, safe for parallel runs.
    # API keys are NOT baked into the image; they are injected at runtime via
    # `docker run -e` and also exported explicitly before the gateway command.
    # model_api_key is exported as both MOONSHOT_API_KEY and OPENROUTER_API_KEY
    # so it works regardless of which LLM provider the model string resolves to.
    env_vars: dict[str, str] = {
        'BRAVE_API_KEY': os.environ.get('BRAVE_API_KEY', 'placeholder'),
    }
    if model_api_key:
        env_vars['MOONSHOT_API_KEY']    = model_api_key
        env_vars['OPENROUTER_API_KEY']  = model_api_key
        env_vars['MODEL_API_KEY']       = model_api_key

    emit_progress(format_progress(case_id, 'container-start', index=run_idx, total=run_total))

    agent_proc   = None
    gateway_proc = None
    started      = time.time()

    try:
        # 1. Start container:
        #    workspace_dir → CONTAINER_WORKSPACE (openclaw reads/writes host files directly)
        #    run_dir       → /run_dir (logs and results shared with host)
        container_rm(task_id)   # clean up any leftover from a previous interrupted run
        container_start(task_id, workspace_dir, run_dir, image, env_vars)

        # 2. Ensure the mounted workspace is writable.
        container_setup_workspace(task_id)

        # 3. Run openclaw-init inside the container to populate openclaw.json
        #    with the correct model + provider + auth config from env vars.
        #    This keeps the Docker image credential-free.
        effective_model = model or 'moonshot/kimi-k2.5'
        init_cmd = f"OPENCLAW_MODEL='{effective_model}' MODEL_API_KEY='{model_api_key}' openclaw-init"
        container_exec(task_id, init_cmd)

        # 4. Start the in-container openclaw gateway on CONTAINER_GATEWAY_PORT.
        #    Each container has an isolated network namespace, so port conflicts
        #    between parallel containers are impossible.
        #    API keys are exported explicitly before the gateway command so that
        #    the gateway process can authenticate with the LLM provider.
        emit_progress(format_progress(case_id, 'container-gateway', index=run_idx, total=run_total))
        gw_env_prefix = ''
        if model_api_key:
            gw_env_prefix += (
                f"export MOONSHOT_API_KEY='{model_api_key}' && "
                f"export OPENROUTER_API_KEY='{model_api_key}' && "
                f"export MODEL_API_KEY='{model_api_key}' && "
            )
        gateway_proc = container_exec_background(
            task_id,
            f'{gw_env_prefix}openclaw gateway',
            log_path=run_dir / 'gateway.log',
        )
        time.sleep(4)   # wait for gateway to be ready

        # 5. Run agent inside container (connects to its own gateway).
        emit_progress(format_progress(case_id, 'container-agent', index=run_idx, total=run_total))
        safe_prompt = prompt.replace("'", "'\\''")
        agent_proc = container_exec_background(
            task_id,
            f"openclaw agent --session-id {CONTAINER_AGENT_SESSION} --timeout {timeout_sec} --message '{safe_prompt}'",
            log_path=run_dir / 'agent.log',
        )
        try:
            agent_proc.wait(timeout=timeout_sec + 30)
        except subprocess.TimeoutExpired:
            agent_proc.kill()
            agent_proc.wait()

        elapsed = round(time.time() - started, 3)

        # 6. Collect: copy session trace JSONL from container.
        #    (workspace is a direct volume mount — no docker cp needed for files)
        emit_progress(format_progress(case_id, 'container-collect', index=run_idx, total=run_total))
        container_session_jsonl = f'/root/.openclaw/agents/main/sessions/{CONTAINER_AGENT_SESSION}.jsonl'
        trace_host = run_dir / f'{CONTAINER_AGENT_SESSION}.jsonl'
        if container_cp_from(task_id, container_session_jsonl, trace_host):
            token_usage = sum_trace_tokens(trace_host)
        else:
            token_usage = {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0, 'total': 0}

    except Exception as exc:
        elapsed = round(time.time() - started, 3)
        return {
            'case_id': case_id,
            'run_dir': str(run_dir),
            'workspace_dir': str(workspace_dir),
            'error': f'{type(exc).__name__}: {exc}',
            'task_success': False,
            'safety_success': False,
            'score': 0.0,
            'token_usage': {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0, 'total': 0},
            'execute_duration_sec': elapsed,
            'container_image': image,
        }

    finally:
        # Close background process log files and destroy container
        for proc in [agent_proc, gateway_proc]:
            if proc is not None:
                log_file = getattr(proc, '_log_file', None)
                if log_file and not log_file.closed:
                    log_file.close()
        container_rm(task_id)

    # 8. Score using oracle.py on the host
    emit_progress(format_progress(case_id, 'score', index=run_idx, total=run_total))
    try:
        score = evaluate_run(case_dir, run_dir)
    except Exception as exc:
        score = {'task_success': False, 'safety_success': False, 'score': 0.0,
                 'error': f'oracle error: {exc}'}

    return {
        'case_id': case_id,
        'run_dir': str(run_dir),
        'workspace_dir': str(workspace_dir),
        'task_success': score.get('task_success', False),
        'safety_success': score.get('safety_success', False),
        'score': score.get('score', 0.0),
        'token_usage': token_usage,
        'execute_duration_sec': elapsed,
        'container_image': image,
    }


def load_local_environment() -> dict[str, Any]:
    env_path = REPO_ROOT / 'environment.json'
    if not env_path.exists():
        return {}
    return load_json_dict(env_path, label='environment.json')


def _resolve_container_args(args: argparse.Namespace, local_env: dict[str, Any]) -> dict[str, Any]:
    image = getattr(args, 'container_image', None) or local_env.get('container_image') or DEFAULT_CONTAINER_IMAGE
    # model: CLI arg > environment.json 'model' > environment.json 'default_model' > None
    model = (
        getattr(args, 'model', None)
        or local_env.get('model')
        or local_env.get('default_model')
        or None
    )
    parallel = max(1, int(getattr(args, 'parallel', 1) or 1))
    # Generic model API key: environment.json 'model_api_key' > shell env vars.
    # The value is exported into the container as both MOONSHOT_API_KEY and
    # OPENROUTER_API_KEY so that whichever provider the chosen model uses will
    # automatically pick it up — no provider-specific field names required.
    model_api_key = (
        local_env.get('model_api_key', '')
        or os.environ.get('MOONSHOT_API_KEY', '')
        or os.environ.get('OPENROUTER_API_KEY', '')
        or os.environ.get('MODEL_API_KEY', '')
    )
    return {
        'image': image,
        'model': model,
        'parallel': parallel,
        'model_api_key': model_api_key,
    }


def run_container_command(args: argparse.Namespace) -> int:
    import signal

    case_dirs  = resolve_run_case_dirs(args)
    local_env  = load_local_environment()
    ctr        = _resolve_container_args(args, local_env)
    run_date   = args.run_date
    total      = len(case_dirs)

    emit_progress(
        f'run-container: {total} case(s), image={ctr["image"]}, '
        f'model={ctr["model"] or "openclaw:main"}, parallel={ctr["parallel"]}'
    )

    results: list[dict[str, Any]] = []
    batch_started = time.time()
    overall_exit  = 0

    # On Ctrl-C / SIGTERM, clean up any leftover risk-bench-* containers
    def _cleanup_on_exit(signum, frame):  # noqa: ANN001
        emit_progress('\n[run-container] interrupted — cleaning up containers...')
        subprocess.run(
            'docker ps -a --filter "name=risk-bench-" -q | xargs -r docker rm -f',
            shell=True, capture_output=True,
        )
        sys.exit(1)

    signal.signal(signal.SIGINT,  _cleanup_on_exit)
    signal.signal(signal.SIGTERM, _cleanup_on_exit)

    def _run_one(idx_case: tuple[int, Path]) -> dict[str, Any]:
        idx, case_dir = idx_case
        case_id = case_dir.name
        try:
            emit_progress(format_progress(case_id, 'prepare', index=idx, total=total))
            _case_config, run_dir = materialize_run(case_dir, run_date, getattr(args, 'run_name', None))
            result = container_run_case(
                case_dir, run_dir,
                image=ctr['image'],
                model=ctr['model'],
                model_api_key=ctr.get('model_api_key', ''),
                run_idx=idx,
                run_total=total,
            )
            emit_progress(
                format_progress(case_id, f'complete (score={result.get("score")})', index=idx, total=total)
            )
            return result
        except Exception as exc:
            emit_progress(format_progress(case_id, f'failed ({type(exc).__name__}: {exc})', index=idx, total=total))
            return {
                'case_id': case_id,
                'task_success': False,
                'safety_success': False,
                'score': 0.0,
                'error': str(exc),
            }

    indexed = list(enumerate(case_dirs, start=1))
    if ctr['parallel'] == 1:
        results = [_run_one(ic) for ic in indexed]
    else:
        with ThreadPoolExecutor(max_workers=ctr['parallel']) as pool:
            futures = {pool.submit(_run_one, ic): ic for ic in indexed}
            for fut in as_completed(futures):
                results.append(fut.result())

    batch_elapsed = round(time.time() - batch_started, 3)
    batch_summary = {
        'mode': 'container_run',
        'container_image': ctr['image'],
        'model': ctr['model'],
        'selected_count': total,
        'completed_count': sum(1 for r in results if 'error' not in r),
        'error_count': sum(1 for r in results if 'error' in r),
        'task_success_count':   sum(1 for r in results if r.get('task_success')),
        'safety_success_count': sum(1 for r in results if r.get('safety_success')),
        'full_success_count':   sum(1 for r in results if r.get('task_success') and r.get('safety_success')),
        'batch_duration_sec': batch_elapsed,
        'total_token_usage': {
            'input':       sum(r.get('token_usage', {}).get('input', 0) for r in results),
            'output':      sum(r.get('token_usage', {}).get('output', 0) for r in results),
            'cache_read':  sum(r.get('token_usage', {}).get('cache_read', 0) for r in results),
            'cache_write': sum(r.get('token_usage', {}).get('cache_write', 0) for r in results),
            'total':       sum(r.get('token_usage', {}).get('total', 0) for r in results),
        },
        'results': results,
    }
    print(json.dumps(batch_summary, indent=2))

    if any('error' in r for r in results):
        overall_exit = 1
    return overall_exit


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

    # ── run-container ──────────────────────────────────────────────────────────
    runc = subparsers.add_parser(
        'run-container',
        help='Run cases inside Docker containers (gateway + agent run in the container).',
        description=(
            'Container-based execution path: spins up a Docker container per case, '
            'runs openclaw gateway + agent inside it, collects results, and scores with oracle.py. '
            'Mirrors WildClawBench eval/run_batch.py but uses agent-risk-benchmark case format.'
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
    runc.set_defaults(handler=run_container_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == '__main__':
    raise SystemExit(main())
