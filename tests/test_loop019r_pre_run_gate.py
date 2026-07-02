"""Loop 019R — pre-run brief positive-vs-boundary intent matcher tests.

These tests pin the behavior (not implementation) of the gate audit:

- Positive forbidden intent hard-stops the brief.
- Boundary acknowledgement ("no candidate promotion",
  "candidate promotion forbidden") is logged as a WARN but does NOT
  hard-stop the brief. Positive execution intent ("candidate
  promotion before tensorial IBP", "promote the candidate now") still
  hard-stops.
- The gate never invokes a reviewer.
- WARN/PASS/FAIL semantics and the DC caveat warning stay intact.

These tests are deliberately built around TWO different fixtures:

  _profile_neutral()        -> omits "candidate promotion" from forbidden_actions
                              (tests boundary acknowledgement in isolation).
  _profile_forbid_promote()-> includes "candidate promotion" in forbidden_actions
                              (tests that negative boundary text remains safe).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loop_engine.config import write_text
from loop_engine.pre_run_brief import audit_pre_run_brief, build_pre_run_brief
from loop_engine.pre_run_gate import check_pre_run_gate
from loop_engine.schemas import validate_with_schema


REPO_ROOT = Path(__file__).resolve().parents[1]


DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


def _profile_neutral() -> dict:
    """Profile that does NOT list 'candidate promotion' in forbidden_actions.

    Tests using this fixture verify that ordinary boundary
    acknowledgement ('no candidate promotion') is not hard-stopped.
    """
    return {
        "profile": "loop_019r_test_profile_neutral",
        "allowed_stage_ids": [],
        "autonomy": {
            "allow_physics_simplification": False,
            "allow_kernel_fusion": False,
            "allow_ibp_reduction": False,
        },
        "permanent_caveats": [DC_CAVEAT],
        "forbidden_actions": [
            "global assembly",
            "IBP",
            "total derivative reduction",
            "full tensorial sigma_abc correctness claim",
        ],
    }


def _profile_forbid_promote() -> dict:
    """Profile that DOES list 'candidate promotion' in forbidden_actions.

    Tests using this fixture verify that negative boundary text is still
    safe even if the profile lists the forbidden token, while positive
    intent remains blocked by the classifier.
    """
    profile = _profile_neutral()
    profile["profile"] = "loop_019r_test_profile_forbid_promote"
    profile["forbidden_actions"] = list(profile["forbidden_actions"]) + ["candidate promotion"]
    return profile


def _write_minimal_stage(
    tmp_path: Path,
    stage_id: str,
    *,
    goal_text: str,
    include_dc_caveat: bool = True,
) -> Path:
    stage = tmp_path / stage_id
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(
        stage / "STAGE_PLAN.md",
        f"""# Stage Plan

## Stage

`{stage_id}`

## Goal

{goal_text}

## Expected Outputs

- output/
""",
    )
    caveat_block = DC_CAVEAT if include_dc_caveat else "no caveat in this fixture"
    write_text(stage / "CLAIM_BOUNDARY.md", f"# Claim Boundary\n\n{caveat_block}\n")
    return stage


# ============================================================================
# Group A: boundary acknowledgement under a NEUTRAL profile
#   These tests pin that "no candidate promotion" / "candidate promotion forbidden"
#   are boundary acknowledgement, NOT positive execution intent.
# ============================================================================


def test_audit_passes_when_goal_says_no_candidate_promotion(tmp_path: Path) -> None:
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_012a_neutral_no_promote",
        goal_text="Prepare artifacts; no candidate promotion.",
    )
    profile = _profile_neutral()
    brief = build_pre_run_brief(stage, profile=profile)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is False, f"audit={audit}"
    assert "candidate promotion" not in audit["blocking_reasons"]
    assert audit["gate"] in {"PASS", "WARN"}


def test_audit_passes_when_goal_says_candidate_promotion_forbidden(tmp_path: Path) -> None:
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_012a_neutral_forbidden_text",
        goal_text="Build loop hypothesis; candidate promotion forbidden.",
    )
    profile = _profile_neutral()
    brief = build_pre_run_brief(stage, profile=profile)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is False, f"audit={audit}"


def test_audit_passes_when_goal_says_do_not_promote_candidate(tmp_path: Path) -> None:
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_012a_neutral_do_not_promote",
        goal_text="Inventory loop sectors; do not promote the candidate.",
    )
    profile = _profile_neutral()
    brief = build_pre_run_brief(stage, profile=profile)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is False, f"audit={audit}"


def test_boundary_acknowledgement_recorded_as_warning_not_block(tmp_path: Path) -> None:
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_012a_ack",
        goal_text="Prepare artifacts; no candidate promotion; no IBP.",
    )
    profile = _profile_neutral()
    brief = build_pre_run_brief(stage, profile=profile)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is False
    assert audit["blocking_reasons"] == []
    assert any("boundary acknowledged" in w for w in audit["warnings"]), audit


# ============================================================================
# Group B: positive intent (regardless of profile neutrality) MUST hard-stop
# ============================================================================


def test_audit_hard_stops_when_goal_says_i_will_promote_candidate(tmp_path: Path) -> None:
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_012a_positive_intent",
        goal_text="I will promote the candidate now.",
    )
    profile = _profile_neutral()
    brief = build_pre_run_brief(stage, profile=profile)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is True
    assert any("promote" in r for r in audit["blocking_reasons"])


def test_audit_hard_stops_when_allowed_actions_include_promote_candidate(tmp_path: Path) -> None:
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_012a_actions_intent",
        goal_text="Inventory loop sectors without promotion.",
    )
    profile = _profile_neutral()
    brief = build_pre_run_brief(stage, profile=profile)
    brief["task_understanding"]["allowed_actions"] = [
        "promote the loop candidate now",
        "preserved boundary",
    ]
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is True
    assert any("promote" in r for r in audit["blocking_reasons"])


def test_audit_hard_stops_when_goal_says_start_ibp(tmp_path: Path) -> None:
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_012a_ibp_positive",
        goal_text="I will start IBP now.",
    )
    profile = _profile_neutral()
    brief = build_pre_run_brief(stage, profile=profile)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is True
    assert any("ibp" in r for r in audit["blocking_reasons"])


def test_audit_hard_stops_when_goal_says_introduce_total_derivative(tmp_path: Path) -> None:
    """Bare 'Introduce total derivative reduction' is positive intent and hard-stops."""
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_012a_td_positive",
        goal_text="Introduce total derivative reduction.",
    )
    profile = _profile_neutral()
    brief = build_pre_run_brief(stage, profile=profile)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is True
    assert any("total derivative" in r or "total-derivative" in r for r in audit["blocking_reasons"])


# ============================================================================
# Group C: preparation-only profile boundary handling
#   Negative boundary acknowledgement remains safe even when the profile
#   lists candidate promotion as a forbidden action. Positive promotion
#   intent still hard-stops.
# ============================================================================


def test_audit_allows_negative_candidate_promotion_boundary_even_when_profile_forbids_token(tmp_path: Path) -> None:
    """Negative 012C-prep wording is boundary acknowledgement, not promotion."""
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_012c_real_loop_candidate_preparation",
        goal_text="Prepare real sigma_abc loop-orbit candidate artifacts for a "
        "future 012C promotion retry; no candidate promotion.",
    )
    profile = _profile_forbid_promote()
    brief = build_pre_run_brief(stage, profile=profile)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is False, audit
    assert audit["blocking_reasons"] == []
    assert any("boundary acknowledged" in w for w in audit["warnings"]), audit


def test_audit_still_blocks_positive_candidate_promotion_when_profile_forbids_token(tmp_path: Path) -> None:
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_012c_loop_orbit_canonicalization_promotion",
        goal_text="Loop candidate promotion before tensorial IBP.",
    )
    profile = _profile_forbid_promote()
    brief = build_pre_run_brief(stage, profile=profile)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is True
    assert any("candidate promotion" in r for r in audit["blocking_reasons"]), audit


def test_audit_passes_when_profile_neutral_and_goal_mentions_promotion(tmp_path: Path) -> None:
    """The same negative wording passes under a neutral profile.

    This documents the difference between the two profile regimes
    and prevents regression to the old substring-match-only behavior.
    """
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_throughput_like",
        goal_text="Prepare real sigma_abc loop-orbit candidate artifacts for a "
        "future 012C promotion retry; no candidate promotion.",
    )
    profile = _profile_neutral()
    brief = build_pre_run_brief(stage, profile=profile)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is False


# ============================================================================
# Group D: WARN-only checks (DC caveat, expected outputs, missing brief)
# ============================================================================


def test_audit_warns_when_expected_outputs_empty(tmp_path: Path) -> None:
    """A stage with no expected_outputs section yields WARN, not hard-stop."""
    stage = tmp_path / "sigma_abc_012a_no_outputs"
    (stage / ".loop").mkdir(parents=True)
    (stage / "reports").mkdir(parents=True)
    write_text(
        stage / "STAGE_PLAN.md",
        "# Stage Plan\n\n## Goal\n\nBuild artifacts; no candidate promotion.\n",
    )
    write_text(stage / "CLAIM_BOUNDARY.md", f"# Claim Boundary\n\n{DC_CAVEAT}\n")
    profile = _profile_neutral()
    brief = build_pre_run_brief(stage, profile=profile)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    assert audit["hard_stop"] is False
    assert any("expected outputs" in w for w in audit["warnings"]), audit


def test_audit_hard_stops_unchanged_for_truly_missing_brief(tmp_path: Path) -> None:
    """boundary: if no brief at all, gate must FAIL (not PASS)."""
    stage = tmp_path / "sigma_abc_012a_no_brief"
    (stage / ".loop").mkdir(parents=True)
    audit = audit_pre_run_brief(stage, None, profile=_profile_neutral())
    assert audit["gate"] == "FAIL"
    assert "pre_run_brief missing" in audit["blocking_reasons"]


# ============================================================================
# Group E: pre_run_gate must remain deterministic + reviewer-free
# ============================================================================


def test_audit_does_not_call_reviewer(tmp_path: Path) -> None:
    stage = _write_minimal_stage(
        tmp_path,
        "sigma_abc_012a_no_reviewer",
        goal_text="I will promote the candidate now.",
    )
    gate = check_pre_run_gate(stage, profile=_profile_neutral())
    assert gate["reviewer_consulted"] is False
    validate_with_schema(gate, "pre_run_gate_result")
