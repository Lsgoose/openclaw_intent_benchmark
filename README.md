# Agent Risk Benchmark (Reference Runner)

This repository contains a lightweight benchmark runner for OpenClaw-oriented risk cases.

Core capabilities:

- case discovery by id/category/path/all
- one-step run (`prepare + execute + score`) or staged workflow
- batch execution with safety guard for shared OpenClaw workspace config
- local oracle scoring per case

## Install

```bash
pip install -e .
```

## Project Layout

```text
agent-risk-benchmark/
  cases/
  doc/
  runs/
  src/
    agent_risk_benchmark/
      runner/
        run_episode.py
    runner/  # compatibility shim
      run_episode.py
  pyproject.toml
  README.md
```

`agent-risk-benchmark` CLI entrypoint points to `agent_risk_benchmark.runner.run_episode:main`.

Legacy module path `runner.run_episode` remains available as a compatibility shim.

## Configuration

Use CLI args and environment variables.

Recommended options:

- CLI args:
  - `--openclaw-home`
  - `--openclaw-config`
  - `--base-url`
  - `--bearer-token`
  - `--agent-id`
- Environment variables:
  - `OPENCLAW_HOME`
  - `OPENCLAW_CONFIG`
  - `OPENCLAW_BASE_URL`
  - `OPENCLAW_BEARER_TOKEN` (or `OPENCLAW_BENCH_TOKEN`)
  - `OPENCLAW_AGENT_ID`

Resolution order (high to low):

1. explicit CLI args
2. environment variables
3. built-in defaults

## Usage

### prequisites
Since we integrate with OpenClaw through its exposed OpenAI-compatible Chat Completions endpoint, please first refer to [openai-http-api](https://docs.openclaw.ai/zh-CN/gateway/openai-http-api) to enable the HTTP API functionality of OpenClaw.

### Start Gateway
```bash
# Start gateway
OPENCLAW_GATEWAY_TOKEN="your_token_here"
openclaw gateway --port 18789
```

### One-step run

Full-parameter example (single command):

```bash
agent-risk-benchmark run \
  --all \
  --run-date 2026-04-03 \
  --run-name run1 \
  --openclaw-home ~/.openclaw \
  --openclaw-config ~/.openclaw/openclaw.json \
  --base-url http://127.0.0.1:18789 \
  --bearer-token "$OPENCLAW_GATEWAY_TOKEN" \
  --agent-id main \
  --model openclaw:main \
  --num-worker 1 \
  --openclaw-timeout 180
```

Full-parameter parallel example (only when each worker is fully isolated):

```bash
agent-risk-benchmark run \
  --all \
  --run-date 2026-04-03 \
  --openclaw-home ~/.openclaw \
  --openclaw-config ~/.openclaw/openclaw.json \
  --base-url http://127.0.0.1:18789 \
  --bearer-token "$OPENCLAW_GATEWAY_TOKEN" \
  --agent-id main \
  --model openclaw:main \
  --num-worker 4 \
  --allow-unsafe-parallel-openclaw \
  --openclaw-timeout 180
```

If your workers share OpenClaw config/workspace sync state, keep `--num-worker 1` and do not use `--allow-unsafe-parallel-openclaw`.

Run one case by case id:

```bash
agent-risk-benchmark run --case project_state_standup_001 --run-date 2026-04-03
```

Run multiple cases:

```bash
agent-risk-benchmark run --case project_state_standup_001 --case game_hotfix_review_001 --run-date 2026-04-03
```

Run by category:

```bash
agent-risk-benchmark run --category 02_content_creation_pipeline_agent --run-date 2026-04-03
```

Run all:

```bash
agent-risk-benchmark run --all --run-date 2026-04-03
```

Custom OpenClaw settings (example):

```bash
agent-risk-benchmark run \
  --all \
  --openclaw-home ~/.openclaw \
  --bearer-token "$OPENCLAW_GATEWAY_TOKEN" \
  --run-date 2026-04-03
```

### Step-by-step run

Full-parameter example (prepare + execute + score):

```bash
agent-risk-benchmark prepare \
  --case-dir cases/02_content_creation_pipeline_agent/project_state_standup_001 \
  --run-date 2026-04-03 \
  --run-name run1

agent-risk-benchmark execute \
  --run-dir runs/2026-04-03/project_state_standup_001/run1 \
  --openclaw-home ~/.openclaw \
  --openclaw-config ~/.openclaw/openclaw.json \
  --base-url http://127.0.0.1:18789 \
  --bearer-token "$OPENCLAW_GATEWAY_TOKEN" \
  --agent-id main \
  --model openclaw:main \
  --openclaw-timeout 180

agent-risk-benchmark score \
  --run-dir runs/2026-04-03/project_state_standup_001/run1
```

Prepare:

```bash
agent-risk-benchmark prepare \
  --case-dir cases/02_content_creation_pipeline_agent/project_state_standup_001 \
  --run-date 2026-04-03 \
  --run-name run1
```

Execute:

```bash
agent-risk-benchmark execute --run-dir runs/2026-04-03/project_state_standup_001/run1
```

Score:

```bash
agent-risk-benchmark score --run-dir runs/2026-04-03/project_state_standup_001/run1
```

## Parallel Execution Safety

If shared OpenClaw config/workspace sync is detected, the runner forces single-worker mode by default to avoid cross-case contamination.

You can explicitly bypass this protection only when you know each worker is isolated:

```bash
agent-risk-benchmark run --all --num-worker 4 --allow-unsafe-parallel-openclaw --run-date 2026-04-03
```

### Container-based run

Run cases inside isolated Docker containers (no host OpenClaw gateway required):

```bash
agent-risk-benchmark run-container \
  --case email_reply_meeting_full_explicit \
  --case email_reply_meeting_goal_ambiguity \
  --parallel 7 \
  --image openclaw-bench:v1.0 \
  --model openrouter/anthropic/claude-sonnet-4-5
```

Run an entire category in parallel:

```bash
agent-risk-benchmark run-container \
  --category 04_personal_ai_second_brain_agent \
  --parallel 4 \
  --image openclaw-bench:v1.0
```

Run all cases:

```bash
agent-risk-benchmark run-container \
  --all \
  --parallel 4
```

Key options:

| Option | Default | Description |
|---|---|---|
| `--image` | `environment.json` → `openclaw-bench:v1.0` | Docker image name |
| `--model` | `openclaw:main` | OpenClaw model string |
| `--parallel` | `1` | Number of containers to run simultaneously |
| `--run-date` | today | Date partition for the run directory |

Each container runs its own isolated OpenClaw gateway internally, so parallel execution is always safe.

## Case Template

Use a `*_template.md` file + `scripts/parse_template.py` to generate a full 7-case ablation set from a single template file.

Each template expands into 7 case directories following the **3-Dimension × 3-State Ablation Matrix**:

| Suffix | Goal | Action | Tool |
|---|---|---|---|
| `_full_explicit` | clear | clear | clear |
| `_goal_ambiguity` | ambiguous | clear | clear |
| `_goal_miss` | absent | clear | clear |
| `_action_ambiguity` | clear | ambiguous | clear |
| `_action_miss` | clear | absent | clear |
| `_tool_ambiguity` | clear | clear | ambiguous |
| `_tool_miss` | clear | clear | absent |

### Usage

```bash
# Expand template → writes 7 case dirs to cases/{category}/
python scripts/parse_template.py path/to/my_template.md

# Preview without writing (dry-run)
python scripts/parse_template.py path/to/my_template.md --dry-run

# Write to a custom output directory
python scripts/parse_template.py path/to/my_template.md --output-dir cases/my_category/

# Overwrite existing directories
python scripts/parse_template.py path/to/my_template.md --force
```

### Example: expanding `kb_article_publish`

```bash
# Preview (no files written)
python scripts/parse_template.py \
  template/kb_article_publish_template.md \
  --dry-run

# Expand → writes 7 case dirs to cases/04_personal_ai_second_brain_agent/
python scripts/parse_template.py \
  template/kb_article_publish_template.md

# Re-expand after editing the template
python scripts/parse_template.py \
  template/kb_article_publish_template.md \
  --force
```

For the full authoring guide and an annotated walkthrough of the example template, see the GUIDE documents in `template/`.

## Add a New Case

Create under `cases/<category>/<case_id>/`:

```text
case.yaml
prompt.txt
note.md
oracle.py
workspace-exp/
checks/
```

`case.yaml` minimum fields:

- `case_id`
- `title`
- `description`
- `prompt_file`
- `workspace_source`
- `oracle.entry`

Shared oracle helpers are in [doc/oracle_common.md](doc/oracle_common.md).

## Development

Install dev dependencies:

```bash
pip install -e .[dev]
```

Common checks:

```bash
python -m black src/agent_risk_benchmark/runner src/runner
python -m ruff check src/agent_risk_benchmark/runner src/runner
python -m mypy src/agent_risk_benchmark/runner
python -m agent_risk_benchmark.runner.run_episode run --help
```

## Docs

- 中文文档: [README.zh-CN.md](README.zh-CN.md)
- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)



