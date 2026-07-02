#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

import _bootstrap  # noqa: F401
from loop_engine.pre_run_brief import write_pre_run_brief


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a stage pre-run brief.")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--profile")
    args = parser.parse_args()
    profile = {}
    if args.profile:
        profile = yaml.safe_load(Path(args.profile).read_text(encoding="utf-8")) or {}
    path = write_pre_run_brief(Path(args.stage), profile=profile)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
