# PLAN.md - TASK_041_REPORT_SCHEMA_CHECKER

## Task ID

TASK_041_REPORT_SCHEMA_CHECKER

## Task Title and Objective

Report Schema Checker.

Objective: add a lightweight command-line checker that validates the expected
`reports/TASK_XXX_<NAME>/` structure for construction-loop task report
directories. The checker must be read-only, local, human-readable, and limited
to report-shape validation.

This is the next checker-phase task after
`TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER`. It must not become a local runner,
automation loop, GitHub action, ci-sweeper, scaffold import, or role-card
checker.

## Source-of-truth Inputs

The executor must use repository files and current repo state as source of
truth:

- `docs/dev/construction_loop/planner.role.md`
- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- Prior checker artifact:
  - `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/PLAN.md`
  - `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/review_result.json`
  - `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/landing_report.md`
  - `scripts/check_forbidden_paths.py`
- Existing script style examples:
  - `scripts/check_forbidden_paths.py`
  - `scripts/check_pre_run_gate.py`
  - `scripts/audit_loop_report_consistency.py`

Current log anchor:

```text
35870f5 TASK_040 add forbidden path smoke checker
```

## Problem

The repository now has a canonical reporting convention, but report-directory
shape is still checked manually. Future construction-loop tasks need a small
read-only checker that can confirm required report artifacts exist in a
`reports/TASK_XXX_<NAME>/` directory before review or landing.

## Goal

Create:

```text
scripts/check_task_report_schema.py
```

The checker must validate expected files for a specified task report directory:

```text
PLAN.md
executor_report.md
review_result.json
landing_report.md
audit_evidence.md, if applicable
final_summary.md, if applicable
build.log, if applicable
```

The checker should also be designed so it can eventually validate declared
human-readable outputs when a task declares them:

```text
human_review/
engineering_audit.tex/pdf
supplement/theoretical_derivation_supplement.tex/pdf
```

For TASK_041, human-readable output validation may be limited to optional
presence checks and clear reporting. Do not invent a full report schema beyond
the current repository docs.

## In-scope Files or File Areas

The executor may create or edit only:

- `scripts/check_task_report_schema.py`
- `reports/TASK_041_REPORT_SCHEMA_CHECKER/executor_report.md`
- `reports/TASK_041_REPORT_SCHEMA_CHECKER/audit_evidence.md`, only if useful
  for traceability
- `reports/TASK_041_REPORT_SCHEMA_CHECKER/final_summary.md`, only if useful for
  handoff
- `reports/TASK_041_REPORT_SCHEMA_CHECKER/build.log`, only if a build, compile,
  or smoke command is actually run

The global forbidden-path list includes `scripts/`, but this task explicitly
allows the single new checker path:

```text
scripts/check_task_report_schema.py
```

No other `scripts/` path is allowed.

## Explicit Out-of-scope Files and Directories

Do not edit:

- `scripts/check_forbidden_paths.py`
- Any other existing `scripts/` file
- `tests/`
- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/`
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/`
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/`
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/`
- Any TASK_042, TASK_043, or later task artifacts

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
- `scripts/` except `scripts/check_task_report_schema.py`
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

Current checker-phase constraints:

- Do not write a local runner.
- Do not enable loop-engineering automated loops.
- Do not use GitHub automation.
- Do not merge or vendor loop-engineering scaffold.
- Continue only one bounded task at a time.
- Do not begin TASK_042 or TASK_043.
- Do not broaden TASK_040 into TASK_041.
- Do not touch forbidden paths except the explicitly allowed
  `scripts/check_task_report_schema.py`.
- Do not add tests unless a future human-approved plan explicitly expands this
  task.

## Required Reporting Conventions

Use the canonical report directory:

```text
reports/TASK_041_REPORT_SCHEMA_CHECKER/
```

Required role artifacts for the task lifecycle:

```text
reports/TASK_041_REPORT_SCHEMA_CHECKER/PLAN.md
reports/TASK_041_REPORT_SCHEMA_CHECKER/executor_report.md
reports/TASK_041_REPORT_SCHEMA_CHECKER/review_result.json
reports/TASK_041_REPORT_SCHEMA_CHECKER/landing_report.md
```

Optional artifacts, only when useful or actually generated:

```text
reports/TASK_041_REPORT_SCHEMA_CHECKER/audit_evidence.md
reports/TASK_041_REPORT_SCHEMA_CHECKER/final_summary.md
reports/TASK_041_REPORT_SCHEMA_CHECKER/build.log
```

No `human_review/` or `supplement/` output is required for TASK_041 unless the
executor discovers a human-approved reason to stop and re-plan.

## Executor Instructions

1. Read the relevant role card first.
2. Run and record:

   ```bash
   pwd
   git branch --show-current
   git status --short
   git log --oneline -5
   ```

3. Read this plan and the TASK_041 section of:

   ```text
   docs/dev/construction_loop/loop_meta_loop_repair_framework.md
   ```

4. Read:

   ```text
   docs/safety.md
   docs/dev/construction_loop/reporting_convention.md
   docs/dev/construction_loop/README.md
   ```

5. Inspect nearby script style:

   ```text
   scripts/check_forbidden_paths.py
   scripts/check_pre_run_gate.py
   scripts/audit_loop_report_consistency.py
   ```

6. Create `scripts/check_task_report_schema.py` as a small Python CLI.
7. The script should use only standard-library modules unless there is an
   existing repo helper that is clearly necessary. A dependency is not expected.
8. The script should accept an explicit report directory path. Suggested
   interface:

   ```bash
   python scripts/check_task_report_schema.py reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER
   ```

9. The checker must verify required files:

   ```text
   PLAN.md
   executor_report.md
   review_result.json
   landing_report.md
   ```

10. The checker should recognize optional files without requiring them:

    ```text
    audit_evidence.md
    final_summary.md
    build.log
    ```

11. The checker should inspect optional `human_review/` and `supplement/`
    subdirectories when present and report whether the expected files are
    present. Do not require these subdirectories unless the task report itself
    declares them or they already exist.
12. The checker should print a human-readable summary and return:
    - `0` when required files are present and no structural issue is detected;
    - nonzero when required files are missing or the target is not a valid
      report directory.
13. The checker must be read-only. It must not create, edit, stage, commit,
    push, freeze, sign off, or run automation.
14. Do not modify `scripts/check_forbidden_paths.py`.
15. Do not start TASK_042, TASK_043, runner, GitHub automation, ci-sweeper,
    provider integration, or loop-engineering scaffold work.
16. Write `reports/TASK_041_REPORT_SCHEMA_CHECKER/executor_report.md`.
17. Run the acceptance commands below.
18. Stop and hand off to Reviewer.

## Acceptance Commands

Executor, Reviewer, and HumanIntegrator should use these commands as
applicable:

```bash
pwd
git branch --show-current
git status --short
git log --oneline -5
test -f scripts/check_task_report_schema.py
test -f reports/TASK_041_REPORT_SCHEMA_CHECKER/executor_report.md
python -m py_compile scripts/check_task_report_schema.py
python scripts/check_task_report_schema.py --help
python scripts/check_task_report_schema.py reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER
```

Smoke-test missing required file behavior in a temporary directory outside the
worktree:

```bash
tmpdir="$(mktemp -d)"
mkdir -p "$tmpdir/reports/TASK_999_SMOKE"
touch "$tmpdir/reports/TASK_999_SMOKE/PLAN.md"
python /Users/wangjiahua/Desktop/25-26/Dissipation\ \&\ Nonlinear\ Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-loop-audit-report/scripts/check_task_report_schema.py "$tmpdir/reports/TASK_999_SMOKE" && echo "UNEXPECTED PASS" || echo "expected missing-report failure"
```

Return to the repo root before final checks:

```bash
cd /Users/wangjiahua/Desktop/25-26/Dissipation\ \&\ Nonlinear\ Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-loop-audit-report
git diff --stat
git diff --check
git diff
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' | grep -v 'scripts/check_task_report_schema.py' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe except approved checker path"
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\.claude/|patterns/|\.github/|loop-constraints.md' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
test ! -f .gitmodules
find . -maxdepth 3 -type d -name 'loop-engineering*'
git diff --cached --name-only
```

Note: while TASK_041 is unstaged, the checker itself is a dirty path under
`scripts/`. That is the only permitted scripts exception for this task.

## Expected Output Files

Expected executor-created files:

- `scripts/check_task_report_schema.py`
- `reports/TASK_041_REPORT_SCHEMA_CHECKER/executor_report.md`

Already-created planner artifact:

- `reports/TASK_041_REPORT_SCHEMA_CHECKER/PLAN.md`

Optional, only if useful and created intentionally:

- `reports/TASK_041_REPORT_SCHEMA_CHECKER/audit_evidence.md`
- `reports/TASK_041_REPORT_SCHEMA_CHECKER/final_summary.md`
- `reports/TASK_041_REPORT_SCHEMA_CHECKER/build.log`

## Reviewer Checklist

Reviewer must be read-only and must not edit, repair, stage, commit, or push.

Check:

- The executor read the relevant role card first.
- The initial repo inspection commands were run and recorded.
- `scripts/check_task_report_schema.py` exists and is the only modified
  `scripts/` path.
- The checker validates required report artifacts:
  - `PLAN.md`
  - `executor_report.md`
  - `review_result.json`
  - `landing_report.md`
- The checker recognizes optional `audit_evidence.md`, `final_summary.md`, and
  `build.log` without requiring them.
- The checker reports optional `human_review/` and `supplement/` shapes when
  present without making them mandatory for ordinary tasks.
- The checker prints human-readable results and returns nonzero on missing
  required files.
- The checker is read-only and does not stage, commit, sign off, freeze, or
  invoke automation.
- No local runner, automated loop, GitHub automation, ci-sweeper, scaffold
  import, or TASK_042/TASK_043 work was started.
- No forbidden paths were dirtied except the explicitly allowed checker file.
- The executor report exists and includes required fields.
- Acceptance commands passed, or any skipped command is justified.

Reviewer output:

```text
reports/TASK_041_REPORT_SCHEMA_CHECKER/review_result.json
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
- Stage only exact TASK_041 approved paths.
- Do not use `git add .`.
- Do not stage unrelated dirty files.
- Do not commit until the human explicitly says `commit now`.
- Do not push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff.
- Write:

  ```text
  reports/TASK_041_REPORT_SCHEMA_CHECKER/landing_report.md
  ```

Landing report must include staged files, excluded files, forbidden path check,
staged diff summary, unresolved issues, recommended commit message, and
`final_recommendation: COMMIT` or `DO_NOT_COMMIT`.

Because `reports/` artifacts may be ignored by Git, HumanIntegrator may need
explicit path force-staging for TASK_041 report files only. Recursive add-dot
staging remains forbidden.

## Acceptance Criteria

- `scripts/check_task_report_schema.py` exists.
- The checker is read-only.
- The checker validates required report files for a specified
  `reports/TASK_XXX_<NAME>/` directory.
- The checker exits nonzero when required files are missing.
- The checker recognizes optional report artifacts without requiring them.
- The checker reports optional human-readable output subdirectories when
  present.
- No local runner, automated loop, GitHub automation, ci-sweeper, scaffold
  import, or TASK_042/TASK_043 implementation was added.
- The task touches no forbidden scientific, checkpoint, signoff, agent-bus,
  loop-engine, schema, audit-history, scaffold, GitHub automation, or
  loop-engineering paths.
- The only allowed `scripts/` dirty path is
  `scripts/check_task_report_schema.py`.
- `reports/TASK_041_REPORT_SCHEMA_CHECKER/executor_report.md` exists and
  records changed files, commands run, tests passed, tests failed, forbidden
  path check, scope deviation, unresolved issues, and recommended next action.
- Reviewer can verify the work with the acceptance commands.

## Stop Conditions

Stop immediately and report to the human if:

- The executor would need to edit any `scripts/` path other than
  `scripts/check_task_report_schema.py`.
- The executor would need to add tests or fixtures not covered by this plan.
- The executor would need to edit `docs/safety.md`,
  `docs/dev/construction_loop/reporting_convention.md`, or other policy docs.
- The executor would need to touch `agent_bus/`, `loop_engine/`, `schemas/`,
  scientific/runtime paths, checkpoints, signoff ledgers, or validation
  artifacts.
- The executor would need to implement TASK_042, TASK_043, a runner, GitHub
  automation, ci-sweeper, provider integration, or loop-engineering scaffold
  work.
- Existing dirty files make it impossible to verify the exact TASK_041 scope.
- Any acceptance command reports an unexpected forbidden path or scaffold path.

## Risks / Ambiguity Notes

- The master framework says Phase 3 may introduce scripts, but the global
  safety policy treats `scripts/` as a forbidden path. This task is the narrow
  checker-phase exception for exactly `scripts/check_task_report_schema.py`.
- The framework uses shorthand `reports/TASK_XXX/` in one checker-task line,
  while the committed reporting convention standardizes new tasks on
  `reports/TASK_XXX_<NAME>/`. This plan follows the committed reporting
  convention.
- `audit_evidence.md`, `final_summary.md`, and `build.log` are listed as
  expected report artifacts, but prior tasks often omit them when not
  applicable. TASK_041 should not fail reports solely for missing optional
  artifacts unless the report declares them or policy later requires them.
- Human-readable output validation is future-facing. For TASK_041, validate
  presence/shape when those directories exist, but do not require them for
  ordinary tasks.
- TASK_042 is the role-card completeness checker. Do not combine it with this
  report-schema checker.

## Definition of Done

TASK_041 is done when:

- Only allowed TASK_041 files were changed.
- The report schema checker exists and passes the acceptance smoke checks.
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
- HEAD: `35870f5 TASK_040 add forbidden path smoke checker`

Whether the next checker-phase task was clearly defined:

- Yes. The master repair framework defines
  `TASK_041_REPORT_SCHEMA_CHECKER` as the next checker-phase task after
  TASK_040, including goal, expected edits, requirements, and future
  human-readable output validation scope.

Exact task id and name:

- `TASK_041_REPORT_SCHEMA_CHECKER`

Files inspected:

- `docs/dev/construction_loop/planner.role.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/PLAN.md`
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/review_result.json`
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/landing_report.md`
- `scripts/check_forbidden_paths.py`
- `scripts/check_pre_run_gate.py`
- `scripts/audit_loop_report_consistency.py`

Files created or modified by Planner:

- `reports/TASK_041_REPORT_SCHEMA_CHECKER/PLAN.md`

Assumptions:

- The current human strategy intentionally continues checker-phase planning
  and does not require planning TASK_034 first.
- The narrow script exception for `scripts/check_task_report_schema.py` is
  authorized by TASK_041's framework-defined expected edits.
- Tests are not added in this task because the repo source-of-truth does not
  explicitly authorize `tests/` for TASK_041.

Blockers:

- None for planning TASK_041.

Staging and commit confirmation:

- Nothing was staged.
- Nothing was committed.
- No push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff was
  performed.
