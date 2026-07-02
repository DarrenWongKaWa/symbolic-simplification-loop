# STAGE_PLAN.md -- 004_tensorial_raw_sector_decomposition_ledger

## Goal

Decompose the raw tensorial expression into raw sector ledgers without simplifying.

## Required Caveat

Stage 001b caveat preserved: DCProjectionTo1D is INHERITED_PASS from finite-frequency xxx projection plus the archived 1D DC notebook pipeline, not a direct full tensorial DC-series PASS.

## Expected Outputs

- `output/sector_decomposition.wl`
- `output/sector_ledger.csv`
- `output/sector_counts.json`
- `validation/sector_decomposition_validation.wl`
- `reports/sector_decomposition_report.md`

## Forbidden Work

- Kernel fusion
- IBP reduction
- Physical basis reduction
- Full tensorial correctness claim
