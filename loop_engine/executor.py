from __future__ import annotations

from pathlib import Path

from .config import write_json, write_text
from .state import StageStatus


def initialize_stage_files(stage: Path) -> None:
    for folder in ["input_snapshots", "scripts", "output", "validation", "reports", ".loop"]:
        (stage / folder).mkdir(parents=True, exist_ok=True)

    if not (stage / "EXECUTION_REPORT.md").exists():
        write_text(stage / "EXECUTION_REPORT.md", f"# Execution Report\n\n## Stage Name\n\n`{stage.name}`\n")
    if not (stage / "CLAIM_BOUNDARY.md").exists():
        write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n## Allowed Claims\n\n- Stage-local validated claims only.\n\n## Forbidden Claims\n\n- Unvalidated scientific success.\n")
    write_json(stage / ".loop" / "state.json", {"stage_name": stage.name, "status": StageStatus.READY_TO_EXECUTE})

