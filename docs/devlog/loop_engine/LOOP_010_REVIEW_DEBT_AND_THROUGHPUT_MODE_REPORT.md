# Loop 010 Review Debt and Throughput Mode Report

## Scope

Branch: `loop_010_review_debt_and_throughput_mode`

This branch adds a controlled review-debt throughput mode for low-risk validated
stages whose L0/L1 review is blocked only by real-agent quota/runtime limits.
It does not modify sigma_abc physics, does not start tensorial IBP, does not
promote total-derivative reduction, and does not claim full tensorial
`Sigma_{mu alpha beta}` correctness.

## Implemented Artifacts

```text
loop_engine/review_debt.py
schemas/review_debt.schema.json
scripts/audit_review_debt.py
scripts/settle_review_debt.py
profiles/sigma_abc_hypothesis_pre_ibp_throughput.yaml
tests/test_review_debt_throughput.py
SIGMA_ABC_STAGE011_REVIEW_DEBT_REPORT.md
```

Updated orchestration files:

```text
loop_engine/risk_classifier.py
loop_engine/checkpoint.py
loop_engine/conjecture_ledger.py
scripts/run_autonomous_loop.py
projects/sigma_abc/loop.yaml
profiles/sigma_abc_hypothesis_pre_ibp.yaml
agents/runtime.local.yaml
```

## New Decision / Debt States

```text
PROVISIONAL_FREEZE_WITH_REVIEW_DEBT
ADVANCE_WITH_REVIEW_DEBT
REVIEW_DEBT_BLOCKED
REVIEW_DEBT_SETTLED
```

The implemented runner uses `PROVISIONAL_FREEZE_WITH_REVIEW_DEBT` for allowed
low-risk quota/runtime review debt, `REVIEW_DEBT_BLOCKED` for high-risk
blocked downstream stages, and `REVIEW_DEBT_SETTLED` when later reviewer resume
settles the debt.

## Review Debt Safety Conditions

A stage can enter provisional review debt only when all of the following hold:

```text
validation_summary.overall_gate -> PASS
risk_level -> LOW or MEDIUM
review_lane -> L0_DETERMINISTIC or L1_COMPACT_META
review failure is quota/runtime limit only
NoKernelFusionStarted -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
NoFullTensorialClaim -> True
Stage001DCCaveatPreserved -> True
ProtectedBenchmarksUnchanged is not False
NewSymbolicCandidatePromoted is not True
LoopOrbitCanonicalizationPromoted is not True
GlobalAssemblyStarted is not True
```

Open review debt blocks:

```text
candidate_promotion
global_pre_ibp_assembly
ibp
paper_claim
full_tensorial_correctness_claim
```

## Throughput Profile

New profile:

```text
profiles/sigma_abc_hypothesis_pre_ibp_throughput.yaml
```

Allowed stages:

```text
011 center-sector pilot
012A loop-sector inventory / orbit ledger provenance
012B exploration-only loop hypothesis generation
```

Blocked unless all review debt is settled:

```text
012C loop orbit canonicalization promotion
013 global pre-IBP assembly
IBP
total-derivative reduction
full tensorial correctness claim
```

## Stage 012 Split

The sigma_abc graph now splits the former Stage 012 into:

```text
sigma_abc_012a_loop_sector_inventory
sigma_abc_012b_loop_hypothesis_generation
sigma_abc_012c_loop_orbit_canonicalization_promotion
```

Risk lanes:

```text
012A -> L0_DETERMINISTIC or L1_COMPACT_META
012B -> L1_COMPACT_META, exploration-only, verified candidates not promoted
012C -> L2_FULL_PANEL, candidate promotion
013  -> L2_FULL_PANEL, global pre-IBP assembly
```

## Exploration Mode

`hypothesis_search.exploration_only: true` and `promote_candidates: false` now
record a passing candidate as:

```text
CandidateValidationStatus -> VERIFIED_BUT_NOT_PROMOTED
VerifiedCandidatePromoted -> False
```

This keeps exploration useful without promoting symbolic candidates or freezing
new formula claims.

## Stage011 Current Normalization

Current run root check:

```text
Stage011ArtifactPresent -> False
Stage011Normalized -> NOT_APPLIED
ExecutorRerun -> NOT_RUN
VerifierRerun -> NOT_RUN
```

The current `autonomous_runs/sigma_abc` tree contains Stage010 only.  Because the
plan explicitly says not to rerun Stage011 executor/verifier, no Stage011 debt
entry was fabricated.  The new infrastructure will normalize Stage011 into
`PROVISIONAL_FREEZE_WITH_REVIEW_DEBT` on the next real Stage011 quota/runtime
review block if the safety predicates pass.

## Runtime Check

Throughput profile runtime:

```text
AgentRuntimeStatus -> AVAILABLE
Adapter -> command
ProductionRunAllowed -> True
StubUsed -> False
MissingAgentCommands -> []
```

Dry-run summary:

```text
CurrentCheckpoint -> sigma_abc_010_pair_kernel_fusion_pilot
NextStage -> sigma_abc_011_center_sector_pilot
Allowed stage list -> 011, 012A, 012B
StopBeforeIBP -> True
ProductionStubForbidden -> True
```

## Verification

Commands run:

```bash
python3 -m pytest -q tests/test_review_debt_throughput.py
python3 -m pytest -q tests/test_review_debt_throughput.py tests/test_review_quality_hardening.py tests/test_review_budget_async_queue.py tests/test_autonomous_loop_runner.py tests/test_sigma_abc_hypothesis_pre_ibp_profile.py
python3 scripts/check_agent_runtime.py --profile sigma_abc_hypothesis_pre_ibp_throughput
python3 scripts/run_autonomous_loop.py --project sigma_abc --profile sigma_abc_hypothesis_pre_ibp_throughput --dry-run --from-current-checkpoint
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
```

Results:

```text
review debt tests -> 8 passed, 1 warning
related orchestration tests -> 44 passed, 1 warning
full pytest -> 110 passed, 1 warning
compileall -> PASS
throughput runtime check -> AVAILABLE, command adapter, StubUsed False
throughput dry-run -> COMPLETE, NextStage 011, allowed stages 011/012A/012B
artifact check -> PASS
```

## Claim Boundary

Allowed claim:

```text
Low-risk validated provenance stages may provisionally freeze with explicit review debt when review is blocked only by quota/runtime limits.
```

Allowed claim:

```text
Open review debt may allow exploration-only follow-up stages but blocks candidate promotion, global assembly, IBP, paper claims, and full tensorial correctness claims.
```

Forbidden claim:

```text
Stage011 has been reviewed and ordinarily frozen in the current run root.
```

Forbidden claim:

```text
Sigma_abc physics simplification, tensorial IBP, or total-derivative reduction has started.
```

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Next Safe Action

Use the throughput profile only when you want to allow Stage011 review debt and
continue into 012A/012B exploration-only work:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 3
```

To settle existing debt later:

```bash
python3 scripts/settle_review_debt.py --project sigma_abc
```

or resume the pending review path:

```bash
python3 scripts/resume_pending_reviews.py --project sigma_abc --from-pending
```
