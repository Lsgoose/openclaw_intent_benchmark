## Run

`cases/` is now grouped into five category folders:

- `cases/01_information_intelligence_agent`
- `cases/02_content_creation_pipeline_agent`
- `cases/03_platform_automation_agent`
- `cases/04_personal_ai_second_brain_agent`
- `cases/05_self_healing_devops_agent`

1. Open sandbox in config.

2. Create `environment.json` in the repo root.
```json
{
  "openclaw_home": "/home/ay/.openclaw-exp",
  "agent_id": "main"
}
```

### One-step run

Use `run` to do `prepare + execute` in one command.

Run one case by `case_id`:

```bash
python3 runner/run_episode.py run   --case project_state_standup_001   --run-date xxxx-xx-xx   --run-name runN
```

Run multiple specific cases:

```bash
python3 runner/run_episode.py run   --case project_state_standup_001   --case game_hotfix_review_001   --run-date xxxx-xx-xx
```

Run one category:

```bash
python3 runner/run_episode.py run   --category 02_content_creation_pipeline_agent   --run-date xxxx-xx-xx
```

Run all discovered cases:

```bash
python3 runner/run_episode.py run   --all   --run-date xxxx-xx-xx
```

You can still run an exact path with `--case-dir` if needed.

Then score a single run with:

```bash
python3 runner/run_episode.py score   --run-dir runs/xxxx-xx-xx/project_state_standup_001/runN
```

### Two-step run

Prepare a run.
```bash
python3 runner/run_episode.py prepare   --case-dir cases/02_content_creation_pipeline_agent/project_state_standup_001   --run-date xxxx-xx-xx   --run-name runN
```

Execute. The runner will automatically:
- update `~/.openclaw-exp/openclaw.json` workspace during `prepare`
- read the gateway token from that config
- copy the OpenClaw session trace back into `runs/...`

```bash
python3 runner/run_episode.py execute   --run-dir runs/xxxx-xx-xx/project_state_standup_001/runN
```

Score.
```bash
python3 runner/run_episode.py score   --run-dir runs/xxxx-xx-xx/project_state_standup_001/runN
```

## Add a new cases

1. Create a new directory under the appropriate category in `cases/`
2. Define the case in `case.yaml`. It tells the runner where to find the prompt and initial workspace, and tells the oracle which evaluator to use.
3. Write `prompt.txt`.
4. Build initial workspace.
5. Add check files under `checks/`. The `checks/` directory contains the data used by the oracle to evaluate the result.
6. Add `oracle.py` to the case directory. Import shared helpers from `oracle_common.py` only if needed.
