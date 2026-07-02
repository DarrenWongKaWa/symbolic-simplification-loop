from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path

import yaml

from loop_engine.config import write_json


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_autonomous_loop import run_hypothesis_search_if_enabled  # noqa: E402


def run_runner(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def test_loop_candidate_promotion_profile_is_l2_only_and_pre_ibp():
    profile_path = REPO_ROOT / "profiles" / "sigma_abc_loop_candidate_promotion.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))

    assert profile["current_checkpoint_override"] == "sigma_abc_012b_loop_hypothesis_generation"
    assert profile["allowed_stage_ids"] == ["sigma_abc_012c_loop_orbit_canonicalization_promotion"]
    assert profile["autonomy"]["max_stages_per_run"] == 1
    assert profile["autonomy"]["stop_after_stage"] == "sigma_abc_012c_loop_orbit_canonicalization_promotion"
    assert profile["autonomy"]["allow_ibp_reduction"] is False
    assert profile["hypothesis_search"]["promote_candidates"] is True
    assert profile["hypothesis_search"]["allow_ibp_conjectures"] is False
    assert profile["hypothesis_search"]["allow_total_derivative_conjectures"] is False
    assert profile["review_policy"]["require_l2_for_candidate_promotion"] is True
    assert profile["review_policy"]["lanes"]["L2_FULL_PANEL"]["reviewers"] == [
        "AlgebraReviewer",
        "PhysicsReviewer",
        "SoftwareReviewer",
        "ScientificMetaReviewer",
    ]


def test_loop_candidate_promotion_dry_run_targets_012c_with_real_runtime():
    result = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_loop_candidate_promotion",
        "--dry-run",
        "--from-current-checkpoint",
    )
    out = result.stdout

    assert "ProfileStatus -> COMPLETE" in out
    assert "CurrentCheckpoint -> sigma_abc_012b_loop_hypothesis_generation" in out
    assert "NextStage -> sigma_abc_012c_loop_orbit_canonicalization_promotion" in out
    assert "StopBeforeIBP -> True" in out
    assert "RealAgentInvocationRequired -> True" in out
    assert "ProductionStubForbidden -> True" in out
    assert "AgentRuntimeStatus -> AVAILABLE" in out
    assert "Adapter -> command" in out
    assert "ProductionRunAllowed -> True" in out
    assert "ReviewLane -> L2_FULL_PANEL" in out
    assert "FullPanelRequired -> True" in out
    assert "OpenReviewDebt -> False" in out
    assert "CandidatePromotionAllowed -> True" in out
    assert "IBPAllowed -> False" in out
    assert "TotalDerivativePromotionAllowed -> False" in out
    assert "StopBeforeGlobalAssembly -> True" in out
    assert "- sigma_abc_012c_loop_orbit_canonicalization_promotion" in out
    assert "- sigma_abc_013_global_pre_ibp_assembly" not in out


def test_sigma_abc_012c_does_not_promote_toy_candidate(tmp_path: Path):
    stage = tmp_path / "sigma_abc_012c_loop_orbit_canonicalization_promotion"
    for subdir in [".loop", "output", "reports", "validation"]:
        (stage / subdir).mkdir(parents=True, exist_ok=True)
    validation = {
        "stage_name": stage.name,
        "overall_gate": "PASS",
        "checks": [],
    }
    write_json(stage / ".loop" / "validation_summary.json", validation)
    write_json(stage / ".loop" / "metrics.json", {"stage_name": stage.name})

    run_hypothesis_search_if_enabled(
        stage,
        {"id": stage.name},
        {
            "hypothesis_search": {
                "enabled": True,
                "promote_candidates": True,
                "exploration_only": False,
                "allow_mock_candidates": False,
            }
        },
    )

    updated = json.loads((stage / ".loop" / "validation_summary.json").read_text(encoding="utf-8"))
    assert updated["overall_gate"] == "FAIL"
    assert updated["CandidateValidationStatus"] == "REJECTED"
    assert updated["VerifiedCandidatePromoted"] is False
    assert not (stage / "output" / "promoted_candidate_manifest.json").exists()
    assert (stage / "failed_conjectures" / "conjecture_002" / "failure_metadata.json").exists()
