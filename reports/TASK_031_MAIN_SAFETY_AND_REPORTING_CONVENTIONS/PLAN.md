# PLAN.md - TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS

## Task ID

TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS

## Task Title

Main Safety and Reporting Conventions

## Objective

Plan a bounded repository change that establishes or repairs the main safety
policy, task reporting convention, and baseline human-output convention for the
construction-loop workflow.

The executor must make the main branch safer for future construction-loop work
without adding runtime automation, changing scientific artifacts, changing
checkpoint/signoff state, or importing probe scaffold files wholesale.

## Source-of-truth Inputs

- `docs/dev/construction_loop/planner.role.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- Existing nearby report convention under `reports/TASK_030_loop_meta_loop_audit/`
- Existing framework-placement report under
  `reports/TASK_030_FRAMEWORK_PLACEMENT/executor_report.md`
- Human task request for `TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS`

If any of these inputs conflict, the executor must prefer the master repair
framework for this repair sequence and report the conflict in
`reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/executor_report.md`.

## Problem

The TASK_030 audit framework says the main repo needs a safety policy and a
common reporting baseline before stronger automation or loop-engineering
integration can be considered. Without these conventions, future tasks may use
ambiguous report locations, skip role handoffs, stage too broadly, or blur human
approval boundaries.

## Goal

Create or repair documentation that makes the following conventions explicit:

1. Every construction-loop task must pass through:

   ```text
   Planner -> Executor -> Reviewer -> HumanIntegrator -> human explicit `commit now`
   ```

2. The first instruction for every new Codex / Claude Code session must be:

   ```text
   Read the relevant role card first.
   ```

3. Before task-specific work, each session must inspect:

   ```bash
   pwd
   git branch --show-current
   git status --short
   git log --oneline -5
   ```

4. Global safety must forbid recursive add-dot staging, commits without the
   exact human instruction `commit now`, and any push, merge, reset, rebase,
   cherry-pick, auto-freeze, or auto-signoff.

5. Construction-loop role cards are expected under:

   ```text
   docs/dev/construction_loop/
   ```

   Especially:

   ```text
   docs/dev/construction_loop/planner.role.md
   docs/dev/construction_loop/executor.role.md
   docs/dev/construction_loop/reviewer.role.md
   docs/dev/construction_loop/human_integrator.role.md
   ```

## Non-goals

- Do not implement automation, validators, dispatchers, provider integrations,
  Langflow integrations, CI sweepers, or GitHub workflow changes.
- Do not edit symbolic/scientific outputs, validation artifacts, checkpoints,
  signoff ledgers, or human approval history.
- Do not copy, vendor, submodule, or wholesale-merge loop-engineering scaffold
  files.
- Do not merge or introduce:
  - `LOOP.md`
  - `STATE.md`
  - `loop-budget.md`
  - `loop-run-log.md`
  - `.claude/`
  - `patterns/`
  - `.github/`
- Do not start TASK_032 or later framework tasks.
- Do not stage, commit, push, merge, reset, rebase, cherry-pick, auto-freeze, or
  auto-signoff.

## Allowed Edits

The executor may edit only the files or file areas below:

- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/executor_report.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/audit_evidence.md`,
  if useful for traceability
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/final_summary.md`,
  if useful for handoff
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/build.log`, only if a
  build or render command is actually run

The executor must confirm whether each target file already exists before
editing. If `docs/dev/construction_loop/README.md` already contains relevant
content, update it minimally rather than replacing it wholesale.

## In-scope Files or File Areas

- `docs/safety.md`
  - Define the main safety policy.
  - To be confirmed by Executor: whether a probe-branch `docs/safety.md` is
    available as reference material. If used, copy only reviewed policy content,
    not probe scaffold.
- `docs/dev/construction_loop/reporting_convention.md`
  - Define canonical task report layout and report artifact meanings.
  - To be confirmed by Executor: whether this file already exists and should be
    repaired instead of newly created.
- `docs/dev/construction_loop/README.md`
  - Link or summarize the safety and reporting conventions from the
    construction-loop documentation entry point.
  - To be confirmed by Executor: existing README structure and appropriate
    insertion point.
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/`
  - Store executor, reviewer, human-integrator, and optional evidence outputs
    for this task.

## Forbidden Edits

The executor must not edit:

- `sigma_abc/`
- `checkpoints/`
- validation artifacts
- scientific output files
- `.loop/human_signoff.yaml`
- human signoff ledgers, histories, or YAML files
- `agent_bus/`
- `loop_engine/`
- `schemas/`
- `scripts/`
- `docs/devlog/audits/`
- `.gitmodules`
- vendored `loop-engineering*` directories
- TASK_030 report artifacts except read-only inspection
- TASK_032 or later report/task artifacts

## Required Safety Conventions

The implemented docs must state that every construction-loop task obeys these
rules unless a future human-approved plan explicitly narrows or extends them:

- First instruction for every new Codex / Claude Code session:

  ```text
  Read the relevant role card first.
  ```

- Before task-specific work, every session inspects:

  ```bash
  pwd
  git branch --show-current
  git status --short
  git log --oneline -5
  ```

- Every task moves through:

  ```text
  Planner -> Executor -> Reviewer -> HumanIntegrator -> human explicit `commit now`
  ```

- No recursive add-dot staging:

  ```bash
  git add .
  ```

  is forbidden.

- No commit unless the human explicitly says:

  ```text
  commit now
  ```

- No push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff.
- No provider integration, Langflow integration, ci-sweeper, vendored
  loop-engineering repo, or git submodule.
- Forbidden path checks must protect scientific, checkpoint, signoff,
  automation, schema, script, and audit-history areas.

## Required Reporting Conventions

The implemented docs must define the canonical task report directory as:

```text
reports/TASK_XXX_<NAME>/
```

Minimum expected report files:

```text
reports/TASK_XXX_<NAME>/PLAN.md
reports/TASK_XXX_<NAME>/executor_report.md
reports/TASK_XXX_<NAME>/review_result.json
reports/TASK_XXX_<NAME>/landing_report.md
reports/TASK_XXX_<NAME>/audit_evidence.md
reports/TASK_XXX_<NAME>/final_summary.md
reports/TASK_XXX_<NAME>/build.log
```

The docs must introduce the basic human-output locations:

```text
reports/TASK_XXX_<NAME>/human_review/
reports/TASK_XXX_<NAME>/supplement/
```

The docs must say these are optional task-dependent subdirectories used when a
task requires human-readable engineering audit PDFs or theoretical derivation
supplements. The docs should point future tasks to the role-card, engineering
audit PDF, and theoretical derivation supplement standards in the master repair
framework when those standards are not yet separately documented.

## Implementation Steps

1. Read the relevant role card first.
2. Run and record:

   ```bash
   pwd
   git branch --show-current
   git status --short
   git log --oneline -5
   ```

3. Read:

   ```text
   docs/dev/construction_loop/loop_meta_loop_repair_framework.md
   docs/dev/construction_loop/planner.role.md
   docs/dev/construction_loop/executor.role.md
   docs/dev/construction_loop/reviewer.role.md
   docs/dev/construction_loop/human_integrator.role.md
   ```

   If any expected role card is missing, report it and continue only with the
   documentation changes that remain safe.

4. Inspect whether the allowed target docs already exist.
5. Create or minimally update `docs/safety.md` with the required safety
   conventions.
6. Create or minimally update
   `docs/dev/construction_loop/reporting_convention.md` with the required
   reporting conventions.
7. Minimally update `docs/dev/construction_loop/README.md` to point to the new
   safety and reporting docs.
8. Write
   `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/executor_report.md`.
9. Run the acceptance commands below.
10. Stop and hand off to Reviewer. Do not stage or commit.

## Acceptance Commands

The executor, reviewer, and human integrator should use these commands as
applicable:

```bash
pwd
git branch --show-current
git status --short
git diff --stat
git diff
test -f docs/safety.md
test -f docs/dev/construction_loop/reporting_convention.md
test -f docs/dev/construction_loop/README.md
test -f reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/executor_report.md
grep -R "Read the relevant role card first" docs/safety.md docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "Planner -> Executor -> Reviewer -> HumanIntegrator -> human explicit" docs/safety.md docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "commit now" docs/safety.md docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "git add \\." docs/safety.md docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "reports/TASK_XXX_<NAME>" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe"
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\\.claude/|patterns/|\\.github/' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
test ! -f .gitmodules
find . -maxdepth 3 -type d -name 'loop-engineering*'
```

## Expected Output Files

- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/README.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/executor_report.md`

Optional, only if useful and created intentionally:

- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/audit_evidence.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/final_summary.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/build.log`

## Executor Instructions

- Stay inside the allowed edit set.
- Prefer small documentation edits over broad rewrites.
- Preserve existing valid content in target docs.
- If a target doc conflicts with the master repair framework, repair only the
  conflict needed for TASK_031 and report the conflict.
- Do not stage files.
- Do not commit.
- Do not push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff.
- End with an executor report listing changed files, commands run, tests passed,
  tests failed, forbidden path check, scope deviation, unresolved issues, and
  recommended next action.

## Reviewer Checklist

Reviewer must be read-only and must not edit, repair, stage, commit, or push.

Check:

- The role-card-first instruction is present.
- The initial repo inspection commands are present.
- The lifecycle
  `Planner -> Executor -> Reviewer -> HumanIntegrator -> human explicit
  commit now` is present.
- `git add .` is explicitly forbidden.
- Commit is allowed only after the exact human instruction `commit now`.
- Push, merge, reset, rebase, cherry-pick, auto-freeze, and auto-signoff are
  explicitly forbidden.
- Role-card paths under `docs/dev/construction_loop/` are named.
- Canonical report location `reports/TASK_XXX_<NAME>/` is defined.
- `human_review/` and `supplement/` are introduced as task-dependent
  human-output locations.
- No forbidden paths or probe scaffold paths were touched.
- Executor report exists and includes required fields.
- Acceptance commands were run or any skipped commands are justified.

Reviewer output:

```text
reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/review_result.json
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
- Run the required initial repo inspection commands.
- Confirm reviewer verdict and absence of blocking issues.
- Confirm staged files, if any, are exact allowed paths only.
- Do not use `git add .`.
- Do not stage unrelated dirty files.
- Do not commit until the human explicitly says `commit now`.
- Do not push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff.
- Write:

  ```text
  reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/landing_report.md
  ```

Landing report must include staged files, excluded files, forbidden path check,
staged diff summary, unresolved issues, recommended commit message, and
`final_recommendation: COMMIT` or `DO_NOT_COMMIT`.

## Acceptance Criteria

- `docs/safety.md` exists and defines the required global safety conventions.
- `docs/dev/construction_loop/reporting_convention.md` exists and defines the
  canonical report directory and expected report artifacts.
- `docs/dev/construction_loop/README.md` points future construction-loop work to
  the safety and reporting conventions.
- The docs explicitly preserve the required role lifecycle and human commit
  gate.
- The docs explicitly require role-card-first session startup and initial repo
  inspection commands.
- The docs explicitly forbid recursive add-dot staging and unapproved git
  history or remote operations.
- The task creates no runtime automation and touches no forbidden scientific,
  checkpoint, signoff, agent-bus, loop-engine, schema, script, or audit-history
  paths.
- Executor report exists with command evidence and final scope checks.
- Reviewer can verify the work with the acceptance commands.

## Stop Conditions

Stop immediately and report to the human if:

- Any required role card needed for safe execution is missing and the missing
  card changes the allowed action boundary.
- Existing docs contain contradictory safety rules that cannot be repaired
  without broad redesign.
- Implementing the task would require editing forbidden paths.
- Implementing the task would require runtime automation, scripts, schemas,
  agent bus changes, checkpoint/signoff changes, or probe scaffold merge.
- The worktree contains unrelated dirty files that make scope verification
  ambiguous.
- The executor cannot produce a clear forbidden-path check.
- Any acceptance command indicates a forbidden path or scaffold path was
  touched.

## Risks / Ambiguity Notes

- The planner role card still names `tasks/TASK_XXX.md` as the manual-session
  output, while the master repair framework names
  `reports/TASK_XXX_<NAME>/PLAN.md` as the required planner output for this
  repair sequence. This plan follows the master repair framework.
- The framework contains both `reports/TASK_XXX/` and
  `reports/TASK_XXX_<NAME>/` examples. This task should standardize on
  `reports/TASK_XXX_<NAME>/` for named construction-loop reports while noting
  any short-form references as shorthand only.
- `docs/safety.md` may have an existing probe-branch counterpart, but this task
  must not merge probe scaffold wholesale.
- The role-card and PDF standards may still be split between the master
  framework and future dedicated docs until later tasks normalize them.

## Definition of Done

TASK_031 is done when:

- Only allowed files were changed.
- Required safety and reporting conventions are present in the docs.
- The executor report records command evidence and scope checks.
- Reviewer returns `PASS` or `PASS_WITH_CAVEAT` with no blocking issues.
- HumanIntegrator, if invoked, stages only exact allowed files and recommends
  commit only after review.
- No commit occurs unless the human explicitly says `commit now`.

## Planner Report

Files created or modified:

- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/PLAN.md`

What was inspected:

- `pwd`
- `git branch --show-current`
- `git status --short`
- `git log --oneline -5`
- `docs/dev/construction_loop/planner.role.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- Nearby TASK_030 report artifacts and existing task/report paths
- Existing construction-loop role-card paths under `docs/dev/construction_loop/`

Assumptions:

- The master repair framework is the source of truth for this repair sequence
  when it differs from the older planner role-card output path.
- `reports/TASK_XXX_<NAME>/PLAN.md` is the intended plan artifact convention
  for TASK_031.
- The executor will confirm existing target-doc contents before making the
  TASK_031 implementation edits.

Staging and commit confirmation:

- Nothing was staged.
- Nothing was committed.
- No push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff was
  performed.
