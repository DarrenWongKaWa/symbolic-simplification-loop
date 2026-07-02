from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import read_json, read_text, write_json, write_text


MAIN_EXECUTOR_FORBIDDEN_PREFIXES = (
    ".loop/reviewer_results/",
    ".loop/review_result.json",
    ".loop/meta_review_result.json",
    ".loop/decision.json",
    ".loop/checkpoint_manifest.json",
)


def actor_may_write(actor: str, rel_path: str) -> bool:
    if actor != "MainExecutor":
        return True
    normalized = rel_path.replace("\\", "/")
    return not any(normalized.startswith(prefix) for prefix in MAIN_EXECUTOR_FORBIDDEN_PREFIXES)


def _patch_history_path(stage: Path) -> Path:
    return stage / ".loop" / "patch_history.json"


def _load_patch_history(stage: Path) -> dict[str, Any]:
    path = _patch_history_path(stage)
    if path.exists():
        return read_json(path)
    return {"reasons": []}


def plan_patch_or_hard_stop(stage: Path, patch_reason: str, max_patch_attempts: int) -> dict[str, Any]:
    history = _load_patch_history(stage)
    reasons = list(history.get("reasons", []))
    if max_patch_attempts <= 0:
        decision = {"action": "HARD_STOP", "reason": "max patch attempts reached before PatchPlanner could run"}
        write_json(stage / ".loop" / "patch_planner_result.json", decision)
        return decision
    if reasons.count(patch_reason) >= 1:
        decision = {"action": "HARD_STOP", "reason": f"same patch reason repeated twice: {patch_reason}"}
        write_json(stage / ".loop" / "patch_planner_result.json", decision)
        return decision
    reasons.append(patch_reason)
    write_json(_patch_history_path(stage), {"reasons": reasons})
    claim_boundary = read_text(stage / "CLAIM_BOUNDARY.md", "")
    plan = {
        "patch_reason": patch_reason,
        "files_allowed_to_edit": ["EXECUTION_REPORT.md", "reports/*", ".loop/metrics.json", ".loop/validation_summary.json"],
        "files_forbidden_to_edit": [
            ".loop/reviewer_results/*",
            ".loop/review_result.json",
            ".loop/meta_review_result.json",
            ".loop/decision.json",
            ".loop/checkpoint_manifest.json",
        ],
        "validation_to_rerun": ["stage validation", "review aggregation", "meta review", "stage digest"],
        "claim_boundary_to_preserve": [line for line in claim_boundary.splitlines() if line.strip()],
        "expected_success_condition": "DecisionEngine returns FREEZE or FREEZE_WITH_CAVEAT after rerun.",
    }
    write_json(stage / ".loop" / "patch_planner_result.json", plan)
    write_json(stage / ".loop" / "blackboard" / "patch_planner_result.json", plan)
    write_text(
        stage / "PATCH_PLAN.md",
        "# Patch Plan\n\n"
        f"patch_reason: {patch_reason}\n\n"
        "MainExecutor may edit only the files listed in `.loop/patch_planner_result.json`.\n",
    )
    return {"action": "PATCH", "reason": patch_reason, "patch_plan": ".loop/patch_planner_result.json"}


def run_digest_reviewer(stage: Path, named_digest_slug: str | None = None) -> dict[str, Any]:
    slug = named_digest_slug or stage.name
    text_candidates = [
        stage / "reports" / f"{slug}_summary.md",
        stage / "reports" / f"{slug}_summary.tex",
        stage / "reports" / "stage_summary.md",
        stage / "reports" / "stage_summary.tex",
    ]
    evidence_candidates = [*text_candidates, stage / "reports" / f"{slug}_summary.pdf"]
    text = "\n".join(read_text(path, "") for path in text_candidates)
    lower = text.lower()
    overclaim = "full tensorial sigma_abc correctness" in lower or "prove full tensorial" in lower
    dc_preserved = "dcprojectionto1d -> inherited_pass" in lower or "dcprojectionto1d -> inherited" in lower
    named_paths = [
        str(path.relative_to(stage))
        for path in evidence_candidates
        if path.exists()
    ]
    missing_named = not any(path.endswith(f"{slug}_summary.md") for path in named_paths)
    verdict = "PASS"
    blocking: list[str] = []
    if overclaim:
        verdict = "NEEDS_PATCH"
        blocking.append("Digest contains full tensorial overclaim.")
    if missing_named:
        verdict = "NEEDS_PATCH"
        blocking.append("Named digest Markdown file is missing.")
    result = {
        "verdict": verdict,
        "stage_name": stage.name,
        "overclaim_detected": overclaim,
        "dc_caveat_preserved": dc_preserved,
        "named_digest_paths": named_paths,
        "blocking_issues": blocking,
    }
    write_json(stage / ".loop" / "digest_reviewer_result.json", result)
    write_json(stage / ".loop" / "blackboard" / "digest_reviewer_result.json", result)
    return result
