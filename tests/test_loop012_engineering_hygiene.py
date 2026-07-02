from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from loop_engine.config import REPO_ROOT, write_json
from loop_engine.review_debt import create_review_debt_if_allowed
from loop_engine.review_queue import enqueue_pending_review
from loop_engine.schemas import schema_path, validate_with_schema


DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


def _review_result(verdict: str = "FAILED", blocking: list[str] | None = None) -> dict:
    return {
        "verdict": verdict,
        "stage_name": "sigma_abc_011_center_sector_pilot",
        "mathematical_status": {
            "exact_reconstruction": True,
            "simplification_real": False,
            "regression_preserved": True,
            "overclaim_detected": False,
        },
        "blocking_issues": blocking or ["AGENT_TIMEOUT: reviewer timed out"],
        "nonblocking_caveats": [DC_CAVEAT],
        "allowed_claims": ["Low-risk provenance checkpoint."],
        "forbidden_claims": ["Do not claim full tensorial sigma_abc correctness."],
        "next_action": "FREEZE",
        "suggested_next_stage": None,
        "patch_instructions": [],
    }


def _stage_with_timeout_debt(run_root: Path) -> Path:
    stage = run_root / "stages" / "sigma_abc_011_center_sector_pilot"
    (stage / ".loop").mkdir(parents=True)
    write_json(stage / ".loop" / "validation_summary.json", {
        "stage_name": stage.name,
        "overall_gate": "PASS",
        "checks": [],
        "caveats": [DC_CAVEAT],
        "NoKernelFusionStarted": True,
        "NoIBPStarted": True,
        "NoTotalDerivativeIntroduced": True,
        "NoFullTensorialClaim": True,
        "Stage001DCCaveatPreserved": True,
    })
    write_json(stage / ".loop" / "review_result.json", _review_result())
    write_json(stage / ".loop" / "risk_classification.json", {
        "risk_level": "LOW",
        "review_lane": "L1_COMPACT_META",
        "reviewers": ["ScientificMetaReviewer"],
    })
    create_review_debt_if_allowed(
        stage,
        {
            "review_debt": {
                "allow_l1_quota_debt": True,
                "allow_low_risk_advance": True,
            }
        },
    )
    enqueue_pending_review(
        stage,
        reason="AGENT_TIMEOUT",
        risk={
            "risk_level": "LOW",
            "review_lane": "L1_COMPACT_META",
            "reviewers": ["ScientificMetaReviewer"],
        },
    )
    return stage


def test_runtime_local_config_uses_repo_root_placeholder():
    runtime_local = REPO_ROOT / "agents" / "runtime.local.yaml"
    data = yaml.safe_load(runtime_local.read_text(encoding="utf-8"))
    text = runtime_local.read_text(encoding="utf-8")

    assert str(REPO_ROOT) not in text
    assert "${REPO_ROOT}" in text

    for profile in data["profiles"].values():
        command = profile["runtime"]["command"]
        assert any("${REPO_ROOT}" in str(item) for item in command)


def test_schema_path_resolver_survives_repo_root_move(monkeypatch, tmp_path: Path):
    import loop_engine.config as config
    import loop_engine.schemas as schemas

    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(schemas, "REPO_ROOT", tmp_path)

    resolved = schema_path("review_result")
    assert resolved.exists()
    assert resolved.name == "review_result.schema.json"
    validate_with_schema(_review_result(verdict="PASS", blocking=[]), "review_result")


def test_pyproject_packages_schema_data():
    pyproject = REPO_ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")

    assert "[tool.setuptools.package-data]" in text
    assert "schemas" in text
    assert "*.schema.json" in text


def test_settle_review_debt_auto_resume_handles_timeout_review_result(tmp_path: Path):
    run_root = tmp_path / "autonomous_runs" / "sigma_abc"
    stage = _stage_with_timeout_debt(run_root)

    from loop_engine.review_debt import settle_review_debt

    blocked = settle_review_debt(run_root, stage.name)
    assert blocked["status"] == "PENDING_REVIEW_RESUME"
    assert blocked["decision"] == "REVIEW_DEBT_REQUIRES_RESUME"
    assert "resume_pending_reviews.py" in blocked["recommended_command"]
    assert json.loads((stage / ".loop" / "review_debt.json").read_text())["status"] == "OPEN"


def test_settle_review_debt_auto_resume_flag_settles_timeout_debt(tmp_path: Path):
    run_root = tmp_path / "autonomous_runs" / "sigma_abc"
    stage = _stage_with_timeout_debt(run_root)

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "settle_review_debt.py"),
            "--project-root",
            str(run_root),
            "--stage-id",
            stage.name,
            "--auto-resume",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "SETTLED"
    assert payload["auto_resume"]["resumed"] == 1
    assert json.loads((stage / ".loop" / "review_debt.json").read_text())["status"] == "SETTLED"


def test_autonomous_report_identity_guard_labels_present():
    text = (REPO_ROOT / "scripts" / "run_autonomous_loop.py").read_text(encoding="utf-8")
    for label in ["ExpectedProfile", "ActualProfile", "ExpectedStage", "ActualStage", "ReportIdentityCheck"]:
        assert label in text


def test_run_stage_boundary_docstring_present():
    text = (REPO_ROOT / "scripts" / "run_stage.py").read_text(encoding="utf-8")
    assert "does not execute full physical verification" in text
    assert "only advances lifecycle state" in text


def test_readme_documents_reviewer_results_directory_and_run_stage_boundary():
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert ".loop/reviewer_results/" in text
    assert ".loop/reviews/" in text
    assert "run_stage.py" in text
    assert "does not execute full physical verification" in text
