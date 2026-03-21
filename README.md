## Run

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

```bash
python3 runner/run_episode.py run   --case-dir cases/project_state_standup_001   --run-date xxxx-xx-xx   --run-name runN
```

Then score it:

```bash
python3 runner/run_episode.py score   --run-dir runs/xxxx-xx-xx/project_state_standup_001/runN
```

### Two-step run

Prepare a run.
```bash
python3 runner/run_episode.py prepare   --case-dir cases/project_state_standup_001   --run-date xxxx-xx-xx   --run-name runN
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

1. Create a new directory under `cases/`
2. Define the case in `case.yaml`. It tells the runner where to find the prompt and initial workspace, and tells the oracle which evaluator to use.
3. Write `prompt.txt`.
4. Build initial workspace.
5. Add check files under `checks/`. The `checks/` directory contains the data used by the oracle to evaluate the result.
6. Add an evaluator to `oracle.py`.
