from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    freeze_allowed: bool = False
    caveats: list[str] = field(default_factory=list)
    suggested_next_stage: str | None = None
    patch_required: bool = False
    retry_after: str | None = None


def _find_runtime_limit_issue(review: dict, meta_review: dict | None = None) -> str | None:
    fields = [
        review.get("blocking_issues", []),
        review.get("nonblocking_caveats", []),
        review.get("patch_instructions", []),
    ]
    if meta_review:
        fields.extend(
            [
                meta_review.get("blocking_issues", []),
                meta_review.get("nonblocking_caveats", []),
                meta_review.get("caveats_to_preserve", []),
            ]
        )
    for values in fields:
        for raw in values or []:
            issue = str(raw)
            lowered = issue.lower()
            if (
                "agent_runtime_quota_exhausted" in lowered
                or "agent_quota_limit" in lowered
                or "agent_runtime_timeout" in lowered
                or "agent_timeout" in lowered
                or "agent_no_output" in lowered
                or "usage limit" in lowered
                or "quota" in lowered
                or "timed out" in lowered
            ):
                return issue
    return None


def _extract_retry_after(issue: str) -> str | None:
    markers = ["RetryAfter ->", "RetryAfter:", "try again at"]
    for marker in markers:
        if marker in issue:
            value = issue.split(marker, 1)[1].strip()
            for delimiter in [" Agent ->", " Summary ->", "\n"]:
                if delimiter in value:
                    value = value.split(delimiter, 1)[0]
            return value.strip().rstrip(".")
    return None


def decide_next_action(
    validation: dict,
    review: dict,
    hard_stops: list[str] | None = None,
    meta_review: dict | None = None,
) -> Decision:
    hard_stops = hard_stops or []
    if hard_stops:
        return Decision("STOP", "; ".join(hard_stops))

    if validation.get("overall_gate") != "PASS":
        return Decision("DO_NOT_FREEZE", "validation failed or missing PASS gate")

    verdict = review.get("verdict")
    next_action = review.get("next_action")

    runtime_limit_issue = _find_runtime_limit_issue(review, meta_review)
    if runtime_limit_issue:
        retry_after = _extract_retry_after(runtime_limit_issue)
        reason = "agent runtime quota exhausted"
        if retry_after:
            reason += f"; retry after {retry_after}"
        return Decision(
            "VALIDATED_PENDING_REVIEW",
            reason,
            freeze_allowed=False,
            patch_required=False,
            retry_after=retry_after,
        )

    meta_verdict = meta_review.get("verdict") if meta_review else None
    if meta_review and meta_verdict not in {"PASS", "PASS_WITH_CAVEAT"}:
        return Decision("DO_NOT_FREEZE", f"meta review blocked freeze: {meta_verdict!r}")

    if verdict == "PASS":
        if next_action == "OPEN_NEXT_STAGE":
            return Decision(
                "FREEZE_THEN_OPEN_NEXT_STAGE",
                "review passed and requested next stage",
                freeze_allowed=True,
                caveats=meta_review.get("caveats_to_preserve", []) if meta_review else [],
                suggested_next_stage=review.get("suggested_next_stage"),
            )
        return Decision(
            "FREEZE",
            "review passed",
            freeze_allowed=True,
            caveats=meta_review.get("caveats_to_preserve", []) if meta_review else [],
        )

    if verdict == "PASS_WITH_CAVEAT":
        caveats = list(review.get("nonblocking_caveats", []))
        if meta_review:
            caveats.extend(meta_review.get("caveats_to_preserve", []))
        return Decision(
            "FREEZE_WITH_CAVEAT",
            "review passed with caveats",
            freeze_allowed=True,
            caveats=caveats,
            suggested_next_stage=review.get("suggested_next_stage"),
        )

    if verdict == "NEEDS_PATCH":
        return Decision("PATCH", "review requested patch", patch_required=True)

    if verdict == "FAILED":
        return Decision("FAIL", "review failed stage")

    return Decision("DO_NOT_FREEZE", f"unknown review verdict: {verdict!r}")
