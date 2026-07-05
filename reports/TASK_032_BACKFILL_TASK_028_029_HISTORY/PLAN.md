# PLAN.md - TASK_032_BACKFILL_TASK_028_029_HISTORY

## Task ID

TASK_032_BACKFILL_TASK_028_029_HISTORY

## Task Title and Objective

Backfill Task History for TASK_028 and TASK_029.

Objective: create the missing canonical task-history files for the already
completed TASK_028 and TASK_029 work, using repository evidence only. This task
must preserve history as it exists; it must not rewrite completed
implementation docs, alter commits, or reinterpret the work beyond the source
artifacts.

## Source-of-truth Inputs

The executor must use these repository files and commits as source-of-truth
inputs:

- `docs/dev/construction_loop/planner.role.md`
- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- Current TASK_031 artifacts:
  - `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/PLAN.md`
  - `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/executor_report.md`
  - `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/review_result.json`
  - `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/landing_report.md`
- TASK_028 historical evidence:
  - `git show c40622b --stat --oneline`
  - `git show c40622b:docs/dev/construction_loop/executor_report.md`
- TASK_029 historical evidence:
  - `git show fa93695 --stat --oneline`
  - `docs/dev/construction_loop/executor_report.md`
  - `git show fa93695:docs/dev/construction_loop/executor_report.md`, if the
    current file changes before execution
- Existing task files used only for local formatting convention:
  - `tasks/TASK_024.md`
  - `tasks/TASK_025_BACKFILL.md`
  - `tasks/TASK_026.md`
  - `tasks/TASK_027.md`

Repo-state observation to preserve: the landing report for TASK_031 records
that the HumanIntegrator did not commit, but current repository HEAD is
`f900ff8 docs: add task 031 safety and reporting conventions`. Treat the git
log as source of truth and mention this only as a non-blocking reporting
inconsistency if it is relevant to the TASK_032 executor report.

## Problem

The master repair framework says TASK_028 and TASK_029 were executed, but their
canonical task files are absent from `tasks/`. The current repo confirms:

```text
tasks/TASK_028_CONSTRUCTION_LOOP_DOCS.md        missing
tasks/TASK_029_ROLE_FILE_IO_CONTRACTS.md        missing
```

This makes the construction-loop history harder to discover and leaves TASK_028
and TASK_029 tracked mainly through executor reports and commits.

## Goal

Create two backfilled task-history files:

```text
tasks/TASK_028_CONSTRUCTION_LOOP_DOCS.md
tasks/TASK_029_ROLE_FILE_IO_CONTRACTS.md
```

Each file must summarize the already-completed task using repository evidence
and must include:

```text
context
problem
goal
allowed edits
forbidden edits
actual changed files
review result summary
commit/status note
lessons learned
```

The task must also produce the standard executor report for TASK_032.

## In-scope Files or File Areas

The executor may create or edit only:

- `tasks/TASK_028_CONSTRUCTION_LOOP_DOCS.md`
- `tasks/TASK_029_ROLE_FILE_IO_CONTRACTS.md`
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/executor_report.md`
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/audit_evidence.md`, only if
  useful for traceability
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/final_summary.md`, only if
  useful for handoff
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/build.log`, only if a build
  or render command is actually run

The executor may read historical commits and existing docs, but must not edit
the completed TASK_028/TASK_029 implementation files.

## Explicit Out-of-scope Files and Directories

Do not edit:

- `docs/dev/construction_loop/README.md`
- `docs/dev/construction_loop/checklist.md`
- `docs/dev/construction_loop/executor.role.md`
- `docs/dev/construction_loop/executor_report.md`
- `docs/dev/construction_loop/external_tools.md`
- `docs/dev/construction_loop/human_integrator.role.md`
- `docs/dev/construction_loop/planner.role.md`
- `docs/dev/construction_loop/reviewer.role.md`
- `docs/dev/construction_loop/task_lifecycle.md`
- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/`
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/`
- Any TASK_033 or later task artifacts

Forbidden unless a future bounded human-approved task explicitly allows it:

- `sigma_abc/`
- `checkpoints/`
- validation artifacts
- human signoff ledgers/history/YAML
- `.loop/human_signoff.yaml`
- scientific output files
- `agent_bus/`
- `loop_engine/`
- `schemas/`
- `scripts/`
- `docs/devlog/audits/`
- `LOOP.md`
- `STATE.md`
- `loop-budget.md`
- `loop-run-log.md`
- `.claude/`
- `.github/`
- `patterns/`
- `loop-constraints.md`
- `.gitmodules`
- vendored `loop-engineering*` directories

## Required Safety Conventions

Every role session must start with:

```text
Read the relevant role card first.
```

Before task-specific work, every role session must inspect and record:

```bash
pwd
git branch --show-current
git status --short
git log --oneline -5
```

The global workflow must remain:

```text
Planner -> Executor -> Reviewer -> HumanIntegrator -> human explicit `commit now`
```

Global prohibitions:

- No `git add .`.
- No recursive add-dot staging.
- No commit unless the human explicitly says `commit now`.
- No push.
- No merge.
- No reset.
- No rebase.
- No cherry-pick.
- No auto-freeze.
- No auto-signoff.
- No ci-sweeper.
- No vendored loop-engineering.
- No git submodule.
- No direct scientific/runtime edits.

Current stage strategy:

- Do not write a local runner.
- Do not enable loop-engineering automated loops.
- Do not use GitHub automation.
- Do not merge or vendor loop-engineering scaffold.
- Continue only one bounded task at a time.
- Do not begin TASK_033.
- Do not perform Reviewer or HumanIntegrator duties while executing TASK_032.

## Required Reporting Conventions

Use the canonical report directory:

```text
reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/
```

Required role artifacts for the task lifecycle:

```text
reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/PLAN.md
reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/executor_report.md
reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/review_result.json
reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/landing_report.md
```

Optional artifacts, only when useful or actually generated:

```text
reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/audit_evidence.md
reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/final_summary.md
reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/build.log
```

No `human_review/` or `supplement/` output is required for this backfill task
unless the executor discovers a human-approved reason to stop and re-plan.

## Executor Instructions

1. Read the relevant role card first.
2. Run and record:

   ```bash
   pwd
   git branch --show-current
   git status --short
   git log --oneline -5
   ```

3. Read this plan and the TASK_032 section of:

   ```text
   docs/dev/construction_loop/loop_meta_loop_repair_framework.md
   ```

4. Read:

   ```text
   docs/safety.md
   docs/dev/construction_loop/reporting_convention.md
   docs/dev/construction_loop/README.md
   ```

5. Confirm both target task files are absent before creating them.
6. Use repository evidence to backfill TASK_028:

   ```bash
   git show c40622b --stat --oneline
   git show c40622b:docs/dev/construction_loop/executor_report.md
   ```

7. Use repository evidence to backfill TASK_029:

   ```bash
   git show fa93695 --stat --oneline
   sed -n '1,260p' docs/dev/construction_loop/executor_report.md
   ```

8. Create `tasks/TASK_028_CONSTRUCTION_LOOP_DOCS.md` with the required
   sections listed in this plan.
9. Create `tasks/TASK_029_ROLE_FILE_IO_CONTRACTS.md` with the required
   sections listed in this plan.
10. Keep each backfilled task file factual. Use terms such as "backfilled from
    existing executor report and commit evidence" where appropriate.
11. Do not alter the completed implementation docs from TASK_028 or TASK_029.
12. Write
    `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/executor_report.md`.
13. Run the acceptance commands below.
14. Stop and hand off to Reviewer. Do not stage or commit.

## Acceptance Commands

Executor, Reviewer, and HumanIntegrator should use these commands as
applicable:

```bash
pwd
git branch --show-current
git status --short
git log --oneline -5
test -f tasks/TASK_028_CONSTRUCTION_LOOP_DOCS.md
test -f tasks/TASK_029_ROLE_FILE_IO_CONTRACTS.md
test -f reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/executor_report.md
grep -E "TASK_028|CONSTRUCTION_LOOP_DOCS|construction loop docs" tasks/TASK_028_CONSTRUCTION_LOOP_DOCS.md
grep -E "TASK_029|ROLE_FILE_IO_CONTRACTS|role file" tasks/TASK_029_ROLE_FILE_IO_CONTRACTS.md
grep -E "context|problem|goal|allowed edits|forbidden edits|actual changed files|review result summary|commit/status note|lessons learned" tasks/TASK_028_CONSTRUCTION_LOOP_DOCS.md
grep -E "context|problem|goal|allowed edits|forbidden edits|actual changed files|review result summary|commit/status note|lessons learned" tasks/TASK_029_ROLE_FILE_IO_CONTRACTS.md
git diff --stat
git diff --check
git diff
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe"
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\.claude/|patterns/|\.github/|loop-constraints.md' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
test ! -f .gitmodules
find . -maxdepth 3 -type d -name 'loop-engineering*'
```

Reviewer may also verify historical anchors:

```bash
git show c40622b --stat --oneline
git show fa93695 --stat --oneline
```

## Expected Output Files

Expected executor-created files:

- `tasks/TASK_028_CONSTRUCTION_LOOP_DOCS.md`
- `tasks/TASK_029_ROLE_FILE_IO_CONTRACTS.md`
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/executor_report.md`

Already-created planner artifact:

- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/PLAN.md`

Optional, only if useful and created intentionally:

- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/audit_evidence.md`
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/final_summary.md`
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/build.log`

## Reviewer Checklist

Reviewer must be read-only and must not edit, repair, stage, commit, or push.

Check:

- The executor read the relevant role card first.
- The initial repo inspection commands were run and recorded.
- The two target task files exist under the exact expected names.
- Each target task file includes:
  - context
  - problem
  - goal
  - allowed edits
  - forbidden edits
  - actual changed files
  - review result summary
  - commit/status note
  - lessons learned
- TASK_028 content is grounded in `c40622b` and the historical TASK_028
  executor report.
- TASK_029 content is grounded in `fa93695` and the TASK_029 executor report.
- The task did not rewrite history or alter completed implementation files.
- No TASK_033 artifacts or implementation were started.
- No forbidden paths or probe scaffold paths were touched.
- The executor report exists and includes required fields.
- Acceptance commands passed, or any skipped command is justified.

Reviewer output:

```text
reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/review_result.json
```

Required verdicts:

```text
PASS
PASS_WITH_CAVEAT
FAIL
```

## HumanIntegrator Checklist

HumanIntegrator must proceed only after Reviewer `PASS` or
`PASS_WITH_CAVEAT` with no blocking issues.

Check:

- Read the relevant role card first.
- Run and record the initial repo inspection commands.
- Confirm reviewer verdict and absence of blocking issues.
- Stage only exact TASK_032 approved paths.
- Do not use `git add .`.
- Do not stage unrelated dirty files.
- Do not commit until the human explicitly says `commit now`.
- Do not push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff.
- Write:

  ```text
  reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/landing_report.md
  ```

Landing report must include staged files, excluded files, forbidden path check,
staged diff summary, unresolved issues, recommended commit message, and
`final_recommendation: COMMIT` or `DO_NOT_COMMIT`.

Because `reports/` artifacts may be ignored by Git, HumanIntegrator may need
explicit path force-staging for TASK_032 report files only. Recursive add-dot
staging remains forbidden.

## Acceptance Criteria

- `tasks/TASK_028_CONSTRUCTION_LOOP_DOCS.md` exists.
- `tasks/TASK_029_ROLE_FILE_IO_CONTRACTS.md` exists.
- Each backfilled task file contains all required sections from the master
  repair framework.
- Each backfilled task file is grounded in existing repository evidence and
  does not invent unrecorded implementation work.
- The task touches no completed TASK_028/TASK_029 implementation docs.
- The task touches no forbidden scientific, checkpoint, signoff, agent-bus,
  loop-engine, schema, script, audit-history, scaffold, GitHub automation, or
  loop-engineering paths.
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/executor_report.md` exists
  and records changed files, commands run, tests passed, tests failed,
  forbidden path check, scope deviation, unresolved issues, and recommended
  next action.
- Reviewer can verify the work with the acceptance commands.

## Stop Conditions

Stop immediately and report to the human if:

- TASK_032 evidence is insufficient to distinguish TASK_028 from TASK_029.
- Either target task file already exists with conflicting content.
- The executor would need to alter completed implementation docs to make the
  backfill accurate.
- The executor would need to edit forbidden paths.
- The executor would need to start TASK_033 or broader reporting
  normalization.
- The worktree contains unrelated dirty files that make scope verification
  ambiguous.
- Any acceptance command reports a forbidden path or scaffold path.
- A report/commit inconsistency materially changes what the task-history files
  should say and cannot be resolved from repository history.

## Risks / Ambiguity Notes

- TASK_028 and TASK_029 were recorded through executor reports, not canonical
  task files. The backfilled files must clearly say they are retrospective
  history records.
- `docs/dev/construction_loop/executor_report.md` was overwritten by TASK_029,
  so TASK_028 must be read from commit `c40622b`.
- The TASK_031 landing report says no commit was made by HumanIntegrator, while
  current HEAD is `f900ff8 docs: add task 031 safety and reporting
  conventions`. This is a non-blocking reporting inconsistency; repository log
  is source of truth.
- Existing older task files use `tasks/TASK_XXX.md` naming, while this task's
  framework-defined expected edits use descriptive filenames. Use the exact
  framework names for TASK_032.
- Do not convert this task into TASK_033 report-location normalization. Legacy
  report path deprecation belongs to TASK_033.

## Definition of Done

TASK_032 is done when:

- Only allowed TASK_032 files were changed.
- TASK_028 and TASK_029 backfill files exist with required sections and
  evidence-grounded content.
- The executor report records command evidence and scope checks.
- Reviewer returns `PASS` or `PASS_WITH_CAVEAT` with no blocking issues.
- HumanIntegrator, if invoked, stages only exact allowed files and recommends a
  commit only after review.
- No commit occurs unless the human explicitly says `commit now`.

## Planner Report

Current pwd / branch / HEAD:

- pwd:
  `/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-loop-audit-report`
- branch: `task-030-loop-meta-loop-audit`
- HEAD: `f900ff8 docs: add task 031 safety and reporting conventions`

Whether TASK_032 was clearly defined:

- Yes. The master repair framework defines
  `TASK_032_BACKFILL_TASK_028_029_HISTORY`, including goal, why, expected edits,
  requirements, and non-goals.

Exact TASK_032 name:

- `TASK_032_BACKFILL_TASK_028_029_HISTORY`

Files inspected:

- `docs/dev/construction_loop/planner.role.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/PLAN.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/executor_report.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/review_result.json`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/landing_report.md`
- `docs/dev/construction_loop/executor_report.md`
- `executor_report.md`
- `tasks/TASK_027.md`
- `git show c40622b:docs/dev/construction_loop/executor_report.md`
- `git show c40622b --stat --oneline`
- `git show fa93695 --stat --oneline`

Files created or modified by Planner:

- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/PLAN.md`

Assumptions:

- The master repair framework and reporting convention override the older
  planner role-card path convention for this repair sequence.
- Commit `c40622b` is the TASK_028 implementation commit.
- Commit `fa93695` is the TASK_029 implementation commit.
- TASK_031 is completed and committed because repository HEAD is `f900ff8`.

Blockers:

- None for planning TASK_032.

Staging and commit confirmation:

- Nothing was staged.
- Nothing was committed.
- No push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff was
  performed.
