#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

import _bootstrap  # noqa: F401
from loop_engine.completion_matrix import load_completion_matrix, write_completion_matrix
from loop_engine.human_signoff import build_signoff_from_decision, write_signoff


def parse_signoff_stdin(stdin_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in stdin_text.splitlines():
        line = raw_line.strip()
        if not line or line == "SIGNOFF":
            continue
        if line.startswith("SIGNOFF "):
            line = line.removeprefix("SIGNOFF ").strip()
        for part in [line] if "=" in line and " " not in line else line.split():
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            fields[key.strip().replace("-", "_")] = value.strip()
    return fields


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a stage human_signoff.yaml from a lightweight human decision.")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--decision", choices=["APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT", "DO_NOT_FREEZE_PATCH", "REJECT_AND_STOP"])
    parser.add_argument("--reason")
    parser.add_argument("--signed-by", default="wangjiahua")
    parser.add_argument("--use-recommended", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stage = Path(args.stage)
    stdin_fields = parse_signoff_stdin(sys.stdin.read()) if not sys.stdin.isatty() else {}

    if not load_completion_matrix(stage):
        write_completion_matrix(stage)
    matrix = load_completion_matrix(stage) or {}

    decision = args.decision or stdin_fields.get("decision")
    if args.use_recommended or not decision:
        decision = matrix.get("recommended_human_action", "DO_NOT_FREEZE_PATCH")
    reason = args.reason or stdin_fields.get("reason")
    signed_by = args.signed_by or stdin_fields.get("signed_by", "wangjiahua")

    signoff = build_signoff_from_decision(stage, decision, reason=reason, signed_by=signed_by, signed_via="sign_stage.py")
    if args.dry_run:
        print(yaml.safe_dump(signoff, sort_keys=False, allow_unicode=True), end="")
        return
    target = write_signoff(stage, signoff)
    print(target)


if __name__ == "__main__":
    main()
