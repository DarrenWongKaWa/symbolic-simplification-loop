from __future__ import annotations

import json
from pathlib import Path

from loop_engine.checkpoint import build_checkpoint_manifest
from loop_engine.config import read_json, write_json, write_text


DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


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


def make_stage(tmp_path: Path, *, name: str = "sigma_abc_011_center_sector_pilot") -> Path:
    stage = tmp_path / name
    for folder in [".loop/reviewer_results", "reports", "output", "validation"]:
        (stage / folder).mkdir(parents=True, exist_ok=True)
    write_text(
        stage / "STAGE_PLAN.md",
        f"# Stage Plan\n\n{name}\n\nGroup rows by provenance. Do not start IBP.\n",
    )
    write_text(
        stage / "EXECUTION_REPORT.md",
        "# Execution Report\n\nCenterFusionDifference -> NOT_CLAIMED.\nNoTotalDerivativeIntroduced -> True.\n",
    )
    write_text(
        stage / "CLAIM_BOUNDARY.md",
        f"# Claim Boundary\n\nDo not claim full tensorial sigma_abc correctness.\n{DC_CAVEAT}\n",
    )
    validation = {
        "stage_name": name,
        "overall_gate": "PASS",
        "identity_type": "RowProvenanceHashConservation",
        "checks": [
            {"name": "CenterProvenanceDifference", "expected": 0, "actual": 0, "gate": "PASS"},
            {"name": "NoIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "NoTotalDerivativeIntroduced", "expected": True, "actual": True, "gate": "PASS"},
        ],
        "CenterFusionDifference": "NOT_CLAIMED",
        "XXXCenterProjectionRegression": "INHERITED_OR_DEFERRED",
        "NoIBPStarted": True,
        "NoTotalDerivativeIntroduced": True,
        "caveats": [DC_CAVEAT],
    }
    review = {
        "verdict": "PASS_WITH_CAVEAT",
        "stage_name": name,
        "reviewer_role": "IntegratorReview",
        "review_scope": "L1_COMPACT_META",
        "mathematical_status": {
            "exact_reconstruction": True,
            "simplification_real": False,
            "regression_preserved": True,
            "overclaim_detected": False,
        },
        "blocking_issues": [],
        "nonblocking_caveats": [DC_CAVEAT],
        "allowed_claims": ["PASS as center-sector row-provenance conservation checkpoint."],
        "forbidden_claims": [
            "NOT PASS as center-sector fused physical kernel formula.",
            "Do not claim full tensorial sigma_abc correctness.",
        ],
        "next_action": "FREEZE",
        "suggested_next_stage": "sigma_abc_012_loop_orbit_canonicalization_pilot",
        "patch_instructions": [],
    }
    metrics = {"stage_name": name, "before": {"rows": 93}, "after": {"families": 3}, "notes": []}
    write_json(stage / ".loop" / "validation_summary.json", validation)
    write_json(stage / ".loop" / "review_result.json", review)
    write_json(stage / ".loop" / "metrics.json", metrics)
    write_text(stage / "review_packet.md", "# Review Packet\n\n" + json.dumps(validation, indent=2) + "\n")
    write_text(stage / "output" / "small_result.wl", "<|\"CenterFusionDifference\" -> \"NOT_CLAIMED\"|>\n")
    write_text(stage / "output" / "giant_ledger.wl", "giant_symbolic_row\n" * 6000)
    return stage


def test_meta_review_requires_pass_as_and_not_pass_as(tmp_path: Path):
    from loop_engine.review_quality import build_review_quality

    stage = make_stage(tmp_path)
    quality = build_review_quality(stage, next_safe_stage="sigma_abc_012_loop_orbit_canonicalization_pilot")

    assert quality["pass_as"] == "center-sector row-provenance conservation checkpoint"
    assert "center-sector fused physical kernel formula" in quality["not_pass_as"]
    assert "full tensorial sigma_abc correctness" in quality["not_pass_as"]
    assert quality["freeze_allowed_by_review_quality"] is True
    assert (stage / ".loop" / "review_quality.json").exists()
    assert (stage / "reports" / "stage_011_center_sector_pilot_review_quality.md").exists()


def test_meta_review_preserves_dc_caveat(tmp_path: Path):
    from loop_engine.review_quality import build_review_quality

    quality = build_review_quality(make_stage(tmp_path))

    assert any("DCProjectionTo1D -> INHERITED_PASS" in caveat for caveat in quality["caveats_preserved"])
    assert quality["overclaim_detected"] is False


def test_meta_review_blocks_full_tensorial_overclaim(tmp_path: Path):
    from loop_engine.review_quality import build_review_quality

    stage = make_stage(tmp_path)
    write_text(stage / "EXECUTION_REPORT.md", "# Execution Report\n\nWe prove full tensorial sigma_abc correctness.\n")
    quality = build_review_quality(stage)

    assert quality["overclaim_detected"] is True
    assert quality["freeze_allowed_by_review_quality"] is False


def test_stage011_low_risk_uses_l1_compact_meta(tmp_path: Path):
    from loop_engine.risk_classifier import classify_stage_risk

    risk = classify_stage_risk(make_stage(tmp_path), tiered_profile())

    assert risk["risk_level"] == "LOW"
    assert risk["review_lane"] == "L1_COMPACT_META"
    assert risk["full_panel_required"] is False


def test_stage012_kernel_or_loop_candidate_uses_l2_full_panel(tmp_path: Path):
    from loop_engine.risk_classifier import classify_stage_risk

    stage = make_stage(tmp_path, name="sigma_abc_012_loop_orbit_canonicalization_pilot")
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n\nLoop orbit canonicalization pilot with candidate promotion.\n")
    validation = read_json(stage / ".loop" / "validation_summary.json")
    validation["NewSymbolicCandidatePromoted"] = True
    write_json(stage / ".loop" / "validation_summary.json", validation)

    risk = classify_stage_risk(stage, tiered_profile())

    assert risk["risk_level"] == "HIGH"
    assert risk["review_lane"] == "L2_FULL_PANEL"
    assert risk["full_panel_required"] is True


def test_stage012_loop_three_band_orbit_text_uses_l2_full_panel(tmp_path: Path):
    from loop_engine.risk_classifier import classify_stage_risk

    stage = make_stage(tmp_path, name="sigma_abc_012_loop_orbit_canonicalization_pilot")
    write_text(
        stage / "STAGE_PLAN.md",
        "# Stage Plan\n\nLoop/three-band orbit-canonicalization pilot before tensorial IBP.\n",
    )

    risk = classify_stage_risk(stage, tiered_profile())

    assert risk["risk_level"] == "HIGH"
    assert risk["review_lane"] == "L2_FULL_PANEL"
    assert risk["full_panel_required"] is True


def test_stage013_global_pre_ibp_assembly_uses_l2_full_panel(tmp_path: Path):
    from loop_engine.risk_classifier import classify_stage_risk

    stage = make_stage(tmp_path, name="sigma_abc_013_global_pre_ibp_assembly")
    write_text(
        stage / "STAGE_PLAN.md",
        "# Stage Plan\n\nAssemble center, pair, and loop pre-IBP ledgers without total-derivative reduction.\n",
    )

    risk = classify_stage_risk(stage, tiered_profile())

    assert risk["risk_level"] == "HIGH"
    assert risk["review_lane"] == "L2_FULL_PANEL"
    assert risk["full_panel_required"] is True


def test_compact_packet_contains_claim_boundary_and_excludes_large_outputs(tmp_path: Path):
    from loop_engine.compact_packet import build_compact_review_packet
    from loop_engine.risk_classifier import classify_stage_risk

    stage = make_stage(tmp_path)
    classify_stage_risk(stage, tiered_profile())
    packet = build_compact_review_packet(stage, tiered_profile())
    text = packet.read_text(encoding="utf-8")

    assert "stage id" in text.lower()
    assert "stage slug" in text.lower()
    assert "claimed output" in text.lower()
    assert "not-claimed output" in text.lower()
    assert "forbidden actions status" in text.lower()
    assert "protected benchmark status" in text.lower()
    assert "Do not claim full tensorial sigma_abc correctness" in text
    assert "giant_symbolic_row" not in text


def test_review_quality_included_in_checkpoint_manifest(tmp_path: Path):
    from loop_engine.review_quality import build_review_quality
    from loop_engine.schemas import validate_with_schema

    stage = make_stage(tmp_path)
    quality = build_review_quality(stage)
    validate_with_schema(quality, "review_quality")
    manifest = build_checkpoint_manifest(stage)

    assert "review_quality" in manifest
    assert manifest["review_quality"]["pass_as"] == quality["pass_as"]
    assert "reports/stage_011_center_sector_pilot_review_quality.md" in {item["path"] for item in manifest["files"]}


def test_resume_pending_review_runs_reviewer_only_and_preserves_executor(tmp_path: Path):
    from loop_engine.review_queue import enqueue_pending_review, resume_pending_reviews
    from loop_engine.risk_classifier import classify_stage_risk

    stage = make_stage(tmp_path)
    risk = classify_stage_risk(stage, tiered_profile())
    before = (stage / "EXECUTION_REPORT.md").read_text(encoding="utf-8")
    enqueue_pending_review(stage, "test pending compact meta review", risk)

    result = resume_pending_reviews(tmp_path)

    assert result["resumed"] == 1
    assert result["executor_rerun_required"] is False
    assert (stage / "EXECUTION_REPORT.md").read_text(encoding="utf-8") == before
    assert (stage / ".loop" / "review_quality.json").exists()
    assert (stage / ".loop" / "decision.json").exists()
    assert read_json(stage / ".loop" / "decision.json")["action"] in {"FREEZE", "FREEZE_WITH_CAVEAT"}


def test_resume_pending_review_does_not_rerun_executor_if_hashes_unchanged(tmp_path: Path):
    from loop_engine.review_queue import enqueue_pending_review, resume_pending_reviews
    from loop_engine.risk_classifier import classify_stage_risk

    stage = make_stage(tmp_path)
    risk = classify_stage_risk(stage, tiered_profile())
    enqueue_pending_review(stage, "test pending compact meta review", risk)
    result = resume_pending_reviews(tmp_path)

    assert result["needs_revalidation"] == 0
    assert result["executor_rerun_required"] is False
