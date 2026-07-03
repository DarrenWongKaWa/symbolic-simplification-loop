"""Tests for the run-root diagnosis path of ``loop_engine.run_diagnosis`` (TASK_024).

These complement ``tests/test_run_failure_diagnosis.py`` (TASK_023) by
covering ``inspect_run_root`` and the ``--run-root``-only invocation path
through ``diagnose_run``.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import yaml
from loop_engine.config import write_json, write_text
from loop_engine.run_diagnosis import (
    diagnose_run,
    inspect_run_root,
    render_next_action_markdown,
    write_next_action_reports,
)
from loop_engine.schemas import validate_with_schema


REPO_ROOT = Path(__file__).resolve().parents[1]
DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


# ---------------------------------------------------------------------------
# Builders (small copies; we do not depend on test_run_failure_diagnosis to keep
# this file self-contained and explicit).
# ---------------------------------------------------------------------------


def _validation(*, overall_gate: str = "PASS") -> dict:
    return {
        "stage_name": "stage_runroot_test",
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
        "stage_name": "stage_runroot_test",
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


def _completion_matrix(*, overall: str = "COMPLETE", recommended: str = "APPROVE_FREEZE") -> dict:
    return {
        "stage_id": "stage_runroot_test",
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


def _stage_skeleton(tmp_path: Path, *, name: str) -> Path:
    stage = tmp_path / "autonomous_runs" / "sigma_abc" / "stages" / name
    (stage / ".loop").mkdir(parents=True, exist_ok=True)
    (stage / "reports").mkdir(parents=True, exist_ok=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", f"# Claim Boundary\n\n{DC_CAVEAT}\n")
    return stage


def _write_validation(stage: Path, *, overall_gate: str = "PASS") -> None:
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate=overall_gate))


def _write_review(stage: Path, *, verdict: str = "PASS") -> None:
    write_json(stage / ".loop" / "review_result.json", _review(verdict=verdict))


def _write_matrix(stage: Path, *, overall: str = "COMPLETE", recommended: str = "APPROVE_FREEZE") -> None:
    write_json(stage / "reports" / "completion_matrix.json", _completion_matrix(overall=overall, recommended=recommended))


def _signoff(*, decision: str = "APPROVE_FREEZE") -> dict:
    permission = {
        "freeze_checkpoint": decision in {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT"},
        "continue_patch_loop": decision == "DO_NOT_FREEZE_PATCH",
        "promote_claim": False,
        "start_ibp": False,
        "start_total_derivative": False,
    }
    return {
        "stage_id": "stage_runroot_test",
        "signed_by": "wangjiahua",
        "signed_at": "2026-07-03T00:00:00+00:00",
        "decision": decision,
        "permission": permission,
        "human_scientific_judgment": {
            "completion_understood": True,
            "boundary_audit_understood": True,
        },
        "notes": "TASK_024 patch test fixture.",
    }


def _make_run_root(tmp_path: Path, *, name: str = "test_run") -> Path:
    rr = tmp_path / name
    (rr / "stages").mkdir(parents=True, exist_ok=True)
    return rr


def _build_basic_project(tmp_path: Path, *, stage_names: list[str]) -> Path:
    """Build a run root with N stages at ``stages/<name>``, each with full basis."""
    rr = _make_run_root(tmp_path)
    for name in stage_names:
        stage = rr / "stages" / name
        (stage / ".loop").mkdir(parents=True, exist_ok=True)
        (stage / "reports").mkdir(parents=True, exist_ok=True)
        write_text(stage / "STAGE_PLAN.md", f"# Stage Plan ({name})\n")
        write_text(stage / "CLAIM_BOUNDARY.md", f"# Claim Boundary ({name})\n\n{DC_CAVEAT}\n")
        _write_validation(stage, overall_gate="PASS")
        _write_review(stage, verdict="PASS")
        _write_matrix(stage, overall="COMPLETE", recommended="APPROVE_FREEZE")
    return rr


def _primary(report: dict) -> str:
    return report["classification"]["code"]


# ---------------------------------------------------------------------------
# inspect_run_root tests
# ---------------------------------------------------------------------------


def test_inspect_run_root_lists_discovered_stages(tmp_path):
    rr = _make_run_root(tmp_path)
    (rr / "stages" / "aaa_stage").mkdir(parents=True)
    (rr / "stages" / "bbb_stage").mkdir(parents=True)
    info = inspect_run_root(rr, repo_root=tmp_path)
    assert info["discovered_stage_ids"] == ["aaa_stage", "bbb_stage"]
    assert info["required_minimum_satisfied"] is True


def test_inspect_run_root_required_minimum_false_when_stages_missing(tmp_path):
    rr = tmp_path / "no_stages"
    rr.mkdir()
    info = inspect_run_root(rr, repo_root=tmp_path)
    assert info["required_minimum_satisfied"] is False
    assert info["stages_dir_exists"] is False


def test_inspect_run_root_required_minimum_false_when_no_stage_dirs(tmp_path):
    rr = _make_run_root(tmp_path)  # creates stages/ but no children
    info = inspect_run_root(rr, repo_root=tmp_path)
    assert info["required_minimum_satisfied"] is False
    assert info["discovered_stage_ids"] == []


def test_inspect_run_root_uses_loop_yaml_order_when_project_specified(tmp_path):
    rr = _make_run_root(tmp_path)
    (rr / "stages" / "b_stage").mkdir(parents=True)
    (rr / "stages" / "a_stage").mkdir(parents=True)
    # Build a fake repo with projects/<project>/loop.yaml.
    repo = tmp_path / "repo"
    (repo / "projects" / "projA").mkdir(parents=True)
    (repo / "projects" / "projA" / "loop.yaml").write_text(
        "project: projA\nstages:\n  - id: a_stage\n  - id: b_stage\n",
        encoding="utf-8",
    )
    info = inspect_run_root(rr, project="projA", repo_root=repo)
    assert info["ordered_stage_ids"] == ["a_stage", "b_stage"]
    assert "projects/projA/loop.yaml" in info["stage_order_source"]


def test_inspect_run_root_lexicographic_fallback_when_no_loop_yaml(tmp_path):
    rr = _make_run_root(tmp_path)
    (rr / "stages" / "b_stage").mkdir(parents=True)
    (rr / "stages" / "a_stage").mkdir(parents=True)
    info = inspect_run_root(rr, repo_root=tmp_path)
    assert info["ordered_stage_ids"] == ["a_stage", "b_stage"]
    assert info["stage_order_source"].startswith("lexicographic")


def test_inspect_run_root_picks_first_failing_stage(tmp_path):
    rr = _make_run_root(tmp_path)
    # First stage passes everywhere; second stage has validation=FAIL.
    _build_basic_project(tmp_path / "_seed", stage_names=["seed_pass_stage"])
    # Manually craft two stages with controlled state.
    s1 = rr / "stages" / "stage_a"
    (s1 / ".loop").mkdir(parents=True)
    (s1 / "reports").mkdir(parents=True)
    write_text(s1 / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(s1 / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(s1, overall_gate="PASS")
    _write_review(s1, verdict="PASS")
    _write_matrix(s1)

    s2 = rr / "stages" / "stage_b"
    (s2 / ".loop").mkdir(parents=True)
    (s2 / "reports").mkdir(parents=True)
    write_text(s2 / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(s2 / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(s2, overall_gate="FAIL")
    _write_review(s2, verdict="PASS")
    _write_matrix(s2)

    info = inspect_run_root(rr, repo_root=tmp_path)
    assert info["selected_stage"].name == "stage_b"
    assert "validation_gate" in info["selection_reason"]


def test_inspect_run_root_picks_first_stage_missing_gate_artifacts(tmp_path):
    rr = _make_run_root(tmp_path)
    s1 = rr / "stages" / "stage_started_no_validation"
    (s1 / ".loop").mkdir(parents=True)
    (s1 / "reports").mkdir(parents=True)
    write_text(s1 / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(s1 / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    # Has review + matrix but NO validation_summary -> appears started but missing gate.
    _write_review(s1, verdict="PASS")
    _write_matrix(s1)

    info = inspect_run_root(rr, repo_root=tmp_path)
    assert info["selected_stage"].name == "stage_started_no_validation"
    assert "missing gate artifacts" in info["selection_reason"]


# ---------------------------------------------------------------------------
# diagnose_run with --run-root only tests
# ---------------------------------------------------------------------------


def test_run_root_missing_stages_dir_classifies_missing_required_file(tmp_path):
    rr = tmp_path / "run_without_stages"
    rr.mkdir()
    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    assert _primary(report) == "MISSING_REQUIRED_FILE"
    assert report["subject"]["run_root"].endswith("run_without_stages")


def test_run_root_no_stage_dirs_classifies_missing_required_file(tmp_path):
    rr = _make_run_root(tmp_path)  # stages/ exists but no children
    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    assert _primary(report) == "MISSING_REQUIRED_FILE"


def test_run_root_one_stage_missing_validation_summary_classifies_missing_required_file(tmp_path):
    rr = _make_run_root(tmp_path)
    stage = rr / "stages" / "stage_no_validation"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    # validation_summary absent; matrix has clearly started the stage.
    _write_review(stage, verdict="PASS")
    _write_matrix(stage)
    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    assert _primary(report) == "MISSING_REQUIRED_FILE"


def test_run_root_validation_failure_stage_classifies_validation_gate_failed(tmp_path):
    rr = _make_run_root(tmp_path)
    stage = rr / "stages" / "bad_validation"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(stage, overall_gate="FAIL")
    _write_review(stage, verdict="PASS")
    _write_matrix(stage)
    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    assert _primary(report) == "VALIDATION_GATE_FAILED"
    # Subject carries run-root metadata + selected stage
    assert report["subject"]["selected_stage"].endswith("bad_validation")
    assert "stage_selection_reason" in report["subject"]


def test_run_root_review_failure_stage_classifies_review_gate_failed(tmp_path):
    rr = _make_run_root(tmp_path)
    stage = rr / "stages" / "bad_review"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(stage, overall_gate="PASS")
    _write_review(stage, verdict="NEEDS_PATCH")
    _write_matrix(stage)
    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    assert _primary(report) == "REVIEW_GATE_FAILED"


def test_run_root_unhealthy_completion_matrix_classifies_completion_matrix_unhealthy(tmp_path):
    rr = _make_run_root(tmp_path)
    stage = rr / "stages" / "bad_matrix"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(stage, overall_gate="PASS")
    _write_review(stage, verdict="PASS")
    _write_matrix(stage, overall="INCOMPLETE", recommended="APPROVE_FREEZE")
    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    assert _primary(report) == "COMPLETION_MATRIX_UNHEALTHY"


def test_run_root_pass_everywhere_but_no_signoff_classifies_human_signoff_required(tmp_path):
    rr = _make_run_root(tmp_path)
    stage = rr / "stages" / "needs_signoff"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(stage, overall_gate="PASS")
    _write_review(stage, verdict="PASS")
    _write_matrix(stage, overall="COMPLETE", recommended="APPROVE_FREEZE")
    # No .loop/human_signoff.yaml
    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    assert _primary(report) == "HUMAN_SIGNOFF_REQUIRED"


def test_run_root_multi_stage_selects_first_blocked_in_lexicographic_order(tmp_path):
    """When multiple stages exist and one has a failure marker, the first failing
    one (by lexicographic order, since no loop.yaml is configured) is selected.

    This guards against ordering by filesystem mtime.
    """
    rr = _make_run_root(tmp_path)
    # Stage "alpha" - passing
    a = rr / "stages" / "alpha"
    (a / ".loop").mkdir(parents=True)
    (a / "reports").mkdir(parents=True)
    write_text(a / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(a / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(a, overall_gate="PASS")
    _write_review(a, verdict="PASS")
    _write_matrix(a)
    # Stage "beta" - review FAILED
    b = rr / "stages" / "beta"
    (b / ".loop").mkdir(parents=True)
    (b / "reports").mkdir(parents=True)
    write_text(b / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(b / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(b, overall_gate="PASS")
    _write_review(b, verdict="NEEDS_PATCH")
    _write_matrix(b)
    # Stage "gamma" - matrix INCOMPLETE
    c = rr / "stages" / "gamma"
    (c / ".loop").mkdir(parents=True)
    (c / "reports").mkdir(parents=True)
    write_text(c / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(c / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(c, overall_gate="PASS")
    _write_review(c, verdict="PASS")
    _write_matrix(c, overall="INCOMPLETE", recommended="APPROVE_FREEZE")

    # Touch the failing one with old mtime to confirm we ignore mtime.
    import os
    old = 1_000_000_000
    os.utime(b, (old, old))

    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    assert _primary(report) == "REVIEW_GATE_FAILED"
    assert report["subject"]["selected_stage"].endswith("beta")
    assert report["subject"]["stage_order_source"].startswith("lexicographic")


def test_run_root_uses_project_loop_yaml_order(tmp_path):
    rr = _make_run_root(tmp_path)
    # Make stages in non-loop order on disk
    s_b = rr / "stages" / "stage_b"
    (s_b / ".loop").mkdir(parents=True)
    (s_b / "reports").mkdir(parents=True)
    write_text(s_b / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(s_b / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(s_b, overall_gate="FAIL")
    _write_review(s_b, verdict="PASS")
    _write_matrix(s_b)

    s_a = rr / "stages" / "stage_a"
    (s_a / ".loop").mkdir(parents=True)
    (s_a / "reports").mkdir(parents=True)
    write_text(s_a / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(s_a / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(s_a, overall_gate="PASS")
    _write_review(s_a, verdict="PASS")
    _write_matrix(s_a)

    repo = tmp_path / "repo"
    (repo / "projects" / "myproj").mkdir(parents=True)
    (repo / "projects" / "myproj" / "loop.yaml").write_text(
        "project: myproj\nstages:\n  - id: stage_a\n  - id: stage_b\n",
        encoding="utf-8",
    )

    report = diagnose_run(run_root=rr, project="myproj", repo_root=repo)
    # stage_a is first by loop.yaml order and passes; stage_b is the first failing one.
    assert _primary(report) == "VALIDATION_GATE_FAILED"
    assert report["subject"]["selected_stage"].endswith("stage_b")
    assert "projects/myproj/loop.yaml" in report["subject"]["stage_order_source"]


def test_run_root_explicit_stage_overrides_run_root_selection(tmp_path):
    """If both run_root and stage are passed, explicit --stage wins for classification.
    The report still carries run-root metadata as context.
    """
    rr = _make_run_root(tmp_path)
    bad = rr / "stages" / "bad_runroot_target"
    (bad / ".loop").mkdir(parents=True)
    (bad / "reports").mkdir(parents=True)
    write_text(bad / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(bad / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(bad, overall_gate="FAIL")
    _write_review(bad, verdict="PASS")
    _write_matrix(bad)

    # Explicit stage elsewhere - PASS.
    explicit = tmp_path / "explicit_stage"
    (explicit / ".loop").mkdir(parents=True)
    (explicit / "reports").mkdir(parents=True)
    write_text(explicit / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(explicit / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(explicit, overall_gate="PASS")
    _write_review(explicit, verdict="PASS")
    _write_matrix(explicit)

    report = diagnose_run(run_root=rr, stage=explicit, repo_root=tmp_path)
    assert _primary(report) != "VALIDATION_GATE_FAILED"
    # run-root meta evidence preserved even with explicit stage.
    labels = {e["label"] for e in report["evidence"]}
    assert "run_root" in labels
    assert "stages_dir" in labels
    assert "selected_stage" in labels
    # explicit_stage flag set; run_root and stage_id both recorded.
    assert report["subject"]["explicit_stage"] is True
    assert report["subject"]["stage_id"] == "explicit_stage"
    assert "run_root" in report["subject"]
    # The explicit stage is healthy -> it would be freeze-eligible except
    # for missing signoff (no human_signoff.yaml written), so primary is
    # HUMAN_SIGNOFF_REQUIRED. (UNKNOWN_FAILURE would indicate a regression.)
    assert _primary(report) == "HUMAN_SIGNOFF_REQUIRED"


def test_run_root_plus_explicit_stage_collects_run_root_evidence(tmp_path):
    """Regression test (TASK_024 patch): --run-root + explicit --stage still
    surfaces run_root discovery evidence + subject.run_root while keeping
    classification driven by the explicit stage.
    """
    rr = _make_run_root(tmp_path)
    bad = rr / "stages" / "bad_runroot_target"
    (bad / ".loop").mkdir(parents=True)
    (bad / "reports").mkdir(parents=True)
    write_text(bad / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(bad / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(bad, overall_gate="FAIL")
    _write_review(bad, verdict="PASS")
    _write_matrix(bad)

    explicit = tmp_path / "explicit_stage"
    (explicit / ".loop").mkdir(parents=True)
    (explicit / "reports").mkdir(parents=True)
    write_text(explicit / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(explicit / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(explicit, overall_gate="PASS")
    _write_review(explicit, verdict="PASS")
    _write_matrix(explicit)

    report = diagnose_run(run_root=rr, stage=explicit, repo_root=tmp_path)

    # 1. Explicit stage drives classification.
    assert report["subject"]["stage_id"] == "explicit_stage"
    assert report["subject"]["explicit_stage"] is True

    # 2. Run-root context still present in subject.
    assert "run_root" in report["subject"]

    # 3. Run-root discovery evidence collected.
    labels = {e["label"] for e in report["evidence"]}
    assert "run_root" in labels
    assert "stages_dir" in labels
    assert "selected_stage" in labels

    # 4. Primary stays driven by explicit stage — VALIDATION_GATE_FAILED
    #    is NOT the primary here, since explicit is healthy. The healthy
    #    explicit stage with no signoff -> HUMAN_SIGNOFF_REQUIRED.
    assert _primary(report) != "VALIDATION_GATE_FAILED"
    assert _primary(report) == "HUMAN_SIGNOFF_REQUIRED"


def test_run_root_happy_gates_missing_decision_and_checkpoint(tmp_path):
    """Regression test (TASK_024 patch): when a stage passes validation,
    review, completion matrix, and has valid signoff BUT is missing
    .loop/decision.json and .loop/checkpoint_manifest.json, diagnosis must
    NOT return UNKNOWN_FAILURE. It must surface MISSING_REQUIRED_FILE with
    evidence for both missing files.
    """
    from loop_engine.completion_matrix import build_completion_matrix

    rr = _make_run_root(tmp_path)
    stage = rr / "stages" / "missing_dec_ckpt"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(stage, overall_gate="PASS")
    _write_review(stage, verdict="PASS")
    # Use the real builder so basis_hashes match current on-disk files,
    # which makes the matrix fresh and triggers the new classifier.
    real_matrix = build_completion_matrix(stage)
    write_json(stage / "reports" / "completion_matrix.json", real_matrix)
    # Valid signoff, but no decision.json or checkpoint_manifest.json.
    signoff_path = stage / ".loop" / "human_signoff.yaml"
    signoff_path.write_text(
        yaml.safe_dump(_signoff(decision="APPROVE_FREEZE"), sort_keys=False),
        encoding="utf-8",
    )

    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    primary = _primary(report)

    # NOT UNKNOWN_FAILURE — must surface a concrete remediation.
    assert primary != "UNKNOWN_FAILURE"
    # Predicted classification: MISSING_REQUIRED_FILE.
    assert primary == "MISSING_REQUIRED_FILE"

    # Evidence must point at both missing files.
    paths_in_evidence = [e.get("path", "") for e in report["evidence"]]
    labels_in_evidence = {e.get("label", "") for e in report["evidence"]}
    assert any("decision.json" in p for p in paths_in_evidence)
    assert any("checkpoint_manifest.json" in p for p in paths_in_evidence)
    assert "decision" in labels_in_evidence
    assert "checkpoint_manifest" in labels_in_evidence

    # Recommendation is concrete (PRODUCE_BASIS_FILES via the existing rationale map).
    assert report["next_action"]["recommended"] == "PRODUCE_BASIS_FILES"


def test_run_root_diagnosis_does_not_create_or_modify_files(tmp_path):
    rr = _make_run_root(tmp_path)
    stage = rr / "stages" / "inert_stage"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(stage, overall_gate="FAIL")
    _write_review(stage, verdict="PASS")
    _write_matrix(stage)
    # Snapshot every file's mtime + content; everything must be unchanged after.
    def _snapshot() -> dict:
        snap = {}
        for p in sorted(rr.rglob("*")):
            if p.is_file():
                snap[p] = (p.stat().st_mtime, p.read_bytes())
        return snap

    before = _snapshot()
    diagnose_run(run_root=rr, repo_root=tmp_path)
    after = _snapshot()
    assert before == after


def test_run_root_report_validates_against_schema(tmp_path):
    rr = _make_run_root(tmp_path)
    stage = rr / "stages" / "schema_check"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(stage, overall_gate="PASS")
    _write_review(stage, verdict="PASS")
    _write_matrix(stage)

    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    # Must validate.
    validate_with_schema(report, "next_action_report")
    # Required run-root metadata present:
    for key in ("run_root", "selected_stage", "stage_selection_reason", "stage_order_source"):
        assert key in report["subject"], key


# ---------------------------------------------------------------------------
# CLI / write-reports smoke (TASK_024 acceptance)
# ---------------------------------------------------------------------------


def test_run_root_cli_writes_schema_valid_reports(tmp_path):
    """End-to-end CLI smoke test against --run-root only."""
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/diagnose_run_failure.py",
            "--run-root",
            str(Path("smoke_projects/mock_polynomial_loop")),
            "--output-dir",
            str(out),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    json_path = out / "next_action_report.json"
    md_path = out / "next_action_report.md"
    assert json_path.exists()
    assert md_path.exists()
    data = json.loads(json_path.read_text())
    validate_with_schema(data, "next_action_report")
    # Run-root subject metadata carried into CLI-generated JSON
    assert "run_root" in data["subject"]
    assert "selected_stage" in data["subject"]


def test_run_root_cli_json_only_and_markdown_only(tmp_path):
    out = tmp_path / "out_json_only"
    proc_json = subprocess.run(
        [
            sys.executable,
            "scripts/diagnose_run_failure.py",
            "--run-root",
            str(Path("smoke_projects/mock_polynomial_loop")),
            "--output-dir",
            str(out),
            "--json-only",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc_json.returncode == 0, proc_json.stderr
    assert (out / "next_action_report.json").exists()
    assert not (out / "next_action_report.md").exists()

    out2 = tmp_path / "out_md_only"
    proc_md = subprocess.run(
        [
            sys.executable,
            "scripts/diagnose_run_failure.py",
            "--run-root",
            str(Path("smoke_projects/mock_polynomial_loop")),
            "--output-dir",
            str(out2),
            "--markdown-only",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc_md.returncode == 0, proc_md.stderr
    assert not (out2 / "next_action_report.json").exists()
    assert (out2 / "next_action_report.md").exists()


def test_run_root_markdown_render_mentions_selected_stage(tmp_path):
    rr = _make_run_root(tmp_path)
    stage = rr / "stages" / "render_check"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(stage, overall_gate="FAIL")
    _write_review(stage, verdict="PASS")
    _write_matrix(stage)
    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    md = render_next_action_markdown(report)
    assert "Selected stage:" in md
    assert "render_check" in md
    assert "Selection reason:" in md


def test_run_root_write_next_action_reports_writes_both(tmp_path):
    rr = _make_run_root(tmp_path)
    stage = rr / "stages" / "writer_check"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + DC_CAVEAT)
    _write_validation(stage, overall_gate="PASS")
    _write_review(stage, verdict="PASS")
    _write_matrix(stage)
    report = diagnose_run(run_root=rr, repo_root=tmp_path)
    out = tmp_path / "out"
    json_path, md_path = write_next_action_reports(report, out)
    assert json_path.exists()
    assert md_path.exists()
    validate_with_schema(json.loads(json_path.read_text()), "next_action_report")
