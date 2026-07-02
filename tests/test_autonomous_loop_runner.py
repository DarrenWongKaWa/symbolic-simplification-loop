from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
# Patch (Loop Skill / Repo Integration Patch): route every
# runner subprocess to an isolated ``autonomous_runs_test`` so
# pytest never mutates the live ``autonomous_runs/sigma_abc``.
# Follow-up patch: tests opt into either a per-test ``tmp_path``
# (via the ``run_root`` parameter below) or, if they really
# need the legacy persistent sandbox, into ``LEGACY_TEST_RUN_ROOT``.
# The default is now a fresh tempfile per call so tests cannot
# pollute each other across pytest collection order.
LEGACY_TEST_RUN_ROOT = REPO_ROOT / "autonomous_runs_test"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_autonomous_loop import run_runtime_reviewer_agents, write_decision  # noqa: E402
from run_autonomous_loop import execute_sigma_abc_center_sector_stage, run_hypothesis_search_if_enabled  # noqa: E402


def run_runner(
    *args: str,
    check: bool = True,
    run_root: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Spawn the autonomous runner in an isolated run root.

    Pass the same ``run_root`` explicitly for tests that need
    multiple runner invocations to share checkpoint state. If
    omitted, use a fresh temporary directory so tests do not
    pollute each other.
    """
    env = os.environ.copy()
    selected_root = run_root or Path(tempfile.mkdtemp(prefix="loop-runner-test-"))
    env["LOOP_RUN_ROOT"] = str(selected_root)
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=REPO_ROOT,
        check=check,
        text=True,
        capture_output=True,
        env=env,
    )


def _autonomous_runs_root(project: str, run_root: Path | None = None) -> Path:
    return (run_root or LEGACY_TEST_RUN_ROOT) / project


def test_required_autonomous_configs_exist_and_are_safe():
    loop = yaml.safe_load((REPO_ROOT / "projects" / "sigma_abc" / "loop.yaml").read_text())
    profile = yaml.safe_load((REPO_ROOT / "profiles" / "sigma_abc_safe_pre_fusion.yaml").read_text())
    policy = yaml.safe_load((REPO_ROOT / "policies" / "sigma_abc_hard_stops.yaml").read_text())
    benchmark = yaml.safe_load((REPO_ROOT / "benchmarks" / "sigma_xxx_projection.yaml").read_text())

    assert loop["project"] == "sigma_abc"
    assert "sigma_abc_006_tensorial_sector_architecture_review" in [stage["id"] for stage in loop["stages"]]
    assert profile["review"]["mode"] == "codex_subagent"
    assert profile["autonomy"]["allow_physics_simplification"] is False
    assert any("kernel_fusion" in item for item in policy["hard_stops"]["forbidden_stage_tags"])
    assert benchmark["protected_benchmark"] == "sigma_xxx_projection"
    assert benchmark["caveats"]["stage001_dc_projection"] == "INHERITED_PASS"


def test_autonomous_runner_mock_two_stages_freezes_without_long_prompt(tmp_path: Path):
    run_root = tmp_path / "runs"
    result = run_runner(
        "--project",
        "mock",
        "--profile",
        "test_safe_loop",
        "--clean",
        run_root=run_root,
    )
    assert result.returncode == 0

    root = run_root / "mock"
    report = root / "AUTONOMOUS_LOOP_RUN_REPORT.md"
    assert report.exists()
    report_text = report.read_text()
    assert "mock_000_identity" in report_text
    assert "mock_001_identity" in report_text
    assert "stages_frozen: 2" in report_text

    for stage_name in ["mock_000_identity", "mock_001_identity"]:
        stage = root / "stages" / stage_name
        assert (stage / ".loop" / "reviewer_results" / "algebra_reviewer.json").exists()
        assert (stage / ".loop" / "reviewer_results" / "physics_reviewer.json").exists()
        assert (stage / ".loop" / "reviewer_results" / "software_reviewer.json").exists()
        assert (stage / ".loop" / "review_result.json").exists()
        assert (stage / ".loop" / "checkpoint_manifest.json").exists()

    decision = json.loads((root / "stages" / "mock_001_identity" / ".loop" / "decision.json").read_text())
    assert decision["action"] == "FREEZE"


def test_autonomous_runner_blocks_validation_failure(tmp_path: Path):
    run_root = tmp_path / "runs"
    result = run_runner(
        "--project",
        "mock_validation_fail",
        "--profile",
        "test_safe_loop",
        "--clean",
        check=False,
        run_root=run_root,
    )
    assert result.returncode == 0
    root = run_root / "mock_validation_fail"
    stage = root / "stages" / "mock_fail_validation"
    decision = json.loads((stage / ".loop" / "decision.json").read_text())
    assert decision["freeze_allowed"] is False
    assert decision["action"] == "DO_NOT_FREEZE"
    assert not (stage / ".loop" / "checkpoint_manifest.json").exists()


def test_autonomous_runner_blocks_missing_reviewer_output(tmp_path: Path):
    run_root = tmp_path / "runs"
    result = run_runner(
        "--project",
        "mock_missing_reviewer",
        "--profile",
        "test_safe_loop",
        "--clean",
        check=False,
        run_root=run_root,
    )
    assert result.returncode == 0
    root = run_root / "mock_missing_reviewer"
    stage = root / "stages" / "mock_missing_reviewer"
    review = json.loads((stage / ".loop" / "review_result.json").read_text())
    decision = json.loads((stage / ".loop" / "decision.json").read_text())
    assert review["verdict"] == "NEEDS_PATCH"
    assert decision["freeze_allowed"] is False
    assert not (stage / ".loop" / "checkpoint_manifest.json").exists()


def test_autonomous_runner_accepts_max_stages_override(tmp_path: Path):
    run_root = tmp_path / "runs"
    result = run_runner(
        "--project",
        "mock",
        "--profile",
        "test_safe_loop",
        "--clean",
        "--max-stages",
        "1",
        run_root=run_root,
    )
    assert result.returncode == 0
    root = run_root / "mock"
    assert (root / "stages" / "mock_000_identity").exists()
    assert not (root / "stages" / "mock_001_identity").exists()


def test_from_current_checkpoint_also_skips_existing_frozen_stages(tmp_path: Path):
    run_root = tmp_path / "runs"
    result = run_runner(
        "--project",
        "mock",
        "--profile",
        "test_safe_loop",
        "--clean",
        "--max-stages",
        "1",
        run_root=run_root,
    )
    assert result.returncode == 0
    result = run_runner(
        "--project",
        "mock",
        "--profile",
        "test_safe_loop",
        "--from-current-checkpoint",
        "--max-stages",
        "1",
        run_root=run_root,
    )
    assert result.returncode == 0
    root = run_root / "mock"
    assert (root / "stages" / "mock_001_identity").exists()


def test_runtime_usage_limit_decision_creates_pending_review_without_patch(tmp_path: Path):
    stage = tmp_path / "quota_stage"
    (stage / ".loop").mkdir(parents=True)
    (stage / ".loop" / "validation_summary.json").write_text(
        json.dumps({"stage_name": "quota_stage", "overall_gate": "PASS", "checks": []}),
        encoding="utf-8",
    )
    (stage / ".loop" / "metrics.json").write_text(json.dumps({"stage_name": "quota_stage"}), encoding="utf-8")
    (stage / "STAGE_PLAN.md").write_text("# Stage Plan\n", encoding="utf-8")
    (stage / "EXECUTION_REPORT.md").write_text("# Execution Report\n", encoding="utf-8")
    (stage / "CLAIM_BOUNDARY.md").write_text("# Claim Boundary\n", encoding="utf-8")
    (stage / "review_packet.md").write_text("# Review Packet\n", encoding="utf-8")
    profile = {
        "profile": "quota_profile",
        "agents": {"require_real_invocation": True, "allow_stub_for_tests": False},
        "runtime": {
            "adapter": "command",
            "command": [
                sys.executable,
                "-c",
                (
                    "import sys; "
                    "sys.stderr.write(\"You've hit your usage limit. Please try again at Jun 30th, 2026 1:01 AM.\\n\"); "
                    "sys.exit(1)"
                ),
            ],
            "timeout_seconds": 30,
        },
    }

    run_runtime_reviewer_agents(stage, profile, review_mode="codex_subagent", review_scope="routine_branch")
    decision = write_decision(stage)
    review = json.loads((stage / ".loop" / "review_result.json").read_text(encoding="utf-8"))

    assert review["verdict"] == "FAILED"
    assert any("AGENT_RUNTIME_QUOTA_EXHAUSTED" in issue for issue in review["blocking_issues"])
    assert decision["action"] == "VALIDATED_PENDING_REVIEW"
    assert decision["freeze_allowed"] is False
    assert decision["patch_required"] is False
    assert decision["retry_after"] == "Jun 30th, 2026 1:01 AM"
    assert not (stage / "PATCH_PLAN.md").exists()


def test_autonomous_runner_hard_stop_blocks_forbidden_stage(tmp_path: Path):
    run_root = tmp_path / "runs"
    result = run_runner(
        "--project",
        "mock_forbidden",
        "--profile",
        "test_safe_loop",
        "--clean",
        check=False,
        run_root=run_root,
    )
    assert result.returncode == 0
    report = (run_root / "mock_forbidden" / "AUTONOMOUS_LOOP_RUN_REPORT.md").read_text()
    assert "HARD_STOP" in report
    assert "kernel_fusion" in report
    stage = run_root / "mock_forbidden" / "stages" / "mock_forbidden_fusion"
    assert not (stage / ".loop" / "checkpoint_manifest.json").exists()


def test_safe_prefusion_run_does_not_pollute_dry_run_expectations(tmp_path: Path):
    first_root = tmp_path / "first_run"
    second_root = tmp_path / "second_run"

    first = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_safe_pre_fusion",
        "--from-current-checkpoint",
        "--clean",
        run_root=first_root,
    )
    assert first.returncode == 0, first.stderr[-1000:]

    second = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_safe_pre_fusion",
        "--dry-run",
        "--from-current-checkpoint",
        run_root=second_root,
    )
    assert second.returncode == 0, second.stderr[-1000:]
    assert "Next allowed stage: sigma_abc_006_tensorial_sector_architecture_review" in second.stdout


def test_sigma_abc_dry_run_reports_profile_driven_next_stage(tmp_path: Path):
    run_root = tmp_path / "runs"
    result = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_safe_pre_fusion",
        "--dry-run",
        "--from-current-checkpoint",
        run_root=run_root,
    )
    assert result.returncode == 0
    assert "Current checkpoint: sigma_abc_005_sector_ledger_xxx_collapse_regression_checkpoint_v1" in result.stdout
    assert "Next allowed stage: sigma_abc_006_tensorial_sector_architecture_review" in result.stdout
    assert "Stop-after stage: sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision" in result.stdout
    assert "Reviewer mode: codex_subagent" in result.stdout
    assert "Protected benchmarks:" in result.stdout
    assert "Permanent caveats:" in result.stdout
    assert "Forbidden actions:" in result.stdout

    audit = REPO_ROOT / "archive" / "local_runs" / (
        [p for p in (REPO_ROOT / "archive" / "local_runs").iterdir() if p.name.endswith("_PROFILE_RUNNER_AUDIT.md")]
        [0]
    ) if (REPO_ROOT / "archive" / "local_runs").exists() else None
    assert audit is not None, "expected an archive PROFILE_RUNNER_AUDIT.md"
    assert audit.exists()
    text = audit.read_text()
    assert "ProfileRunnerStatus -> COMPLETE" in text


def test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008(tmp_path: Path):
    run_root = tmp_path / "runs"
    result = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_safe_pre_fusion",
        "--from-current-checkpoint",
        "--clean",
        run_root=run_root,
    )
    assert result.returncode == 0
    root = run_root / "sigma_abc"
    report = root / "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md"
    assert report.exists()
    text = report.read_text()
    for stage_name in [
        "sigma_abc_006_tensorial_sector_architecture_review",
        "sigma_abc_007_pair_sector_basis_closure_pilot",
        "sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision",
    ]:
        assert stage_name in text
        assert (root / "stages" / stage_name / ".loop" / "checkpoint_manifest.json").exists()
    assert "sigma_abc_009" not in text
    assert "DCProjectionTo1D -> INHERITED_PASS" in text
    assert "full tensorial kernel fusion" in text


def test_sigma_abc_pair_kernel_fusion_pilot_runs_only_stage_010(tmp_path: Path):
    run_root = tmp_path / "runs"
    result = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_pair_kernel_fusion_pilot",
        "--from-current-checkpoint",
        "--clean",
        run_root=run_root,
    )
    assert result.returncode == 0
    root = run_root / "sigma_abc"
    stage = root / "stages" / "sigma_abc_010_pair_kernel_fusion_pilot"
    assert stage.exists()
    assert not (root / "stages" / "sigma_abc_011_pair_ibp").exists()

    required = [
        "output/pair_kernel_fusion_tables.wl",
        "output/pair_fused_kernel_families.wl",
        "output/pair_kernel_fusion_counts.json",
        "reports/pair_kernel_fusion_pilot_report.md",
        "validation/pair_kernel_fusion_validation.wl",
        ".loop/validation_summary.json",
        ".loop/reviewer_results/algebra_reviewer.json",
        ".loop/reviewer_results/physics_reviewer.json",
        ".loop/reviewer_results/software_reviewer.json",
        ".loop/review_result.json",
        ".loop/decision.json",
        ".loop/checkpoint_manifest.json",
    ]
    for rel in required:
        assert (stage / rel).exists(), rel

    validation = json.loads((stage / ".loop" / "validation_summary.json").read_text())
    assert validation["overall_gate"] == "PASS"
    expected_fields = {
        "PairSectorLoaded": True,
        "PairSectorRowCount": 912,
        "Stage009PairBasisLoaded": True,
        "PairKernelFusionTablesExist": True,
        "PairRowsConserved": True,
        "PairFusionDifference": 0,
        "XXXPairProjectionRegression": "PASS",
        "Stage001DCCaveatPreserved": True,
        "NoCenterSectorTouched": True,
        "NoLoopSectorTouched": True,
        "NoIBPStarted": True,
        "NoTotalDerivativeIntroduced": True,
        "NoFullTensorialClaim": True,
    }
    for key, value in expected_fields.items():
        assert validation[key] == value

    counts = json.loads((stage / "output" / "pair_kernel_fusion_counts.json").read_text())
    assert counts["pair_rows"] == 912
    assert counts["pair_families"] == 3
    assert counts["center_rows_touched"] == 0
    assert counts["loop_rows_touched"] == 0

    report = run_root / "sigma_abc" / "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md"
    assert report.exists(), (
        f"expected report at {report}, repo root should be clean of generated reports"
    )
    assert not (REPO_ROOT / "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md").exists(), (
        "REPO_ROOT should NOT contain generated runner reports by default"
    )
    text = report.read_text()
    assert "PairFusionDifference -> 0" in text
    assert "NoTotalDerivativeIntroduced -> True" in text


def test_sigma_abc_center_sector_pilot_dry_run_points_to_stage_011_without_running_it(tmp_path: Path):
    run_root = tmp_path / "runs"
    result = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_center_sector_pilot",
        "--dry-run",
        "--from-current-checkpoint",
        run_root=run_root,
    )
    assert result.returncode == 0
    assert "NextStage -> sigma_abc_011_center_sector_pilot" in result.stdout
    assert "Stop-after stage: sigma_abc_011_center_sector_pilot" in result.stdout
    assert "Reviewer mode: codex_subagent" in result.stdout


def test_center_sector_pilot_exports_non_tautological_provenance_validation(tmp_path: Path):
    stage = tmp_path / "sigma_abc_011_center_sector_pilot"
    for subdir in [".loop", "output", "reports", "validation"]:
        (stage / subdir).mkdir(parents=True, exist_ok=True)

    validation = execute_sigma_abc_center_sector_stage(
        stage,
        {"id": "sigma_abc_011_center_sector_pilot"},
        {"protected_benchmark": "sigma_xxx_projection"},
    )
    validation_wl = (stage / "validation" / "center_sector_pilot_validation.wl").read_text(encoding="utf-8")

    assert validation["identity_type"] == "RowProvenanceHashConservation"
    assert validation["CenterProvenanceDifference"] == 0
    assert validation["CenterFusionDifference"] == "NOT_CLAIMED"
    assert validation["XXXCenterProjectionRegression"] == "INHERITED_OR_DEFERRED"
    assert "centerSectorFused = sectorData[\"CenterSector\"]" not in validation_wl
    assert "XXXCenterProjectionRegression\" -> \"PASS\"" not in validation_wl
    assert '"CenterSectorRowCount" -> 93' not in validation_wl
    assert '"OverallGate" -> "PASS"' not in validation_wl


def test_sigma_abc_stage_hypothesis_search_does_not_promote_toy_candidate(tmp_path: Path):
    stage = tmp_path / "sigma_abc_011_center_sector_pilot"
    for subdir in [".loop", "output", "reports", "validation"]:
        (stage / subdir).mkdir(parents=True, exist_ok=True)
    validation = {
        "stage_name": "sigma_abc_011_center_sector_pilot",
        "overall_gate": "PASS",
        "checks": [],
    }
    (stage / ".loop" / "validation_summary.json").write_text(json.dumps(validation), encoding="utf-8")
    (stage / ".loop" / "metrics.json").write_text(json.dumps({"stage_name": stage.name}), encoding="utf-8")

    run_hypothesis_search_if_enabled(
        stage,
        {"id": "sigma_abc_011_center_sector_pilot"},
        {"hypothesis_search": {"enabled": True}},
    )

    promoted = json.loads((stage / "output" / "promoted_candidate_manifest.json").read_text(encoding="utf-8"))
    expression = (stage / "candidates" / promoted["conjecture_id"] / "candidate_expression.wl").read_text(encoding="utf-8")
    candidate_validation = (stage / "candidates" / promoted["conjecture_id"] / "candidate_validation.wl").read_text(encoding="utf-8")
    candidate_result = json.loads((stage / "candidates" / promoted["conjecture_id"] / "candidate_validation_result.json").read_text(encoding="utf-8"))
    conjecture = json.loads((stage / ".loop" / "conjectures" / f"{promoted['conjecture_id']}.json").read_text(encoding="utf-8"))

    assert conjecture["target_sector"] == "center/contact sector"
    assert "x + 1" not in expression
    assert "CenterPatternLedger" in expression
    assert "centerProvenanceDifference" in candidate_validation
    assert candidate_result["identity_checked"] == "center row-id and term-hash multisets conserved"
