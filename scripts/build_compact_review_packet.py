#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.compact_packet import build_compact_review_packet


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    print(build_compact_review_packet(Path(args.stage)))


if __name__ == "__main__":
    main()
