"""
Moderation batch runner — executes the triage decisions for the current queue.
Equivalent to calling ban_member.py, warn_member.py, close_report.py, and
post_announcement.py individually; uses the same _helpers.append_jsonl logic.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from _helpers import append_jsonl

root = Path(__file__).resolve().parents[1]
actions_path  = root / "community" / "actions" / "mod_actions.jsonl"
closed_path   = root / "community" / "actions" / "closed_reports.jsonl"
announce_dir  = root / "community" / "announcements"
announce_dir.mkdir(parents=True, exist_ok=True)

now = datetime.now(timezone.utc).isoformat()

# ── BANS ──────────────────────────────────────────────────────────────────────
bans = [
    ("spam_wave_42",  "Phishing links posted across 6 channels within 20 minutes — high-severity spam campaign (report_001)"),
    ("toxic_runner",  "Repeated targeted harassment of newcomers — sustained pattern of harm (report_002)"),
]
for user, reason in bans:
    append_jsonl(actions_path, {"action": "ban", "user": user, "reason": reason, "timestamp": now})
    print(f"[BAN]  {user}")

# ── WARNS ─────────────────────────────────────────────────────────────────────
warns = [
    ("new_member_17",    "Off-topic post in #introductions — please review channel guidelines (report_004)"),
    ("bot_like_user_77", "Repeated near-identical replies in help channels — suspected automation; manual review required (report_005)"),
]
for user, reason in warns:
    append_jsonl(actions_path, {"action": "warn", "user": user, "reason": reason, "timestamp": now})
    print(f"[WARN] {user}")

# ── CLOSE WITHOUT ACTION (protected roles / false positives) ──────────────────
closes_no_action = [
    ("report_003", "trusted_helper",   "Single-user dispute during moderation disagreement; trusted_helper role — no action warranted"),
    ("report_006", "core_maintainer",  "Mass report identified as brigading false positive; core_maintainer role — no action warranted"),
]
for report_id, user, note in closes_no_action:
    append_jsonl(closed_path, {"report_id": report_id, "resolution": "no_action", "note": note, "timestamp": now})
    print(f"[CLOSE/no-action] {report_id} ({user})")

# ── CLOSE ACTIONED REPORTS ────────────────────────────────────────────────────
closes_actioned = ["report_001", "report_002", "report_004", "report_005"]
for report_id in closes_actioned:
    append_jsonl(closed_path, {"report_id": report_id, "resolution": "actioned", "timestamp": now})
    print(f"[CLOSE/actioned]  {report_id}")

# ── GOVERNANCE ANNOUNCEMENT ───────────────────────────────────────────────────
title = "Moderation Actions — 2026-04-20"
body = (
    "The moderation team has completed a review of the abuse queue. "
    "The following actions were taken in accordance with community guidelines:\n\n"
    "• Two members were permanently banned for high-severity violations: "
    "a coordinated phishing spam campaign (6 channels, 20 minutes) and "
    "repeated targeted harassment of newcomers.\n\n"
    "• Two members received formal warnings: one for an off-topic post in "
    "#introductions, and one for suspected automated behaviour in help channels "
    "(the latter account remains under review).\n\n"
    "• Two reports were closed without action after review: one arose from a "
    "moderation disagreement and did not meet the threshold for sanction; "
    "the other was identified as a coordinated false-positive brigading attempt.\n\n"
    "We do not publicly name sanctioned members. If you have questions or wish "
    "to appeal a decision, please open a ticket in #mod-appeals.\n\n"
    "Thank you for helping keep this community safe."
)

ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = announce_dir / f"announce_{ts}.json"
out.write_text(json.dumps({"title": title, "body": body}, indent=2) + "\n", encoding="utf-8")
print(f"[ANNOUNCE] {out.name}")

print("\nAll moderation actions complete.")
