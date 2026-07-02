# Loop 009 Review Quality Hardening Report

## Scope

Branch:

```text
loop_009_review_quality_hardening_and_stage_resume
```

This branch hardens the repo-native review layer.  It does not modify
`sigma_abc` physics, does not start tensorial IBP, does not promote
total-derivative reduction, and does not claim full tensorial
`sigma_{mu alpha beta}` correctness.

## Implemented

- Added explicit review-quality artifacts:
  - `schemas/review_quality.schema.json`
  - `loop_engine/review_quality.py`
  - `scripts/audit_review_quality.py`
  - `templates/SCIENTIFIC_META_REVIEW_RUBRIC.md`
  - `templates/CLAIM_BOUNDARY_AUDIT.template.md`
- Strengthened `skill/scientific_metareviewer.md` so meta review must answer:
  `PASS as what`, `NOT PASS as what`, validated claims, deferred claims,
  caveats, overclaim status, freeze permission, human-approval status, lane,
  and next safe stage.
- Strengthened `review_minipacket.md` generation with:
  stage id, stage slug, review lane, risk classification, identity type,
  claimed output, not-claimed output, forbidden-actions status, protected
  benchmark status, caveats, and exact review questions.
- Added named review-quality reports:
  `reports/stage_<id>_<slug>_review_quality.md`.
- Added review-quality data into checkpoint manifests when present.
- Hardened risk-lane classification:
  - Stage 011 row-provenance conservation -> `L1_COMPACT_META`.
  - Stage 012 loop orbit canonicalization -> `L2_FULL_PANEL`.
  - Stage 013 global pre-IBP assembly -> `L2_FULL_PANEL`.
  - IBP / total derivative remains approval-gated.
- Hardened pending-review resume:
  - does not rerun executor if pending input hashes are unchanged;
  - generates review-quality output;
  - keeps freeze blocked when review-quality or real reviewer gates fail.
- Added command timeout handling for real agent runtime:
  `TimeoutExpired` now produces structured invocation evidence instead of
  crashing the runner.
- Added `--max-stages` support to `scripts/run_autonomous_loop.py`.
- Fixed `--from-current-checkpoint` behavior so existing frozen checkpoints in
  the run root are also skipped.
- Fixed runner stop policy so `VALIDATED_PENDING_REVIEW` stops the bounded run
  instead of continuing to the next production stage.

## Verification

Commands run:

```bash
python3 -m pytest -q tests/test_review_quality_hardening.py
python3 -m pytest -q tests/test_review_quality_hardening.py tests/test_review_budget_async_queue.py tests/test_meta_review_and_digest.py
python3 -m pytest -q tests/test_agent_runtime_adapter.py::test_command_agent_adapter_timeout_returns_structured_failure tests/test_decision_engine.py tests/test_autonomous_loop_runner.py::test_runtime_usage_limit_decision_creates_pending_review_without_patch
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
```

Final verification:

```text
pytest -> 102 passed, 1 warning
compileall -> PASS
```

The warning is the pre-existing Python `dateutil` deprecation warning.

## Stage 011 Resume Outcome

Final production attempt:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 2
```

Result:

```text
Stage011Status -> VALIDATED_PENDING_REVIEW
Validation -> PASS
ReviewLane -> L1_COMPACT_META
RiskLevel -> LOW
FullPanelRequired -> False
Reviewer -> ScientificMetaReviewer
actually_invoked -> True
stub_used -> False
read_only_contract_enforced -> True
Decision -> VALIDATED_PENDING_REVIEW
FreezeAllowed -> False
PatchRequired -> False
RetryAfter -> 4:47 PM
```

The real Codex reviewer command was invoked, but the local Codex runtime
reported a usage limit.  This is not treated as a patchable code failure.

## Safety Boundary

Preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

Not started:

```text
Stage012 -> not started in final run
Stage013 -> not started in final run
tensorial IBP -> not started
total derivative reduction -> not promoted
full tensorial sigma_abc correctness -> not claimed
```

## Current State

Loop 009 infrastructure is complete and verified.  The sigma_abc production
run is paused at Stage 011 pending real reviewer quota reset.

Recommended next command after quota reset:

```bash
python3 scripts/resume_pending_reviews.py --project sigma_abc --from-pending
```

