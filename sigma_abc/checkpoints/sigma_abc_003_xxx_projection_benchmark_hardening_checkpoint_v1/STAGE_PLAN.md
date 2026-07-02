# STAGE_PLAN.md -- 003_xxx_projection_benchmark_hardening

## Goal

Register sigma_xxx final checkpoint as the future projection benchmark.

## Required Caveat

Stage 001b caveat preserved: DCProjectionTo1D is INHERITED_PASS from finite-frequency xxx projection plus the archived 1D DC notebook pipeline, not a direct full tensorial DC-series PASS.

## Expected Outputs

- `sigma_abc/benchmarks/sigma_xxx_projection_benchmark.md`
- `sigma_abc/benchmarks/benchmark_manifest.json`
- `sigma_abc/benchmarks/sigma_xxx_reference_summary.json`

## Forbidden Work

- Run final kernel-level projection benchmark prematurely
- Claim full tensorial correctness
