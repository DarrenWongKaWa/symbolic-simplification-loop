#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.reviewer import REVIEW_MODES, load_review_mode, run_local_reviewer_agents
from loop_engine.schemas import load_and_validate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--mode", choices=REVIEW_MODES)
    parser.add_argument(
        "--scope",
        choices=["routine_branch", "major_checkpoint", "paper_claim", "scientific_route", "general"],
        default="routine_branch",
    )
    args = parser.parse_args()
    stage = Path(args.stage)
    mode = args.mode or load_review_mode(stage)
    for path in run_local_reviewer_agents(stage, mode=mode, review_scope=args.scope):
        load_and_validate(path, "review_result")
        print(path)


if __name__ == "__main__":
    main()
