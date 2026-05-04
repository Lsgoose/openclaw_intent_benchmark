"""Container-based execution path for agent-risk-benchmark.

Mirrors WildClawBench's eval/run_batch.py but adapted to agent-risk-benchmark's
case format (case.yaml / workspace-exp / oracle.py).

Each case spins up an isolated Docker container that runs its own openclaw
gateway + agent internally. Results and traces are collected back to the host
run directory via volume mounts and ``docker cp``.
"""
from __future__ import annotations

import csv
import hashlib
import os
import queue
import shlex
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Shared utilities are imported from run_episode at function-call time to
# avoid a circular-import error at module load time (run_episode imports
# run_container_command from here; we import helpers from run_episode).
# All symbols below are resolved lazily inside the functions that use them.


CONTAINER_WORKSPACE = '/root/.openclaw/workspace'
CONTAINER_AGENT_SESSION = 'bench-run'
DEFAULT_CONTAINER_IMAGE = 'openclaw-bench:v1.0'


def _use_litellm_proxy_init() -> bool:
    v = os.environ.get('OPENCLAW_USE_LITELLM_PROXY', '').strip().lower()
    return v in ('1', 'true', 'yes')


def _use_softcoding_init() -> bool:
    """Use openclaw-init-softcoding (Ofox bases from environment.json /run_dir copy)."""
    v = os.environ.get('OPENCLAW_USE_SOFTCODING_INIT', '').strip().lower()
    return v in ('1', 'true', 'yes')


def _litellm_proxy_container_env() -> dict[str, str]:
    """Forward LiteLLM proxy settings from host into the bench container (for openclaw-init-proxy)."""
    out: dict[str, str] = {}
    for k in (
        'LITELLM_PROXY_BASE',
        'LITELLM_PROXY_ANTHROPIC_BASE',
        'LITELLM_PROXY_GEMINI_BASE',
        'OFOX_ANTHROPIC_API',
    ):
        v = os.environ.get(k, '').strip()
        if v:
            out[k] = v
    return out


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
    # Linux Docker often has no host.docker.internal unless explicitly mapped; bench containers
    # that use LITELLM_PROXY_BASE=http://host.docker.internal:... would otherwise get
    # "LLM request failed: network connection error".
    extra_run_args: list[str] = []
    proxy_base = (env_vars.get('LITELLM_PROXY_BASE') or '').strip()
    if proxy_base and 'host.docker.internal' in proxy_base:
        extra_run_args.extend(['--add-host=host.docker.internal:host-gateway'])

    r = subprocess.run(
        [
            'docker', 'run', '-d', '--name', name,
            *extra_run_args,
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
    llm_params: dict[str, str] | None = None,
    run_idx: int,
    run_total: int,
    softcoding_port_pool: queue.Queue[int] | None = None,
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
        evaluate_run,
    )
    from .tools import (  # noqa: PLC0415
        emit_progress,
        format_progress,
        load_case_config,
        sum_trace_tokens,
    )

    case_config = load_case_config(case_dir)
    case_id = str(case_config['case_id'])
    timeout_sec = int(case_config.get('timeout_sec', DEFAULT_REQUEST_TIMEOUT_SEC))
    prompt = (run_dir / 'prompt.txt').read_text(encoding='utf-8')
    workspace_dir = run_dir / 'workspace'

    # Docker name must be unique per run_dir: same case_id can run concurrently
    # (e.g. ROUNDS=2, or pass-trials) with different --run-name / run1..runN paths.
    _fp = hashlib.sha256(str(run_dir.resolve()).encode('utf-8')).hexdigest()[:20]
    task_id = f'risk-bench-{_fp}'[:63]

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
    env_vars.update(_litellm_proxy_container_env())

    emit_progress(format_progress(case_id, 'container-start', index=run_idx, total=run_total))
    started = time.time()
    gateway_proc = None
    agent_proc = None
    gw_port: int | None = None
    gw_token = f'bench-{_fp}'

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
        # shlex.quote avoids shell breakage if model or key contains quotes/spaces.
        init_env = (
            f"OPENCLAW_MODEL={shlex.quote(effective_model)} "
            f"MODEL_API_KEY={shlex.quote(model_api_key)}"
        )
        lp = llm_params or {}
        for env_name, key in (
            ('TEMPERATURE', 'temperature'),
            ('TOP_P', 'topP'),
            ('MAX_TOKENS', 'maxTokens'),
        ):
            v = lp.get(key)
            if v is not None and str(v).strip() != '':
                init_env += f" {env_name}={shlex.quote(str(v).strip())}"
        if _use_litellm_proxy_init():
            init_bin = 'openclaw-init-proxy'
        elif _use_softcoding_init():
            init_bin = 'openclaw-init-softcoding'
        else:
            init_bin = 'openclaw-init'
        container_exec(task_id, f"{init_env} {init_bin}")

        # 3. Start the in-container openclaw gateway.
        #    Each container has an isolated network namespace so port conflicts
        #    between parallel containers are impossible.
        emit_progress(format_progress(case_id, 'container-gateway', index=run_idx, total=run_total))
        if _use_softcoding_init():
            # Use a deterministic port pool so that a user can optionally expose/inspect the gateway
            # via host networking, and so logs are predictable across parallel runs.
            if softcoding_port_pool is None:
                gw_port = 20000
            else:
                gw_port = int(softcoding_port_pool.get())
        else:
            gw_port = None
        gw_env_prefix = ''
        if model_api_key:
            gw_env_prefix = (
                f"export MOONSHOT_API_KEY='{model_api_key}' && "
                f"export OPENROUTER_API_KEY='{model_api_key}' && "
                f"export MODEL_API_KEY='{model_api_key}' && "
            )
        # Ensure HTTP OpenAI-compatible endpoints are available for curl-mode.
        enable_http = ''
        if _use_softcoding_init():
            enable_http = (
                "python3 - <<'PY'\n"
                "import json, os\n"
                "p=os.path.expanduser('~/.openclaw/openclaw.json')\n"
                "cfg={}\n"
                "try:\n"
                "  cfg=json.loads(open(p,'r',encoding='utf-8').read())\n"
                "except Exception:\n"
                "  cfg={}\n"
                "gw=cfg.setdefault('gateway',{})\n"
                "http=gw.setdefault('http',{})\n"
                "eps=http.setdefault('endpoints',{})\n"
                "cc=eps.setdefault('chatCompletions',{})\n"
                "cc['enabled']=True\n"
                "open(p,'w',encoding='utf-8').write(json.dumps(cfg,indent=2)+\"\\n\")\n"
                "print('[run-container] enabled gateway.http.endpoints.chatCompletions')\n"
                "PY\n"
            )
        gw_port_arg = f" --port {int(gw_port)}" if gw_port is not None else ""
        gw_token_env = f"export OPENCLAW_GATEWAY_TOKEN='{gw_token}' && "
        gw_token_arg = " --token \"$OPENCLAW_GATEWAY_TOKEN\" --allow-unconfigured" if _use_softcoding_init() else ""
        gateway_proc = container_exec_background(
            task_id,
            f'{gw_env_prefix}{enable_http}{gw_token_env}openclaw gateway{gw_port_arg}{gw_token_arg}',
            log_path=run_dir / 'gateway.log',
        )
        time.sleep(4)  # wait for gateway to be ready

        # 4. Run agent inside container (connects to its own gateway).
        emit_progress(format_progress(case_id, 'container-agent', index=run_idx, total=run_total))
        if _use_softcoding_init():
            # Curl-mode: use OpenAI-compatible HTTP API rather than openclaw agent CLI.
            # Pin session key so the session JSONL lands at the same path as CLI mode.
            gwp = int(gw_port or 20000)
            safe_prompt = prompt.replace("'", "'\\''")
            tok_q = shlex.quote(gw_token)
            agent_proc = container_exec_background(
                task_id,
                (
                    f"export OPENCLAW_GATEWAY_TOKEN={tok_q} && "
                    "set -euo pipefail; "
                    "req=/run_dir/openclaw_request.json; resp=/run_dir/openclaw_response.json; "
                    "python3 - <<'PY'\n"
                    "import json\n"
                    f"prompt={safe_prompt!r}\n"
                    "payload={\n"
                    "  'model':'openclaw/default',\n"
                    "  'messages':[{'role':'user','content':prompt}],\n"
                    "  'max_tokens':256\n"
                    "}\n"
                    "open('/run_dir/openclaw_request.json','w',encoding='utf-8').write(json.dumps(payload,ensure_ascii=False,indent=2)+'\\n')\n"
                    "PY\n"
                    f"curl -sS --max-time {timeout_sec} "
                    f"\"http://127.0.0.1:{gwp}/v1/chat/completions\" "
                    "-H \"Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN\" "
                    "-H \"Content-Type: application/json\" "
                    f"-H \"x-openclaw-session-key: {CONTAINER_AGENT_SESSION}\" "
                    "-d @\"$req\" > \"$resp\"; "
                    "python3 - <<'PY'\n"
                    "import json\n"
                    "p='/run_dir/openclaw_response.json'\n"
                    "try:\n"
                    "  obj=json.loads(open(p,'r',encoding='utf-8').read())\n"
                    "except Exception:\n"
                    "  obj={}\n"
                    "txt=''\n"
                    "choices=obj.get('choices')\n"
                    "if isinstance(choices,list) and choices:\n"
                    "  msg=choices[0].get('message') or {}\n"
                    "  c=msg.get('content','')\n"
                    "  if isinstance(c,str):\n"
                    "    txt=c\n"
                    "open('/run_dir/assistant.txt','w',encoding='utf-8').write(txt)\n"
                    "PY\n"
                ),
                log_path=run_dir / 'agent.log',
            )
        else:
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
        if _use_softcoding_init() and gw_port is not None and softcoding_port_pool is not None:
            softcoding_port_pool.put(int(gw_port))

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


def _llm_params_from_local_env(local_env: dict[str, Any]) -> dict[str, str]:
    """Read ``temperature`` / ``topP`` / ``maxTokens`` from environment.json.

    Preferred: a ``params`` object (same shape as openclaw ``agents.defaults.models[primary].params``).
    Legacy: root-level ``temperature`` (and optional ``topP``, ``maxTokens``) for older configs.
    """
    keys = ('temperature', 'topP', 'maxTokens')
    merged: dict[str, str] = {}
    params_block = local_env.get('params')
    if isinstance(params_block, dict):
        for k in keys:
            v = params_block.get(k)
            if v is not None and str(v).strip() != '':
                merged[k] = str(v).strip()
    for k in keys:
        if k in merged:
            continue
        v = local_env.get(k)
        if v is not None and str(v).strip() != '':
            merged[k] = str(v).strip()
    return merged


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
    llm_params = _llm_params_from_local_env(local_env)
    return {
        'image': image,
        'model': model,
        'parallel': parallel,
        'model_api_key': model_api_key,
        'llm_params': llm_params,
    }


_PER_CASE_MODEL_TSV_FIELDNAMES: tuple[str, ...] = (
    'model',
    'written_at_utc',
    'pass_trials',
    'sample_k',
    'pass_metric',
    'pass_score_threshold',
    'c_success',
    'n_trials',
    'pass_at_k_hypergeom',
    'pass_pow_k_hypergeom',
    'discrete_pass_at_k',
    'discrete_pass_pow_k',
    'discrete_pass_all_k',
    'mean_task_success_rate',
    'mean_safety_success_rate',
    'mean_score',
    'task_progress',
    'tok_in_sum',
    'tok_out_sum',
    'cache_read_sum',
    'cache_write_sum',
    'tok_total_sum',
    'mean_http_duration_sec',
    'mean_execute_duration_sec',
    'trace_steps_sum',
    'last_trial_run_dir',
    'batch_summary_json',
)


def _discrete_pass_pow_k_case_rate(pm: dict[str, Any]) -> float | None:
    """Fraction of cases with c_success >= sample_k (discrete counterpart to pass^k)."""
    pcs = pm.get('per_case') or []
    try:
        sk = int(pm.get('sample_k') or 0)
    except (TypeError, ValueError):
        sk = 0
    if not pcs or sk < 1:
        return None
    ok = sum(1 for pc in pcs if int(pc.get('c_success') or 0) >= sk)
    return round(ok / len(pcs), 6)


def _fmt_cell(v: Any, *, nd: int = 6) -> str:
    if v is None:
        return ''
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        s = f'{v:.{nd}f}'.rstrip('0').rstrip('.')
        return s if s not in ('-0', '') else '0'
    return str(v)


def _write_per_case_model_comparison_tsv(
    *,
    runs_date_dir: Path,
    repo_root: Path,
    model: str | None,
    pass_trials: int,
    pass_metric: str,
    pass_score_threshold: float,
    sample_k: int | None,
    pm_doc: dict[str, Any] | None,
    case_run_paths: dict[str, list[Path]],
    summary_path: Path | None,
    emit_progress: Any,
) -> None:
    """Append/update one row per model under each case dir for cross-model comparison tables."""
    from .tools import (  # noqa: PLC0415
        collect_trial_run_metrics,
        load_score_json,
        mean_reasoning_progress_ratio_from_score_dicts,
        trial_satisfies_metric,
    )

    model_key = (model or '').strip() or 'unknown'
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    summary_cell = ''
    if summary_path is not None:
        try:
            summary_cell = str(summary_path.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            summary_cell = str(summary_path.resolve())

    def _row_from_per_case(pc: dict[str, Any], paths: list[Path]) -> dict[str, str]:
        rates = pc.get('outcome_rates') or {}
        agg = pc.get('aggregates') or {}
        tu = agg.get('token_usage_sum') or {}
        last_dir = str(paths[-1].resolve()) if paths else ''
        c_succ = int(pc.get('c_success') or 0)
        try:
            sk_pc = int(pc.get('sample_k') or 0)
        except (TypeError, ValueError):
            sk_pc = 0
        disc_pow = sk_pc > 0 and c_succ >= sk_pc
        return {
            'model': model_key,
            'written_at_utc': ts,
            'pass_trials': str(pass_trials),
            'sample_k': '' if sample_k is None else str(sample_k),
            'pass_metric': pass_metric,
            'pass_score_threshold': _fmt_cell(pass_score_threshold, nd=4),
            'c_success': str(c_succ),
            'n_trials': str(int(pc.get('n_trials') or 0)),
            'pass_at_k_hypergeom': _fmt_cell(pc.get('pass_at_k_hypergeom'), nd=8),
            'pass_pow_k_hypergeom': _fmt_cell(pc.get('pass_pow_k_hypergeom'), nd=8),
            'discrete_pass_at_k': _fmt_cell(bool(pc.get('pass_at_k'))),
            'discrete_pass_pow_k': _fmt_cell(disc_pow),
            'discrete_pass_all_k': _fmt_cell(bool(pc.get('pass_all_k'))),
            'mean_task_success_rate': _fmt_cell(rates.get('mean_task_success_rate'), nd=6),
            'mean_safety_success_rate': _fmt_cell(rates.get('mean_safety_success_rate'), nd=6),
            'mean_score': _fmt_cell(rates.get('mean_score'), nd=6),
            'task_progress': _fmt_cell(rates.get('task_progress'), nd=6),
            'tok_in_sum': str(int(tu.get('input', 0) or 0)),
            'tok_out_sum': str(int(tu.get('output', 0) or 0)),
            'cache_read_sum': str(int(tu.get('cache_read', 0) or 0)),
            'cache_write_sum': str(int(tu.get('cache_write', 0) or 0)),
            'tok_total_sum': str(int(tu.get('total', 0) or 0)),
            'mean_http_duration_sec': _fmt_cell(agg.get('mean_http_duration_sec'), nd=6),
            'mean_execute_duration_sec': _fmt_cell(agg.get('mean_execute_duration_sec'), nd=6),
            'trace_steps_sum': str(int(agg.get('trace_step_count_sum') or 0)),
            'last_trial_run_dir': last_dir,
            'batch_summary_json': summary_cell,
        }

    def _row_fallback(_case_id: str, paths: list[Path]) -> dict[str, str]:
        n = len(paths)
        c_ok = 0
        tok_in = tok_out = cread = cwr = ttot = 0
        steps = 0
        https: list[float] = []
        execs: list[float] = []
        scores: list[float] = []
        score_dicts_for_prog: list[dict[str, Any]] = []
        tasks = 0
        safes = 0
        scored = 0
        last_dir = ''
        for rd in paths:
            if not rd.is_dir():
                continue
            last_dir = str(rd.resolve())
            sc = load_score_json(rd)
            m = collect_trial_run_metrics(rd)
            tu = m.get('token_usage') or {}
            tok_in += int(tu.get('input', 0) or 0)
            tok_out += int(tu.get('output', 0) or 0)
            cread += int(tu.get('cache_read', 0) or 0)
            cwr += int(tu.get('cache_write', 0) or 0)
            ttot += int(tu.get('total', 0) or 0)
            steps += int(m.get('trace_step_count') or 0)
            if m.get('http_duration_sec') is not None:
                https.append(float(m['http_duration_sec']))
            if m.get('execute_duration_sec') is not None:
                execs.append(float(m['execute_duration_sec']))
            if sc is not None:
                scored += 1
                score_dicts_for_prog.append(sc)
                if trial_satisfies_metric(sc, pass_metric, pass_score_threshold):
                    c_ok += 1
                if sc.get('task_success'):
                    tasks += 1
                if sc.get('safety_success'):
                    safes += 1
                try:
                    scores.append(float(sc.get('score', 0) or 0))
                except (TypeError, ValueError):
                    pass
        mean_sc = sum(scores) / len(scores) if scores else None
        mt = tasks / scored if scored else None
        ms = safes / scored if scored else None
        rp = mean_reasoning_progress_ratio_from_score_dicts(score_dicts_for_prog)
        prog = rp if rp is not None else (mean_sc if mean_sc is not None else mt)
        m_http = round(sum(https) / len(https), 6) if https else None
        m_ex = round(sum(execs) / len(execs), 6) if execs else None
        sk_eff = int(sample_k) if sample_k is not None else n
        disc_pow = n > 0 and sk_eff > 0 and c_ok >= sk_eff
        return {
            'model': model_key,
            'written_at_utc': ts,
            'pass_trials': str(pass_trials),
            'sample_k': '' if sample_k is None else str(sample_k),
            'pass_metric': pass_metric,
            'pass_score_threshold': _fmt_cell(pass_score_threshold, nd=4),
            'c_success': str(c_ok),
            'n_trials': str(n),
            'pass_at_k_hypergeom': '',
            'pass_pow_k_hypergeom': '',
            'discrete_pass_at_k': _fmt_cell(c_ok >= 1) if n else '',
            'discrete_pass_pow_k': _fmt_cell(disc_pow) if n else '',
            'discrete_pass_all_k': _fmt_cell(c_ok == n) if n else '',
            'mean_task_success_rate': _fmt_cell(mt, nd=6),
            'mean_safety_success_rate': _fmt_cell(ms, nd=6),
            'mean_score': _fmt_cell(mean_sc, nd=6) if mean_sc is not None else '',
            'task_progress': _fmt_cell(prog, nd=6) if prog is not None else '',
            'tok_in_sum': str(tok_in),
            'tok_out_sum': str(tok_out),
            'cache_read_sum': str(cread),
            'cache_write_sum': str(cwr),
            'tok_total_sum': str(ttot),
            'mean_http_duration_sec': _fmt_cell(m_http, nd=6),
            'mean_execute_duration_sec': _fmt_cell(m_ex, nd=6),
            'trace_steps_sum': str(steps),
            'last_trial_run_dir': last_dir,
            'batch_summary_json': summary_cell,
        }

    per_by_id: dict[str, dict[str, Any]] = {}
    if pm_doc:
        for pc in pm_doc.get('per_case') or []:
            cid = str(pc.get('case_id') or '').strip()
            if cid:
                per_by_id[cid] = pc

    for case_id, paths in sorted(case_run_paths.items(), key=lambda x: x[0]):
        case_dir = runs_date_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        out_path = case_dir / 'run_container_models.tsv'
        rows_by_model: dict[str, dict[str, str]] = {}
        if out_path.is_file():
            with out_path.open(newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for r in reader:
                    if not r:
                        continue
                    mk = (r.get('model') or '').strip()
                    if mk:
                        rows_by_model[mk] = {k: (r.get(k) or '') for k in _PER_CASE_MODEL_TSV_FIELDNAMES}

        pc = per_by_id.get(case_id)
        if pc is not None:
            new_row = _row_from_per_case(pc, paths)
        else:
            new_row = _row_fallback(case_id, paths)
        rows_by_model[model_key] = new_row

        with out_path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=_PER_CASE_MODEL_TSV_FIELDNAMES, delimiter='\t', extrasaction='ignore')
            writer.writeheader()
            for mk in sorted(rows_by_model):
                writer.writerow({k: rows_by_model[mk].get(k, '') for k in _PER_CASE_MODEL_TSV_FIELDNAMES})
    emit_progress(
        f'[run-container] per-case model tables: {len(case_run_paths)} × run_container_models.tsv '
        f'under {runs_date_dir}/<case_id>/'
    )


def run_container_command(args: Any) -> int:
    """CLI handler for the ``run-container`` subcommand."""
    from .run_episode import (  # noqa: PLC0415
        REPO_ROOT,
        RUNS_ROOT,
        category_for_case_dir,
        materialize_run,
        resolve_run_case_dirs,
    )
    from .tools import (  # noqa: PLC0415
        build_pass_metrics_document,
        emit_progress,
        format_batch_rollup_text,
        format_progress,
        load_case_config,
        resolve_cases_root,
        resolve_summary_outpath,
        summarize_batch_results,
        write_summary_file,
    )

    case_dirs = resolve_run_case_dirs(args)
    cases_root = resolve_cases_root(REPO_ROOT, getattr(args, 'cases_root', None))
    local_env = load_local_environment()
    ctr = _resolve_container_args(args, local_env)
    run_date = args.run_date
    total = len(case_dirs)
    softcoding_port_pool: queue.Queue[int] | None = None
    if _use_softcoding_init():
        # When using the softcoding image + curl-mode HTTP path, reserve a small predictable
        # port pool so parallel workers do not fight over local gateway ports.
        # Port selection rule: [20000, 20000+parallel-1], and a freed port is returned to the pool.
        softcoding_port_pool = queue.Queue()
        base = 20000
        for p in range(base, base + int(ctr['parallel'])):
            softcoding_port_pool.put(p)

    emit_progress(
        f'run-container: {total} case(s), image={ctr["image"]}, '
        f'model={ctr["model"] or "openclaw:main"}, parallel={ctr["parallel"]}'
    )

    results: list[dict[str, Any]] = []
    batch_started = time.time()
    overall_exit = 0
    pass_trials = max(1, int(getattr(args, 'pass_trials', 1) or 1))

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
        cfg = load_case_config(case_dir)
        case_id_key = str(cfg['case_id'])
        emit_progress(format_progress(case_id_key, 'prepare', index=idx, total=total))
        trial_paths: list[Path] = []
        trial_results: list[dict[str, Any]] = []
        if pass_trials > 1:
            # Name trials so different --run-name batches do not reuse run1..runN (e.g. model matrix on same date).
            batch_tag = getattr(args, 'run_name', None)
            for tr in range(1, pass_trials + 1):
                slot = f'{batch_tag}_run{tr}' if batch_tag else f'run{tr}'
                _cc, run_dir = materialize_run(case_dir, run_date, slot)
                result = container_run_case(
                    case_dir, run_dir,
                    image=ctr['image'],
                    model=ctr['model'],
                    model_api_key=ctr.get('model_api_key', ''),
                    llm_params=ctr.get('llm_params'),
                    run_idx=idx,
                    run_total=total,
                    softcoding_port_pool=softcoding_port_pool,
                )
                trial_paths.append(Path(result['run_dir']))
                trial_results.append(result)
        else:
            _cc, run_dir = materialize_run(case_dir, run_date, getattr(args, 'run_name', None))
            result = container_run_case(
                case_dir, run_dir,
                image=ctr['image'],
                model=ctr['model'],
                model_api_key=ctr.get('model_api_key', ''),
                llm_params=ctr.get('llm_params'),
                run_idx=idx,
                run_total=total,
                softcoding_port_pool=softcoding_port_pool,
            )
            trial_paths.append(Path(result['run_dir']))
            trial_results.append(result)
        for r in trial_results:
            r['category'] = category_for_case_dir(case_dir, cases_root)
            r['case_dir'] = str(case_dir.resolve())
        last = trial_results[-1]
        emit_progress(
            format_progress(
                str(last.get('case_id', case_id_key)),
                f'complete ({len(trial_results)} trial(s); last score={last.get("score")})',
                index=idx,
                total=total,
            )
        )
        return {'case_id': case_id_key, 'trial_paths': trial_paths, 'trial_results': trial_results}

    indexed = list(enumerate(case_dirs, start=1))
    blobs: list[dict[str, Any]] = []
    if ctr['parallel'] == 1:
        blobs = [_run_one(ic) for ic in indexed]
    else:
        with ThreadPoolExecutor(max_workers=ctr['parallel']) as pool:
            futures = {pool.submit(_run_one, ic): ic for ic in indexed}
            for fut in as_completed(futures):
                blobs.append(fut.result())

    case_run_paths: dict[str, list[Path]] = {}
    for b in blobs:
        case_run_paths[b['case_id']] = b['trial_paths']
        results.extend(b['trial_results'])

    batch_elapsed = round(time.time() - batch_started, 3)

    # ── Per-case table ─────────────────────────────────────────────────────────
    col_w = max(len(r.get('case_id', '')) for r in results)
    header = (
        f"{'case':<{col_w}}  task    safety  score   tok_in  tok_out  c_read  c_wr  secs"
    )
    print(header)
    print('-' * len(header))
    for r in results:
        tu = r.get('token_usage') or {}
        if 'error' in r:
            print(f"{r.get('case_id', '?'):<{col_w}}  ERROR: {r['error']}")
        else:
            task   = '✓' if r.get('task_success')   else '✗'
            safety = '✓' if r.get('safety_success')  else '✗'
            print(
                f"{r['case_id']:<{col_w}}  {task:<6}  {safety:<6}  "
                f"{r.get('score', 0.0):.1f}    "
                f"{tu.get('input', 0):>6}  {tu.get('output', 0):>7}  "
                f"{tu.get('cache_read', 0):>6}  {tu.get('cache_write', 0):>4}  "
                f"{r.get('execute_duration_sec', 0):.1f}s"
            )

    # ── Batch summary (by category + overall) ──────────────────────────────────
    rollups = summarize_batch_results(results)

    pm_doc: dict[str, Any] | None = None
    try:
        pm_doc = build_pass_metrics_document(
            run_date=str(run_date),
            runs_partition=RUNS_ROOT / str(run_date),
            case_run_paths=case_run_paths,
            metric=str(getattr(args, 'pass_metric', 'full')),
            score_threshold=float(getattr(args, 'pass_score_threshold', 1.0)),
            sample_k=getattr(args, 'pass_sample_k', None),
            model_label=str(ctr['model']).strip() if ctr.get('model') else None,
            source='run_container',
        )
    except ValueError as exc:
        emit_progress(f'[run-container] pass metrics skipped: {exc}')

    batch_doc: dict[str, Any] = {
        'mode': 'run_container',
        'run_date': run_date,
        'cases_root': str(cases_root),
        'container_image': ctr['image'],
        'model': ctr['model'],
        'parallel': ctr['parallel'],
        'pass_trials': pass_trials,
        'wall_clock_sec': batch_elapsed,
        'batch_rollup': rollups,
        'results': results,
    }
    if pm_doc is not None:
        batch_doc['pass_metrics'] = pm_doc
        roll = pm_doc.get('rollup') or {}
        tok = roll.get('total_token_usage') or {}
        disc_pow_k_rate = _discrete_pass_pow_k_case_rate(pm_doc)
        batch_doc['summary_table_row'] = {
            'model': ctr.get('model'),
            'run_date': str(run_date),
            'pass_trials': pass_trials,
            'sample_k': pm_doc.get('sample_k'),
            'pass_at_k': roll.get('mean_pass_at_k_hypergeom'),
            'pass_pow_k': roll.get('mean_pass_pow_k_hypergeom'),
            'hypergeom_mean_pass_at_k': roll.get('mean_pass_at_k_hypergeom'),
            'hypergeom_mean_pass_pow_k': roll.get('mean_pass_pow_k_hypergeom'),
            'discrete_pass_at_k_case_rate': pm_doc.get('pass_at_k_rate'),
            'discrete_pass_pow_k_case_rate': disc_pow_k_rate,
            'discrete_pass_all_n_case_rate': pm_doc.get('pass_all_k_rate'),
            'token_input': int(tok.get('input', 0) or 0),
            'token_output': int(tok.get('output', 0) or 0),
            'token_cache_read': int(tok.get('cache_read', 0) or 0),
            'token_cache_write': int(tok.get('cache_write', 0) or 0),
            'token_total': int(tok.get('total', 0) or 0),
            'mean_http_duration_sec': roll.get('mean_http_duration_sec'),
            'mean_execute_duration_sec': roll.get('mean_execute_duration_sec'),
            'mean_task_progress': roll.get('mean_task_progress'),
            'trials_with_http_latency': int(roll.get('trials_with_http_latency', 0) or 0),
            'trials_with_execute_duration': int(roll.get('trials_with_execute_duration', 0) or 0),
            'total_trace_steps': int(roll.get('total_trace_steps', 0) or 0),
        }

    pass_doc_path = getattr(args, 'pass_doc', None)
    no_pass_doc = bool(getattr(args, 'no_pass_doc', False))
    if pm_doc and int(pm_doc.get('case_count') or 0) > 0:
        write_pass_md = False
        target: Path | None = None
        if pass_doc_path:
            target = Path(str(pass_doc_path)).expanduser().resolve()
            write_pass_md = True
        elif pass_trials > 1 and not no_pass_doc:
            ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            target = (RUNS_ROOT / str(run_date) / f'pass_metrics_run_container_{ts}.md').resolve()
            write_pass_md = True
        if write_pass_md and target is not None:
            written_pass = write_summary_file(target, pm_doc)
            emit_progress(f'Wrote pass metrics document: {written_pass}')
    summary_path = resolve_summary_outpath(
        args,
        run_date=str(run_date),
        mode_label='run-container',
        case_count=total,
        runs_root=RUNS_ROOT,
    )
    written_summary_path: Path | None = None
    if summary_path:
        written_summary_path = write_summary_file(summary_path, batch_doc)
        emit_progress(f'Wrote summary: {written_summary_path}')

    sample_k_val: int | None = None
    if pm_doc is not None and pm_doc.get('sample_k') is not None:
        sample_k_val = int(pm_doc['sample_k'])
    else:
        raw_sk = getattr(args, 'pass_sample_k', None)
        if raw_sk is not None:
            sample_k_val = int(raw_sk)

    if case_run_paths:
        _write_per_case_model_comparison_tsv(
            runs_date_dir=RUNS_ROOT / str(run_date),
            repo_root=REPO_ROOT,
            model=ctr.get('model'),
            pass_trials=pass_trials,
            pass_metric=str(getattr(args, 'pass_metric', 'full')),
            pass_score_threshold=float(getattr(args, 'pass_score_threshold', 1.0)),
            sample_k=sample_k_val,
            pm_doc=pm_doc,
            case_run_paths=case_run_paths,
            summary_path=written_summary_path,
            emit_progress=emit_progress,
        )

    print()
    print(f"image={ctr['image']}  model={ctr['model'] or 'openclaw:main'}  wall_clock_sec={batch_elapsed}")
    print(format_batch_rollup_text(rollups))
    if pm_doc and pm_doc.get('rollup'):
        pr = pm_doc['rollup']
        m1 = pr.get('mean_pass_at_k_hypergeom')
        m2 = pr.get('mean_pass_pow_k_hypergeom')
        m1s = f'{m1:.4f}' if m1 is not None else '—'
        m2s = f'{m2:.4f}' if m2 is not None else '—'
        print(
            f'pass_metrics (hypergeom, mean over cases): pass@k={m1s}  pass^k={m2s}  '
            f'(pass_trials={pass_trials}, sample_k={pm_doc.get("sample_k")})'
        )

    errors = rollups['overall']['error_count']
    if errors:
        overall_exit = 1
    return overall_exit
