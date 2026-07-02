#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.config import REPO_ROOT, relative_to_repo
from loop_engine.scientist_review import build_scientist_review_packet


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a human-facing scientist review packet from existing loop evidence."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--from-stage")
    parser.add_argument("--to-stage")
    parser.add_argument("--format", choices=["md", "tex", "pdf"], action="append", default=["md"])
    args = parser.parse_args()

    output = args.output or (REPO_ROOT / "docs" / "scientist_review" / args.project)
    # Stage-range flags are reserved for future narrower packets; current packet
    # remains read-only and summarizes live project stages.
    packet = build_scientist_review_packet(args.project, output, build_pdf=("pdf" in args.format or True))
    print(
        json.dumps(
            {
                "project": packet.project,
                "output_dir": relative_to_repo(packet.output_dir),
                "stage_count": len(packet.stage_dossiers),
                "generated_files": [relative_to_repo(path) for path in packet.generated_files],
                "pdf_built": packet.pdf_built,
                "pdf_error": packet.pdf_error,
                "signoff_file_created": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
