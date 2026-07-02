from __future__ import annotations

import json
import sys
from pathlib import Path

from loop_engine.agent_runtime import AgentInvocationRequest, CommandAgentAdapter
from loop_engine.config import read_json, write_json, write_text

DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


def make_l1_stage(tmp_path: Path, *, name: str = "sigma_abc_012a_loop_sector_inventory", lane: str = "L1_COMPACT_META") -> Path:
    stage = tmp_path / name
    for folder in [".loop/reviewer_results", ".loop/review_queue", "reports", "output", "validation"]:
        (stage / folder).mkdir(parents=True, exist_ok=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n\nLow-risk provenance stage only.\n")
    write_text(stage / "EXECUTION_REPORT.md", "# Execution Report\n\nNo symbolic promotion.\n")
    write_text(stage / "CLAIM_BOUNDARY.md", f"# Claim Boundary\n\n{DC_CAVEAT}\n")
    validation = {
        "stage_name": stage.name,
        "overall_gate": "PASS",
        "identity_type": "Loop011L1DebtFixture",
        "checks": [{"name": "fixture", "expected": "PASS", "actual": "PASS", "gate": "PASS"}],
        "NoCandidatePromoted": True,
        "NoKernelFusionStarted": True,
        "NoIBPStarted": True,
        "NoTotalDerivativeIntroduced": True,
        "NoFullTensorialClaim": True,
        "Stage001DCCaveatPreserved": True,
        "ProtectedBenchmarksUnchanged": True,
        "caveats": [DC_CAVEAT],
    }
    risk = {
        "risk_level": "LOW" if lane == "L1_COMPACT_META" else "HIGH",
        "review_lane": lane,
        "reviewers": ["ScientificMetaReviewer"] if lane == "L1_COMPACT_META" else ["AlgebraReviewer", "PhysicsReviewer", "SoftwareReviewer", "ScientificMetaReviewer"],
        "full_panel_required": lane == "L2_FULL_PANEL",
    }
    write_json(stage / ".loop" / "validation_summary.json", validation)
    write_json(stage / ".loop" / "risk_classification.json", risk)
    write_json(stage / ".loop" / "metrics.json", {"stage_name": stage.name})
    return stage


def throughput_profile() -> dict:
    return {
        "review_debt": {
            "allow_low_risk_advance": True,
            "allow_l1_quota_debt": True,
            "max_open_review_debts": 2,
            "block_before_l2_promotion": True,
            "block_before_global_assembly": True,
            "block_before_ibp": True,
        },
        "review_policy": {
            "l1_timeout_seconds": 180,
            "l1_on_timeout": "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT",
            "l1_on_quota": "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT",
            "l1_on_no_output": "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT",
            "l1_allow_advance_if_validation_passed": True,
            "l1_requires_review_debt_entry": True,
            "l2_timeout_seconds": 900,
            "l2_on_timeout": "VALIDATED_PENDING_REVIEW",
            "l2_allow_advance_if_validation_passed": False,
            "lanes": {
                "L1_COMPACT_META": {"reviewers": ["ScientificMetaReviewer"]},
                "L2_FULL_PANEL": {"reviewers": ["AlgebraReviewer", "PhysicsReviewer", "SoftwareReviewer", "ScientificMetaReviewer"]},
            },
        },
    }


def write_runtime_review(stage: Path, *, kind: str, lane: str = "L1_COMPACT_META") -> None:
    review = {
        "verdict": "FAILED",
        "stage_name": stage.name,
        "reviewer_role": "ScientificMetaReviewer",
        "review_scope": lane,
        "mathematical_status": {
            "exact_reconstruction": False,
            "simplification_real": False,
            "regression_preserved": False,
            "overclaim_detected": False,
        },
        "blocking_issues": [f"{kind}: real L1 reviewer invocation did not produce valid freeze evidence."],
        "nonblocking_caveats": [],
        "allowed_claims": [],
        "forbidden_claims": ["Do not ordinary-freeze without a valid review."],
        "next_action": "FAIL",
        "suggested_next_stage": None,
        "patch_instructions": [],
    }
    write_json(stage / ".loop" / "review_result.json", review)


def test_command_agent_adapter_timeout_returns_agent_timeout_status(tmp_path: Path):
    stage = tmp_path / "stage"
    stage.mkdir()
    prompt = stage / "prompt.md"
    output = stage / ".loop" / "reviewer_results" / "scientific_metareviewer.json"
    write_text(prompt, "# Prompt\n")
    adapter = CommandAgentAdapter(
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        timeout_seconds=1,
    )

    summary = adapter.invoke(
        AgentInvocationRequest(
            agent_name="ScientificMetaReviewer",
            stage_dir=stage,
            prompt_path=prompt,
            output_path=output,
            schema_name="review_result",
        )
    )

    assert summary["runtime_status"] == "AGENT_TIMEOUT"
    assert summary["exit_code"] is None
    assert summary["review_debt_required"] is True
    assert (stage / ".loop" / "agent_invocations" / "ScientificMetaReviewer" / "exit_code.txt").read_text().strip() == "TIMEOUT"


def test_command_agent_adapter_no_output_returns_agent_no_output_status(tmp_path: Path):
    stage = tmp_path / "stage"
    stage.mkdir()
    prompt = stage / "prompt.md"
    output = stage / ".loop" / "reviewer_results" / "scientific_metareviewer.json"
    write_text(prompt, "# Prompt\n")
    adapter = CommandAgentAdapter(command=[sys.executable, "-c", "pass"], timeout_seconds=5)

    summary = adapter.invoke(
        AgentInvocationRequest(
            agent_name="ScientificMetaReviewer",
            stage_dir=stage,
            prompt_path=prompt,
            output_path=output,
            schema_name="review_result",
        )
    )

    assert summary["runtime_status"] == "AGENT_NO_OUTPUT"
    assert summary["schema_valid"] is False
    assert summary["review_debt_required"] is True


def test_l1_timeout_creates_review_debt_not_hard_stop(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed

    stage = make_l1_stage(tmp_path)
    write_runtime_review(stage, kind="AGENT_TIMEOUT")

    result = create_review_debt_if_allowed(stage, throughput_profile())

    assert result["stage_status"] == "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT"
    assert result["status"] == "OPEN"
    assert result["allowed_to_advance"] is True
    assert result["CheckpointStatus"] == "PROVISIONAL_WITH_REVIEW_DEBT"
    decision = read_json(stage / ".loop" / "decision.json")
    assert decision["action"] == "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT"
    assert decision["OrdinaryReviewComplete"] is False
    assert decision["PatchRequired"] is False


def test_l1_no_output_creates_review_debt(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed

    stage = make_l1_stage(tmp_path)
    write_runtime_review(stage, kind="AGENT_NO_OUTPUT")

    result = create_review_debt_if_allowed(stage, throughput_profile())

    assert result["stage_status"] == "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT"
    assert result["reason"].startswith("AGENT_NO_OUTPUT")


def test_l1_review_debt_allows_012b_and_012c_prep_but_blocks_012c_promotion(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed, downstream_blocked_by_review_debt

    stage = make_l1_stage(tmp_path)
    write_runtime_review(stage, kind="AGENT_TIMEOUT")
    create_review_debt_if_allowed(stage, throughput_profile())

    assert downstream_blocked_by_review_debt(tmp_path, "sigma_abc_012b_loop_hypothesis_generation")["blocked"] is False
    prep = downstream_blocked_by_review_debt(tmp_path, "sigma_abc_012c_real_loop_candidate_preparation")
    assert prep["blocked"] is False
    blocked = downstream_blocked_by_review_debt(tmp_path, "sigma_abc_012c_loop_orbit_canonicalization_promotion")
    assert blocked["blocked"] is True
    assert "candidate_promotion" in blocked["reason"]


def test_l2_timeout_does_not_allow_advance(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed

    stage = make_l1_stage(tmp_path, name="sigma_abc_012c_loop_orbit_canonicalization_promotion", lane="L2_FULL_PANEL")
    write_runtime_review(stage, kind="AGENT_TIMEOUT", lane="L2_FULL_PANEL")

    result = create_review_debt_if_allowed(stage, throughput_profile())

    assert result["stage_status"] == "REVIEW_DEBT_BLOCKED"
    assert result["allowed_to_advance"] is False


def test_settle_l1_review_debt_without_executor_rerun(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed, settle_review_debt

    stage = make_l1_stage(tmp_path)
    write_text(stage / "EXECUTOR_SENTINEL.txt", "do not change\n")
    sentinel_before = (stage / "EXECUTOR_SENTINEL.txt").read_text()
    write_runtime_review(stage, kind="AGENT_TIMEOUT")
    create_review_debt_if_allowed(stage, throughput_profile())
    review = read_json(stage / ".loop" / "review_result.json")
    review["verdict"] = "PASS_WITH_CAVEAT"
    review["blocking_issues"] = []
    review["nonblocking_caveats"] = [DC_CAVEAT]
    review["next_action"] = "FREEZE"
    write_json(stage / ".loop" / "review_result.json", review)

    result = settle_review_debt(tmp_path, stage.name)

    assert result["status"] == "SETTLED"
    assert read_json(stage / ".loop" / "review_debt.json")["CheckpointStatus"] == "FROZEN_WITH_CAVEAT"
    assert (stage / "EXECUTOR_SENTINEL.txt").read_text() == sentinel_before


def test_failed_debt_review_blocks_promotion(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed, downstream_blocked_by_review_debt, settle_review_debt

    stage = make_l1_stage(tmp_path)
    write_runtime_review(stage, kind="AGENT_TIMEOUT")
    create_review_debt_if_allowed(stage, throughput_profile())
    review = read_json(stage / ".loop" / "review_result.json")
    review["blocking_issues"] = ["sign convention mismatch in reviewed symbolic ledger"]
    write_json(stage / ".loop" / "review_result.json", review)

    result = settle_review_debt(tmp_path, stage.name)

    assert result["status"] == "BLOCKING"
    blocked = downstream_blocked_by_review_debt(tmp_path, "sigma_abc_012c_loop_orbit_canonicalization_promotion")
    assert blocked["blocked"] is True


def test_multistage_run_report_identity_uses_last_attempted_stage(tmp_path: Path):
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "scripts"))
    from run_autonomous_loop import StageRun, write_run_report

    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "autonomy": {
            "allow_physics_simplification": False,
            "allow_kernel_fusion": False,
            "allow_ibp_reduction": False,
            "stop_after_stage": "sigma_abc_012b_loop_hypothesis_generation",
        },
        "review": {"mode": "codex_subagent"},
    }
    loop = {"current_checkpoint": "sigma_abc_010_pair_kernel_fusion_pilot", "current_checkpoint_caveats": []}
    policy = {"policy": "sigma_abc_hard_stops", "caveats_to_preserve": []}
    benchmark = {"protected_benchmark": "sigma_xxx_projection"}
    records = [
        StageRun("sigma_abc_011_center_sector_pilot", status="PROVISIONAL_FREEZE_WITH_REVIEW_DEBT", validation_gate="PASS", review_verdict="FAILED", decision_action="PROVISIONAL_FREEZE_WITH_REVIEW_DEBT", checkpoint_created=True),
        StageRun("sigma_abc_012a_loop_sector_inventory", status="PROVISIONAL_FREEZE_WITH_REVIEW_DEBT", validation_gate="PASS", review_verdict="FAILED", decision_action="PROVISIONAL_FREEZE_WITH_REVIEW_DEBT", checkpoint_created=True),
        StageRun("sigma_abc_012b_loop_hypothesis_generation", status="PROVISIONAL_FREEZE_WITH_REVIEW_DEBT", validation_gate="PASS", review_verdict="FAILED", decision_action="PROVISIONAL_FREEZE_WITH_REVIEW_DEBT", checkpoint_created=True),
    ]

    report = write_run_report(tmp_path, "sigma_abc", "sigma_abc_hypothesis_pre_ibp_throughput", loop, profile, policy, benchmark, records)
    text = report.read_text()

    assert "ActualStage -> sigma_abc_012b_loop_hypothesis_generation" in text
    assert "ReportIdentityCheck -> PASS" in text
