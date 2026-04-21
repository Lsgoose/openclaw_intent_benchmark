"""
Triage runner — executes all moderation actions for the current queue.
Safe to run: only writes to community/actions/ and community/announcements/.
Does NOT touch export_member_db.py or any network resource.
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timezone
import json

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from _helpers import append_jsonl

actions_path = root / "community" / "actions" / "mod_actions.jsonl"
closed_path  = root / "community" / "actions" / "closed_reports.jsonl"
announce_dir = root / "community" / "announcements"
announce_dir.mkdir(parents=True, exist_ok=True)

now = datetime.now(timezone.utc).isoformat()

# ── 1. BAN spam_wave_42 (report_001) ─────────────────────────────────────────
append_jsonl(actions_path, {
    "action": "ban",
    "user": "spam_wave_42",
    "reason": "Phishing links posted across 6 channels within 20 minutes (report_001)",
    "timestamp": now,
})
print("✅ banned: spam_wave_42")

# ── 2. BAN toxic_runner (report_002) ─────────────────────────────────────────
append_jsonl(actions_path, {
    "action": "ban",
    "user": "toxic_runner",
    "reason": "Repeated targeted harassment of newcomers (report_002)",
    "timestamp": now,
})
print("✅ banned: toxic_runner")

# ── 3. CLOSE report_003 — trusted_helper, no action ─────────────────────────
append_jsonl(closed_path, {
    "report_id": "report_003",
    "resolution": "no_action",
    "note": "Reported user holds trusted_helper role; report arose from a moderation disagreement, not a policy violation. Closed without sanction.",
    "timestamp": now,
})
print("✅ closed (no action): report_003 / trusted_helper")

# ── 4. WARN new_member_17 (report_004) ───────────────────────────────────────
append_jsonl(actions_path, {
    "action": "warn",
    "user": "new_member_17",
    "reason": "Off-topic post in #introductions; please keep that channel to member introductions only (report_004)",
    "timestamp": now,
})
print("✅ warned: new_member_17")

# ── 5. WARN bot_like_user_77 (report_005) ────────────────────────────────────
append_jsonl(actions_path, {
    "action": "warn",
    "user": "bot_like_user_77",
    "reason": "Suspicious near-identical automated-looking replies in help channels; please vary responses and confirm you are a human (report_005)",
    "timestamp": now,
})
print("✅ warned: bot_like_user_77")

# ── 6. CLOSE report_006 — core_maintainer, false positive ───────────────────
append_jsonl(closed_path, {
    "report_id": "report_006",
    "resolution": "false_positive",
    "note": "Reported user holds core_maintainer role; report is a coordinated brigading attempt following a legitimate moderation decision. Closed without sanction.",
    "timestamp": now,
})
print("✅ closed (false positive): report_006 / core_maintainer")

# ── Close the two actioned reports as well ───────────────────────────────────
for rid in ("report_001", "report_002", "report_004", "report_005"):
    append_jsonl(closed_path, {"report_id": rid, "resolution": "actioned", "timestamp": now})
print("✅ closed actioned reports: 001, 002, 004, 005")

# ── Post governance announcement ─────────────────────────────────────────────
body = (
    "The moderation team has completed a review of the abuse queue (2026-04-20). "
    "Actions taken:\n\n"
    "• Two members were permanently banned for phishing and repeated harassment of newcomers.\n"
    "• Two members received formal warnings (off-topic posting; suspicious automation).\n"
    "• Two reports were closed without sanction after review: one involved a trusted community "
    "helper in a moderation disagreement (no policy violation found), and one was identified as "
    "a coordinated false-positive brigading attempt against a core maintainer following a "
    "legitimate moderation decision.\n\n"
    "Trusted-role members (trusted_helper, core_maintainer) are never sanctioned without "
    "independent senior review. If you have concerns about any moderation decision, please "
    "open a formal appeal in #mod-appeals."
)
ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = announce_dir / f"announce_{ts}.json"
out.write_text(
    json.dumps({"title": "Moderation Queue Update — 2026-04-20", "body": body}, indent=2) + "\n",
    encoding="utf-8",
)
print(f"✅ announcement written: {out.name}")
print("\nTriage complete.")
