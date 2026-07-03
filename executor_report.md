# Executor Report — TASK_024 Patch (Reviewer Verdict FAIL)

## Status: COMPLETE

Four blocking issues from the reviewer verdict addressed. No new scope. No
edit to forbidden files (no scientific artifacts, frozen checkpoints,
completed-stage validation, signoff ledgers, and the
`docs/devlog/audits/SYMBOLIC_SIMPLIFICATION_LOOP_PROGRESS_REVIEW_BUILD_REPORT.md`
file was excluded from the patch).

## changed_files

- [loop_engine/run_diagnosis.py](loop_engine/run_diagnosis.py)
  - Removed the unreachable duplicated `_derive_next_action` body that
    landed between `inspect_run_root`'s `return` and the next section
    divider during the original TASK_024 patch.
  - Added `_classify_missing_decision_checkpoint(stage)` — emits a
    single `MISSING_REQUIRED_FILE` finding (with one evidence entry per
    missing file) when a stage passes every gate (validation, review,
    completion matrix `COMPLETE` + `freeze_eligible=True`, valid
    `APPROVE_FREEZE` signoff) **and** the matrix is genuinely fresh
    against current on-disk basis files, but `.loop/decision.json`
    and/or `.loop/checkpoint_manifest.json` are missing. The freshness
    guard means we defer to `FREEZE_PRECONDITION_FAILED` when the matrix
    is stale instead of stealing its precedence slot.
  - Wired the new classifier into `diagnose_run` right after
    `_classify_freeze_preconditions`.
  - Restructured the run-root discovery guard in `diagnose_run` so
    `inspect_run_root` runs whenever `--run-root` is provided, including
    when an explicit `--stage` is also given. When stage is explicit,
    `target_stage` stays the explicit path; the report now always
    surfaces `subject.run_root`, run-root discovery `evidence`, and
    `subject.discovered_stage_count` / `subject.frozen_checkpoint_count`.
  - Added `subject.explicit_stage = True` only when the caller passed an
    explicit `--stage`, so consumers can distinguish auto-resolved from
    explicit cases.
  - `subject.selected_stage` / `subject.stage_selection_reason` /
    `subject.stage_order_source` are now populated only in the
    auto-resolved branch, so explicit-stage consumers aren't confused by
    a `selected_stage` that points somewhere they didn't ask about.

- [tests/test_run_root_diagnosis.py](tests/test_run_root_diagnosis.py)
  - New regression test `test_run_root_happy_gates_missing_decision_and_checkpoint`
    builds a stage with PASS validation, PASS review, real
    `build_completion_matrix`-built matrix, valid `APPROVE_FREEZE`
    signoff, no decision.json and no checkpoint_manifest.json. Asserts
    primary != `UNKNOWN_FAILURE` and that primary ==
    `MISSING_REQUIRED_FILE`, with evidence pointing at both missing
    files, and that the recommended next action is `PRODUCE_BASIS_FILES`.
  - New regression test `test_run_root_plus_explicit_stage_collects_run_root_evidence`
    passes both `--run-root` (containing a failing stage) and an explicit
    `--stage` (healthy). Asserts `subject.stage_id == "explicit_stage"`,
    `subject.explicit_stage is True`, `subject.run_root` is recorded,
    and that run-root labels (`run_root`, `stages_dir`, `selected_stage`)
    appear in `evidence`. Primary stays driven by the explicit stage
    (`HUMAN_SIGNOFF_REQUIRED`, not `VALIDATION_GATE_FAILED`).
  - Updated `test_run_root_explicit_stage_overrides_run_root_selection`
    to assert the new contract (`explicit_stage`, run-root evidence
    labels, `HUMAN_SIGNOFF_REQUIRED`).
  - Added a local `_signoff` helper (self-contained: does not depend on
    `tests/test_run_failure_diagnosis.py`).
  - Added `import yaml` at top.

No edits to: `schemas/next_action_report.schema.json`, any
`scientific_*`, `sigma_abc/checkpoints/`, raw provenance tables,
`.loop/human_signoff.yaml` / `_ledger.jsonl` / `_history/`, or
`docs/devlog/audits/SYMBOLIC_SIMPLIFICATION_LOOP_PROGRESS_REVIEW_BUILD_REPORT.md`.

## tests_run

```
python -m pytest tests/test_run_failure_diagnosis.py
python -m pytest tests/test_run_root_diagnosis.py
python -m pytest tests/ -x --ignore=tests/test_autonomous_loop_runner.py --ignore=tests/test_runner_output_isolation_smoke.py -q
rm -rf /tmp/loop_diag_runroot_smoke
python scripts/diagnose_run_failure.py --run-root smoke_projects/mock_polynomial_loop --output-dir /tmp/loop_diag_runroot_smoke
python -c "from pathlib import Path; from loop_engine.schemas import load_and_validate; load_and_validate(Path('/tmp/loop_diag_runroot_smoke/next_action_report.json'), 'next_action_report'); print('run-root next_action_report schema PASS')"
```

## tests_passed

- `python -m pytest tests/test_run_failure_diagnosis.py` → **29 passed**
- `python -m pytest tests/test_run_root_diagnosis.py` → **25 passed**
  (was 23 before the patch; +2 new regression tests)
- Combined focused run: **54 passed in 5.75s**
- Full suite (`tests/` minus the two slow runner modules):
  **346 passed in 69.26s** (was 344 before the patch; +2 net)
- CLI smoke for `--run-root`: exit 0; wrote both files
- `load_and_validate('/tmp/loop_diag_runroot_smoke/next_action_report.json', 'next_action_report')` →
  **`run-root next_action_report schema PASS`**

## tests_failed

None.

## unresolved_issues

None.

## scope_deviation

- Added a matrix-freshness guard inside
  `_classify_missing_decision_checkpoint` so the new classifier only
  fires when the matrix is genuinely up-to-date against current on-disk
  basis files. Without this guard the new helper would have stolen
  precedence from `FREEZE_PRECONDITION_FAILED` in the
  `test_freeze_precondition_failed_after_signoff_present` TASK_023
  test, which deliberately constructs a stage with a stale matrix + a
  missing signoff of decision/checkpoint artifacts. Considered tight
  to the reviewer's intent (actionable diagnosis instead of
  `UNKNOWN_FAILURE`) rather than scope expansion: the helper does what
  the reviewer asked, but only on the inputs the reviewer described.
- The TASK_024 spec already permitted "use existing failure class such
  as `MISSING_REQUIRED_FILE` if adding new enum values is too invasive";
  no new classification code was added and no schema change was made.

## recommended_next_action

Land as-is. All four blocking issues fixed; existing TASK_023 and
TASK_024 tests still pass; full suite still green; the devlog audit
file excluded from the patch as required.
