## Run

1. Open sandbox in config.

2. 
```
python3 runner/run_episode.py prepare \
  --case-dir cases/caseN \
  --run-date  xxxx-xx-xx\
  --run-name runN
```
3. Copy the workspace_dir to the config.

4. 
```
OPENCLAW_BENCH_TOKEN='xxxxxxx' \
python3 runner/run_episode.py execute \
  --run-dir runs/xxxx-xx-xx/case_name/runN \
  --base-url http://127.0.0.1:xxxxx \
  --model openclaw:main \
  --agent-id main
```

## Add a new cases

1. Create a new directory under `cases/`

2. Define the case in case.yaml. It tells the runner where to find the prompt and initial workspace, and tells the oracle which evaluator to use.

3. Write prompt.txt

4. Build inital workspace

5. Add check files under `checks/`. The `checks/` directory contains the data used by the oracle to evaluate the result.

6. Add an evaluator to `oracle.py`


