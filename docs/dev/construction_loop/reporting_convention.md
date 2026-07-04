# Reporting Convention

This document defines the **canonical reporting layout** for every
construction-loop task in this repository. It is the entry point that all
Planners, Executors, Reviewers, HumanIntegrators, and downstream audits must
follow.

It does not implement reporting automation. It defines what reports exist,
where they live, and what each one means.

## Purpose

The TASK_030 audit found that report artifacts lived at multiple inconsistent
locations:

```text
root executor_report.md
docs/dev/construction_loop/executor_report.md
docs/dev/construction_loop/loop_engineering_probe_report.md
reports/TASK_030_loop_meta_loop_audit/
```

This convention collapses those into one canonical layout and introduces
optional task-dependent subdirectories for human-readable outputs.

## Canonical task report directory

Every construction-loop task must use exactly one canonical report directory:

```text
reports/TASK_XXX_<NAME>/
```

Use the task ID and a short uppercase name. Examples:

```text
reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/
reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/
reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/
```

The legacy short form `reports/TASK_XXX/` (without `<NAME>`) may appear in
older artifacts as shorthand but is not the canonical form for new tasks.

## Required report artifacts

The minimum set of report files every construction-loop task must produce:

```text
reports/TASK_XXX_<NAME>/PLAN.md
reports/TASK_XXX_<NAME>/executor_report.md
reports/TASK_XXX_<NAME>/review_result.json
reports/TASK_XXX_<NAME>/landing_report.md
reports/TASK_XXX_<NAME>/audit_evidence.md
reports/TASK_XXX_<NAME>/final_summary.md
reports/TASK_XXX_<NAME>/build.log
```

Roles produce these files:

| File                  | Producer        | Purpose                                              |
| --------------------- | --------------- | ---------------------------------------------------- |
| `PLAN.md`             | Planner         | Bounded plan, allowed/forbidden edits, validation.   |
| `executor_report.md`  | Executor        | What changed, commands run, scope checks.            |
| `review_result.json`  | Reviewer        | Verdict (`PASS`, `PASS_WITH_CAVEAT`, `FAIL`).        |
| `landing_report.md`   | HumanIntegrator | Staged files, diff summary, commit recommendation.   |
| `audit_evidence.md`   | Any role        | Optional traceability evidence for audits.           |
| `final_summary.md`    | HumanIntegrator | Short handoff summary for downstream review.         |
| `build.log`           | Any role        | Only written if a build/render command actually ran. |

Markdown and JSON files are for machine-assisted review and audit
traceability. LaTeX/PDF outputs are for human review — see
[Human-readable outputs](#human-readable-outputs).

## Lifecycle markers

For agent-bus mode, the lifecycle also requires ready and failed markers
alongside the reports:

```text
agent_bus/<role>/outbox/<ROLE>_READY
agent_bus/<role>/failed/<role>_failed.md
```

Manual session mode does not emit these markers; handoff is conversational
plus the report files.

## Human-readable outputs

Some tasks require human-readable engineering or scientific review that
Markdown and JSON alone cannot provide. For those tasks, the report
directory may also contain:

```text
reports/TASK_XXX_<NAME>/human_review/
reports/TASK_XXX_<NAME>/supplement/
```

These are task-dependent subdirectories and should be created only when the
task actually requires them.

### human_review/ — engineering audit

Use `human_review/` for engineering audits such as:

```text
loop / meta-loop audit
role-card audit
file-location audit
automation safety audit
probe scaffold audit
merge policy audit
```

Recommended files when used:

```text
reports/TASK_XXX_<NAME>/human_review/engineering_audit.tex
reports/TASK_XXX_<NAME>/human_review/engineering_audit.pdf
reports/TASK_XXX_<NAME>/human_review/build.log
```

Required sections, when this format is used:

```text
1. Executive Summary
2. Direct Answers
3. Scope and Non-goals
4. Evidence Sources
5. Architecture / Workflow Diagram
6. Role-card Completeness Matrix
7. File-location Contract Audit
8. Human-readable Output Audit
9. Safety Boundary / Forbidden Paths
10. Automation Readiness Assessment
11. Risks and Caveats
12. Recommended Next Tasks
13. Human Decision Checklist
```

Allowed status words in such audits:

```text
COMPLETE
PARTIAL
MISSING
PROBE_ONLY
DO_NOT_USE_YET
PASS
PASS_WITH_CAVEAT
FAIL
```

### supplement/ — theoretical derivation

Use `supplement/` for theoretical / scientific derivation tasks such as:

```text
symbolic simplification
sigma_xxx / sigma_abc derivation
normal-form reduction
coefficient extraction
validation ledger
checkpoint-ready mathematical report
```

Recommended files when used:

```text
reports/TASK_XXX_<NAME>/supplement/theoretical_derivation_supplement.tex
reports/TASK_XXX_<NAME>/supplement/theoretical_derivation_supplement.pdf
reports/TASK_XXX_<NAME>/supplement/build.log
reports/TASK_XXX_<NAME>/supplement/symbol_dictionary.tex
reports/TASK_XXX_<NAME>/supplement/validation_ledger_table.tex
reports/TASK_XXX_<NAME>/supplement/kernel_appendix.tex
reports/TASK_XXX_<NAME>/supplement/stage_to_derivation_map.md
reports/TASK_XXX_<NAME>/supplement/input_snapshot_manifest.wl
```

Required sections, when this format is used:

```text
1. Scientific Claim Boundary
2. Starting Formula / Input Snapshot
3. Notation and Symbol Dictionary
4. Stage-to-Derivation Map
5. Algebraic Transformation Ledger
6. Normal Form / Reduced Form
7. Residual Terms and Failed Reductions
8. Validation Ledger
9. Benchmark / Regression Results
10. Allowed Claims
11. Not Claimed
12. Reproducibility Notes
13. Appendix: Full Kernels / Coefficient Tables
```

This convention must require explicit statements of:

```text
Old expression
New expression
identity checked: Old - New = 0
or: Old - New - dF = 0
validation command
validation artifact
max error, if numerical
exact symbolic result, if symbolic
checkpoint status
review status
claim boundary
```

Conservative claim-boundary examples:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
No full tensorial sigma_abc correctness is claimed unless directly validated.
No total-derivative / IBP reduction is promoted unless the active profile allows it.
```

## Pointer to deeper standards

The role-card, engineering audit PDF, and theoretical derivation supplement
standards are defined in the master repair framework:

```text
docs/dev/construction_loop/loop_meta_loop_repair_framework.md
```

This convention intentionally points there rather than duplicating those
standards. Later tasks may split each standard into its own dedicated doc.

## Legacy report paths

For traceability, the legacy locations are deprecated for new content:

```text
root executor_report.md                                       = legacy / discouraged
docs/dev/construction_loop/executor_report.md                 = bootstrap history only
docs/dev/construction_loop/loop_engineering_probe_report.md  = probe evidence only
```

New content must use the canonical `reports/TASK_XXX_<NAME>/` layout. Future
work may rename or move legacy files into the canonical layout under a
dedicated task.

## Source of truth

If this convention conflicts with a later human-approved plan, the later plan
wins for the specific task it covers. If this convention conflicts with the
master repair framework
(`docs/dev/construction_loop/loop_meta_loop_repair_framework.md`), the master
framework wins for the repair sequence; report the conflict in the task
report.