from __future__ import annotations

from pathlib import Path


def hard_stop_reasons(stage: Path) -> list[str]:
    reasons: list[str] = []
    if (stage / "STOP").exists():
        reasons.append("STOP file exists")
    loop_dir = stage / ".loop"
    if (loop_dir / "protected_regression_failed").exists():
        reasons.append("protected regression failed")
    if (loop_dir / "human_approval_required").exists():
        reasons.append("human approval required")
    return reasons


def assert_no_hard_stop(stage: Path) -> None:
    reasons = hard_stop_reasons(stage)
    if reasons:
        raise RuntimeError("; ".join(reasons))

