# Task ID

TASK_024

# Title

Run-Root Diagnosis for Autonomous Loop Outputs

# Problem

`TASK_023` added `scripts/diagnose_run_failure.py`, but `--run-root` is currently mostly metadata. Diagnosis remains effectively stage-oriented or command-oriented. Future meta-loop callers need to pass only an autonomous run root and still receive a useful deterministic `next_action_report.json`.

This is not enough for autonomous loop supervision because run-level outputs contain multiple stage directories, run reports, checkpoint state, and partial artifacts. The diagnosis layer should identify the active/latest failing stage where possible, detect missing stage gate artifacts, and classify the next action without requiring the human to locate the stage manually.

# Goal

Strengthen `--run-root` diagnosis so autonomous loop outputs are useful inputs on their own.

When called with `--run-root`, the tool must:

- Inspect run-level autonomous loop artifacts.
- Identify the current/latest relevant stage deterministically where possible.
- Detect missing validation, review, completion matrix, signoff, decision, and checkpoint artifacts.
- Reuse stage-level diagnosis once a target stage is selected.
- Emit a schema-valid `next_action_report.json` and markdown report.
- Preserve the read-only diagnostic boundary.

# Non-goals

- Do not change TASK_023 behavior for explicit `--stage`.
- Do not change scientific validation, review, completion matrix, signoff, freeze, or checkpoint semantics.
- Do not auto-run validation, reviewers, completion-matrix generation, signoff, freeze, or patch planning.
- Do not infer scientific correctness from run report prose.
- Do not repair missing artifacts.
- Do not modify TASK_023 task/spec files.

# Allowed edits

- `loop_engine/run_diagnosis.py`
- `scripts/diagnose_run_failure.py`
- `schemas/next_action_report.schema.json`, only if needed for backward-compatible run-root fields
- `tests/test_run_failure_diagnosis.py` or a new focused test file such as `tests/test_run_root_diagnosis.py`
- Smoke fixtures under `tests/fixtures/run_diagnosis/` or `tmp_path` generated fixtures
- Minimal documentation comments in the diagnosis module or tests

# Forbidden edits

- Do not edit scientific artifacts.
- Do not edit files under `sigma_abc/checkpoints/`.
- Do not edit frozen checkpoint manifests.
- Do not edit raw provenance tables.
- Do not edit validated `sigma_abc` outputs.
- Do not edit `.loop/human_signoff.yaml`.
- Do not edit `.loop/human_signoff_ledger.jsonl`.
- Do not edit `.loop/human_signoff_history/`.
- Do not modify unrelated untracked devlog audit files.
- Do not weaken existing schemas or freeze precondition logic.

# Implementation steps

1. Add run-root discovery logic.

Implement a pure helper such as `inspect_run_root(run_root: Path, project: str | None = None) -> dict`.

It should discover:

- `AUTONOMOUS_LOOP_RUN_REPORT.md`
- `stages/`
- `checkpoints/`
- stage directories under `stages/*`
- per-stage `.loop/validation_summary.json`
- per-stage `.loop/review_result.json`
- per-stage `.loop/decision.json`
- per-stage `reports/completion_matrix.json`
- per-stage `.loop/human_signoff.yaml`
- per-stage `.loop/checkpoint_manifest.json`

2. Determine stage order deterministically.

Use this precedence:

- If `--project` is provided and `projects/<project>/loop.yaml` exists, use its `stages[].id` order.
- Else if `run_root.name` maps to `projects/<run_root.name>/loop.yaml`, use that order.
- Else sort discovered stage directory names lexicographically.

Do not use modification time as the primary ordering signal.

3. Select the run-root diagnosis target stage.

Implement deterministic selection:

- If any ordered stage has validation/review/decision/completion artifacts showing failure or blocked status, select the first such stage.
- Else select the first ordered stage missing required gate artifacts after it appears to have started.
- Else select the first ordered stage without a checkpoint manifest when prior ordered stages are frozen.
- Else, if all discovered stages appear frozen, select the last ordered stage and classify the run as no known failure or `UNKNOWN_FAILURE` with evidence that no failure was found.
- If no stage directories exist, classify as `MISSING_REQUIRED_FILE`.

4. Define run-level required and optional artifacts.

For run-root-only diagnosis:

Required minimum:

- `run_root` exists
- `run_root/stages/` exists
- at least one stage directory exists

Optional but useful evidence:

- `AUTONOMOUS_LOOP_RUN_REPORT.md`
- `checkpoints/`
- run-level stdout/stderr/status inputs from TASK_023 command metadata

Missing optional run report should not automatically fail if stage artifacts are available. Missing `stages/` or no stages should classify as `MISSING_REQUIRED_FILE`.

5. Integrate with existing stage diagnosis.

Once a target stage is selected, call the existing stage-level diagnosis path rather than duplicating validation/review/completion/signoff logic.

The final report should include run-root metadata:

- `subject.run_root`
- `subject.project`, if known
- `subject.selected_stage`
- `subject.stage_selection_reason`
- `subject.stage_order_source`

6. Add run-root artifact health evidence.

The report should include evidence entries for:

- run report present/missing
- stages directory present/missing
- discovered stage count
- selected stage
- selected stage missing artifacts
- frozen checkpoint count
- stage order source

7. Preserve existing classification vocabulary.

Do not introduce new primary classification codes unless absolutely necessary. Use existing TASK_023 codes:

- Missing `stages/` or no stage dirs -> `MISSING_REQUIRED_FILE`
- Invalid run/stage JSON artifact -> `SCHEMA_VALIDATION_FAILED`
- Selected stage validation failed -> `VALIDATION_GATE_FAILED`
- Selected stage review failed -> `REVIEW_GATE_FAILED`
- Completion matrix unhealthy -> `COMPLETION_MATRIX_UNHEALTHY`
- Otherwise-freezable stage missing signoff -> `HUMAN_SIGNOFF_REQUIRED`
- Freeze precondition failure -> `FREEZE_PRECONDITION_FAILED`
- Boundary approval issue -> `BOUNDARY_APPROVAL_REQUIRED`
- Nonzero command with no better run evidence -> `COMMAND_FAILED`
- No known failure -> `UNKNOWN_FAILURE`

8. Update CLI behavior.

`python scripts/diagnose_run_failure.py --run-root PATH --output-dir OUT` should work without `--stage`.

If both `--run-root` and `--stage` are provided:

- Prefer explicit `--stage` for classification.
- Still include run-root metadata as contextual evidence.
- Do not let run-root selection override explicit stage selection.

9. Add tests.

Cover at least:

- Run root missing `stages/` -> `MISSING_REQUIRED_FILE`.
- Run root with no stage dirs -> `MISSING_REQUIRED_FILE`.
- Run root with one stage missing validation summary -> `MISSING_REQUIRED_FILE`.
- Run root with validation failure stage -> selects that stage and returns `VALIDATION_GATE_FAILED`.
- Run root with review failure stage -> selects that stage and returns `REVIEW_GATE_FAILED`.
- Run root with unhealthy completion matrix -> `COMPLETION_MATRIX_UNHEALTHY`.
- Run root with validation/review/completion pass but missing human signoff -> `HUMAN_SIGNOFF_REQUIRED`.
- Run root with multiple stages selects the first failing/blocked stage by loop order, not filesystem mtime.
- `--project mock` uses `projects/mock/loop.yaml` ordering.
- CLI writes schema-valid JSON and markdown for run-root-only invocation.
- Diagnosis does not create or modify signoff ledgers, checkpoint manifests, scientific outputs, or validated sigma artifacts.

# Acceptance commands

```bash
python -m pytest tests/test_run_failure_diagnosis.py
python -m pytest tests/test_run_root_diagnosis.py
python scripts/diagnose_run_failure.py --run-root smoke_projects/mock_polynomial_loop --output-dir /tmp/loop_diag_runroot_smoke
python - <<'PY'
from pathlib import Path
from loop_engine.schemas import load_and_validate
load_and_validate(Path('/tmp/loop_diag_runroot_smoke/next_action_report.json'), 'next_action_report')
print('run-root next_action_report schema PASS')
PY
```

# Expected output files

- Updated `loop_engine/run_diagnosis.py`
- Updated `scripts/diagnose_run_failure.py`
- Optional backward-compatible update to `schemas/next_action_report.schema.json`
- Updated or new pytest file for run-root diagnosis
- Optional fixtures under `tests/fixtures/run_diagnosis/`
- Runtime outputs:
  - `next_action_report.json`
  - `next_action_report.md`

# Risks

- Stage selection can be ambiguous when run roots contain manually copied or partial stage directories. Mitigate with explicit `stage_selection_reason` and deterministic ordering.
- Parsing run report prose can be brittle. Mitigate by treating run reports as evidence only, not as the source of truth when structured artifacts exist.
- Run-root-only diagnosis may classify missing artifacts as failures even for intentionally prepared but unstarted stages. Mitigate by selecting only discovered stage directories and reporting missing basis clearly.
- Adding schema fields can break TASK_023 tests if not backward compatible. Keep new run-root fields optional or inside existing `subject`/`evidence` structures.

# Definition of done

TASK_024 is done when:

- `--run-root` alone produces useful, deterministic diagnosis for autonomous loop outputs.
- The selected stage and selection reason are recorded in `next_action_report.json`.
- Missing validation/review/completion/signoff artifacts are detected from run-root context.
- Existing explicit `--stage` diagnosis behavior remains compatible.
- JSON output validates against `next_action_report.schema.json`.
- Markdown output explains the selected stage, evidence, classification, next action, and forbidden actions.
- Tests cover run-root-only diagnosis, multi-stage selection, schema validation, and read-only guarantees.
- No scientific artifacts, frozen checkpoints, human signoff ledgers, or validated `sigma_abc` outputs are modified.
