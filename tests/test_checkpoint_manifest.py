from __future__ import annotations

from pathlib import Path

import pytest

from loop_engine.checkpoint import build_checkpoint_manifest, freeze_checkpoint
from loop_engine.completion_matrix import write_completion_matrix
from loop_engine.config import write_json, write_text
from loop_engine.human_signoff import build_signoff_from_decision, write_signoff


def make_stage(tmp_path: Path) -> Path:
    stage = tmp_path / "project" / "stages" / "000_raw_import"
    (stage / ".loop").mkdir(parents=True)
    (stage / "input_snapshots").mkdir()
    (stage / "output").mkdir()
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n")
    write_text(stage / "output" / "result.wl", "Result -> 0\n")
    write_json(
        stage / ".loop" / "validation_summary.json",
        {
            "stage_name": "000_raw_import",
            "overall_gate": "PASS",
            "identity_type": "OldMinusNewZero",
            "checks": [{"name": "exact", "expected": "0", "actual": "0", "gate": "PASS"}],
            "protected_regressions": [],
            "caveats": [],
        },
    )
    write_json(
        stage / ".loop" / "review_result.json",
        {
            "verdict": "PASS",
            "stage_name": "000_raw_import",
            "mathematical_status": {
                "exact_reconstruction": True,
                "simplification_real": True,
                "regression_preserved": True,
                "overclaim_detected": False,
            },
            "blocking_issues": [],
            "nonblocking_caveats": [],
            "allowed_claims": ["allowed"],
            "forbidden_claims": ["forbidden"],
            "next_action": "FREEZE",
            "suggested_next_stage": None,
            "patch_instructions": [],
        },
    )
    write_completion_matrix(stage)
    write_signoff(stage, build_signoff_from_decision(stage, "APPROVE_FREEZE", reason=None, signed_by="pytest"))
    return stage


def test_checkpoint_manifest_contains_hashes_and_byte_counts(tmp_path: Path):
    stage = make_stage(tmp_path)
    manifest = build_checkpoint_manifest(stage)
    assert manifest["stage_name"] == "000_raw_import"
    assert any(record["path"] == "output/result.wl" for record in manifest["files"])
    assert all(record["bytes"] >= 0 and record["sha256"] for record in manifest["files"])


def test_freeze_checkpoint_copies_stage(tmp_path: Path):
    stage = make_stage(tmp_path)
    target = freeze_checkpoint(stage)
    assert target.exists()
    assert (target / ".loop" / "checkpoint_manifest.json").exists()


def test_freeze_rejects_failed_validation(tmp_path: Path):
    stage = make_stage(tmp_path)
    write_json(
        stage / ".loop" / "validation_summary.json",
        {
            "stage_name": "000_raw_import",
            "overall_gate": "FAIL",
            "checks": [{"name": "exact", "gate": "FAIL"}],
        },
    )
    with pytest.raises(RuntimeError):
        freeze_checkpoint(stage)
