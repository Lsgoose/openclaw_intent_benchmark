## Install

Install the benchmark CLI into your current Python environment:

```bash
pip install -e .
```


## Run

### Prepare
1. Open sandbox in config.

2. Change `environment.json` in the root. For example
```json
{
  "openclaw_home": "/xxx/.openclaw-exp",
  "agent_id": "main"
}
```


### Run in one step
Run one case by `case_id`:

```bash
risk run   --case project_state_standup_001   --run-date xxxx-xx-xx   --run-name runN
```

Run multiple cases:

```bash
risk run   --case project_state_standup_001   --case game_hotfix_review_001   --run-date xxxx-xx-xx
```

Run by category:

```bash
risk run   --category 02_content_creation_pipeline_agent   --run-date xxxx-xx-xx
```

Run all cases:

```bash
risk run   --all   --run-date xxxx-xx-xx
```

You can still run an exact path with `--case-dir` if needed.



### Run step by step

Prepare a run.
```bash
risk prepare   --case-dir cases/02_content_creation_pipeline_agent/project_state_standup_001   --run-date xxxx-xx-xx   --run-name runN
```

Execute. The runner will automatically:

```bash
risk execute   --run-dir runs/xxxx-xx-xx/project_state_standup_001/runN
```

### Score

Score a single run with:

```bash
risk score   --run-dir runs/xxxx-xx-xx/project_state_standup_001/runN
```

## Add a new case

Create new cases under `cases/`

A new case should usually look like this:

```text
cases/<category>/<case_id>/
  case.yaml
  prompt.txt
  note.md
  oracle.py
  workspace-exp/
  checks/
```



### 1 Define `case.yaml`

`case.yaml` is the main configuration file for the case. It tells the runner where to find the prompt, the initial workspace, and the case-local oracle entry. At minimum it should define:

- `case_id`
- `title`
- `description`
- `prompt_file`
- `workspace_source`
- `oracle.entry`

Example:

```yaml
case_id: my_new_case_001
title: One-line title for the task
description: >
  Short description of the task and what can go wrong.
category: internal_to_external
prompt_file: prompt.txt
workspace_source: workspace-exp
oracle:
  entry: oracle.py
```


### 3. Write `prompt.txt`

`prompt.txt` is the task instruction sent to OpenClaw.

### 4. Build `workspace-exp/`

`workspace-exp/` is the initial workspace that gets copied into `runs/.../workspace` during `prepare`.


### 5. Add `checks/` files

Put oracle input files in `checks/`. Common examples are:

- `protected_paths.txt`
- `expected_hashes.json`
- `allowed_diff_roots.json`
- `protected_refs.json`
- `secret_patterns.json`



### 6. Implement `oracle.py`

Each case owns its own scoring logic in `oracle.py`.


oracle_common.py provides shared helpers such as `score_result()` and `load_checks_config()`. See [doc/oracle_common.md](doc/oracle_common.md).



