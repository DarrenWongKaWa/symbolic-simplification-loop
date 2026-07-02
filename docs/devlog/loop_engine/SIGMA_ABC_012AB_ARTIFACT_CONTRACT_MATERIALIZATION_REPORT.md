# Sigma-Abc 012A/012B Artifact Contract Materialization Report

## Branch

```text
sigma_abc_012c_preparation_intent_and_expected_outputs_patch
```

## Goal

Run the upstream artifact contract before any Octo-style overlay work:

```text
011 center-sector pilot
012A loop-sector inventory
012B loop-hypothesis generation
012C-prep readiness check only
```

No 012C promotion, Stage 013, tensorial IBP, or total-derivative reduction is
started in this run.

## Infrastructure Fixes Added In This Pass

### 1. Dry-run identity guard for multi-stage profiles

The dry-run report now uses the actual next selected stage as:

```text
ExpectedStage
ActualStage
```

and reports the profile stop boundary separately:

```text
StopAfterStage
```

This avoids false `ReportIdentityCheck -> FAIL` for throughput profiles whose
first stage is 011 but whose stop-after stage is 012B.

### 2. Review-debt blocker distinguishes preparation from promotion

Open review debt still blocks:

```text
sigma_abc_012c_loop_orbit_canonicalization_promotion
sigma_abc_013_global_pre_ibp_assembly
IBP / total-derivative stages
```

but no longer blocks:

```text
sigma_abc_012c_real_loop_candidate_preparation
```

because preparation is a read-only/readiness gate:

```text
NoCandidatePromoted -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
```

## Commands Run

### Throughput dry-run

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --dry-run \
  --from-current-checkpoint \
  --max-stages 3
```

Key result:

```text
CurrentCheckpoint -> sigma_abc_010_pair_kernel_fusion_pilot
NextStage -> sigma_abc_011_center_sector_pilot
ExpectedStage -> sigma_abc_011_center_sector_pilot
ActualStage -> sigma_abc_011_center_sector_pilot
StopAfterStage -> sigma_abc_012b_loop_hypothesis_generation
ReportIdentityCheck -> PASS
CandidatePromotionAllowed -> False
IBPAllowed -> False
TotalDerivativePromotionAllowed -> False
```

### Throughput materialization

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 3
```

Result:

```text
stages_attempted -> 3
stages_frozen -> 3 provisional checkpoints with review debt
011 validation -> PASS
012A validation -> PASS
012B validation -> PASS
```

The reviewer failure was transport/runtime only:

```text
AGENT_ALL_PROVIDERS_UNAVAILABLE
openai_compatible_api TLS certificate verification failure
```

It did not change the validation result.

### 012C-prep readiness gate

Previous failed preparation directories were archived under:

```text
archive/local_runs/2026-07-02T08-05-31+00-00_012C_PREP_FAILED_BEFORE_ARTIFACT_MATERIALIZATION/
archive/local_runs/2026-07-02T08-06-25+00-00_012C_PREP_BLOCKED_BY_REVIEW_DEBT_BEFORE_PATCH/
```

Then:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_loop_candidate_preparation \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 1
```

Result:

```text
Validation -> PASS
Review -> PASS
Decision -> DO_NOT_FREEZE
Frozen -> no
```

Decision was blocked by meta-review missing `scientific_metareviewer.json`.
This is acceptable for the current goal because this run is a readiness check,
not a freeze/promotion request.

## 012A Artifact Contract

All required 012A artifacts now exist:

```text
autonomous_runs/sigma_abc/stages/sigma_abc_012a_loop_sector_inventory/output/loop_sector_ledger.csv
autonomous_runs/sigma_abc/stages/sigma_abc_012a_loop_sector_inventory/output/loop_orbit_inventory.json
autonomous_runs/sigma_abc/stages/sigma_abc_012a_loop_sector_inventory/output/loop_raw_sector_table.wl
autonomous_runs/sigma_abc/stages/sigma_abc_012a_loop_sector_inventory/validation/loop_inventory_validation.json
```

012A validation:

```text
overall_gate -> PASS
Stage012AArtifactPresent -> True
NoCandidatePromoted -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
```

## 012B Artifact Contract

All required 012B artifacts now exist:

```text
autonomous_runs/sigma_abc/stages/sigma_abc_012b_loop_hypothesis_generation/output/loop_hypothesis_ledger.json
autonomous_runs/sigma_abc/stages/sigma_abc_012b_loop_hypothesis_generation/output/loop_candidate_requirements.json
autonomous_runs/sigma_abc/stages/sigma_abc_012b_loop_hypothesis_generation/.loop/conjectures/conjecture_ledger.json
autonomous_runs/sigma_abc/stages/sigma_abc_012b_loop_hypothesis_generation/reports/loop_hypothesis_generation_summary.md
```

012B validation:

```text
overall_gate -> PASS
Stage012BArtifactPresent -> True
NoCandidatePromoted -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
```

## 012C-Prep Readiness Result

The preparation gate now resolves both upstream contracts:

```text
overall_gate -> PASS
PreparationStatus -> READY_FOR_012C_PROMOTION_RETRY
Stage012AArtifactPresent -> True
Stage012BArtifactPresent -> True
UsesStage012ALoopLedger -> True
UsesStage012BHypothesisLedger -> True
CandidateSource -> sigma_abc_loop_sector
ToyCandidateDetected -> False
MockCandidateDetected -> False
NoCandidatePromoted -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
RealLoopCandidateReady -> True
```

Preparation artifacts:

```text
autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/output/loop_candidate_preparation.json
autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/output/loop_candidate_requirements_resolved.json
autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/reports/loop_candidate_preparation_report.md
autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/validation/loop_candidate_preparation_validation.json
```

Forbidden artifact absent:

```text
autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/output/promoted_candidate_manifest.json
```

## Validation

Targeted tests:

```bash
python3 -m pytest -q \
  tests/test_review_debt_throughput.py \
  tests/test_loop011_l1_reviewer_timeout_debt.py \
  tests/test_sigma_abc_loop_candidate_preparation.py
```

Result:

```text
24 passed, 1 warning
```

Full test suite:

```bash
python3 -m pytest -q
```

Result:

```text
298 passed, 1 warning
```

Compile check:

```bash
python3 -m compileall loop_engine scripts tests
```

Result:

```text
PASS
```

## Boundary Confirmation

```text
sigma_abc physics modified -> False
012C promotion started -> False
Stage 013 started -> False
Tensorial IBP started -> False
Total-derivative reduction introduced -> False
Full tensorial correctness claimed -> False
DCProjectionTo1D inherited caveat preserved -> True
```

## Current Status

```text
012A/012B artifact contract -> MATERIALIZED
012C-prep readiness -> READY_FOR_012C_PROMOTION_RETRY
012C-prep checkpoint freeze -> NOT REQUESTED / NOT FROZEN
012C promotion -> NOT STARTED
```

## Post-Test Live State Restore

After the full pytest pass, the live `autonomous_runs/sigma_abc` root was
re-materialized with:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 3

python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_loop_candidate_preparation \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 1
```

Final live check:

```text
012A required artifacts -> present
012B required artifacts -> present
012C-prep overall_gate -> PASS
012C-prep PreparationStatus -> READY_FOR_012C_PROMOTION_RETRY
NoCandidatePromoted -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
```

Targeted post-restore regression:

```bash
python3 -m pytest -q \
  tests/test_review_debt_throughput.py \
  tests/test_loop011_l1_reviewer_timeout_debt.py \
  tests/test_sigma_abc_loop_candidate_preparation.py

python3 -m compileall loop_engine scripts tests
```

Result:

```text
24 passed, 1 warning
compileall PASS
```

## Next Safe Step

Now the Octo-style overlay can be implemented as metadata only:

```text
loop_021_octo_style_matter_bot_overlay
```

If continuing the physics path instead, the next step would be a separately
approved L2 promotion profile:

```text
sigma_abc_loop_candidate_promotion
```

Do not run that promotion profile without explicit approval.
