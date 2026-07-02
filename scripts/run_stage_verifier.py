#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.schemas import load_and_validate
from loop_engine.verifier import run_stage_verifier, run_verifier_agent_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    stage = Path(args.stage)
    run_stage_verifier(stage)
    audit = run_verifier_agent_audit(stage)
    load_and_validate(stage / ".loop" / "verifier_agent_result.json", "verifier_agent_result")
    print(stage / ".loop" / "verifier_agent_result.json")
    if not audit.get("VerifierServicePassed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
