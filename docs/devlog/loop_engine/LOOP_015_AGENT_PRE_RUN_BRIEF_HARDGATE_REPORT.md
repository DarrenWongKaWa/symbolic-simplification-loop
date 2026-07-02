# Loop 015 — B-hardgate Pre-run Brief

## Status

PASS.

The hard-gate layer executes *after* the B-lite brief is materialized
and decides `execution_allowed` deterministically — no reviewer
consultation, no LLM involvement, no downgrade for human override.
On stage 010 the gate returned `execution_allowed=true` with
`reviewer_consulted=false`, exactly as required.

```text
python3 scripts/check_pre_run_gate.py \
  --stage autonomous_runs/sigma_abc/stages/sigma_abc_010_pair_kernel_fusion_pilot \
  --profile profiles/sigma_abc_pair_kernel_fusion_pilot.yaml
-> exit 0; .loop/pre_run_gate_result.json materialized
```

`sigma_abc` physics NOT modified. No 012C promotion, Stage 013
global pre-IBP assembly, tensorial IBP, or total-derivative reduction
started. Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## What Loop 015 Is

A *hard* pre-run gate that decides whether the executor may proceed.
It evaluates the brief produced by Loop 014 plus the profile plus the
frozen claim boundary and emits a single verdict:

```text
decision   = PRE_RUN_GATE_PASSED  |  PRE_RUN_GATE_FAILED
allowed    = True | False
reviewer   = False (always — gate is deterministic)
```

The gate must block (and refuse to call any reviewer) if any of:

```text
- pre_run_brief.json missing
- pre_run_brief.stage_id != current stage_id
- profile_id mismatch
- profile_match.in_approved_stage_ids != True
- profile_match.dependencies_covered != True
- profile_match.expected_outputs_covered != True
- profile_match.forbidden_actions_covered != True
- task_understanding.claim_boundary_acknowledged != True
- task_understanding.caveats_acknowledged does not contain the
  permanent caveat:
  "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."
- pre_run_brief_audit.hard_stop == True
```

## Artifacts

```text
schemas/pre_run_gate_result.schema.json          # contract
loop_engine/pre_run_gate.py                      # check_pre_run_gate()
scripts/check_pre_run_gate.py                    # CLI
tests/test_loop014_017_pre_run_identity_traceability.py   # coverage
```

Runtime artifact on stage 010:

```text
.loop/pre_run_gate_result.json                   # verdict
```

## Observed Behavior on Stage 010

```text
pre_run_gate_result.stage_id          = sigma_abc_010_pair_kernel_fusion_pilot
pre_run_gate_result.profile_id        = sigma_abc_pair_kernel_fusion_pilot
pre_run_gate_result.gate              = WARN
pre_run_gate_result.execution_allowed = True
pre_run_gate_result.reviewer_consulted = False
pre_run_gate_result.blocking_reasons  = []
pre_run_gate_result.warnings          = ["expected outputs incomplete"]
```

The `reviewer_consulted=False` invariant is the single most important
contract here: even when the brief has WARN-level issues, the gate
must NOT escalate to L1/L2 reviewers. Decision authority stays with
the deterministic completion matrix and human signoff, which is what
Loop 013 locked in.

## Blocking-Rule Coverage

The 014–017 test file exercises three blocking paths:

```text
test_pre_run_gate_blocks_invalid_and_allows_valid_without_reviewer
  1) brief absent             -> execution_allowed=False, reviewer_consulted=False
  2) valid brief              -> execution_allowed=True,  reviewer_consulted=False
  3) stage_id mismatch        -> execution_allowed=False, reviewer_consulted=False
```

All three pass deterministically; no reviewer is ever instantiated.

## Schema Validation

```text
loop_engine.schemas.validate_with_schema(
    pre_run_gate_result_payload, "pre_run_gate_result"
)
-> OK
```

## Hard-Stop Boundary

The 015 gate is intentionally narrow. It does NOT replace any of:

```text
- completion matrix
- human_signoff.yaml
- freeze_preconditions
- identity traceability gate (Loop 017)
- completion-matrix completion gate (Loop 013)
```

It only decides whether the executor may *begin* stage work. It must
not decide correctness, claims, or freeze eligibility.

## Remaining Non-goals

Loop 015 must not:

```text
- Consult any L1/L2 reviewer.
- Weaken freeze_preconditions.
- Weaken human_signoff requirement.
- Override a hard-stop from Loop 014 audit.
- Touch sigma_abc physics.
```

## Next

Proceed to Loop 016 (scientific identity rendering), which produces
the md/tex identity section embedded in stage summaries.