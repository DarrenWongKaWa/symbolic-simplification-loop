from __future__ import annotations

from pathlib import Path

from .config import read_json, read_text, write_json, write_text


REVIEW_MODES = ("codex_subagent", "manual_chatgpt", "openai_api")
DEFAULT_REVIEW_MODE = "codex_subagent"

REQUIRED_REVIEWERS = {
    "algebra_reviewer": "AlgebraReviewer",
    "physics_reviewer": "PhysicsReviewer",
    "software_reviewer": "SoftwareReviewer",
}

REVIEWER_KEY_BY_ROLE = {
    "AlgebraReviewer": "algebra_reviewer",
    "PhysicsReviewer": "physics_reviewer",
    "SoftwareReviewer": "software_reviewer",
    "ScientificMetaReviewer": "scientific_metareviewer",
}


REVIEWER_PROFILES = {
    "AlgebraReviewer": {
        "focus": "Old - New - dF identities, row counts, validation gates, protected algebraic regressions.",
        "questions": [
            "Does the validation identity match the stage goal?",
            "Are row counts, cokernel counts, and reconstruction gates internally consistent?",
            "Does any claimed IBP equivalence include an exported primitive?",
            "Did protected kernels such as KR remain unchanged when claimed?",
        ],
    },
    "PhysicsReviewer": {
        "focus": "basis choice, symmetry logic, index conventions, physical claim boundary, and external-kernel convention maps.",
        "questions": [
            "Are basis objects and index conventions defined consistently?",
            "Are model-specific parity or symmetry cancellations kept separate from general identities?",
            "Are Anan or other external comparisons convention-mapped honestly?",
            "Are forbidden claims excluded from the proposed checkpoint?",
        ],
    },
    "SoftwareReviewer": {
        "focus": "repo hygiene, stale files, pre/post-IBP table provenance, reproducibility, and script/output consistency.",
        "questions": [
            "Do scripts use the intended current input snapshots?",
            "Is there evidence of stale, pre-IBP, or wrong-version table mixing?",
            "Are generated reports consistent with machine-readable validation files?",
            "Can another local run reproduce the key outputs from archived inputs?",
        ],
    },
    "ScientificMetaReviewer": {
        "focus": "scientific claim boundary, caveat preservation, benchmark protection, and next-branch scope.",
        "questions": [
            "Does the stage overclaim beyond deterministic validation?",
            "Are permanent caveats preserved exactly?",
            "Are protected benchmarks and forbidden operations handled honestly?",
            "Is the next action freeze, pending review, patch, or human approval?",
        ],
    },
}


def load_review_mode(stage: Path) -> str:
    candidates = [
        stage / ".loop" / "review_config.json",
        stage.parents[1] / "loop_config.json" if len(stage.parents) > 1 else stage / "loop_config.json",
        stage.parent / "loop_config.json",
    ]
    for path in candidates:
        if path.exists():
            config = read_json(path)
            mode = config.get("review", {}).get("mode", DEFAULT_REVIEW_MODE)
            if mode not in REVIEW_MODES:
                raise ValueError(f"Unsupported review mode {mode!r}; expected one of {REVIEW_MODES}")
            return mode
    return DEFAULT_REVIEW_MODE


def load_review_result(stage: Path) -> dict:
    candidates = [
        stage / ".loop" / "review_result.json",
        stage / "review_result.json",
    ]
    for path in candidates:
        if path.exists():
            return read_json(path)
    raise FileNotFoundError(f"No review_result.json found for stage {stage}")


def import_review_result(stage: Path, source: Path) -> Path:
    review = read_json(source)
    target = stage / ".loop" / "review_result.json"
    write_json(target, review)
    return target


def import_role_review_result(stage: Path, source: Path, reviewer_role: str | None = None) -> Path:
    review = read_json(source)
    role = reviewer_role or review.get("reviewer_role") or source.stem.replace("review_result.", "")
    if role not in REVIEWER_PROFILES and role not in {"GeneralReviewer", "ManualGPT", "OpenAIAPI", "IntegratorReview"}:
        raise ValueError(f"Unsupported reviewer role {role!r}")
    target = stage / ".loop" / "reviews" / f"review_result.{role}.json"
    write_json(target, review)
    return target


def aggregate_review_results(stage: Path, required_reviewer_keys: list[str] | None = None) -> Path:
    required_reviewer_keys = required_reviewer_keys or list(REQUIRED_REVIEWERS)
    reviewer_results_dir = stage / ".loop" / "reviewer_results"
    lower_files = {
        path.stem: path for path in sorted(reviewer_results_dir.glob("*.json"))
    } if reviewer_results_dir.exists() else {}
    missing = [name for name in required_reviewer_keys if name not in lower_files]

    if lower_files and missing:
        aggregate = {
            "verdict": "NEEDS_PATCH",
            "stage_name": stage.name,
            "reviewer_role": "IntegratorReview",
            "review_scope": "routine_branch",
            "mathematical_status": {
                "exact_reconstruction": False,
                "simplification_real": False,
                "regression_preserved": False,
                "overclaim_detected": False,
            },
            "blocking_issues": [f"Missing reviewer output: {name}.json" for name in missing],
            "nonblocking_caveats": [],
            "allowed_claims": [],
            "forbidden_claims": [],
            "next_action": "PATCH",
            "suggested_next_stage": None,
            "patch_instructions": ["Run scripts/run_reviewer_agents.py or provide all three structured reviewer outputs."],
            "source_review_files": [str(path.relative_to(stage)) for path in lower_files.values()],
        }
        target = stage / ".loop" / "review_result.json"
        write_json(target, aggregate)
        return target

    if lower_files:
        files = [lower_files[name] for name in required_reviewer_keys]
    else:
        reviews_dir = stage / ".loop" / "reviews"
        files = sorted(reviews_dir.glob("review_result.*.json")) if reviews_dir.exists() else []
        if not files:
            aggregate = {
                "verdict": "NEEDS_PATCH",
                "stage_name": stage.name,
                "reviewer_role": "IntegratorReview",
                "review_scope": "routine_branch",
                "mathematical_status": {
                    "exact_reconstruction": False,
                    "simplification_real": False,
                    "regression_preserved": False,
                    "overclaim_detected": False,
                },
                "blocking_issues": [f"No role review results found under {reviewer_results_dir}"],
                "nonblocking_caveats": [],
                "allowed_claims": [],
                "forbidden_claims": [],
                "next_action": "PATCH",
                "suggested_next_stage": None,
                "patch_instructions": ["Run scripts/run_reviewer_agents.py or import manual reviewer results before deciding."],
                "source_review_files": [],
            }
            target = stage / ".loop" / "review_result.json"
            write_json(target, aggregate)
            return target

    reviews = [read_json(path) for path in files]
    verdicts = [review.get("verdict") for review in reviews]
    if "FAILED" in verdicts:
        verdict = "FAILED"
        next_action = "FAIL"
    elif "NEEDS_PATCH" in verdicts:
        verdict = "NEEDS_PATCH"
        next_action = "PATCH"
    elif "PASS_WITH_CAVEAT" in verdicts:
        verdict = "PASS_WITH_CAVEAT"
        next_action = "FREEZE"
    else:
        verdict = "PASS"
        next_action = "FREEZE"

    def flatten(field: str) -> list[str]:
        values: list[str] = []
        for review in reviews:
            values.extend(str(item) for item in review.get(field, []))
        return values

    exact = all(review.get("mathematical_status", {}).get("exact_reconstruction", False) for review in reviews)
    simplification = all(review.get("mathematical_status", {}).get("simplification_real", False) for review in reviews)
    regression = all(review.get("mathematical_status", {}).get("regression_preserved", False) for review in reviews)
    overclaim = any(review.get("mathematical_status", {}).get("overclaim_detected", False) for review in reviews)

    aggregate = {
        "verdict": verdict,
        "stage_name": stage.name,
        "reviewer_role": "IntegratorReview",
        "review_scope": "routine_branch",
        "mathematical_status": {
            "exact_reconstruction": exact,
            "simplification_real": simplification,
            "regression_preserved": regression,
            "overclaim_detected": overclaim,
        },
        "blocking_issues": flatten("blocking_issues"),
        "nonblocking_caveats": flatten("nonblocking_caveats"),
        "allowed_claims": flatten("allowed_claims"),
        "forbidden_claims": flatten("forbidden_claims"),
        "next_action": next_action,
        "suggested_next_stage": next((review.get("suggested_next_stage") for review in reviews if review.get("suggested_next_stage")), None),
        "patch_instructions": flatten("patch_instructions"),
        "source_review_files": [str(path.relative_to(stage)) for path in files],
    }
    target = stage / ".loop" / "review_result.json"
    write_json(target, aggregate)
    return target


def _role_output_name(role_key: str) -> str:
    return f"{role_key}.json"


def run_local_reviewer_agent(stage: Path, role_key: str, mode: str | None = None, review_scope: str = "routine_branch") -> Path:
    if role_key not in REQUIRED_REVIEWERS:
        raise ValueError(f"Unsupported reviewer key {role_key!r}")
    mode = mode or load_review_mode(stage)
    if mode not in REVIEW_MODES:
        raise ValueError(f"Unsupported review mode {mode!r}; expected one of {REVIEW_MODES}")

    role = REQUIRED_REVIEWERS[role_key]
    validation_path = stage / ".loop" / "validation_summary.json"
    metrics_path = stage / ".loop" / "metrics.json"
    packet_path = stage / "review_packet.md"
    claim_path = stage / "CLAIM_BOUNDARY.md"

    validation = read_json(validation_path) if validation_path.exists() else {}
    metrics = read_json(metrics_path) if metrics_path.exists() else {}
    packet = read_text(packet_path, "(missing review_packet.md)")
    claim_boundary = read_text(claim_path, "")

    blocking: list[str] = []
    caveats: list[str] = []
    if validation.get("overall_gate") != "PASS":
        blocking.append("validation_summary.overall_gate is not PASS")
    for required in [packet_path, validation_path, metrics_path]:
        if not required.exists():
            blocking.append(f"missing required reviewer input: {required.relative_to(stage)}")
    if not claim_path.exists():
        caveats.append("CLAIM_BOUNDARY.md is missing; reviewer used packet-only boundary.")

    if mode == "manual_chatgpt":
        caveats.append("Configured for manual ChatGPT review; local reviewer emitted a placeholder structured audit.")
    elif mode == "openai_api":
        caveats.append("Configured for OpenAI API review; local runner did not call external API in this implementation.")

    overclaim = "full tensorial" in packet.lower() and "forbidden" not in packet.lower() + claim_boundary.lower()
    if overclaim:
        blocking.append("possible overclaim detected without an explicit forbidden-claims boundary")

    verdict = "NEEDS_PATCH" if blocking else "PASS"
    next_action = "PATCH" if blocking else "FREEZE"
    payload = {
        "verdict": verdict,
        "stage_name": stage.name,
        "reviewer_role": role,
        "review_scope": review_scope,
        "mathematical_status": {
            "exact_reconstruction": validation.get("overall_gate") == "PASS",
            "simplification_real": bool(metrics.get("deltas")) or bool(metrics.get("after")),
            "regression_preserved": validation.get("overall_gate") == "PASS",
            "overclaim_detected": overclaim,
        },
        "blocking_issues": blocking,
        "nonblocking_caveats": caveats,
        "allowed_claims": [
            "Stage may freeze only if validation_summary.overall_gate is PASS and all required reviewer inputs exist."
        ],
        "forbidden_claims": [
            "Do not override validation failures with reviewer approval.",
            "Do not claim unvalidated physics from a structured local review.",
        ],
        "next_action": next_action,
        "suggested_next_stage": None,
        "patch_instructions": blocking,
        "source_review_files": [
            str(path.relative_to(stage))
            for path in [packet_path, validation_path, metrics_path, claim_path]
            if path.exists()
        ],
    }
    target = stage / ".loop" / "reviewer_results" / _role_output_name(role_key)
    write_json(target, payload)
    return target


def run_local_reviewer_agents(stage: Path, mode: str | None = None, review_scope: str = "routine_branch") -> list[Path]:
    return [
        run_local_reviewer_agent(stage, role_key, mode=mode, review_scope=review_scope)
        for role_key in REQUIRED_REVIEWERS
    ]


def build_reviewer_agent_prompt(
    stage: Path,
    mode: str = "codex_subagent",
    reviewer_role: str = "GeneralReviewer",
    review_scope: str = "routine_branch",
) -> Path:
    if mode not in REVIEW_MODES:
        raise ValueError(f"Unsupported review mode {mode!r}; expected one of {REVIEW_MODES}")
    if reviewer_role != "GeneralReviewer" and reviewer_role not in REVIEWER_PROFILES:
        raise ValueError(f"Unsupported reviewer role {reviewer_role!r}")
    packet_path = stage / "review_packet.md"
    if not packet_path.exists():
        raise FileNotFoundError(f"Missing review packet: {packet_path}")

    validation_hint = stage / ".loop" / "validation_summary.json"
    profile = REVIEWER_PROFILES.get(
        reviewer_role,
        {
            "focus": "general symbolic review packet audit",
            "questions": [
                "Is the algebra exact according to exported validation gates?",
                "Is the simplification real?",
                "Did protected regressions survive?",
                "Is the claim boundary honest?",
            ],
        },
    )
    role_questions = "\n".join(f"- {question}" for question in profile["questions"])
    target_name = "reviewer_agent_prompt.md" if reviewer_role == "GeneralReviewer" else f"reviewer_agent_prompt.{reviewer_role}.md"
    prompt = f"""# Symbolic Reviewer-Agent Audit

## Mode

`{mode}`

## Reviewer Role

`{reviewer_role}`

## Review Scope

`{review_scope}`

Routine branches should use Codex subagent reviewers. Major checkpoints, paper claims, and scientific-route decisions should also receive a separate web-GPT scientific audit.

## Suggested Codex Custom-Agent Settings

```text
sandbox_mode = "read-only"
model_reasoning_effort = "high"
```

## Role

You are an independent symbolic reviewer. You audit the review packet and selected validation artifacts, then return structured JSON matching `schemas/review_result.schema.json`.

Your focus:

```text
{profile["focus"]}
```

## Hard Boundary

- Do not edit code, symbolic outputs, validation files, checkpoints, or reports.
- Do not replace verifier scripts.
- Do not claim mathematical proof from narrative alone.
- If `validation_summary.overall_gate != "PASS"`, recommend against freezing.

## Files To Read

- `{packet_path}`
- `{validation_hint}` if present
- `.loop/metrics.json` if present
- `CLAIM_BOUNDARY.md` if present

## Audit Questions

1. Is the algebra exact according to exported validation gates?
2. Is the simplification real, or only a relabeling?
3. Were stale, pre-IBP, or wrong-version tables mixed in?
4. Did protected regressions survive?
5. Is the claim boundary honest?
6. Should this stage freeze, patch, fail, or open a next stage?

## Role-Specific Questions

{role_questions}

## Required Output

Return JSON only. The main agent will save role-specific results under `.loop/reviews/` and aggregate them into `.loop/review_result.json`.

```json
{{
  "verdict": "PASS | PASS_WITH_CAVEAT | NEEDS_PATCH | FAILED",
  "stage_name": "{stage.name}",
  "reviewer_role": "{reviewer_role}",
  "review_scope": "{review_scope}",
  "mathematical_status": {{
    "exact_reconstruction": true,
    "simplification_real": true,
    "regression_preserved": true,
    "overclaim_detected": false
  }},
  "blocking_issues": [],
  "nonblocking_caveats": [],
  "allowed_claims": [],
  "forbidden_claims": [],
  "next_action": "FREEZE | PATCH | FAIL | OPEN_NEXT_STAGE",
  "suggested_next_stage": null,
  "patch_instructions": []
}}
```
"""
    target = stage / target_name
    write_text(target, prompt)
    return target


def build_reviewer_agent_prompts(stage: Path, mode: str = "codex_subagent", review_scope: str = "routine_branch") -> list[Path]:
    return [
        build_reviewer_agent_prompt(stage, mode=mode, reviewer_role=role, review_scope=review_scope)
        for role in REVIEWER_PROFILES
    ]
