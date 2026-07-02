# Human Task Brief

## Project Name

`<project_name>`

## Scientific Target

Describe the expression or physical quantity to simplify.

## Raw Input Expression Location

`raw/<file-or-folder>`

## Desired Physical Basis

- `<basis object 1>`
- `<basis object 2>`

## Known Benchmark

State exact symbolic or numerical regressions that must survive.

## Allowed Operations

- Algebraic simplification with exact reconstruction.
- Integration by parts only with exported primitive `F`.
- Symmetry reductions only after convention and parity checks.

## Forbidden Operations

- Dropping terms by intuition.
- Mixing stale pre-IBP and post-IBP tables.
- Claiming model-specific cancellation as a general identity.

## Claim Boundary

Allowed claims:

- `<claim>`

Forbidden claims:

- `<forbidden claim>`

## Stopping Criteria

- Validation gate fails.
- Protected regression fails.
- Structured reviewer verdict is `NEEDS_PATCH` or `FAILED`.
- `STOP` file exists.
