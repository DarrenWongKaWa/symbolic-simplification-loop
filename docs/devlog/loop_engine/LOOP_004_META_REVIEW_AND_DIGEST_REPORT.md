# Loop 004 Meta Review And Digest Report

## Branch

`loop_004_scientific_metareviewer_and_stage_digest`

## Scope

This branch extends the loop infrastructure only.  It does not modify
`sigma_abc` physics, does not start a new `sigma_abc` stage, does not change
frozen checkpoints, and does not claim full tensorial
`\sigma_{\mu\alpha\beta}` correctness.

## Files Added

- `SCIENTIFIC_REVIEWER_AUDIT.md`
- `skill/scientific_metareviewer.md`
- `schemas/meta_review_result.schema.json`
- `templates/META_REVIEW_RESULT.template.json`
- `templates/HUMAN_READABLE_REVIEW.template.md`
- `templates/STAGE_SUMMARY.template.md`
- `templates/STAGE_SUMMARY.template.tex`
- `loop_engine/meta_review.py`
- `loop_engine/stage_digest.py`
- `scripts/run_scientific_metareviewer.py`
- `scripts/build_stage_digest.py`
- `tests/test_meta_review_and_digest.py`
- `reports/stage_010_retrospective_summary.md`
- `reports/stage_010_retrospective_summary.tex`
- `reports/stage_010_retrospective_summary.pdf`

## Files Updated

- `scripts/run_autonomous_loop.py`
- `loop_engine/decision.py`
- `loop_engine/checkpoint.py`
- `profiles/test_safe_loop.yaml`
- `profiles/sigma_abc_safe_pre_fusion.yaml`
- `profiles/sigma_abc_pair_basis_refinement.yaml`
- `profiles/sigma_abc_pair_kernel_fusion_pilot.yaml`
- `profiles/sigma_abc_center_sector_pilot.yaml`
- `profiles/sigma_abc_loop_orbit_canonicalization_pilot.yaml`
- `tests/test_decision_engine.py`

## Meta-Review Behavior

The ordinary reviewer loop remains:

```text
AlgebraReviewer + PhysicsReviewer + SoftwareReviewer -> .loop/review_result.json
```

The new meta-review layer runs after ordinary reviewer aggregation and before
decision/freeze:

```text
.loop/validation_summary.json
.loop/review_result.json
.loop/reviewer_results/*.json
EXECUTION_REPORT.md
CLAIM_BOUNDARY.md
review_packet.md
  -> .loop/meta_review_result.json
  -> reports/human_readable_review.md
```

It enforces:

```text
validation_summary.overall_gate != PASS -> meta verdict cannot be PASS
review_result.verdict == FAILED -> meta verdict cannot be PASS
missing reviewer output -> NEEDS_PATCH
blocking overclaim -> NEEDS_PATCH or FAILED
DCProjectionTo1D inherited-pass caveat must be preserved
```

## Stage Digest Behavior

Every autonomous stage now builds:

```text
reports/stage_summary.md
reports/stage_summary.tex
reports/stage_summary.pdf
reports/stage_summary_build.json
```

If `xelatex` is available, the PDF is compiled.  If it is unavailable, the
builder records `PDFCompileStatus -> SKIPPED_XELATEX_UNAVAILABLE` while still
writing Markdown and TeX.

## Checkpoint Manifest Integration

Checkpoint manifests now include:

```text
.loop/meta_review_result.json
reports/human_readable_review.md
reports/stage_summary.md
reports/stage_summary.tex
reports/stage_summary.pdf
reports/stage_summary_build.json
```

The manifest also stores `meta_review_result` and `stage_digest_artifacts`.

## Stage 010 Retrospective Digest

The retrospective digest was generated from the archived Stage 010 report:

```text
reports/stage_010_retrospective_summary.md
reports/stage_010_retrospective_summary.tex
reports/stage_010_retrospective_summary.pdf
```

It preserves:

```text
Stage 010 PASS as pair-sector-only row-provenance kernel-family fusion pilot.
912 pair rows -> 3 band-pair families.
PairFusionDifference -> 0.
XXXPairProjectionRegression -> PASS.
No IBP was started.
No total derivative was introduced.
No full tensorial sigma_{mu alpha beta} correctness was claimed.
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Commands Run

```bash
python3 -m pytest tests/test_meta_review_and_digest.py -q
python3 -m pytest tests/test_decision_engine.py tests/test_meta_review_and_digest.py -q
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
python3 -m pytest tests/test_schema_validation.py -q
python3 scripts/build_stage_digest.py --stage010-retrospective
python3 scripts/run_autonomous_loop.py --project mock --profile test_safe_loop --clean
python3 scripts/run_autonomous_loop.py --project mock_validation_fail --profile test_safe_loop --clean
python3 scripts/run_autonomous_loop.py --project mock_missing_reviewer --profile test_safe_loop --clean
```

## Smoke Test Results

```text
mock autonomous loop -> FREEZE
meta_review_result.json created -> True
human_readable_review.md created -> True
stage_summary.md/tex/pdf created -> True
checkpoint manifest includes digest artifacts -> True
validation failure blocks freeze -> True
missing reviewer blocks freeze -> True
Stage 010 retrospective digest created -> True
```

## How Future Sigma ABC Stages Should Run

Use the existing autonomous runner and an approved profile:

```bash
python3 scripts/run_autonomous_loop.py --project sigma_abc --profile <approved_profile> --from-current-checkpoint
```

For dry-run inspection:

```bash
python3 scripts/run_autonomous_loop.py --project sigma_abc --profile <approved_profile> --dry-run --from-current-checkpoint
```

The runner now performs:

```text
stage execution
ordinary reviewer aggregation
ScientificMetaReviewer
stage digest build
decision
checkpoint freeze if all gates pass
```

## Claim Boundary

Allowed:

- Claim that the loop infrastructure now supports repo-local scientific
  meta-review.
- Claim that autonomous mock stages can freeze without manual ChatGPT
  copy-paste review.
- Claim that each frozen autonomous stage can carry a short human-readable
  Markdown/TeX/PDF digest.

Forbidden:

- Do not claim `sigma_abc` physics was advanced in this branch.
- Do not claim full tensorial `sigma_{\mu\alpha\beta}` correctness.
- Do not claim tensorial kernel fusion or tensorial IBP started.
- Do not erase the inherited DC projection caveat.

## Persistent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
