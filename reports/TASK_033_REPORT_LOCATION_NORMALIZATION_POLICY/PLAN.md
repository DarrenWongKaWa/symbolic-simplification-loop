# PLAN.md - TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY

## Task ID

TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY

## Task Title and Objective

Report Location Normalization Policy.

Objective: define and repair the repository policy for canonical construction
loop report locations, explicitly deprecating ambiguous legacy report paths
while preserving historical artifacts as read-only evidence.

This is a bounded documentation-policy task. It must not move, rename, delete,
rewrite, or restage historical reports. It must not start checker work,
automation, scaffold import, or TASK_034.

## Source-of-truth Inputs

The executor must use repository files and current repo state as source of
truth:

- `docs/dev/construction_loop/planner.role.md`
- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- Prior task artifacts:
  - `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/PLAN.md`
  - `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/review_result.json`
  - `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/landing_report.md`
  - `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/PLAN.md`
  - `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/review_result.json`
  - `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/landing_report.md`
- Legacy or ambiguous report-path evidence:
  - `executor_report.md`
  - `docs/dev/construction_loop/executor_report.md`
  - `docs/dev/construction_loop/loop_engineering_probe_report.md`
  - `reports/TASK_030_loop_meta_loop_audit/`
  - `reports/TASK_030_FRAMEWORK_PLACEMENT/executor_report.md`
- Current log anchor:
  - `9d62546 TASK_032 backfill task history records`

Repo-state observation to preserve if relevant: a TASK_032 commit exists at
HEAD even if a commit-step report elsewhere said no commit was created. Treat
repository log as source of truth.

## Problem

The TASK_030 audit found report-location ambiguity across several historical
paths:

```text
root executor_report.md
docs/dev/construction_loop/executor_report.md
docs/dev/construction_loop/loop_engineering_probe_report.md
reports/TASK_030_loop_meta_loop_audit/
```

TASK_031 introduced a canonical reporting convention, but TASK_033 is the
explicit policy task that must normalize report-location language, label legacy
locations, and prevent future tasks from adding new reports in ambiguous paths.

## Goal

Update the reporting policy so future construction-loop tasks use:

```text
reports/TASK_XXX_<NAME>/
```

and explicitly declare:

```text
root executor_report.md = legacy / discouraged
docs/dev/construction_loop/executor_report.md = bootstrap history only
docs/dev/construction_loop/loop_engineering_probe_report.md = probe evidence only
future reports = reports/TASK_XXX_<NAME>/
```

The policy must also explicitly include:

```text
reports/TASK_XXX_<NAME>/human_review/
engineering audit PDF format
theoretical supplement PDF format
legacy report-path deprecation
```

## In-scope Files or File Areas

The executor may edit only:

- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/executor_report.md`
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/audit_evidence.md`,
  only if useful for traceability
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/final_summary.md`,
  only if useful for handoff
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/build.log`, only if a
  build or render command is actually run

The executor may read the ambiguous report paths listed above, but must not
edit, move, rename, or delete them.

## Explicit Out-of-scope Files and Directories

Do not edit:

- `executor_report.md`
- `docs/dev/construction_loop/executor_report.md`
- `docs/dev/construction_loop/loop_engineering_probe_report.md`
- `reports/TASK_030_loop_meta_loop_audit/`
- `reports/TASK_030_FRAMEWORK_PLACEMENT/`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/`
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/`
- `tasks/`
- `docs/safety.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- Any TASK_034 or later task artifacts

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

The workflow must remain:

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
- Do not begin TASK_040, TASK_041, or TASK_042 checker work.
- Do not begin TASK_034.

## Required Reporting Conventions

Use the canonical report directory:

```text
reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/
```

Required role artifacts for the task lifecycle:

```text
reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/PLAN.md
reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/executor_report.md
reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/review_result.json
reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/landing_report.md
```

Optional artifacts, only when useful or actually generated:

```text
reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/audit_evidence.md
reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/final_summary.md
reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/build.log
```

No `human_review/` or `supplement/` output is required unless the executor
discovers a human-approved reason to stop and re-plan.

## Executor Instructions

1. Read the relevant role card first.
2. Run and record:

   ```bash
   pwd
   git branch --show-current
   git status --short
   git log --oneline -5
   ```

3. Read this plan and the TASK_033 section of:

   ```text
   docs/dev/construction_loop/loop_meta_loop_repair_framework.md
   ```

4. Read:

   ```text
   docs/safety.md
   docs/dev/construction_loop/reporting_convention.md
   docs/dev/construction_loop/README.md
   ```

5. Inspect the historical report paths as read-only evidence:

   ```text
   executor_report.md
   docs/dev/construction_loop/executor_report.md
   docs/dev/construction_loop/loop_engineering_probe_report.md
   reports/TASK_030_loop_meta_loop_audit/
   reports/TASK_030_FRAMEWORK_PLACEMENT/executor_report.md
   ```

6. Minimally update `docs/dev/construction_loop/reporting_convention.md` to
   make the legacy-path policy explicit and unambiguous. If the current file
   already contains part of the policy, repair gaps rather than duplicating
   content.
7. Minimally update `docs/dev/construction_loop/README.md` only if needed to
   point readers to the report-location normalization / legacy path policy.
8. Do not move, rename, delete, or rewrite legacy report artifacts.
9. Do not start TASK_034 or any checker/automation task.
10. Write
    `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/executor_report.md`.
11. Run the acceptance commands below.
12. Stop and hand off to Reviewer. Do not stage or commit.

## Acceptance Commands

Executor, Reviewer, and HumanIntegrator should use these commands as
applicable:

```bash
pwd
git branch --show-current
git status --short
git log --oneline -5
test -f docs/dev/construction_loop/reporting_convention.md
test -f docs/dev/construction_loop/README.md
test -f reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/executor_report.md
grep -R "root executor_report.md" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "docs/dev/construction_loop/executor_report.md" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "docs/dev/construction_loop/loop_engineering_probe_report.md" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "legacy / discouraged" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "bootstrap history only" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "probe evidence only" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "reports/TASK_XXX_<NAME>" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "human_review" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "engineering audit PDF" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "theoretical" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
git diff --stat
git diff --check
git diff
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe"
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\.claude/|patterns/|\.github/|loop-constraints.md' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
test ! -f .gitmodules
find . -maxdepth 3 -type d -name 'loop-engineering*'
```

Reviewer may also inspect the historical paths directly:

```bash
test -f executor_report.md
test -f docs/dev/construction_loop/executor_report.md
test -f docs/dev/construction_loop/loop_engineering_probe_report.md
test -d reports/TASK_030_loop_meta_loop_audit
```

## Expected Output Files

Expected executor-created or executor-modified files:

- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`, only if a minimal pointer update is
  needed
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/executor_report.md`

Already-created planner artifact:

- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/PLAN.md`

Optional, only if useful and created intentionally:

- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/audit_evidence.md`
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/final_summary.md`
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/build.log`

## Reviewer Checklist

Reviewer must be read-only and must not edit, repair, stage, commit, or push.

Check:

- The executor read the relevant role card first.
- The initial repo inspection commands were run and recorded.
- The legacy report-path policy is explicit and uses the required labels:
  - `root executor_report.md = legacy / discouraged`
  - `docs/dev/construction_loop/executor_report.md = bootstrap history only`
  - `docs/dev/construction_loop/loop_engineering_probe_report.md = probe evidence only`
  - future reports use `reports/TASK_XXX_<NAME>/`
- The policy includes `human_review/`, engineering audit PDF format, and
  theoretical supplement PDF format.
- Historical legacy report artifacts were not moved, renamed, deleted, or
  rewritten.
- README was either minimally updated or left unchanged with a clear executor
  justification.
- No TASK_034, TASK_040, TASK_041, or TASK_042 work was started.
- No forbidden paths or probe scaffold paths were touched.
- The executor report exists and includes required fields.
- Acceptance commands passed, or any skipped command is justified.

Reviewer output:

```text
reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/review_result.json
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
- Stage only exact TASK_033 approved paths.
- Do not use `git add .`.
- Do not stage unrelated dirty files.
- Do not commit until the human explicitly says `commit now`.
- Do not push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff.
- Write:

  ```text
  reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/landing_report.md
  ```

Landing report must include staged files, excluded files, forbidden path check,
staged diff summary, unresolved issues, recommended commit message, and
`final_recommendation: COMMIT` or `DO_NOT_COMMIT`.

Because `reports/` artifacts may be ignored by Git, HumanIntegrator may need
explicit path force-staging for TASK_033 report files only. Recursive add-dot
staging remains forbidden.

## Acceptance Criteria

- `docs/dev/construction_loop/reporting_convention.md` explicitly normalizes
  report locations and deprecates ambiguous legacy paths.
- The policy states:
  - `root executor_report.md = legacy / discouraged`
  - `docs/dev/construction_loop/executor_report.md = bootstrap history only`
  - `docs/dev/construction_loop/loop_engineering_probe_report.md = probe evidence only`
  - future reports use `reports/TASK_XXX_<NAME>/`
- The policy explicitly includes `human_review/`, engineering audit PDF format,
  theoretical supplement PDF format, and legacy report-path deprecation.
- `docs/dev/construction_loop/README.md` points to the policy or the executor
  justifies why the existing pointer is sufficient.
- Historical reports remain in place as evidence.
- The task touches no forbidden scientific, checkpoint, signoff, agent-bus,
  loop-engine, schema, script, audit-history, scaffold, GitHub automation, or
  loop-engineering paths.
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/executor_report.md`
  exists and records changed files, commands run, tests passed, tests failed,
  forbidden path check, scope deviation, unresolved issues, and recommended
  next action.
- Reviewer can verify the work with the acceptance commands.

## Stop Conditions

Stop immediately and report to the human if:

- TASK_033 evidence is insufficient to distinguish legacy paths from canonical
  paths.
- The executor would need to move, rename, delete, or rewrite historical report
  artifacts to satisfy the policy.
- The executor would need to edit forbidden paths.
- The executor would need to start TASK_034 or broader merge-policy work.
- The executor would need to start checker, script, GitHub, CI, or automation
  work.
- The worktree contains unrelated dirty files that make scope verification
  ambiguous.
- Any acceptance command reports a forbidden path or scaffold path.

## Risks / Ambiguity Notes

- `docs/dev/construction_loop/reporting_convention.md` already contains some
  TASK_033-like language from TASK_031. The executor should refine and complete
  the policy, not duplicate it.
- The master framework says `future reports = reports/TASK_XXX/` in one
  shorthand line while the canonical convention says
  `reports/TASK_XXX_<NAME>/`. This plan follows the current reporting
  convention and uses `reports/TASK_XXX_<NAME>/` for new tasks; short forms may
  be described only as legacy shorthand.
- `reports/TASK_030_loop_meta_loop_audit/` uses a mixed-case historical name.
  TASK_033 should label it as historical evidence without moving it.
- This task is policy-only. Machine-checkable validation belongs to later
  TASK_040/TASK_041/TASK_042 tasks.

## Definition of Done

TASK_033 is done when:

- Only allowed TASK_033 files were changed.
- The report-location normalization policy is explicit and verifiable.
- Legacy report paths are labeled without moving or rewriting historical
  artifacts.
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
- HEAD: `9d62546 TASK_032 backfill task history records`

Whether TASK_033 was clearly defined:

- Yes. The master repair framework defines
  `TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY`, including goal, why,
  expected edits, required decision, and required policy content.

Exact TASK_033 name:

- `TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY`

Files inspected:

- `docs/dev/construction_loop/planner.role.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/PLAN.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/review_result.json`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/landing_report.md`
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/PLAN.md`
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/review_result.json`
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/landing_report.md`
- `executor_report.md`
- `docs/dev/construction_loop/executor_report.md`
- `docs/dev/construction_loop/loop_engineering_probe_report.md`
- Existing `reports/` and `tasks/` path listing

Files created or modified by Planner:

- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/PLAN.md`

Assumptions:

- The master repair framework and current reporting convention override the
  older planner role-card path convention for this repair sequence.
- TASK_032 is completed and committed because repository HEAD is `9d62546`.
- Current `reporting_convention.md` may already satisfy part of TASK_033; the
  executor should perform a minimal repair/clarification pass rather than
  duplicating sections.

Blockers:

- None for planning TASK_033.

Staging and commit confirmation:

- Nothing was staged.
- Nothing was committed.
- No push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff was
  performed.
