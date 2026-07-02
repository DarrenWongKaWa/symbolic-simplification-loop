#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.project import init_project


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--sigma-abc-template", action="store_true")
    args = parser.parse_args()
    project = init_project(Path(args.root), args.name, from_sigma_abc_template=args.sigma_abc_template)
    print(project)


if __name__ == "__main__":
    main()

