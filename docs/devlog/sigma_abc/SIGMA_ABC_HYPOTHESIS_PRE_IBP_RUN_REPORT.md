# Sigma ABC Hypothesis Pre-IBP Run Report

## Scope

Profile:

```text
sigma_abc_hypothesis_pre_ibp
```

This run was allowed to attempt:

```text
011 center-sector pilot
012 loop orbit canonicalization pilot
013 global pre-IBP assembly
014 sigma_xxx projection regression hardening
```

The run did not reach stages 012--014 because stage 011 could not freeze after
real-agent review was blocked by Codex usage quota.

## Loop 007 Runtime Gate

Before starting production, the clean mock real-agent loop froze successfully:

```text
mock stage -> mock_000_identity
validation overall_gate -> PASS
review verdict -> PASS_WITH_CAVEAT
decision -> FREEZE_WITH_CAVEAT
checkpoint_manifest.json -> created
AlgebraReviewer actually_invoked -> True
PhysicsReviewer actually_invoked -> True
SoftwareReviewer actually_invoked -> True
stub_used -> False for all reviewers
schema_valid -> True for all reviewers
read_only_contract_enforced -> True for all reviewers
```

The runtime adapter checkpoint is:

```text
loop_007_real_subagent_runtime_adapter_checkpoint_v1
```

## Stages Attempted

| Stage | Validation | Review | Decision | Frozen |
| --- | --- | --- | --- | --- |
| `sigma_abc_011_center_sector_pilot` | PASS | FAILED due real-agent quota | RETRY_AFTER_RUNTIME_LIMIT | no |

No stage 012, 013, or 014 was started.

## Stage 011 Validation Status

The patched Stage 011 executor no longer claims expression-level center fusion.
It validates only row-provenance conservation:

```text
identity_type -> RowProvenanceHashConservation
CenterSectorRowCount -> 93
CenterProvenanceDifference -> 0
CenterFusionDifference -> NOT_CLAIMED
XXXCenterProjectionRegression -> INHERITED_OR_DEFERRED
NoPairSectorTouched -> True
NoLoopSectorTouched -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
NoFullTensorialClaim -> True
overall_gate -> PASS
```

The promoted candidate is no longer the toy `(x+1)^2` candidate.  Its validation
is a center/contact row-id and term-hash multiset conservation check.

## Conjectures

```text
conjectures proposed -> 2
candidates built -> 2
candidates archived -> 1
verified candidate promoted -> True
```

The failed conjecture was archived as a normal failed conjecture, not a hard
stop.

## Runtime Review Status

The real reviewer invocations were attempted and did not use stubs:

| Reviewer | actually_invoked | stub_used | exit_code | schema_valid | read_only_contract_enforced | freeze_evidence_valid |
| --- | --- | --- | --- | --- | --- | --- |
| AlgebraReviewer | True | False | 1 | False | True | False |
| PhysicsReviewer | True | False | 1 | False | True | False |
| SoftwareReviewer | True | False | 1 | False | True | False |

All three reviewer invocations failed because the external Codex runtime quota
was exhausted:

```text
AGENT_RUNTIME_QUOTA_EXHAUSTED
RetryAfter -> 6:27 AM
```

The corrected decision output is:

```text
Decision -> RETRY_AFTER_RUNTIME_LIMIT
FreezeAllowed -> False
PatchRequired -> False
RetryAfter -> 6:27 AM
```

## Validation Identities Checked

```text
Center row-id multiset conservation
Center term-hash multiset conservation
Stage010PairFusionRegression -> PASS
sigma_xxx_projection protected benchmark -> PASS metadata
DCProjectionTo1D caveat preserved
```

## Sigma XXX Benchmark Status

```text
sigma_xxx_projection -> PASS
Stage010PairFusionRegression -> PASS
```

No new full tensorial projection equality was claimed.

## DC Inherited Caveat Status

Preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Named Digest Files

Generated before quota stopped freeze:

```text
autonomous_runs/sigma_abc/stages/sigma_abc_011_center_sector_pilot/reports/stage_summary.pdf
autonomous_runs/sigma_abc/stages/sigma_abc_011_center_sector_pilot/reports/sigma_abc_011_center_sector_pilot_summary.pdf
autonomous_runs/sigma_abc/stages/sigma_abc_011_center_sector_pilot/reports/stage_sigma_abc_011_center_sector_pilot_hypothesis_search_summary.md
```

## Current Best Sigma ABC Expression Status

```text
current frozen checkpoint -> sigma_abc_010_pair_kernel_fusion_pilot
stage 011 center/contact row-provenance pilot -> validation PASS but NOT FROZEN
full tensorial sigma_abc correctness -> NOT CLAIMED
tensorial IBP -> NOT STARTED
total-derivative reduction -> NOT STARTED
```

## Human Approval Before IBP

Human approval is still required before any tensorial IBP or total-derivative
reduction.  The present blocker is not an IBP decision; it is external Codex
runtime quota.

## Recommended Next Profile

After quota reset, rerun the same production profile from the current frozen
checkpoint:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests
```

Do not start tensorial IBP or total-derivative reduction before the pre-IBP
profile freezes its approved stages.
