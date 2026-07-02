#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.completion_matrix import write_completion_matrix
from loop_engine.config import read_json, utc_now
from loop_engine.human_signoff import build_signoff_from_decision, write_signoff


DECISION_MAP = {
    "DO_NOT_FREEZE": "DO_NOT_FREEZE_PATCH",
    "APPROVE": "APPROVE_FREEZE",
    "APPROVE_WITH_CAVEAT": "APPROVE_FREEZE_WITH_CAVEAT",
    "REJECT": "REJECT_AND_STOP",
}


def migrate(stage: Path) -> Path:
    legacy = stage / ".loop" / "human_signoff.json"
    if not legacy.exists():
        raise FileNotFoundError(legacy)
    if not (stage / "reports" / "completion_matrix.json").exists():
        write_completion_matrix(stage)
    old = read_json(legacy)
    decision = DECISION_MAP.get(old.get("decision"), old.get("decision", "DO_NOT_FREEZE_PATCH"))
    reason = old.get("reason") or old.get("blocking_reason") or "Migrated legacy human_signoff.json."
    if isinstance(reason, list):
        reason = "; ".join(str(item) for item in reason)
    signoff = build_signoff_from_decision(
        stage,
        decision,
        reason=str(reason),
        signed_by=str(old.get("signed_by") or "wangjiahua"),
        signed_via="migrate_human_signoff.py",
    )
    target = write_signoff(stage, signoff)
    history = stage / ".loop" / "human_signoff_history"
    history.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().replace(":", "").replace("-", "")
    shutil.copy2(legacy, history / f"{stamp}_legacy_human_signoff.json")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy .loop/human_signoff.json to .loop/human_signoff.yaml.")
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    print(migrate(Path(args.stage)))


if __name__ == "__main__":
    main()
