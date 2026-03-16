Open sandbox in config.

python3 runner/run_episode.py prepare \
  --case-dir cases/caseN \
  --run-date  xxxx-xx-xx\
  --run-name runN

Copy the workspace_dir to the config.

OPENCLAW_BENCH_TOKEN='xxxxxxx' \
python3 runner/run_episode.py execute \
  --run-dir runs/xxxx-xx-xx/case_name/runN \
  --base-url http://127.0.0.1:xxxxx \
  --model openclaw:main \
  --agent-id main
