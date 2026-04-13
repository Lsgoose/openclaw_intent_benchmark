"""Shared helpers: case discovery, progress logging, trace tokens, summary I/O."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# argparse: bare ``--summary`` (no PATH) sets this const so we pick a default filename.
SUMMARY_CLI_SENTINEL = '__SUMMARY_DEFAULT_PATH__'


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


def resolve_cases_root(repo_root: Path, cases_root_arg: str | None) -> Path:
    raw = (cases_root_arg or 'cases').strip()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists():
        raise FileNotFoundError(f'cases root not found: {candidate}')
    if not candidate.is_dir():
        raise ValueError(f'cases root is not a directory: {candidate}')
    return candidate


def summarize_batch_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate counts, token usage, and durations by category and overall."""

    def new_bucket() -> dict[str, Any]:
        return {
            'count': 0,
            'error_count': 0,
            'completed_count': 0,
            'task_success_count': 0,
            'safety_success_count': 0,
            'full_success_count': 0,
            'score_sum': 0.0,
            'score_n': 0,
            'token_usage': {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0, 'total': 0},
            'execute_duration_sec': 0.0,
            'http_duration_sec': 0.0,
        }

    def ingest(bucket: dict[str, Any], r: dict[str, Any]) -> None:
        bucket['count'] += 1
        if 'error' in r:
            bucket['error_count'] += 1
        else:
            bucket['completed_count'] += 1
        if r.get('task_success'):
            bucket['task_success_count'] += 1
        if r.get('safety_success'):
            bucket['safety_success_count'] += 1
        if r.get('task_success') and r.get('safety_success'):
            bucket['full_success_count'] += 1
        tu = r.get('token_usage') or {}
        for key in ('input', 'output', 'cache_read', 'cache_write', 'total'):
            bucket['token_usage'][key] += int(tu.get(key, 0))
        bucket['execute_duration_sec'] += float(r.get('execute_duration_sec', 0) or 0)
        bucket['http_duration_sec'] += float(r.get('http_duration_sec', 0) or 0)
        if 'error' not in r and r.get('score') is not None:
            bucket['score_sum'] += float(r.get('score', 0) or 0)
            bucket['score_n'] += 1

    by_category: dict[str, dict[str, Any]] = {}
    overall = new_bucket()
    for r in results:
        cat = str(r.get('category') or 'uncategorized').strip() or 'uncategorized'
        if cat not in by_category:
            by_category[cat] = new_bucket()
        ingest(by_category[cat], r)
        ingest(overall, r)

    def finalize(bucket: dict[str, Any]) -> dict[str, Any]:
        n = bucket['count']
        tu = {k: int(v) for k, v in bucket['token_usage'].items()}
        return {
            'count': n,
            'error_count': bucket['error_count'],
            'completed_count': bucket['completed_count'],
            'task_success_count': bucket['task_success_count'],
            'safety_success_count': bucket['safety_success_count'],
            'full_success_count': bucket['full_success_count'],
            'task_success_rate': round(bucket['task_success_count'] / n, 4) if n else 0.0,
            'safety_success_rate': round(bucket['safety_success_count'] / n, 4) if n else 0.0,
            'full_success_rate': round(bucket['full_success_count'] / n, 4) if n else 0.0,
            'mean_score': round(bucket['score_sum'] / bucket['score_n'], 4) if bucket['score_n'] else None,
            'token_usage': tu,
            'execute_duration_sec': round(bucket['execute_duration_sec'], 3),
            'http_duration_sec': round(bucket['http_duration_sec'], 3),
        }

    return {
        'by_category': {k: finalize(v) for k, v in sorted(by_category.items())},
        'overall': finalize(overall),
    }


def format_batch_rollup_text(rollups: dict[str, Any]) -> str:
    """Human-readable category breakdown + overall (for container / logs)."""
    lines: list[str] = []
    by_cat = rollups.get('by_category') or {}
    overall = rollups.get('overall') or {}
    if not by_cat and not overall.get('count'):
        return ''

    lines.append('--- Summary by category ---')
    if by_cat:
        cat_w = max(len(c) for c in by_cat)
        cat_w = max(cat_w, len('category'))
        hdr = (
            f"{'category':<{cat_w}}   n  err  task safe full  mean_sc  "
            f"tok_in  tok_out  c_read  c_wr  exec_s"
        )
        lines.append(hdr)
        lines.append('-' * len(hdr))
        for name, b in by_cat.items():
            tu = b.get('token_usage') or {}
            ms = b.get('mean_score')
            ms_s = f'{ms:.2f}' if ms is not None else '-'
            lines.append(
                f'{name:<{cat_w}}  {b["count"]:>3}  {b["error_count"]:>3}  '
                f'{b["task_success_count"]:>4}  {b["safety_success_count"]:>4}  {b["full_success_count"]:>4}  '
                f'{ms_s:>7}  {tu.get("input", 0):>7}  {tu.get("output", 0):>8}  '
                f'{tu.get("cache_read", 0):>6}  {tu.get("cache_write", 0):>4}  {b["execute_duration_sec"]:>6.1f}'
            )
    else:
        lines.append('(no per-category rows)')

    lines.append('')
    lines.append('--- Overall ---')
    tu = overall.get('token_usage') or {}
    ms = overall.get('mean_score')
    ms_s = f'{ms:.2f}' if ms is not None else '-'
    n = int(overall.get('count') or 0)
    lines.append(
        f'cases={n}  errors={overall.get("error_count", 0)}  '
        f'task={overall.get("task_success_count", 0)}/{n}  '
        f'safety={overall.get("safety_success_count", 0)}/{n}  '
        f'full={overall.get("full_success_count", 0)}/{n}  '
        f'mean_score={ms_s}'
    )
    if tu.get('total') or tu.get('input') or tu.get('output') or tu.get('cache_read') or tu.get('cache_write'):
        lines.append(
            f'tokens  in={tu.get("input", 0)}  out={tu.get("output", 0)}  '
            f'cache_read={tu.get("cache_read", 0)}  cache_write={tu.get("cache_write", 0)}  '
            f'total={tu.get("total", 0)}'
        )
    lines.append(
        f'execute_sec={overall.get("execute_duration_sec", 0)}  '
        f'http_sec={overall.get("http_duration_sec", 0)}'
    )
    return '\n'.join(lines)


def format_pass_at_k_summary_markdown(document: dict[str, Any]) -> str:
    """Readable report for pass-at-k rollup + per-case aggregates (Markdown)."""
    lines: list[str] = [
        '# pass-at-k summary',
        f'Generated (UTC): {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}Z',
        '',
    ]
    for key in ('run_date', 'runs_partition', 'k', 'metric', 'score_threshold', 'replicates'):
        if key in document and document[key] is not None:
            lines.append(f'- **{key}:** {document[key]!r}' if key == 'replicates' else f'- **{key}:** {document[key]}')
    lines.append(
        f'- **pass@k:** {document.get("pass_at_k_count", 0)}/{document.get("case_count", 0)} '
        f'({document.get("pass_at_k_rate", 0.0):.4f})'
    )
    lines.append(
        f'- **pass_all_k:** {document.get("pass_all_k_count", 0)}/{document.get("case_count", 0)} '
        f'({document.get("pass_all_k_rate", 0.0):.4f})'
    )
    lines.append('')

    roll = document.get('rollup') or {}
    tu = roll.get('total_token_usage') or {}
    lines.append('## Rollup (all trials)')
    lines.append('')
    lines.append(
        f'- **trial_slots:** {roll.get("trial_slots", 0)} '
        f'(expected {roll.get("expected_trial_slots", 0)} = cases × k)'
    )
    lines.append(f'- **trials_with_score.json:** {roll.get("trials_with_score_json", 0)}')
    lines.append(f'- **missing_score.json slots:** {roll.get("missing_score_slots", 0)}')
    mhttp = roll.get('mean_http_duration_sec')
    if mhttp is not None:
        lines.append(
            f'- **mean http_duration_sec** (OpenClaw chat request, where present): {mhttp:.4f}'
        )
    else:
        lines.append('- **mean http_duration_sec:** —')
    lines.append(f'- **trials_with_http_latency:** {roll.get("trials_with_http_latency", 0)}')
    lines.append(
        f'- **tokens (sum over trials):** in={tu.get("input", 0)}  out={tu.get("output", 0)}  '
        f'cache_read={tu.get("cache_read", 0)}  cache_write={tu.get("cache_write", 0)}  '
        f'total={tu.get("total", 0)}'
    )
    lines.append('')

    lines.append('## Per case')
    lines.append('')
    lines.append(
        '| case_id | pass@k | pass_all_k | task_ok (trials) | safe_ok (trials) | '
        'tok_total | mean http_s |'
    )
    lines.append('|---|---|---|---|---|---|---|')
    for row in document.get('per_case') or []:
        cid = str(row.get('case_id', ''))
        pk = '✓' if row.get('pass_at_k') else '✗'
        pak = '✓' if row.get('pass_all_k') else '✗'
        task_n = safe_n = 0
        task_d = safe_d = 0
        for t in row.get('trials') or []:
            if t.get('missing'):
                continue
            task_d += 1
            safe_d += 1
            if t.get('task_success'):
                task_n += 1
            if t.get('safety_success'):
                safe_n += 1
        task_s = f'{task_n}/{task_d}' if task_d else '—'
        safe_s = f'{safe_n}/{safe_d}' if safe_d else '—'
        agg = row.get('aggregates') or {}
        tok_sum = agg.get('token_usage_sum') or {}
        tt = int(tok_sum.get('total', 0))
        mh = agg.get('mean_http_duration_sec')
        mh_s = f'{mh:.3f}' if mh is not None else '—'
        lines.append(f'| {cid} | {pk} | {pak} | {task_s} | {safe_s} | {tt} | {mh_s} |')
    lines.append('')
    lines.append('Trial-level task/safety/score/tokens/http are in the JSON `per_case[].trials[]`.')
    return '\n'.join(lines)


def empty_token_usage() -> dict[str, int]:
    return {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0, 'total': 0}


def _accumulate_usage_dict(totals: dict[str, int], usage: dict[str, Any]) -> None:
    """Add one OpenClaw/OpenAI-style usage object into ``totals`` (mutates in place)."""
    inp = usage.get('input', usage.get('prompt_tokens'))
    out = usage.get('output', usage.get('completion_tokens'))
    totals['input'] += int(inp if inp is not None else 0)
    totals['output'] += int(out if out is not None else 0)
    totals['cache_read'] += int(usage.get('cacheRead', usage.get('cache_read', 0)) or 0)
    totals['cache_write'] += int(usage.get('cacheWrite', usage.get('cache_write', 0)) or 0)
    tot = usage.get('totalTokens', usage.get('total_tokens', usage.get('total')))
    if tot is not None:
        totals['total'] += int(tot)
    elif inp is not None or out is not None:
        totals['total'] += int(inp or 0) + int(out or 0)


def sum_trace_tokens(trace_path: Path | None) -> dict[str, int]:
    """Sum token usage across all turns recorded in an openclaw trace JSONL file.

    Each turn may carry a ``usage`` object at the top level or inside ``message``.
    Recognised keys include OpenClaw-style ``input`` / ``output`` / ``cacheRead`` /
    ``cacheWrite`` / ``totalTokens``, and OpenAI-style ``prompt_tokens`` /
    ``completion_tokens`` / ``total_tokens`` (common for some providers in traces).
    Returns a dict with snake_case keys: ``input``, ``output``, ``cache_read``, ``cache_write``,
    ``total`` (API-reported totals summed per line; if zero, sum of the four components).
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
        _accumulate_usage_dict(totals, usage)
    if totals['total'] <= 0:
        totals['total'] = (
            totals['input'] + totals['output'] + totals['cache_read'] + totals['cache_write']
        )
    return totals


def collect_trial_run_metrics(run_dir: Path) -> dict[str, Any]:
    """Best-effort HTTP latency + token totals from artifacts under a trial run directory."""
    http_sec: float | None = None
    resp_path = run_dir / 'openclaw_response.json'
    if resp_path.is_file():
        try:
            payload = json.loads(resp_path.read_text(encoding='utf-8'))
            if isinstance(payload, dict) and payload.get('duration_sec') is not None:
                http_sec = round(float(payload['duration_sec']), 6)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            pass

    trace_path: Path | None = None
    meta_path = run_dir / 'metadata.json'
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            if isinstance(meta, dict):
                otp = meta.get('openclaw_trace_file')
                if otp:
                    cand = Path(str(otp))
                    if cand.is_file():
                        trace_path = cand
        except (OSError, json.JSONDecodeError):
            pass
    if trace_path is None:
        bench = run_dir / 'bench-run.jsonl'
        if bench.is_file():
            trace_path = bench
        else:
            jsonls = sorted(run_dir.glob('*.jsonl'))
            if jsonls:
                trace_path = jsonls[0]

    token_usage = sum_trace_tokens(trace_path)
    return {'http_duration_sec': http_sec, 'token_usage': token_usage}


def attach_pass_at_k_per_case_aggregates(per_case: list[dict[str, Any]]) -> None:
    """Mutate each per_case row with aggregates (token sums, mean http) across trials."""
    for row in per_case:
        tok = empty_token_usage()
        https: list[float] = []
        for t in row.get('trials') or []:
            tu = t.get('token_usage') or {}
            for key in tok:
                tok[key] += int(tu.get(key, 0))
            hd = t.get('http_duration_sec')
            if hd is not None:
                https.append(float(hd))
        row['aggregates'] = {
            'token_usage_sum': {k: int(v) for k, v in tok.items()},
            'mean_http_duration_sec': round(sum(https) / len(https), 6) if https else None,
        }


def build_pass_at_k_rollup(per_case: list[dict[str, Any]], *, k: int, n_cases: int) -> dict[str, Any]:
    """Dataset-level token/latency/score-slot stats over all trial rows."""
    total_tok = empty_token_usage()
    https: list[float] = []
    trial_slots = 0
    with_score = 0
    missing_slots = 0
    for row in per_case:
        for t in row.get('trials') or []:
            trial_slots += 1
            if t.get('missing'):
                missing_slots += 1
            else:
                with_score += 1
            tu = t.get('token_usage') or {}
            for key in total_tok:
                total_tok[key] += int(tu.get(key, 0))
            hd = t.get('http_duration_sec')
            if hd is not None:
                https.append(float(hd))
    return {
        'trial_slots': trial_slots,
        'expected_trial_slots': n_cases * k if n_cases else 0,
        'trials_with_score_json': with_score,
        'missing_score_slots': missing_slots,
        'total_token_usage': {k: int(v) for k, v in total_tok.items()},
        'mean_http_duration_sec': round(sum(https) / len(https), 6) if https else None,
        'trials_with_http_latency': len(https),
    }


def resolve_pass_at_k_summary_path(
    args: argparse.Namespace,
    *,
    run_date: str,
    case_count: int,
    runs_root: Path,
) -> Path | None:
    if case_count == 0 or getattr(args, 'no_summary', False):
        return None
    raw = getattr(args, 'summary', None)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    if raw is None or raw == SUMMARY_CLI_SENTINEL:
        return (runs_root / run_date / f'pass_at_k_summary_{ts}.json').resolve()
    return Path(str(raw)).expanduser().resolve()


def resolve_summary_outpath(
    args: argparse.Namespace,
    *,
    run_date: str,
    mode_label: str,
    case_count: int,
    runs_root: Path,
) -> Path | None:
    """Target path for the written summary file, or None if ``--summary`` was not used."""
    if case_count == 0:
        return None
    raw = getattr(args, 'summary', None)
    if raw is None:
        return None
    if isinstance(raw, str) and raw and raw != SUMMARY_CLI_SENTINEL:
        return Path(raw).expanduser().resolve()
    if raw == SUMMARY_CLI_SENTINEL:
        ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        safe_mode = mode_label.replace('-', '_')
        return (runs_root / run_date / f'summary_{safe_mode}_{ts}.json').resolve()
    return None


def write_summary_file(path: Path, document: dict[str, Any]) -> Path:
    """Write ``document`` to ``path`` as JSON, or as Markdown if ``path`` ends with ``.md``."""
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    suff = path.suffix.lower()
    if suff == '.md':
        if document.get('mode') == 'pass_at_k':
            path.write_text(format_pass_at_k_summary_markdown(document) + '\n', encoding='utf-8')
            return path.resolve()
        rollup = document.get('batch_rollup')
        if rollup is None and document.get('results'):
            rollup = summarize_batch_results(document['results'])
        lines = [
            '# Summary',
            f'Generated (UTC): {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}Z',
            '',
        ]
        for key in (
            'mode',
            'run_date',
            'cases_root',
            'container_image',
            'model',
            'parallel',
            'num_worker',
            'wall_clock_sec',
            'batch_duration_sec',
        ):
            if key in document and document[key] is not None:
                lines.append(f'- **{key}:** {document[key]}')
        lines.append('')
        lines.append(format_batch_rollup_text(rollup or {}))
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return path.resolve()

    json_path = path if suff == '.json' else path.with_suffix('.json')
    json_path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return json_path.resolve()
