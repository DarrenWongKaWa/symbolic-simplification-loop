# Pair Kernel Fusion Pilot Report

## Scope

This stage performs a limited pair-sector-only kernel fusion pilot.  It operates
only on the frozen pair/two-band sector ledger from Stage 004 and the Stage 009
pair-basis refinement checkpoint.

## Fusion Rule

Rows are grouped by unordered pair-band family:

- `pair_bands_1_2`: 304 rows
- `pair_bands_1_3`: 304 rows
- `pair_bands_2_3`: 304 rows

## Validation

```text
PairSectorLoaded -> True
PairSectorRowCount -> 912
Stage009PairBasisLoaded -> True
PairRowsConserved -> True
PairFusionDifference -> 0
XXXPairProjectionRegression -> PASS
NoCenterSectorTouched -> True
NoLoopSectorTouched -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
NoFullTensorialClaim -> True
```

## Boundary

No center/contact sector rows are touched.  No loop/three-band sector rows are
touched.  No tensorial IBP, total-derivative reduction, global coupled solve, or
full tensorial correctness claim is introduced.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
