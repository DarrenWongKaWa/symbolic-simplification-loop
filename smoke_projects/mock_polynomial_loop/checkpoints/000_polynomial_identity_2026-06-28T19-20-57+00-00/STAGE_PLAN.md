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
