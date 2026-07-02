from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import read_json, read_text, write_json, write_text
from .reviewer import REQUIRED_REVIEWERS
from .schemas import validate_with_schema


DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


def _contains_full_tensorial_claim(text: str, *, honor_forbidden_context: bool = True) -> bool:
    lower = text.lower()
    forbidden_context = honor_forbidden_context and (
        "forbidden" in lower or "do not claim" in lower or "not full tensorial" in lower
    )
    claim_markers = [
        "full tensorial sigma_abc correctness",
        "full tensorial \\sigma",
        "prove full tensorial",
        "proves full tensorial",
    ]
    return any(marker in lower for marker in claim_markers) and not forbidden_context


def _contains_unapproved_ibp(text: str) -> bool:
    lower = text.lower()
    if "noibpstarted" in lower or "no ibp" in lower or "no tensorial ibp" in lower:
        return False
    return "ibp" in lower and "approval" not in lower and "forbidden" not in lower


def _read_optional_json(path: Path) -> dict[str, Any]:
    return read_json(path) if path.exists() else {}


def run_scientific_metareview(stage: Path, next_safe_stage: str | None = None) -> Path:
    validation_path = stage / ".loop" / "validation_summary.json"
    metrics_path = stage / ".loop" / "metrics.json"
    review_path = stage / ".loop" / "review_result.json"
    risk_path = stage / ".loop" / "risk_classification.json"
    reviewer_dir = stage / ".loop" / "reviewer_results"
    execution_path = stage / "EXECUTION_REPORT.md"
    claim_path = stage / "CLAIM_BOUNDARY.md"
    packet_path = stage / "review_packet.md"

    validation = _read_optional_json(validation_path)
    metrics = _read_optional_json(metrics_path)
    review = _read_optional_json(review_path)
    risk = _read_optional_json(risk_path)
    texts = "\n".join(
        [
            read_text(execution_path),
            read_text(claim_path),
            read_text(packet_path),
            str(validation),
            str(review),
            str(metrics),
        ]
    )

    required_reviewers = [
        {
            "AlgebraReviewer": "algebra_reviewer",
            "PhysicsReviewer": "physics_reviewer",
            "SoftwareReviewer": "software_reviewer",
            "ScientificMetaReviewer": "scientific_metareviewer",
        }.get(name, str(name).lower())
        for name in risk.get("reviewers", REQUIRED_REVIEWERS)
    ]
    missing_reviewers = [name for name in required_reviewers if not (reviewer_dir / f"{name}.json").exists()]
    blocking: list[str] = []
    if validation.get("overall_gate") != "PASS":
        blocking.append("validation_summary.overall_gate is not PASS")
    if review.get("verdict") == "FAILED":
        blocking.append("ordinary review_result verdict is FAILED")
    if not review:
        blocking.append("ordinary review_result.json is missing")
    for reviewer in missing_reviewers:
        blocking.append(f"missing reviewer output: {reviewer}.json")

    packet_text = read_text(packet_path)
    full_tensorial_claim = _contains_full_tensorial_claim(packet_text, honor_forbidden_context=False) or _contains_full_tensorial_claim(texts)
    ibp_unapproved = _contains_unapproved_ibp(texts)
    dc_caveat_preserved = DC_CAVEAT in texts or "DCProjectionTo1D -> INHERITED_PASS" in texts
    overclaim = full_tensorial_claim or ibp_unapproved or not dc_caveat_preserved
    if full_tensorial_claim:
        blocking.append("blocking overclaim: full tensorial sigma_abc correctness claim detected")
    if ibp_unapproved:
        blocking.append("blocking overclaim: IBP appears to have started without explicit approval")
    if not dc_caveat_preserved:
        blocking.append("Stage 001 DC inherited-pass caveat is not preserved")

    if full_tensorial_claim or ibp_unapproved:
        verdict = "FAILED"
    elif blocking:
        verdict = "NEEDS_PATCH"
    elif validation.get("caveats") or review.get("nonblocking_caveats") or dc_caveat_preserved:
        verdict = "PASS_WITH_CAVEAT"
    else:
        verdict = "PASS"

    stage_name = stage.name
    if "pair_kernel_fusion" in stage_name:
        scientific_status = "PASS as pair-sector row-provenance fusion pilot, not final tensorial pair kernel formula."
    elif "center_sector" in stage_name:
        scientific_status = "PASS as center/contact-sector row-provenance pattern fusion pilot, not center-sector IBP."
    elif "mock" in stage_name:
        scientific_status = "PASS as mock exact-identity loop stage."
    else:
        scientific_status = "PASS as stage-local checkpoint with preserved claim boundary."
    if verdict in {"NEEDS_PATCH", "FAILED"}:
        scientific_status = f"{verdict}: stage must not freeze until blocking issues are patched."

    caveats = list(dict.fromkeys([*validation.get("caveats", []), *review.get("nonblocking_caveats", [])]))
    if dc_caveat_preserved and not any("DCProjectionTo1D" in caveat for caveat in caveats):
        caveats.append(DC_CAVEAT)

    payload = {
        "verdict": verdict,
        "stage_name": stage_name,
        "scientific_status": scientific_status,
        "engineering_status": "Validation, ordinary review, and reviewer-role artifacts were audited.",
        "allowed_claims": review.get("allowed_claims", []),
        "forbidden_claims": review.get("forbidden_claims", []) + ["Do not claim full tensorial sigma_abc correctness."],
        "caveats_to_preserve": caveats,
        "boundary_audit": {
            "overclaim_detected": overclaim,
            "full_tensorial_claim_detected": full_tensorial_claim,
            "ibp_started_without_approval": ibp_unapproved,
            "dc_caveat_preserved": dc_caveat_preserved,
        },
        "next_safe_stage": next_safe_stage,
        "human_approval_required": True,
        "short_human_summary": scientific_status,
        "blocking_issues": blocking,
        "source_files": [
            str(path.relative_to(stage))
            for path in [
                validation_path,
                metrics_path,
                review_path,
                risk_path,
                execution_path,
                claim_path,
                packet_path,
            ]
            if path.exists()
        ],
    }
    validate_with_schema(payload, "meta_review_result")
    target = stage / ".loop" / "meta_review_result.json"
    write_json(target, payload)
    write_json(stage / ".loop" / f"{stage.name}_meta_review.json", payload)
    write_human_readable_review(stage, payload)
    return target


def write_human_readable_review(stage: Path, meta: dict[str, Any]) -> Path:
    caveats = "\n".join(f"- {item}" for item in meta.get("caveats_to_preserve", [])) or "- none"
    allowed = "\n".join(f"- {item}" for item in meta.get("allowed_claims", [])) or "- none"
    forbidden = "\n".join(f"- {item}" for item in meta.get("forbidden_claims", [])) or "- none"
    blocking = "\n".join(f"- {item}" for item in meta.get("blocking_issues", [])) or "- none"
    text = f"""# Human Readable Scientific Review

## Verdict

`{meta['verdict']}`

## Scientific Status

{meta['scientific_status']}

## Engineering Status

{meta['engineering_status']}

## Boundary Audit

```json
{meta['boundary_audit']}
```

## Allowed Claims

{allowed}

## Forbidden Claims

{forbidden}

## Caveats To Preserve

{caveats}

## Blocking Issues

{blocking}

## Short Human Summary

{meta['short_human_summary']}
"""
    target = stage / "reports" / "human_readable_review.md"
    write_text(target, text)
    write_text(stage / "reports" / f"{stage.name}_human_review.md", text)
    return target
