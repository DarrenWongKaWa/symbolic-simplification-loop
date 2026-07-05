# TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT

## Task Title and Objective

Title: WEP Capability Auditor and Report

Objective: introduce a bounded Workflow Execution Protocol / Work Execution Protocol
(WEP) Capability Auditor role card and produce a human-readable LaTeX/PDF
engineering audit that states, with evidence, what the current construction-loop
workflow can and cannot safely do.

This task is assigned as TASK_052 because the master repair framework already
reserves TASK_042 through TASK_051 for other bounded tasks. TASK_042 is reserved
for `TASK_042_ROLE_CARD_COMPLETENESS_CHECKER` and must not be hijacked.

## Source-of-Truth Inputs

Executor must read and treat these files as the authoritative inputs:

- `docs/dev/construction_loop/planner.role.md`
- `docs/dev/construction_loop/executor.role.md`
- `docs/dev/construction_loop/reviewer.role.md`
- `docs/dev/construction_loop/human_integrator.role.md`
- `docs/safety.md`
- `docs/dev/construction_loop/reporting_convention.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- `docs/dev/construction_loop/README.md`
- `scripts/check_forbidden_paths.py`
- `scripts/check_task_report_schema.py`
- Existing canonical task reports under `reports/TASK_031_*` through
  `reports/TASK_041_*`, as evidence only.

Executor must also inspect the current path inventories before editing:

```bash
find docs/dev/construction_loop -maxdepth 2 -type f | sort
find reports -maxdepth 2 -type f | sort
find tasks -maxdepth 2 -type f | sort
find scripts -maxdepth 2 -type f | sort
```

The following files were absent at planning time and should remain source
ambiguities unless Executor confirms otherwise:

- `docs/dev/construction_loop/wep_capability_auditor.role.md`
- `docs/dev/construction_loop/auditor.role.md`
- `docs/dev/construction_loop/role_card_schema.md`
- `docs/dev/construction_loop/file_location_contract.md`

## In-Scope Files or File Areas

Executor may create or modify only:

- `docs/dev/construction_loop/wep_capability_auditor.role.md`
- `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/executor_report.md`
- `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/review_result.json`
- `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/landing_report.md`
- `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/audit_evidence.md`
- `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/final_summary.md`
- `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/build.log`, if a root
  report build command is actually run.
- `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/human_review/engineering_audit.tex`
- `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/human_review/engineering_audit.pdf`
- `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/human_review/build.log`

`reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/PLAN.md` is created by this
Planner and should not be rewritten except to correct a blocking ambiguity found
before Executor begins.

## Explicit Out-of-Scope Files and Directories

Executor must not create, modify, delete, stage, or normalize these paths:

- `sigma_abc/`
- `checkpoints/`
- validation artifacts
- scientific output files
- human signoff ledgers, histories, or YAML files
- `.loop/human_signoff.yaml`
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
- any vendored `loop-engineering*` directory

Executor must not implement or modify checker scripts, local runners, GitHub
automation, Langflow integration, role-card schema files, file-location contract
files, scientific/runtime code, checkpoints, or signoff machinery in this task.

## Required Safety Conventions

Every role session must begin with:

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

The global lifecycle must remain:

```text
Planner -> Executor -> Reviewer -> HumanIntegrator -> human explicit `commit now`
```

Global prohibitions:

- no `git add .`
- no recursive add-dot staging
- no `git add -A`
- no `git add --all`
- no commit unless the human explicitly says `commit now`
- no push
- no merge
- no reset
- no rebase
- no cherry-pick
- no auto-freeze
- no auto-signoff
- no ci-sweeper
- no vendored loop-engineering
- no git submodule
- no direct scientific/runtime edits
- no local construction-loop runner
- no loop-engineering automated-loop enablement
- no GitHub automation
- no TASK_053 work

## Required Reporting Conventions

This task must use the canonical report directory:

```text
reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/
```

Required task artifacts:

- `PLAN.md`
- `executor_report.md`
- `review_result.json`
- `landing_report.md`

Recommended traceability artifacts:

- `audit_evidence.md`
- `final_summary.md`
- `build.log`, only if a root-level build command actually ran.

Required human-readable engineering audit artifacts:

- `human_review/engineering_audit.tex`
- `human_review/engineering_audit.pdf`
- `human_review/build.log`

If local LaTeX tooling is unavailable, Executor must still create
`engineering_audit.tex` and `human_review/build.log` documenting the exact build
command attempted and the failure. PDF absence is a blocking issue unless
Reviewer explicitly records a non-blocking caveat accepted by the human.

Executor must record this known checker caveat: at TASK_041,
`scripts/check_task_report_schema.py` recognizes `human_review/` but requires
only `PLAN.md`, `executor_report.md`, `review_result.json`, and
`landing_report.md`. It does not currently enforce the presence of
`engineering_audit.tex`, `engineering_audit.pdf`, or `human_review/build.log`.
This task must not repair that checker.

## WEP Capability Report Requirements

The PDF title must be:

```text
WEP Capability Report
```

The report must include these sections:

1. Current repo state
2. Capability matrix
3. What WEP can do now
4. What WEP cannot do yet
5. Automation level assessment
6. Loop-engineering status
7. Safety boundaries for scientific/runtime files
8. Recommended next upgrades
9. Caveats / NOT_PROVEN items

The capability matrix must use these columns:

```text
Capability | Status | Evidence | What it can do now | What it cannot do yet | Risk
```

Allowed matrix status values are only:

```text
IMPLEMENTED
PARTIAL
POLICY_ONLY
CHECKER_EXISTS
PROBE_ONLY
NOT_STARTED
NOT_PROVEN
DO_NOT_USE_YET
```

The matrix must cover at least:

- role-card protocol
- Planner -> Executor -> Reviewer -> HumanIntegrator -> human commit workflow
- human commit gate
- safety policy
- reporting convention
- `human_review/` PDF convention
- engineering audit PDF convention
- theoretical supplement convention
- task history / task index status
- report location normalization
- loop-engineering merge policy
- loop naming / task naming conventions
- role-card schema
- role-card backfill
- file-location contract
- task registry / index
- forbidden-path checker
- report schema checker
- role-card checker
- task-index checker
- agent-bus dry run
- loop-engineering audit wrapper
- construction-loop runner
- GitHub Actions smoke
- Langflow readiness

Conservative conclusions required:

- Distinguish human-followed protocol from machine-checkable protocol.
- Distinguish checker-backed behavior from policy-only behavior.
- Do not claim a local construction-loop runner exists.
- Do not claim loop-engineering can take over this repo.
- Treat loop-engineering as probe-only / audit-cost-helper unless later tasks
  implement the approved wrapper and safety checks.
- Do not claim WEP may touch scientific/runtime paths.
- State that scientific/runtime edits require a future bounded,
  human-approved task with verifier, reviewer, checkpoint, and signoff
  constraints.
- Automation level must be conservative. Current WEP should be rated no higher
  than partial checker-assisted prompt-loop unless Executor finds stronger
  repo-local evidence.

## Executor Instructions

1. Read `docs/dev/construction_loop/executor.role.md` first.
2. Record `pwd`, branch, status, and recent log before task-specific work.
3. Confirm that no WEP Capability Auditor role card already exists.
4. Confirm that TASK_042 through TASK_051 are reserved by
   `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`, and that
   TASK_052 is unused.
5. Create `docs/dev/construction_loop/wep_capability_auditor.role.md`.
6. Make the new role card read-only by default: it may inspect repository
   evidence and write only task-approved WEP capability reports. It must not
   edit implementation files, symbolic outputs, scientific/runtime paths,
   checkpoints, signoff ledgers, scripts, schemas, agent bus, or loop engine
   files unless a later bounded plan explicitly authorizes that work.
7. Create the WEP Capability Report in LaTeX under `human_review/` and compile
   it to PDF if local tooling is available.
8. Write `executor_report.md` with changed files, commands run, pass/fail
   results, unresolved issues, scope deviations, and recommended next action.
9. Run the acceptance commands below where applicable.
10. Do not stage, commit, push, merge, reset, rebase, cherry-pick, auto-freeze,
    auto-signoff, or begin any later task.

## Acceptance Commands

Executor and Reviewer should run:

```bash
git status --short
python3 scripts/check_forbidden_paths.py
python3 scripts/check_task_report_schema.py reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/
test -f docs/dev/construction_loop/wep_capability_auditor.role.md
test -f reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/human_review/engineering_audit.tex
test -f reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/human_review/build.log
test -f reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/human_review/engineering_audit.pdf
```

If PDF compilation fails because LaTeX tooling is unavailable, replace the final
`test -f ...engineering_audit.pdf` with a documented review decision explaining
why the missing PDF is accepted or why the task must return to Executor.

## Reviewer Checklist

Reviewer must verify:

- The patch is limited to the in-scope paths.
- The WEP Capability Auditor role card exists at
  `docs/dev/construction_loop/wep_capability_auditor.role.md`.
- The role card follows the existing construction-loop role-card style and
  includes purpose, operating modes, read paths, write paths, stop condition,
  forbidden actions, handoff target, human gate, and output format.
- The role card does not grant authority to edit scientific/runtime files,
  checkpoints, signoff ledgers, scripts, schemas, agent bus, or loop engine
  files.
- `engineering_audit.tex`, `engineering_audit.pdf`, and
  `human_review/build.log` exist, or PDF absence has a documented build failure
  and explicit non-blocking rationale.
- The report uses only the allowed WEP matrix status values.
- The report distinguishes policy-only, checker-backed, probe-only, and
  implemented capabilities.
- The report does not overclaim automation, local runner readiness,
  loop-engineering readiness, or scientific/runtime authority.
- The known TASK_041 report-schema checker caveat is recorded.
- `python3 scripts/check_forbidden_paths.py` passes.
- `python3 scripts/check_task_report_schema.py
  reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/` passes or any failure is
  treated as blocking unless caused solely by the known optional-output caveat.
- No forbidden paths, scaffold paths, or future-task files were touched.

## HumanIntegrator Checklist

HumanIntegrator must:

- Read `docs/dev/construction_loop/human_integrator.role.md` first.
- Record `pwd`, branch, status, and recent log before task-specific work.
- Require a non-`FAIL` `review_result.json` before staging.
- Inspect `git status --short`, `git diff --stat`, and `git diff`.
- Stage only exact approved paths, one file at a time.
- Use `git add -f` only for ignored report artifacts under the exact
  `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/` path.
- Never use `git add .`, `git add -A`, or `git add --all`.
- Confirm no forbidden path is staged.
- Write `landing_report.md`.
- Stop before commit until the human explicitly says `commit now`.

## Acceptance Criteria

The task is acceptable when:

- `docs/dev/construction_loop/wep_capability_auditor.role.md` exists and is
  bounded to read-only audit behavior unless a future task says otherwise.
- Canonical report artifacts exist under
  `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/`.
- The WEP Capability Report exists as LaTeX and PDF in `human_review/`, with a
  build log.
- The report answers what WEP can do now, what it cannot do yet, and what is
  not proven.
- The report uses the required capability matrix columns and allowed status
  values.
- The report rates current automation conservatively and does not claim a
  local runner, loop-engineering takeover, GitHub automation, or Langflow
  integration.
- The report states that scientific/runtime files remain protected and out of
  scope.
- The known report-schema checker limitation around optional PDF artifacts is
  documented.
- Acceptance commands were run or any skipped command has a clear reason in
  `executor_report.md` and `review_result.json`.
- Nothing was staged or committed by Executor or Reviewer.

## Stop Conditions

Stop and report to the human without broadening scope if:

- A WEP Capability Auditor role card already exists under a different canonical
  name.
- TASK_052 is discovered to be reserved by a repo source-of-truth file.
- Creating the role card would require modifying role-card schema or
  file-location contract files.
- The PDF cannot be built and Reviewer does not accept `.tex` plus build log as
  sufficient.
- Any forbidden path would need to be touched.
- Any scientific/runtime path would need to be touched.
- Any acceptance command reveals a forbidden path, schema, or scope issue.
- The task would require modifying scripts, GitHub automation, agent bus,
  loop engine, schemas, checkpoints, or signoff files.

## Risks / Ambiguity Notes

- `WEP` is a project-local phrase in this prompt and should be expanded in the
  report as Workflow Execution Protocol / Work Execution Protocol. Executor
  must not imply that WEP is an external standard unless repo evidence says so.
- The master repair framework defines engineering audit status words
  separately from this task's WEP capability matrix values. Use the WEP matrix
  values for the WEP capability matrix, and do not mix the two sets without an
  explicit explanation.
- The report-schema checker currently treats human-readable outputs as optional.
  That is a known limitation to record, not a TASK_052 repair target.
- The repo contains scripts for the scientific symbolic loop. Their existence
  must not be interpreted as permission for WEP to run or modify scientific
  outputs.
- Reports may be ignored by git; HumanIntegrator must use exact-path staging
  and `git add -f` only where needed.

## Planner Report

- Current pwd:
  `/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-loop-audit-report`
- Current branch: `task-030-loop-meta-loop-audit`
- Current HEAD: `98a2040 TASK_041 add report schema checker`
- TASK_042 clearly free: no. It is reserved for
  `TASK_042_ROLE_CARD_COMPLETENESS_CHECKER`.
- Selected task: `TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT`
- Files inspected:
  - `docs/dev/construction_loop/planner.role.md`
  - `docs/dev/construction_loop/executor.role.md`
  - `docs/dev/construction_loop/reviewer.role.md`
  - `docs/dev/construction_loop/human_integrator.role.md`
  - `docs/safety.md`
  - `docs/dev/construction_loop/reporting_convention.md`
  - `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
  - `docs/dev/construction_loop/README.md`
  - `scripts/check_forbidden_paths.py`
  - `scripts/check_task_report_schema.py`
  - path inventories under `docs/dev/construction_loop/`, `reports/`, `tasks/`,
    and `scripts/`
- Files created or modified:
  - `reports/TASK_052_WEP_CAPABILITY_AUDITOR_AND_REPORT/PLAN.md`
- Assumptions:
  - Because TASK_042 through TASK_051 are reserved and no TASK_052 source entry
    exists, TASK_052 is the next safe unused bounded task ID.
  - The WEP Capability Auditor role card is the intended exact role-card name
    because no existing `wep_capability_auditor.role.md` or `auditor.role.md`
    was found.
- Blockers:
  - None for planning. Executor must stop if a newer repo state assigns TASK_052
    before execution begins.
- Staging / commit confirmation:
  - Planner did not stage files.
  - Planner did not commit.
  - Planner did not push, merge, reset, rebase, cherry-pick, auto-freeze, or
    auto-signoff.
