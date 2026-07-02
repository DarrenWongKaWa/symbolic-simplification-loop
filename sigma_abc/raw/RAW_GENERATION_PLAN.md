# RAW_GENERATION_PLAN

## Goal

Generate or transcribe `raw/raw_sigma_abc.wl` in a future branch.

## Recommended Next Stage

```text
sigma_abc_001_raw_generation_or_transcription
```

## Required Steps

1. Select one source route from `RAW_SOURCE_OPTIONS.md`.
2. Declare tensor, band, thermal, and finite-`Gamma` conventions.
3. Produce a Wolfram Language association satisfying
   `RAW_SIGMA_ABC_CONTRACT.md`.
4. Keep `Expression -> Missing["NotGeneratedYet"]` until a real expression is
   available.
5. Run contract validation.
6. Prepare projection benchmark machinery, but do not claim success until the
   raw expression exists.

## Forbidden During This Stage

- No simplification of the tensorial expression.
- No dropping of center, pair, loop, or residual sectors.
- No claim of equality to external compact kernels.

