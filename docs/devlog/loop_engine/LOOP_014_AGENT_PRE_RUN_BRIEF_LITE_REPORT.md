# Loop 014 — B-lite Agent Pre-run Brief

## Status

PASS.

The B-lite pre-run brief layer is wired into the autonomous runner,
schema-validating on the existing sigma_abc stage 010 fixture, and
behaving exactly as a *lite* (warn-only) gate: forbidden-intent still
hard-stops; missing-deps / missing-expected-outputs only warn.

```text
python3 scripts/build_pre_run_brief.py \
  --stage autonomous_runs/sigma_abc/stages/sigma_abc_010_pair_kernel_fusion_pilot \
  --profile profiles/sigma_abc_pair_kernel_fusion_pilot.yaml
-> exit 0; .loop/pre_run_brief.json materialized

python3 scripts/audit_pre_run_brief.py \
  --stage .../sigma_abc_010_pair_kernel_fusion_pilot \
  --profile profiles/sigma_abc_pair_kernel_fusion_pilot.yaml
-> exit 0; .loop/pre_run_brief_audit.json materialized; hard_stop = False
```

`sigma_abc` physics NOT modified. No 012C promotion, Stage 013
global pre-IBP assembly, tensorial IBP, or total-derivative
reduction started. Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## What Loop 014 Is

A *lite* gate that runs **before any executor work** on a stage. It
materializes a structured declaration of the agent's task understanding
(goal restated, expected outputs declared, dependencies acknowledged,
forbidden actions listed, claim boundary acknowledged, caveats
acknowledged). It must:

- Validate against `schemas/pre_run_brief.schema.json`.
- Surface warnings for missing expected outputs / missing dependencies /
  missing caveats / unacknowledged claim boundary.
- Hard-stop **only** when the brief itself declares an explicit
  forbidden intent (IBP, total-derivative reduction, candidate
  promotion, full tensorial sigma_abc correctness claim, profile
  bypassing).

The brief is *not* a reviewer call. It does not invoke any L1 / L2
reviewer.

## Artifacts

```text
schemas/pre_run_brief.schema.json                        # contract
loop_engine/pre_run_brief.py                             # build + audit + write
scripts/build_pre_run_brief.py                           # CLI
scripts/audit_pre_run_brief.py                           # CLI
templates/PRE_RUN_BRIEF.template.md                      # template
templates/AGENT_SELF_UNDERSTANDING.template.md           # template
tests/test_loop014_017_pre_run_identity_traceability.py  # 7 case coverage
```

Runtime artifacts on stage 010:

```text
.loop/pre_run_brief.json                                 # brief payload
.loop/pre_run_brief_audit.json                           # audit verdict
reports/agent_self_understanding.md                      # human-readable
```

## Observed Behavior on Stage 010 (sigma_abc_pair_kernel_fusion_pilot)

```text
profile_id                              = sigma_abc_pair_kernel_fusion_pilot
stage_id                                = sigma_abc_010_pair_kernel_fusion_pilot
task_understanding.claim_boundary_acknowledged   = True
task_understanding.caveats_acknowledged          = [
  "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."
]
task_understanding.forbidden_actions             = [
  "IBP",
  "candidate promotion",
  "full tensorial sigma_abc correctness claim",
  "global assembly",
  "total derivative reduction"
]
task_understanding.expected_outputs              = []
profile_match.in_approved_stage_ids              = True
profile_match.dependencies_covered               = True
profile_match.expected_outputs_covered            = True
profile_match.forbidden_actions_covered          = True
```

Audit:

```text
pre_run_brief_audit.gate        = WARN
pre_run_brief_audit.hard_stop   = False
pre_run_brief_audit.warnings    = ["expected outputs incomplete"]
pre_run_brief_audit.blocking_reasons = []
```

The single WARN reflects that the brief payload's `expected_outputs`
list is empty for stage 010 — STAGE_PLAN uses bare `output/` paths.
This is a *content* warning only, not a hard-stop. The downstream
015 gate (Loop 015 report) handles the actual go/no-go decision.

## Hard-Stop Proof

The 014 test
`test_pre_run_brief_warns_and_hard_stops_explicit_forbidden_intent`
demonstrates the hard-stop branch: when the brief's
`task_understanding.goal_restated` is rewritten to

```text
"I will start IBP and claim full tensorial sigma_abc correctness."
```

the auditor reports `hard_stop=True, gate=FAIL`. With the profile-
derived brief on stage 010, no such forbidden intent is present, so
`hard_stop=False`.

## Schema Validation

```text
loop_engine.schemas.validate_with_schema(
    pre_run_brief_payload, "pre_run_brief"
)
-> OK
```

## Files Changed By This Loop

This loop did NOT modify the engine, schema, templates, or CLI scripts
beyond what already existed. The only material change since the prior
materialization on stage 010 was the post-Phase-1 refresh via the
existing CLI scripts. No new tests were added in this loop; the
existing 7-case test file already covers it (PASS).

## Remaining Non-goals

Loop 014 must not:

```text
- Replace the deterministic completion matrix.
- Bypass freeze_preconditions.
- Weaken the hard-stop on forbidden intent.
- Auto-promote any 012C candidate.
- Touch sigma_abc physics.
```

## Next

Proceed to Loop 015 (hard-gate), which uses the brief to decide
`execution_allowed`.