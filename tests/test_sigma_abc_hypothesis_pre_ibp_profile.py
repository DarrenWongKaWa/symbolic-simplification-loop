from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_runner(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=REPO_ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def test_sigma_abc_hypothesis_pre_ibp_dry_run_reports_required_gates():
    result = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_hypothesis_pre_ibp",
        "--dry-run",
        "--from-current-checkpoint",
    )
    out = result.stdout
    assert "ProfileStatus -> COMPLETE" in out
    assert "CurrentCheckpoint -> sigma_abc_010_pair_kernel_fusion_pilot" in out
    assert "NextStage -> sigma_abc_011_center_sector_pilot" in out
    assert "HypothesisSearchEnabled -> True" in out
    assert "AutoPatchEnabled -> True" in out
    assert "ConjectureLedgerEnabled -> True" in out
    assert "FailedConjecturesArchived -> True" in out
    assert "NamedStageDigestsEnabled -> True" in out
    assert "ScientificMetaReviewerEnabled -> True" in out
    assert "StopBeforeIBP -> True" in out
    assert "RealAgentInvocationRequired -> True" in out
    assert "AgentInvocationEvidenceRequired -> True" in out
    assert "ProductionStubForbidden -> True" in out
    assert "AgentRuntimeStatus -> AVAILABLE" in out
    assert "Adapter -> command" in out
    assert "ProductionRunAllowed -> True" in out
    assert "MissingAgentCommands -> []" in out


def test_sigma_abc_hypothesis_pre_ibp_runtime_available_without_starting_production():
    result = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_hypothesis_pre_ibp",
        "--dry-run",
        "--from-current-checkpoint",
    )
    assert result.returncode == 0
    assert "AgentRuntimeStatus -> AVAILABLE" in result.stdout
    assert "ProductionRunAllowed -> True" in result.stdout
    assert "NextStage -> sigma_abc_011_center_sector_pilot" in result.stdout


def test_agent_runtime_dry_run_is_not_mislabeled_as_ibp_blocker():
    result = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_hypothesis_pre_ibp",
        "--dry-run",
        "--from-current-checkpoint",
    )
    assert "AgentRuntimeStatus -> AVAILABLE" in result.stdout
    assert "Human Approval Required Before IBP" not in result.stdout
