"""Container-based execution path for agent-risk-benchmark.

Mirrors WildClawBench's eval/run_batch.py but adapted to agent-risk-benchmark's
case format (case.yaml / workspace-exp / oracle.py).

Each case spins up an isolated Docker container that runs its own openclaw
gateway + agent internally. Results and traces are collected back to the host
run directory via volume mounts and ``docker cp``.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# Shared utilities are imported from run_episode at function-call time to
# avoid a circular-import error at module load time (run_episode imports
# run_container_command from here; we import helpers from run_episode).
# All symbols below are resolved lazily inside the functions that use them.


CONTAINER_WORKSPACE = '/root/.openclaw/workspace'
CONTAINER_AGENT_SESSION = 'bench-run'
DEFAULT_CONTAINER_IMAGE = 'openclaw-bench:v1.0'


# ── Low-level Docker helpers ───────────────────────────────────────────────────

def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(['docker', *args], capture_output=True, text=True, check=check)


def container_start(
    name: str,
    workspace_dir: Path,
    run_dir: Path,
    image: str,
    env_vars: dict[str, str],
) -> None:
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
        [
            'docker', 'run', '-d', '--name', name,
            *no_proxy_args,
            *env_args,
            '-v', f'{workspace_dir}:{CONTAINER_WORKSPACE}',
            '-v', f'{run_dir}:/run_dir',
            image, '/bin/bash', '-c', 'tail -f /dev/null',
        ],
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


# ── High-level per-case lifecycle ─────────────────────────────────────────────

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
    """Full container lifecycle for one case.

    prepare → start container (run_dir mounted as /run_dir) →
    docker-cp workspace in → gateway → agent → collect → score → cleanup.

    API keys are injected at runtime via env-var prefixes on the gateway command
    so that no credentials need to be baked into the Docker image.
    ``model_api_key`` is exported as both MOONSHOT_API_KEY and OPENROUTER_API_KEY
    so it works regardless of which provider the model string resolves to.

    Returns a result dict matching the existing run_command output schema.
    """
    # Deferred imports to avoid circular dependency at module load time.
    from .run_episode import (  # noqa: PLC0415
        DEFAULT_REQUEST_TIMEOUT_SEC,
        emit_progress,
        evaluate_run,
        format_progress,
        load_case_config,
        sum_trace_tokens,
    )

    case_config = load_case_config(case_dir)
    case_id = str(case_config['case_id'])
    timeout_sec = int(case_config.get('timeout_sec', DEFAULT_REQUEST_TIMEOUT_SEC))
    prompt = (run_dir / 'prompt.txt').read_text(encoding='utf-8')
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
        env_vars['MOONSHOT_API_KEY'] = model_api_key
        env_vars['OPENROUTER_API_KEY'] = model_api_key
        env_vars['MODEL_API_KEY'] = model_api_key

    emit_progress(format_progress(case_id, 'container-start', index=run_idx, total=run_total))
    started = time.time()
    gateway_proc = None
    agent_proc = None

    # 1. Start container:
    #    workspace_dir → CONTAINER_WORKSPACE (openclaw reads/writes host files directly)
    #    run_dir       → /run_dir (logs and results shared with host)
    container_rm(task_id)  # clean up any leftover from a previous interrupted run
    container_start(task_id, workspace_dir, run_dir, image, env_vars)
    try:
        container_setup_workspace(task_id)

        # 2. Run openclaw-init inside the container to populate openclaw.json
        #    with the correct model + provider + auth config from env vars.
        #    This keeps the Docker image credential-free.
        effective_model = model or 'moonshot/kimi-k2.5'
        container_exec(task_id, f"OPENCLAW_MODEL='{effective_model}' MODEL_API_KEY='{model_api_key}' openclaw-init")

        # 3. Start the in-container openclaw gateway.
        #    Each container has an isolated network namespace so port conflicts
        #    between parallel containers are impossible.
        emit_progress(format_progress(case_id, 'container-gateway', index=run_idx, total=run_total))
        gw_env_prefix = ''
        if model_api_key:
            gw_env_prefix = (
                f"export MOONSHOT_API_KEY='{model_api_key}' && "
                f"export OPENROUTER_API_KEY='{model_api_key}' && "
                f"export MODEL_API_KEY='{model_api_key}' && "
            )
        gateway_proc = container_exec_background(
            task_id,
            f'{gw_env_prefix}openclaw gateway',
            log_path=run_dir / 'gateway.log',
        )
        time.sleep(4)  # wait for gateway to be ready

        # 4. Run agent inside container (connects to its own gateway).
        emit_progress(format_progress(case_id, 'container-agent', index=run_idx, total=run_total))
        safe_prompt = prompt.replace("'", "'\\''")
        agent_proc = container_exec_background(
            task_id,
            f"openclaw agent --session-id {CONTAINER_AGENT_SESSION} --timeout {timeout_sec} --message '{safe_prompt}'",
            log_path=run_dir / 'agent.log',
        )
        deadline = time.time() + timeout_sec + 30
        while agent_proc.poll() is None and time.time() < deadline:
            time.sleep(0.5)
        if agent_proc.poll() is None:
            agent_proc.kill()
            agent_proc.wait()

        elapsed = round(time.time() - started, 3)

        # 5. Collect: copy session trace JSONL from container.
        #    (workspace is a direct volume mount — no docker cp needed for workspace files)
        emit_progress(format_progress(case_id, 'container-collect', index=run_idx, total=run_total))
        container_session_jsonl = f'/root/.openclaw/agents/main/sessions/{CONTAINER_AGENT_SESSION}.jsonl'
        trace_host = run_dir / f'{CONTAINER_AGENT_SESSION}.jsonl'
        if container_cp_from(task_id, container_session_jsonl, trace_host):
            token_usage = sum_trace_tokens(trace_host)
        else:
            token_usage = {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0, 'total': 0}

    finally:
        # Always close log file handles and destroy the container, even on error.
        for proc in [agent_proc, gateway_proc]:
            if proc is not None:
                log_file = getattr(proc, '_log_file', None)
                if log_file and not log_file.closed:
                    log_file.close()
        container_rm(task_id)

    # 6. Score using oracle.py on the host.
    emit_progress(format_progress(case_id, 'score', index=run_idx, total=run_total))
    score = evaluate_run(case_dir, run_dir)

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


# ── Batch container command ────────────────────────────────────────────────────

def load_local_environment() -> dict[str, Any]:
    """Load optional environment.json from the benchmark repo root."""
    from .run_episode import REPO_ROOT, load_json_dict  # noqa: PLC0415

    env_path = REPO_ROOT / 'environment.json'
    if not env_path.exists():
        return {}
    return load_json_dict(env_path, label='environment.json')


def _resolve_container_args(args: Any, local_env: dict[str, Any]) -> dict[str, Any]:
    """Resolve container execution parameters from CLI args and environment.json."""
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


def run_container_command(args: Any) -> int:
    """CLI handler for the ``run-container`` subcommand."""
    from .run_episode import (  # noqa: PLC0415
        emit_progress,
        format_progress,
        materialize_run,
        resolve_run_case_dirs,
    )

    case_dirs = resolve_run_case_dirs(args)
    local_env = load_local_environment()
    ctr = _resolve_container_args(args, local_env)
    run_date = args.run_date
    total = len(case_dirs)

    emit_progress(
        f'run-container: {total} case(s), image={ctr["image"]}, '
        f'model={ctr["model"] or "openclaw:main"}, parallel={ctr["parallel"]}'
    )

    results: list[dict[str, Any]] = []
    batch_started = time.time()
    overall_exit = 0

    # On Ctrl-C / SIGTERM, clean up any leftover risk-bench-* containers
    def _cleanup_on_exit(signum, frame):  # noqa: ANN001
        emit_progress('\n[run-container] interrupted — cleaning up containers...')
        subprocess.run(
            'docker ps -a --filter "name=risk-bench-" -q | xargs -r docker rm -f',
            shell=True, capture_output=True,
        )
        sys.exit(1)

    signal.signal(signal.SIGINT, _cleanup_on_exit)
    signal.signal(signal.SIGTERM, _cleanup_on_exit)

    def _run_one(idx_case: tuple[int, Path]) -> dict[str, Any]:
        idx, case_dir = idx_case
        case_id = case_dir.name
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
        emit_progress(format_progress(case_id, f'complete (score={result.get("score")})', index=idx, total=total))
        return result

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
        'task_success_count': sum(1 for r in results if r.get('task_success')),
        'safety_success_count': sum(1 for r in results if r.get('safety_success')),
        'full_success_count': sum(1 for r in results if r.get('task_success') and r.get('safety_success')),
        'batch_duration_sec': batch_elapsed,
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

    if any('error' in r for r in results):
        overall_exit = 1
    return overall_exit
