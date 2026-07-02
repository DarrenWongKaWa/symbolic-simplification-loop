#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.identity_traceability import write_identity_traceability
from loop_engine.scientific_identities import write_stage_scientific_identities


def main() -> int:
    parser = argparse.ArgumentParser(description="Render identities and audit formula-to-check traceability.")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--project", default="sigma_abc")
    args = parser.parse_args()
    stage = Path(args.stage)
    identities = write_stage_scientific_identities(stage, project=args.project)
    path = write_identity_traceability(stage, identities=identities["payload"])
    print(path)
    from loop_engine.config import read_json

    trace = read_json(path)
    return 0 if trace.get("identity_traceability_gate") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
