from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from loop_engine.checkpoint import build_checkpoint_manifest
from loop_engine.config import read_json, write_json, write_text
from loop_engine.schemas import schema_path, validate_with_schema
from loop_engine.state import freeze_preconditions


REPO_ROOT = Path(__file__).resolve().parents[1]
DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


def _review(verdict: str = "PASS") -> dict:
    return {
        "verdict": verdict,
        "stage_name": "sigma_abc_012c_real_loop_candidate_preparation",
        "reviewer_role": "IntegratorReview",
        "review_scope": "routine_branch",
        "mathematical_status": {
            "exact_reconstruction": verdict in {"PASS", "PASS_WITH_CAVEAT"},
            "simplification_real": True,
            "regression_preserved": True,
            "overclaim_detected": False,
        },
        "blocking_issues": [] if verdict in {"PASS", "PASS_WITH_CAVEAT"} else ["review failed"],
        "nonblocking_caveats": [DC_CAVEAT],
        "allowed_claims": ["PASS as preparation gate only."],
        "forbidden_claims": ["Do not claim full tensorial sigma_abc correctness."],
        "next_action": "FREEZE",
        "suggested_next_stage": None,
        "patch_instructions": [],
    }


def _validation(*, gate: str = "PASS", ready: bool = True) -> dict:
    checks = [
        {"name": "NoIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
        {"name": "NoTotalDerivativeIntroduced", "expected": True, "actual": True, "gate": "PASS"},
        {"name": "NoCandidatePromoted", "expected": True, "actual": True, "gate": "PASS"},
        {"name": "DCProjectionCaveatPreserved", "expected": True, "actual": True, "gate": "PASS"},
    ]
    if ready:
        checks.extend(
            [
                {"name": "Stage012AArtifactPresent", "expected": True, "actual": True, "gate": "PASS"},
                {"name": "Stage012BArtifactPresent", "expected": True, "actual": True, "gate": "PASS"},
                {"name": "UsesStage012ALoopLedger", "expected": True, "actual": True, "gate": "PASS"},
                {"name": "UsesStage012BHypothesisLedger", "expected": True, "actual": True, "gate": "PASS"},
                {"name": "RealLoopCandidateReady", "expected": True, "actual": True, "gate": "PASS"},
            ]
        )
    else:
        checks.extend(
            [
                {"name": "Stage012AArtifactPresent", "expected": True, "actual": False, "gate": "FAIL"},
                {"name": "Stage012BArtifactPresent", "expected": True, "actual": False, "gate": "FAIL"},
                {"name": "UsesStage012ALoopLedger", "expected": True, "actual": False, "gate": "FAIL"},
                {"name": "UsesStage012BHypothesisLedger", "expected": True, "actual": False, "gate": "FAIL"},
                {"name": "RealLoopCandidateReady", "expected": True, "actual": False, "gate": "FAIL"},
            ]
        )
    return {
        "stage_name": "sigma_abc_012c_real_loop_candidate_preparation",
        "overall_gate": gate if ready else "FAIL",
        "checks": checks,
        "protected_regressions": [
            {"name": "sigma_xxx_projection", "status": "REGISTERED", "gate": "REGISTERED"}
        ],
        "caveats": [DC_CAVEAT],
        "boundary_audit": {
            "overclaim_detected": False,
            "full_tensorial_claim_detected": False,
            "ibp_started_without_approval": False,
            "dc_caveat_preserved": True,
        },
    }


def make_stage(tmp_path: Path, *, ready: bool = True) -> Path:
    stage = tmp_path / "autonomous_runs" / "sigma_abc" / "stages" / "sigma_abc_012c_real_loop_candidate_preparation"
    for folder in [".loop", "reports", "output", "validation"]:
        (stage / folder).mkdir(parents=True, exist_ok=True)
    write_text(
        stage / "STAGE_PLAN.md",
        """# Stage Plan

expected_outputs:
- output/loop_candidate_preparation.json
- reports/loop_candidate_preparation_report.md

completion_plan:
- id: RealLoopCandidateReady
  category: validation
  description: Real loop candidate preparation is ready.
""",
    )
    write_text(stage / "CLAIM_BOUNDARY.md", f"# Claim Boundary\n\n{DC_CAVEAT}\n")
    write_text(stage / "review_packet.md", f"# Review Packet\n\n{DC_CAVEAT}\n")
    write_text(stage / "output" / "loop_candidate_preparation.json", "{}\n")
    write_text(stage / "reports" / "loop_candidate_preparation_report.md", "# Report\n")
    write_json(stage / ".loop" / "validation_summary.json", _validation(ready=ready))
    write_json(stage / ".loop" / "review_result.json", _review())
    return stage


def test_schemas_exist_and_accept_minimal_valid_payloads():
    assert schema_path("completion_matrix").exists()
    assert schema_path("human_signoff").exists()
    validate_with_schema(
        {
            "stage_id": "stage",
            "overall_completion": "COMPLETE",
            "freeze_eligible": True,
            "generated_at": "2026-07-01T00:00:00+00:00",
            "basis": {
                "stage_plan": "STAGE_PLAN.md",
                "validation_summary": ".loop/validation_summary.json",
                "review_result": ".loop/review_result.json",
                "claim_boundary": "CLAIM_BOUNDARY.md",
            },
            "items": [],
            "boundary_audit": {},
            "recommended_human_action": "APPROVE_FREEZE",
        },
        "completion_matrix",
    )
    validate_with_schema(
        {
            "stage_id": "stage",
            "signed_by": "wangjiahua",
            "signed_at": "2026-07-01T00:00:00+00:00",
            "decision": "APPROVE_FREEZE",
            "basis": {
                "completion_matrix": "reports/completion_matrix.json",
                "validation_summary": ".loop/validation_summary.json",
                "review_result": ".loop/review_result.json",
                "claim_boundary": "CLAIM_BOUNDARY.md",
            },
            "basis_hashes": {},
            "human_scientific_judgment": {
                "completion_understood": True,
                "blocking_items_understood": True,
                "boundary_audit_understood": True,
                "caveats_understood": True,
            },
            "permission": {
                "freeze_checkpoint": True,
                "continue_patch_loop": False,
                "promote_claim": False,
                "start_ibp": False,
                "start_total_derivative": False,
            },
        },
        "human_signoff",
    )


def test_completion_matrix_classifies_validation_and_protected_regression(tmp_path: Path):
    from loop_engine.completion_matrix import build_completion_matrix, validate_completion_matrix_freshness, write_completion_matrix

    stage = make_stage(tmp_path, ready=False)
    matrix = build_completion_matrix(stage)
    by_id = {item["id"]: item for item in matrix["items"]}
    assert by_id["NoIBPStarted"]["status"] == "DONE"
    assert by_id["Stage012AArtifactPresent"]["status"] == "FAILED"
    assert by_id["sigma_xxx_projection"]["status"] == "REGISTERED"
    assert by_id["output:output/loop_candidate_preparation.json"]["status"] == "DONE"
    assert matrix["overall_completion"] == "FAILED"
    assert matrix["freeze_eligible"] is False
    assert matrix["recommended_human_action"] == "DO_NOT_FREEZE_PATCH"
    assert matrix["boundary_audit"]["dc_caveat_preserved"] is True

    path = write_completion_matrix(stage)
    assert path == stage / "reports" / "completion_matrix.json"
    assert (stage / "reports" / "completion_matrix.md").exists()
    fresh, reasons = validate_completion_matrix_freshness(stage, read_json(path))
    assert fresh, reasons
    write_text(stage / "CLAIM_BOUNDARY.md", "# changed\n")
    fresh, reasons = validate_completion_matrix_freshness(stage, read_json(path))
    assert fresh is False
    assert any("CLAIM_BOUNDARY.md" in reason for reason in reasons)


def test_completion_matrix_recommends_reject_for_boundary_unsafe(tmp_path: Path):
    from loop_engine.completion_matrix import build_completion_matrix

    stage = make_stage(tmp_path)
    validation = read_json(stage / ".loop" / "validation_summary.json")
    validation["boundary_audit"]["overclaim_detected"] = True
    write_json(stage / ".loop" / "validation_summary.json", validation)
    matrix = build_completion_matrix(stage)
    assert matrix["recommended_human_action"] == "REJECT_AND_STOP"
    assert matrix["boundary_audit"]["overclaim_detected"] is True


def test_human_signoff_semantics_history_ledger_and_reject(tmp_path: Path):
    from loop_engine.completion_matrix import write_completion_matrix
    from loop_engine.human_signoff import (
        apply_reject,
        build_signoff_from_decision,
        check_signoff_freeze_eligible,
        load_signoff,
        validate_signoff,
        validate_signoff_freshness,
        write_signoff,
    )

    stage = make_stage(tmp_path)
    write_completion_matrix(stage)
    patch = build_signoff_from_decision(
        stage,
        "DO_NOT_FREEZE_PATCH",
        reason="Stage012A/012B artifacts are missing.",
        signed_by="wangjiahua",
    )
    ok, reasons = validate_signoff(patch)
    assert ok, reasons
    assert patch["permission"]["continue_patch_loop"] is True
    assert patch["permission"]["freeze_checkpoint"] is False
    write_signoff(stage, patch)
    loaded = load_signoff(stage)
    assert loaded["decision"] == "DO_NOT_FREEZE_PATCH"
    ok, reasons = check_signoff_freeze_eligible(loaded)
    assert ok is False
    assert any("blocks freeze" in reason for reason in reasons)

    caveat = build_signoff_from_decision(stage, "APPROVE_FREEZE_WITH_CAVEAT", reason=DC_CAVEAT, signed_by="wangjiahua")
    assert caveat["accepted_caveats"]
    write_signoff(stage, caveat)
    assert any((stage / ".loop" / "human_signoff_history").glob("*DO_NOT_FREEZE_PATCH.yaml"))
    assert (stage / ".loop" / "human_signoff_ledger.jsonl").read_text(encoding="utf-8").count("\n") >= 2
    fresh, reasons = validate_signoff_freshness(stage, load_signoff(stage))
    assert fresh, reasons

    bad_caveat = caveat | {"accepted_caveats": []}
    ok, reasons = validate_signoff(bad_caveat)
    assert ok is False
    assert any("accepted_caveats" in reason for reason in reasons)

    reject = build_signoff_from_decision(stage, "REJECT_AND_STOP", reason="Reject stage.", signed_by="wangjiahua")
    apply_reject(stage, reject)
    assert (stage / ".loop" / "STOP").exists()


def test_signoff_permission_cannot_exceed_profile_defaults(tmp_path: Path):
    from loop_engine.completion_matrix import write_completion_matrix
    from loop_engine.human_signoff import build_signoff_from_decision, validate_signoff

    stage = make_stage(tmp_path)
    write_completion_matrix(stage)
    signoff = build_signoff_from_decision(stage, "APPROVE_FREEZE", reason=None, signed_by="wangjiahua")
    signoff["permission"]["start_ibp"] = True
    ok, reasons = validate_signoff(signoff, profile={"default_permissions": {"start_ibp": False}})
    assert ok is False
    assert any("start_ibp" in reason for reason in reasons)


def test_freeze_preconditions_require_matrix_signoff_and_block_bad_items(tmp_path: Path):
    from loop_engine.completion_matrix import write_completion_matrix
    from loop_engine.human_signoff import build_signoff_from_decision, write_signoff

    stage = make_stage(tmp_path, ready=True)
    validation = read_json(stage / ".loop" / "validation_summary.json")
    review = read_json(stage / ".loop" / "review_result.json")
    assert any("completion_matrix" in reason for reason in freeze_preconditions(stage, validation, review))

    write_completion_matrix(stage)
    assert any("human_signoff" in reason for reason in freeze_preconditions(stage, validation, review))

    patch = build_signoff_from_decision(stage, "DO_NOT_FREEZE_PATCH", reason="Patch.", signed_by="wangjiahua")
    write_signoff(stage, patch)
    assert any("DO_NOT_FREEZE_PATCH" in reason for reason in freeze_preconditions(stage, validation, review))

    approve = build_signoff_from_decision(stage, "APPROVE_FREEZE", reason=None, signed_by="wangjiahua")
    write_signoff(stage, approve)
    assert freeze_preconditions(stage, validation, review) == []

    blocked = make_stage(tmp_path / "blocked", ready=False)
    blocked_validation = read_json(blocked / ".loop" / "validation_summary.json")
    blocked_review = read_json(blocked / ".loop" / "review_result.json")
    write_completion_matrix(blocked)
    blocked_approve = build_signoff_from_decision(blocked, "APPROVE_FREEZE", reason=None, signed_by="wangjiahua")
    write_signoff(blocked, blocked_approve)
    reasons = freeze_preconditions(blocked, blocked_validation, blocked_review)
    assert any("validation_summary.overall_gate" in reason for reason in reasons)
    assert any("blocking incomplete items" in reason for reason in reasons)


def test_manifest_and_digest_include_completion_matrix_and_signoff(tmp_path: Path):
    from loop_engine.completion_matrix import write_completion_matrix
    from loop_engine.human_signoff import build_signoff_from_decision, write_signoff
    from loop_engine.stage_digest import build_stage_digest

    stage = make_stage(tmp_path)
    write_completion_matrix(stage)
    write_signoff(stage, build_signoff_from_decision(stage, "APPROVE_FREEZE_WITH_CAVEAT", reason=DC_CAVEAT, signed_by="wangjiahua"))
    build_stage_digest(stage)
    digest = (stage / "reports" / "stage_summary.md").read_text(encoding="utf-8")
    assert "Completion matrix summary" in digest
    assert "Human signoff" in digest
    manifest = build_checkpoint_manifest(stage)
    assert manifest["completion_matrix"] == "reports/completion_matrix.json"
    assert manifest["human_signoff"] == ".loop/human_signoff.yaml"
    assert manifest["human_signoff_decision"] == "APPROVE_FREEZE_WITH_CAVEAT"
    assert DC_CAVEAT in manifest["accepted_caveats"]


def test_sign_stage_cli_chat_protocol_and_dry_run(tmp_path: Path):
    from loop_engine.completion_matrix import write_completion_matrix

    stage = make_stage(tmp_path)
    write_completion_matrix(stage)
    dry = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "sign_stage.py"),
            "--stage",
            str(stage),
            "--decision",
            "DO_NOT_FREEZE_PATCH",
            "--reason",
            "Stage012A/012B artifacts are missing.",
            "--signed-by",
            "wangjiahua",
            "--dry-run",
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "DO_NOT_FREEZE_PATCH" in dry.stdout
    assert not (stage / ".loop" / "human_signoff.yaml").exists()

    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "sign_stage.py"), "--stage", str(stage)],
        cwd=REPO_ROOT,
        input="SIGNOFF stage=sigma_abc_012c_real_loop_candidate_preparation\ndecision=DO_NOT_FREEZE_PATCH\nreason=patch safely\nsigned_by=wangjiahua\n",
        check=True,
        text=True,
        capture_output=True,
    )
    assert (stage / ".loop" / "human_signoff.yaml").exists()


def test_migrate_old_human_signoff_json_to_yaml(tmp_path: Path):
    from loop_engine.human_signoff import load_signoff

    stage = make_stage(tmp_path)
    write_json(stage / ".loop" / "human_signoff.json", {"stage_id": stage.name, "decision": "DO_NOT_FREEZE", "signed_by": "wangjiahua"})
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "migrate_human_signoff.py"), "--stage", str(stage)],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    migrated = load_signoff(stage)
    assert migrated["decision"] == "DO_NOT_FREEZE_PATCH"
    assert migrated["permission"]["continue_patch_loop"] is True
    assert migrated["permission"]["freeze_checkpoint"] is False
    assert any((stage / ".loop" / "human_signoff_history").glob("*legacy_human_signoff.json"))


def test_current_012c_contract_regression_shape(tmp_path: Path):
    from loop_engine.completion_matrix import build_completion_matrix, write_completion_matrix
    from loop_engine.human_signoff import build_signoff_from_decision, write_signoff

    stage = make_stage(tmp_path, ready=False)
    matrix = build_completion_matrix(stage)
    failed = {item["id"] for item in matrix["items"] if item["status"] == "FAILED"}
    assert {
        "Stage012AArtifactPresent",
        "Stage012BArtifactPresent",
        "UsesStage012ALoopLedger",
        "UsesStage012BHypothesisLedger",
        "RealLoopCandidateReady",
    } <= failed
    assert matrix["recommended_human_action"] == "DO_NOT_FREEZE_PATCH"
    assert matrix["boundary_audit"]["overclaim_detected"] is False
    assert matrix["boundary_audit"]["full_tensorial_claim_detected"] is False
    assert matrix["boundary_audit"]["ibp_started_without_approval"] is False
    assert matrix["boundary_audit"]["dc_caveat_preserved"] is True

    write_completion_matrix(stage)
    write_signoff(stage, build_signoff_from_decision(stage, "APPROVE_FREEZE", reason=None, signed_by="wangjiahua"))
    reasons = freeze_preconditions(
        stage,
        read_json(stage / ".loop" / "validation_summary.json"),
        read_json(stage / ".loop" / "review_result.json"),
    )
    assert any("blocking incomplete items" in reason for reason in reasons)


# ============================================================================
# Loop 013 completion-matrix status hotfix tests
# ============================================================================


def test_status_from_gate_literal_mapping():
    from loop_engine.completion_matrix import _status_from_gate

    assert _status_from_gate("PASS") == "DONE"
    assert _status_from_gate("pass") == "DONE"
    assert _status_from_gate("PASS_WITH_CAVEAT") == "DONE_WITH_CAVEAT"
    assert _status_from_gate("REGISTERED") == "REGISTERED"
    assert _status_from_gate("REGISTERED_NOT_RUN") == "REGISTERED"
    assert _status_from_gate("INHERITED_PASS") == "REGISTERED"
    assert _status_from_gate("INHERITED") == "REGISTERED"
    assert _status_from_gate("FAIL") == "FAILED"
    assert _status_from_gate("MISSING") == "MISSING"
    assert _status_from_gate("BLOCKED") == "BLOCKED"
    # Safe fallback for unknown gate strings
    assert _status_from_gate("UNKNOWN_FUTURE_GATE") == "MISSING"


def test_completion_matrix_schema_accepts_done_with_caveat_status():
    payload = {
        "stage_id": "stage",
        "overall_completion": "COMPLETE",
        "freeze_eligible": True,
        "generated_at": "2026-07-01T00:00:00+00:00",
        "basis": {
            "stage_plan": "STAGE_PLAN.md",
            "validation_summary": ".loop/validation_summary.json",
            "review_result": ".loop/review_result.json",
            "claim_boundary": "CLAIM_BOUNDARY.md",
        },
        "items": [
            {
                "id": "CaveatedCheck",
                "category": "validation",
                "description": "Check with caveat",
                "status": "DONE_WITH_CAVEAT",
                "blocking": False,
            }
        ],
        "boundary_audit": {},
        "recommended_human_action": "APPROVE_FREEZE_WITH_CAVEAT",
    }
    validate_with_schema(payload, "completion_matrix")


def test_protected_regression_registered_not_run_is_non_blocking(tmp_path):
    from loop_engine.completion_matrix import build_completion_matrix

    stage = make_stage(tmp_path)
    validation = read_json(stage / ".loop" / "validation_summary.json")
    validation["protected_regressions"] = [
        {"name": "sigma_xxx_projection", "status": "REGISTERED_NOT_RUN", "gate": "REGISTERED_NOT_RUN"}
    ]
    write_json(stage / ".loop" / "validation_summary.json", validation)

    matrix = build_completion_matrix(stage)
    by_id = {item["id"]: item for item in matrix["items"]}
    assert by_id["sigma_xxx_projection"]["status"] == "REGISTERED"
    assert by_id["sigma_xxx_projection"]["blocking"] is False


def test_dcprojection_to_1d_inherited_pass_is_non_blocking(tmp_path):
    from loop_engine.completion_matrix import build_completion_matrix

    stage = make_stage(tmp_path)
    validation = read_json(stage / ".loop" / "validation_summary.json")
    validation["protected_regressions"] = [
        {"name": "DCProjectionTo1D", "status": "INHERITED_PASS", "gate": "INHERITED_PASS"}
    ]
    write_json(stage / ".loop" / "validation_summary.json", validation)

    matrix = build_completion_matrix(stage)
    by_id = {item["id"]: item for item in matrix["items"]}
    assert by_id["DCProjectionTo1D"]["status"] == "REGISTERED"
    assert by_id["DCProjectionTo1D"]["blocking"] is False


def test_registered_gates_do_not_count_as_blocking_incomplete(tmp_path):
    from loop_engine.completion_matrix import build_completion_matrix

    stage = make_stage(tmp_path)  # ready=True
    validation = read_json(stage / ".loop" / "validation_summary.json")
    validation["protected_regressions"] = [
        {"name": "sigma_xxx_projection", "gate": "REGISTERED"},
        {"name": "DCProjectionTo1D", "gate": "INHERITED_PASS"},
        {"name": "future_projection_x", "gate": "REGISTERED_NOT_RUN"},
        {"name": "legacy_protected", "gate": "INHERITED"},
    ]
    write_json(stage / ".loop" / "validation_summary.json", validation)

    matrix = build_completion_matrix(stage)
    blocking_incomplete = [
        item for item in matrix["items"]
        if item["blocking"] and item["status"] in {"MISSING", "FAILED", "BLOCKED"}
    ]
    assert blocking_incomplete == []
    assert matrix["overall_completion"] == "COMPLETE"
    assert matrix["freeze_eligible"] is True


def test_012c_like_stage_with_registered_protected_regressions_still_incomplete(tmp_path):
    from loop_engine.completion_matrix import build_completion_matrix

    # ready=False -> Stage012A/012B and friends are FAILED
    stage = make_stage(tmp_path, ready=False)
    validation = read_json(stage / ".loop" / "validation_summary.json")
    validation["protected_regressions"] = [
        {"name": "sigma_xxx_projection", "gate": "REGISTERED_NOT_RUN"},
        {"name": "DCProjectionTo1D", "gate": "INHERITED_PASS"},
    ]
    write_json(stage / ".loop" / "validation_summary.json", validation)

    matrix = build_completion_matrix(stage)
    # Stage012A/012B FAILED propagate -> overall_completion FAILED
    assert matrix["overall_completion"] == "FAILED"
    # Recommended action still DO_NOT_FREEZE_PATCH (dependency failure, not boundary failure)
    assert matrix["recommended_human_action"] == "DO_NOT_FREEZE_PATCH"
    # The REGISTERED protected regressions are NOT the cause of blocking
    blocking_bad = [
        item for item in matrix["items"]
        if item["blocking"] and item["status"] in {"MISSING", "FAILED", "BLOCKED"}
    ]
    for item in blocking_bad:
        assert "Projection" not in item["id"]
        assert "INHERITED" not in item["id"]
        assert "DCProjection" not in item["id"]
        assert "sigma_xxx" not in item["id"]
    # Boundary audit remains safe
    assert matrix["boundary_audit"]["overclaim_detected"] is False
    assert matrix["boundary_audit"]["full_tensorial_claim_detected"] is False
    assert matrix["boundary_audit"]["ibp_started_without_approval"] is False
    assert matrix["boundary_audit"]["dc_caveat_preserved"] is True
