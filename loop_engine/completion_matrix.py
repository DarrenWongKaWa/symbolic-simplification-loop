from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .config import read_json, read_text, utc_now, write_json, write_text
from .schemas import validate_with_schema


BASIS = {
    "stage_plan": "STAGE_PLAN.md",
    "validation_summary": ".loop/validation_summary.json",
    "review_result": ".loop/review_result.json",
    "claim_boundary": "CLAIM_BOUNDARY.md",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _basis_hashes(stage: Path, basis: dict[str, str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key, rel in basis.items():
        path = stage / rel
        hashes[key] = _sha256(path) if path.exists() else "MISSING"
    return hashes


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    return read_json(path) if path.exists() else {}


def _status_from_gate(gate: Any) -> str:
    gate_text = str(gate).upper()
    table = {
        "PASS": "DONE",
        "PASS_WITH_CAVEAT": "DONE_WITH_CAVEAT",
        "REGISTERED": "REGISTERED",
        "REGISTERED_NOT_RUN": "REGISTERED",
        "INHERITED_PASS": "REGISTERED",
        "INHERITED": "REGISTERED",
        "FAIL": "FAILED",
        "MISSING": "MISSING",
        "BLOCKED": "BLOCKED",
    }
    return table.get(gate_text, "MISSING")


def _category_for_check(name: str) -> str:
    lowered = name.lower()
    if "artifact" in lowered or "ledger" in lowered or "dependency" in lowered:
        return "dependency"
    if "caveat" in lowered or "overclaim" in lowered or "ibp" in lowered or "totalderivative" in lowered:
        return "boundary"
    if "regression" in lowered or "projection" in lowered:
        return "protected_regression"
    return "validation"


def _plan_expected_outputs(plan_text: str) -> list[str]:
    outputs: list[str] = []
    in_expected = False
    for line in plan_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("expected_outputs"):
            in_expected = True
            continue
        if in_expected and stripped.startswith("-"):
            item = stripped.removeprefix("-").strip().strip("`")
            if item:
                outputs.append(item)
            continue
        if in_expected and stripped and not line.startswith((" ", "\t")):
            in_expected = False
    return outputs


def _plan_completion_items(plan_text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    in_plan = False
    current: dict[str, Any] = {}
    for line in plan_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("completion_plan"):
            in_plan = True
            continue
        if not in_plan:
            continue
        if stripped.startswith("- id:"):
            if current.get("id"):
                items.append(current)
            current = {"id": stripped.split(":", 1)[1].strip()}
            continue
        if current and re.match(r"^[A-Za-z_]+:", stripped):
            key, value = stripped.split(":", 1)
            current[key.strip()] = value.strip()
    if current.get("id"):
        items.append(current)
    return items


def _boundary_audit(stage: Path, validation: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    validation_boundary = validation.get("boundary_audit", {}) or {}
    review_boundary = review.get("boundary_audit", {}) or {}
    boundary = {**validation_boundary, **review_boundary}
    math_status = review.get("mathematical_status", {}) or {}
    if "overclaim_detected" not in boundary and "overclaim_detected" in math_status:
        boundary["overclaim_detected"] = math_status.get("overclaim_detected")
    packet = read_text(stage / "review_packet.md") + "\n" + read_text(stage / "CLAIM_BOUNDARY.md")
    boundary.setdefault("overclaim_detected", False)
    boundary.setdefault("full_tensorial_claim_detected", "full tensorial sigma_abc correctness" in packet.lower())
    boundary.setdefault("ibp_started_without_approval", False)
    boundary.setdefault("dc_caveat_preserved", True)
    for key in ["overclaim_detected", "full_tensorial_claim_detected", "ibp_started_without_approval"]:
        boundary[key] = bool(validation_boundary.get(key) or review_boundary.get(key) or boundary.get(key))
    if validation_boundary.get("dc_caveat_preserved") is False or review_boundary.get("dc_caveat_preserved") is False:
        boundary["dc_caveat_preserved"] = False
    return boundary


def _build_recommended_action(items: list[dict[str, Any]], boundary: dict[str, Any], validation: dict[str, Any], review: dict[str, Any]) -> str:
    unsafe = any(
        boundary.get(key)
        for key in ["overclaim_detected", "full_tensorial_claim_detected", "ibp_started_without_approval"]
    ) or boundary.get("dc_caveat_preserved") is False
    if unsafe:
        return "REJECT_AND_STOP"
    blocking_bad = [item for item in items if item.get("blocking") and item.get("status") in {"MISSING", "FAILED", "BLOCKED"}]
    if blocking_bad or validation.get("overall_gate") != "PASS" or review.get("verdict") not in {"PASS", "PASS_WITH_CAVEAT"}:
        return "DO_NOT_FREEZE_PATCH"
    caveats = [*validation.get("caveats", []), *review.get("nonblocking_caveats", [])]
    return "APPROVE_FREEZE_WITH_CAVEAT" if caveats else "APPROVE_FREEZE"


def _overall_completion(items: list[dict[str, Any]], validation: dict[str, Any], boundary: dict[str, Any]) -> str:
    if any(boundary.get(key) for key in ["overclaim_detected", "full_tensorial_claim_detected", "ibp_started_without_approval"]) or boundary.get("dc_caveat_preserved") is False:
        return "FAILED"
    statuses = {item.get("status") for item in items if item.get("blocking")}
    if "FAILED" in statuses or validation.get("overall_gate") == "FAIL":
        return "FAILED"
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if "MISSING" in statuses:
        return "INCOMPLETE"
    return "COMPLETE"


def build_completion_matrix(stage: Path, profile: dict | None = None) -> dict[str, Any]:
    validation = _read_json_if_exists(stage / ".loop" / "validation_summary.json")
    review = _read_json_if_exists(stage / ".loop" / "review_result.json")
    plan_text = read_text(stage / "STAGE_PLAN.md")
    items: list[dict[str, Any]] = []

    for check in validation.get("checks", []):
        name = str(check.get("name") or check.get("id") or "unnamed_check")
        status = _status_from_gate(check.get("gate", check.get("status")))
        items.append(
            {
                "id": name,
                "category": _category_for_check(name),
                "description": str(check.get("description") or name),
                "expected_from": ".loop/validation_summary.json",
                "actual_evidence": f"actual={check.get('actual')} gate={check.get('gate')}",
                "status": status,
                "blocking": status in {"MISSING", "FAILED", "BLOCKED"} and status != "REGISTERED",
            }
        )

    for regression in validation.get("protected_regressions", []):
        name = str(regression.get("name") or regression.get("id") or "protected_regression")
        status = "REGISTERED" if str(regression.get("status", regression.get("gate", "REGISTERED"))).upper() == "REGISTERED" else _status_from_gate(regression.get("gate", regression.get("status")))
        items.append(
            {
                "id": name,
                "category": "protected_regression",
                "description": f"Protected regression {name}",
                "expected_from": ".loop/validation_summary.json::protected_regressions",
                "actual_evidence": str(regression),
                "status": status,
                "blocking": status in {"FAILED", "MISSING", "BLOCKED"},
            }
        )

    for rel in _plan_expected_outputs(plan_text):
        exists = (stage / rel).exists()
        items.append(
            {
                "id": f"output:{rel}",
                "category": "output_file",
                "description": f"Expected output `{rel}` exists.",
                "expected_from": "STAGE_PLAN.md::expected_outputs",
                "actual_evidence": rel if exists else "missing",
                "status": "DONE" if exists else "MISSING",
                "blocking": not exists,
            }
        )

    present_ids = {item["id"] for item in items}
    for item in _plan_completion_items(plan_text):
        item_id = str(item.get("id"))
        if item_id in present_ids:
            continue
        items.append(
            {
                "id": item_id,
                "category": item.get("category", "custom") if item.get("category") in {"dependency", "boundary", "validation", "scientific_caveat", "review_evidence", "output_file", "protected_regression", "custom"} else "custom",
                "description": item.get("description", item_id),
                "expected_from": "STAGE_PLAN.md::completion_plan",
                "actual_evidence": "not found in validation_summary",
                "status": "MISSING",
                "blocking": True,
            }
        )

    boundary = _boundary_audit(stage, validation, review)
    recommended = _build_recommended_action(items, boundary, validation, review)
    overall = _overall_completion(items, validation, boundary)
    matrix = {
        "stage_id": stage.name,
        "overall_completion": overall,
        "freeze_eligible": overall == "COMPLETE" and recommended in {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT"},
        "generated_at": utc_now(),
        "basis": BASIS.copy(),
        "basis_hashes": _basis_hashes(stage, BASIS),
        "items": items,
        "boundary_audit": boundary,
        "recommended_human_action": recommended,
    }
    validate_with_schema(matrix, "completion_matrix")
    return matrix


def render_completion_matrix_md(matrix: dict[str, Any]) -> str:
    blocking = [item for item in matrix.get("items", []) if item.get("blocking") and item.get("status") in {"MISSING", "FAILED", "BLOCKED"}]
    passed_boundary = [item for item in matrix.get("items", []) if item.get("category") == "boundary" and item.get("status") == "DONE"]

    def table(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "| Item | Category | Status | Evidence |\n|---|---|---|---|\n| none | - | - | - |"
        body = "\n".join(
            f"| {item.get('id')} | {item.get('category')} | {item.get('status')} | {str(item.get('actual_evidence', '')).replace('|', '/')} |"
            for item in rows
        )
        return "| Item | Category | Status | Evidence |\n|---|---|---|---|\n" + body

    boundary_rows = "\n".join(f"| {key} | {value} |" for key, value in sorted(matrix.get("boundary_audit", {}).items()))
    return f"""# Completion Matrix: {matrix.get('stage_id')}

## Overall

- Overall completion: {matrix.get('overall_completion')}
- Evidence-level freeze eligible: {'YES' if matrix.get('freeze_eligible') else 'NO'}
- Recommended human action: {matrix.get('recommended_human_action')}

## Blocking / missing items

{table(blocking)}

## Passed boundary checks

{table(passed_boundary)}

## Boundary audit

| Field | Value |
|---|---|
{boundary_rows or '| none | - |'}

## Scientific interpretation

Incomplete dependency/readiness items should be patched before freeze. Boundary audit failures are separate hard-safety findings and cannot be overridden by human signoff.

## Recommended signoff

{matrix.get('recommended_human_action')}
"""


def write_completion_matrix(stage: Path, profile: dict | None = None) -> Path:
    matrix = build_completion_matrix(stage, profile=profile)
    reports = stage / "reports"
    write_json(reports / "completion_matrix.json", matrix)
    write_text(reports / "completion_matrix.md", render_completion_matrix_md(matrix))
    return reports / "completion_matrix.json"


def load_completion_matrix(stage: Path) -> dict[str, Any] | None:
    path = stage / "reports" / "completion_matrix.json"
    return read_json(path) if path.exists() else None


def validate_completion_matrix_freshness(stage: Path, matrix: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for key, rel in (matrix.get("basis") or {}).items():
        path = stage / rel
        expected = (matrix.get("basis_hashes") or {}).get(key)
        actual = _sha256(path) if path.exists() else "MISSING"
        if expected != actual:
            reasons.append(f"{rel} hash changed: expected {expected}, actual {actual}")
    return not reasons, reasons
