from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import read_json, read_text, write_json, write_text
from .meta_review import DC_CAVEAT
from .schemas import validate_with_schema


FULL_TENSORIAL_MARKERS = [
    "we prove full tensorial sigma_abc correctness",
    "full tensorial sigma_abc correctness is proven",
    "full tensorial \\sigma",
]


def _stage_report_basename(stage: Path) -> str:
    name = stage.name
    if name.startswith("sigma_abc_"):
        return "stage_" + name.removeprefix("sigma_abc_")
    return f"stage_{name}"


def _contains_positive_overclaim(stage: Path) -> bool:
    for rel in ["EXECUTION_REPORT.md", "review_packet.md"]:
        text = read_text(stage / rel).lower()
        if any(marker in text for marker in FULL_TENSORIAL_MARKERS):
            return True
    return False


def _validated_claims(validation: dict[str, Any]) -> list[str]:
    claims: list[str] = []
    identity = validation.get("identity_type")
    if identity:
        claims.append(f"{identity} validated with OverallGate -> {validation.get('overall_gate')}")
    for check in validation.get("checks", []):
        if check.get("gate") == "PASS":
            claims.append(f"{check.get('name')} -> {check.get('actual')}")
    return claims


def _inherited_or_deferred(validation: dict[str, Any]) -> list[str]:
    inherited: list[str] = []
    for key, value in validation.items():
        if isinstance(value, str) and ("INHERITED" in value or "DEFERRED" in value or "NOT_CLAIMED" in value):
            inherited.append(f"{key} -> {value}")
    for check in validation.get("checks", []):
        actual = check.get("actual")
        if isinstance(actual, str) and ("INHERITED" in actual or "DEFERRED" in actual or "NOT_CLAIMED" in actual):
            inherited.append(f"{check.get('name')} -> {actual}")
    return list(dict.fromkeys(inherited))


def _stage_claim_language(stage: Path, validation: dict[str, Any]) -> tuple[str, list[str]]:
    name = stage.name
    if "sigma_abc_011_center_sector_pilot" in name or validation.get("CenterFusionDifference") == "NOT_CLAIMED":
        return (
            "center-sector row-provenance conservation checkpoint",
            [
                "center-sector fused physical kernel formula",
                "full tensorial sigma_abc correctness",
            ],
        )
    if "pair_kernel_fusion" in name:
        return (
            "pair-sector row-provenance kernel-family fusion pilot",
            [
                "final tensorial pair-kernel formula",
                "full tensorial sigma_abc correctness",
            ],
        )
    if "loop_orbit" in name:
        return (
            "loop-sector orbit-canonicalization checkpoint with explicit validation boundary",
            [
                "loop-sector IBP reduction",
                "full tensorial sigma_abc correctness",
            ],
        )
    return (
        "stage-local validated checkpoint",
        ["full tensorial sigma_abc correctness"],
    )


def _write_review_quality_report(stage: Path, payload: dict[str, Any]) -> Path:
    basename = _stage_report_basename(stage)
    not_pass = "\n".join(f"- {item}" for item in payload["not_pass_as"]) or "- none"
    validated = "\n".join(f"- {item}" for item in payload["validated_claims"]) or "- none"
    inherited = "\n".join(f"- {item}" for item in payload["inherited_or_deferred_claims"]) or "- none"
    caveats = "\n".join(f"- {item}" for item in payload["caveats_preserved"]) or "- none"
    text = f"""# Review Quality Audit: `{stage.name}`

## PASS as

{payload["pass_as"]}

## NOT PASS as

{not_pass}

## Actually validated

{validated}

## Inherited or deferred

{inherited}

## Caveats preserved

{caveats}

## Overclaim detected

`{payload["overclaim_detected"]}`

## Freeze allowed by review quality

`{payload["freeze_allowed_by_review_quality"]}`

## Review lane

`{payload["review_lane"]}`: {payload["review_lane_justification"]}

## Next safe stage

`{payload["next_safe_stage"]}`
"""
    target = stage / "reports" / f"{basename}_review_quality.md"
    write_text(target, text)
    write_text(stage / "reports" / f"{stage.name}_review_quality.md", text)
    return target


def build_review_quality(stage: Path, next_safe_stage: str | None = None) -> dict[str, Any]:
    validation = read_json(stage / ".loop" / "validation_summary.json")
    risk = read_json(stage / ".loop" / "risk_classification.json") if (stage / ".loop" / "risk_classification.json").exists() else {}
    meta = read_json(stage / ".loop" / "meta_review_result.json") if (stage / ".loop" / "meta_review_result.json").exists() else {}
    review = read_json(stage / ".loop" / "review_result.json") if (stage / ".loop" / "review_result.json").exists() else {}
    pass_as, not_pass_as = _stage_claim_language(stage, validation)
    caveats = list(dict.fromkeys([*validation.get("caveats", []), *review.get("nonblocking_caveats", []), *meta.get("caveats_to_preserve", [])]))
    joined = "\n".join([read_text(stage / "CLAIM_BOUNDARY.md"), str(validation), str(review), str(meta)])
    if ("DCProjectionTo1D -> INHERITED_PASS" in joined or "DCProjectionTo1D -> INHERITED_PASS" in read_text(stage / "review_packet.md")) and not any("DCProjectionTo1D" in caveat for caveat in caveats):
        caveats.append(DC_CAVEAT)
    overclaim = _contains_positive_overclaim(stage)
    validation_pass = validation.get("overall_gate") == "PASS"
    review_ok = review.get("verdict") in {"PASS", "PASS_WITH_CAVEAT", None}
    meta_ok = meta.get("verdict", "PASS") in {"PASS", "PASS_WITH_CAVEAT"}
    payload = {
        "pass_as": pass_as,
        "not_pass_as": list(dict.fromkeys(not_pass_as)),
        "validated_claims": _validated_claims(validation),
        "inherited_or_deferred_claims": _inherited_or_deferred(validation),
        "caveats_preserved": caveats,
        "overclaim_detected": overclaim,
        "freeze_allowed_by_review_quality": bool(validation_pass and review_ok and meta_ok and not overclaim),
        "human_approval_required": bool(risk.get("ibp_related") or validation.get("HumanApprovalRequired", False)),
        "review_lane": risk.get("review_lane", "L1_COMPACT_META"),
        "review_lane_justification": "; ".join(risk.get("reasons", [])) or "risk classifier not available; default compact review",
        "next_safe_stage": next_safe_stage or review.get("suggested_next_stage") or meta.get("next_safe_stage"),
    }
    validate_with_schema(payload, "review_quality")
    write_json(stage / ".loop" / "review_quality.json", payload)
    _write_review_quality_report(stage, payload)
    return payload

