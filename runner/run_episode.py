from __future__ import annotations

import argparse
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


REPO_ROOT = Path(__file__).resolve().parent.parent
ORACLE_PATH = REPO_ROOT / 'oracle.py'
RUNS_ROOT = REPO_ROOT / 'runs'
DEFAULT_BASE_URL = 'http://127.0.0.1:19789'
DEFAULT_MODEL = 'openclaw:main'
DEFAULT_AGENT_ID = 'main'
DEFAULT_SUITE = 'openclaw_safety'
DEFAULT_REQUEST_TIMEOUT_SEC = 180


def load_case_config(case_dir: Path) -> dict[str, Any]:
    return yaml.safe_load((case_dir / 'case.yaml').read_text(encoding='utf-8'))


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
    lines = [
        json.dumps({'role': 'user', 'content': prompt}, ensure_ascii=False),
    ]
    if assistant_text:
        lines.append(json.dumps({'role': 'assistant', 'content': assistant_text}, ensure_ascii=False))
    transcript_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def evaluate_run(case_dir: Path, run_dir: Path) -> dict[str, Any]:
    output_path = run_dir / 'score.json'
    subprocess.run(
        [
            sys.executable,
            str(ORACLE_PATH),
            '--case-dir',
            str(case_dir),
            '--run-dir',
            str(run_dir),
            '--output',
            str(output_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(output_path.read_text(encoding='utf-8'))


def prepare_command(args: argparse.Namespace) -> int:
    case_dir = Path(args.case_dir).resolve()
    case_config, run_dir = materialize_run(case_dir, args.run_date, args.run_name)
    summary = {
        'case_id': case_config['case_id'],
        'run_dir': str(run_dir),
        'workspace_dir': str((run_dir / 'workspace').resolve()),
        'prompt_file': str((run_dir / 'prompt.txt').resolve()),
        'next_step': 'Update your OpenClaw agent workspace to workspace_dir, then run the execute subcommand.',
    }
    print(json.dumps(summary, indent=2))
    return 0


def execute_command(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    metadata = load_run_metadata(run_dir)
    case_dir = Path(metadata['case_dir'])
    case_config = load_case_config(case_dir)
    prompt = (run_dir / 'prompt.txt').read_text(encoding='utf-8')
    timeout_sec = int(case_config.get('timeout_sec', DEFAULT_REQUEST_TIMEOUT_SEC))

    bearer_token = args.bearer_token or os.environ.get('OPENCLAW_BENCH_TOKEN')
    if not bearer_token:
        raise ValueError('missing bearer token: provide --bearer-token or set OPENCLAW_BENCH_TOKEN')

    session_path = run_dir / 'session.json'
    if args.session_key:
        session_key = args.session_key
    elif session_path.exists():
        session_key = json.loads(session_path.read_text(encoding='utf-8'))['session_key']
    else:
        session_key = build_session_key(metadata['case_id'], metadata['run_id'])

    invocation = invoke_openclaw_chat(
        base_url=args.base_url,
        bearer_token=bearer_token,
        model=args.model,
        prompt=prompt,
        session_key=session_key,
        timeout_sec=timeout_sec,
        agent_id=args.agent_id,
    )

    parsed_response = parse_json_maybe(invocation['response_text'])
    assistant_text = extract_assistant_text(parsed_response or {}) if parsed_response else ''

    write_json(run_dir / 'openclaw_request.json', invocation['request'])
    write_json(
        run_dir / 'session.json',
        {
            'session_key': session_key,
            'base_url': args.base_url,
            'model': args.model,
            'agent_id': args.agent_id,
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

    metadata = update_metadata(
        run_dir,
        status='executed',
        executed_at_epoch=time.time(),
        openclaw_base_url=args.base_url,
        openclaw_model=args.model,
        openclaw_agent_id=args.agent_id,
        session_key=session_key,
        request_status_code=invocation['status_code'],
    )

    if not invocation['ok']:
        metadata = update_metadata(
            run_dir,
            status='http_failed',
            http_error=invocation.get('error'),
        )
        summary = {
            'case_id': metadata['case_id'],
            'run_dir': str(run_dir),
            'workspace_dir': metadata['workspace_dir'],
            'session_key': session_key,
            'http_ok': False,
            'http_status_code': invocation['status_code'],
            'error': invocation.get('error'),
        }
        print(json.dumps(summary, indent=2))
        return 2

    if parsed_response is None:
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
        }
        print(json.dumps(summary, indent=2))
        return 2

    score = evaluate_run(case_dir, run_dir)
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
    }
    print(json.dumps(summary, indent=2))
    return 0


def score_command(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    metadata = load_run_metadata(run_dir)
    case_dir = Path(metadata['case_dir'])
    score = evaluate_run(case_dir, run_dir)
    print(json.dumps(score, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Prepare, execute, and score benchmark episodes against OpenClaw.')
    subparsers = parser.add_subparsers(dest='subcommand', required=True)

    prepare = subparsers.add_parser('prepare', help='Create a run directory and copy the initial workspace.')
    prepare.add_argument('--case-dir', required=True, help='Path to a case directory, for example cases/cfg_overwrite_001.')
    prepare.add_argument('--run-date', default=str(date.today()), help='Date partition for the run directory.')
    prepare.add_argument('--run-name', help='Run directory name, default is the next available runN.')
    prepare.set_defaults(handler=prepare_command)

    execute = subparsers.add_parser('execute', help='Send the case prompt to an already-configured OpenClaw Gateway.')
    execute.add_argument('--run-dir', required=True, help='Path to an existing run directory under runs/.')
    execute.add_argument('--base-url', default=DEFAULT_BASE_URL, help='OpenClaw Gateway base URL.')
    execute.add_argument('--bearer-token', help='Gateway bearer token. Defaults to OPENCLAW_BENCH_TOKEN if omitted.')
    execute.add_argument('--model', default=DEFAULT_MODEL, help='OpenClaw model name, for example openclaw:main.')
    execute.add_argument('--agent-id', default=DEFAULT_AGENT_ID, help='Optional x-openclaw-agent-id header value.')
    execute.add_argument('--session-key', help='Optional explicit session key override for this run.')
    execute.set_defaults(handler=execute_command)

    score = subparsers.add_parser('score', help='Run the oracle for an existing run directory.')
    score.add_argument('--run-dir', required=True, help='Path to an existing run directory under runs/.')
    score.set_defaults(handler=score_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == '__main__':
    raise SystemExit(main())
