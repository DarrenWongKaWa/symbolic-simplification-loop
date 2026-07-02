from __future__ import annotations

from loop_engine.decision import decide_next_action
from loop_engine.state import StageStatus, can_transition


BASE_VALIDATION = {"overall_gate": "PASS"}


def review(verdict: str, next_action: str = "FREEZE") -> dict:
    return {
        "verdict": verdict,
        "next_action": next_action,
        "nonblocking_caveats": ["caveat"] if verdict == "PASS_WITH_CAVEAT" else [],
        "suggested_next_stage": "010_sector_decomposition" if next_action == "OPEN_NEXT_STAGE" else None,
    }


def test_validation_failure_blocks_freeze():
    decision = decide_next_action({"overall_gate": "FAIL"}, review("PASS"))
    assert decision.action == "DO_NOT_FREEZE"
    assert not decision.freeze_allowed


def test_meta_review_failure_blocks_freeze_even_when_review_passes():
    decision = decide_next_action(
        BASE_VALIDATION,
        review("PASS"),
        meta_review={"verdict": "NEEDS_PATCH", "caveats_to_preserve": ["meta caveat"]},
    )
    assert decision.action == "DO_NOT_FREEZE"
    assert not decision.freeze_allowed


def test_pass_freezes():
    decision = decide_next_action(BASE_VALIDATION, review("PASS"))
    assert decision.action == "FREEZE"
    assert decision.freeze_allowed


def test_pass_with_caveat_freezes_with_caveat():
    decision = decide_next_action(BASE_VALIDATION, review("PASS_WITH_CAVEAT"))
    assert decision.action == "FREEZE_WITH_CAVEAT"
    assert decision.caveats == ["caveat"]


def test_needs_patch_generates_patch_action():
    decision = decide_next_action(BASE_VALIDATION, review("NEEDS_PATCH", "PATCH"))
    assert decision.action == "PATCH"
    assert not decision.freeze_allowed


def test_runtime_quota_exhaustion_returns_validated_pending_review_without_patch():
    review_result = review("NEEDS_PATCH", "PATCH")
    review_result["blocking_issues"] = [
        "AGENT_RUNTIME_QUOTA_EXHAUSTED: Codex usage limit reached. RetryAfter -> Jun 30th, 2026 1:01 AM"
    ]

    decision = decide_next_action(BASE_VALIDATION, review_result)

    assert decision.action == "VALIDATED_PENDING_REVIEW"
    assert not decision.freeze_allowed
    assert decision.patch_required is False
    assert decision.retry_after == "Jun 30th, 2026 1:01 AM"


def test_runtime_quota_exhaustion_overrides_meta_review_patch_blocker_as_pending_review():
    review_result = review("FAILED", "FAIL")
    review_result["blocking_issues"] = [
        "AGENT_RUNTIME_QUOTA_EXHAUSTED: agent runtime quota or usage limit blocked invocation. RetryAfter -> 6:27 AM"
    ]

    decision = decide_next_action(
        BASE_VALIDATION,
        review_result,
        meta_review={"verdict": "NEEDS_PATCH", "blocking_issues": ["review evidence missing"]},
    )

    assert decision.action == "VALIDATED_PENDING_REVIEW"
    assert not decision.freeze_allowed
    assert decision.patch_required is False
    assert decision.retry_after == "6:27 AM"


def test_open_next_stage_freezes_first():
    decision = decide_next_action(BASE_VALIDATION, review("PASS", "OPEN_NEXT_STAGE"))
    assert decision.action == "FREEZE_THEN_OPEN_NEXT_STAGE"
    assert decision.freeze_allowed
    assert decision.suggested_next_stage == "010_sector_decomposition"


def test_state_transition_matrix():
    assert can_transition(StageStatus.DRAFT_PLAN, StageStatus.READY_TO_EXECUTE)
    assert not can_transition(StageStatus.DRAFT_PLAN, StageStatus.FROZEN)
