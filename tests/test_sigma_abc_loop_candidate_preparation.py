from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_autonomous_loop import execute_sigma_abc_loop_candidate_preparation_stage, execute_sigma_abc_prefusion_stage  # noqa: E402


def run_runner(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def test_loop_candidate_preparation_profile_targets_real_candidate_prep_stage():
    profile_path = REPO_ROOT / "profiles" / "sigma_abc_loop_candidate_preparation.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))

    assert profile["current_checkpoint_override"] == "sigma_abc_012b_loop_hypothesis_generation"
    assert profile["allowed_stage_ids"] == ["sigma_abc_012c_real_loop_candidate_preparation"]
    assert profile["stage_intent"] == "candidate_preparation_only"
    assert profile["candidate_promotion_allowed"] is False
    assert profile["autonomy"]["allow_ibp_reduction"] is False
    assert profile["autonomy"]["allow_kernel_fusion"] is False
    assert profile["hypothesis_search"]["enabled"] is False
    assert profile["review_policy"]["lanes"]["L1_COMPACT_META"]["reviewers"] == ["ScientificMetaReviewer"]


def test_loop_candidate_preparation_dry_run_has_identity_guard():
    result = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_loop_candidate_preparation",
        "--dry-run",
        "--from-current-checkpoint",
    )

    out = result.stdout
    assert "NextStage -> sigma_abc_012c_real_loop_candidate_preparation" in out
    assert "CandidatePromotionAllowed -> False" in out
    assert "IBPAllowed -> False" in out
    assert "TotalDerivativePromotionAllowed -> False" in out
    assert "ExpectedProfile -> sigma_abc_loop_candidate_preparation" in out
    assert "ExpectedStage -> sigma_abc_012c_real_loop_candidate_preparation" in out
    assert "ReportIdentityCheck -> PASS" in out


def test_stage012a_and_stage012b_prefusion_export_artifact_contracts(tmp_path):
    stage012a = tmp_path / "sigma_abc_012a_loop_sector_inventory"
    stage012b = tmp_path / "sigma_abc_012b_loop_hypothesis_generation"
    for stage in (stage012a, stage012b):
        stage.mkdir(parents=True)

    execute_sigma_abc_prefusion_stage(stage012a, {"goal": "loop inventory"}, {"protected_benchmark": "sigma_xxx_projection"})
    execute_sigma_abc_prefusion_stage(stage012b, {"goal": "loop hypothesis"}, {"protected_benchmark": "sigma_xxx_projection"})

    for relative in [
        "output/loop_sector_ledger.csv",
        "output/loop_orbit_inventory.json",
        "output/loop_raw_sector_table.wl",
        "validation/loop_inventory_validation.json",
    ]:
        assert (stage012a / relative).exists()
    for relative in [
        "output/loop_hypothesis_ledger.json",
        "output/loop_candidate_requirements.json",
        ".loop/conjectures/conjecture_ledger.json",
        "reports/loop_hypothesis_generation_summary.md",
    ]:
        assert (stage012b / relative).exists()

    assert json.loads((stage012a / ".loop" / "validation_summary.json").read_text())["Stage012AArtifactPresent"] is True
    assert json.loads((stage012b / ".loop" / "validation_summary.json").read_text())["Stage012BArtifactPresent"] is True


def test_loop_candidate_preparation_blocks_when_stage012_inputs_are_absent(tmp_path):
    run_base = tmp_path / "autonomous_runs"
    stage_dir = run_base / "sigma_abc" / "stages" / "sigma_abc_012c_real_loop_candidate_preparation"

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"),
            "--project",
            "sigma_abc",
            "--profile",
            "sigma_abc_loop_candidate_preparation",
            "--from-current-checkpoint",
            "--auto-patch",
            "--write-digests",
            "--max-stages",
            "1",
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "LOOP_RUN_ROOT": str(run_base)},
        check=True,
        text=True,
        capture_output=True,
    )
    assert "AUTONOMOUS_LOOP_RUN_REPORT.md" in result.stdout

    validation_path = stage_dir / ".loop" / "validation_summary.json"
    assert validation_path.exists()
    validation = json.loads(validation_path.read_text(encoding="utf-8"))

    assert validation["overall_gate"] == "FAIL"
    assert validation["ReportIdentityCheck"] == "PASS"
    assert validation["CandidateSource"] == "sigma_abc_loop_sector"
    assert validation["ToyCandidateDetected"] is False
    assert validation["MockCandidateDetected"] is False
    assert validation["Stage012AArtifactPresent"] is False
    assert validation["Stage012BArtifactPresent"] is False
    assert validation["UsesStage012ALoopLedger"] is False
    assert validation["UsesStage012BHypothesisLedger"] is False
    assert validation["PreparationStatus"] == "BLOCKED_MISSING_STAGE012AB_ARTIFACT_CONTRACT"
    assert validation["NoCandidatePromoted"] is True
    assert validation["NoIBPStarted"] is True
    assert validation["NoTotalDerivativeIntroduced"] is True
    assert (stage_dir / ".loop" / "pre_run_gate_result.json").exists()
    pre_run_gate = json.loads((stage_dir / ".loop" / "pre_run_gate_result.json").read_text(encoding="utf-8"))
    assert pre_run_gate["execution_allowed"] is True
    assert not (stage_dir / "output" / "promoted_candidate_manifest.json").exists()
    for relative in [
        "output/loop_candidate_preparation.json",
        "output/loop_candidate_requirements_resolved.json",
        "output/loop_raw_sector_table.wl",
        "output/loop_orbit_dictionary.wl",
        "output/loop_candidate_expression.wl",
        "output/loop_candidate_basis_table.wl",
        "validation/loop_candidate_preparation_validation.json",
        "validation/loop_candidate_validation.wl",
        "validation/loop_xxx_projection_regression.wl",
    ]:
        assert (stage_dir / relative).exists(), f"{relative} should be produced by preparation readiness check"


def test_loop_candidate_preparation_requires_complete_stage012_artifact_contract(tmp_path):
    run_root = tmp_path / "run"
    stage_dir = run_root / "stages" / "sigma_abc_012c_real_loop_candidate_preparation"
    stage_dir.mkdir(parents=True)

    stage012a = run_root / "stages" / "sigma_abc_012a_loop_sector_inventory"
    stage012b = run_root / "stages" / "sigma_abc_012b_loop_hypothesis_generation"
    (stage012a / "output").mkdir(parents=True)
    (stage012a / "validation").mkdir(parents=True)
    (stage012b / "output").mkdir(parents=True)
    (stage012b / ".loop" / "conjectures").mkdir(parents=True)
    (stage012b / "reports").mkdir(parents=True)

    (stage012a / "output" / "loop_sector_ledger.csv").write_text("orbit,count\nraw,1\n", encoding="utf-8")
    (stage012b / "output" / "loop_hypothesis_ledger.json").write_text("{}", encoding="utf-8")

    validation = execute_sigma_abc_loop_candidate_preparation_stage(
        stage_dir,
        {"id": "sigma_abc_012c_real_loop_candidate_preparation"},
        {"protected_benchmark": "sigma_xxx_projection"},
    )

    assert validation["overall_gate"] == "FAIL"
    assert validation["Stage012AArtifactPresent"] is False
    assert validation["Stage012BArtifactPresent"] is False
    assert validation["UsesStage012ALoopLedger"] is False
    assert validation["UsesStage012BHypothesisLedger"] is False


def test_loop_candidate_preparation_resolves_complete_stage012_contract_from_checkpoints(tmp_path):
    run_root = tmp_path / "run"
    stage_dir = run_root / "stages" / "sigma_abc_012c_real_loop_candidate_preparation"
    stage_dir.mkdir(parents=True)

    checkpoint_a = run_root / "checkpoints" / "sigma_abc_012a_loop_sector_inventory_2026-07-01T00-00-00+00-00"
    checkpoint_b = run_root / "checkpoints" / "sigma_abc_012b_loop_hypothesis_generation_2026-07-01T00-00-00+00-00"
    for checkpoint in (checkpoint_a, checkpoint_b):
        (checkpoint / ".loop").mkdir(parents=True)
        (checkpoint / "output").mkdir(parents=True)
        (checkpoint / "validation").mkdir(parents=True)
        (checkpoint / "reports").mkdir(parents=True)

    (checkpoint_a / "output" / "loop_sector_ledger.csv").write_text("orbit,count\nraw,1\n", encoding="utf-8")
    (checkpoint_a / "output" / "loop_orbit_inventory.json").write_text('{"orbits": []}', encoding="utf-8")
    (checkpoint_a / "output" / "loop_raw_sector_table.wl").write_text("LoopRawSectorTable = {};\n", encoding="utf-8")
    (checkpoint_a / "validation" / "loop_inventory_validation.json").write_text('{"OverallGate":"PASS"}', encoding="utf-8")

    (checkpoint_b / "output" / "loop_hypothesis_ledger.json").write_text('{"hypotheses": []}', encoding="utf-8")
    (checkpoint_b / "output" / "loop_candidate_requirements.json").write_text('{"requirements": []}', encoding="utf-8")
    (checkpoint_b / ".loop" / "conjectures").mkdir(exist_ok=True)
    (checkpoint_b / ".loop" / "conjectures" / "conjecture_001.json").write_text('{"conjecture_id":"loop_001"}', encoding="utf-8")
    (checkpoint_b / ".loop" / "conjectures" / "conjecture_ledger.json").write_text('{"conjecture_count":1}', encoding="utf-8")
    (checkpoint_b / "reports" / "loop_hypothesis_generation_summary.md").write_text("# Loop Hypothesis Generation\n", encoding="utf-8")

    validation = execute_sigma_abc_loop_candidate_preparation_stage(
        stage_dir,
        {"id": "sigma_abc_012c_real_loop_candidate_preparation"},
        {"protected_benchmark": "sigma_xxx_projection"},
    )

    assert validation["overall_gate"] == "PASS"
    assert validation["Stage012AArtifactPresent"] is True
    assert validation["Stage012BArtifactPresent"] is True
    assert validation["UsesStage012ALoopLedger"] is True
    assert validation["UsesStage012BHypothesisLedger"] is True
    assert validation["PreparationStatus"] == "READY_FOR_012C_PROMOTION_RETRY"
    assert validation["NoCandidatePromoted"] is True
    assert validation["NoIBPStarted"] is True
    assert validation["NoTotalDerivativeIntroduced"] is True
    assert (stage_dir / "output" / "loop_candidate_preparation.json").exists()
    assert (stage_dir / "output" / "loop_candidate_requirements_resolved.json").exists()
    assert (stage_dir / "validation" / "loop_candidate_preparation_validation.json").exists()
    assert (stage_dir / "input_snapshots" / "stage012a" / "output" / "loop_sector_ledger.csv").exists()
    assert (stage_dir / "input_snapshots" / "stage012b" / "output" / "loop_hypothesis_ledger.json").exists()
    assert not (stage_dir / "output" / "promoted_candidate_manifest.json").exists()
