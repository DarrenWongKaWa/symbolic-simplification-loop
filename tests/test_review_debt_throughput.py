from pathlib import Path

from loop_engine.config import read_json, write_json, write_text

DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


def make_stage(tmp_path: Path, name: str = "sigma_abc_011_center_sector_pilot", *, risk_level="LOW", lane="L1_COMPACT_META") -> Path:
    stage = tmp_path / name
    for folder in [".loop/reviewer_results", ".loop/review_queue", "reports", "output", "validation"]:
        (stage / folder).mkdir(parents=True, exist_ok=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n\nGroup center/contact rows by provenance only. Do not start IBP.\n")
    write_text(stage / "EXECUTION_REPORT.md", "# Execution Report\n\nCenterFusionDifference -> NOT_CLAIMED.\nNoTotalDerivativeIntroduced -> True.\n")
    write_text(stage / "CLAIM_BOUNDARY.md", f"# Claim Boundary\n\nDo not claim full tensorial sigma_abc correctness.\n{DC_CAVEAT}\n")
    validation = {
        "stage_name": name,
        "overall_gate": "PASS",
        "identity_type": "RowProvenanceHashConservation",
        "checks": [
            {"name": "NoIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "NoTotalDerivativeIntroduced", "expected": True, "actual": True, "gate": "PASS"},
        ],
        "CenterFusionDifference": "NOT_CLAIMED",
        "XXXCenterProjectionRegression": "INHERITED_OR_DEFERRED",
        "NoIBPStarted": True,
        "NoTotalDerivativeIntroduced": True,
        "NoFullTensorialClaim": True,
        "NoKernelFusionStarted": True,
        "NewSymbolicCandidatePromoted": False,
        "LoopOrbitCanonicalizationPromoted": False,
        "GlobalAssemblyStarted": False,
        "Stage001DCCaveatPreserved": True,
        "ProtectedBenchmarksUnchanged": True,
        "caveats": [DC_CAVEAT],
    }
    review = {
        "verdict": "FAILED",
        "stage_name": name,
        "reviewer_role": "ScientificMetaReviewer",
        "review_scope": lane,
        "mathematical_status": {"exact_reconstruction": True, "simplification_real": False, "regression_preserved": True, "overclaim_detected": False},
        "blocking_issues": ["AGENT_RUNTIME_QUOTA_EXHAUSTED: usage limit. RetryAfter -> 4:47 PM"],
        "nonblocking_caveats": [DC_CAVEAT],
        "allowed_claims": ["PASS as center-sector row-provenance conservation checkpoint."],
        "forbidden_claims": ["NOT PASS as center-sector fused physical kernel formula."],
        "next_action": "FAIL",
        "suggested_next_stage": None,
        "patch_instructions": [],
    }
    risk = {"risk_level": risk_level, "review_lane": lane, "reviewers": ["ScientificMetaReviewer"] if lane == "L1_COMPACT_META" else ["AlgebraReviewer", "PhysicsReviewer", "SoftwareReviewer", "ScientificMetaReviewer"], "full_panel_required": lane == "L2_FULL_PANEL"}
    metrics = {"stage_name": name, "before": {"rows": 93}, "after": {"families": 3}, "notes": []}
    write_json(stage / ".loop" / "validation_summary.json", validation)
    write_json(stage / ".loop" / "review_result.json", review)
    write_json(stage / ".loop" / "risk_classification.json", risk)
    write_json(stage / ".loop" / "metrics.json", metrics)
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
        "review_policy": {"lanes": {"L1_COMPACT_META": {"reviewers": ["ScientificMetaReviewer"]}, "L2_FULL_PANEL": {"reviewers": ["AlgebraReviewer", "PhysicsReviewer", "SoftwareReviewer", "ScientificMetaReviewer"]}}},
    }


def test_low_risk_l1_quota_can_create_review_debt(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed

    stage = make_stage(tmp_path)
    result = create_review_debt_if_allowed(stage, throughput_profile())

    assert result["stage_status"] == "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT"
    assert result["review_debt"] is True
    assert result["allowed_to_advance"] is True
    assert result["status"] == "OPEN"
    assert (stage / ".loop" / "review_debt.json").exists()
    assert (stage / ".loop" / "review_debt_ledger.jsonl").exists()


def test_high_risk_l2_quota_cannot_advance_with_review_debt(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed

    stage = make_stage(tmp_path, name="sigma_abc_012c_loop_orbit_canonicalization_promotion", risk_level="HIGH", lane="L2_FULL_PANEL")
    result = create_review_debt_if_allowed(stage, throughput_profile())

    assert result["stage_status"] == "REVIEW_DEBT_BLOCKED"
    assert result["allowed_to_advance"] is False


def test_review_debt_blocks_global_assembly(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed, downstream_blocked_by_review_debt

    stage = make_stage(tmp_path)
    create_review_debt_if_allowed(stage, throughput_profile())

    blocked = downstream_blocked_by_review_debt(tmp_path, "sigma_abc_013_global_pre_ibp_assembly")
    assert blocked["blocked"] is True
    assert "global_pre_ibp_assembly" in blocked["reason"]


def test_review_debt_blocks_candidate_promotion(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed, downstream_blocked_by_review_debt

    stage = make_stage(tmp_path)
    create_review_debt_if_allowed(stage, throughput_profile())

    blocked = downstream_blocked_by_review_debt(tmp_path, "sigma_abc_012c_loop_orbit_canonicalization_promotion")
    assert blocked["blocked"] is True
    assert "candidate_promotion" in blocked["reason"]


def test_review_debt_allows_candidate_preparation_readiness_gate(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed, downstream_blocked_by_review_debt

    stage = make_stage(tmp_path)
    create_review_debt_if_allowed(stage, throughput_profile())

    blocked = downstream_blocked_by_review_debt(tmp_path, "sigma_abc_012c_real_loop_candidate_preparation")
    assert blocked["blocked"] is False
    assert "may run" in blocked["reason"]


def test_review_debt_allows_exploration_only_stage(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed, downstream_blocked_by_review_debt

    stage = make_stage(tmp_path)
    create_review_debt_if_allowed(stage, throughput_profile())

    blocked = downstream_blocked_by_review_debt(tmp_path, "sigma_abc_012b_loop_hypothesis_generation")
    assert blocked["blocked"] is False


def test_settle_review_debt_promotes_provisional_checkpoint(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed, settle_review_debt

    stage = make_stage(tmp_path)
    create_review_debt_if_allowed(stage, throughput_profile())
    write_json(stage / ".loop" / "review_result.json", {**read_json(stage / ".loop" / "review_result.json"), "verdict": "PASS_WITH_CAVEAT", "blocking_issues": [], "nonblocking_caveats": [DC_CAVEAT]})

    result = settle_review_debt(tmp_path, stage.name)

    assert result["status"] == "SETTLED"
    assert read_json(stage / ".loop" / "review_debt.json")["status"] == "SETTLED"
    assert read_json(stage / ".loop" / "decision.json")["action"] == "REVIEW_DEBT_SETTLED"


def test_failed_review_debt_marks_downstream_dependency_invalid(tmp_path: Path):
    from loop_engine.review_debt import create_review_debt_if_allowed, settle_review_debt

    stage = make_stage(tmp_path)
    create_review_debt_if_allowed(stage, throughput_profile())
    write_json(stage / ".loop" / "review_result.json", {**read_json(stage / ".loop" / "review_result.json"), "verdict": "FAILED", "blocking_issues": ["sign convention mismatch"]})

    result = settle_review_debt(tmp_path, stage.name)

    assert result["status"] == "BLOCKING"
    assert read_json(stage / ".loop" / "decision.json")["action"] == "REVIEW_INVALIDATED_DEPENDENCY"


def test_stage012_split_risk_lanes(tmp_path: Path):
    from loop_engine.risk_classifier import classify_stage_risk

    profile = throughput_profile()
    s12a = make_stage(tmp_path, name="sigma_abc_012a_loop_sector_inventory")
    write_text(s12a / "STAGE_PLAN.md", "# Stage Plan\n\nLoop-sector inventory and row provenance only. No orbit canonicalization promotion.\n")
    risk12a = classify_stage_risk(s12a, profile)
    assert risk12a["review_lane"] in {"L0_DETERMINISTIC", "L1_COMPACT_META"}

    s12b = make_stage(tmp_path, name="sigma_abc_012b_loop_hypothesis_generation")
    write_text(s12b / "STAGE_PLAN.md", "# Stage Plan\n\nConjecture generation only. VERIFIED_BUT_NOT_PROMOTED. No candidate promoted.\n")
    validation = read_json(s12b / ".loop" / "validation_summary.json")
    validation["HypothesisExplorationOnly"] = True
    validation["VerifiedCandidatePromoted"] = False
    validation["CandidateValidationStatus"] = "VERIFIED_BUT_NOT_PROMOTED"
    write_json(s12b / ".loop" / "validation_summary.json", validation)
    risk12b = classify_stage_risk(s12b, profile)
    assert risk12b["review_lane"] == "L1_COMPACT_META"

    s12c = make_stage(tmp_path, name="sigma_abc_012c_loop_orbit_canonicalization_promotion")
    write_text(s12c / "STAGE_PLAN.md", "# Stage Plan\n\nLoop orbit canonicalization candidate promotion.\n")
    validation = read_json(s12c / ".loop" / "validation_summary.json")
    validation["NewSymbolicCandidatePromoted"] = True
    write_json(s12c / ".loop" / "validation_summary.json", validation)
    risk12c = classify_stage_risk(s12c, profile)
    assert risk12c["review_lane"] == "L2_FULL_PANEL"
