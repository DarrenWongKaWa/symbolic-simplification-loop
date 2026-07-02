# STAGE_PLAN.md -- 002_raw_import_and_convention_audit

## Goal

Register the frozen raw generator checkpoint as official raw input and audit tensor/frequency/Gamma/projection conventions.

## Required Caveat

Stage 001b caveat preserved: DCProjectionTo1D is INHERITED_PASS from finite-frequency xxx projection plus the archived 1D DC notebook pipeline, not a direct full tensorial DC-series PASS.

## Expected Outputs

- `sigma_abc/HUMAN_TASK_BRIEF.md`
- `sigma_abc/raw_input_manifest.json`
- `sigma_abc/tensor_index_convention.md`
- `sigma_abc/frequency_convention.md`
- `sigma_abc/gamma_convention.md`
- `sigma_abc/projection_rule_xxx.md`

## Forbidden Work

- Start sector decomposition
- Start kernel fusion
- Start IBP
- Claim full tensorial correctness
