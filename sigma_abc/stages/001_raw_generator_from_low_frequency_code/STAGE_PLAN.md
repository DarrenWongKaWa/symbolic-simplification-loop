# STAGE_PLAN.md -- 001_raw_generator_from_low_frequency_code

## Goal

Build a candidate tensorial `raw_sigma_abc` generator by abstracting the existing finite-frequency 1D `low_frequency` code.

## Inputs

- `abc_w1_w2_1D.txt`
- `Sigma_abc_dc_1D.txt`
- `DC limit - Gamma Expansion -1D.nb`
- `band_sum_abstractor.wl`

## Allowed Work

- Extract thermal rho kernel conventions.
- Lift 1D matrix elements into directional tensorial wrappers.
- Validate `xxx` projection against the archived 1D expressions.

## Forbidden Work

- No tensorial kernel fusion.
- No tensorial IBP reduction.
- No full tensorial correctness claim.

## Hard Gate

Continue only if both finite-frequency and DC `xxx` projection checks pass.
