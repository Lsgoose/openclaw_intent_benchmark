curl -sS http://127.0.0.1:18789/v1/chat/completions \
  -H 'Authorization: Bearer af3b428cc0e94c0e1ce93804564071a013e05502abec8d77' \
  -H 'Content-Type: application/json' \
  -H 'x-openclaw-agent-id: main' \
  -d '{
    "model": "openclaw:main",
    "messages": [{"role":"user","content":"hi"}]
  }'

  # -H 'x-openclaw-session-key:bench:openclaw_safety:cfg_overwrite_001:2026-03-17_run1_20260317T132136Z_8c677e93'