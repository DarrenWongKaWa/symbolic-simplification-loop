#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.review_quality import build_review_quality
from loop_engine.schemas import load_and_validate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--next-safe-stage")
    args = parser.parse_args()
    stage = Path(args.stage)
    build_review_quality(stage, next_safe_stage=args.next_safe_stage)
    target = stage / ".loop" / "review_quality.json"
    load_and_validate(target, "review_quality")
    print(target)


if __name__ == "__main__":
    main()
