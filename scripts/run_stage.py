#!/usr/bin/env python3
"""Mark a stage as executing.

Boundary: this helper only advances lifecycle state. It does not execute full physical verification,
Mathematica/Wolfram symbolic checks, reviewer agents, or
checkpoint freezing. Use `scripts/run_autonomous_loop.py` for the full
plan/execute/validate/review/decision cycle.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.completion_matrix import load_completion_matrix
from loop_engine.config import read_json, write_json
from loop_engine.human_signoff import load_signoff
from loop_engine.safety import assert_no_hard_stop
from loop_engine.state import StageStatus


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    stage = Path(args.stage)
    assert_no_hard_stop(stage)
    state_path = stage / ".loop" / "state.json"
    state = read_json(state_path) if state_path.exists() else {"stage_name": stage.name}
    state["status"] = StageStatus.EXECUTING
    write_json(state_path, state)
    print(f"{stage}: status={StageStatus.EXECUTING}")
    matrix = load_completion_matrix(stage)
    signoff = load_signoff(stage)
    print(f"Completion matrix: {'present' if matrix else 'missing'}")
    if matrix:
        print(f"Recommended human action: {matrix.get('recommended_human_action')}")
        print(f"Freeze eligible mirror: {matrix.get('freeze_eligible')}")
    print(f"Human signoff: {signoff.get('decision') if signoff else 'missing'}")


if __name__ == "__main__":
    main()
