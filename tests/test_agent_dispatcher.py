"""Tests for the artifact-based agent dispatcher (TASK_026).

All tests use ``tmp_path`` to avoid touching real artifacts. These tests do
NOT invoke Claude or Codex CLI; the dispatcher is manual-provider-only.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from loop_engine import agent_bus
from loop_engine.config import write_json, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _make_nar(tmp_path: Path, *, classification_code: str = "MISSING_REQUIRED_FILE") -> Path:
    p = tmp_path / "next_action_report.json"
    write_json(p, {
        "schema_version": "1.0.0",
        "classification": {
            "code": classification_code,
            "description": f"test {classification_code}",
        },
        "all_classifications": [],
        "subject": {"kind": "stage", "stage_id": "test_stage"},
        "evidence": [],
        "gate_status": {
            "pre_run_gate": "MISSING",
            "validation_gate": "MISSING",
            "review_verdict": "MISSING",
            "completion": "MISSING",
            "freeze_eligible": None,
            "command_return_code": None,
        },
        "next_action": {
            "recommended": "PRODUCE_BASIS_FILES",
            "rationale": "test",
            "human_required": False,
            "boundary_approval_required": False,
            "patch_or_reject_recommended": False,
        },
        "forbidden_actions": [],
        "diagnostic_warnings": [],
        "tool_metadata": {"diagnostic_readonly": True},
    })
    return p


def _make_task_spec(tmp_path: Path, *, task_id: str = "TASK_TEST") -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / f"{task_id}.md"
    p.write_text(
        "# Task ID\n\n"
        f"{task_id}\n\n"
        "# Title\n\nTest task\n\n"
        "# Problem\n\nFixture\n\n"
        "# Goal\n\nFixture\n\n"
        "# Non-goals\n\nNone\n\n"
        "# Allowed edits\n\n- tests/\n\n"
        "# Forbidden edits\n\nNone\n\n"
        "# Implementation steps\n\n1. trivial\n\n"
        "# Acceptance commands\n\npytest\n\n"
        "# Expected output files\n\nNone\n\n"
        "# Risks\n\nNone\n\n"
        "# Definition of done\n\nDone.\n",
        encoding="utf-8",
    )
    return p


def _make_executor_report(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "executor_report.md"
    p.write_text(
        "# Executor Report\n\n"
        "## Status\n\nCOMPLETE\n\n"
        "## changed_files\n\n- tests/test_agent_dispatcher.py\n\n"
        "## commands_run\n\npytest\n\n"
        "## tests_passed\n\nmany\n\n"
        "## tests_failed\n\nNone\n\n"
        "## unresolved_issues\n\nNone\n\n"
        "## scope_deviation\n\nNone\n\n"
        "## recommended_next_action\n\nLand\n",
        encoding="utf-8",
    )
    return p


def _make_reviewer_result(tmp_path: Path, *, human_boundary_assessment: str = "") -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "patch_review_result.json"
    write_json(p, {
        "verdict": "PASS",
        "blocking_issues": [],
        "caveats": [DC_CAVEAT],
        "nonblocking_caveats": [DC_CAVEAT],
        "recommended_next_action": "MERGE_PATCH",
        "safe_to_continue": True,
        "required_followups": [],
        "reviewed_files": ["tests/test_agent_dispatcher.py"],
        "acceptance_evidence_assessment": "PASS: tests run, all green.",
        "human_boundary_assessment": human_boundary_assessment,
    })
    return p


def _make_stage_fixture(stage: Path) -> Path:
    """Create a stage-like fixture and return the stage path.

    Caller controls the parent directory.
    """
    stage.mkdir(parents=True, exist_ok=True)
    (stage / ".loop").mkdir(exist_ok=True)
    (stage / "reports").mkdir(exist_ok=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", f"# Claim Boundary\n\n{DC_CAVEAT}\n")
    write_text(stage / "validation_summary.json", "{}")
    write_text(stage / "review_result.json", "{}")
    write_text(stage / "completion_matrix.json", "{}")
    write_text(stage / ".loop" / "human_signoff.yaml", "decision: APPROVE_FREEZE\n")
    write_text(stage / ".loop" / "human_signoff_ledger.jsonl", "{}\n")
    (stage / ".loop" / "human_signoff_history").mkdir(exist_ok=True)
    write_text(stage / ".loop" / "human_signoff_history" / "x.json", "{}\n")
    return stage


# ---------------------------------------------------------------------------
# Layout + round lifecycle
# ---------------------------------------------------------------------------


def test_ensure_bus_layout_creates_all_required_dirs(tmp_path):
    paths = agent_bus.ensure_bus_layout(tmp_path)
    for role, subdirs in agent_bus.LAYOUT:
        for sub in subdirs:
            assert (paths["bus_root"] / role / sub).is_dir(), (role, sub)


def test_start_round_writes_planner_inbox_prompt(tmp_path):
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    state = agent_bus.start_round(bus, next_action_report=nar)
    assert state["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC
    assert (bus / "planner" / "inbox" / "planner_prompt.md").exists()
    body = (bus / "planner" / "inbox" / "planner_prompt.md").read_text()
    assert "MISSING_REQUIRED_FILE" in body
    assert "boundary" in body.lower()


def test_missing_planner_task_keeps_phase_waiting_for_task_spec(tmp_path):
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    out = agent_bus.advance(bus)
    # Nothing in planner outbox -> stays in WAITING_FOR_TASK_SPEC after
    # the first attempt consumes PLANNER_PROMPT_READY -> WAITING.
    assert out["phase"] in {
        agent_bus.PHASE_WAITING_FOR_TASK_SPEC,
        agent_bus.PHASE_PLANNER_PROMPT_READY,
    }


def test_accepted_planner_task_creates_executor_prompt(tmp_path):
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    # Drop a task spec into planner outbox.
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    # Without a ready marker the dispatcher must NOT auto-write one.
    out = agent_bus.advance(bus)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC
    assert (bus / "planner" / "outbox" / "TASK_READY").exists() is False
    # Drop the ready marker; the next advance must consume the task.
    _write_ready(bus, "planner")
    out = agent_bus.advance(bus)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_EXECUTOR_REPORT
    assert (bus / "executor" / "inbox" / "executor_prompt.md").exists()


def test_missing_executor_report_keeps_phase_waiting_for_executor_report(tmp_path):
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    out = agent_bus.advance(bus)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_EXECUTOR_REPORT
    # No executor report -> still waiting.
    out2 = agent_bus.advance(bus, repo_root=tmp_path)
    assert out2["phase"] == agent_bus.PHASE_WAITING_FOR_EXECUTOR_REPORT


def test_executor_report_triggers_git_evidence_collection(tmp_path):
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    # advance#1: WAITING_FOR_TASK_SPEC -> WAITING_FOR_EXECUTOR_REPORT
    out1 = agent_bus.advance(bus)
    assert out1["phase"] == agent_bus.PHASE_WAITING_FOR_EXECUTOR_REPORT
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    # Without executor ready marker, advance must NOT auto-write one.
    out2 = agent_bus.advance(bus, repo_root=tmp_path)
    assert out2["phase"] == agent_bus.PHASE_WAITING_FOR_EXECUTOR_REPORT
    assert (bus / "executor" / "outbox" / "EXECUTOR_READY").exists() is False
    _write_ready(bus, "executor")
    # advance#2: WAITING_FOR_EXECUTOR_REPORT -> WAITING_FOR_REVIEW_RESULT
    # Note: evidence files are NOT written at this phase move; they are
    # written only at WAITING_FOR_REVIEW_RESULT -> ROUND_SUMMARY_READY.
    out2 = agent_bus.advance(bus, repo_root=tmp_path)
    assert out2["phase"] == agent_bus.PHASE_WAITING_FOR_REVIEW_RESULT
    assert not (bus / "round_state" / "git_status.txt").exists()
    # Preplace reviewer result to run the next advance.
    rev = _make_reviewer_result(tmp_path / "reviews")
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(rev.read_text())
    _write_ready(bus, "reviewer")
    out3 = agent_bus.advance(bus, repo_root=tmp_path)
    assert (bus / "round_state" / "git_status.txt").exists()
    assert (bus / "round_state" / "git_diff_stat.txt").exists()
    assert (bus / "round_state" / "git_diff.patch").exists()
    assert out3["phase"] == agent_bus.PHASE_ROUND_SUMMARY_READY


def test_executor_report_records_acceptance_commands(tmp_path):
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)  # -> WAITING_FOR_EXECUTOR_REPORT
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)  # -> WAITING_FOR_REVIEW_RESULT
    rev = _make_reviewer_result(tmp_path / "reviews")
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(rev.read_text())
    _write_ready(bus, "reviewer")
    agent_bus.advance(bus, repo_root=tmp_path, acceptance_commands=["echo a", "echo b"], no_command_run=True)
    payload = json.loads((bus / "round_state" / "acceptance_results.json").read_text())
    assert payload["no_command_run"] is True
    cmds = [r["command"] for r in payload["results"]]
    assert "echo a" in cmds
    assert "echo b" in cmds
    for r in payload["results"]:
        assert r["run"] is False


def test_reviewer_prompt_includes_evidence(tmp_path):
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)  # -> WAITING_FOR_EXECUTOR_REPORT
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)  # -> WAITING_FOR_REVIEW_RESULT
    rev = (bus / "reviewer" / "inbox" / "reviewer_prompt.md").read_text()
    assert "TASK_TEST" in rev
    assert "executor_report.md" in rev
    assert "git_status" in rev
    assert "git_diff.patch" in rev
    assert "acceptance_results" in rev
    assert "patch_review_result.json" in rev


def test_missing_reviewer_result_keeps_phase_waiting_for_review_result(tmp_path):
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    out = agent_bus.advance(bus, repo_root=tmp_path)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_REVIEW_RESULT
    # No reviewer result -> still waiting.
    out2 = agent_bus.advance(bus, repo_root=tmp_path)
    assert out2["phase"] == agent_bus.PHASE_WAITING_FOR_REVIEW_RESULT


def test_round_summary_json_and_markdown_written_after_reviewer_result(tmp_path):
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)  # -> WAITING_FOR_EXECUTOR_REPORT
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)  # -> WAITING_FOR_REVIEW_RESULT
    rev = _make_reviewer_result(tmp_path / "reviews")
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(rev.read_text())
    _write_ready(bus, "reviewer")
    out = agent_bus.advance(bus, repo_root=tmp_path)  # -> ROUND_SUMMARY_READY
    assert out["phase"] == agent_bus.PHASE_ROUND_SUMMARY_READY
    summary = json.loads((bus / "round_state" / "agent_round_summary.json").read_text())
    assert summary["verdict"] == "PASS"
    assert summary["no_checkpoint_freeze_or_signoff_mutation"] is True
    md = (bus / "round_state" / "agent_round_summary.md").read_text()
    assert "Agent Round Summary" in md
    assert "auto-freeze checkpoints" in md


def test_multiple_planner_task_specs_fail_deterministically(tmp_path):
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_A.md").write_text("# A")
    (bus / "planner" / "outbox" / "TASK_B.md").write_text("# B")
    with pytest.raises(agent_bus.AmbiguousPlannerTasks):
        agent_bus.accept_planner_task(bus)


def test_human_boundary_routes_summary_to_human_inbox(tmp_path):
    """Classification == HUMAN_SIGNOFF_REQUIRED in the seed report must
    short-circuit at start_round() to WAITING_FOR_HUMAN_APPROVAL with a
    boundary summary in human/inbox. The full TASK -> executor -> reviewer
    dance must NOT run."""
    nar = _make_nar(tmp_path, classification_code="HUMAN_SIGNOFF_REQUIRED")
    bus = tmp_path / "bus"
    state = agent_bus.start_round(bus, next_action_report=nar)
    assert state["phase"] == agent_bus.PHASE_WAITING_FOR_HUMAN_APPROVAL
    assert state["human_boundary_required"] is True
    # No planner prompt written.
    assert not (bus / "planner" / "inbox" / "planner_prompt.md").exists()
    # Boundary summary dropped in human/inbox.
    boundary_files = list((bus / "human" / "inbox").glob("boundary_*.md"))
    assert len(boundary_files) == 1
    body = boundary_files[0].read_text()
    assert "HUMAN_SIGNOFF_REQUIRED" in body
    # Even when a planner outbox is preplaced, advance must NOT consume
    # it (the round is awaiting human approval).
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text("# task")
    out = agent_bus.advance(bus)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_HUMAN_APPROVAL
    assert not (bus / "executor" / "inbox" / "executor_prompt.md").exists()


def test_human_boundary_boundary_approval_required_short_circuits(tmp_path):
    """Same contract for BOUNDARY_APPROVAL_REQUIRED classification."""
    nar = _make_nar(tmp_path, classification_code="BOUNDARY_APPROVAL_REQUIRED")
    bus = tmp_path / "bus"
    state = agent_bus.start_round(bus, next_action_report=nar)
    assert state["phase"] == agent_bus.PHASE_WAITING_FOR_HUMAN_APPROVAL
    assert state["human_boundary_required"] is True
    assert not (bus / "planner" / "inbox" / "planner_prompt.md").exists()
    assert any((bus / "human" / "inbox").glob("boundary_*.md"))


def test_cli_advance_creates_planner_prompt(tmp_path):
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_agent_dispatcher.py",
            "--bus-root",
            str(bus),
            "--next-action-report",
            str(nar),
            "--advance",
            "--no-command-run",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert (bus / "planner" / "inbox" / "planner_prompt.md").exists()
    assert (bus / "planner" / "outbox").is_dir()
    assert (bus / "executor" / "outbox").is_dir()
    assert (bus / "reviewer" / "outbox").is_dir()
    assert (bus / "round_state" / "current_round.json").exists()


def test_dispatcher_does_not_modify_scientific_or_signoff_artifacts(tmp_path):
    """Run a full round against a fixture stage and confirm every
    protected file is byte-identical before and after.
    """
    stage = _make_stage_fixture(tmp_path / "stage_fixture")
    protected_paths = [
        "STAGE_PLAN.md",
        "CLAIM_BOUNDARY.md",
        "validation_summary.json",
        "review_result.json",
        "completion_matrix.json",
        ".loop/human_signoff.yaml",
        ".loop/human_signoff_ledger.jsonl",
        ".loop/human_signoff_history/x.json",
    ]

    def snapshot():
        return {rel: (stage / rel).read_bytes() for rel in protected_paths}

    before = snapshot()

    nar = _make_nar(tmp_path, classification_code="FREEZE_PRECONDITION_FAILED")
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)  # -> WAITING_FOR_EXECUTOR_REPORT
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)  # -> WAITING_FOR_REVIEW_RESULT
    rev = _make_reviewer_result(tmp_path / "reviews")
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(rev.read_text())
    _write_ready(bus, "reviewer")
    agent_bus.advance(bus, repo_root=tmp_path)  # -> ROUND_SUMMARY_READY
    # Also probe --summary-only and --status to ensure they don't touch
    # protected files.
    agent_bus.summarize_only(bus, repo_root=tmp_path)
    agent_bus.status(bus)

    after = snapshot()
    assert before == after


def test_needs_human_boundary_detects_tokens_in_task_text():
    assert agent_bus.needs_human_boundary(
        None,
        "TODO: gate the freeze step",
        None,
        None,
    ) is True
    assert agent_bus.needs_human_boundary(
        None,
        "Implement a small helper.",
        None,
        None,
    ) is False


def test_render_planner_prompt_includes_forbidden_section():
    nar = {
        "classification": {"code": "VALIDATION_GATE_FAILED", "description": "x"},
        "all_classifications": [{"code": "VALIDATION_GATE_FAILED", "description": "x"}],
        "subject": {"kind": "stage", "stage_id": "s", "project": "p", "run_root": "r"},
        "next_action": {"recommended": "PATCH_AND_REVALIDATE", "rationale": "r"},
        "forbidden_actions": ["modify scientific outputs", "auto-freeze checkpoints"],
    }
    body = agent_bus.render_planner_prompt(nar, {"round_id": "AGENT_x_y"})
    assert "VALIDATION_GATE_FAILED" in body
    assert "auto-freeze checkpoints" in body
    assert "boundary" in body.lower()


# ---------------------------------------------------------------------------
# TASK_026 patch regression tests (reviewer verdict FIX):
#   a. missing planner output leaves WAITING_FOR_TASK_SPEC
#   b. preplaced outbox artifacts require multiple advance() calls
#   c. notes.md is not accepted as planner task
#   d. invalid patch_review_result JSON is rejected
#   e. HUMAN_SIGNOFF_REQUIRED / BOUNDARY_APPROVAL_REQUIRED routes to
#      human/inbox at round start
# ---------------------------------------------------------------------------


def test_a_missing_planner_output_leaves_waiting_for_task_spec(tmp_path):
    """With no planner output, advance() must NOT advance the phase.
    Status must be WAITING_FOR_TASK_SPEC (not PLANNER_PROMPT_READY).
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    out = agent_bus.advance(bus)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC
    assert out["expected_next_artifact"].startswith("Wait for")


def test_b1_preplaced_artifacts_require_multiple_advance_calls(tmp_path):
    """Even with all three outbox artifacts preplaced, a single advance()
    call must move at most one phase. The reviewer saw the bug where one
    advance reached ROUND_SUMMARY_READY in one shot.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    rep = _make_executor_report(tmp_path / "reports")
    rev = _make_reviewer_result(tmp_path / "reviews")

    # Preplace all artifacts AND all ready markers up front.
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    (bus / "executor" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    (bus / "reviewer" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(rev.read_text())
    _write_ready(bus, "reviewer")

    # Call #1: WAITING_FOR_TASK_SPEC -> WAITING_FOR_EXECUTOR_REPORT
    out1 = agent_bus.advance(bus)
    assert out1["phase"] == agent_bus.PHASE_WAITING_FOR_EXECUTOR_REPORT
    # Reviewer artifact must NOT have been consumed yet.
    assert agent_bus.read_round_state(bus).get("patch_review_result") is None

    # Call #2: WAITING_FOR_EXECUTOR_REPORT -> WAITING_FOR_REVIEW_RESULT
    out2 = agent_bus.advance(bus, repo_root=tmp_path)
    assert out2["phase"] == agent_bus.PHASE_WAITING_FOR_REVIEW_RESULT
    # Still not consumed.
    assert agent_bus.read_round_state(bus).get("patch_review_result") is None

    # Call #3: WAITING_FOR_REVIEW_RESULT -> ROUND_SUMMARY_READY.
    out3 = agent_bus.advance(bus, repo_root=tmp_path)
    assert out3["phase"] == agent_bus.PHASE_ROUND_SUMMARY_READY


def test_b2_each_phase_move_records_waits_for_artifact(tmp_path):
    """Sanity: status reports the right 'expected_next_artifact' after each
    phase move.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    out = agent_bus.status(bus)
    assert "planner" in out["expected_next_artifact"]
    # After dropping a task spec + ready marker, a single advance
    # yields WAITING_FOR_EXECUTOR_REPORT.
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    out = agent_bus.advance(bus)
    assert "executor" in out["expected_next_artifact"]
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    out = agent_bus.advance(bus, repo_root=tmp_path)
    assert "reviewer" in out["expected_next_artifact"]


def test_c_planner_outbox_notes_md_is_not_accepted(tmp_path):
    """A non-TASK_*.md file (e.g. notes.md) must NOT be accepted as a
    planner task spec, even when it is the only file in the outbox.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "notes.md").write_text("# random notes")
    with pytest.raises(FileNotFoundError):
        agent_bus.accept_planner_task(bus)
    # Explicit task_path pointing at notes.md is also rejected.
    with pytest.raises(agent_bus.InvalidPlannerTask):
        agent_bus.accept_planner_task(bus, task_path=bus / "planner" / "outbox" / "notes.md")
    # And advance() must leave the phase at WAITING_FOR_TASK_SPEC.
    out = agent_bus.advance(bus)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC


def test_c2_planner_outbox_with_mixed_files_picks_only_task(tmp_path):
    """If both notes.md and TASK_X.md are present, the dispatcher must
    accept only TASK_X.md, not notes.md.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "notes.md").write_text("# notes")
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    chosen = agent_bus.accept_planner_task(bus)
    assert chosen.name == "TASK_TEST.md"


def test_d_invalid_patch_review_result_is_rejected(tmp_path):
    """An invalid reviewer JSON (e.g. {"unexpected":"shape"}) must NOT
    produce ROUND_SUMMARY_READY. The dispatcher must leave the phase at
    WAITING_FOR_REVIEW_RESULT and write a reviewer_error.json artifact.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)  # -> WAITING_FOR_EXECUTOR_REPORT
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)  # -> WAITING_FOR_REVIEW_RESULT

    # Place a reviewer result with only an unexpected field.
    (bus / "reviewer" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(
        json.dumps({"unexpected": "shape"})
    )
    _write_ready(bus, "reviewer")

    # Direct call surfaces the error (advance() swallows it for callers).
    with pytest.raises(agent_bus.InvalidReviewerResult):
        agent_bus.accept_reviewer_result(bus)
    out = agent_bus.advance(bus, repo_root=tmp_path)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_REVIEW_RESULT
    err_path = bus / "round_state" / "reviewer_error.json"
    assert err_path.exists()
    err = json.loads(err_path.read_text())
    assert "error" in err


def test_d2_invalid_reviewer_result_malformed_json(tmp_path):
    """Garbage JSON must raise InvalidReviewerResult and stay at
    WAITING_FOR_REVIEW_RESULT.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)
    (bus / "reviewer" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text("{not json")
    _write_ready(bus, "reviewer")
    with pytest.raises(agent_bus.InvalidReviewerResult):
        agent_bus.accept_reviewer_result(bus)
    out = agent_bus.advance(bus, repo_root=tmp_path)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_REVIEW_RESULT


def test_e_human_signoff_required_at_round_start_routes_to_human_inbox(tmp_path):
    """When next_action_report classifies as HUMAN_SIGNOFF_REQUIRED, the
    dispatcher must short-circuit to WAITING_FOR_HUMAN_APPROVAL at round
    start and drop a boundary summary in human/inbox, NOT write a planner
    prompt. advance() must keep waiting even when planner artifacts are
    preplaced.
    """
    nar = _make_nar(tmp_path, classification_code="HUMAN_SIGNOFF_REQUIRED")
    bus = tmp_path / "bus"
    state = agent_bus.start_round(bus, next_action_report=nar)
    assert state["phase"] == agent_bus.PHASE_WAITING_FOR_HUMAN_APPROVAL
    assert state["human_boundary_required"] is True
    assert not (bus / "planner" / "inbox" / "planner_prompt.md").exists()
    summary = list((bus / "human" / "inbox").glob("boundary_*.md"))
    assert len(summary) == 1
    # Preplace planner output AND ready marker; must still be ignored.
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    rep = _make_executor_report(tmp_path / "reports")
    rev = _make_reviewer_result(tmp_path / "reviews")
    (bus / "executor" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    (bus / "reviewer" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(rev.read_text())
    _write_ready(bus, "reviewer")
    out = agent_bus.advance(bus, repo_root=tmp_path)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_HUMAN_APPROVAL
    assert not (bus / "executor" / "inbox" / "executor_prompt.md").exists()
    assert not (bus / "reviewer" / "inbox" / "reviewer_prompt.md").exists()


def test_e2_boundary_approval_required_at_round_start_short_circuits(tmp_path):
    """Same behavior for BOUNDARY_APPROVAL_REQUIRED."""
    nar = _make_nar(tmp_path, classification_code="BOUNDARY_APPROVAL_REQUIRED")
    bus = tmp_path / "bus"
    state = agent_bus.start_round(bus, next_action_report=nar)
    assert state["phase"] == agent_bus.PHASE_WAITING_FOR_HUMAN_APPROVAL
    assert not (bus / "planner" / "inbox" / "planner_prompt.md").exists()
    assert any((bus / "human" / "inbox").glob("boundary_*.md"))


def test_f_status_for_waiting_for_human_approval_mentions_artifact_dirs(tmp_path):
    """Caveat fix: ``expected_next_artifact`` must clearly tell callers
    that the dispatcher is waiting for a human approval/rejection
    artifact under ``agent_bus/human/approved/`` or
    ``agent_bus/human/rejected/``. It must NOT report "Unknown phase".
    """
    nar = _make_nar(tmp_path, classification_code="HUMAN_SIGNOFF_REQUIRED")
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    out = agent_bus.status(bus)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_HUMAN_APPROVAL
    msg = out["expected_next_artifact"]
    assert msg != "Unknown phase", msg
    assert "agent_bus/human/approved/" in msg, msg
    assert "agent_bus/human/rejected/" in msg, msg


# ---------------------------------------------------------------------------
# TASK_027 patch regression tests
#   g. job envelopes: input/output paths, ready marker, failed artifact,
#      forbidden paths, provider name/type, allowed next states
#   h. role prompts include READ/WRITE/READY MARKER/FAILED ARTIFACT/
#      DO NOT EDIT/STOP CONDITION sections
#   i. manual provider does not invoke external agents
#   j. watch mode advances one phase at a time
#   k. watch mode idles when expected artifact is absent
#   l. watch mode idles when ready marker is absent (with --no-auto-marker)
#   m. watch mode refuses to advance with invalid reviewer result
#   n. watch mode stops at WAITING_FOR_HUMAN_APPROVAL
#   o. status output includes role, ready marker, provider, human boundary
#   p. failed artifact transitions to FAILED on next advance
#   q. job envelope schema validates
# ---------------------------------------------------------------------------


def _write_ready(bus: Path, role: str) -> None:
    marker = bus / role / "outbox" / {
        "planner": "TASK_READY",
        "executor": "EXECUTOR_READY",
        "reviewer": "REVIEW_READY",
    }[role]
    marker.write_text(f"{role} ready", encoding="utf-8")


def test_g_planner_job_envelope_contract(tmp_path):
    """Planner job envelope: input/output paths, ready marker, failed
    artifact, forbidden paths, provider name/type, allowed next states.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    envelope_path = bus / "planner" / "inbox" / "planner_job.json"
    assert envelope_path.exists()
    envelope = json.loads(envelope_path.read_text())
    assert envelope["role"] == "planner"
    assert envelope["provider_name"] == "CodexPlanner"
    assert envelope["provider_type"] == agent_bus.PROVIDER_TYPE_MANUAL
    assert envelope["ready_marker"].endswith("TASK_READY")
    assert envelope["failed_artifact"].endswith("planner_failed.md")
    assert any("TASK_*.md" in p for p in envelope["output_files"])
    assert "sigma_abc/" in envelope["forbidden_paths"]
    assert ".loop/human_signoff.yaml" in envelope["forbidden_paths"]
    assert agent_bus.PHASE_WAITING_FOR_EXECUTOR_REPORT in envelope["allowed_next_states"]
    # Bug fix: envelope phase must match the active waiting phase,
    # not INIT.
    assert envelope["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC
    # Schema-validates.
    from loop_engine.schemas import validate_with_schema
    validate_with_schema(envelope, "agent_bus_job")


def test_g_executor_job_envelope_contract(tmp_path):
    """Executor job envelope after planner task acceptance."""
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)
    envelope = json.loads((bus / "executor" / "inbox" / "executor_job.json").read_text())
    assert envelope["role"] == "executor"
    assert envelope["provider_name"] == "ClaudeCodeExecutor"
    assert envelope["provider_type"] == agent_bus.PROVIDER_TYPE_MANUAL
    assert envelope["ready_marker"].endswith("EXECUTOR_READY")
    assert envelope["failed_artifact"].endswith("executor_failed.md")
    assert any(p.endswith("executor_report.md") for p in envelope["output_files"])
    assert envelope["phase"] == agent_bus.PHASE_WAITING_FOR_EXECUTOR_REPORT
    # Inputs must include the planner prompt and task spec.
    assert any(p.endswith("planner_prompt.md") for p in envelope["input_files"])
    assert any(p.endswith("TASK_TEST.md") for p in envelope["input_files"])


def test_g_reviewer_job_envelope_contract(tmp_path):
    """Reviewer job envelope after executor report acceptance."""
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)
    envelope = json.loads((bus / "reviewer" / "inbox" / "reviewer_job.json").read_text())
    assert envelope["role"] == "reviewer"
    assert envelope["provider_name"] == "CodexReviewer"
    assert envelope["provider_type"] == agent_bus.PROVIDER_TYPE_MANUAL
    assert envelope["ready_marker"].endswith("REVIEW_READY")
    assert envelope["failed_artifact"].endswith("reviewer_failed.md")
    assert envelope["expected_schema"] == "patch_review_result"
    # Bug fix: reviewer envelope must record the active waiting phase.
    assert envelope["phase"] == agent_bus.PHASE_WAITING_FOR_REVIEW_RESULT
    # Inputs must include executor report, git status, git diff, acceptance.
    input_text = " ".join(envelope["input_files"])
    assert "executor_report.md" in input_text
    assert "git_status.txt" in input_text
    assert "git_diff.patch" in input_text
    assert "acceptance_results.json" in input_text


def test_h_planner_prompt_has_required_sections(tmp_path):
    """Planner prompt must contain ROLE / ROUND_ID / READ / WRITE ONLY /
    READY MARKER / FAILED ARTIFACT / DO NOT EDIT / STOP CONDITION."""
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    body = (bus / "planner" / "inbox" / "planner_prompt.md").read_text()
    for required in ("## ROLE", "## ROUND_ID", "## READ", "## WRITE ONLY",
                     "## READY MARKER", "## FAILED ARTIFACT",
                     "## DO NOT EDIT", "## STOP CONDITION"):
        assert required in body, f"missing section: {required}"


def test_h_executor_prompt_has_required_sections(tmp_path):
    """Executor prompt must include all required sections."""
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)
    body = (bus / "executor" / "inbox" / "executor_prompt.md").read_text()
    for required in ("## ROLE", "## ROUND_ID", "## READ", "## WRITE ONLY",
                     "## READY MARKER", "## FAILED ARTIFACT",
                     "## DO NOT EDIT", "## STOP CONDITION"):
        assert required in body, f"missing section: {required}"


def test_h_reviewer_prompt_has_required_sections(tmp_path):
    """Reviewer prompt must include all required sections."""
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)
    body = (bus / "reviewer" / "inbox" / "reviewer_prompt.md").read_text()
    for required in ("## ROLE", "## ROUND_ID", "## READ", "## WRITE ONLY",
                     "## READY MARKER", "## FAILED ARTIFACT",
                     "## DO NOT EDIT", "## STOP CONDITION"):
        assert required in body, f"missing section: {required}"


def test_i_manual_provider_does_not_invoke_external_agents(monkeypatch, tmp_path):
    """The dispatcher's manual provider must not spawn Claude or Codex
    CLIs. Stub subprocess.run/Popen to assert no calls happen.
    """
    import subprocess as sp
    called: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        called.append(list(cmd) if isinstance(cmd, list) else [str(cmd)])
        return sp.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(sp, "run", fake_run)
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)
    rev = _make_reviewer_result(tmp_path / "reviews")
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(rev.read_text())
    _write_ready(bus, "reviewer")
    agent_bus.advance(bus, repo_root=tmp_path)
    # The only subprocess.run calls allowed are git/pytest/etc., never
    # invoking claude or codex binaries.
    for cmd in called:
        joined = " ".join(str(c) for c in cmd).lower()
        assert "claude" not in joined, cmd
        assert "codex" not in joined, cmd


def test_j_watch_mode_advances_one_phase_per_iteration(tmp_path):
    """watch() must perform at most one phase move per poll cycle."""
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    rep = _make_executor_report(tmp_path / "reports")
    rev = _make_reviewer_result(tmp_path / "reviews")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    (bus / "executor" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    (bus / "reviewer" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(rev.read_text())
    _write_ready(bus, "reviewer")
    # max_iterations=10 with no sleep -> exactly 3 advances + 1 stop.
    obs = agent_bus.watch(bus, poll_interval=0.0, max_iterations=10, sleep_fn=lambda _s: None)
    # Expect at most one phase move per poll, ending in ROUND_SUMMARY_READY.
    final = obs[-1]
    assert final["phase"] == agent_bus.PHASE_ROUND_SUMMARY_READY
    # Count ADVANCE outcomes.
    advances = [o for o in obs if o.get("watch_outcome") == agent_bus.WATCH_OUTCOME_ADVANCE]
    assert len(advances) == 3, [o.get("watch_outcome") for o in obs]
    assert obs[-1]["watch_outcome"] in {
        agent_bus.WATCH_OUTCOME_ADVANCE,
        agent_bus.WATCH_OUTCOME_STOP_TERMINAL,
    }


def test_k_watch_mode_idles_when_expected_artifact_absent(tmp_path):
    """No task spec in planner outbox -> watch must idle, not advance."""
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    obs = agent_bus.watch(bus, poll_interval=0.0, max_iterations=3, sleep_fn=lambda _s: None)
    assert obs[-1]["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC
    assert obs[-1]["watch_outcome"] == agent_bus.WATCH_OUTCOME_IDLE


def test_l_watch_mode_idles_when_ready_marker_absent(tmp_path):
    """Artifact present but no ready marker must IDLE_WAITING_FOR_READY_MARKER,
    and the dispatcher must NOT auto-write the marker.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    # Resolve the concrete task spec the planner would have chosen.
    chosen = agent_bus.accept_planner_task_choose_only(bus)
    # Validation must reject: ready marker absent.
    ok, reason = agent_bus.validate_artifact_for_role(
        "planner", bus, artifact_path=chosen
    )
    assert ok is False
    assert "ready marker" in reason
    # advance() must NOT advance and must NOT create the ready marker.
    out = agent_bus.advance(bus)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC
    assert (bus / "planner" / "outbox" / "TASK_READY").exists() is False
    # Watch outcome must clearly indicate the missing-marker state.
    assert out["watch_outcome"] == agent_bus.WATCH_OUTCOME_IDLE_WAITING_FOR_READY_MARKER
    # After the marker is dropped, the next advance must succeed.
    _write_ready(bus, "planner")
    out = agent_bus.advance(bus)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_EXECUTOR_REPORT
    assert out["watch_outcome"] == agent_bus.WATCH_OUTCOME_ADVANCE


def test_m_watch_mode_refuses_to_advance_with_invalid_reviewer_result(tmp_path):
    """Garbage reviewer JSON must keep phase WAITING_FOR_REVIEW_RESULT."""
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)
    (bus / "reviewer" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text("{not json")
    obs = agent_bus.watch(bus, poll_interval=0.0, max_iterations=2, sleep_fn=lambda _s: None)
    assert obs[-1]["phase"] == agent_bus.PHASE_WAITING_FOR_REVIEW_RESULT
    assert obs[-1]["watch_outcome"] in {
        agent_bus.WATCH_OUTCOME_FAIL,
        agent_bus.WATCH_OUTCOME_IDLE,
    }


def test_n_watch_mode_stops_at_human_boundary(tmp_path):
    """HUMAN_SIGNOFF_REQUIRED -> watch must STOP_HUMAN_BOUNDARY, never
    touch the planner inbox.
    """
    nar = _make_nar(tmp_path, classification_code="HUMAN_SIGNOFF_REQUIRED")
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    # Preplace planner artifacts; watch must still idle at the boundary.
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text("# task")
    _write_ready(bus, "planner")
    obs = agent_bus.watch(bus, poll_interval=0.0, max_iterations=3, sleep_fn=lambda _s: None)
    assert obs[0]["phase"] == agent_bus.PHASE_WAITING_FOR_HUMAN_APPROVAL
    assert obs[0]["watch_outcome"] == agent_bus.WATCH_OUTCOME_STOP_HUMAN_BOUNDARY
    assert not (bus / "executor" / "inbox" / "executor_prompt.md").exists()


def test_o_status_includes_role_ready_marker_provider(tmp_path):
    """--status output must include role, ready marker, provider, etc."""
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    out = agent_bus.status(bus)
    assert out["current_role"] == "planner"
    assert out["provider_name"] == "CodexPlanner"
    assert out["provider_type"] == agent_bus.PROVIDER_TYPE_MANUAL
    assert out["expected_ready_marker"].endswith("TASK_READY")
    assert out["failed_artifact_path"].endswith("planner_failed.md")
    assert out["current_job_envelope_path"].endswith("planner_job.json")
    assert out["expected_artifact_path"].endswith("TASK_*.md")


def test_p_failed_artifact_transitions_to_failed(tmp_path):
    """A planner failed artifact must transition the round to FAILED
    automatically on the next advance.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    failed = bus / "planner" / "failed" / "planner_failed.md"
    failed.parent.mkdir(parents=True, exist_ok=True)
    failed.write_text("# failed", encoding="utf-8")
    out = agent_bus.advance(bus)
    # Failed artifact present -> round transitions to FAILED.
    assert out["phase"] == agent_bus.PHASE_FAILED
    assert out["failure_role"] == "planner"
    assert "planner failed artifact" in out["failure_reason"]
    # Failure evidence persisted.
    assert (bus / "round_state" / "failure_planner.json").exists()
    # Watch outcome must be FAIL (not IDLE).
    assert out["watch_outcome"] == agent_bus.WATCH_OUTCOME_FAIL
    # Validation must also reject when explicitly called.
    ok, reason = agent_bus.validate_artifact_for_role("planner", bus)
    assert ok is False
    assert "failed artifact" in reason


def test_q_mock_provider_for_role_only_used_in_tests(tmp_path):
    """Mock provider override must still be classified as 'mock' and the
    default manual provider must remain manual.
    """
    envelope_manual = agent_bus.render_job_envelope(
        "planner", tmp_path, {"round_id": "X", "phase": "WAITING_FOR_TASK_SPEC"}
    )
    assert envelope_manual["provider_type"] == agent_bus.PROVIDER_TYPE_MANUAL
    envelope_mock = agent_bus.render_job_envelope(
        "planner", tmp_path, {"round_id": "X", "phase": "WAITING_FOR_TASK_SPEC"},
        provider_override=("MockPlanner", agent_bus.PROVIDER_TYPE_MOCK),
    )
    assert envelope_mock["provider_name"] == "MockPlanner"
    assert envelope_mock["provider_type"] == agent_bus.PROVIDER_TYPE_MOCK
    # Default manual provider name must NOT be clobbered by mock override.
    assert envelope_manual["provider_name"] == "CodexPlanner"


def test_r_watch_mode_calls_advance_at_most_once_per_iteration(tmp_path):
    """Internal: ``watch_one`` must invoke ``advance()`` at most once
    even when no transition is possible.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    out_first = agent_bus.watch_one(bus, sleep_fn=lambda _s: None)
    out_second = agent_bus.watch_one(bus, sleep_fn=lambda _s: None)
    # Phase should not move; we have no planner output.
    assert out_first["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC
    assert out_second["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC
    assert out_first["watch_outcome"] == agent_bus.WATCH_OUTCOME_IDLE


def test_s_dispatcher_does_not_touch_scientific_or_signoff_artifacts_watch(tmp_path):
    """Even with watch mode, protected files are byte-identical."""
    stage = _make_stage_fixture(tmp_path / "stage_fixture")
    protected_paths = [
        "STAGE_PLAN.md",
        "CLAIM_BOUNDARY.md",
        "validation_summary.json",
        "review_result.json",
        "completion_matrix.json",
        ".loop/human_signoff.yaml",
        ".loop/human_signoff_ledger.jsonl",
        ".loop/human_signoff_history/x.json",
    ]
    snapshot_before = {rel: (stage / rel).read_bytes() for rel in protected_paths}
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.watch(bus, poll_interval=0.0, max_iterations=2, sleep_fn=lambda _s: None)
    snapshot_after = {rel: (stage / rel).read_bytes() for rel in protected_paths}
    assert snapshot_before == snapshot_after


# ---------------------------------------------------------------------------
# TASK_027 PATCH regression tests (reviewer verdict FAIL -> FIX):
#   a. output file exists but ready marker absent -> no advance
#   b. dispatcher does not auto-create ready markers
#   c. planner failed artifact -> FAILED
#   d. executor failed artifact -> FAILED
#   e. reviewer failed artifact -> FAILED
#   f. planner job envelope phase equals WAITING_FOR_TASK_SPEC
#   g. existing one-phase preplaced-artifact behavior remains safe
#   h. invalid reviewer result remains rejected
#   i. human boundary still stops at WAITING_FOR_HUMAN_APPROVAL
# ---------------------------------------------------------------------------


def test_t27a_output_present_but_marker_absent_blocks_advance(tmp_path):
    """Output exists, ready marker absent -> advance() must NOT move the
    phase. State must remain WAITING_FOR_TASK_SPEC. The watch outcome
    must clearly indicate the missing-marker state.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    # No ready marker dropped. advance() must NOT advance.
    out = agent_bus.advance(bus)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC
    assert (bus / "planner" / "outbox" / "TASK_READY").exists() is False
    assert out["watch_outcome"] == agent_bus.WATCH_OUTCOME_IDLE_WAITING_FOR_READY_MARKER
    # Direct validation must reject.
    chosen = agent_bus.accept_planner_task_choose_only(bus)
    ok, reason = agent_bus.validate_artifact_for_role(
        "planner", bus, artifact_path=chosen
    )
    assert ok is False
    assert "ready marker" in reason


def test_t27b_dispatcher_does_not_auto_create_ready_markers(tmp_path):
    """Across all three roles, the dispatcher must NEVER auto-create
    ready markers. The provider/session must write them.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    # Planner role.
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    agent_bus.advance(bus)
    assert (bus / "planner" / "outbox" / "TASK_READY").exists() is False
    # Now drop the marker; advance must move us forward.
    _write_ready(bus, "planner")
    agent_bus.advance(bus)
    # Executor role: drop report, do NOT drop marker.
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    agent_bus.advance(bus, repo_root=tmp_path)
    assert (bus / "executor" / "outbox" / "EXECUTOR_READY").exists() is False
    # Drop the marker; advance moves us forward.
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)
    # Reviewer role: drop result, do NOT drop marker.
    rev = _make_reviewer_result(tmp_path / "reviews")
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(rev.read_text())
    agent_bus.advance(bus, repo_root=tmp_path)
    assert (bus / "reviewer" / "outbox" / "REVIEW_READY").exists() is False


def test_t27c_planner_failed_artifact_transitions_to_failed(tmp_path):
    """Planner dropped <planner>/failed/planner_failed.md -> round must
    transition to FAILED on the next advance.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    failed = bus / "planner" / "failed" / "planner_failed.md"
    failed.parent.mkdir(parents=True, exist_ok=True)
    failed.write_text("planner could not produce a task spec", encoding="utf-8")
    out = agent_bus.advance(bus)
    assert out["phase"] == agent_bus.PHASE_FAILED
    assert out["failure_role"] == "planner"
    assert out["watch_outcome"] == agent_bus.WATCH_OUTCOME_FAIL
    assert (bus / "round_state" / "failure_planner.json").exists()
    # Subsequent advance() calls must not re-open the round.
    out2 = agent_bus.advance(bus)
    assert out2["phase"] == agent_bus.PHASE_FAILED


def test_t27d_executor_failed_artifact_transitions_to_failed(tmp_path):
    """Executor dropped <executor>/failed/executor_failed.md -> round must
    transition to FAILED on the next advance (after a valid planner
    handoff).
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)  # -> WAITING_FOR_EXECUTOR_REPORT
    failed = bus / "executor" / "failed" / "executor_failed.md"
    failed.parent.mkdir(parents=True, exist_ok=True)
    failed.write_text("executor cannot complete the task", encoding="utf-8")
    out = agent_bus.advance(bus, repo_root=tmp_path)
    assert out["phase"] == agent_bus.PHASE_FAILED
    assert out["failure_role"] == "executor"
    assert out["watch_outcome"] == agent_bus.WATCH_OUTCOME_FAIL
    assert (bus / "round_state" / "failure_executor.json").exists()


def test_t27e_reviewer_failed_artifact_transitions_to_failed(tmp_path):
    """Reviewer dropped <reviewer>/failed/reviewer_failed.md -> round must
    transition to FAILED on the next advance (after valid planner +
    executor handoffs).
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)  # -> WAITING_FOR_EXECUTOR_REPORT
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)  # -> WAITING_FOR_REVIEW_RESULT
    failed = bus / "reviewer" / "failed" / "reviewer_failed.md"
    failed.parent.mkdir(parents=True, exist_ok=True)
    failed.write_text("reviewer cannot complete the review", encoding="utf-8")
    out = agent_bus.advance(bus, repo_root=tmp_path)
    assert out["phase"] == agent_bus.PHASE_FAILED
    assert out["failure_role"] == "reviewer"
    assert out["watch_outcome"] == agent_bus.WATCH_OUTCOME_FAIL
    assert (bus / "round_state" / "failure_reviewer.json").exists()


def test_t27f_planner_job_envelope_phase_equals_waiting_for_task_spec(tmp_path):
    """The generated planner job envelope must record the active waiting
    phase (WAITING_FOR_TASK_SPEC), not the initial INIT phase.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    state = agent_bus.start_round(bus, next_action_report=nar)
    # Round state itself must already be in the waiting phase.
    assert state["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC
    envelope_path = bus / "planner" / "inbox" / "planner_job.json"
    assert envelope_path.exists()
    envelope = json.loads(envelope_path.read_text())
    assert envelope["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC


def test_t27g_preplaced_artifacts_one_phase_per_advance_still_safe(tmp_path):
    """Existing TASK_026 safety: preplaced artifacts + ready markers
    must require one advance() per phase move, not be consumed across
    multiple phases in a single call.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    rep = _make_executor_report(tmp_path / "reports")
    rev = _make_reviewer_result(tmp_path / "reviews")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    (bus / "executor" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    (bus / "reviewer" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(rev.read_text())
    _write_ready(bus, "reviewer")
    out1 = agent_bus.advance(bus)
    assert out1["phase"] == agent_bus.PHASE_WAITING_FOR_EXECUTOR_REPORT
    out2 = agent_bus.advance(bus, repo_root=tmp_path)
    assert out2["phase"] == agent_bus.PHASE_WAITING_FOR_REVIEW_RESULT
    out3 = agent_bus.advance(bus, repo_root=tmp_path)
    assert out3["phase"] == agent_bus.PHASE_ROUND_SUMMARY_READY


def test_t27h_invalid_reviewer_result_still_rejected(tmp_path):
    """TASK_026 safety: invalid reviewer JSON must NOT advance; phase
    must stay at WAITING_FOR_REVIEW_RESULT.
    """
    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    agent_bus.advance(bus)
    rep = _make_executor_report(tmp_path / "reports")
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    agent_bus.advance(bus, repo_root=tmp_path)
    (bus / "reviewer" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text("{not json")
    _write_ready(bus, "reviewer")
    with pytest.raises(agent_bus.InvalidReviewerResult):
        agent_bus.accept_reviewer_result(bus)
    out = agent_bus.advance(bus, repo_root=tmp_path)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_REVIEW_RESULT
    assert (bus / "round_state" / "reviewer_error.json").exists()


def test_t27i_human_boundary_still_stops_at_waiting_for_human_approval(tmp_path):
    """HUMAN_SIGNOFF_REQUIRED -> round enters WAITING_FOR_HUMAN_APPROVAL.
    Even with preplaced planner + executor + reviewer artifacts AND their
    ready markers, advance() must not move the phase.
    """
    nar = _make_nar(tmp_path, classification_code="HUMAN_SIGNOFF_REQUIRED")
    bus = tmp_path / "bus"
    state = agent_bus.start_round(bus, next_action_report=nar)
    assert state["phase"] == agent_bus.PHASE_WAITING_FOR_HUMAN_APPROVAL
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    _write_ready(bus, "planner")
    rep = _make_executor_report(tmp_path / "reports")
    rev = _make_reviewer_result(tmp_path / "reviews")
    (bus / "executor" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "executor" / "outbox" / "executor_report.md").write_text(rep.read_text())
    _write_ready(bus, "executor")
    (bus / "reviewer" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "reviewer" / "outbox" / "patch_review_result.json").write_text(rev.read_text())
    _write_ready(bus, "reviewer")
    out = agent_bus.advance(bus, repo_root=tmp_path)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_HUMAN_APPROVAL
    assert not (bus / "executor" / "inbox" / "executor_prompt.md").exists()
    assert not (bus / "reviewer" / "inbox" / "reviewer_prompt.md").exists()


def test_t27j_missing_ready_marker_state_validates_against_schema(tmp_path):
    """Regression: the round state written after a missing-ready-marker
    advance() must (a) record ``watch_outcome = IDLE_WAITING_FOR_READY_MARKER``
    on disk and (b) validate against ``agent_bus_state.schema.json``
    without error. The schema enum must include the new outcome.
    """
    from loop_engine.schemas import validate_with_schema

    nar = _make_nar(tmp_path)
    bus = tmp_path / "bus"
    agent_bus.start_round(bus, next_action_report=nar)
    task = _make_task_spec(tmp_path / "task")
    (bus / "planner" / "outbox").mkdir(parents=True, exist_ok=True)
    (bus / "planner" / "outbox" / "TASK_TEST.md").write_text(task.read_text())
    # No ready marker dropped. advance() must NOT advance.
    out = agent_bus.advance(bus)
    assert out["phase"] == agent_bus.PHASE_WAITING_FOR_TASK_SPEC
    assert out["watch_outcome"] == agent_bus.WATCH_OUTCOME_IDLE_WAITING_FOR_READY_MARKER
    # Re-read the on-disk round state and confirm the new outcome is
    # persisted.
    state_path = bus / "round_state" / "current_round.json"
    assert state_path.exists()
    state = json.loads(state_path.read_text())
    assert state["watch_outcome"] == agent_bus.WATCH_OUTCOME_IDLE_WAITING_FOR_READY_MARKER
    # Schema validation must succeed against the updated enum.
    validate_with_schema(state, "agent_bus_state")

