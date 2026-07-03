"""Tests for the deterministic, read-only run-diagnosis layer (TASK_023)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from loop_engine.config import write_json, write_text
from loop_engine.run_diagnosis import (
    diagnose_run,
    render_next_action_markdown,
    write_next_action_reports,
)
from loop_engine.schemas import validate_with_schema


REPO_ROOT = Path(__file__).resolve().parents[1]
DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _validation(*, overall_gate: str = "PASS") -> dict:
    return {
        "stage_name": "stage_diagnosis_test",
        "overall_gate": overall_gate,
        "checks": [
            {"name": "NoIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
        ],
        "boundary_audit": {
            "overclaim_detected": False,
            "full_tensorial_claim_detected": False,
            "ibp_started_without_approval": False,
            "dc_caveat_preserved": True,
        },
    }


def _review(*, verdict: str = "PASS") -> dict:
    return {
        "verdict": verdict,
        "stage_name": "stage_diagnosis_test",
        "mathematical_status": {
            "exact_reconstruction": True,
            "simplification_real": True,
            "regression_preserved": True,
            "overclaim_detected": False,
        },
        "blocking_issues": [],
        "nonblocking_caveats": [DC_CAVEAT],
        "allowed_claims": ["PASS"],
        "forbidden_claims": ["Do not claim full tensorial sigma_abc correctness."],
        "next_action": "FREEZE",
        "patch_instructions": [],
    }


def _stage_skeleton(tmp_path: Path, *, name: str = "stage_diagnosis_test") -> Path:
    stage = tmp_path / "autonomous_runs" / "sigma_abc" / "stages" / name
    (stage / ".loop").mkdir(parents=True, exist_ok=True)
    (stage / "reports").mkdir(parents=True, exist_ok=True)
    write_text(
        stage / "STAGE_PLAN.md",
        "# Stage Plan\n",
    )
    write_text(stage / "CLAIM_BOUNDARY.md", f"# Claim Boundary\n\n{DC_CAVEAT}\n")
    write_text(stage / "review_packet.md", f"# Review Packet\n\n{DC_CAVEAT}\n")
    return stage


def _completion_matrix(*, overall: str = "COMPLETE", recommended: str = "APPROVE_FREEZE") -> dict:
    return {
        "stage_id": "stage_diagnosis_test",
        "overall_completion": overall,
        "freeze_eligible": overall == "COMPLETE" and recommended in {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT"},
        "generated_at": "2026-07-03T00:00:00+00:00",
        "basis": {
            "stage_plan": "STAGE_PLAN.md",
            "validation_summary": ".loop/validation_summary.json",
            "review_result": ".loop/review_result.json",
            "claim_boundary": "CLAIM_BOUNDARY.md",
        },
        "items": [],
        "boundary_audit": {
            "overclaim_detected": False,
            "full_tensorial_claim_detected": False,
            "ibp_started_without_approval": False,
            "dc_caveat_preserved": True,
        },
        "recommended_human_action": recommended,
    }


def _signoff(*, decision: str = "APPROVE_FREEZE") -> dict:
    permission = {
        "freeze_checkpoint": decision in {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT"},
        "continue_patch_loop": decision == "DO_NOT_FREEZE_PATCH",
        "promote_claim": False,
        "start_ibp": False,
        "start_total_derivative": False,
    }
    return {
        "stage_id": "stage_diagnosis_test",
        "signed_by": "wangjiahua",
        "signed_at": "2026-07-03T00:00:00+00:00",
        "decision": decision,
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
        "permission": permission,
    }


def _report_codes(report: dict) -> list[str]:
    return [item["code"] for item in report.get("all_classifications", [])]


# ---------------------------------------------------------------------------
# Classification coverage
# ---------------------------------------------------------------------------


def test_schema_round_trip():
    """The schema must accept the empty/minimal report we emit."""
    sample = diagnose_run()
    # Raises if invalid.
    validate_with_schema(sample, "next_action_report")


def test_unknown_failure_when_no_artifacts():
    report = diagnose_run()
    assert report["classification"]["code"] == "UNKNOWN_FAILURE"
    assert report["next_action"]["recommended"] == "ASK_HUMAN_REVIEWER"


def test_command_failed_when_nonzero_exit():
    report = diagnose_run(command_return_code=2, stderr_file=Path("/dev/null"))
    assert report["classification"]["code"] == "COMMAND_FAILED"
    assert report["next_action"]["recommended"] == "INSPECT_AND_RETRY"
    assert any("command" in ev["summary"].lower() or "non-zero" in ev["summary"].lower() or ev.get("path") for ev in report["evidence"])


def test_command_failed_via_status_json(tmp_path):
    status = tmp_path / "command_status.json"
    write_json(status, {"return_code": 7, "argv": ["x"]})
    report = diagnose_run(command_status_json=status)
    assert report["classification"]["code"] == "COMMAND_FAILED"


def test_missing_required_file(tmp_path):
    stage = _stage_skeleton(tmp_path)
    # Intentionally leave validation_summary.json absent.
    report = diagnose_run(stage=stage)
    codes = _report_codes(report)
    assert "MISSING_REQUIRED_FILE" in codes
    assert report["classification"]["code"] == "MISSING_REQUIRED_FILE"


def test_schema_validation_failed_malformed_json(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_text(stage / ".loop" / "validation_summary.json", "{not valid json")
    report = diagnose_run(stage=stage)
    codes = _report_codes(report)
    assert "SCHEMA_VALIDATION_FAILED" in codes
    # Schema failure outranks missing-file because the file exists but is malformed.
    assert report["classification"]["code"] == "SCHEMA_VALIDATION_FAILED"


def test_schema_validation_failed_schema_invalid(tmp_path):
    stage = _stage_skeleton(tmp_path)
    # overall_gate is required and must be one of the enum values; omit it.
    write_json(stage / ".loop" / "validation_summary.json", {"stage_name": "x", "checks": []})
    report = diagnose_run(stage=stage)
    assert report["classification"]["code"] == "SCHEMA_VALIDATION_FAILED"


def test_validation_gate_failed(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    report = diagnose_run(stage=stage)
    codes = _report_codes(report)
    assert "VALIDATION_GATE_FAILED" in codes
    assert report["classification"]["code"] == "VALIDATION_GATE_FAILED"
    assert report["gate_status"]["validation_gate"] == "FAIL"


def test_review_gate_failed_verdict_needs_patch(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="NEEDS_PATCH"))
    report = diagnose_run(stage=stage)
    assert report["classification"]["code"] == "REVIEW_GATE_FAILED"
    assert report["next_action"]["recommended"] == "IMPLEMENT_PATCH_INSTRUCTIONS"


def test_review_gate_failed_verdict_failed(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="FAILED"))
    report = diagnose_run(stage=stage)
    assert report["classification"]["code"] == "REVIEW_GATE_FAILED"


def test_completion_matrix_unhealthy_incomplete(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    write_json(stage / "reports" / "completion_matrix.json", _completion_matrix(overall="INCOMPLETE"))
    report = diagnose_run(stage=stage)
    assert report["classification"]["code"] == "COMPLETION_MATRIX_UNHEALTHY"
    assert report["gate_status"]["freeze_eligible"] is False


def test_completion_matrix_unhealthy_reject(tmp_path):
    """Completion matrix unhealthy because overall is BLOCKED, with no boundary trigger.

    A pure completion-marker failure (BLOCKED) classifies as
    COMPLETION_MATRIX_UNHEALTHY because no boundary audit fired.
    """
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    write_json(
        stage / "reports" / "completion_matrix.json",
        _completion_matrix(overall="BLOCKED", recommended="DO_NOT_FREEZE_PATCH"),
    )
    report = diagnose_run(stage=stage)
    codes = _report_codes(report)
    assert "COMPLETION_MATRIX_UNHEALTHY" in codes
    assert report["classification"]["code"] == "COMPLETION_MATRIX_UNHEALTHY"


def test_completion_matrix_reject_with_boundary_audit_is_boundary_primary(tmp_path):
    """A REJECT_AND_STOP recommendation implies a boundary audit flag fired.

    By precedence, BOUNDARY_APPROVAL_REQUIRED outranks COMPLETION_MATRIX_UNHEALTHY.
    """
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    matrix = _completion_matrix(recommended="REJECT_AND_STOP")
    matrix["boundary_audit"]["overclaim_detected"] = True
    write_json(stage / "reports" / "completion_matrix.json", matrix)
    report = diagnose_run(stage=stage)
    codes = _report_codes(report)
    assert "BOUNDARY_APPROVAL_REQUIRED" in codes
    assert "COMPLETION_MATRIX_UNHEALTHY" in codes
    assert report["classification"]["code"] == "BOUNDARY_APPROVAL_REQUIRED"


def test_boundary_approval_required_for_ibp(tmp_path):
    stage = _stage_skeleton(tmp_path)
    val = _validation(overall_gate="PASS")
    val["boundary_audit"]["ibp_started_without_approval"] = True
    write_json(stage / ".loop" / "validation_summary.json", val)
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    report = diagnose_run(stage=stage)
    codes = _report_codes(report)
    assert "BOUNDARY_APPROVAL_REQUIRED" in codes
    assert report["classification"]["code"] == "BOUNDARY_APPROVAL_REQUIRED"
    assert report["next_action"]["boundary_approval_required"] is True


def test_boundary_approval_required_overclaim_in_plan(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_text(stage / "STAGE_PLAN.md", "# Plan\n\nGoal: promote the candidate now.\n")
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    report = diagnose_run(stage=stage)
    codes = _report_codes(report)
    assert "BOUNDARY_APPROVAL_REQUIRED" in codes
    assert report["classification"]["code"] == "BOUNDARY_APPROVAL_REQUIRED"


def test_human_signoff_required_when_freeze_eligible_but_no_signoff(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    write_json(stage / "reports" / "completion_matrix.json", _completion_matrix(overall="COMPLETE"))
    report = diagnose_run(stage=stage)
    assert report["classification"]["code"] == "HUMAN_SIGNOFF_REQUIRED"
    assert report["next_action"]["recommended"] == "OBTAIN_HUMAN_SIGNOFF"
    assert report["next_action"]["human_required"] is True


def test_human_signoff_required_when_signoff_blocks_freeze(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    write_json(stage / "reports" / "completion_matrix.json", _completion_matrix(overall="COMPLETE"))
    # Signoff present but explicitly blocks freeze.
    import yaml
    (stage / ".loop" / "human_signoff.yaml").write_text(
        yaml.safe_dump(_signoff(decision="DO_NOT_FREEZE_PATCH")),
        encoding="utf-8",
    )
    report = diagnose_run(stage=stage)
    assert report["classification"]["code"] == "HUMAN_SIGNOFF_REQUIRED"


def test_freeze_precondition_failed_after_signoff_present(tmp_path):
    """Freeze preconditions fail when basis files drift after signoff/completion.

    Use real ``build_completion_matrix`` so hashes are correct, then mutate
    a basis file to trigger a non-signoff, non-boundary ``freeze_preconditions``
    reason (stale completion_matrix). Signoff stays valid; freeze can't
    proceed because the matrix is stale.
    """
    from loop_engine.completion_matrix import build_completion_matrix, write_completion_matrix
    import yaml

    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    write_completion_matrix(stage)  # writes real, hash-correct matrix
    # Build a signoff whose basis_hashes match the current on-disk files.
    from loop_engine.human_signoff import build_signoff_from_decision

    signoff = build_signoff_from_decision(
        stage,
        decision="APPROVE_FREEZE",
        reason=None,
        signed_by="wangjiahua",
    )
    (stage / ".loop" / "human_signoff.yaml").write_text(yaml.safe_dump(signoff), encoding="utf-8")

    # Mutate STAGE_PLAN.md AFTER signoff was written -> matrix becomes stale.
    write_text(stage / "STAGE_PLAN.md", "# Plan\n\nMutated after signoff.\n")

    report = diagnose_run(stage=stage)
    codes = _report_codes(report)
    assert "FREEZE_PRECONDITION_FAILED" in codes
    assert report["classification"]["code"] == "FREEZE_PRECONDITION_FAILED"


def test_all_healthy_when_artifacts_complete(tmp_path):
    """All validation/review/completion/signoff artifacts are healthy.

    With a real completion matrix + signoff, the only diagnostic note is
    that freeze is human-gated (HUMAN_SIGNOFF_REQUIRED) until the operator
    decides. No failure code should fire.
    """
    from loop_engine.completion_matrix import build_completion_matrix, write_completion_matrix
    from loop_engine.human_signoff import build_signoff_from_decision
    import yaml

    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    write_completion_matrix(stage)
    signoff = build_signoff_from_decision(
        stage,
        decision="APPROVE_FREEZE",
        reason=None,
        signed_by="wangjiahua",
    )
    (stage / ".loop" / "human_signoff.yaml").write_text(yaml.safe_dump(signoff), encoding="utf-8")
    report = diagnose_run(stage=stage)
    # Operator-gated, not a failure.
    codes = _report_codes(report)
    assert "VALIDATION_GATE_FAILED" not in codes
    assert "REVIEW_GATE_FAILED" not in codes
    assert "COMPLETION_MATRIX_UNHEALTHY" not in codes
    assert "FREEZE_PRECONDITION_FAILED" not in codes
    assert "SCHEMA_VALIDATION_FAILED" not in codes


# ---------------------------------------------------------------------------
# Report rendering + writing
# ---------------------------------------------------------------------------


def test_render_markdown_contains_sections():
    report = diagnose_run(command_return_code=3)
    md = render_next_action_markdown(report)
    assert "# Next Action Report" in md
    assert "Primary classification" in md
    assert "Recommended next action" in md
    assert "Read-only guarantee" in md
    assert "COMMAND_FAILED" in md


def test_write_reports_writes_both_and_validates_schema(tmp_path):
    out = tmp_path / "diag"
    report = diagnose_run(command_return_code=1)
    json_path, md_path = write_next_action_reports(report, out)
    assert json_path.exists()
    assert md_path.exists()
    # JSON validates against the new schema.
    payload = json.loads(json_path.read_text())
    validate_with_schema(payload, "next_action_report")
    # Markdown contains expected primary section.
    body = md_path.read_text()
    assert "Primary classification" in body
    assert report["classification"]["code"] in body


def test_write_reports_json_only_skips_markdown(tmp_path):
    out = tmp_path / "diag"
    report = diagnose_run(command_return_code=1)
    json_path, md_path = write_next_action_reports(report, out, json_only=True)
    assert json_path.exists()
    assert not md_path.exists()


def test_write_reports_markdown_only_skips_json(tmp_path):
    out = tmp_path / "diag"
    report = diagnose_run(command_return_code=1)
    json_path, md_path = write_next_action_reports(report, out, markdown_only=True)
    assert not json_path.exists()
    assert md_path.exists()


# ---------------------------------------------------------------------------
# Read-only contract
# ---------------------------------------------------------------------------


def test_diagnose_run_does_not_modify_stage_files(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    write_json(stage / "reports" / "completion_matrix.json", _completion_matrix(overall="COMPLETE"))

    before = _snapshot_stage(stage)
    report = diagnose_run(stage=stage)
    after = _snapshot_stage(stage)
    assert before == after
    assert report["tool_metadata"]["diagnostic_readonly"] is True
    assert report["tool_metadata"]["modified_artifacts"] == []


def _snapshot_stage(stage: Path) -> dict[str, str | None]:
    return {
        rel: (p.read_text(encoding="utf-8") if p.exists() else None)
        for rel in [
            ".loop/validation_summary.json",
            ".loop/review_result.json",
            ".loop/human_signoff.yaml",
            "reports/completion_matrix.json",
            "CLAIM_BOUNDARY.md",
            "STAGE_PLAN.md",
            "review_packet.md",
        ]
        for p in [stage / rel]
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_writes_both_files_and_validates_against_schema(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out_dir = tmp_path / "cli_out"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "diagnose_run_failure.py"),
            "--stage",
            str(stage),
            "--output-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (out_dir / "next_action_report.json").exists()
    assert (out_dir / "next_action_report.md").exists()
    payload = json.loads((out_dir / "next_action_report.json").read_text())
    validate_with_schema(payload, "next_action_report")
    assert payload["classification"]["code"] == "VALIDATION_GATE_FAILED"


def test_cli_reports_command_failed(tmp_path):
    out_dir = tmp_path / "cli_out"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "diagnose_run_failure.py"),
            "--command-return-code",
            "5",
            "--output-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads((out_dir / "next_action_report.json").read_text())
    assert payload["classification"]["code"] == "COMMAND_FAILED"


def test_cli_json_only(tmp_path):
    out_dir = tmp_path / "cli_out"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "diagnose_run_failure.py"),
            "--command-return-code",
            "5",
            "--json-only",
            "--output-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (out_dir / "next_action_report.json").exists()
    assert not (out_dir / "next_action_report.md").exists()


def test_cli_does_not_create_signoff_or_checkpoint(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    write_json(stage / "reports" / "completion_matrix.json", _completion_matrix(overall="COMPLETE"))
    before_files = {p.relative_to(stage) for p in stage.rglob("*") if p.is_file()}
    out_dir = tmp_path / "cli_out"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "diagnose_run_failure.py"),
            "--stage",
            str(stage),
            "--output-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    # The CLI must NOT create human_signoff.yaml, the ledger, or history.
    assert not (stage / ".loop" / "human_signoff.yaml").exists()
    assert not (stage / ".loop" / "human_signoff_ledger.jsonl").exists()
    assert not (stage / ".loop" / "human_signoff_history").exists()
    # It also must not have written any output into the stage itself.
    after_files = {p.relative_to(stage) for p in stage.rglob("*") if p.is_file()}
    assert before_files == after_files


# ---------------------------------------------------------------------------
# Acceptance: smoke project
# ---------------------------------------------------------------------------


def test_acceptance_smoke_polynomial_stage(tmp_path):
    """Run the CLI against the real smoke project and confirm schema validity."""
    stage = REPO_ROOT / "smoke_projects" / "mock_polynomial_loop" / "stages" / "000_polynomial_identity"
    assert stage.exists(), "smoke project missing - test infra assumption broken"
    out_dir = tmp_path / "loop_diag_smoke"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "diagnose_run_failure.py"),
            "--stage",
            str(stage),
            "--output-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads((out_dir / "next_action_report.json").read_text())
    validate_with_schema(payload, "next_action_report")
    # CLI output paths were printed.
    assert "next_action_report.json" in result.stdout
    assert "next_action_report.md" in result.stdout