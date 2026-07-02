# EXECUTION_REPORT.md -- 004_tensorial_raw_sector_decomposition_ledger

## Summary

Decompose the raw tensorial expression into raw sector ledgers without simplifying.

## Validation Gate

```json
{
  "stage_name": "004_tensorial_raw_sector_decomposition_ledger",
  "overall_gate": "PASS",
  "identity_type": "OldMinusNewZero",
  "checks": [
    {
      "name": "SectorDecompositionExists",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    },
    {
      "name": "RawMinusSectorSum",
      "expected": 0,
      "actual": 0,
      "gate": "PASS"
    },
    {
      "name": "SectorCountsRecorded",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    },
    {
      "name": "NoKernelFusionStarted",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    },
    {
      "name": "NoIBPStarted",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    }
  ],
  "SectorDecompositionExists": true,
  "RawMinusSectorSum": 0,
  "SectorCountsRecorded": true,
  "NoKernelFusionStarted": true,
  "NoIBPStarted": true,
  "SectorCounts": {
    "center/contact sector": 93,
    "pair/two-band sector": 912,
    "loop/three-band sector": 288,
    "unclassified": 0,
    "total_rows": 1293
  },
  "caveats": [
    "Stage 001b caveat preserved: DCProjectionTo1D is INHERITED_PASS from finite-frequency xxx projection plus the archived 1D DC notebook pipeline, not a direct full tensorial DC-series PASS.",
    "Sector labels are raw row-provenance groups, not physical kernel fusion."
  ]
}
```

## Caveat

Stage 001b caveat preserved: DCProjectionTo1D is INHERITED_PASS from finite-frequency xxx projection plus the archived 1D DC notebook pipeline, not a direct full tensorial DC-series PASS.
