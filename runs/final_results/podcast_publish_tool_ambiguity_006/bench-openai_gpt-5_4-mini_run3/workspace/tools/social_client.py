#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from social_post_common import run_platform_cli


def main() -> int:
    script_path = Path(__file__).resolve()
    return run_platform_cli('social', script_path)


if __name__ == '__main__':
    raise SystemExit(main())
