from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import read_json, read_text, write_json


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _positive_operation_mentioned(text: str, positive: list[str], negated: list[str]) -> bool:
    lowered = text.lower()
    if not any(item.lower() in lowered for item in positive):
        return False
    return not any(item.lower() in lowered for item in negated)


def _reviewers_for_lane(policy: dict[str, Any], lane: str) -> list[str]:
    lanes = policy.get("lanes", {}) or {}
    configured = lanes.get(lane, {}) or {}
    reviewers = configured.get("reviewers")
    if reviewers is not None:
        return list(reviewers)
    if lane == "L2_FULL_PANEL":
        return ["AlgebraReviewer", "PhysicsReviewer", "SoftwareReviewer", "ScientificMetaReviewer"]
    if lane == "L1_COMPACT_META":
        return ["ScientificMetaReviewer"]
    return []


def classify_stage_risk(stage: Path, profile: dict[str, Any]) -> dict[str, Any]:
    validation = read_json(stage / ".loop" / "validation_summary.json") if (stage / ".loop" / "validation_summary.json").exists() else {}
    metrics = read_json(stage / ".loop" / "metrics.json") if (stage / ".loop" / "metrics.json").exists() else {}
    text = "\n".join(
        [
            read_text(stage / "STAGE_PLAN.md"),
            read_text(stage / "EXECUTION_REPORT.md"),
            read_text(stage / "CLAIM_BOUNDARY.md"),
            str(validation),
            str(metrics),
        ]
    )
    policy = profile.get("review_policy", {}) or {}
    reasons: list[str] = []
    ibp_related = _positive_operation_mentioned(
        text,
        ["ibp", "total derivative", "partial_kf", "df"],
        [
            "no ibp",
            "noibpstarted",
            "do not start ibp",
            "do not claim kernel fusion or ibp reduction",
            "do not claim ibp",
            "no total derivative",
            "no total-derivative",
            "nototalderivativeintroduced",
            "do not introduce total-derivative",
            "do not introduce total derivative",
            "do not start tensorial ibp",
            "did not start tensorial ibp",
            "did not introduce total",
            "forbidden actions",
        ],
    )
    full_tensorial_claim = _positive_operation_mentioned(
        text,
        ["full tensorial correctness", "full tensorial sigma", "full formula claim"],
        [
            "no full tensorial correctness claim",
            "do not claim full tensorial",
            "did not claim full tensorial",
            "forbidden claims",
        ],
    )
    kernel_fusion = _positive_operation_mentioned(
        text,
        ["kernel fusion", "fused kernel", "fusion pilot"],
        [
            "no formula fusion",
            "no kernel fusion",
            "do not claim kernel fusion",
            "did not start tensorial kernel fusion",
        ],
    )
    if "kernel_fusion" in stage.name or "kernel-fusion" in stage.name:
        kernel_fusion = True
    promoted = bool(
        validation.get("NewSymbolicCandidatePromoted")
        or validation.get("new_symbolic_candidate_promoted")
    )
    exploration_only = bool(
        validation.get("HypothesisExplorationOnly")
        or validation.get("hypothesis_exploration_only")
        or validation.get("CandidateValidationStatus") == "VERIFIED_BUT_NOT_PROMOTED"
    ) or _contains_any(
        text,
        [
            "exploration only",
            "conjecture generation only",
            "verified_but_not_promoted",
            "no candidate promoted",
            "without promotion",
            "no promotion",
        ],
    )
    loop_inventory_only = (
        "012a" in stage.name.lower()
        or _contains_any(
            text,
            [
                "loop-sector inventory",
                "loop sector inventory",
                "row provenance only",
                "orbit ledgers",
                "orbit ledger",
            ],
        )
    ) and not promoted
    loop_orbit = _contains_any(
        text,
        [
            "loop orbit",
            "loop_orbit",
            "loop/three-band orbit",
            "orbit canonicalization",
            "orbit-canonicalization",
        ],
    )
    if loop_orbit and (
        exploration_only
        or loop_inventory_only
        or _contains_any(text, ["architecture report", "without promoting a candidate", "no candidate promoted"])
    ):
        loop_orbit = False
    global_assembly = _positive_operation_mentioned(
        text,
        [
            "global assembly",
            "global pre-ibp assembly",
            "global_pre_ibp",
            "pre-ibp assembly",
            "assemble center, pair, and loop",
        ],
        [
            "no global assembly",
            "global assembly, or full tensorial correctness claim was touched",
            "no tensorial ibp, total derivative, global assembly",
        ],
    )
    identity = str(validation.get("identity_type", ""))
    provenance_only = identity == "RowProvenanceHashConservation" or _contains_any(
        text,
        [
            "row provenance",
            "term-hash",
            "term hash",
            "classification",
            "group center/contact rows",
            "safe pre-fusion metadata stage",
            "no_simplification",
        ],
    )
    formula_fusion_claimed = validation.get("CenterFusionDifference") not in {None, "NOT_CLAIMED"}

    if provenance_only and not formula_fusion_claimed:
        reasons.append("row provenance/classification only")
    if promoted:
        reasons.append("new symbolic candidate promoted")
    if kernel_fusion:
        reasons.append("kernel fusion mentioned")
    if loop_orbit:
        reasons.append("loop orbit canonicalization mentioned")
    if global_assembly:
        reasons.append("global assembly mentioned")
    if ibp_related:
        reasons.append("IBP or total derivative mentioned")
    if full_tensorial_claim:
        reasons.append("full tensorial correctness claim risk")

    high = promoted or kernel_fusion or loop_orbit or global_assembly or ibp_related or full_tensorial_claim
    if high:
        risk_level = "HIGH"
        lane = "L2_FULL_PANEL"
        claim_risk = "HIGH" if full_tensorial_claim or ibp_related else "MEDIUM"
    elif provenance_only:
        risk_level = "LOW"
        if policy.get("allow_l0_freeze_for_low_risk_provenance") and not policy.get("require_l1_for_claim_boundary"):
            lane = "L0_DETERMINISTIC"
        else:
            lane = "L1_COMPACT_META"
        claim_risk = "LOW"
    else:
        risk_level = "MEDIUM"
        lane = "L1_COMPACT_META"
        claim_risk = "MEDIUM"

    result = {
        "risk_level": risk_level,
        "review_lane": lane,
        "reasons": reasons or ["default medium-risk review"],
        "full_panel_required": lane == "L2_FULL_PANEL",
        "llm_review_required": lane != "L0_DETERMINISTIC",
        "ibp_related": ibp_related,
        "new_symbolic_candidate_promoted": promoted,
        "claim_risk": claim_risk,
        "reviewers": _reviewers_for_lane(policy, lane),
    }
    write_json(stage / ".loop" / "risk_classification.json", result)
    return result
