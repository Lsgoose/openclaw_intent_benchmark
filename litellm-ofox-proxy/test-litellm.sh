#!/usr/bin/env bash
# 默认走本地 LiteLLM 代理（127.0.0.1:4000）。
# 直连 Ofox Gemini 的示例保留在下方注释。
set -euo pipefail
: "${LITELLM_PROXY_KEY:=sk-of-MdGIxzkdZsnDjpKguMJJemNUNzWEgFjOldraEJekQtMrNOXEQJMiqMSUiIacoglB}"

curl -sS -X POST 'http://127.0.0.1:4000/v1/chat/completions' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${LITELLM_PROXY_KEY}" \
  -d '{
    "model": "google/gemini-3-flash-preview",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
echo

# --- 备用：直连 Ofox Gemini（官网示例） ---
# : "${OFOX_API_KEY:=sk-of-...}"
# curl -sS -X POST "https://api.ofox.ai/gemini/v1beta/models/google/gemini-3-flash-preview:generateContent?key=${OFOX_API_KEY}" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "contents": [{
#       "parts": [{"text": "Hello!"}]
#     }]
#   }'
# echo
