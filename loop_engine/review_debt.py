from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import read_json, utc_now, write_json
from .decision import decide_next_action
from .schemas import validate_with_schema

RUNTIME_LIMIT_MARKERS = (
    "AGENT_RUNTIME_QUOTA_EXHAUSTED",
    "AGENT_RUNTIME_TIMEOUT",
    "AGENT_QUOTA_LIMIT",
    "AGENT_TIMEOUT",
    "AGENT_NO_OUTPUT",
    "usage limit",
    "quota",
    "timed out",
    "no output",
)

DEFAULT_BLOCKING_BEFORE = [
    "candidate_promotion",
    "global_pre_ibp_assembly",
    "ibp",
    "paper_claim",
    "full_tensorial_correctness_claim",
]

PROMOTION_STAGE_MARKERS = (
    "012c",
    "candidate_promotion",
    "canonicalization_promotion",
    "promotion",
)

PREPARATION_ONLY_STAGE_MARKERS = (
    "real_loop_candidate_preparation",
    "loop_candidate_preparation",
    "candidate_preparation",
)

GLOBAL_ASSEMBLY_MARKERS = (
    "013",
    "global_pre_ibp_assembly",
    "global_assembly",
)

IBP_MARKERS = ("ibp", "total_derivative", "total-derivative")


def _review_runtime_limited(review: dict[str, Any]) -> bool:
    fields = []
    for key in ["blocking_issues", "nonblocking_caveats", "patch_instructions"]:
        fields.extend(str(item) for item in review.get(key, []) or [])
    text = "\n".join(fields).lower()
    return any(marker.lower() in text for marker in RUNTIME_LIMIT_MARKERS)


def _first_runtime_marker(review: dict[str, Any]) -> str:
    for key in ["blocking_issues", "nonblocking_caveats", "patch_instructions"]:
        for raw in review.get(key, []) or []:
            text = str(raw)
            lowered = text.lower()
            for marker in RUNTIME_LIMIT_MARKERS:
                if marker.lower() in lowered:
                    return text
    return "AGENT_RUNTIME_LIMIT"


def _stage_blocks(validation: dict[str, Any]) -> list[str]:
    blocks: list[str] = []
    if validation.get("NewSymbolicCandidatePromoted") or validation.get("new_symbolic_candidate_promoted"):
        blocks.append("new symbolic candidate promoted")
    if not validation.get("NoKernelFusionStarted", True):
        blocks.append("kernel fusion started")
    if validation.get("LoopOrbitCanonicalizationPromoted"):
        blocks.append("loop orbit canonicalization promoted")
    if validation.get("GlobalAssemblyStarted"):
        blocks.append("global assembly started")
    if not validation.get("NoIBPStarted", True):
        blocks.append("IBP started")
    if not validation.get("NoTotalDerivativeIntroduced", True):
        blocks.append("total derivative introduced")
    if not validation.get("NoFullTensorialClaim", True):
        blocks.append("full tensorial claim present")
    if validation.get("ProtectedBenchmarksUnchanged") is False:
        blocks.append("protected benchmarks changed")
    if validation.get("Stage001DCCaveatPreserved") is False:
        blocks.append("DC caveat not preserved")
    return blocks


def review_debt_allowed(stage: Path, profile: dict[str, Any]) -> tuple[bool, list[str]]:
    validation = read_json(stage / ".loop" / "validation_summary.json")
    review = read_json(stage / ".loop" / "review_result.json")
    risk = read_json(stage / ".loop" / "risk_classification.json") if (stage / ".loop" / "risk_classification.json").exists() else {}
    cfg = profile.get("review_debt", {}) or {}
    reasons: list[str] = []
    if validation.get("overall_gate") != "PASS":
        reasons.append("validation_summary.overall_gate is not PASS")
    if risk.get("risk_level") not in {"LOW", "MEDIUM"}:
        reasons.append(f"risk level {risk.get('risk_level')!r} is not LOW/MEDIUM")
    if risk.get("review_lane") not in {"L0_DETERMINISTIC", "L1_COMPACT_META"}:
        reasons.append(f"review lane {risk.get('review_lane')!r} is not L0/L1")
    if risk.get("review_lane") == "L1_COMPACT_META" and not cfg.get("allow_l1_quota_debt", False):
        reasons.append("profile does not allow L1 quota debt")
    if not cfg.get("allow_low_risk_advance", False):
        reasons.append("profile does not allow low-risk advance")
    if not _review_runtime_limited(review):
        reasons.append("review did not fail only because quota/runtime limit")
    reasons.extend(_stage_blocks(validation))
    return not reasons, reasons


def _ledger_path(stage: Path) -> Path:
    return stage / ".loop" / "review_debt_ledger.jsonl"


def _append_ledger(stage: Path, entry: dict[str, Any]) -> None:
    path = _ledger_path(stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def create_review_debt_if_allowed(stage: Path, profile: dict[str, Any]) -> dict[str, Any]:
    validation = read_json(stage / ".loop" / "validation_summary.json")
    review = read_json(stage / ".loop" / "review_result.json")
    risk = read_json(stage / ".loop" / "risk_classification.json") if (stage / ".loop" / "risk_classification.json").exists() else {}
    allowed, reasons = review_debt_allowed(stage, profile)
    cfg = profile.get("review_debt", {}) or {}
    blocking_before = list(cfg.get("blocking_before", DEFAULT_BLOCKING_BEFORE)) or DEFAULT_BLOCKING_BEFORE
    status = "OPEN" if allowed else "BLOCKING"
    reason = _first_runtime_marker(review) if allowed else "; ".join(reasons)
    entry = {
        "stage_id": stage.name,
        "stage_status": "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT" if allowed else "REVIEW_DEBT_BLOCKED",
        "status": status,
        "reason": reason,
        "risk_level": risk.get("risk_level"),
        "review_lane": risk.get("review_lane"),
        "allowed_to_advance": bool(allowed),
        "review_debt": bool(allowed),
        "OrdinaryReviewComplete": False,
        "CheckpointStatus": "PROVISIONAL_WITH_REVIEW_DEBT" if allowed else "NOT_FROZEN",
        "ExecutorRerunRequired": False,
        "VerifierRerunRequired": False,
        "blocking_before": blocking_before,
        "required_resume_command": "python3 scripts/resume_pending_reviews.py --project sigma_abc --from-pending",
        "created_at": utc_now(),
        "validation_gate": validation.get("overall_gate"),
        "pass_as": "center-sector row-provenance conservation checkpoint" if "011" in stage.name else "low-risk provenance checkpoint",
        "not_pass_as": [
            "center-sector fused physical kernel formula",
            "full tensorial sigma_abc correctness",
        ],
        "CenterFusionDifference": validation.get("CenterFusionDifference"),
        "XXXCenterProjectionRegression": validation.get("XXXCenterProjectionRegression"),
    }
    validate_with_schema(entry, "review_debt")
    write_json(stage / ".loop" / "review_debt.json", entry)
    _append_ledger(stage, entry)
    decision = {
        "action": entry["stage_status"],
        "reason": entry["reason"],
        "freeze_allowed": bool(allowed),
        "provisional": bool(allowed),
        "review_debt": bool(allowed),
        "ReviewDebt": "OPEN" if allowed else "BLOCKING",
        "OrdinaryReviewComplete": False,
        "CheckpointStatus": entry["CheckpointStatus"],
        "ExecutorRerunRequired": False,
        "VerifierRerunRequired": False,
        "allowed_to_advance": bool(allowed),
        "patch_required": False,
        "PatchRequired": False,
    }
    write_json(stage / ".loop" / "decision.json", decision)
    write_json(stage / "decision.json", decision)
    return entry


def iter_open_review_debts(run_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(run_root.glob("stages/*/.loop/review_debt.json")):
        data = read_json(path)
        if data.get("status") == "OPEN":
            data.setdefault("stage_path", str(path.parents[1]))
            entries.append(data)
    for path in sorted(run_root.glob("*/.loop/review_debt.json")):
        data = read_json(path)
        if data.get("status") == "OPEN":
            data.setdefault("stage_path", str(path.parents[1]))
            entries.append(data)
    unique: dict[str, dict[str, Any]] = {entry["stage_id"]: entry for entry in entries}
    return list(unique.values())


def _iter_unsettled_review_debts(run_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(run_root.glob("stages/*/.loop/review_debt.json")):
        data = read_json(path)
        if data.get("status") in {"OPEN", "BLOCKING"}:
            data.setdefault("stage_path", str(path.parents[1]))
            entries.append(data)
    for path in sorted(run_root.glob("*/.loop/review_debt.json")):
        data = read_json(path)
        if data.get("status") in {"OPEN", "BLOCKING"}:
            data.setdefault("stage_path", str(path.parents[1]))
            entries.append(data)
    unique: dict[str, dict[str, Any]] = {entry["stage_id"]: entry for entry in entries}
    return list(unique.values())


def downstream_blocked_by_review_debt(run_root: Path, stage_id: str) -> dict[str, Any]:
    debts = _iter_unsettled_review_debts(run_root)
    if not debts:
        return {"blocked": False, "reason": "no open review debt", "open_review_debts": []}
    lowered = stage_id.lower()
    preparation_only = any(marker in lowered for marker in PREPARATION_ONLY_STAGE_MARKERS)
    reason = None
    if any(marker in lowered for marker in GLOBAL_ASSEMBLY_MARKERS):
        reason = "global_pre_ibp_assembly blocked by open review debt"
    elif not preparation_only and any(marker in lowered for marker in PROMOTION_STAGE_MARKERS):
        reason = "candidate_promotion blocked by open review debt"
    elif any(marker in lowered for marker in IBP_MARKERS):
        reason = "ibp blocked by open review debt"
    if reason:
        return {"blocked": True, "reason": reason, "open_review_debts": [entry["stage_id"] for entry in debts]}
    return {"blocked": False, "reason": "stage may run with open review debt", "open_review_debts": [entry["stage_id"] for entry in debts]}


def settle_review_debt(run_root: Path, stage_id: str | None = None) -> dict[str, Any]:
    candidates = []
    for path in sorted(run_root.glob("stages/*/.loop/review_debt.json")):
        candidates.append(path)
    for path in sorted(run_root.glob("*/.loop/review_debt.json")):
        candidates.append(path)
    settled: list[dict[str, Any]] = []
    for debt_path in candidates:
        stage = debt_path.parents[1]
        debt = read_json(debt_path)
        if stage_id and debt.get("stage_id") != stage_id:
            continue
        if debt.get("status") != "OPEN":
            continue
        review = read_json(stage / ".loop" / "review_result.json")
        validation = read_json(stage / ".loop" / "validation_summary.json")
        if review.get("verdict") in {"PASS", "PASS_WITH_CAVEAT"} and validation.get("overall_gate") == "PASS":
            debt["status"] = "SETTLED"
            debt["stage_status"] = "REVIEW_DEBT_SETTLED"
            debt["allowed_to_advance"] = True
            debt["CheckpointStatus"] = "FROZEN_WITH_CAVEAT"
            debt["settled_at"] = utc_now()
            decision = {
                "action": "REVIEW_DEBT_SETTLED",
                "reason": "review debt settled by PASS/PASS_WITH_CAVEAT review",
                "freeze_allowed": True,
                "review_debt": False,
                "patch_required": False,
            }
        elif _review_runtime_limited(review):
            debt["stage_status"] = "PENDING_REVIEW_RESUME"
            debt["allowed_to_advance"] = False
            debt["CheckpointStatus"] = "PENDING_REVIEW_RESUME"
            debt["last_settle_attempt_at"] = utc_now()
            decision = {
                "action": "REVIEW_DEBT_REQUIRES_RESUME",
                "reason": "review_result contains only reviewer runtime/timeout failure; resume review before settling debt",
                "freeze_allowed": False,
                "review_debt": True,
                "patch_required": False,
                "recommended_command": "python3 scripts/resume_pending_reviews.py --project sigma_abc --from-pending",
            }
        else:
            debt["status"] = "BLOCKING"
            debt["stage_status"] = "REVIEW_DEBT_BLOCKING"
            debt["allowed_to_advance"] = False
            debt["CheckpointStatus"] = "REVIEW_DEBT_BLOCKING"
            debt["settled_at"] = utc_now()
            decision = {
                "action": "REVIEW_INVALIDATED_DEPENDENCY",
                "reason": "review debt settlement failed; downstream provisional dependencies invalidated",
                "freeze_allowed": False,
                "review_debt": True,
                "patch_required": True,
            }
        validate_with_schema(debt, "review_debt")
        write_json(debt_path, debt)
        _append_ledger(stage, debt)
        write_json(stage / ".loop" / "decision.json", decision)
        write_json(stage / "decision.json", decision)
        settled.append(
            {
                "stage_id": debt["stage_id"],
                "status": debt.get("stage_status") if decision["action"] == "REVIEW_DEBT_REQUIRES_RESUME" else debt["status"],
                "decision": decision["action"],
                "recommended_command": decision.get("recommended_command"),
            }
        )
    if stage_id and len(settled) == 1:
        return settled[0]
    return {"settled": settled, "count": len(settled)}
