from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent_invocation import file_sha256
from .config import read_json, utc_now, write_json, write_text
from .decision import decide_next_action
from .meta_review import run_scientific_metareview
from .review_quality import build_review_quality
from .reviewer import aggregate_review_results
from .stage_digest import build_stage_digest


HASHED_INPUTS = [
    "STAGE_PLAN.md",
    "EXECUTION_REPORT.md",
    "CLAIM_BOUNDARY.md",
    ".loop/validation_summary.json",
    ".loop/metrics.json",
    ".loop/risk_classification.json",
    "review_minipacket.md",
]


def input_hashes(stage: Path) -> dict[str, str | None]:
    hashes: dict[str, str | None] = {}
    for rel in HASHED_INPUTS:
        path = stage / rel
        hashes[rel] = file_sha256(path) if path.exists() else None
    return hashes


def enqueue_pending_review(stage: Path, reason: str, risk: dict[str, Any], retry_after: str | None = None) -> Path:
    queue_dir = stage / ".loop" / "review_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "stage_name": stage.name,
        "stage_path": str(stage),
        "stage_status": "VALIDATED_PENDING_REVIEW",
        "reason": reason,
        "retry_after": retry_after,
        "risk_classification": risk,
        "review_lane": risk.get("review_lane"),
        "required_reviewers": risk.get("reviewers", []),
        "input_hashes": input_hashes(stage),
        "executor_rerun_required": False,
        "reviewer_resume_required": True,
        "created_at": utc_now(),
    }
    target = queue_dir / "pending_reviews.jsonl"
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    write_json(
        stage / ".loop" / "runtime_limits.json",
        {
            "status": "VALIDATED_PENDING_REVIEW",
            "reason": reason,
            "retry_after": retry_after,
            "patch_required": False,
        },
    )
    return target


def validation_inputs_unchanged(stage: Path, pending_record: dict[str, Any]) -> bool:
    return input_hashes(stage) == pending_record.get("input_hashes", {})


def _deterministic_review(stage: Path) -> dict[str, Any]:
    validation = read_json(stage / ".loop" / "validation_summary.json")
    verdict = "PASS" if validation.get("overall_gate") == "PASS" else "NEEDS_PATCH"
    review = {
        "verdict": verdict,
        "stage_name": stage.name,
        "reviewer_role": "DeterministicLaneReview",
        "review_scope": "L0_DETERMINISTIC",
        "mathematical_status": {
            "exact_reconstruction": validation.get("overall_gate") == "PASS",
            "simplification_real": False,
            "regression_preserved": validation.get("overall_gate") == "PASS",
            "overclaim_detected": False,
        },
        "blocking_issues": [] if verdict == "PASS" else ["validation_summary.overall_gate is not PASS"],
        "nonblocking_caveats": ["L0 deterministic lane; no LLM reviewer invoked."],
        "allowed_claims": ["Low-risk deterministic provenance stage may freeze only with validation PASS."],
        "forbidden_claims": ["Do not infer new symbolic simplification from L0 review."],
        "next_action": "FREEZE" if verdict == "PASS" else "PATCH",
        "suggested_next_stage": None,
        "patch_instructions": [],
    }
    write_json(stage / ".loop" / "review_result.json", review)
    return review


def _write_decision(stage: Path, review: dict[str, Any]) -> dict[str, Any]:
    validation = read_json(stage / ".loop" / "validation_summary.json")
    meta_path = stage / ".loop" / "meta_review_result.json"
    quality_path = stage / ".loop" / "review_quality.json"
    meta = read_json(meta_path) if meta_path.exists() else None
    quality = read_json(quality_path) if quality_path.exists() else None
    decision = decide_next_action(validation, review, meta_review=meta)
    if decision.freeze_allowed and quality and not quality.get("freeze_allowed_by_review_quality", False):
        payload = {
            "action": "DO_NOT_FREEZE",
            "reason": "review_quality blocked freeze",
            "freeze_allowed": False,
            "caveats": quality.get("caveats_preserved", []),
            "suggested_next_stage": quality.get("next_safe_stage"),
            "patch_required": False,
            "retry_after": None,
        }
        write_json(stage / ".loop" / "decision.json", payload)
        write_json(stage / "decision.json", payload)
        return payload
    payload = {
        "action": decision.action,
        "reason": decision.reason,
        "freeze_allowed": decision.freeze_allowed,
        "caveats": decision.caveats,
        "suggested_next_stage": decision.suggested_next_stage,
        "patch_required": decision.patch_required,
        "retry_after": decision.retry_after,
    }
    write_json(stage / ".loop" / "decision.json", payload)
    write_json(stage / "decision.json", payload)
    return payload


def _compact_meta_review(stage: Path, record: dict[str, Any]) -> dict[str, Any]:
    validation = read_json(stage / ".loop" / "validation_summary.json")
    risk = record.get("risk_classification", {})
    verdict = "PASS_WITH_CAVEAT" if validation.get("caveats") else "PASS"
    review = {
        "verdict": verdict if validation.get("overall_gate") == "PASS" else "NEEDS_PATCH",
        "stage_name": stage.name,
        "reviewer_role": "ScientificMetaReviewer",
        "review_scope": risk.get("review_lane", "L1_COMPACT_META"),
        "mathematical_status": {
            "exact_reconstruction": validation.get("overall_gate") == "PASS",
            "simplification_real": False,
            "regression_preserved": validation.get("overall_gate") == "PASS",
            "overclaim_detected": False,
        },
        "blocking_issues": [] if validation.get("overall_gate") == "PASS" else ["validation_summary.overall_gate is not PASS"],
        "nonblocking_caveats": list(validation.get("caveats", [])),
        "allowed_claims": ["PASS as center-sector row-provenance conservation checkpoint."],
        "forbidden_claims": [
            "NOT PASS as center-sector fused physical kernel formula.",
            "Do not claim full tensorial sigma_abc correctness.",
        ],
        "next_action": "FREEZE" if validation.get("overall_gate") == "PASS" else "PATCH",
        "suggested_next_stage": "sigma_abc_012_loop_orbit_canonicalization_pilot",
        "patch_instructions": [],
    }
    write_json(stage / ".loop" / "reviewer_results" / "scientific_metareviewer.json", review)
    aggregate_review_results(stage, required_reviewer_keys=["scientific_metareviewer"])
    run_scientific_metareview(stage, next_safe_stage=review["suggested_next_stage"])
    build_review_quality(stage, next_safe_stage=review["suggested_next_stage"])
    build_stage_digest(stage)
    return read_json(stage / ".loop" / "review_result.json")


def iter_pending_records(run_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    queue_paths = set(run_root.glob("stages/*/.loop/review_queue/pending_reviews.jsonl"))
    queue_paths.update(run_root.glob("*/.loop/review_queue/pending_reviews.jsonl"))
    for queue_path in sorted(queue_paths):
        for line in queue_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


def resume_pending_reviews(run_root: Path, *, allow_l0_freeze: bool = False) -> dict[str, Any]:
    resumed = 0
    needs_revalidation = 0
    decisions: list[dict[str, Any]] = []
    for record in iter_pending_records(run_root):
        stage = Path(record["stage_path"])
        if not validation_inputs_unchanged(stage, record):
            needs_revalidation += 1
            write_json(
                stage / ".loop" / "decision.json",
                {
                    "action": "RERUN_VALIDATION",
                    "reason": "pending review input hashes changed",
                    "freeze_allowed": False,
                    "patch_required": False,
                },
            )
            continue
        lane = record.get("review_lane")
        if lane == "L0_DETERMINISTIC" and allow_l0_freeze:
            review = _deterministic_review(stage)
            decisions.append(_write_decision(stage, review))
            resumed += 1
        elif lane == "L1_COMPACT_META":
            review = _compact_meta_review(stage, record)
            decisions.append(_write_decision(stage, review))
            resumed += 1
        else:
            write_text(
                stage / ".loop" / "resume_pending_review_required.txt",
                "Non-L0 pending review requires configured reviewer invocation.\n",
            )
    return {
        "resumed": resumed,
        "needs_revalidation": needs_revalidation,
        "executor_rerun_required": False,
        "decisions": decisions,
    }
