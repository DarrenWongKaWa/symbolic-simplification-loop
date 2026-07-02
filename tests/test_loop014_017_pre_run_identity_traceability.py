from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from loop_engine.config import read_json, write_json, write_text
from loop_engine.schemas import schema_path, validate_with_schema


REPO_ROOT = Path(__file__).resolve().parents[1]
DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


def _stage(tmp_path: Path, *, stage_id: str = "sigma_abc_012c_real_loop_candidate_preparation") -> Path:
    stage = tmp_path / "autonomous_runs" / "sigma_abc" / "stages" / stage_id
    for folder in [".loop", "reports", "output", "validation"]:
        (stage / folder).mkdir(parents=True, exist_ok=True)
    write_text(
        stage / "STAGE_PLAN.md",
        """# Stage Plan

Goal: Prepare real loop candidate artifacts from upstream ledgers.

dependencies:
- sigma_abc_012a_loop_sector_inventory
- sigma_abc_012b_loop_hypothesis_generation

expected_outputs:
- output/loop_candidate_preparation.json
- reports/loop_candidate_preparation_report.md
""",
    )
    write_text(stage / "CLAIM_BOUNDARY.md", f"# Claim Boundary\n\n{DC_CAVEAT}\n\nNo IBP.\n")
    write_text(stage / "review_packet.md", f"# Review Packet\n\n{DC_CAVEAT}\n")
    write_json(
        stage / ".loop" / "validation_summary.json",
        {
            "stage_name": stage.name,
            "overall_gate": "PASS",
            "identity_type": "ProjectionRegression",
            "checks": [
                {"name": "Stage012AArtifactPresent", "expected": True, "actual": True, "gate": "PASS"},
                {"name": "NoCandidatePromoted", "expected": True, "actual": True, "gate": "PASS"},
                {"name": "NoIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
                {"name": "XXXProjectionRegression", "expected": 0, "actual": 0, "gate": "PASS"},
            ],
            "protected_regressions": [{"name": "ProtectedSigmaXXXBenchmark", "gate": "PASS"}],
            "caveats": [DC_CAVEAT],
        },
    )
    write_json(
        stage / ".loop" / "review_result.json",
        {
            "verdict": "PASS",
            "stage_name": stage.name,
            "reviewer_role": "IntegratorReview",
            "review_scope": "routine_branch",
            "mathematical_status": {
                "exact_reconstruction": True,
                "simplification_real": True,
                "regression_preserved": True,
                "overclaim_detected": False,
            },
            "blocking_issues": [],
            "nonblocking_caveats": [DC_CAVEAT],
            "allowed_claims": ["PASS as preparation gate."],
            "forbidden_claims": ["Do not claim full tensorial sigma_abc correctness."],
            "next_action": "FREEZE",
            "suggested_next_stage": None,
            "patch_instructions": [],
        },
    )
    write_json(stage / ".loop" / "metrics.json", {"stage_name": stage.name, "notes": []})
    write_text(stage / "output" / "loop_candidate_preparation.json", "{}\n")
    write_text(stage / "reports" / "loop_candidate_preparation_report.md", "# Report\n")
    return stage


def _profile() -> dict:
    return {
        "profile": "sigma_abc_loop_candidate_preparation",
        "allowed_stage_ids": ["sigma_abc_012c_real_loop_candidate_preparation"],
        "autonomy": {
            "allow_ibp_reduction": False,
            "allow_kernel_fusion": False,
            "allow_physics_simplification": False,
        },
        "permanent_caveats": [DC_CAVEAT],
        "forbidden_actions": [
            "candidate promotion",
            "global assembly",
            "IBP",
            "total derivative reduction",
            "full tensorial sigma_abc correctness claim",
        ],
    }


def test_pre_run_brief_schema_generation_audit_and_digest(tmp_path: Path):
    from loop_engine.pre_run_brief import audit_pre_run_brief, build_pre_run_brief, write_pre_run_brief
    from loop_engine.stage_digest import build_stage_digest

    stage = _stage(tmp_path)
    assert schema_path("pre_run_brief").exists()
    brief = build_pre_run_brief(stage, profile=_profile())
    validate_with_schema(brief, "pre_run_brief")
    assert brief["task_understanding"]["claim_boundary_acknowledged"] is True
    assert DC_CAVEAT in brief["task_understanding"]["caveats_acknowledged"]
    assert "IBP" in brief["task_understanding"]["forbidden_actions"]

    path = write_pre_run_brief(stage, profile=_profile())
    assert path == stage / ".loop" / "pre_run_brief.json"
    assert (stage / "reports" / "agent_self_understanding.md").exists()
    audit = audit_pre_run_brief(stage, read_json(path), profile=_profile())
    assert audit["hard_stop"] is False
    assert audit["gate"] == "PASS"

    build_stage_digest(stage)
    digest = (stage / "reports" / "stage_summary.md").read_text(encoding="utf-8")
    assert "Pre-run brief" in digest
    assert "ClaimBoundaryAcknowledged -> True" in digest


def test_pre_run_brief_warns_and_hard_stops_explicit_forbidden_intent(tmp_path: Path):
    from loop_engine.pre_run_brief import audit_pre_run_brief, build_pre_run_brief

    stage = _stage(tmp_path)
    brief = build_pre_run_brief(stage, profile=_profile())
    brief["task_understanding"]["expected_outputs"] = []
    audit = audit_pre_run_brief(stage, brief, profile=_profile())
    assert audit["gate"] == "WARN"
    assert any("expected outputs" in warning for warning in audit["warnings"])

    brief["task_understanding"]["goal_restated"] = "I will start IBP and claim full tensorial sigma_abc correctness."
    audit = audit_pre_run_brief(stage, brief, profile=_profile())
    assert audit["hard_stop"] is True
    assert audit["gate"] == "FAIL"


def test_pre_run_gate_blocks_invalid_and_allows_valid_without_reviewer(tmp_path: Path):
    from loop_engine.pre_run_brief import write_pre_run_brief
    from loop_engine.pre_run_gate import check_pre_run_gate

    stage = _stage(tmp_path)
    missing = check_pre_run_gate(stage, profile=_profile())
    assert missing["execution_allowed"] is False
    assert any("pre_run_brief" in reason for reason in missing["blocking_reasons"])

    write_pre_run_brief(stage, profile=_profile())
    allowed = check_pre_run_gate(stage, profile=_profile())
    assert allowed["execution_allowed"] is True
    assert allowed["reviewer_consulted"] is False
    validate_with_schema(allowed, "pre_run_gate_result")

    bad = read_json(stage / ".loop" / "pre_run_brief.json")
    bad["stage_id"] = "wrong_stage"
    write_json(stage / ".loop" / "pre_run_brief.json", bad)
    blocked = check_pre_run_gate(stage, profile=_profile())
    assert blocked["execution_allowed"] is False
    assert any("stage_id" in reason for reason in blocked["blocking_reasons"])


def test_scientific_identity_library_rendering_and_digest(tmp_path: Path):
    from loop_engine.scientific_identities import (
        load_identity_library,
        render_stage_scientific_identities,
        write_stage_scientific_identities,
    )
    from loop_engine.stage_digest import build_stage_digest

    stage = _stage(tmp_path)
    library = load_identity_library("sigma_abc")
    assert any(identity["label"] == "XXX projection regression" for identity in library["identities"])
    rendered = render_stage_scientific_identities(stage, project="sigma_abc")
    assert "DCProjectionTo1D" in rendered["markdown"]
    assert "\\mathcal{K}_{\\mathrm{IBP}}" in rendered["tex"]
    assert rendered["validation_status_changed"] is False

    paths = write_stage_scientific_identities(stage, project="sigma_abc")
    assert paths["markdown"].exists()
    assert paths["tex"].exists()
    build_stage_digest(stage)
    digest = (stage / "reports" / "stage_summary.md").read_text(encoding="utf-8")
    assert "Scientific identities" in digest
    assert "XXX projection regression" in digest


def test_identity_traceability_links_and_blocks_unlinked_identity(tmp_path: Path):
    from loop_engine.identity_traceability import audit_identity_traceability, write_identity_traceability
    from loop_engine.scientific_identities import write_stage_scientific_identities

    stage = _stage(tmp_path)
    identities = write_stage_scientific_identities(stage, project="sigma_abc")
    trace = audit_identity_traceability(stage, identities=identities["payload"])
    validate_with_schema(trace, "identity_traceability")
    by_label = {item["identity_label"]: item for item in trace["items"]}
    assert by_label["XXX projection regression"]["trace_status"] == "LINKED"
    assert by_label["DC inherited caveat"]["trace_status"] == "INFORMATIONAL_ONLY"
    assert trace["identity_traceability_gate"] == "PASS"

    payload = identities["payload"]
    payload["identities"].append(
        {
            "label": "Unlinked blocking identity",
            "latex": "X=0",
            "check": "MissingCheck",
            "role": "reconstruction",
            "blocking": True,
        }
    )
    blocked = audit_identity_traceability(stage, identities=payload)
    assert blocked["identity_traceability_gate"] == "FAIL"
    assert any(item["trace_status"] == "MISSING_CHECK" for item in blocked["items"])

    path = write_identity_traceability(stage, identities=identities["payload"])
    assert path == stage / ".loop" / "identity_traceability.json"


def test_identity_traceability_blocks_freeze_and_checkpoint_manifest_includes_it(tmp_path: Path):
    from loop_engine.checkpoint import build_checkpoint_manifest
    from loop_engine.completion_matrix import write_completion_matrix
    from loop_engine.human_signoff import build_signoff_from_decision, write_signoff
    from loop_engine.identity_traceability import write_identity_traceability
    from loop_engine.scientific_identities import write_stage_scientific_identities
    from loop_engine.state import freeze_preconditions

    stage = _stage(tmp_path)
    identities = write_stage_scientific_identities(stage, project="sigma_abc")
    trace_path = write_identity_traceability(stage, identities=identities["payload"])
    write_completion_matrix(stage)
    write_signoff(
        stage,
        build_signoff_from_decision(
            stage,
            "APPROVE_FREEZE_WITH_CAVEAT",
            reason="All deterministic gates pass with inherited DC caveat.",
            signed_by="pytest",
            accepted_caveats=[DC_CAVEAT],
        ),
    )
    assert freeze_preconditions(stage, read_json(stage / ".loop" / "validation_summary.json"), read_json(stage / ".loop" / "review_result.json")) == []
    manifest = build_checkpoint_manifest(stage)
    assert manifest["identity_traceability"] == ".loop/identity_traceability.json"
    assert any(record["path"] == ".loop/identity_traceability.json" for record in manifest["files"])

    trace = read_json(trace_path)
    trace["identity_traceability_gate"] = "FAIL"
    trace["blocking_failures"] = ["Unlinked blocking identity"]
    write_json(trace_path, trace)
    reasons = freeze_preconditions(stage, read_json(stage / ".loop" / "validation_summary.json"), read_json(stage / ".loop" / "review_result.json"))
    assert any("identity_traceability" in reason for reason in reasons)


def test_cli_scripts_for_pre_run_and_traceability(tmp_path: Path):
    stage = _stage(tmp_path)
    profile_path = tmp_path / "profile.yaml"
    import yaml

    profile_path.write_text(yaml.safe_dump(_profile()), encoding="utf-8")
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "build_pre_run_brief.py"), "--stage", str(stage), "--profile", str(profile_path)],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_pre_run_gate.py"), "--stage", str(stage), "--profile", str(profile_path)],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "audit_identity_traceability.py"), "--stage", str(stage), "--project", "sigma_abc"],
        cwd=REPO_ROOT,
        check=True,
    )
    assert (stage / ".loop" / "pre_run_brief.json").exists()
    assert (stage / ".loop" / "pre_run_gate_result.json").exists()
    assert (stage / ".loop" / "identity_traceability.json").exists()
