# Loop 008 Review Budget and Async Queue Report

## Branch

```text
loop_008_review_budget_and_async_queue
```

## Goal

Reduce quota blocking and reviewer token cost by adding tiered review lanes,
compact review packets, and resumable pending-review queues.  This branch does
not change `sigma_abc` physics, does not start Stage 012, and does not change
frozen checkpoints.

## Review Lanes Added

```text
L0_DETERMINISTIC
  - no LLM reviewer required
  - allowed for low-risk deterministic/schema/provenance stages

L1_COMPACT_META
  - compact packet required
  - only ScientificMetaReviewer required
  - used for low-risk provenance/classification stages with claim-boundary review

L2_FULL_PANEL
  - AlgebraReviewer + PhysicsReviewer + SoftwareReviewer + ScientificMetaReviewer
  - required for kernel fusion, loop orbit canonicalization, global assembly,
    new symbolic candidate promotion, IBP/total derivative, and full formula claims
```

## Implemented Artifacts

```text
loop_engine/risk_classifier.py
loop_engine/compact_packet.py
loop_engine/review_queue.py
scripts/build_compact_review_packet.py
scripts/resume_pending_reviews.py
templates/COMPACT_REVIEW_PACKET.template.md
```

Updated integration points:

```text
loop_engine/decision.py
loop_engine/meta_review.py
loop_engine/reviewer.py
scripts/run_autonomous_loop.py
profiles/sigma_abc_hypothesis_pre_ibp.yaml
profiles/sigma_abc_safe_pre_fusion.yaml
schemas/review_result.schema.json
```

## Risk Classifier Behavior

The classifier reads:

```text
STAGE_PLAN.md
.loop/validation_summary.json
.loop/metrics.json
CLAIM_BOUNDARY.md
profile YAML
```

and writes:

```text
.loop/risk_classification.json
```

For the existing Stage 011 center-sector pilot:

```text
risk_level -> LOW
review_lane -> L1_COMPACT_META
full_panel_required -> False
llm_review_required -> True
new_symbolic_candidate_promoted -> False
ibp_related -> False
```

The classifier distinguishes forbidden/negative boundary language such as
`NoIBPStarted`, `NoTotalDerivativeIntroduced`, and `Do not claim kernel fusion`
from actual positive operation claims.

## Compact Packet Behavior

For L1/L2 stages the runner writes:

```text
review_minipacket.md
```

The minipacket contains the stage goal, validation summary, changed outputs,
claim boundary, caveats, protected benchmark status, forbidden-action status,
and exact reviewer questions.  It intentionally excludes full ledgers, large
symbolic tables, and full stdout unless the risk classifier requires full-panel
review.

## Async Queue Behavior

Quota/runtime-limit reviewer failure now produces:

```text
Decision -> VALIDATED_PENDING_REVIEW
FreezeAllowed -> False
PatchRequired -> False
ExecutorRerunRequired -> False
ReviewerResumeRequired -> True
```

The queue artifacts are:

```text
.loop/review_queue/pending_reviews.jsonl
.loop/runtime_limits.json
```

Resume command:

```bash
python3 scripts/resume_pending_reviews.py --project sigma_abc --from-pending
```

Resume verifies input hashes before review.  If hashes changed, it requests
revalidation instead of reusing stale validation.  L0 mock resume was verified
without rerunning executor.

## Stage 011 Normalized Status

The existing attempted Stage 011 was not rerun.  Its executor/verifier outputs
remain preserved, and its state was normalized to pending review:

```text
Stage011Status -> VALIDATED_PENDING_REVIEW
FreezeAllowed -> False
PatchRequired -> False
ExecutorRerunRequired -> False
ReviewerResumeRequired -> True
ReviewLane -> L1_COMPACT_META
RiskLevel -> LOW
FullPanelRequired -> False
```

Stage 011 validation remains:

```text
identity_type -> RowProvenanceHashConservation
CenterProvenanceDifference -> 0
CenterFusionDifference -> NOT_CLAIMED
XXXCenterProjectionRegression -> INHERITED_OR_DEFERRED
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
overall_gate -> PASS
```

Report:

```text
SIGMA_ABC_STAGE011_PENDING_REVIEW_REPORT.md
```

## Verification

Commands run:

```bash
python3 -m pytest -q tests/test_review_budget_async_queue.py
python3 -m pytest -q tests/test_review_budget_async_queue.py tests/test_decision_engine.py tests/test_autonomous_loop_runner.py::test_runtime_usage_limit_decision_creates_pending_review_without_patch
python3 -m pytest -q tests/test_autonomous_loop_runner.py::test_autonomous_runner_mock_two_stages_freezes_without_long_prompt tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008 tests/test_mailbox_orchestration.py::test_stage_named_digest_paths tests/test_meta_review_and_digest.py::test_autonomous_runner_runs_meta_review_and_digest
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
python3 scripts/run_autonomous_loop.py --project mock --profile test_hypothesis_search_loop --clean
python3 scripts/resume_pending_reviews.py --project mock_pending --from-pending --allow-l0-freeze
```

Results:

```text
pytest -> 88 passed, 1 warning
compileall -> PASS
mock hypothesis loop -> PASS
mock pending resume -> resumed 1, executor_rerun_required False, decision FREEZE
```

## Boundary

No `sigma_abc` physics was changed.  No new `sigma_abc` stage was started.
No tensorial IBP or total-derivative reduction was introduced.  No frozen
checkpoint was overwritten.  Reviewer outputs were not faked.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Next Step

After quota reset, resume Stage 011 reviewer-only using the pending queue.  Do
not rerun MainExecutor unless the pending input hashes changed.
