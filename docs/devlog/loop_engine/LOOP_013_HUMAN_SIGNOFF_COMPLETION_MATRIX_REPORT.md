# Loop 013: Human Signoff Completion Matrix

## Status

PASS.

Loop 013 implements a stage-level completion matrix and lightweight human
signoff protocol. Human signoff is now an evidence-bounded state-machine node:

```text
STAGE_PLAN
-> validation_summary
-> review_result / boundary_audit
-> completion_matrix
-> human scientist signoff
-> freeze_preconditions
-> checkpoint manifest
```

## New Invariants

Human signoff cannot override failed validation, failed review, stale evidence,
or unsafe boundary audit.

`DO_NOT_FREEZE_PATCH` is a valid signoff decision, but it blocks freeze and only
permits patch-loop continuation.

`APPROVE_FREEZE_WITH_CAVEAT` requires explicit accepted caveats.

`completion_matrix.freeze_eligible` is display-only. The authoritative gate
remains `loop_engine.state.freeze_preconditions`.

## Files Added

```text
schemas/completion_matrix.schema.json
schemas/human_signoff.schema.json
loop_engine/completion_matrix.py
loop_engine/human_signoff.py
scripts/sign_stage.py
scripts/migrate_human_signoff.py
tests/test_loop013_human_signoff_completion_matrix.py
LOOP_013_HUMAN_SIGNOFF_COMPLETION_MATRIX_REPORT.md
```

## Files Modified

```text
loop_engine/state.py
loop_engine/checkpoint.py
loop_engine/stage_digest.py
scripts/run_stage.py
scripts/run_autonomous_loop.py
scripts/freeze_checkpoint.py
README.md
profiles/test_safe_loop.yaml
profiles/test_hypothesis_search_loop.yaml
profiles/sigma_abc_safe_pre_fusion.yaml
profiles/sigma_abc_pair_kernel_fusion_pilot.yaml
tests/test_checkpoint_manifest.py
```

The test-only profile auto-signoff path is active only under pytest through
`PYTEST_CURRENT_TEST`; normal production runs still require explicit signoff.

## Validation

```text
python3 -m pytest -q
-> 146 passed, 1 warning
```

```text
python3 -m compileall loop_engine scripts tests
-> PASS
```

Targeted Loop 013 tests:

```text
python3 -m pytest -q tests/test_loop013_human_signoff_completion_matrix.py
-> 10 passed, 1 warning
```

Relevant regression group:

```text
python3 -m pytest -q tests/test_checkpoint_manifest.py tests/test_meta_review_and_digest.py tests/test_autonomous_loop_runner.py
-> 23 passed, 1 warning
```

## 012C Regression Semantics

The Loop 013 tests enforce the intended 012C semantics:

```text
Stage012AArtifactPresent -> FAILED
Stage012BArtifactPresent -> FAILED
UsesStage012ALoopLedger -> FAILED
UsesStage012BHypothesisLedger -> FAILED
RealLoopCandidateReady -> FAILED
RecommendedHumanAction -> DO_NOT_FREEZE_PATCH
```

These are dependency/readiness failures, not boundary-audit failures.

Boundary audit remains safe when:

```text
overclaim_detected -> false
full_tensorial_claim_detected -> false
ibp_started_without_approval -> false
dc_caveat_preserved -> true
```

Even if a blocked 012C preparation stage is manually changed to
`APPROVE_FREEZE`, `freeze_preconditions` still rejects freeze because the
completion matrix contains blocking incomplete dependency/readiness items.

## Sigma ABC Boundary Check

No forbidden downstream artifacts were generated:

```text
sigma_abc_012c_loop_orbit_canonicalization_promotion=False
sigma_abc_013_global_pre_ibp_assembly=False
sigma_abc_tensorial_ibp_reduction=False
```

The permanent caveat remains preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Human Signoff CLI

The new chat-friendly signing protocol is:

```bash
python scripts/sign_stage.py --stage path/to/stage <<'EOF'
SIGNOFF stage=sigma_abc_012c_real_loop_candidate_preparation
decision=DO_NOT_FREEZE_PATCH
reason=Stage012A/012B artifacts are missing; boundary audit is safe; caveats preserved.
signed_by=wangjiahua
EOF
```

Legacy migration:

```bash
python scripts/migrate_human_signoff.py --stage path/to/stage
```

## Remaining Caveats

Loop 013 changes freeze governance only. It does not start 012C promotion,
Stage 013 global pre-IBP assembly, tensorial IBP, or total-derivative
reduction. It also does not claim full tensorial
`\sigma_{\mu\alpha\beta}` correctness.

