# Structured Reviewer Packet: 000_polynomial_identity

## Stage Plan

# Stage Plan

## Stage

`000_polynomial_identity`

## Goal

Verify the mock symbolic identity

```text
Old = x^2 + 2 x + 1
New = (x + 1)^2
Old - New = 0
```

through the full symbolic-simplification loop lifecycle.

## Input Snapshots

- `input_snapshots/mock_old_expression.txt`
- `input_snapshots/sigma_xxx_benchmark_metadata.json`

## Expected Outputs

- `output/mock_new_expression.txt`
- `output/mock_identity_difference.json`
- `.loop/validation_summary.json`
- `review_packet.md`
- `.loop/review_result.json`
- `.loop/decision.json`
- `.loop/checkpoint_manifest.json`

## Allowed Transformations

- Exact polynomial expansion.

## Forbidden Transformations

- Do not perform `sigma_abc` simplification.
- Do not claim physics progress from this smoke test.

## Validation Identity

```text
OldExpression - NewExpression == 0
```

## Protected Regressions

- `examples/sigma_xxx_case/benchmark_sigma_xxx_projection.json` is registered as benchmark metadata.

## Claim Boundary

Allowed:

- The loop infrastructure validates, reviews, decides, and freezes a mock stage.

Forbidden:

- The `sigma_abc` symbolic simplification has started.
- The smoke test proves any physics simplification identity.

## Next-Stage Trigger

No next scientific stage is opened by this smoke test.


## Execution Report

# Execution Report

## Stage Name

`000_polynomial_identity`

## Files Created

- `input_snapshots/mock_old_expression.txt`
- `output/mock_new_expression.txt`
- `output/mock_identity_difference.json`
- `.loop/validation_summary.json`

## Scripts Run

- `scripts/run_full_loop_smoke_test.py`

## Input Snapshots Used

- `input_snapshots/mock_old_expression.txt`
- `input_snapshots/sigma_xxx_benchmark_metadata.json`

## Main Outputs

- `(x + 1)^2`

## Validation Results

```text
Old - New = 0
overall_gate: PASS
```

## Metrics Before / After

```json
{
  "before": {
    "terms": 3
  },
  "after": {
    "expanded_terms": 3,
    "difference": 0
  }
}
```

## Known Caveats

- This is an infrastructure smoke test, not a physics simplification.

## Next Recommended Action

`BUILD_REVIEW_PACKET`


## Key Files

- `input_snapshots/mock_old_expression.txt`
- `input_snapshots/sigma_xxx_benchmark_metadata.json`
- `output/mock_identity_difference.json`
- `output/mock_new_expression.txt`
- `validation/validation_summary.json`
- `reports/sigma_xxx_benchmark_registration.md`

## Metrics Before / After

```json
{
  "after": {
    "difference": "0",
    "expanded_terms": 3,
    "expression": "(x + 1)^2"
  },
  "before": {
    "expression": "x^2 + 2 x + 1",
    "terms": 3
  },
  "deltas": {
    "identity_difference": "0"
  },
  "notes": [
    "Toy exact identity used to smoke-test loop lifecycle."
  ],
  "stage_name": "000_polynomial_identity"
}
```

## Validation Summary

```json
{
  "caveats": [
    "Infrastructure-only smoke test; no physics simplification was run."
  ],
  "checks": [
    {
      "actual": "0",
      "expected": "0",
      "gate": "PASS",
      "name": "mock_polynomial_identity",
      "new": "(x + 1)^2",
      "old": "x^2 + 2 x + 1"
    }
  ],
  "identity_type": "OldMinusNewZero",
  "overall_gate": "PASS",
  "protected_regressions": [
    {
      "gate": "PASS",
      "name": "sigma_xxx_benchmark_metadata_registered",
      "source": "examples/sigma_xxx_case/benchmark_sigma_xxx_projection.json"
    }
  ],
  "stage_name": "000_polynomial_identity"
}
```

## Claim Boundary

# Claim Boundary

## Allowed Claims

- The mock polynomial stage validates exactly.
- The loop infrastructure can generate review packets, structured review results, decisions, and checkpoints.

## Forbidden Claims

- `sigma_abc` simplification has started.
- Any physical conductivity formula has been simplified by this smoke test.

## Caveats

- This stage uses a toy polynomial identity only.


## Reviewer Mode

Default V1 mode:

```text
codex_subagent
```

Manual ChatGPT and OpenAI API review are optional modes.

Routine branch review should use read-only Codex subagents:

```text
AlgebraReviewer   algebraic exactness, row counts, validation gates
PhysicsReviewer   basis, symmetry, conventions, claim boundary
SoftwareReviewer  stale files, table provenance, reproducibility
```

Major checkpoints, paper claims, final scientific audits, and next-branch scientific-route decisions should also receive a separate web-GPT audit.

This symbolic reviewer-agent audit is not the same as Codex app `/review`, which is for code diffs and inline comments.

## Reviewer Hard Boundary

- Do not edit code or symbolic outputs.
- Do not replace verifier scripts.
- Audit exactness gates, stale inputs, protected regressions, claim boundary, and next action.
- If validation failed, recommend against freezing even if the narrative looks plausible.

## Reviewer Questions

1. Is the algebra exact?
2. Is the simplification real?
3. Were old or stale tables mixed in?
4. Did protected regressions survive?
5. Is the claim boundary honest?
6. Should this branch freeze, patch, fail, or open next stage?
