#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.packet_builder import build_review_packet
from loop_engine.config import write_json
from loop_engine.state import StageStatus


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare one manual review loop for a stage.")
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    stage = Path(args.stage)
    packet = build_review_packet(stage)
    write_json(stage / ".loop" / "state.json", {"stage_name": stage.name, "status": StageStatus.READY_FOR_REVIEW})
    print({"review_packet": str(packet), "next": "send packet to reviewer, save review_result.json, import it"})


if __name__ == "__main__":
    main()

