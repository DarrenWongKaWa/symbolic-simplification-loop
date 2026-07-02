#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.config import REPO_ROOT, write_json
from loop_engine.review_queue import resume_pending_reviews


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--from-pending", action="store_true")
    parser.add_argument("--allow-l0-freeze", action="store_true")
    args = parser.parse_args()
    run_root = REPO_ROOT / "autonomous_runs" / args.project
    result = resume_pending_reviews(run_root, allow_l0_freeze=args.allow_l0_freeze)
    target = run_root / "RESUME_PENDING_REVIEWS_REPORT.json"
    write_json(target, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
