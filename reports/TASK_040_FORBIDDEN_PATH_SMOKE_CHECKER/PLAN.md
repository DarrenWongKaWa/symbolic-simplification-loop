# PLAN.md - TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER

## Task ID

TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER

## Task Title and Objective

Forbidden Path Smoke Checker.

Objective: add a lightweight command-line checker that reports whether the
current Git dirty state touches construction-loop forbidden paths. The checker
must be simple, local, human-readable, and non-mutating.

This is the first checker-phase task among TASK_040 / TASK_041 / TASK_042.
It must not become a local runner, automation loop, GitHub action, ci-sweeper,
or scaffold import.

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
  - `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/PLAN.md`
  - `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/review_result.json`
  - `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/landing_report.md`
- Existing script style examples:
  - `scripts/check_pre_run_gate.py`
  - `scripts/audit_loop_report_consistency.py`

Current log anchor:

```text
c7d3b2e TASK_033 normalize report location policy
```

## Problem

Construction-loop safety currently relies on humans manually running shell
greps such as:

```bash
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/'
```

The master repair framework defines TASK_040 as the first lightweight checker
task so future roles can run a single reproducible smoke command before review
or landing.

## Goal

Create:

```text
scripts/check_forbidden_paths.py
```

The script must:

- run read-only;
- read `git status --short` for the current working tree;
- match the forbidden-path denylist from `docs/safety.md` and the master repair
  framework;
- print a human-readable result;
- return nonzero if a forbidden dirty path is detected;
- return zero when dirty paths are absent or dirty paths are outside the
  denylist;
- never modify files, freeze artifacts, sign off, stage, commit, push, or
  invoke automation.

## In-scope Files or File Areas

The executor may create or edit only:

- `scripts/check_forbidden_paths.py`
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/executor_report.md`
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/audit_evidence.md`, only if
  useful for traceability
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/final_summary.md`, only if
  useful for handoff
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/build.log`, only if a build,
  compile, or smoke command is actually run

The global forbidden-path list includes `scripts/`, but this task explicitly
allows the single new checker path:

```text
scripts/check_forbidden_paths.py
```

No other `scripts/` path is allowed.

## Explicit Out-of-scope Files and Directories

Do not edit:

- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/`
- `reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/`
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/`
- Any TASK_041, TASK_042, TASK_043, or later task artifacts
- Any tests, unless a future human-approved plan explicitly expands the task
  scope

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
- `scripts/` except `scripts/check_forbidden_paths.py`
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
- Do not begin TASK_041 or TASK_042.
- Do not touch forbidden paths except the explicitly allowed
  `scripts/check_forbidden_paths.py`.

## Required Reporting Conventions

Use the canonical report directory:

```text
reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/
```

Required role artifacts for the task lifecycle:

```text
reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/PLAN.md
reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/executor_report.md
reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/review_result.json
reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/landing_report.md
```

Optional artifacts, only when useful or actually generated:

```text
reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/audit_evidence.md
reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/final_summary.md
reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/build.log
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

3. Read this plan and the TASK_040 section of:

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
   scripts/check_pre_run_gate.py
   scripts/audit_loop_report_consistency.py
   ```

6. Create `scripts/check_forbidden_paths.py` as a small Python CLI.
7. The script should use only standard-library modules unless there is an
   existing repo helper that is clearly necessary. A dependency is not expected.
8. The script should inspect the current working directory by running:

   ```bash
   git status --short
   ```

9. The forbidden matcher must include at least:

   ```text
   sigma_abc/
   checkpoints/
   human_signoff
   docs/devlog/audits/
   agent_bus/
   loop_engine/
   schemas/
   scripts/
   .loop/human_signoff.yaml
   LOOP.md
   STATE.md
   loop-budget.md
   loop-run-log.md
   .claude/
   .github/
   patterns/
   loop-constraints.md
   .gitmodules
   loop-engineering*
   ```

10. The script may treat `validation artifacts` and `scientific output files`
    as documentation-only categories if no precise path pattern is available;
    do not invent broad destructive matching beyond the repo's documented path
    denylist.
11. Return codes:
    - `0` when no forbidden dirty path is detected.
    - Nonzero when one or more forbidden dirty paths are detected.
    - Nonzero when `git status --short` cannot be run.
12. Print enough detail for a reviewer to see which forbidden paths were
    detected.
13. Do not stage files.
14. Do not commit.
15. Do not start TASK_041, TASK_042, or any runner/automation work.
16. Write
    `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/executor_report.md`.
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
test -f scripts/check_forbidden_paths.py
test -f reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/executor_report.md
python -m py_compile scripts/check_forbidden_paths.py
```

Smoke-test the checker in temporary Git repositories outside the worktree:

```bash
tmpdir="$(mktemp -d)"
cd "$tmpdir"
git init -q
python /Users/wangjiahua/Desktop/25-26/Dissipation\ \&\ Nonlinear\ Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-loop-audit-report/scripts/check_forbidden_paths.py
echo "ok" > README.md
python /Users/wangjiahua/Desktop/25-26/Dissipation\ \&\ Nonlinear\ Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-loop-audit-report/scripts/check_forbidden_paths.py
mkdir -p sigma_abc
echo "bad" > sigma_abc/dirty.txt
python /Users/wangjiahua/Desktop/25-26/Dissipation\ \&\ Nonlinear\ Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-loop-audit-report/scripts/check_forbidden_paths.py && echo "UNEXPECTED PASS" || echo "expected forbidden-path failure"
```

Return to the repo root before final checks:

```bash
cd /Users/wangjiahua/Desktop/25-26/Dissipation\ \&\ Nonlinear\ Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-loop-audit-report
git diff --stat
git diff --check
git diff
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' | grep -v 'scripts/check_forbidden_paths.py' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe except approved checker path"
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\.claude/|patterns/|\.github/|loop-constraints.md' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
test ! -f .gitmodules
find . -maxdepth 3 -type d -name 'loop-engineering*'
git diff --cached --name-only
```

Note: while TASK_040 is unstaged, the checker itself is a dirty path under
`scripts/`. That is the only permitted scripts exception for this task.

## Expected Output Files

Expected executor-created files:

- `scripts/check_forbidden_paths.py`
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/executor_report.md`

Already-created planner artifact:

- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/PLAN.md`

Optional, only if useful and created intentionally:

- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/audit_evidence.md`
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/final_summary.md`
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/build.log`

## Reviewer Checklist

Reviewer must be read-only and must not edit, repair, stage, commit, or push.

Check:

- The executor read the relevant role card first.
- The initial repo inspection commands were run and recorded.
- `scripts/check_forbidden_paths.py` exists and is the only modified
  `scripts/` path.
- The script reads `git status --short`.
- The script matches documented forbidden paths.
- The script prints human-readable results.
- The script returns nonzero when a forbidden dirty path is detected.
- The script returns zero when only non-forbidden dirty paths are present.
- The script does not modify files, stage, commit, sign off, freeze, or invoke
  automation.
- No local runner, automated loop, GitHub automation, ci-sweeper, scaffold
  import, or TASK_041/TASK_042 work was started.
- No forbidden paths were dirtied except the explicitly allowed checker file.
- The executor report exists and includes required fields.
- Acceptance commands passed, or any skipped command is justified.

Reviewer output:

```text
reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/review_result.json
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
- Stage only exact TASK_040 approved paths.
- Do not use `git add .`.
- Do not stage unrelated dirty files.
- Do not commit until the human explicitly says `commit now`.
- Do not push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff.
- Write:

  ```text
  reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/landing_report.md
  ```

Landing report must include staged files, excluded files, forbidden path check,
staged diff summary, unresolved issues, recommended commit message, and
`final_recommendation: COMMIT` or `DO_NOT_COMMIT`.

Because `reports/` artifacts may be ignored by Git, HumanIntegrator may need
explicit path force-staging for TASK_040 report files only. Recursive add-dot
staging remains forbidden.

## Acceptance Criteria

- `scripts/check_forbidden_paths.py` exists.
- The script is read-only and uses `git status --short`.
- The script detects dirty paths under the documented forbidden path denylist.
- The script exits nonzero when forbidden dirty paths are present.
- The script exits zero when no forbidden dirty paths are present.
- The script prints a reviewer-readable summary of its decision.
- No local runner, automated loop, GitHub automation, ci-sweeper, scaffold
  import, or TASK_041/TASK_042 implementation was added.
- The task touches no forbidden scientific, checkpoint, signoff, agent-bus,
  loop-engine, schema, audit-history, scaffold, GitHub automation, or
  loop-engineering paths.
- The only allowed `scripts/` dirty path is
  `scripts/check_forbidden_paths.py`.
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/executor_report.md` exists
  and records changed files, commands run, tests passed, tests failed,
  forbidden path check, scope deviation, unresolved issues, and recommended
  next action.
- Reviewer can verify the work with the acceptance commands.

## Stop Conditions

Stop immediately and report to the human if:

- The executor would need to edit any `scripts/` path other than
  `scripts/check_forbidden_paths.py`.
- The executor would need to add tests or fixtures not covered by this plan.
- The executor would need to edit `docs/safety.md` or other policy docs.
- The executor would need to touch `agent_bus/`, `loop_engine/`, `schemas/`,
  scientific/runtime paths, checkpoints, signoff ledgers, or validation
  artifacts.
- The executor would need to implement TASK_041, TASK_042, a runner, GitHub
  automation, ci-sweeper, provider integration, or loop-engineering scaffold
  work.
- Existing dirty files make it impossible to verify the exact TASK_040 scope.
- Any acceptance command reports an unexpected forbidden path or scaffold path.

## Risks / Ambiguity Notes

- The master framework says Phase 3 may introduce scripts, but the global
  safety policy treats `scripts/` as a forbidden path. This task is the narrow
  human-requested checker-phase exception for exactly
  `scripts/check_forbidden_paths.py`.
- `validation artifacts` and `scientific output files` are categories rather
  than precise path prefixes in the current docs. The checker should preserve
  documented concrete path checks and avoid inventing overly broad patterns.
- Running the checker in the worktree while `scripts/check_forbidden_paths.py`
  is dirty may cause it to report its own path as forbidden. Use temporary
  Git repositories for behavior smoke tests and use the final scope check to
  verify that no forbidden path other than the approved checker path is dirty.
- TASK_041 and TASK_042 are later checker tasks. Do not combine them with
  TASK_040.

## Definition of Done

TASK_040 is done when:

- Only allowed TASK_040 files were changed.
- The forbidden-path checker exists and passes the acceptance smoke checks.
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
- HEAD: `c7d3b2e TASK_033 normalize report location policy`

Whether the next checker-phase task was clearly defined:

- Yes. The master repair framework defines
  `TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER` as the first checker-phase task
  among TASK_040 / TASK_041 / TASK_042, including goal, expected edits,
  requirements, and must-not constraints.

Exact task id and name:

- `TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER`

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
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/PLAN.md`
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/review_result.json`
- `reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/landing_report.md`
- `scripts/check_pre_run_gate.py`
- `scripts/audit_loop_report_consistency.py`
- Existing `scripts/`, `reports/`, `tasks/`, and construction-loop docs path
  listings

Files created or modified by Planner:

- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/PLAN.md`

Assumptions:

- The current human strategy intentionally advances to checker-phase planning
  and does not require planning TASK_034 first.
- The narrow script exception for `scripts/check_forbidden_paths.py` is
  authorized by TASK_040's framework-defined expected edits.
- No tests are added in this task because the framework-defined expected edits
  name only the checker script and TASK_040 report directory.

Blockers:

- None for planning TASK_040.

Staging and commit confirmation:

- Nothing was staged.
- Nothing was committed.
- No push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff was
  performed.
