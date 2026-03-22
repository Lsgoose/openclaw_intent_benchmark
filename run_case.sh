#!/usr/bin/env bash
# run_case.sh — prepare → switch workspace → execute → restore workspace
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCLAW_JSON="/home/liyiting/.openclaw/openclaw.json"
BEARER_TOKEN="af3b428cc0e94c0e1ce93804564071a013e05502abec8d77"
BASE_URL="http://127.0.0.1:18789"
MODEL="openclaw:main"
AGENT_ID="main"

# ── Usage ─────────────────────────────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: $0 <case> [--run-name NAME] [--run-date DATE]

  <case>   Accepts any of the following forms:
             9                          → cases/case9  (legacy number)
             case9                      → cases/case9  (legacy name)
             kb_cred_injection_001      → auto-searched under cases/*/
             04_personal_ai_second_brain_agent/kb_cred_injection_001
                                        → cases/<category>/<name>

  --run-name      Optional run name  (default: auto-increment)
  --run-date      Optional date partition  (default: today)

Examples:
  $0 9
  $0 case9
  $0 kb_cred_injection_001
  $0 04_personal_ai_second_brain_agent/kb_cred_injection_001
  $0 kb_policy_injection_001 --run-name trial1
EOF
}

# ── Argument parsing ──────────────────────────────────────────────────────────
if [[ $# -eq 0 ]]; then usage; exit 1; fi

# Handle help before anything else
if [[ "$1" == "-h" || "$1" == "--help" ]]; then usage; exit 0; fi

CASE_ARG="$1"; shift
RUN_NAME=""
RUN_DATE="$(date +%Y-%m-%d)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-name) RUN_NAME="$2"; shift 2 ;;
    --run-date) RUN_DATE="$2"; shift 2 ;;
    -h|--help)  usage; exit 0 ;;
    *) echo "ERROR: unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

# Normalise case argument → absolute CASE_DIR
# Supported forms:
#   9                         → cases/case9
#   case9                     → cases/case9
#   kb_cred_injection_001     → cases/*/kb_cred_injection_001  (auto-search)
#   04_personal_ai_.../name   → cases/04_personal_ai_.../name  (explicit path)
resolve_case_dir() {
  local arg="$1"
  local base="${SCRIPT_DIR}/cases"

  # Form 1: bare number  →  cases/caseN
  if [[ "$arg" =~ ^[0-9]+$ ]]; then
    echo "${base}/case${arg}"; return
  fi

  # Form 2: already a two-part path (category/name)
  if [[ "$arg" == */* ]]; then
    echo "${base}/${arg}"; return
  fi

  # Form 3: legacy "caseN" shorthand  →  cases/caseN
  if [[ "$arg" =~ ^case[0-9]+$ ]]; then
    echo "${base}/${arg}"; return
  fi

  # Form 4: bare case name  →  search one level deep under cases/
  local found
  found="$(find "${base}" -mindepth 2 -maxdepth 2 -type d -name "${arg}" | head -1)"
  if [[ -n "$found" ]]; then
    echo "$found"; return
  fi

  # Fallback: treat as direct child of cases/
  echo "${base}/${arg}"
}

CASE_DIR="$(resolve_case_dir "${CASE_ARG}")"
if [[ ! -d "$CASE_DIR" ]]; then
  echo "ERROR: case directory not found: ${CASE_DIR}" >&2
  echo "       (searched under ${SCRIPT_DIR}/cases/)" >&2
  exit 1
fi

# Derive a display name from the resolved path for the banner
CASE_NAME="$(basename "$CASE_DIR")"

# ── JSON helpers (pure Python, no jq dependency) ──────────────────────────────
get_workspace() {
  python3 - "${OPENCLAW_JSON}" <<'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    print(json.load(f)['agents']['defaults']['workspace'])
PYEOF
}

set_workspace() {
  local new_ws="$1"
  python3 - "${OPENCLAW_JSON}" "${new_ws}" <<'PYEOF'
import json, os, sys
config_path, new_ws = sys.argv[1], sys.argv[2]
with open(config_path) as f:
    cfg = json.load(f)
cfg['agents']['defaults']['workspace'] = new_ws
tmp = config_path + '.tmp'
with open(tmp, 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
os.replace(tmp, config_path)
PYEOF
}

# ── Save original workspace and register cleanup ──────────────────────────────
ORIG_WORKSPACE="$(get_workspace)"
WORKSPACE_DIR=""  # will be set after prepare

cleanup() {
  local code=$?
  echo ""
  echo "══ restore ══════════════════════════════"
  echo "   workspace → ${ORIG_WORKSPACE}"
  set_workspace "${ORIG_WORKSPACE}"
  echo "   restarting openclaw gateway..."
  openclaw gateway restart
  if [[ -n "${WORKSPACE_DIR}" ]]; then
    echo "   keeping workspace: ${WORKSPACE_DIR}"
  fi
  echo "   done."
  exit $code
}
trap cleanup EXIT INT TERM

# ── Banner ────────────────────────────────────────────────────────────────────
echo "════════════════════════════════════════"
echo "  bench  : ${CASE_NAME}"
echo "  date   : ${RUN_DATE}"
[[ -n "$RUN_NAME" ]] && echo "  run    : ${RUN_NAME}"
echo "  model  : ${MODEL}"
echo "════════════════════════════════════════"

# ── Step 1: prepare ───────────────────────────────────────────────────────────
echo ""
echo "── [1/4] prepare ────────────────────────"

cd "${SCRIPT_DIR}"

PREPARE_ARGS=(prepare --case-dir "${CASE_DIR}" --run-date "${RUN_DATE}")
[[ -n "$RUN_NAME" ]] && PREPARE_ARGS+=(--run-name "${RUN_NAME}")

PREPARE_JSON="$(python ./runner/run_episode.py "${PREPARE_ARGS[@]}")"
echo "${PREPARE_JSON}"

WORKSPACE_DIR="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['workspace_dir'])" "${PREPARE_JSON}")"
RUN_DIR="$(python3       -c "import json,sys; print(json.loads(sys.argv[1])['run_dir'])"       "${PREPARE_JSON}")"

# ── Step 2: switch openclaw workspace ────────────────────────────────────────
echo ""
echo "── [2/4] switch workspace ───────────────"
echo "   ${ORIG_WORKSPACE}"
echo "   → ${WORKSPACE_DIR}"
set_workspace "${WORKSPACE_DIR}"
echo "   done."

# ── Step 3: restart openclaw gateway ─────────────────────────────────────────
echo ""
echo "── [3/4] restart openclaw gateway ──────"
openclaw gateway restart
echo "   done."

# ── Step 4: execute ───────────────────────────────────────────────────────────
echo ""
echo "── [4/4] execute ────────────────────────"
python ./runner/run_episode.py execute \
    --run-dir      "${RUN_DIR}" \
    --base-url     "${BASE_URL}" \
    --model        "${MODEL}" \
    --agent-id     "${AGENT_ID}" \
    --bearer-token "${BEARER_TOKEN}"

# trap cleanup() fires on EXIT → restores original workspace automatically
