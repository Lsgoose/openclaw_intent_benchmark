"""Compatibility shim for legacy `runner.run_episode` import path."""

from __future__ import annotations

from agent_risk_benchmark.runner.run_episode import main

if __name__ == '__main__':
    raise SystemExit(main())
