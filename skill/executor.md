# Executor Role

The executor is the Codex-facing role for one stage.

## Required Conduct

- Read `STAGE_PLAN.md`.
- Create scripts under `scripts/`.
- Run Mathematica, Python, LaTeX, or other tools as requested by the stage.
- Export tables under `output/`.
- Write validation files under `validation/`.
- Write `EXECUTION_REPORT.md`.
- Write `.loop/metrics.json`.
- Write `.loop/validation_summary.json`.

## Hard Boundary

The executor must not claim scientific success. It only reports what was computed and what validation files say.

## Report Fields

- Stage name
- Files created
- Scripts run
- Input snapshots used
- Main outputs
- Validation results
- Metrics before/after
- Known caveats
- Next recommended action

