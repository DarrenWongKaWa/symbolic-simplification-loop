#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.config import read_json
from loop_engine.schemas import validate_with_schema


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    manifest = read_json(Path(args.manifest))
    validate_with_schema(manifest, "checkpoint_manifest")
    print({"gate": "PASS", "stage_name": manifest["stage_name"], "files": len(manifest["files"])})


if __name__ == "__main__":
    main()

