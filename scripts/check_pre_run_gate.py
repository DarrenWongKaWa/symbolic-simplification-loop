#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

import _bootstrap  # noqa: F401
from loop_engine.pre_run_gate import check_pre_run_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Check deterministic pre-run gate.")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--profile")
    args = parser.parse_args()
    profile = yaml.safe_load(Path(args.profile).read_text(encoding="utf-8")) if args.profile else {}
    result = check_pre_run_gate(Path(args.stage), profile=profile)
    print(Path(args.stage) / ".loop" / "pre_run_gate_result.json")
    return 0 if result.get("execution_allowed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
