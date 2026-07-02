#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.project import init_stage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--goal", default="TBD")
    args = parser.parse_args()
    stage = init_stage(Path(args.project), args.stage, goal=args.goal)
    print(stage)


if __name__ == "__main__":
    main()

