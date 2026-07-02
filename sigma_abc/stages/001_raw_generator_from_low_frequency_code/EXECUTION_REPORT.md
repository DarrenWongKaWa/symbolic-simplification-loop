# EXECUTION_REPORT.md -- 001_raw_generator_from_low_frequency_code

## Summary

Stage 001 generated a candidate projection-preserving tensorial wrapper from the `low_frequency` 1D sources.

## Generated Files

- `scripts/thermal_rho_kernels.wl`
- `scripts/generate_raw_sigma_abc.wl`
- `raw/raw_sigma_abc.wl`
- `raw/raw_sigma_abc_finite_frequency.wl`
- `raw/raw_sigma_abc_dc.wl`
- `raw/raw_sigma_abc_manifest.json`

## Validation Result

- Finite-frequency xxx projection: `PASS`
- Direct DC source xxx projection: `PASS`
- DC series xxx projection: `TIMEOUT`
- Overall gate: `FAIL`

## Stop Decision

Because the DC series benchmark did not pass, the overnight chain stops here.
