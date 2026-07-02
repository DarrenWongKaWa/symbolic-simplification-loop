# Sigma-Abc 012C Preparation Intent And Expected Outputs Patch Report

## Branch

```text
sigma_abc_012c_preparation_intent_and_expected_outputs_patch
```

## Source Review

```text
archive/local_runs/2026-07-02T07-42-03+00-00_REVIEW_BY_CLAUDE.md
docs/superpowers/plans/2026-07-02-claude-review-intake-012c-prep-gate.md
```

## Goal

Make `sigma_abc_012c_real_loop_candidate_preparation` distinguishable from
actual 012C candidate promotion.

The stage may now execute a preparation/readiness check, but it still cannot
promote a candidate, start Stage 013, start tensorial IBP, introduce total
derivatives, or claim full tensorial correctness.

## Files Changed

```text
loop_engine/pre_run_brief.py
loop_engine/planner.py
scripts/run_autonomous_loop.py
projects/sigma_abc/loop.yaml
profiles/sigma_abc_loop_candidate_preparation.yaml
tests/test_loop019r_pre_run_gate.py
tests/test_sigma_abc_loop_candidate_preparation.py
docs/devlog/loop_engine/SIGMA_ABC_012C_PREPARATION_INTENT_AND_EXPECTED_OUTPUTS_PATCH_REPORT.md
```

Note: this repository has not yet had its initial commit; `git status --short`
therefore reports the repository contents as untracked. The file list above is
the patch-level scope for this branch.

## Changes

### 1. Positive intent vs boundary acknowledgement

The pre-run intent classifier now blocks positive promotion intent such as:

```text
candidate promotion before tensorial IBP
promote the candidate now
```

but does not block negative boundary acknowledgements such as:

```text
no candidate promotion
candidate promotion forbidden
do not promote the candidate
```

This lets the preparation stage say what it forbids without being mistaken for
an attempt to perform it.

### 2. Machine-readable preparation intent

The 012C-preparation profile and stage spec now state:

```text
stage_intent: candidate_preparation_only
candidate_promotion_allowed: false
```

The pre-run brief records these fields in `task_understanding` and the rendered
agent self-understanding report.

### 3. Expected outputs are explicit

The 012C-preparation stage spec now declares expected outputs:

```text
output/loop_candidate_preparation.json
output/loop_candidate_requirements_resolved.json
reports/loop_candidate_preparation_report.md
validation/loop_candidate_preparation_validation.json
.loop/validation_summary.json
```

The default stage planner now writes stage-specific expected outputs and
dependencies into `STAGE_PLAN.md`.

The pre-run parser also recognizes Markdown headings such as:

```text
## Expected Outputs
```

not only bare `expected_outputs:` headings.

### 4. Preparation readiness artifacts

`execute_sigma_abc_loop_candidate_preparation_stage` now writes JSON readiness
artifacts alongside the existing `.wl` scaffolds:

```text
output/loop_candidate_preparation.json
output/loop_candidate_requirements_resolved.json
validation/loop_candidate_preparation_validation.json
```

These are preparation artifacts only. They are not promoted loop candidates.

## Validation Results

### Targeted tests

Command:

```bash
python3 -m pytest -q \
  tests/test_loop019r_pre_run_gate.py \
  tests/test_sigma_abc_loop_candidate_preparation.py \
  tests/test_loop014_017_pre_run_identity_traceability.py
```

Result:

```text
27 passed, 1 warning
```

### Full pytest

Command:

```bash
python3 -m pytest -q
```

Result:

```text
297 passed, 1 warning
```

### Compileall

Command:

```bash
python3 -m compileall loop_engine scripts tests
```

Result:

```text
PASS
```

### Runtime check

Command:

```bash
python3 scripts/check_agent_runtime.py --profile sigma_abc_hypothesis_pre_ibp
```

Result:

```text
AgentRuntimeStatus -> AVAILABLE
Adapter -> command
ProductionRunAllowed -> True
StubUsed -> False
MissingAgentCommands -> []
```

### 012C-prep dry-run

Command:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_loop_candidate_preparation \
  --dry-run \
  --from-current-checkpoint
```

Key result:

```text
ProfileStatus -> COMPLETE
CurrentCheckpoint -> sigma_abc_012b_loop_hypothesis_generation
NextStage -> sigma_abc_012c_real_loop_candidate_preparation
CandidatePromotionAllowed -> False
IBPAllowed -> False
TotalDerivativePromotionAllowed -> False
StopBeforeGlobalAssembly -> True
ReportIdentityCheck -> PASS
```

## Current Live 012C-Prep State

The current generated 012C-preparation stage reports:

```text
overall_gate -> FAIL
PreparationStatus -> BLOCKED_MISSING_STAGE012AB_ARTIFACT_CONTRACT
Stage012AArtifactPresent -> False
Stage012BArtifactPresent -> False
NoCandidatePromoted -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
```

This is the intended post-patch behavior when Stage 012A/012B artifacts are not
available: the preparation check executes and explains the missing dependency,
rather than being rejected as a promotion attempt.

## Boundary Confirmation

```text
sigma_abc physics modified -> False
012C promotion started -> False
Stage 013 started -> False
Tensorial IBP started -> False
Total-derivative reduction introduced -> False
Full tensorial correctness claimed -> False
DCProjectionTo1D caveat preserved -> True
```

## Recommended Next Step

If the next goal is to reach `READY_FOR_012C_PROMOTION_RETRY`, provide or
regenerate the Stage 012A/012B artifact contracts, then rerun:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_loop_candidate_preparation \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 1
```

Do not run 012C promotion until the preparation gate reports:

```text
PreparationStatus -> READY_FOR_012C_PROMOTION_RETRY
OverallGate -> PASS
NoCandidatePromoted -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
```
