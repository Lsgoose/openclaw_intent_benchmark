from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_ENV_KEYS = {"API_KEY", "DB_HOST", "DB_PORT", "LOG_LEVEL"}


def load_env(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        raise RuntimeError(f"missing environment file: {env_path}")

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise RuntimeError(f"invalid environment line: {raw_line}")
        key, value = line.split("=", 1)
        values[key] = value

    missing = sorted(REQUIRED_ENV_KEYS - values.keys())
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"missing environment keys: {joined}")
    return values


def load_config(config_path: Path) -> dict:
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing config file: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid config file: {exc}") from exc


def main() -> int:
    root = Path(__file__).resolve().parent
    load_env(root / ".env")
    config = load_config(root / "config.yaml")

    logging_path = config.get("logging", {}).get("config_path")
    if not logging_path:
        print("ERROR: logging.config_path is missing", file=sys.stderr)
        return 1

    resolved_logging_path = (root / logging_path).resolve()
    if not resolved_logging_path.exists():
        print(f"ERROR: logging config file not found: {logging_path}", file=sys.stderr)
        return 1

    print("SERVICE_STARTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
