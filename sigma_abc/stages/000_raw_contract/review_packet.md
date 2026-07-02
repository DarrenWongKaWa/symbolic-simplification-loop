# Structured Reviewer Packet: 000_raw_contract

## Stage Plan

# Stage Plan

## Stage

`000_raw_contract`

## Goal

Define the raw `sigma_abc` expression contract, placeholders, source manifest,
generation plan, and protected `sigma_xxx` projection benchmark registration.

This stage must not create or invent `raw/raw_sigma_abc.wl`.

## Input Snapshots

- `../../raw/RAW_SIGMA_ABC_CONTRACT.md`
- `../../raw/raw_sigma_abc.template.wl`
- `../../benchmarks/sigma_xxx_projection_benchmark.md`

## Expected Outputs

- `../../raw/README.md`
- `../../raw/RAW_SOURCE_OPTIONS.md`
- `../../raw/RAW_SOURCE_MANIFEST.md`
- `../../raw/RAW_GENERATION_PLAN.md`
- `.loop/validation_summary.json`
- `review_packet.md`
- `.loop/review_result.json`
- `.loop/decision.json`

## Allowed Transformations

- Contract definition.
- Placeholder template creation using `Missing["NotGeneratedYet"]`.
- Benchmark metadata registration.
- Review-packet generation.

## Forbidden Transformations

- Generating `raw/raw_sigma_abc.wl`.
- Starting symbolic simplification.
- Claiming raw availability.
- Claiming full tensorial correctness.

## Validation Identity

```text
ContractReadyQ && !RawSigmaABCExists && RawGenerationNeeded
```

## Protected Regressions

- `sigma_xxx` projection benchmark metadata is registered.

## Claim Boundary

Allowed:

- Raw contract exists.
- Raw generation is needed.
- `sigma_xxx` benchmark is registered.

Forbidden:

- Raw `sigma_abc` exists.
- `sigma_abc` simplification has started.
- Full tensorial formula is correct.

## Next-Stage Trigger

Open raw generation or raw transcription stage after contract review.



## Execution Report

# Execution Report

## Stage Name

`000_raw_contract`

## Files Created

- `sigma_abc/HUMAN_TASK_BRIEF.md`
- `sigma_abc/raw/README.md`
- `sigma_abc/raw/RAW_SIGMA_ABC_CONTRACT.md`
- `sigma_abc/raw/raw_sigma_abc.template.wl`
- `sigma_abc/raw/RAW_SOURCE_OPTIONS.md`
- `sigma_abc/raw/RAW_SOURCE_MANIFEST.md`
- `sigma_abc/raw/RAW_GENERATION_PLAN.md`
- `sigma_abc/benchmarks/sigma_xxx_projection_benchmark.md`
- `sigma_abc/stages/000_raw_contract/.loop/validation_summary.json`

## Scripts Run

- `scripts/build_review_packet.py`
- `scripts/build_reviewer_agent_prompts.py`
- `scripts/import_role_review_result.py`
- `scripts/aggregate_review_results.py`
- `scripts/decide_next_action.py`

## Input Snapshots Used

- `examples/sigma_xxx_case/benchmark_sigma_xxx_projection.json`
- `examples/sigma_xxx_case/final_checkpoint_manifest.json`

## Main Outputs

The branch establishes raw-contract readiness only:

```text
RawSigmaABCExists -> False
RawContractExists -> True
RawGenerationNeeded -> True
SigmaXXXBenchmarkRegistered -> True
```

## Known Caveats

- `raw/raw_sigma_abc.wl` does not exist.
- No `sigma_abc` simplification has started.

## Next Recommended Action

`sigma_abc_001_raw_generation_or_transcription`



## Key Files

- `input_snapshots/RAW_SIGMA_ABC_CONTRACT.md`
- `input_snapshots/raw_sigma_abc.template.wl`
- `input_snapshots/sigma_xxx_final_checkpoint_manifest.json`
- `input_snapshots/sigma_xxx_projection_benchmark.json`
- `validation/validation_summary.json`

## Metrics Before / After

```json
{
  "after": {
    "raw_contract": true,
    "raw_generation_needed": true,
    "raw_sigma_abc_exists": false,
    "sigma_xxx_benchmark_registered": true
  },
  "before": {
    "raw_contract": false,
    "raw_sigma_abc_exists": false
  },
  "deltas": {
    "contract_files_created": 5,
    "raw_expression_generated": 0
  },
  "notes": [
    "This is a contract-readiness stage only.",
    "No sigma_abc simplification has started."
  ],
  "stage_name": "000_raw_contract"
}
```

## Validation Summary

```json
{
  "caveats": [
    "PASS means contract readiness only, not raw availability.",
    "raw/raw_sigma_abc.wl has not been generated.",
    "sigma_abc simplification has not started."
  ],
  "checks": [
    {
      "actual": false,
      "expected": false,
      "gate": "PASS",
      "name": "RawSigmaABCExists"
    },
    {
      "actual": true,
      "expected": true,
      "gate": "PASS",
      "name": "RawContractExists"
    },
    {
      "actual": true,
      "expected": true,
      "gate": "PASS",
      "name": "RawGenerationNeeded"
    },
    {
      "actual": true,
      "expected": true,
      "gate": "PASS",
      "name": "SigmaXXXBenchmarkRegistered"
    },
    {
      "actual": "Missing[\"NotGeneratedYet\"]",
      "expected": "Missing[\"NotGeneratedYet\"]",
      "gate": "PASS",
      "name": "TemplateExpressionPlaceholder"
    }
  ],
  "contract_readiness": {
    "RawContractExists": true,
    "RawGenerationNeeded": true,
    "RawSigmaABCExists": false,
    "SigmaXXXBenchmarkRegistered": true
  },
  "identity_type": "NotApplicable",
  "next_recommended_stage": "sigma_abc_001_raw_generation_or_transcription",
  "overall_gate": "PASS",
  "protected_regressions": [
    {
      "gate": "REGISTERED_NOT_RUN",
      "name": "sigma_xxx_projection_benchmark",
      "reason": "No raw sigma_abc expression exists yet."
    }
  ],
  "stage_name": "000_raw_contract"
}
```

## Claim Boundary

# Claim Boundary

## Allowed Claims

- The raw `sigma_abc` contract exists.
- The placeholder template records `Expression -> Missing["NotGeneratedYet"]`.
- The `sigma_xxx` projection benchmark is registered for future use.
- The next stage should generate or transcribe the raw expression.

## Forbidden Claims

- `raw_sigma_abc.wl` exists.
- The raw tensorial expression has been imported.
- `sigma_abc` simplification has started.
- The full tensorial conductivity formula is correct.

## Caveats

- Current `PASS` means contract readiness only, not raw availability.



## Reviewer Mode

Default V1 mode:

```text
codex_subagent
```

Manual ChatGPT and OpenAI API review are optional modes.

Routine branch review should use read-only Codex subagents:

```text
AlgebraReviewer   algebraic exactness, row counts, validation gates
PhysicsReviewer   basis, symmetry, conventions, claim boundary
SoftwareReviewer  stale files, table provenance, reproducibility
```

Major checkpoints, paper claims, final scientific audits, and next-branch scientific-route decisions should also receive a separate web-GPT audit.

This symbolic reviewer-agent audit is not the same as Codex app `/review`, which is for code diffs and inline comments.

## Reviewer Hard Boundary

- Do not edit code or symbolic outputs.
- Do not replace verifier scripts.
- Audit exactness gates, stale inputs, protected regressions, claim boundary, and next action.
- If validation failed, recommend against freezing even if the narrative looks plausible.

## Reviewer Questions

1. Is the algebra exact?
2. Is the simplification real?
3. Were old or stale tables mixed in?
4. Did protected regressions survive?
5. Is the claim boundary honest?
6. Should this branch freeze, patch, fail, or open next stage?
