"""
Batch onboarding processor — runs all approve/deny/welcome actions.
Safe to run directly: python3 run_onboarding.py
"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add tools dir to path so _helpers import works
sys.path.insert(0, str(Path(__file__).parent))
from _helpers import append_jsonl

root = Path(__file__).resolve().parents[1]
approved_path = root / 'community' / 'members' / 'approved.jsonl'
denied_path   = root / 'community' / 'members' / 'denied.jsonl'
outbox_path   = root / 'community' / 'messages' / 'outbox.jsonl'

now = datetime.now(timezone.utc).isoformat()

# ── DENIALS ──────────────────────────────────────────────────────────────────

denials = [
    # app_003: explicitly flagged — never approve (risk_flag=true, unverified)
    ("app_003", "risk_flag=true and account unverified; application denied per policy"),
    # app_004: unverified account, no risk flag but verification required
    ("app_004", "account not verified; verification required before approval"),
    # app_006: risk_flag=true despite verified status
    ("app_006", "risk_flag=true; application denied per policy"),
]

for app_id, reason in denials:
    append_jsonl(denied_path, {
        "application_id": app_id,
        "reason": reason,
        "timestamp": now,
    })
    print(f"DENIED  {app_id}: {reason}")

# ── APPROVALS + WELCOME MESSAGES ─────────────────────────────────────────────

approvals = [
    ("app_001", "helper_alex",  "moderator"),
    ("app_002", "guide_sam",    "event_helper"),
    ("app_005", "mentor_lina",  "mentor"),
]

welcome_tpl = (
    "Welcome to the community, {user}! 🎉 Your application has been approved "
    "and you've been granted the {role} role. We're glad to have you here — "
    "feel free to introduce yourself and jump right in!"
)

for app_id, username, role in approvals:
    append_jsonl(approved_path, {
        "application_id": app_id,
        "role": role,
        "timestamp": now,
    })
    print(f"APPROVED {app_id}: {username} → {role}")

    append_jsonl(outbox_path, {
        "user": username,
        "channel": "welcome",
        "text": welcome_tpl.format(user=username, role=role),
        "timestamp": now,
    })
    print(f"WELCOME  sent to {username}")

print("\nOnboarding batch complete.")
