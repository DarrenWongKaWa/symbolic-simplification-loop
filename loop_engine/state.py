from __future__ import annotations

from enum import StrEnum
from pathlib import Path


class StageStatus(StrEnum):
    DRAFT_PLAN = "DRAFT_PLAN"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    EXECUTING = "EXECUTING"
    VALIDATING = "VALIDATING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    NEEDS_PATCH = "NEEDS_PATCH"
    PASS_CHECKPOINT = "PASS_CHECKPOINT"
    PASS_WITH_CAVEAT = "PASS_WITH_CAVEAT"
    FAILED = "FAILED"
    FROZEN = "FROZEN"


FREEZABLE_REVIEW_VERDICTS = {"PASS", "PASS_WITH_CAVEAT"}


LEGAL_TRANSITIONS = {
    StageStatus.DRAFT_PLAN: {StageStatus.READY_TO_EXECUTE},
    StageStatus.READY_TO_EXECUTE: {StageStatus.EXECUTING},
    StageStatus.EXECUTING: {StageStatus.VALIDATING, StageStatus.FAILED},
    StageStatus.VALIDATING: {StageStatus.READY_FOR_REVIEW, StageStatus.NEEDS_PATCH, StageStatus.FAILED},
    StageStatus.READY_FOR_REVIEW: {StageStatus.UNDER_REVIEW},
    StageStatus.UNDER_REVIEW: {
        StageStatus.NEEDS_PATCH,
        StageStatus.PASS_CHECKPOINT,
        StageStatus.PASS_WITH_CAVEAT,
        StageStatus.FAILED,
    },
    StageStatus.NEEDS_PATCH: {StageStatus.READY_TO_EXECUTE, StageStatus.FAILED},
    StageStatus.PASS_CHECKPOINT: {StageStatus.FROZEN},
    StageStatus.PASS_WITH_CAVEAT: {StageStatus.FROZEN},
    StageStatus.FAILED: set(),
    StageStatus.FROZEN: set(),
}


def can_transition(current: StageStatus | str, target: StageStatus | str) -> bool:
    current_status = StageStatus(current)
    target_status = StageStatus(target)
    return target_status in LEGAL_TRANSITIONS[current_status]


def stage_loop_dir(stage: Path) -> Path:
    return stage / ".loop"


def freeze_preconditions(stage: Path, validation: dict, review: dict) -> list[str]:
    from .completion_matrix import load_completion_matrix, validate_completion_matrix_freshness
    from .human_signoff import load_signoff, validate_signoff_freshness

    missing: list[str] = []
    if validation.get("overall_gate") != "PASS":
        missing.append("validation_summary.overall_gate must be PASS")
    if review.get("verdict") not in FREEZABLE_REVIEW_VERDICTS:
        missing.append("review_result.verdict must be PASS or PASS_WITH_CAVEAT")
    if not (stage / "CLAIM_BOUNDARY.md").exists():
        missing.append("CLAIM_BOUNDARY.md is required")

    traceability_path = stage / ".loop" / "identity_traceability.json"
    if traceability_path.exists():
        from .config import read_json

        traceability = read_json(traceability_path)
        if traceability.get("identity_traceability_gate") != "PASS":
            failures = ", ".join(traceability.get("blocking_failures", []))
            missing.append(f"identity_traceability gate must be PASS: {failures}")

    matrix = load_completion_matrix(stage)
    if matrix is None:
        missing.append("reports/completion_matrix.json is required before freezing")
    else:
        fresh, reasons = validate_completion_matrix_freshness(stage, matrix)
        missing.extend(f"stale completion_matrix: {reason}" for reason in reasons if not fresh)
        boundary = matrix.get("boundary_audit", {})
        if boundary.get("overclaim_detected"):
            missing.append("completion_matrix.boundary_audit.overclaim_detected is true")
        if boundary.get("full_tensorial_claim_detected"):
            missing.append("completion_matrix.boundary_audit.full_tensorial_claim_detected is true")
        if boundary.get("ibp_started_without_approval"):
            missing.append("completion_matrix.boundary_audit.ibp_started_without_approval is true")
        if boundary.get("dc_caveat_preserved") is False:
            missing.append("completion_matrix.boundary_audit.dc_caveat_preserved must be true")
        blocking_bad = [
            item for item in matrix.get("items", [])
            if item.get("blocking") and item.get("status") in {"MISSING", "FAILED", "BLOCKED"}
        ]
        if blocking_bad:
            ids = ", ".join(str(item.get("id", "<unknown>")) for item in blocking_bad)
            missing.append(f"completion_matrix has blocking incomplete items: {ids}")

    signoff = load_signoff(stage)
    if signoff is None:
        missing.append("human_signoff.yaml is required before freezing")
        return missing

    fresh, reasons = validate_signoff_freshness(stage, signoff)
    missing.extend(f"stale human_signoff: {reason}" for reason in reasons if not fresh)

    decision = signoff.get("decision")
    if decision not in {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT"}:
        missing.append(f"human_signoff.decision blocks freeze: got {decision!r}")
    permission = signoff.get("permission", {})
    if not permission.get("freeze_checkpoint"):
        missing.append("human_signoff.permission.freeze_checkpoint must be true")
    judgment = signoff.get("human_scientific_judgment", {})
    if not judgment.get("completion_understood"):
        missing.append("human_signoff.human_scientific_judgment.completion_understood must be true")
    if not judgment.get("boundary_audit_understood"):
        missing.append("human_signoff.human_scientific_judgment.boundary_audit_understood must be true")
    if not judgment.get("caveats_understood"):
        missing.append("human_signoff.human_scientific_judgment.caveats_understood must be true")
    if decision == "APPROVE_FREEZE_WITH_CAVEAT" and not signoff.get("accepted_caveats"):
        missing.append("APPROVE_FREEZE_WITH_CAVEAT requires non-empty accepted_caveats")
    return missing
