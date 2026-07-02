#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.reviewer import import_role_review_result
from loop_engine.schemas import load_and_validate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--role")
    args = parser.parse_args()
    source = Path(args.file)
    load_and_validate(source, "review_result")
    print(import_role_review_result(Path(args.stage), source, reviewer_role=args.role))


if __name__ == "__main__":
    main()

