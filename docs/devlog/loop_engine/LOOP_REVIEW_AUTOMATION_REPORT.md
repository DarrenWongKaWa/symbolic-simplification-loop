# Loop Review Automation Report

Branch: `loop_002_codex_subagent_reviewer_mode`

## Goal

This branch removes the manual copy-paste review bottleneck for routine Loop
Engineering stages.  It adds a Codex-local structured reviewer mode that reads
the stage packet, validation summary, metrics, and optional claim boundary, then
emits machine-readable reviewer JSON files for aggregation by the decision
engine.

This branch only changes loop infrastructure.  It does not modify
`sigma_abc` physics, does not continue any `sigma_abc` stage, and does not start
tensorial kernel fusion or tensorial IBP reduction.

## Implemented Review Modes

The loop now supports a review-mode setting:

```json
{
  "review": {
    "mode": "manual_chatgpt | codex_subagent | openai_api"
  }
}
```

The default mode is:

```text
codex_subagent
```

Current operational status:

| Mode | Status | Purpose |
| --- | --- | --- |
| `codex_subagent` | implemented | Routine local structured stage review |
| `manual_chatgpt` | supported as a configuration option | External human/GPT checkpoint review |
| `openai_api` | reserved | Future API-backed reviewer execution |

## Reviewer Roles

Three read-only reviewer roles are now defined:

| Reviewer | Template | Primary audit focus |
| --- | --- | --- |
| AlgebraReviewer | `skill/algebra_reviewer.md` | exact reconstruction, validation gates, row/provenance consistency |
| PhysicsReviewer | `skill/physics_reviewer.md` | basis conventions, claim boundary, overclaim risks |
| SoftwareReviewer | `skill/software_reviewer.md` | repo hygiene, stale inputs, missing files, reproducibility |

Each reviewer reads:

```text
review_packet.md
.loop/validation_summary.json
.loop/metrics.json
CLAIM_BOUNDARY.md, if present
```

Each reviewer writes:

```text
.loop/reviewer_results/algebra_reviewer.json
.loop/reviewer_results/physics_reviewer.json
.loop/reviewer_results/software_reviewer.json
```

The aggregate reviewer output is:

```text
.loop/review_result.json
```

## Scripts Added Or Updated

| File | Role |
| --- | --- |
| `scripts/run_reviewer_agents.py` | Runs the three local structured reviewer roles and writes per-reviewer JSON |
| `scripts/aggregate_review_results.py` | Aggregates reviewer outputs into `.loop/review_result.json` |
| `scripts/run_full_loop_smoke_test.py` | Runs the smoke stage using `codex_subagent` review mode |
| `loop_engine/reviewer.py` | Implements review-mode loading, local reviewer execution, and strict aggregation |
| `loop_config.json` | Sets default review mode to `codex_subagent` |

## Decision Engine Behavior

The decision engine now combines:

```text
.loop/validation_summary.json
.loop/review_result.json
```

The safety policy is:

| Condition | Result |
| --- | --- |
| validation FAIL, reviewer PASS | freeze blocked |
| validation PASS, reviewer PASS | freeze allowed |
| validation PASS, reviewer PASS_WITH_CAVEAT | checkpoint freeze allowed with caveat |
| reviewer disagreement | aggregate to `PASS_WITH_CAVEAT` or `NEEDS_PATCH` |
| missing required reviewer output | aggregate to `NEEDS_PATCH`; freeze blocked |

## Tests Added

`tests/test_codex_reviewer_mode.py` covers:

1. validation failure overrides reviewer pass;
2. `PASS_WITH_CAVEAT` can freeze only when validation passes;
3. reviewer disagreement aggregates to `PASS_WITH_CAVEAT` or `NEEDS_PATCH`;
4. missing reviewer output blocks freeze;
5. `codex_subagent` mode generates reviewer results and an aggregate review.

## Full Smoke Test Result

The smoke test uses the mock symbolic stage:

```text
Old = x^2 + 2 x + 1
New = (x + 1)^2
Old - New = 0
```

Generated files include:

```text
STAGE_PLAN.md
EXECUTION_REPORT.md
.loop/validation_summary.json
review_packet.md
.loop/reviewer_results/algebra_reviewer.json
.loop/reviewer_results/physics_reviewer.json
.loop/reviewer_results/software_reviewer.json
.loop/review_result.json
.loop/decision.json
.loop/checkpoint_manifest.json
```

Smoke-test decision:

```text
DecisionAction -> FREEZE
freeze_allowed -> true
```

Checkpoint freezing created:

```text
smoke_projects/mock_polynomial_loop/stages/000_polynomial_identity/.loop/checkpoint_manifest.json
```

## Acceptance Checklist

| Acceptance item | Status |
| --- | --- |
| pytest PASS | verified by smoke and final test run |
| schema validation PASS | verified for smoke-stage loop JSON files |
| mock stage runs without manual ChatGPT review | PASS |
| reviewer_results/*.json created | PASS |
| aggregate review_result.json created | PASS |
| decision engine returns FREEZE for mock PASS case | PASS |
| validation failure blocks freeze | covered by test |

## Claim Boundary

Allowed:

```text
The loop infrastructure now supports a Codex-local structured reviewer mode for
routine branch review.
```

Allowed:

```text
The mock symbolic stage can pass validation, pass local structured review, and
freeze a checkpoint without manual ChatGPT copy-paste review.
```

Not allowed:

```text
The Codex-local reviewer replaces final scientific checkpoint review.
```

Not allowed:

```text
This branch proves any new sigma_abc physics.
```

Not allowed:

```text
This branch starts sigma_abc simplification, kernel fusion, or IBP reduction.
```

