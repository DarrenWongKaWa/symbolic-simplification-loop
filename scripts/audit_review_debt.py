#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.review_debt import create_review_debt_if_allowed, iter_open_review_debts
from loop_engine.config import REPO_ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage")
    parser.add_argument("--project")
    parser.add_argument("--profile", default="sigma_abc_hypothesis_pre_ibp_throughput")
    args = parser.parse_args()
    if args.stage:
        import yaml
        profile_path = REPO_ROOT / "profiles" / f"{args.profile}.yaml"
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) if profile_path.exists() else {}
        result = create_review_debt_if_allowed(Path(args.stage), profile)
    else:
        run_root = REPO_ROOT / "autonomous_runs" / args.project
        result = {"open_review_debts": iter_open_review_debts(run_root)}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
