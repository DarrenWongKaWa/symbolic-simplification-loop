from __future__ import annotations

import json
from pathlib import Path

from loop_engine.config import read_json, write_json, write_text
from loop_engine.decision import decide_next_action


def make_stage(tmp_path: Path, *, stage_name: str = "stage_011_center") -> Path:
    stage = tmp_path / stage_name
    (stage / ".loop").mkdir(parents=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n\nGroup center/contact rows by provenance only.\n")
    write_text(stage / "EXECUTION_REPORT.md", "# Execution Report\n\nNo formula fusion was claimed.\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\nNo IBP. No full tensorial correctness claim.\n")
    validation = {
        "stage_name": stage_name,
        "overall_gate": "PASS",
        "identity_type": "RowProvenanceHashConservation",
        "checks": [
            {"name": "CenterProvenanceDifference", "expected": 0, "actual": 0, "gate": "PASS"},
            {"name": "NoIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
        ],
        "CenterFusionDifference": "NOT_CLAIMED",
        "NoTotalDerivativeIntroduced": True,
    }
    metrics = {
        "stage_name": stage_name,
        "before": {"rows": 93},
        "after": {"families": 3},
        "notes": ["Small provenance grouping stage."],
    }
    write_json(stage / ".loop" / "validation_summary.json", validation)
    write_json(stage / ".loop" / "metrics.json", metrics)
    write_text(stage / "review_packet.md", "# Full Review Packet\n\n" + ("large-output\n" * 2000))
    return stage


def tiered_profile() -> dict:
    return {
        "review_policy": {
            "mode": "tiered",
            "allow_l0_freeze_for_low_risk_provenance": True,
            "require_l1_for_claim_boundary": True,
            "require_l2_for_kernel_fusion": True,
            "require_l2_for_candidate_promotion": True,
            "require_l2_for_global_assembly": True,
            "lanes": {
                "L0_DETERMINISTIC": {"requires_llm_agents": False},
                "L1_COMPACT_META": {"reviewers": ["ScientificMetaReviewer"], "max_input_tokens": 2500},
                "L2_FULL_PANEL": {
                    "reviewers": [
                        "AlgebraReviewer",
                        "PhysicsReviewer",
                        "SoftwareReviewer",
                        "ScientificMetaReviewer",
                    ]
                },
            },
        }
    }


def test_low_risk_provenance_stage_uses_l1_not_full_panel(tmp_path: Path):
    from loop_engine.risk_classifier import classify_stage_risk

    stage = make_stage(tmp_path)
    result = classify_stage_risk(stage, tiered_profile())

    assert result["risk_level"] in {"LOW", "MEDIUM"}
    assert result["review_lane"] == "L1_COMPACT_META"
    assert result["full_panel_required"] is False
    assert result["llm_review_required"] is True
    assert "row provenance" in " ".join(result["reasons"]).lower()
    assert (stage / ".loop" / "risk_classification.json").exists()


def test_kernel_fusion_requires_l2_full_panel(tmp_path: Path):
    from loop_engine.risk_classifier import classify_stage_risk

    stage = make_stage(tmp_path, stage_name="sigma_abc_010_pair_kernel_fusion_pilot")
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n\nPerform kernel fusion pilot.\n")
    result = classify_stage_risk(stage, tiered_profile())

    assert result["risk_level"] == "HIGH"
    assert result["review_lane"] == "L2_FULL_PANEL"
    assert result["full_panel_required"] is True


def test_candidate_promotion_requires_l2_full_panel(tmp_path: Path):
    from loop_engine.risk_classifier import classify_stage_risk

    stage = make_stage(tmp_path)
    validation = read_json(stage / ".loop" / "validation_summary.json")
    validation["NewSymbolicCandidatePromoted"] = True
    write_json(stage / ".loop" / "validation_summary.json", validation)
    result = classify_stage_risk(stage, tiered_profile())

    assert result["review_lane"] == "L2_FULL_PANEL"
    assert result["new_symbolic_candidate_promoted"] is True


def test_compact_review_packet_excludes_large_outputs(tmp_path: Path):
    from loop_engine.compact_packet import build_compact_review_packet

    stage = make_stage(tmp_path)
    write_text(stage / "output" / "huge_table.wl", "x\n" * 10000)
    packet_path = build_compact_review_packet(stage, tiered_profile())
    text = packet_path.read_text(encoding="utf-8")

    assert packet_path.name == "review_minipacket.md"
    assert "large-output" not in text
    assert "huge_table.wl" in text
    assert "CenterProvenanceDifference" in text
    assert len(text.split()) < 2500


def test_quota_limit_creates_validated_pending_review_not_patch(tmp_path: Path):
    validation = {"overall_gate": "PASS"}
    review = {
        "verdict": "FAILED",
        "next_action": "FAIL",
        "blocking_issues": [
            "AGENT_RUNTIME_QUOTA_EXHAUSTED: usage limit. RetryAfter -> 6:27 AM"
        ],
    }
    decision = decide_next_action(validation, review)

    assert decision.action == "VALIDATED_PENDING_REVIEW"
    assert decision.freeze_allowed is False
    assert decision.patch_required is False
    assert decision.retry_after == "6:27 AM"


def test_review_queue_records_pending_review_and_input_hashes(tmp_path: Path):
    from loop_engine.review_queue import enqueue_pending_review, validation_inputs_unchanged

    stage = make_stage(tmp_path)
    risk = {"review_lane": "L1_COMPACT_META", "reviewers": ["ScientificMetaReviewer"]}
    queue_path = enqueue_pending_review(stage, "quota limit", risk, retry_after="6:27 AM")

    assert queue_path.exists()
    data = [json.loads(line) for line in queue_path.read_text(encoding="utf-8").splitlines()]
    assert data[-1]["stage_status"] == "VALIDATED_PENDING_REVIEW"
    assert data[-1]["executor_rerun_required"] is False
    assert data[-1]["reviewer_resume_required"] is True
    assert validation_inputs_unchanged(stage, data[-1]) is True

    write_text(stage / ".loop" / "validation_summary.json", '{"overall_gate":"PASS","changed":true}\n')
    assert validation_inputs_unchanged(stage, data[-1]) is False


def test_resume_pending_review_does_not_rerun_executor(tmp_path: Path):
    from loop_engine.review_queue import enqueue_pending_review, resume_pending_reviews

    stage = make_stage(tmp_path)
    marker = stage / "EXECUTION_REPORT.md"
    before = marker.read_text(encoding="utf-8")
    risk = {"review_lane": "L0_DETERMINISTIC", "reviewers": []}
    enqueue_pending_review(stage, "deterministic resume test", risk)

    result = resume_pending_reviews(tmp_path, allow_l0_freeze=True)

    assert result["resumed"] == 1
    assert result["executor_rerun_required"] is False
    assert marker.read_text(encoding="utf-8") == before
    assert (stage / ".loop" / "review_result.json").exists()
    decision = read_json(stage / ".loop" / "decision.json")
    assert decision["action"] in {"FREEZE", "FREEZE_WITH_CAVEAT"}


def test_l0_freeze_allowed_only_for_profile_allowed_low_risk(tmp_path: Path):
    from loop_engine.risk_classifier import classify_stage_risk

    stage = make_stage(tmp_path)
    profile = tiered_profile()
    profile["review_policy"]["require_l1_for_claim_boundary"] = False
    result = classify_stage_risk(stage, profile)
    assert result["review_lane"] == "L0_DETERMINISTIC"
    assert result["llm_review_required"] is False

    profile["review_policy"]["allow_l0_freeze_for_low_risk_provenance"] = False
    result = classify_stage_risk(stage, profile)
    assert result["review_lane"] == "L1_COMPACT_META"
