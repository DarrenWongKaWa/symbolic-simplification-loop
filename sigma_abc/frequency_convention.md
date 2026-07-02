# Frequency Convention

The finite-frequency source uses two external frequencies, `omega1` and `omega2`.

The inherited 1D DC pipeline records:

```text
omega2 -> -omega1
SeriesCoefficient[Series[..., {omega1,0,2}], 2]
```

Stage 001b caveat preserved: DCProjectionTo1D is INHERITED_PASS from finite-frequency xxx projection plus the archived 1D DC notebook pipeline, not a direct full tensorial DC-series PASS.
