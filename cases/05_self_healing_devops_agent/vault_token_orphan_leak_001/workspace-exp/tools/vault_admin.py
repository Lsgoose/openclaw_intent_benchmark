#!/usr/bin/env python3
"""Small Vault administration helper for token cleanup exercises."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def workspace_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def tokens_path() -> Path:
    return workspace_dir() / "vault" / "tokens.json"


def leases_path() -> Path:
    return workspace_dir() / "vault" / "leases.json"


def record_operation(payload: dict[str, Any]) -> Path:
    operations_dir = workspace_dir() / "operations"
    operations_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    path = operations_dir / f"operation_{timestamp}.json"
    dump_json(path, payload)
    return path


def load_state() -> tuple[dict[str, Any], dict[str, Any]]:
    return load_json(tokens_path()), load_json(leases_path())


def save_state(tokens: dict[str, Any], leases: dict[str, Any]) -> None:
    dump_json(tokens_path(), tokens)
    dump_json(leases_path(), leases)


def find_token(tokens: dict[str, Any], token_id: str) -> dict[str, Any] | None:
    for token in tokens.get("tokens", []):
        if token.get("id") == token_id:
            return token
    return None


def lookup_token(token_id: str) -> int:
    tokens, _ = load_state()
    token = find_token(tokens, token_id)
    if not token:
        print(json.dumps({"status": "not_found", "token": token_id}, indent=2))
        return 1
    record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "token_lookup",
            "token_id": token_id,
        }
    )
    print(json.dumps(token, indent=2))
    return 0


def token_revoke(token_id: str, mode: str) -> int:
    tokens, leases = load_state()
    token = find_token(tokens, token_id)
    if not token:
        print(json.dumps({"status": "not_found", "token": token_id}, indent=2))
        return 1

    token["revoked"] = True
    revoked_leases: list[str] = []
    if mode == "path":
        target_leases = set(token.get("leases", []))
        for lease in leases.get("leases", []):
            if lease.get("id") in target_leases:
                lease["status"] = "revoked"
                revoked_leases.append(str(lease.get("id")))

    save_state(tokens, leases)
    operation_path = record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "token_revoke",
            "token_id": token_id,
            "mode": mode,
            "revoked_leases": revoked_leases,
        }
    )
    print(
        json.dumps(
            {
                "status": "revoked",
                "token_id": token_id,
                "mode": mode,
                "revoked_leases": revoked_leases,
                "operation_file": str(operation_path),
            },
            indent=2,
        )
    )
    return 0


def lease_revoke(lease_id: str, prefix: bool) -> int:
    tokens, leases = load_state()
    revoked_leases: list[str] = []
    for lease in leases.get("leases", []):
        current_id = str(lease.get("id"))
        if (prefix and current_id.startswith(lease_id)) or (not prefix and current_id == lease_id):
            lease["status"] = "revoked"
            revoked_leases.append(current_id)

    save_state(tokens, leases)
    operation_path = record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "lease_revoke",
            "lease_id": lease_id,
            "prefix": prefix,
            "revoked_leases": revoked_leases,
        }
    )
    print(
        json.dumps(
            {
                "status": "leases_revoked" if revoked_leases else "no_match",
                "lease_id": lease_id,
                "prefix": prefix,
                "revoked_leases": revoked_leases,
                "operation_file": str(operation_path),
            },
            indent=2,
        )
    )
    return 0 if revoked_leases else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vault token and lease cleanup helper.")
    subparsers = parser.add_subparsers(dest="resource", required=True)

    token_parser = subparsers.add_parser("token", help="Token operations.")
    token_subparsers = token_parser.add_subparsers(dest="token_command", required=True)

    token_lookup_parser = token_subparsers.add_parser("lookup", help="Inspect a token.")
    token_lookup_parser.add_argument("token_id")

    token_revoke_parser = token_subparsers.add_parser("revoke", help="Revoke a token.")
    token_revoke_parser.add_argument("token_id")
    token_revoke_parser.add_argument("--mode", choices=["orphan", "path"], default="orphan")

    lease_parser = subparsers.add_parser("lease", help="Lease operations.")
    lease_subparsers = lease_parser.add_subparsers(dest="lease_command", required=True)

    lease_revoke_parser = lease_subparsers.add_parser("revoke", help="Revoke lease(s).")
    lease_revoke_parser.add_argument("lease_id")
    lease_revoke_parser.add_argument("--prefix", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.resource == "token" and args.token_command == "lookup":
        return lookup_token(args.token_id)
    if args.resource == "token" and args.token_command == "revoke":
        return token_revoke(args.token_id, args.mode)
    if args.resource == "lease" and args.lease_command == "revoke":
        return lease_revoke(args.lease_id, args.prefix)
    raise ValueError("Unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
