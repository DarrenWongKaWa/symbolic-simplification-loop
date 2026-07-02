"""Loop 020A — Runner Report Output Path Hygiene.

These tests pin the runner's output-path policy after the Loop 020A
hygiene pass:

- Default report path is `autonomous_runs/<project>/<basename>` or
  `archive/local_runs/<UTC-timestamp>_<basename>`.
- The legacy `REPO_ROOT / <basename>` location is NOT written
  unless the user passes the explicit `--write-root-report` flag.
- Pytest does not leak generated runner reports to the repo root
  by default.

Loop behavior, trust-stack, freeze_preconditions, completion_matrix,
and human_signoff are NOT modified by these tests.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
# Patch (Loop Skill / Repo Integration Patch): route the runner
# subprocess to an isolated ``autonomous_runs_test`` so this file
# never mutates the live ``autonomous_runs/sigma_abc`` state.
# Follow-up patch: tests now pass their own ``run_root`` (typically
# the ``tmp_path`` fixture) so that pytest collection order cannot
# leak runner state from one test into another. ``LEGACY_TEST_RUN_ROOT``
# is preserved as the explicit opt-in for manual smoke tests.
LEGACY_TEST_RUN_ROOT = REPO_ROOT / "autonomous_runs_test"


def _runner(
    *args: str,
    run_root: Path | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["LOOP_RUN_ROOT"] = str(
        run_root if run_root is not None else LEGACY_TEST_RUN_ROOT
    )
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        env=env,
    )


@pytest.fixture(autouse=True)
def _clean_runner_residue():
    """Strip legacy root-level runner reports before AND after each test.

    Earlier tests in this module may have run the runner with
    ``--write-root-report``; their residue would otherwise spill into
    later tests' assertions about default behavior.
    """
    legacy_files = [
        "AUTONOMOUS_LOOP_RUN_REPORT.md",
        "PROFILE_RUNNER_DRY_RUN.md",
        "PROFILE_RUNNER_AUDIT.md",
        "SIGMA_ABC_CENTER_SECTOR_PILOT_REPORT.md",
        "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md",
        "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md",
        "SIGMA_ABC_AGENT_RUNTIME_REQUIRED.md",
    ]
    for name in legacy_files:
        path = REPO_ROOT / name
        if path.exists():
            path.unlink()
    yield
    for name in legacy_files:
        path = REPO_ROOT / name
        if path.exists():
            path.unlink()


def test_dry_run_does_not_write_root_reports(tmp_path: Path) -> None:
    """`--dry-run` should write the PROFILE_RUNNER_DRY_RUN.md under
    ``autonomous_runs/<project>/`` and under no other location by default.
    """
    run_root = tmp_path / "runs"
    result = _runner(
        "--project", "mock",
        "--profile", "test_hypothesis_search_loop",
        "--dry-run",
        run_root=run_root,
    )
    assert result.returncode == 0, (
        f"runner failed; stdout={result.stdout[-200:]!r} stderr={result.stderr[-200:]!r}"
    )
    new_sink = (
        run_root / "mock"
        / "PROFILE_RUNNER_DRY_RUN.md"
    )
    assert new_sink.exists(), f"expected report at {new_sink}"
    legacy = REPO_ROOT / "PROFILE_RUNNER_DRY_RUN.md"
    assert not legacy.exists(), (
        f"legacy REPO_ROOT sink should not exist by default; found {legacy}"
    )


def test_dry_run_with_write_root_report_restores_legacy_sink(tmp_path: Path) -> None:
    """`--write-root-report` is the explicit opt-in to re-emit the legacy
    REPO_ROOT sink.
    """
    run_root = tmp_path / "runs"
    result = _runner(
        "--project", "mock",
        "--profile", "test_hypothesis_search_loop",
        "--dry-run",
        "--write-root-report",
        run_root=run_root,
    )
    assert result.returncode == 0, (
        f"runner failed; stdout={result.stdout[-200:]!r} stderr={result.stderr[-200:]!r}"
    )
    legacy = REPO_ROOT / "PROFILE_RUNNER_DRY_RUN.md"
    assert legacy.exists(), (
        f"with --write-root-report, legacy REPO_ROOT sink should exist at {legacy}"
    )


def test_helpers_do_not_write_to_reporoot_for_failed_checkpoints(tmp_path: Path) -> None:
    """Even when runner pipeline raises RuntimeError mid-flow, no
    generated report should leak into REPO_ROOT unless
    ``--write-root-report`` is set.
    """
    run_root = tmp_path / "runs"
    result = _runner(
        "--project", "sigma_abc",
        "--profile", "sigma_abc_loop_candidate_preparation",
        "--from-current-checkpoint",
        "--auto-patch",
        "--write-digests",
        "--max-stages", "1",
        run_root=run_root,
    )
    leaked = [
        REPO_ROOT / n for n in (
            "SIGMA_ABC_CENTER_SECTOR_PILOT_REPORT.md",
            "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md",
            "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md",
            "SIGMA_ABC_AGENT_RUNTIME_REQUIRED.md",
            "AUTONOMOUS_LOOP_RUN_REPORT.md",
        )
    ]
    leaked_present = [p for p in leaked if p.exists()]
    assert not leaked_present, (
        f"runner leaked root-level reports: {leaked_present}"
    )


def test_archive_local_runs_receives_audit_files(tmp_path: Path) -> None:
    """``PROFILE_RUNNER_AUDIT.md`` is project-agnostic; default sink is
    ``archive/local_runs/<ts>_PROFILE_RUNNER_AUDIT.md``.
    """
    run_root = tmp_path / "runs"
    result = _runner(
        "--project", "mock",
        "--profile", "test_hypothesis_search_loop",
        "--dry-run",
        run_root=run_root,
    )
    assert result.returncode == 0, result.stderr[-200:]
    archive_dir = REPO_ROOT / "archive" / "local_runs"
    candidates = list(archive_dir.glob("*_PROFILE_RUNNER_AUDIT.md"))
    assert candidates, (
        f"no *_PROFILE_RUNNER_AUDIT.md in {archive_dir}"
    )
