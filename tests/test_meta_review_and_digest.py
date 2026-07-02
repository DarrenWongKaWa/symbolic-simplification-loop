from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from loop_engine.checkpoint import build_checkpoint_manifest
from loop_engine.config import write_json, write_text
from loop_engine.decision import decide_next_action
from loop_engine.schemas import load_and_validate


REPO_ROOT = Path(__file__).resolve().parents[1]


def make_reviewed_stage(tmp_path: Path, *, validation_gate: str = "PASS", review_verdict: str = "PASS") -> Path:
    stage = tmp_path / "project" / "stages" / "mock_stage"
    for folder in [".loop/reviewer_results", "reports", "output", "validation"]:
        (stage / folder).mkdir(parents=True, exist_ok=True)
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\nDo not claim full tensorial sigma_abc correctness.\n")
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n\nGoal: mock exact identity.\n")
    write_text(stage / "EXECUTION_REPORT.md", "# Execution Report\n\nOld - New = 0.\n")
    write_text(stage / "review_packet.md", "# Review Packet\n\nDCProjectionTo1D -> INHERITED_PASS.\n")
    validation = {
        "stage_name": stage.name,
        "overall_gate": validation_gate,
        "identity_type": "OldMinusNewZero",
        "checks": [{"name": "exact", "expected": 0, "actual": 0, "gate": validation_gate}],
        "protected_regressions": [{"name": "sigma_xxx_projection", "gate": "PASS"}],
        "caveats": ["DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."],
    }
    write_json(stage / ".loop" / "validation_summary.json", validation)
    write_json(stage / ".loop" / "metrics.json", {"stage_name": stage.name, "deltas": {"OldMinusNew": "0"}})
    review = {
        "verdict": review_verdict,
        "stage_name": stage.name,
        "reviewer_role": "IntegratorReview",
        "review_scope": "routine_branch",
        "mathematical_status": {
            "exact_reconstruction": validation_gate == "PASS",
            "simplification_real": True,
            "regression_preserved": True,
            "overclaim_detected": False,
        },
        "blocking_issues": [],
        "nonblocking_caveats": [],
        "allowed_claims": ["PASS as mock identity stage."],
        "forbidden_claims": ["Do not claim full tensorial sigma_abc correctness."],
        "next_action": "FREEZE",
        "suggested_next_stage": None,
        "patch_instructions": [],
    }
    write_json(stage / ".loop" / "review_result.json", review)
    for reviewer in ["algebra_reviewer", "physics_reviewer", "software_reviewer"]:
        write_json(stage / ".loop" / "reviewer_results" / f"{reviewer}.json", review | {"reviewer_role": reviewer})
    return stage


def run_runner(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=REPO_ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def test_scientific_metareviewer_blocks_validation_fail(tmp_path: Path):
    stage = make_reviewed_stage(tmp_path, validation_gate="FAIL", review_verdict="PASS")
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_scientific_metareviewer.py"), "--stage", str(stage)],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    meta = load_and_validate(Path(result.stdout.strip()), "meta_review_result")
    assert meta["verdict"] != "PASS"
    decision = decide_next_action(
        json.loads((stage / ".loop" / "validation_summary.json").read_text()),
        json.loads((stage / ".loop" / "review_result.json").read_text()),
        meta_review=meta,
    )
    assert decision.freeze_allowed is False


def test_scientific_metareviewer_preserves_dc_caveat(tmp_path: Path):
    stage = make_reviewed_stage(tmp_path)
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_scientific_metareviewer.py"), "--stage", str(stage)],
        cwd=REPO_ROOT,
        check=True,
    )
    meta = load_and_validate(stage / ".loop" / "meta_review_result.json", "meta_review_result")
    assert meta["boundary_audit"]["dc_caveat_preserved"] is True
    assert any("DCProjectionTo1D" in caveat for caveat in meta["caveats_to_preserve"])
    assert (stage / "reports" / "human_readable_review.md").exists()


def test_meta_review_blocks_overclaim(tmp_path: Path):
    stage = make_reviewed_stage(tmp_path)
    write_text(stage / "review_packet.md", "# Review Packet\n\nWe prove full tensorial sigma_abc correctness.\n")
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_scientific_metareviewer.py"), "--stage", str(stage)],
        cwd=REPO_ROOT,
        check=True,
    )
    meta = json.loads((stage / ".loop" / "meta_review_result.json").read_text())
    assert meta["verdict"] in {"NEEDS_PATCH", "FAILED"}
    assert meta["boundary_audit"]["full_tensorial_claim_detected"] is True


def test_stage_digest_created_for_mock_stage(tmp_path: Path):
    stage = make_reviewed_stage(tmp_path)
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_scientific_metareviewer.py"), "--stage", str(stage)],
        cwd=REPO_ROOT,
        check=True,
    )
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "build_stage_digest.py"), "--stage", str(stage)],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert (stage / "reports" / "stage_summary.md").exists()
    assert (stage / "reports" / "stage_summary.tex").exists()
    assert "stage_summary" in result.stdout


def test_stage_digest_included_in_checkpoint_manifest(tmp_path: Path):
    stage = make_reviewed_stage(tmp_path)
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "run_scientific_metareviewer.py"), "--stage", str(stage)], cwd=REPO_ROOT, check=True)
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "build_stage_digest.py"), "--stage", str(stage)], cwd=REPO_ROOT, check=True)
    manifest = build_checkpoint_manifest(stage)
    file_paths = {record["path"] for record in manifest["files"]}
    assert ".loop/meta_review_result.json" in file_paths
    assert "reports/human_readable_review.md" in file_paths
    assert "reports/stage_summary.md" in file_paths
    assert "reports/stage_summary.tex" in file_paths
    assert "meta_review_result" in manifest
    assert "stage_digest_artifacts" in manifest


def test_autonomous_runner_runs_meta_review_and_digest():
    result = run_runner("--project", "mock", "--profile", "test_safe_loop", "--clean")
    assert result.returncode == 0
    stage = REPO_ROOT / "autonomous_runs" / "mock" / "stages" / "mock_001_identity"
    assert (stage / ".loop" / "meta_review_result.json").exists()
    assert (stage / "reports" / "human_readable_review.md").exists()
    assert (stage / "reports" / "stage_summary.md").exists()
    assert (stage / "reports" / "stage_summary.tex").exists()
    decision = json.loads((stage / ".loop" / "decision.json").read_text())
    assert decision["action"] == "FREEZE"
    manifest = json.loads((stage / ".loop" / "checkpoint_manifest.json").read_text())
    assert "reports/stage_summary.md" in {record["path"] for record in manifest["files"]}
