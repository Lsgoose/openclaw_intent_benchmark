#!/usr/bin/env python3
"""Elasticsearch snapshot helper for repository setup exercises."""

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


def repositories_path() -> Path:
    return workspace_dir() / "elasticsearch" / "repositories.json"


def target_spec_path() -> Path:
    return workspace_dir() / "configs" / "repo_target.json"


def record_operation(payload: dict[str, Any]) -> Path:
    operations_dir = workspace_dir() / "operations"
    operations_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    path = operations_dir / f"operation_{timestamp}.json"
    dump_json(path, payload)
    return path


def normalize_base_path(value: str) -> str:
    return value.strip().strip("/")


def load_repositories() -> dict[str, Any]:
    return load_json(repositories_path())


def save_repositories(payload: dict[str, Any]) -> None:
    dump_json(repositories_path(), payload)


def target_spec() -> dict[str, Any]:
    return load_json(target_spec_path())


def find_repository(payload: dict[str, Any], name: str) -> dict[str, Any] | None:
    for repo in payload.get("repositories", []):
        if repo.get("name") == name:
            return repo
    return None


def verify_repository_state(repo: dict[str, Any]) -> bool:
    expected = target_spec()
    matches = (
        str(repo.get("name") or "") == str(expected.get("name") or "")
        and str(repo.get("bucket") or "") == str(expected.get("bucket") or "")
        and normalize_base_path(str(repo.get("base_path") or "")) == normalize_base_path(str(expected.get("base_path") or ""))
        and str(repo.get("region") or "") == str(expected.get("region") or "")
    )
    repo["verified"] = matches
    repo["health"] = "green" if matches else "red"
    return matches


def create_repo(name: str, bucket: str, base_path: str, region: str, verify: bool) -> int:
    payload = load_repositories()
    repo = find_repository(payload, name)
    if repo is None:
        repo = {"name": name}
        payload.setdefault("repositories", []).append(repo)

    repo["bucket"] = bucket
    repo["base_path"] = normalize_base_path(base_path)
    repo["region"] = region
    repo["verified"] = False
    repo["health"] = "unknown"

    verification_success = False
    if verify:
        verification_success = verify_repository_state(repo)

    save_repositories(payload)
    operation_path = record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "create_repo",
            "name": name,
            "bucket": bucket,
            "base_path": normalize_base_path(base_path),
            "region": region,
            "verify": verify,
            "verification_success": verification_success,
        }
    )
    print(
        json.dumps(
            {
                "status": "created",
                "name": name,
                "verify": verify,
                "verification_success": verification_success,
                "operation_file": str(operation_path),
            },
            indent=2,
        )
    )
    return 0


def verify_repo(name: str) -> int:
    payload = load_repositories()
    repo = find_repository(payload, name)
    if repo is None:
        print(json.dumps({"status": "not_found", "name": name}, indent=2))
        return 1

    verification_success = verify_repository_state(repo)
    save_repositories(payload)
    operation_path = record_operation(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "verify_repo",
            "name": name,
            "verification_success": verification_success,
        }
    )
    print(
        json.dumps(
            {
                "status": "verified" if verification_success else "failed",
                "name": name,
                "verification_success": verification_success,
                "operation_file": str(operation_path),
            },
            indent=2,
        )
    )
    return 0 if verification_success else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Elasticsearch snapshot repository helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create-repo", help="Create or update a repository.")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--bucket", required=True)
    create_parser.add_argument("--base-path", required=True)
    create_parser.add_argument("--region", required=True)
    verify_group = create_parser.add_mutually_exclusive_group()
    verify_group.add_argument("--verify", action="store_true")
    verify_group.add_argument("--no-verify", action="store_true")

    verify_parser = subparsers.add_parser("verify-repo", help="Verify an existing repository.")
    verify_parser.add_argument("--name", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "create-repo":
        return create_repo(args.name, args.bucket, args.base_path, args.region, bool(args.verify))
    if args.command == "verify-repo":
        return verify_repo(args.name)
    raise ValueError("Unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
