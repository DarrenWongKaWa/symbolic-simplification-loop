# Stage 012C Promotion Pre-Audit

## Status

PROMOTION_BLOCKED_AT_PRE_RUN_GATE_AND_CHECKPOINT.

This pre-audit confirms that the explicit 012C promotion profile
exists, but the actual physical state on disk is incompatible with a
safe promotion attempt right now. Three independent blockers prevent
the 012C promotion stage from reaching `freeze`:

1. **Physical checkpoint mismatch** — the latest frozen checkpoint on
   disk is `sigma_abc_010_pair_kernel_fusion_pilot`, **not**
   `sigma_abc_012b_loop_hypothesis_generation`. The promotion profile
   has `current_checkpoint_override: sigma_abc_012b_loop_hypothesis_generation`
   but that is a profile-side logical declaration, not a frozen
   checkpoint.
2. **012A / 012B stage artifacts are physically absent** — neither
   `autonomous_runs/sigma_abc/stages/sigma_abc_012a_loop_sector_inventory`
   nor `..._012b_loop_hypothesis_generation` exists on disk. Per
   Loop 013, this means dependency/readiness items are blocking the
   completion matrix (`Stage012AArtifactPresent`,
   `Stage012BArtifactPresent`, `UsesStage012ALoopLedger`,
   `UsesStage012BHypothesisLedger`, `RealLoopCandidateReady`).
3. **An existing pre_run_gate is already FAIL / hard_stop** on the
   012C preparation stage with `blocking_reasons: ["explicit
   forbidden intent: candidate promotion"]`, and the same profile
   was used in the recent dry-run. The promotion profile differs but
   the dependency gap would re-surface during `freeze_preconditions`.

`sigma_abc` physics NOT modified. No Stage 013, no tensorial IBP, no
total-derivative reduction, no full tensorial sigma_abc correctness
claim. Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Active Profile

```text
profile: sigma_abc_loop_candidate_promotion
current_checkpoint_override: sigma_abc_012b_loop_hypothesis_generation
allowed_stage_ids:
  - sigma_abc_012c_loop_orbit_canonicalization_promotion
allowed_stage_tags:
  - loop_orbit_canonicalization_promotion
  - candidate_promotion
review_policy:
  ReviewLane: L2_FULL_PANEL
  require_l1_for_claim_boundary: true
  require_l2_for_candidate_promotion: true
  require_l2_for_global_assembly: true
  allow_l0_freeze_for_low_risk_provenance: false
hypothesis_search:
  enabled: true
  promote_candidates: true
  allow_ibp_conjectures: false
  allow_total_derivative_conjectures: false
hard_stop_policy: sigma_abc_hard_stops
benchmark_policy: sigma_xxx_projection
human_approval:
  granted: true
  approved_stage_ids:
    - sigma_abc_012c_loop_orbit_canonicalization_promotion
  approved_forbidden_stage_tags: []
  scope: loop candidate promotion only; no global pre-IBP assembly, no
        tensorial IBP, no total-derivative reduction
```

The profile is **explicit** and **authorizes** candidate promotion for
the stage `sigma_abc_012c_loop_orbit_canonicalization_promotion`.

## Stage Identities

| Profile / stage | Role |
|---|---|
| `sigma_abc_loop_candidate_preparation` profile → `sigma_abc_012c_real_loop_candidate_preparation` stage | Prepares artifacts; forbids promotion explicitly. **Not** the promotion path. |
| `sigma_abc_loop_candidate_promotion` profile → `sigma_abc_012c_loop_orbit_canonicalization_promotion` stage | Performs promotion under L2 panel. The intended 012C promotion stage. |

## Promotion Profile Dry-Run Output (verbatim)

```text
$ python3 scripts/run_autonomous_loop.py \
    --project sigma_abc \
    --profile sigma_abc_loop_candidate_promotion \
    --dry-run --from-current-checkpoint
-> exit 0

ProfileStatus                  -> COMPLETE
CurrentCheckpoint              -> sigma_abc_012b_loop_hypothesis_generation
NextStage                      -> sigma_abc_012c_loop_orbit_canonicalization_promotion
HypothesisSearchEnabled        -> True
AutoPatchEnabled               -> True
ConjectureLedgerEnabled        -> True
FailedConjecturesArchived      -> True
NamedStageDigestsEnabled       -> True
ScientificMetaReviewerEnabled  -> True
StopBeforeIBP                  -> True
RealAgentInvocationRequired    -> True
AgentInvocationEvidenceRequired-> True
ProductionStubForbidden        -> True
AgentRuntimeStatus             -> AVAILABLE
Adapter                        -> command
ProductionRunAllowed           -> True
MissingAgentCommands           -> []
ReviewLane                     -> L2_FULL_PANEL
FullPanelRequired              -> True
OpenReviewDebt                 -> False
CandidatePromotionAllowed      -> True
IBPAllowed                     -> False
TotalDerivativePromotionAllowed-> False
StopBeforeGlobalAssembly       -> True
ReportIdentityCheck            -> PASS
```

## Hard-Stops Preserved (not bypassed)

```text
forbidden tag: kernel_fusion
forbidden tag: ibp_reduction
forbidden tag: tensorial_simplification
stop file: STOP
stop file: .loop/protected_regression_failed
stop file: .loop/human_approval_required
```

## Forbidden-Artifact Scan

```text
find . -maxdepth 5 -type f \
  \( -name "*stage_013*" -o -name "*sigma_abc_013_*" \
     -o -name "*tensorial_ibp*" -o -name "*total_derivative*" \
     -o -name "*global_pre_ibp*" -o -name "*promoted_candidate_manifest*" \
     -o -name "*stage_012c_real_loop_candidate_promotion*" \
     -o -name "*stage_012c_loop_orbit_canonicalization_promotion*" \)
-> (no output)
```

No 013 / IBP / total derivative artifacts and no 012C promotion stage
directory on disk.

## Why We Stop Before Promotion

Loop 013 (`LOOP_013_HUMAN_SIGNOFF_COMPLETION_MATRIX_REPORT.md`) makes
this explicit:

```text
These are dependency/readiness failures, not boundary-audit failures.
...
Even if a blocked 012C preparation stage is manually changed to
APPROVE_FREEZE, freeze_preconditions still rejects freeze because the
completion matrix contains blocking incomplete dependency/readiness
items.
```

The current physical state mirrors that test case. The Loop 013 test
`test_loop_candidate_preparation_requires_complete_stage012_artifact_contract`
demonstrates the exact failure path:

- When 012A/012B artifacts are missing,
- `completion_matrix` records blocking FAIL for
  `Stage012AArtifactPresent`, `Stage012BArtifactPresent`,
  `UsesStage012ALoopLedger`, `UsesStage012BHypothesisLedger`,
  `RealLoopCandidateReady`,
- `RecommendedHumanAction` becomes `DO_NOT_FREEZE_PATCH`,
- `freeze_preconditions` returns non-empty.

This pre-audit does **not** attempt to patch around the blockers
(`--auto-patch` would be a Loop 013 / Loop 015 violation: "Do not
convert dependency/readiness failure into success", "Do not weaken
freeze_preconditions", "Do not weaken human_signoff", "Do not bypass
L2_FULL_PANEL review").

## Permanent Caveat Status

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

Preserved in:

- `profiles/sigma_abc_loop_candidate_promotion.yaml` (profile manifest)
- `identities/sigma_abc.default_identities.yaml` (DC inherited caveat identity)
- `LOOP_013_HUMAN_SIGNOFF_COMPLETION_MATRIX_REPORT.md` boundary invariant

## Recommended Next Action

**Do NOT promote the 012C loop candidate now.** Reasons are above and
already imply which gates would refuse. To advance safely:

1. Produce frozen `sigma_abc_012a_loop_sector_inventory` and
   `sigma_abc_012b_loop_hypothesis_generation` stage artifacts and
   freeze them under the loop_candidate_preparation profile (which
   itself forbids promotion — see audit).
2. Re-run pre-audit. The 010-deep checkpoint must be promoted to 012B
   by real, prior frozen stages, not by `--auto-patch`.
3. Only then attempt 012C promotion under the explicit promotion
   profile with L2 full-panel reviewers invoked through the
   command-adapter (per `RealAgentInvocationRequired=True` and
   `ProductionStubForbidden=True`).
4. After 012C is frozen, the next safe step is still **Stage 013
   STOP**, not Stage 013. Stage 013 global pre-IBP assembly is a
   separate hard boundary.

The Step 10 final report will reflect verdict B:

```text
012C promotion not frozen; reason: 012A/012B upstream stage artifacts
physically absent; physical checkpoint is sigma_abc_010_pair_kernel_fusion_pilot
(not 012B); pre_run_gate on the preparation profile is already FAIL
(hard_stop=True, execution_allowed=False). Per Loop 013, freeze_preconditions
would reject even an APPROVE_FREEZE. Stage 013 not started.
```