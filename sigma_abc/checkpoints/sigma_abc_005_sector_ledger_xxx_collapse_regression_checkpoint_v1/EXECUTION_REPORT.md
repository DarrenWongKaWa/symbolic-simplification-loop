# EXECUTION_REPORT.md -- 005_sector_ledger_xxx_collapse_regression

## Summary

Check that the tensorial sector ledger collapses to the known projected 1D xxx source structure.

## Validation Gate

```json
{
  "stage_name": "005_sector_ledger_xxx_collapse_regression",
  "overall_gate": "PASS",
  "identity_type": "ProjectionRegression",
  "checks": [
    {
      "name": "SectorLedgerXXXCollapse",
      "expected": "PASS",
      "actual": "PASS",
      "gate": "PASS"
    },
    {
      "name": "RawProjectionStillPASS",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    },
    {
      "name": "DCProjectionStillInheritedPASS",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    },
    {
      "name": "SectorProvenancePreserved",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    },
    {
      "name": "NoSimplificationStarted",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    }
  ],
  "SectorLedgerXXXCollapse": "PASS",
  "RawProjectionStillPASS": true,
  "DCProjectionStillInheritedPASS": true,
  "SectorProvenancePreserved": true,
  "NoSimplificationStarted": true,
  "caveats": [
    "Stage 001b caveat preserved: DCProjectionTo1D is INHERITED_PASS from finite-frequency xxx projection plus the archived 1D DC notebook pipeline, not a direct full tensorial DC-series PASS.",
    "This is a raw-level xxx collapse regression, not final kernel-level sigma_xxx equality."
  ]
}
```

## Caveat

Stage 001b caveat preserved: DCProjectionTo1D is INHERITED_PASS from finite-frequency xxx projection plus the archived 1D DC notebook pipeline, not a direct full tensorial DC-series PASS.
