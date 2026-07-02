# STAGE_PLAN.md -- 005_sector_ledger_xxx_collapse_regression

## Goal

Check that the tensorial sector ledger collapses to the known projected 1D xxx source structure.

## Required Caveat

Stage 001b caveat preserved: DCProjectionTo1D is INHERITED_PASS from finite-frequency xxx projection plus the archived 1D DC notebook pipeline, not a direct full tensorial DC-series PASS.

## Expected Outputs

- `validation/sector_ledger_xxx_collapse_validation.wl`
- `reports/sector_ledger_xxx_collapse_report.md`
- `output/sector_ledger_xxx_projection_summary.json`

## Forbidden Work

- Kernel-level projection benchmark
- Kernel fusion
- IBP reduction
- Full tensorial correctness claim
