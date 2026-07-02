#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.config import REPO_ROOT, write_json
from loop_engine.review_debt import settle_review_debt
from loop_engine.review_queue import resume_pending_reviews


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project")
    group.add_argument("--project-root")
    parser.add_argument("--stage-id")
    parser.add_argument("--auto-resume", action="store_true", help="Run reviewer-only resume before settling open runtime-limited review debt.")
    args = parser.parse_args()
    run_root = REPO_ROOT / "autonomous_runs" / args.project if args.project else Path(args.project_root)
    auto_resume = None
    if args.auto_resume:
        auto_resume = resume_pending_reviews(run_root)
    result = settle_review_debt(run_root, args.stage_id)
    if auto_resume is not None:
        if isinstance(result, dict):
            result["auto_resume"] = auto_resume
    target = run_root / "SETTLE_REVIEW_DEBT_REPORT.json"
    write_json(target, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
