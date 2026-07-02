from __future__ import annotations

from pathlib import Path

from .executor import initialize_stage_files
from .planner import write_default_stage_plan


def open_next_stage(project: Path, stage_name: str, goal: str = "TBD") -> Path:
    stage = project / "stages" / stage_name
    if stage.exists():
        raise FileExistsError(stage)
    initialize_stage_files(stage)
    write_default_stage_plan(stage, goal=goal)
    return stage

