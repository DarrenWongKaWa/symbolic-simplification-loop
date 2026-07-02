#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.reviewer import aggregate_review_results
from loop_engine.schemas import load_and_validate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    target = aggregate_review_results(Path(args.stage))
    load_and_validate(target, "review_result")
    print(target)


if __name__ == "__main__":
    main()
