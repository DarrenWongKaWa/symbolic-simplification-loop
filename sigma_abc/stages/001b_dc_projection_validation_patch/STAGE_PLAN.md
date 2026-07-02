# STAGE_PLAN.md -- 001b_dc_projection_validation_patch

## Goal

Patch the Stage 001 DC projection validation strategy without weakening scientific safety.

## Inputs

- Stage 001 raw generator outputs.
- `abc_w1_w2_1D.txt`
- `Sigma_abc_dc_1D.txt`
- `DC limit - Gamma Expansion -1D.nb`

## Validation Logic

Overall gate may pass only if:

```text
FiniteFrequencyProjectionTo1D -> PASS
DCProjectionTo1D -> PASS or INHERITED_PASS
```

## Forbidden Work

- No sector decomposition.
- No tensorial kernel fusion.
- No tensorial IBP.
- No full tensorial correctness claim.
