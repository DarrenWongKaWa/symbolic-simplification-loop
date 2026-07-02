#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.reviewer import REVIEW_MODES, build_reviewer_agent_prompt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--mode", choices=REVIEW_MODES, default="codex_subagent")
    parser.add_argument(
        "--role",
        choices=["GeneralReviewer", "AlgebraReviewer", "PhysicsReviewer", "SoftwareReviewer"],
        default="GeneralReviewer",
    )
    parser.add_argument(
        "--scope",
        choices=["routine_branch", "major_checkpoint", "paper_claim", "scientific_route", "general"],
        default="routine_branch",
    )
    args = parser.parse_args()
    print(build_reviewer_agent_prompt(Path(args.stage), mode=args.mode, reviewer_role=args.role, review_scope=args.scope))


if __name__ == "__main__":
    main()
