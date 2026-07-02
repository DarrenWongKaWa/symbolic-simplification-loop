# Loop 019 — Upstream 011 / 012A / 012B Materialization Pre-Audit

## Status

PROFILE_AND_HISTORY_IDENTIFIED; AWAITING_PROFILE_EXECUTION_APPROVAL.

Phase 1 root-cause investigation complete. The pre-audit identifies
exactly **one** profile that matches the user's explicit constraints
(stop at 012B, no promotion, no IBP, no total derivative, allow
review debt for upstream low-risk pilot stages):

```text
profiles/sigma_abc_hypothesis_pre_ibp_throughput.yaml
```

This pre-audit does **not** start any runner. The runner invocation
is a separate user-approved step.

`sigma_abc` physics NOT modified. No 012C promotion. No Stage 013. No
tensorial IBP. No total-derivative reduction. No claim of full
tensorial sigma_abc correctness.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Current Physical Checkpoint (before any action)

```text
autonomous_runs/sigma_abc/checkpoints/sigma_abc_010_pair_kernel_fusion_pilot_2026-07-01T11-54-10+00-00
```

The 010 frozen checkpoint contains a valid human_signoff.yaml:

```text
decision: APPROVE_FREEZE_WITH_CAVEAT
permission.freeze_checkpoint: true
permission.start_ibp: false
permission.start_total_derivative: false
permission.promote_claim: false
accepted_caveats:
  - "DCProjectionTo1D -> INHERITED_PASS, ..."
basis_hashes: (validation_summary, review_result,
               completion_matrix, claim_boundary) — all hashed
```

That is the deepest physical frozen checkpoint on disk. There is
**no** frozen `sigma_abc_011_*`, `012a_*`, or `012b_*` checkpoint.

## Missing Stage / Checkpoint Directories

```text
MISSING  autonomous_runs/sigma_abc/stages/sigma_abc_011_center_sector_pilot/
MISSING  autonomous_runs/sigma_abc/stages/sigma_abc_012a_loop_sector_inventory/
MISSING  autonomous_runs/sigma_abc/stages/sigma_abc_012b_loop_hypothesis_generation/
MISSING  autonomous_runs/sigma_abc/checkpoints/sigma_abc_011_center_sector_pilot_*/
MISSING  autonomous_runs/sigma_abc/checkpoints/sigma_abc_012a_loop_sector_inventory_*/
MISSING  autonomous_runs/sigma_abc/checkpoints/sigma_abc_012b_loop_hypothesis_generation_*/
```

The 011 review-debt report
(`SIGMA_ABC_STAGE011_REVIEW_DEBT_REPORT.md`) itself records that the
current run root contained Stage010 only, with `Stage011ArtifactPresent ->
False`. The 012AB artifact contract patch report
(`SIGMA_ABC_012AB_ARTIFACT_CONTRACT_PATCH_REPORT.md`) records an
interrupted throughput attempt that produced **011 + 012A artifacts**
but hung on the real `ScientificMetaReviewer` for 012A, generating
**no 012B artifact**. Both reports confirm we are starting from no
physical upstream materialization.

## Required Upstream Stages

Per the gate chain (Loop 013 §012C Regression Semantics + 012AB
contract patch report), the 012C preparation gate demands these
frozen upstream stages:

```text
sigma_abc_011_center_sector_pilot            (center/contact row-provenance pilot)
sigma_abc_012a_loop_sector_inventory         (loop-sector inventory artifacts)
sigma_abc_012b_loop_hypothesis_generation    (loop-hypothesis conjectures, exploration only)
```

These are listed in `profiles/sigma_abc_hypothesis_pre_ibp_throughput.yaml`
as `allowed_stage_ids`.

## Active Profile (recommended)

Profile:

```text
profiles/sigma_abc_hypothesis_pre_ibp_throughput.yaml
```

Key contract clauses (verbatim from the profile, paraphrased only for
this audit's inventory):

```text
autonomy.max_stages_per_run: 3
autonomy.stop_after_stage:   sigma_abc_012b_loop_hypothesis_generation
allowed_stage_ids:
  - sigma_abc_011_center_sector_pilot
  - sigma_abc_012a_loop_sector_inventory
  - sigma_abc_012b_loop_hypothesis_generation
human_approval.granted: true
human_approval.scope: "throughput mode for low-risk review debt and
                      exploration-only loop conjectures; no promotion,
                      no tensorial IBP, no total derivatives"
hypothesis_search.promote_candidates: false
hypothesis_search.exploration_only: true
review_policy.l1_on_timeout: PROVISIONAL_FREEZE_WITH_REVIEW_DEBT
review_policy.l1_on_quota:  PROVISIONAL_FREEZE_WITH_REVIEW_DEBT
review_policy.l1_on_no_output: PROVISIONAL_FREEZE_WITH_REVIEW_DEBT
review_policy.l2_on_timeout: VALIDATED_PENDING_REVIEW
review_policy.l2_allow_advance_if_validation_passed: false
review_debt.allow_low_risk_advance: true
review_debt.max_open_review_debts: 2
review_debt.block_before_l2_promotion: true
review_debt.block_before_global_assembly: true
review_debt.block_before_ibp: true
review_debt.blocking_before:
  - candidate_promotion
  - global_pre_ibp_assembly
  - ibp
  - paper_claim
  - full_tensorial_correctness_claim
```

Why this profile specifically:

- `stop_after_stage: 012b` ensures the runner **cannot** reach
  `012c_promotion` or `013` or `014`.
- `allowed_stage_ids` does **not** list `sigma_abc_012c_loop_orbit_canonicalization_promotion`
  nor `sigma_abc_013_*`.
- `promote_candidates: false`.
- Review-debt fallbacks handle the historically recurring
  Codex quota / no-output scenario on the ScientificMetaReviewer.

## Forbidden Artifact Scan (baseline, before any action)

```text
$ find . -maxdepth 5 -type f \
    \( -name "*stage_013*" -o -name "*sigma_abc_013_*" \
       -o -name "*tensorial_ibp*" -o -name "*total_derivative*" \
       -o -name "*global_pre_ibp*" -o -name "*promoted_candidate_manifest*" \
       -o -name "*stage_012c_loop_orbit_canonicalization_promotion*" \)
-> (no output)
```

Clean baseline. No forbidden artifacts present.

## Historical Pitfalls To Avoid

From `SIGMA_ABC_STAGE011_PENDING_REVIEW_REPORT.md` and
`SIGMA_ABC_STAGE011_RUNTIME_RETRY_AFTER_LIMIT_REPORT.md`:

- The last live 011 run had `validation -> PASS` and
  `decision -> VALIDATED_PENDING_REVIEW` (NOT frozen), because
  `ScientificMetaReviewer` was quota-limited.
- The throughput profile's `l1_on_quota: PROVISIONAL_FREEZE_WITH_REVIEW_DEBT`
  is **exactly** the fallback designed for that scenario, but it does
  **not** convert "review-debt open" into "freeze unconditionally".
- The blocker set (`review_debt.blocking_before`) covers
  `candidate_promotion`, `global_pre_ibp_assembly`, `ibp`,
  `paper_claim`, `full_tensorial_correctness_claim`. None of these
  become available from materializing 011 / 012A / 012B.

From `SIGMA_ABC_012AB_ARTIFACT_CONTRACT_PATCH_REPORT.md` ("Throughput
Attempt" section):

- A prior throughput run generated **011 + 012A artifacts**
  successfully. **012A's real `ScientificMetaReviewer` hung** without
  producing `stdout.txt / stderr.txt / exit_code.txt`.
- The run was interrupted manually.
- The contract patch report recommends: "Resolve the real-agent
  runtime hang or run the low-risk Stage 012B generation after the
  reviewer runtime is available."
- This pre-audit inherits that caveat. If reviewer runtime is again
  unavailable, the same fallback applies; if 012A falls back to
  PROVISIONAL_FREEZE_WITH_REVIEW_DEBT, the debt is *allowed* open
  (per profile) but cannot promote or trigger IBP/total-derivative.

## Active Signoff / Boundary Status (010 chain)

The 010 frozen checkpoint has a valid pytest-profile auto-signoff
explicitly labeled `signed_by: pytest_profile` and reason
`"Auto signoff generated only for pytest profile regression."`. That
signoff will not propagate; Loop 013 § 012C Regression Semantics
makes that explicit:

```text
completion_matrix contains blocking incomplete dependency/readiness items
   -> freeze_preconditions still rejects freeze
```

So even if a future 011/012A/012B freeze runs through pytest auto-
signoff, the 012C promotion remains blocked by `Stage012AArtifactPresent
-> FAILED`, etc., until the upstream stages are physically materialized
and frozen under the throughput profile's own review-debt fallback.

## Recommended Next Command (pending user approval)

```text
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 3
```

Expected gate outcomes (if all upstream artifacts serialize):

```text
Stage 011 freeze: PROVISIONAL_FREEZE_WITH_REVIEW_DEBT (if quota limit) or PASS (if reviewer available)
Stage 012A freeze: PROVISIONAL_FREEZE_WITH_REVIEW_DEBT (likely; historical precedent) or PASS
Stage 012B freeze: PROVISIONAL_FREEZE_WITH_REVIEW_DEBT or PASS

Stage013NotStarted  -> True
Stage012CPromotionNotStarted -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
DCProjectionTo1D caveat -> preserved

Deep physical checkpoint after run:
  sigma_abc_012b_loop_hypothesis_generation_<timestamp>
```

Worst-case outcome (real-agent reviewer again blocked):

```text
PROVISIONAL_FREEZE_WITH_REVIEW_DEBT for 011 and 012A
Stage 012B still attempted via low-risk path
review_debt.open <= 2 (per profile)
No 012C promotion reached
No 013 reached
No IBP reached
No total derivative reached
```

In both cases the output of the runner will need to be classified
against verdict A/B/C in
`LOOP_019_UPSTREAM_012A_012B_MATERIALIZATION_REPORT.md`.

## Permanent Caveat Preserved

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Boundary of This Pre-Audit

This file does **not** invoke the runner. Step 2 (user-approval-gated
profile execution) is the separate step.

## Files Examined

```text
LOOP_018_STAGE_012C_PROMOTION_REPORT.md
STAGE_012C_PROMOTION_PRE_AUDIT.md
LOOP_014_017_FINAL_INTEGRATION_REPORT.md
LOOP_013_HUMAN_SIGNOFF_COMPLETION_MATRIX_REPORT.md
SIGMA_ABC_HYPOTHESIS_PRE_IBP_RUN_REPORT.md
SIGMA_ABC_STAGE011_PENDING_REVIEW_REPORT.md
SIGMA_ABC_STAGE011_REVIEW_DEBT_REPORT.md
SIGMA_ABC_STAGE011_RUNTIME_RETRY_AFTER_LIMIT_REPORT.md
SIGMA_ABC_CENTER_SECTOR_PILOT_REPORT.md
SIGMA_ABC_012AB_ARTIFACT_CONTRACT_PATCH_REPORT.md
SIGMA_ABC_HUMAN_APPROVAL_REQUIRED.md
SIGMA_ABC_HUMAN_APPROVAL_REQUIRED_FOR_IBP.md
profiles/sigma_abc_center_sector_pilot.yaml
profiles/sigma_abc_hypothesis_pre_ibp.yaml
profiles/sigma_abc_hypothesis_pre_ibp_throughput.yaml
profiles/sigma_abc_loop_candidate_preparation.yaml
profiles/sigma_abc_loop_candidate_promotion.yaml
```

## Next Safe Action

User must explicitly approve running

```text
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 3
```

before any stage is executed. The runner invocation and the
final-verdict report (`LOOP_019_..._REPORT.md`, verdict A/B/C) belong
to the next prompt, not to this pre-audit.