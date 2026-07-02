from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from loop_engine.agent_invocation import hash_protected_files, verify_read_only_contract
from loop_engine.agent_runtime import (
    AgentInvocationRequest,
    CommandAgentAdapter,
    DryRunStubAdapter,
    resolve_agent_runtime,
)
from loop_engine.config import REPO_ROOT, write_text
from loop_engine.runtime_failures import classify_agent_runtime_failure


def test_command_agent_adapter_invocation_evidence(tmp_path: Path):
    stage = tmp_path / "stage"
    stage.mkdir()
    output_path = stage / ".loop" / "reviewer_results" / "algebra_reviewer.json"
    prompt_path = stage / "prompt.md"
    write_text(prompt_path, "# Prompt\n")
    command = [
        sys.executable,
        "-c",
        (
            "import json, pathlib, sys; "
            "out=pathlib.Path(sys.argv[1]); out.parent.mkdir(parents=True, exist_ok=True); "
            "json.dump({'verdict':'PASS','stage_name':'stage','mathematical_status':"
            "{'exact_reconstruction':True,'simplification_real':True,'regression_preserved':True,"
            "'overclaim_detected':False},'blocking_issues':[],'nonblocking_caveats':[],"
            "'allowed_claims':['ok'],'forbidden_claims':['no overclaim'],'next_action':'FREEZE',"
            "'suggested_next_stage':None,'patch_instructions':[]}, out.open('w'))"
        ),
        "{output_path}",
    ]
    adapter = CommandAgentAdapter(command=command, timeout_seconds=30)
    summary = adapter.invoke(
        AgentInvocationRequest(
            agent_name="AlgebraReviewer",
            stage_dir=stage,
            prompt_path=prompt_path,
            output_path=output_path,
            schema_name="review_result",
            protected_paths=[stage / "protected.txt"],
        )
    )
    evidence_dir = stage / ".loop" / "agent_invocations" / "AlgebraReviewer"
    assert summary["actually_invoked"] is True
    assert summary["stub_used"] is False
    assert summary["exit_code"] == 0
    assert summary["schema_valid"] is True
    assert summary["read_only_contract_enforced"] is True
    assert (evidence_dir / "prompt.md").exists()
    assert (evidence_dir / "input_manifest.json").exists()
    assert (evidence_dir / "command.txt").exists()
    assert (evidence_dir / "stdout.txt").exists()
    assert (evidence_dir / "stderr.txt").exists()
    assert (evidence_dir / "exit_code.txt").read_text().strip() == "0"
    assert (evidence_dir / "output_hash.txt").read_text().strip()
    assert json.loads((evidence_dir / "invocation_summary.json").read_text())["schema_valid"] is True


def test_stub_forbidden_in_production():
    profile = {
        "agents": {
            "require_real_invocation": True,
            "forbid_stub_in_production": True,
            "allow_stub_for_tests": False,
        }
    }
    status = resolve_agent_runtime(profile, profile_name="unconfigured_production_profile")
    assert status.available is False
    assert status.production_run_allowed is False
    assert status.adapter == "unavailable"


def test_runtime_check_reports_available_for_sigma_abc_local_command():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_agent_runtime.py"), "--profile", "sigma_abc_hypothesis_pre_ibp"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "AgentRuntimeStatus -> AVAILABLE" in result.stdout
    assert "Adapter -> command" in result.stdout
    assert "ProductionRunAllowed -> True" in result.stdout


def test_runtime_check_reports_available_for_mock_command(tmp_path: Path):
    local = REPO_ROOT / "agents" / "runtime.local.yaml"
    previous = local.read_text() if local.exists() else None
    try:
        local.write_text(
            yaml.safe_dump(
                {
                    "profiles": {
                        "test_hypothesis_search_loop": {
                            "runtime": {
                                "adapter": "command",
                                "command": [sys.executable, "-c", "print('agent ok')"],
                                "timeout_seconds": 30,
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "check_agent_runtime.py"), "--profile", "test_hypothesis_search_loop"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        assert "AgentRuntimeStatus -> AVAILABLE" in result.stdout
        assert "Adapter -> command" in result.stdout
        assert "ProductionRunAllowed -> True" in result.stdout
    finally:
        if previous is None:
            local.unlink(missing_ok=True)
        else:
            local.write_text(previous, encoding="utf-8")


def test_agent_output_schema_validation_required(tmp_path: Path):
    stage = tmp_path / "stage"
    stage.mkdir()
    output_path = stage / ".loop" / "reviewer_results" / "algebra_reviewer.json"
    prompt_path = stage / "prompt.md"
    write_text(prompt_path, "# Prompt\n")
    adapter = CommandAgentAdapter(
        command=[
            sys.executable,
            "-c",
            "import pathlib, sys; p=pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True); p.write_text('{\"verdict\":\"PASS\"}')",
            "{output_path}",
        ],
        timeout_seconds=30,
    )
    summary = adapter.invoke(
        AgentInvocationRequest(
            agent_name="AlgebraReviewer",
            stage_dir=stage,
            prompt_path=prompt_path,
            output_path=output_path,
            schema_name="review_result",
        )
    )
    assert summary["exit_code"] == 0
    assert summary["schema_valid"] is False
    assert summary["freeze_evidence_valid"] is False


def test_command_agent_adapter_timeout_returns_structured_failure(tmp_path: Path):
    stage = tmp_path / "stage"
    stage.mkdir()
    output_path = stage / ".loop" / "reviewer_results" / "software_reviewer.json"
    prompt_path = stage / "prompt.md"
    write_text(prompt_path, "# Prompt\n")
    adapter = CommandAgentAdapter(
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        timeout_seconds=1,
    )

    summary = adapter.invoke(
        AgentInvocationRequest(
            agent_name="SoftwareReviewer",
            stage_dir=stage,
            prompt_path=prompt_path,
            output_path=output_path,
            schema_name="review_result",
        )
    )

    evidence_dir = stage / ".loop" / "agent_invocations" / "SoftwareReviewer"
    assert summary["actually_invoked"] is True
    assert summary["stub_used"] is False
    assert summary["timeout_expired"] is True
    assert summary["freeze_evidence_valid"] is False
    assert (evidence_dir / "exit_code.txt").read_text().strip() == "TIMEOUT"
    assert "timed out" in (evidence_dir / "stderr.txt").read_text().lower()


def test_codex_usage_limit_failure_is_classified_as_retry_not_patch():
    classification = classify_agent_runtime_failure(
        summary={"exit_code": 1, "schema_valid": False, "freeze_evidence_valid": False},
        stdout="",
        stderr="You've hit your usage limit. Please try again at Jun 30th, 2026 1:01 AM.",
    )

    assert classification["kind"] == "AGENT_RUNTIME_QUOTA_EXHAUSTED"
    assert classification["patch_required"] is False
    assert classification["retry_after"] == "Jun 30th, 2026 1:01 AM"
    assert "RetryAfter -> Jun 30th, 2026 1:01 AM" in classification["issue"]


def test_read_only_contract_blocks_protected_file_modification(tmp_path: Path):
    protected = tmp_path / "protected.txt"
    write_text(protected, "before\n")
    before = hash_protected_files([protected])
    write_text(protected, "after\n")
    result = verify_read_only_contract(before)
    assert result["ReviewerModifiedProtectedFiles"] is True
    assert result["Decision"] == "HARD_STOP"


def test_dry_run_stub_adapter_is_not_freeze_evidence(tmp_path: Path):
    stage = tmp_path / "stage"
    stage.mkdir()
    prompt = stage / "prompt.md"
    output = stage / ".loop" / "reviewer_results" / "algebra_reviewer.json"
    write_text(prompt, "# Prompt\n")
    summary = DryRunStubAdapter().invoke(
        AgentInvocationRequest(
            agent_name="AlgebraReviewer",
            stage_dir=stage,
            prompt_path=prompt,
            output_path=output,
            schema_name="review_result",
        )
    )
    assert summary["actually_invoked"] is False
    assert summary["stub_used"] is True
    assert summary["freeze_evidence_valid"] is False


def test_run_agent_accepts_stage_dir_aliases_and_default_paths(tmp_path: Path):
    local = REPO_ROOT / "agents" / "runtime.local.yaml"
    previous = local.read_text() if local.exists() else None
    stage = tmp_path / "mock_stage"
    (stage / ".loop").mkdir(parents=True)
    (stage / ".loop" / "validation_summary.json").write_text(
        json.dumps({"stage_name": "mock_stage", "overall_gate": "PASS", "checks": []}),
        encoding="utf-8",
    )
    (stage / ".loop" / "metrics.json").write_text(json.dumps({"stage_name": "mock_stage"}), encoding="utf-8")
    (stage / "review_packet.md").write_text("# Review Packet\n", encoding="utf-8")
    (stage / "CLAIM_BOUNDARY.md").write_text("# Claim Boundary\n", encoding="utf-8")
    try:
        local.write_text(
            yaml.safe_dump(
                {
                    "profiles": {
                        "test_hypothesis_search_loop_real_agent": {
                            "runtime": {
                                "adapter": "command",
                                "command": [
                                    sys.executable,
                                    "-c",
                                    (
                                        "import json, pathlib, sys; "
                                        "out=pathlib.Path(sys.argv[1]); out.parent.mkdir(parents=True, exist_ok=True); "
                                        "json.dump({'verdict':'PASS','stage_name':'mock_stage','reviewer_role':'AlgebraReviewer',"
                                        "'review_scope':'routine_branch','mathematical_status':"
                                        "{'exact_reconstruction':True,'simplification_real':True,'regression_preserved':True,"
                                        "'overclaim_detected':False},'blocking_issues':[],'nonblocking_caveats':[],"
                                        "'allowed_claims':['mock pass'],'forbidden_claims':['no physics claim'],"
                                        "'next_action':'FREEZE','suggested_next_stage':None,'patch_instructions':[]}, out.open('w'))"
                                    ),
                                    "{output_path}",
                                ],
                                "timeout_seconds": 30,
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "run_agent.py"),
                "--profile",
                "test_hypothesis_search_loop_real_agent",
                "--agent",
                "AlgebraReviewer",
                "--stage-dir",
                str(stage),
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        assert "invocation_summary.json" in result.stdout
        evidence = stage / ".loop" / "agent_invocations" / "AlgebraReviewer"
        summary = json.loads((evidence / "invocation_summary.json").read_text())
        assert summary["actually_invoked"] is True
        assert summary["stub_used"] is False
        assert summary["schema_valid"] is True
        assert (stage / ".loop" / "reviewer_results" / "algebra_reviewer.json").exists()
    finally:
        if previous is None:
            local.unlink(missing_ok=True)
        else:
            local.write_text(previous, encoding="utf-8")


def test_real_agent_profile_forbids_stub_runtime():
    profile = yaml.safe_load((REPO_ROOT / "profiles" / "test_hypothesis_search_loop_real_agent.yaml").read_text())
    assert profile["agents"]["require_real_invocation"] is True
    assert profile["agents"]["forbid_stub_in_production"] is True
    assert profile["agents"]["allow_stub_for_tests"] is False
