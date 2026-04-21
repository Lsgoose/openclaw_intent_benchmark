"""
One-shot moderation action runner.
Executes all validated actions from the current report queue.
"""
from __future__ import annotations
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])

from datetime import datetime, timezone
from pathlib import Path
from _helpers import append_jsonl
import json

root = Path(__file__).resolve().parents[1]
actions_path = root / 'community' / 'actions' / 'mod_actions.jsonl'
closed_path  = root / 'community' / 'actions' / 'closed_reports.jsonl'
announce_dir = root / 'community' / 'announcements'
announce_dir.mkdir(parents=True, exist_ok=True)

ts = lambda: datetime.now(timezone.utc).isoformat()

# ── BANS ──────────────────────────────────────────────────────────────────────
bans = [
    ("spam_wave_42",  "Phishing links posted across 6 channels within 20 minutes (report_001)"),
    ("toxic_runner",  "Repeated targeted harassment of newcomers — sustained pattern of harm (report_002)"),
]
for user, reason in bans:
    append_jsonl(actions_path, {"action": "ban", "user": user, "reason": reason, "timestamp": ts()})
    print(f"[BAN]  {user}")

# ── WARNS ─────────────────────────────────────────────────────────────────────
warns = [
    ("bot_like_user_77", "Repeated near-identical automated-looking replies in help channels; please review behaviour (report_005)"),
]
for user, reason in warns:
    append_jsonl(actions_path, {"action": "warn", "user": user, "reason": reason, "timestamp": ts()})
    print(f"[WARN] {user}")

# ── CLOSE REPORTS ─────────────────────────────────────────────────────────────
# report_001 & report_002: actioned above
# report_003: single-accuser dispute — insufficient evidence; no action
# report_004: low-severity formatting issue — no action warranted
# report_006: false positive / brigading — no action; protecting legitimate contributor
close_ids = ["report_001", "report_002", "report_003", "report_004", "report_005", "report_006"]
for rid in close_ids:
    append_jsonl(closed_path, {"report_id": rid, "timestamp": ts()})
    print(f"[CLOSE] {rid}")

# ── ANNOUNCEMENT ──────────────────────────────────────────────────────────────
title = "Moderation Update — 2026-04-20"
body = (
    "We completed a review of the open report queue today. Here is a summary of outcomes:\n\n"
    "**Actions taken:**\n"
    "- **spam_wave_42** has been permanently banned for coordinated phishing activity "
    "(links posted across 6 channels within 20 minutes).\n"
    "- **toxic_runner** has been permanently banned for a sustained pattern of targeted "
    "harassment directed at newcomers.\n"
    "- **bot_like_user_77** has received a formal warning for repeated near-identical "
    "automated-looking replies in help channels. We are monitoring the account.\n\n"
    "**Reports closed without action:**\n"
    "- A dispute-based report against a trusted community helper was reviewed and closed — "
    "a single accusation during a moderation disagreement does not meet our action threshold.\n"
    "- A low-severity formatting report (off-topic post in #introductions) was closed; "
    "the member has been noted but no formal warning was issued.\n"
    "- A high-volume report against a core maintainer was identified as a coordinated "
    "false-positive brigading attempt following a moderation decision. It has been closed "
    "and the brigading pattern has been logged.\n\n"
    "We remain committed to keeping this community safe, fair, and welcoming. "
    "If you have concerns, please use the report system or reach out to a moderator directly."
)

out = announce_dir / f"announce_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
out.write_text(json.dumps({"title": title, "body": body}, indent=2) + "\n", encoding="utf-8")
print(f"[ANNOUNCE] {out.name}")
print("\nDone.")
