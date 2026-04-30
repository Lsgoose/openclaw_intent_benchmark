#!/usr/bin/env bash
# config.yaml 里 OpenAI 兼容路由用的是 os.environ/OFOX_V1_API_KEY，不是 OFOX_API_KEY。
set -euo pipefail
cd "$(dirname "$0")"

# : "${OFOX_V1_API_KEY:=${OFOX_API_KEY:-sk-of-yeHONkzKRHkUCiXAaOaeanQaWrOLuGikdbmGvLdANnahLMOaykSTgoAXCgbsVVbl}}"
: "${OFOX_V1_API_KEY:=${OFOX_API_KEY:-sk-of-MdGIxzkdZsnDjpKguMJJemNUNzWEgFjOldraEJekQtMrNOXEQJMiqMSUiIacoglB}}"



export OFOX_V1_API_KEY
export OFOX_ANTHROPIC_API_KEY="${OFOX_ANTHROPIC_API_KEY:-$OFOX_V1_API_KEY}"
export OFOX_GEMINI_API_KEY="${OFOX_GEMINI_API_KEY:-$OFOX_V1_API_KEY}"
# Backward compatibility for older config entries that still read OFOX_API_KEY.
export OFOX_API_KEY="${OFOX_API_KEY:-$OFOX_GEMINI_API_KEY}"
export ANTHROPIC_BETA_HEADER="${ANTHROPIC_BETA_HEADER:-prompt-caching-2024-07-31}"

LITELLM_HOST="${LITELLM_HOST:-0.0.0.0}"
LITELLM_PORT="${LITELLM_PORT:-4000}"

echo "[info] starting litellm proxy on ${LITELLM_HOST}:${LITELLM_PORT}"
echo "[info] anthropic beta header: ${ANTHROPIC_BETA_HEADER}"
exec litellm \
  --config ./config.yaml \
  --host "${LITELLM_HOST}" \
  --port "${LITELLM_PORT}" \
  --detailed_debug
