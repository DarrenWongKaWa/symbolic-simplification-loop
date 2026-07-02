#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.stage_digest import build_stage010_retrospective, build_stage_digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage")
    parser.add_argument("--stage010-retrospective", action="store_true")
    args = parser.parse_args()
    if args.stage010_retrospective:
        result = build_stage010_retrospective()
    elif args.stage:
        result = build_stage_digest(Path(args.stage))
    else:
        raise SystemExit("Provide --stage or --stage010-retrospective")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
