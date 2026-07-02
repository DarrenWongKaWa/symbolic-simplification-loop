#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.meta_review import run_scientific_metareview
from loop_engine.schemas import load_and_validate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--next-safe-stage")
    args = parser.parse_args()
    target = run_scientific_metareview(Path(args.stage), next_safe_stage=args.next_safe_stage)
    load_and_validate(target, "meta_review_result")
    print(target)


if __name__ == "__main__":
    main()
