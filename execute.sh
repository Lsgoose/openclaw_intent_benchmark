python ./runner/run_episode.py \
    execute \
    --run-dir runs/2026-03-17/cfg_overwrite_001/run1 \
    --base-url http://127.0.0.1:18789 \
    --model openclaw:main \
    --agent-id main \
    --bearer-token af3b428cc0e94c0e1ce93804564071a013e05502abec8d77

python ./runner/run_episode.py \
    execute \
    --run-dir runs/2026-03-18/git_secret_commit_001/run5 \
    --base-url http://127.0.0.1:18789 \
    --model openclaw:main \
    --agent-id main \
    --bearer-token af3b428cc0e94c0e1ce93804564071a013e05502abec8d77

python ./runner/run_episode.py \
    execute \
    --run-dir /home/liyiting/agent/agent-risk-benchmark/runs/2026-03-18/bulk_delete_001/run6 \
    --base-url http://127.0.0.1:18789 \
    --model openclaw:main \
    --agent-id main \
    --bearer-token af3b428cc0e94c0e1ce93804564071a013e05502abec8d77

python ./runner/run_episode.py \
    execute \
    --run-dir /home/liyiting/agent/agent-risk-benchmark/runs/2026-03-18/indirect_injection_001/run7 \
    --base-url http://127.0.0.1:18789 \
    --model openclaw:main \
    --agent-id main \
    --bearer-token af3b428cc0e94c0e1ce93804564071a013e05502abec8d77

python ./runner/run_episode.py \
    execute \
    --run-dir runs/2026-03-18/dep_install_malicious_001/run8 \
    --base-url http://127.0.0.1:18789 \
    --model openclaw:main \
    --agent-id main \
    --bearer-token af3b428cc0e94c0e1ce93804564071a013e05502abec8d77