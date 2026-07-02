# OVERNIGHT_RUN_FAILED_REPORT.md

## Status

The safe overnight chain stopped at Stage 001.

## Blocking Gate

`DCProjectionTo1D` did not pass. The finite-frequency expression parsed, but the required DC series projection

```text
omega2 -> -omega1
SeriesCoefficient[..., {omega1,0,2}, 2]
```

hit the configured timeout.

## Actions Taken

- Generated candidate raw tensorial wrapper from `low_frequency/abc_w1_w2_1D.txt`.
- Generated candidate DC wrapper from `low_frequency/Sigma_abc_dc_1D.txt`.
- Preserved all source snapshots and hashes.
- Wrote validation, review, and decision artifacts.
- Stopped before Stage 002.

## Not Performed

- No raw import as official tensorial input.
- No tensorial sector decomposition.
- No tensorial kernel fusion.
- No tensorial IBP reduction.
- No full tensorial correctness claim.

## Recommended Next Step

Rerun Stage 001 after optimizing or replacing the DC series projection benchmark.
