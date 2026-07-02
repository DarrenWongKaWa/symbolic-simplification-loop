from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from loop_engine.mailbox import append_event, initialize_mailbox, mailbox_state
from loop_engine.orchestrator import plan_patch_or_hard_stop
from loop_engine.verifier import run_stage_verifier, run_verifier_agent_audit


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_runner(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=REPO_ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def test_mailbox_state_created(tmp_path: Path):
    stage = tmp_path / "stage"
    initialize_mailbox(stage, "stage_alpha", attempt=1)
    assert (stage / ".loop" / "mailbox" / "state.json").exists()
    assert (stage / ".loop" / "mailbox" / "events.jsonl").exists()
    assert (stage / ".loop" / "mailbox" / "attempt_001" / "main_executor").exists()


def test_mailbox_events_record_agent_order(tmp_path: Path):
    stage = tmp_path / "stage"
    initialize_mailbox(stage, "stage_alpha", attempt=1)
    append_event(stage, "stage_alpha", 1, "MainExecutor", "STARTED", [], [], "execution started")
    append_event(stage, "stage_alpha", 1, "VerifierAgent", "COMPLETED", [], [], "validation audited")
    events = [
        json.loads(line)
        for line in (stage / ".loop" / "mailbox" / "events.jsonl").read_text().splitlines()
        if line.strip()
    ]
    actors = [event["actor"] for event in events]
    assert actors == ["MainExecutor", "VerifierAgent"]


def test_patch_decision_routes_to_patch_planner(tmp_path: Path):
    stage = tmp_path / "stage"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir()
    (stage / "CLAIM_BOUNDARY.md").write_text("Do not claim full tensorial sigma_abc correctness.\n")
    (stage / ".loop" / "validation_summary.json").write_text(json.dumps({"overall_gate": "FAIL", "checks": []}))
    (stage / ".loop" / "review_result.json").write_text(json.dumps({"verdict": "PASS"}))
    (stage / ".loop" / "meta_review_result.json").write_text(json.dumps({"verdict": "NEEDS_PATCH", "blocking_issues": ["report wording"]}))
    decision = plan_patch_or_hard_stop(stage, patch_reason="report wording", max_patch_attempts=2)
    assert decision["action"] == "PATCH"
    assert (stage / "PATCH_PLAN.md").exists()
    assert (stage / ".loop" / "patch_planner_result.json").exists()


def test_patch_planner_required_before_executor_retry(tmp_path: Path):
    stage = tmp_path / "stage"
    initialize_mailbox(stage, "stage_alpha", attempt=1)
    assert not (stage / "PATCH_PLAN.md").exists()
    decision = plan_patch_or_hard_stop(stage, patch_reason="missing caveat", max_patch_attempts=0)
    assert decision["action"] == "HARD_STOP"
    assert "max patch attempts" in decision["reason"]


def test_second_failed_same_patch_hard_stops(tmp_path: Path):
    stage = tmp_path / "stage"
    initialize_mailbox(stage, "stage_alpha", attempt=1)
    first = plan_patch_or_hard_stop(stage, patch_reason="same weak validation", max_patch_attempts=2)
    second = plan_patch_or_hard_stop(stage, patch_reason="same weak validation", max_patch_attempts=2)
    assert first["action"] == "PATCH"
    assert second["action"] == "HARD_STOP"


def test_verifier_agent_cannot_override_validation_fail(tmp_path: Path):
    stage = tmp_path / "stage"
    (stage / ".loop").mkdir(parents=True)
    (stage / ".loop" / "validation_summary.json").write_text(
        json.dumps({"stage_name": "stage", "overall_gate": "FAIL", "checks": [{"name": "bad", "gate": "FAIL"}]})
    )
    (stage / ".loop" / "metrics.json").write_text(json.dumps({"stage_name": "stage"}))
    service = run_stage_verifier(stage)
    audit = run_verifier_agent_audit(stage)
    assert service["VerifierServicePassed"] is False
    assert audit["VerifierAgentAuditPassed"] is False
    assert audit["CannotOverrideValidationFailure"] is True


def test_digest_reviewer_blocks_overclaim_in_pdf(tmp_path: Path):
    stage = tmp_path / "stage"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir()
    (stage / "reports" / "stage_alpha_summary.tex").write_text("We prove full tensorial sigma_abc correctness.")
    from loop_engine.orchestrator import run_digest_reviewer

    result = run_digest_reviewer(stage, named_digest_slug="stage_alpha")
    assert result["verdict"] == "NEEDS_PATCH"
    assert result["overclaim_detected"] is True


def test_main_executor_forbidden_from_writing_reviewer_results():
    from loop_engine.orchestrator import actor_may_write

    assert actor_may_write("MainExecutor", ".loop/reviewer_results/algebra_reviewer.json") is False
    assert actor_may_write("MainExecutor", "output/result.wl") is True


def test_production_profile_requires_real_agent_invocation():
    profile = yaml.safe_load((REPO_ROOT / "profiles" / "sigma_abc_pair_kernel_fusion_pilot.yaml").read_text())
    assert profile["agents"]["require_real_invocation"] is True
    assert profile["agents"]["forbid_stub_in_production"] is True
    assert profile["orchestration"]["use_mailbox"] is True


def test_stage_named_digest_paths():
    result = run_runner("--project", "mock", "--profile", "test_safe_loop", "--clean")
    assert result.returncode == 0
    stage = REPO_ROOT / "autonomous_runs" / "mock" / "stages" / "mock_001_identity"
    assert (stage / "reports" / "mock_001_identity_summary.md").exists()
    assert (stage / "reports" / "mock_001_identity_summary.tex").exists()
    assert (stage / "reports" / "mock_001_identity_human_review.md").exists()
    assert (stage / ".loop" / "mock_001_identity_meta_review.json").exists()
    manifest = json.loads((stage / ".loop" / "checkpoint_manifest.json").read_text())
    paths = {record["path"] for record in manifest["files"]}
    assert "reports/mock_001_identity_summary.md" in paths
    assert "reports/stage_summary.md" in paths
