# Stage Plan

## Stage

`000_raw_contract`

## Goal

Define the raw `sigma_abc` expression contract, placeholders, source manifest,
generation plan, and protected `sigma_xxx` projection benchmark registration.

This stage must not create or invent `raw/raw_sigma_abc.wl`.

## Input Snapshots

- `../../raw/RAW_SIGMA_ABC_CONTRACT.md`
- `../../raw/raw_sigma_abc.template.wl`
- `../../benchmarks/sigma_xxx_projection_benchmark.md`

## Expected Outputs

- `../../raw/README.md`
- `../../raw/RAW_SOURCE_OPTIONS.md`
- `../../raw/RAW_SOURCE_MANIFEST.md`
- `../../raw/RAW_GENERATION_PLAN.md`
- `.loop/validation_summary.json`
- `review_packet.md`
- `.loop/review_result.json`
- `.loop/decision.json`

## Allowed Transformations

- Contract definition.
- Placeholder template creation using `Missing["NotGeneratedYet"]`.
- Benchmark metadata registration.
- Review-packet generation.

## Forbidden Transformations

- Generating `raw/raw_sigma_abc.wl`.
- Starting symbolic simplification.
- Claiming raw availability.
- Claiming full tensorial correctness.

## Validation Identity

```text
ContractReadyQ && !RawSigmaABCExists && RawGenerationNeeded
```

## Protected Regressions

- `sigma_xxx` projection benchmark metadata is registered.

## Claim Boundary

Allowed:

- Raw contract exists.
- Raw generation is needed.
- `sigma_xxx` benchmark is registered.

Forbidden:

- Raw `sigma_abc` exists.
- `sigma_abc` simplification has started.
- Full tensorial formula is correct.

## Next-Stage Trigger

Open raw generation or raw transcription stage after contract review.

