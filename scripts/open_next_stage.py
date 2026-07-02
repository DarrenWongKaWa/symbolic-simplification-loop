#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.integrator import open_next_stage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--goal", default="TBD")
    args = parser.parse_args()
    print(open_next_stage(Path(args.project), args.stage, goal=args.goal))


if __name__ == "__main__":
    main()

