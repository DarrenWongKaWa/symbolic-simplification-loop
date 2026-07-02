from __future__ import annotations

import shutil
from pathlib import Path

from .config import REPO_ROOT, write_text
from .executor import initialize_stage_files
from .planner import CONDUCTIVITY_STAGES, write_default_stage_plan


PROJECT_DIRS = [
    "raw",
    "stages",
    "checkpoints",
    "review_packets",
    "review_results",
    "reports",
    "validation",
    "supplements",
]


def init_project(root: Path, name: str, from_sigma_abc_template: bool = False) -> Path:
    project = root / name
    if project.exists():
        raise FileExistsError(project)
    project.mkdir(parents=True)
    for folder in PROJECT_DIRS:
        (project / folder).mkdir()

    write_text(project / "README.md", f"# {name}\n\nSymbolic simplification loop project.\n")
    write_text(project / "AGENTS.md", (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"))

    brief_source = REPO_ROOT / "templates" / "HUMAN_TASK_BRIEF.template.md"
    if from_sigma_abc_template:
        brief_source = REPO_ROOT / "examples" / "sigma_abc_template" / "HUMAN_TASK_BRIEF.md"
    shutil.copy2(brief_source, project / "HUMAN_TASK_BRIEF.md")
    return project


def init_stage(project: Path, stage_name: str, goal: str = "TBD") -> Path:
    stage = project / "stages" / stage_name
    if stage.exists():
        raise FileExistsError(stage)
    initialize_stage_files(stage)
    write_default_stage_plan(stage, goal=goal)
    return stage


def write_expected_conductivity_stages(path: Path) -> None:
    lines = ["# Expected Conductivity Stages", ""]
    lines.extend(f"- `{stage}`" for stage in CONDUCTIVITY_STAGES)
    write_text(path, "\n".join(lines) + "\n")

