"""Loop Skill / Repo Integration Patch tests.

Implements Task 1, Task 3, Task 4 of the patch plan at
``docs/superpowers/plans/2026-07-02-loop-skill-repo-integration-patch.md``.

Tests pin:
- safe-prefusion report routing under sigma_abc run root
  (project-name bug fix)
- failed freeze does NOT leave ``.loop/checkpoint_manifest.json``
  on disk (manifest hygiene)
- runner respects ``LOOP_RUN_ROOT`` env override for pytest-time
  isolation from the live ``autonomous_runs/sigma_abc``

Note: the same-name test
``tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008``
is an EXISTING test that fails on the ``human_signoff.yaml is
required`` invariant (Loop 013 trust-stack). It is NOT the bug
this patch fixes. The new test below asserts the project-name
routing fix lands correctly regardless of the human-signoff
invariant state.

Boundaries:
- sigma_abc/ physics unchanged.
- 012C / 013 / IBP / total derivative NOT started.
- DCProjectionTo1D -> INHERITED_PASS preserved.
- No real API keys written to disk.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

from loop_engine.checkpoint import freeze_checkpoint
from loop_engine.config import write_json, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_runner_subprocess(
    *args: str,
    env: dict[str, str] | None = None,
    timeout: int = 300,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Spawn the real autonomous runner as a subprocess.

    Pass ``env`` to control ``LOOP_RUN_ROOT`` for isolation.
    """
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=cwd or REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=env,
    )


# ---- Task 1: safe-prefusion report routing ---------------------------


def test_safe_prefusion_report_is_written_under_sigma_abc_run_root():
    """After patch: SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md must
    exist in the correct run root.

    Note: even after the project-name bug fix, the runner may
    fail with ``RuntimeError("human_signoff.yaml is required")``
    on stages 011/012A/012B in the sigma_abc_safe_pre_fusion
    profile (this is the Loop 013 trust-stack invariant that is
    NOT modified by this patch). The report-write side, however,
    happens unconditionally at the end of ``write_run_report``
    for the safe-pre-fusion profile. If the runner returns
    non-zero, this assertion is expected to fail and the
    developer is NOT in scope to fix the human-signoff
    invariant here.
    """
    result = run_runner_subprocess(
        "--project", "sigma_abc",
        "--profile", "sigma_abc_safe_pre_fusion",
        "--from-current-checkpoint",
        "--clean",
    )
    # The runner may exit non-zero (human_signoff.yaml hard-stop);
    # we only assert the report file landed.
    report = (
        REPO_ROOT / "autonomous_runs" / "sigma_abc"
        / "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md"
    )
    assert report.exists(), (
        f"runner.returncode={result.returncode}; "
        f"stderr-tail={result.stderr[-500:]}"
    )


# ---- Task 3: failed freeze does not leave manifest -------------------


def make_freeze_ready_but_unsigned_stage(tmp_path: Path) -> Path:
    """Build a stage that has all four freeze-artifacts but no
    ``human_signoff.yaml``.
    """
    stage = tmp_path / "project" / "stages" / "unsigned_stage"
    for folder in [".loop", "reports", "output", "validation"]:
        (stage / folder).mkdir(parents=True, exist_ok=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n\nGoal: unsigned freeze test.\n")
    write_text(
        stage / "CLAIM_BOUNDARY.md",
        "# Claim Boundary\n\nNo full tensorial claim.\n",
    )
    write_text(stage / "review_packet.md", "# Review Packet\n")
    write_json(
        stage / ".loop" / "validation_summary.json",
        {
            "stage_name": stage.name,
            "overall_gate": "PASS",
            "identity_type": "OldMinusNewZero",
            "checks": [{"name": "exact", "expected": 0, "actual": 0, "gate": "PASS"}],
            "protected_regressions": [],
            "caveats": [],
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
            "nonblocking_caveats": [],
            "allowed_claims": ["PASS as unsigned test."],
            "forbidden_claims": [],
            "next_action": "FREEZE",
            "suggested_next_stage": None,
            "patch_instructions": [],
        },
    )
    write_json(stage / ".loop" / "metrics.json", {"stage_name": stage.name})
    from loop_engine.completion_matrix import write_completion_matrix

    write_completion_matrix(stage)
    return stage


def test_failed_freeze_does_not_leave_checkpoint_manifest(tmp_path: Path):
    stage = make_freeze_ready_but_unsigned_stage(tmp_path)
    try:
        freeze_checkpoint(stage, tmp_path / "checkpoints")
    except RuntimeError as exc:
        assert "human_signoff.yaml is required" in str(exc)
    else:
        raise AssertionError("freeze_checkpoint unexpectedly succeeded")
    assert not (stage / ".loop" / "checkpoint_manifest.json").exists(), (
        "failed freeze left checkpoint_manifest.json on disk; "
        "this breaks the skill invariant that checkpoint_manifest.json "
        "exists only when freeze is allowed"
    )


# ---- Task 4: LOOP_RUN_ROOT env override -----------------------------


def test_runner_respects_loop_run_root_env(tmp_path: Path):
    """Runner reads ``LOOP_RUN_ROOT`` and writes under that
    directory instead of polluting ``autonomous_runs/sigma_abc``.

    Uses ``--project sigma_abc`` because it is the only project
    with a ``projects/<name>/loop.yaml`` on disk; the
    ``test_hypothesis_search_loop`` profile is independent of
    that project's stages (only its loop graph is read).
    """
    isolated = tmp_path / "isolated_runs"
    env = dict(os.environ)
    env["LOOP_RUN_ROOT"] = str(isolated)
    result = run_runner_subprocess(
        "--project", "sigma_abc",
        "--profile", "test_hypothesis_search_loop",
        "--clean",
        env=env,
    )
    assert result.returncode == 0, (
        f"runner.returncode={result.returncode}; "
        f"stderr-tail={result.stderr[-500:]}"
    )
    candidate = isolated / "sigma_abc" / "AUTONOMOUS_LOOP_RUN_REPORT.md"
    assert candidate.exists(), (
        f"expected {candidate} to exist when LOOP_RUN_ROOT={isolated}"
    )
