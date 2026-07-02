from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import read_text, utc_now, write_json, write_text
from .schemas import validate_with_schema


DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."
DEFAULT_FORBIDDEN_ACTIONS = [
    "candidate promotion",
    "global assembly",
    "IBP",
    "total derivative reduction",
    "full tensorial sigma_abc correctness claim",
]
EXPLICIT_FORBIDDEN_PATTERNS = [
    "start ibp",
    "perform ibp",
    "introduce total derivative",
    "total-derivative reduction",
    "promote a candidate",
    "promote the candidate",
    "promote this candidate",
    "promote candidate",
    "promote the loop candidate",
    "promote the sigma_abc candidate",
    "promote candidates",
    "candidate promotion",
    "global assembly",
    "claim full tensorial",
    "full tensorial sigma_abc correctness",
]

# Patterns that, when found inside a sentence, mark that sentence as a
# NEGATIVE / forbidden-boundary ACKNOWLEDGEMENT rather than positive
# execution intent. These must be substring matches against the lower-cased
# sentence.
_NEGATIVE_SENTENCE_MARKERS = (
    # Whole-phrase negations.
    "no candidate promotion",
    "without candidate promotion",
    "without promotion",
    "candidate promotion forbidden",
    "candidate promotion is forbidden",
    "promote the candidate forbidden",
    "promotion is forbidden",
    # Verbal negations of the imperative verbs themselves.
    "do not promote",
    "does not promote",
    "did not promote",
    "not promote",
    "never promote",
    "must not promote",
    "will not promote",
    "shall not promote",
    "should not promote",
    "do not start ibp",
    "do not perform ibp",
    "do not introduce total derivative",
    "do not introduce total-derivative",
    "do not reduce ibp",
    "do not claim full tensorial",
    "do not perform the integration by parts",
    "not start ibp",
    "not perform ibp",
    "not introduce total derivative",
    "not introduce total-derivative",
    "not reduce ibp",
    "not claim full tensorial",
    "never start ibp",
    "never perform ibp",
    "never introduce total derivative",
    "without starting ibp",
    "without performing ibp",
    "without introducing total derivative",
    "without introducing total-derivative",
    "without reducing ibp",
    "without claiming full tensorial",
    "no ibp",
    "no total derivative",
    "no total-derivative",
    "no tensorial ibp",
    "no global assembly",
    "no full tensorial claim",
)

# Patterns that, when found inside a sentence, mark that sentence as
# POSITIVE execution intent — even if the substring matches a
# forbidden phrase.
_POSITIVE_SENTENCE_MARKERS = (
    # Explicit first-person / we / agent / executor intent.
    "i will start ibp",
    "i will perform ibp",
    "i will introduce total derivative",
    "i will reduce",
    "i will promote",
    "i will promote the candidate",
    "i will promote candidate",
    "i will promote this candidate",
    "i will claim full tensorial",
    "we will start ibp",
    "we will perform ibp",
    "we will promote",
    "the agent will promote",
    "the executor will promote",
    "the executor will start ibp",
    "the executor will introduce",
    "the executor will perform",
    # Bare-imperative variants (the most common in real STAGE_PLAN.md plans).
    "promote the candidate",
    "promote this candidate",
    "promote the loop candidate",
    "promote the sigma_abc candidate",
    "promote candidate",
    "promote candidates",
    "candidate promotion",
    "start ibp",
    "perform ibp",
    "introduce total derivative",
    "introduce total-derivative",
    "perform the integration by parts",
    "reduce ibp",
    "claim full tensorial",
    "now perform ibp",
    "now start ibp",
    "now introduce total derivative",
    "now reduce ibp",
    "promote the candidate now",
    "promote candidate now",
    "start ibp now",
    "perform ibp now",
    "introduce total derivative now",
    "introduce total-derivative now",
)


_BARE_IMPERATIVE_FORBIDDEN_TRIGGERS = (
    "promote the candidate",
    "promote this candidate",
    "promote the loop candidate",
    "promote the sigma_abc candidate",
    "promote candidate",
    "promote candidates",
    "start ibp",
    "perform ibp",
    "introduce total derivative",
    "introduce total-derivative",
    "reduce ibp",
    "claim full tensorial",
)


def _classify_sentence(sentence: str) -> str:
    """Return 'positive', 'negative', or 'neutral' for the lower-cased sentence.

    Negative-context phrasing (e.g. "do not promote the candidate",
    "without introducing total derivative") takes precedence over the
    bare-imperative-only positive markers. The only ways to override
    this precedence are explicit first-person or imperative NOW / WILL
    markers (e.g. "I will start ibp", "now start ibp", "the executor
    will promote", "promote the candidate now"). Those remain
    positive regardless of surrounding negation.

    This is the Loop 019R contract: most bare-imperative positive
    markers also match many negative-context sentences as substrings
    (e.g. "do not start ibp" contains "start ibp"). The classifier
    therefore enforces negative-precedence except when the positive
    marker explicitly anchors execution intent at the start of the
    sentence or with a `now`/`will` accent.
    """
    lowered = sentence.lower()
    has_negative = any(marker in lowered for marker in _NEGATIVE_SENTENCE_MARKERS)

    override_markers = (
        "i will ",
        "we will ",
        "the agent will ",
        "the executor will ",
        "i am going to ",
        "we are going to ",
    )
    has_now_anchor = " now " in f" {lowered} " or lowered.endswith(" now") or lowered.endswith(" now.")
    has_positive_override = (
        any(prefix in lowered for prefix in override_markers) or has_now_anchor
    )

    if has_negative and not has_positive_override:
        return "negative"

    has_positive = any(marker in lowered for marker in _POSITIVE_SENTENCE_MARKERS)
    if has_positive:
        return "positive"
    return "neutral"


def _split_into_sentences(text: str) -> list[str]:
    """Split a free-form string into clause-level sentences."""
    if not text:
        return []
    # Split on punctuation that separates independent clauses.
    parts = re.split(r"[.;:\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def _explicit_profile_forbiddens(profile: dict[str, Any] | None) -> list[str]:
    """Return the profile's *explicit* forbidden_actions list (raw, lowercased).

    Profile-driven boundary enforcement looks ONLY at the explicit
    declarations in the profile YAML, not at the implicit additions
    that `_profile_forbidden` would otherwise derive from
    DEFAULT_FORBIDDEN_ACTIONS and autonomy. This is intentional: implicit
    additions are global, but profile-driven enforcement is profile-
    specific. Tests can therefore set up "neutral" vs
    "forbid-promotion" regimes by adding or removing a single
    forbidden_actions entry.
    """
    profile = profile or {}
    return [str(item).lower() for item in (profile.get("forbidden_actions") or [])]


def _positive_intent_hits(text: str, profile: dict[str, Any] | None = None) -> list[str]:
    """Return forbidden patterns whose match in `text` is positive execution intent.

    A pattern is treated as positive execution intent only when at least one
    sentence containing the pattern classifies as `positive`.

    Boundary acknowledgement (every containing sentence is `negative`
    or `neutral`) is excluded.  This keeps preparation-only stages such as
    "no candidate promotion" from being misread as promotion attempts while
    still hard-stopping positive wording such as "candidate promotion before
    tensorial IBP" or "promote the candidate now".
    """
    lowered = text.lower()
    sentences = _split_into_sentences(lowered)
    hits: list[str] = []
    for pattern in EXPLICIT_FORBIDDEN_PATTERNS:
        if pattern not in lowered:
            continue
        containing_sentences = [s for s in sentences if pattern in s]
        if not containing_sentences:
            continue
        any_positive = any(_classify_sentence(s) == "positive" for s in containing_sentences)
        if any_positive:
            hits.append(pattern)
    return hits


def _boundary_acknowledgement_hits(text: str, profile: dict[str, Any] | None = None) -> list[str]:
    """Return forbidden patterns whose matches are all boundary acknowledgements.

    A pattern is treated as boundary acknowledgement when every containing
    sentence is `negative` or `neutral`.
    """
    lowered = text.lower()
    sentences = _split_into_sentences(lowered)
    acks: list[str] = []
    for pattern in EXPLICIT_FORBIDDEN_PATTERNS:
        if pattern not in lowered:
            continue
        containing_sentences = [s for s in sentences if pattern in s]
        if not containing_sentences:
            continue
        all_acceptable = all(
            _classify_sentence(s) in {"negative", "neutral"} for s in containing_sentences
        )
        if all_acceptable and any(
            _classify_sentence(s) == "negative" for s in containing_sentences
        ):
            acks.append(pattern)
    return acks


def _parse_list_section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    out: list[str] = []
    active = False
    wanted = _normalize_section_heading(heading)
    for raw in lines:
        line = raw.strip()
        normalized = _normalize_section_heading(line)
        if normalized == wanted:
            active = True
            continue
        if active and _looks_like_section_heading(line):
            break
        if active and line.startswith("-"):
            out.append(line[1:].strip())
    return out


def _normalize_section_heading(line: str) -> str:
    stripped = line.strip().rstrip(":").strip()
    while stripped.startswith("#"):
        stripped = stripped[1:].strip()
    return re.sub(r"[\s_-]+", "_", stripped.lower())


def _looks_like_section_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return True
    return stripped.endswith(":") and not stripped.startswith("-")


def _section_present(text: str, heading: str) -> bool:
    wanted = _normalize_section_heading(heading)
    return any(_normalize_section_heading(line) == wanted for line in text.splitlines())


def _goal_from_plan(plan_text: str) -> str:
    """Locate the Goal description in a STAGE_PLAN.md body.

    The plan may use either:

      - a section header followed by body lines
            ````markdown
            ## Goal

            Inventory loop sectors without promotion.
            ````

      - or a single-line directive
            ````markdown
            Goal: Inventory loop sectors without promotion.
            ````

    Both are accepted. Falls back to the first non-blank, non-heading
    paragraph (legacy behaviour) for plans that use neither form.
    """
    lines = plan_text.splitlines()
    # Pass 1: look for a `## Goal` section and collect non-heading, non-blank
    # body lines until the next section header.
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.lower() in {"## goal", "### goal", "#### goal"}:
            collected: list[str] = []
            for inner in lines[index + 1 :]:
                inner_stripped = inner.strip()
                if inner_stripped.startswith("#"):
                    break
                if inner_stripped:
                    collected.append(inner_stripped)
            if collected:
                return " ".join(collected)
            break
    # Pass 2: look for a single-line `Goal: ...` directive.
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("goal:"):
            return stripped.split(":", 1)[1].strip()
    # Pass 3 (legacy fallback): first non-blank, non-heading line.
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.endswith(":"):
            return stripped
    return "Stage goal is defined by STAGE_PLAN.md."


def _profile_id(profile: dict[str, Any] | None) -> str:
    return str((profile or {}).get("profile") or (profile or {}).get("id") or "unknown_profile")


def _profile_forbidden(profile: dict[str, Any] | None) -> list[str]:
    profile = profile or {}
    actions = list(profile.get("forbidden_actions", []) or [])
    autonomy = profile.get("autonomy", {}) or {}
    if not autonomy.get("allow_ibp_reduction", False):
        actions.append("IBP")
    if not autonomy.get("allow_kernel_fusion", False):
        actions.append("kernel fusion unless explicitly allowed by stage profile")
    if not autonomy.get("allow_physics_simplification", False):
        actions.append("full tensorial sigma_abc correctness claim")
    actions.extend(DEFAULT_FORBIDDEN_ACTIONS)
    return sorted(dict.fromkeys(str(action) for action in actions if action))


def _profile_caveats(profile: dict[str, Any] | None) -> list[str]:
    caveats = list((profile or {}).get("permanent_caveats", []) or [])
    if not any("DCProjectionTo1D" in caveat for caveat in caveats):
        caveats.append(DC_CAVEAT)
    return caveats


def build_pre_run_brief(
    stage: Path,
    *,
    profile: dict[str, Any] | None = None,
    stage_spec: dict[str, Any] | None = None,
    written_by: str = "MainExecutor",
) -> dict[str, Any]:
    plan_text = read_text(stage / "STAGE_PLAN.md")
    expected = list(stage_spec.get("expected_outputs", []) if stage_spec else []) or _parse_list_section(plan_text, "expected_outputs")
    dependencies = list(stage_spec.get("dependencies", []) if stage_spec else []) or _parse_list_section(plan_text, "dependencies")
    allowed_stage_ids = set((profile or {}).get("allowed_stage_ids", []) or [])
    forbidden = _profile_forbidden(profile)
    caveats = _profile_caveats(profile)
    stage_intent = str(
        (stage_spec or {}).get("intent")
        or (profile or {}).get("stage_intent")
        or "unspecified"
    )
    candidate_promotion_allowed = bool(
        (stage_spec or {}).get(
            "candidate_promotion_allowed",
            (profile or {}).get("candidate_promotion_allowed", False),
        )
    )
    brief = {
        "stage_id": stage.name,
        "profile_id": _profile_id(profile),
        "written_by": written_by,
        "generated_at": utc_now(),
        "task_understanding": {
            "goal_restated": str((stage_spec or {}).get("goal") or _goal_from_plan(plan_text)),
            "stage_intent": stage_intent,
            "candidate_promotion_allowed": candidate_promotion_allowed,
            "expected_outputs": expected,
            "dependencies_acknowledged": dependencies,
            "allowed_actions": [
                "read declared inputs",
                "write declared stage artifacts",
                "run deterministic validation",
                "preserve claim boundary",
            ],
            "forbidden_actions": forbidden,
            "claim_boundary_acknowledged": (stage / "CLAIM_BOUNDARY.md").exists(),
            "caveats_acknowledged": caveats,
        },
        "profile_match": {
            "in_approved_stage_ids": (not allowed_stage_ids) or stage.name in allowed_stage_ids,
            "forbidden_actions_covered": all(action in forbidden for action in DEFAULT_FORBIDDEN_ACTIONS if action != "global assembly")
            or bool(forbidden),
            "dependencies_covered": bool(dependencies) or not _section_present(plan_text, "dependencies"),
            "expected_outputs_covered": bool(expected) or not _section_present(plan_text, "expected_outputs"),
        },
    }
    validate_with_schema(brief, "pre_run_brief")
    return brief


def audit_pre_run_brief(stage: Path, brief: dict[str, Any] | None, *, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    warnings: list[str] = []
    blocking: list[str] = []
    if brief is None:
        blocking.append("pre_run_brief missing")
        return {
            "stage_id": stage.name,
            "gate": "FAIL",
            "hard_stop": False,
            "warnings": warnings,
            "blocking_reasons": blocking,
        }
    task = brief.get("task_understanding", {})
    profile_match = brief.get("profile_match", {})
    if not task.get("expected_outputs"):
        warnings.append("expected outputs incomplete")
    if not profile_match.get("expected_outputs_covered", False):
        warnings.append("expected outputs not covered")
    if not profile_match.get("dependencies_covered", False):
        warnings.append("dependencies incomplete")
    if not task.get("claim_boundary_acknowledged"):
        warnings.append("claim boundary incomplete")
    if not any("DCProjectionTo1D" in caveat for caveat in task.get("caveats_acknowledged", [])):
        warnings.append("permanent DC caveat missing")
    if not profile_match.get("in_approved_stage_ids", True):
        warnings.append("stage not listed in approved profile stage ids")

    combined_text = " ".join(
        [
            str(task.get("goal_restated", "")),
            str(task.get("stage_intent", "")),
            " ".join(str(action) for action in task.get("allowed_actions", [])),
        ]
    )
    forbidden_hits = _positive_intent_hits(combined_text, profile=profile)
    forbidden_acks = _boundary_acknowledgement_hits(combined_text, profile=profile)

    hard_stop = bool(forbidden_hits)
    if hard_stop:
        blocking.extend(f"explicit forbidden intent: {hit}" for hit in forbidden_hits)
    if forbidden_acks:
        warnings.append(
            "forbidden boundary acknowledged: "
            + ", ".join(sorted(set(forbidden_acks)))
        )

    gate = "FAIL" if blocking else ("WARN" if warnings else "PASS")
    return {
        "stage_id": stage.name,
        "profile_id": _profile_id(profile),
        "gate": gate,
        "hard_stop": hard_stop,
        "warnings": warnings,
        "blocking_reasons": blocking,
        "forbidden_boundary_acknowledged": sorted(set(forbidden_acks)),
        "positive_intent_forbidden_hits": sorted(set(forbidden_hits)),
    }


def render_agent_self_understanding(brief: dict[str, Any], audit: dict[str, Any]) -> str:
    task = brief.get("task_understanding", {})
    return f"""# Agent Self-Understanding

## Stage

`{brief.get('stage_id')}`

## Goal Restated

{task.get('goal_restated', '')}

## Stage Intent

```text
{task.get('stage_intent', 'unspecified')}
CandidatePromotionAllowed -> {task.get('candidate_promotion_allowed', False)}
```

## Expected Outputs

{chr(10).join(f"- {item}" for item in task.get('expected_outputs', [])) or "- none"}

## Dependencies Acknowledged

{chr(10).join(f"- {item}" for item in task.get('dependencies_acknowledged', [])) or "- none"}

## Forbidden Actions

{chr(10).join(f"- {item}" for item in task.get('forbidden_actions', [])) or "- none"}

## Caveats Acknowledged

{chr(10).join(f"- {item}" for item in task.get('caveats_acknowledged', [])) or "- none"}

## Audit

```text
Gate -> {audit.get('gate')}
HardStop -> {audit.get('hard_stop')}
Warnings -> {len(audit.get('warnings', []))}
```
"""


def write_pre_run_brief(stage: Path, *, profile: dict[str, Any] | None = None, stage_spec: dict[str, Any] | None = None) -> Path:
    brief = build_pre_run_brief(stage, profile=profile, stage_spec=stage_spec)
    audit = audit_pre_run_brief(stage, brief, profile=profile)
    path = stage / ".loop" / "pre_run_brief.json"
    write_json(path, brief)
    write_json(stage / ".loop" / "pre_run_brief_audit.json", audit)
    write_text(stage / "reports" / "agent_self_understanding.md", render_agent_self_understanding(brief, audit))
    return path
