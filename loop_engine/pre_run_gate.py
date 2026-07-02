from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import read_json, write_json
from .pre_run_brief import DC_CAVEAT, audit_pre_run_brief
from .schemas import validate_with_schema


def _profile_id(profile: dict[str, Any] | None) -> str:
    return str((profile or {}).get("profile") or (profile or {}).get("id") or "unknown_profile")


def _profile_forbidden(profile: dict[str, Any] | None) -> list[str]:
    profile = profile or {}
    out = list(profile.get("forbidden_actions", []) or [])
    autonomy = profile.get("autonomy", {}) or {}
    if not autonomy.get("allow_ibp_reduction", False):
        out.append("IBP")
    if not autonomy.get("allow_physics_simplification", False):
        out.append("full tensorial sigma_abc correctness claim")
    out.extend(["total derivative reduction", "candidate promotion"])
    return sorted(dict.fromkeys(str(item) for item in out if item))


def _covers(available: list[str], required: list[str]) -> bool:
    available_text = "\n".join(available).lower()
    return all(str(item).lower() in available_text for item in required)


def check_pre_run_gate(stage: Path, *, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    path = stage / ".loop" / "pre_run_brief.json"
    blocking: list[str] = []
    warnings: list[str] = []
    brief = None
    if not path.exists():
        blocking.append("pre_run_brief.json is required before execution")
    else:
        brief = read_json(path)
        try:
            validate_with_schema(brief, "pre_run_brief")
        except Exception as exc:
            blocking.append(f"pre_run_brief schema invalid: {exc}")
    if brief is not None:
        if brief.get("stage_id") != stage.name:
            blocking.append(f"pre_run_brief stage_id mismatch: {brief.get('stage_id')} != {stage.name}")
        expected_profile = _profile_id(profile)
        if expected_profile != "unknown_profile" and brief.get("profile_id") not in {expected_profile, None, "unknown_profile"}:
            blocking.append(f"pre_run_brief profile_id mismatch: {brief.get('profile_id')} != {expected_profile}")
        task = brief.get("task_understanding", {})
        if not task.get("claim_boundary_acknowledged"):
            blocking.append("claim_boundary_acknowledged must be true")
        caveats = task.get("caveats_acknowledged", [])
        if not any("DCProjectionTo1D" in str(caveat) for caveat in caveats):
            blocking.append(DC_CAVEAT)
        if not _covers(task.get("forbidden_actions", []), _profile_forbidden(profile)):
            blocking.append("pre_run_brief missing one or more profile-forbidden actions")
        audit = audit_pre_run_brief(stage, brief, profile=profile)
        warnings.extend(audit.get("warnings", []))
        if audit.get("hard_stop"):
            blocking.extend(audit.get("blocking_reasons", []))
    result = {
        "stage_id": stage.name,
        "profile_id": _profile_id(profile),
        "gate": "FAIL" if blocking else ("WARN" if warnings else "PASS"),
        "execution_allowed": not blocking,
        "blocking_reasons": blocking,
        "warnings": warnings,
        "reviewer_consulted": False,
    }
    validate_with_schema(result, "pre_run_gate_result")
    write_json(stage / ".loop" / "pre_run_gate_result.json", result)
    return result
