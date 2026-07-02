#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

import _bootstrap  # noqa: F401
from loop_engine.config import read_json, write_json
from loop_engine.pre_run_brief import audit_pre_run_brief


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a stage pre-run brief.")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--profile")
    args = parser.parse_args()
    stage = Path(args.stage)
    profile = yaml.safe_load(Path(args.profile).read_text(encoding="utf-8")) if args.profile else {}
    brief = read_json(stage / ".loop" / "pre_run_brief.json") if (stage / ".loop" / "pre_run_brief.json").exists() else None
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    write_json(stage / ".loop" / "pre_run_brief_audit.json", audit)
    print(stage / ".loop" / "pre_run_brief_audit.json")
    return 1 if audit.get("hard_stop") else 0


if __name__ == "__main__":
    raise SystemExit(main())
