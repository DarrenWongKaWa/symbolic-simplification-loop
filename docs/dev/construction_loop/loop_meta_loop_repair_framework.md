# Loop / Meta-Loop Repair Framework

## Purpose

This document is the master repair framework after `TASK_030_LOOP_META_LOOP_AUDIT`.
It does not implement fixes directly.
It defines the repair sequence for two layers:

1. **Loop**
   - The scientific / symbolic-simplification automation loop inside `symbolic-simplification-loop`.
   - Includes role cards, agent_bus, diagnosis, verifier, checkpoint, signoff, human approval, reports, task files, and automation safety.
2. **Meta-loop**
   - The construction-team loop powered by `cobusgreyling/loop-engineering`.
   - Includes `LOOP.md`, `STATE.md`, `loop-constraints.md`, `loop-budget.md`, skills, agents, audit/cost, probe worktree, and human collaboration rules.

The goal is to turn the audit findings into a controlled sequence of small tasks.
Each task must go through:

```text
Planner -> Executor -> Reviewer -> HumanIntegrator -> Human explicit commit approval
```

No task in this framework should be implemented all at once.

⸻

## Global conclusion from TASK_030

The audit concluded:

```text
Loop status: PARTIAL
Meta-loop status: PROBE_ONLY
loop-engineering can run as a construction scaffold: YES_BUT_PROBE_ONLY
unattended operation: NO_NOT_YET
scientific/runtime edits by meta-loop: NO
replace verifier/signoff/checkpoint: NO
merge scaffold wholesale: NO
copy docs/safety.md to main: MAYBE, after human review
```

Therefore the repair strategy is:

1. Stabilize safety and reporting conventions.
2. Backfill missing task history.
3. Normalize role-card and file-location contracts.
4. Add machine-checkable validators.
5. Add dry-run automation.
6. Only then consider stronger loop-engineering / GitHub / Langflow integration.

⸻

## Global safety rules

Unless a specific task explicitly says otherwise, all tasks must obey:

### Forbidden edits

```text
sigma_abc/
checkpoints/
validation artifacts
human signoff ledgers/history/YAML
.loop/human_signoff.yaml
scientific output files
agent_bus/
loop_engine/
schemas/
scripts/
docs/devlog/audits/
```

### Forbidden actions

```text
no git add .
no commit without explicit human instruction
no push
no merge
no cherry-pick
no rebase
no reset
no auto-freeze
no auto-signoff
no provider integration
no Langflow integration
no ci-sweeper
no vendored loop-engineering repo
no git submodule
```

### Required checks for every task

Every Executor and HumanIntegrator must run:

```bash
git status --short
git diff --stat
git diff
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe"
test ! -f .gitmodules
find . -maxdepth 3 -type d -name 'loop-engineering*'
```

⸻

## Standard per-task workflow

Every task should follow this lifecycle.

### 1. Planner

Planner writes a bounded PLAN.md for exactly one task.

Required Planner output:

```text
reports/TASK_XXX_<NAME>/PLAN.md
```

The plan must include:

```text
Task ID
Title
Problem
Goal
Non-goals
Allowed edits
Forbidden edits
Implementation steps
Validation commands
Expected output files
Risks
Definition of done
```

Planner does not edit repo files other than the task plan.

⸻

### 2. Executor

Executor implements only the current task.

Required Executor output:

```text
reports/TASK_XXX_<NAME>/executor_report.md
```

The report must include:

```text
task_id
changed_files
commands_run
tests_passed
tests_failed
forbidden_path_check
scope_deviation
unresolved_issues
recommended_next_action
```

Executor does not stage, commit, push, freeze, or sign off.

⸻

### 3. Reviewer

Reviewer checks the patch.

Required Reviewer output:

```text
reports/TASK_XXX_<NAME>/review_result.json
```

Required verdicts:

```text
PASS
PASS_WITH_CAVEAT
FAIL
```

Required fields:

```json
{
  "verdict": "PASS | PASS_WITH_CAVEAT | FAIL",
  "blocking_issues": [],
  "caveats": [],
  "recommended_next_action": "",
  "safe_to_continue": true,
  "test_results": {}
}
```

Reviewer does not edit, repair, stage, commit, or push.

⸻

### 4. HumanIntegrator

HumanIntegrator stages exact files only after Reviewer PASS or PASS_WITH_CAVEAT with no blocking issues.

Required HumanIntegrator output:

```text
reports/TASK_XXX_<NAME>/landing_report.md
```

The report must include:

```text
staged_files
excluded_files
forbidden_path_check
staged_diff_summary
unresolved_issues
recommended_commit_message
final_recommendation: COMMIT | DO_NOT_COMMIT
```

HumanIntegrator must not use:

```text
git add .
```

Commit only after the human explicitly says:

```text
commit now
```

⸻

## Global role-card and human-output standards

These standards apply to future construction-loop tasks. They do not implement any repair by themselves.

### Role-card standard

Every construction-loop role card should be a Markdown file at:

```text
docs/dev/construction_loop/<role>.role.md
```

Required fields:

```text
role_name
layer
purpose
manual_read_paths
manual_write_paths
agent_bus_read_paths
agent_bus_write_paths
ready_marker
failed_artifact
stop_condition
forbidden_actions
handoff_target
human_gate
output_format
```

Concise role-card template:

```md
# Role: <role_name>

## layer

## purpose

## operating_modes

### manual mode

### agent-bus mode

## read_paths

### manual_read_paths

### agent_bus_read_paths

## write_paths

### manual_write_paths

### agent_bus_write_paths

## ready_marker

## failed_artifact

## stop_condition

## forbidden_actions

- no git add .
- no commit
- no push
- no auto-freeze
- no auto-signoff
- no scientific/runtime/checkpoint/signoff edits unless explicitly allowed

## handoff_target

## human_gate

## output_format
```

### Standard task output directory

Canonical task output directory:

```text
reports/TASK_XXX_<NAME>/
  PLAN.md
  executor_report.md
  review_result.json
  landing_report.md
  audit_evidence.md
  final_summary.md
  build.log
```

Human-review extension:

```text
reports/TASK_XXX_<NAME>/
  human_review/
    human_review.tex
    human_review.pdf
    build.log
    figures/
    tables/
```

Markdown and JSON outputs are for machine-assisted review and audit traceability.
PDF outputs are for human scientific or architecture review.
For important scientific or architecture tasks, Markdown/JSON alone is not sufficient.

### Engineering audit PDF standard

Applicable to:

```text
loop / meta-loop audit
role-card audit
file-location audit
automation safety audit
probe scaffold audit
merge policy audit
```

Recommended files:

```text
reports/TASK_XXX_<NAME>/human_review/engineering_audit.tex
reports/TASK_XXX_<NAME>/human_review/engineering_audit.pdf
reports/TASK_XXX_<NAME>/human_review/build.log
```

Required sections:

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

Must answer:

```text
What is complete?
What is partial?
What is probe-only?
What is forbidden?
What can be copied?
What must not be merged?
What requires explicit human approval?
What is the next safe task?
```

Allowed status words:

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

### Theoretical derivation supplement PDF standard

Applicable to:

```text
symbolic simplification
sigma_xxx / sigma_abc derivation
normal-form reduction
coefficient extraction
validation ledger
checkpoint-ready mathematical report
```

Recommended files:

```text
reports/TASK_XXX_<NAME>/supplement/
  theoretical_derivation_supplement.tex
  theoretical_derivation_supplement.pdf
  build.log
  symbol_dictionary.tex
  validation_ledger_table.tex
  kernel_appendix.tex
  stage_to_derivation_map.md
  input_snapshot_manifest.wl
```

Required sections:

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

It must require explicit statements of:

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

### Role output_format extension

Role cards' `output_format` should include PDF outputs when required:

```text
Planner:
  reports/TASK_XXX_<NAME>/PLAN.md

Executor:
  reports/TASK_XXX_<NAME>/executor_report.md
  reports/TASK_XXX_<NAME>/human_review/*.tex, if the task requires human-readable PDF
  reports/TASK_XXX_<NAME>/human_review/*.pdf, if compiled
  reports/TASK_XXX_<NAME>/supplement/*.tex, if the task is a scientific derivation task
  reports/TASK_XXX_<NAME>/supplement/*.pdf, if compiled

Reviewer:
  reports/TASK_XXX_<NAME>/review_result.json
  optional: reports/TASK_XXX_<NAME>/review_notes.md

HumanIntegrator:
  reports/TASK_XXX_<NAME>/landing_report.md
```

For tasks requiring human scientific or architecture review, Markdown/JSON reports are not sufficient. The task should also produce a LaTeX-rendered PDF in one of two formats: engineering audit PDF or theoretical derivation supplement PDF.

⸻

## Phase 1 — Main-branch safety and documentation conventions

Goal:

Make the main repo safe for future automation before adding any stronger automation.

No runtime implementation in this phase.

⸻

## TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS

### Goal

Bring the safety policy, report-location convention, and basic human-output convention into the main branch.

### Why

The probe branch has docs/safety.md, but the main branch needs its own safety policy before future construction-loop work.
Future tasks also need a common reporting baseline that links to the role-card and human-output standards when those standards exist.

### Expected edits

```text
docs/safety.md
docs/dev/construction_loop/reporting_convention.md
docs/dev/construction_loop/README.md
reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/
```

### Key requirements

docs/safety.md must define:

```text
forbidden-path denylist
no auto-freeze
no auto-signoff
no auto-commit
no push without human approval
no git add .
no vendored loop-engineering
no submodule unless approved
```

reporting_convention.md must define:

```text
reports/TASK_XXX/
  PLAN.md
  executor_report.md
  review_result.json
  landing_report.md
  audit_evidence.md
  final_summary.md
  build.log
```

It should also introduce the basic human-output convention:

```text
reports/TASK_XXX_<NAME>/human_review/
reports/TASK_XXX_<NAME>/supplement/
```

and point future tasks to the role-card, engineering audit PDF, and theoretical derivation supplement PDF standards when they exist.

### Non-goals

Do not merge:

```text
LOOP.md
STATE.md
loop-budget.md
loop-run-log.md
.claude/
patterns/
.github/
```

⸻

## TASK_032_BACKFILL_TASK_028_029_HISTORY

### Goal

Backfill missing task specs for TASK_028 and TASK_029.

### Why

The audit found that TASK_028 and TASK_029 were executed but their canonical task files were absent from tasks/.

### Expected edits

```text
tasks/TASK_028_CONSTRUCTION_LOOP_DOCS.md
tasks/TASK_029_ROLE_FILE_IO_CONTRACTS.md
reports/TASK_032_BACKFILL_TASK_028_029_HISTORY/
```

### Requirements

Each task file should include:

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

### Non-goals

Do not rewrite history.
Do not alter completed implementation files unless the task explicitly permits.

⸻

## TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY

### Goal

Define canonical report locations and deprecate ambiguous report paths.

### Why

The audit found naming/location ambiguity:

```text
root executor_report.md
docs/dev/construction_loop/executor_report.md
docs/dev/construction_loop/loop_engineering_probe_report.md
reports/TASK_030_loop_meta_loop_audit/
```

### Expected edits

```text
docs/dev/construction_loop/reporting_convention.md
docs/dev/construction_loop/README.md
reports/TASK_033_REPORT_LOCATION_NORMALIZATION_POLICY/
```

### Required decision

Declare:

```text
root executor_report.md = legacy / discouraged
docs/dev/construction_loop/executor_report.md = bootstrap history only
docs/dev/construction_loop/loop_engineering_probe_report.md = probe evidence only
future reports = reports/TASK_XXX/
```

The policy must explicitly include:

```text
reports/TASK_XXX_<NAME>/human_review/
engineering audit PDF format
theoretical supplement PDF format
legacy report-path deprecation
```

⸻

## TASK_034_LOOP_ENGINEERING_MERGE_POLICY

### Goal

Write a merge policy for the loop-engineering probe scaffold.

### Why

The audit concluded:

```text
ACCEPT_PROBE_BUT_DO_NOT_MERGE_SCAFFOLD
```

A policy is needed before any scaffold file enters main.

### Expected edits

```text
docs/dev/construction_loop/loop_engineering_merge_policy.md
docs/dev/construction_loop/README.md
reports/TASK_034_LOOP_ENGINEERING_MERGE_POLICY/
```

### Must answer

```text
What can be copied to main?
What must remain probe-only?
What requires separate review?
What must never be merged wholesale?
How should human approve crossing from probe to main?
```

### Default policy

docs/safety.md may be copied after review.
LOOP.md / STATE.md / loop-budget.md / loop-run-log.md / .claude scaffold should remain probe-only until a merge policy is approved.

⸻

## TASK_035_LOOP_NAMING_BOUNDARY

### Goal

Clarify the naming boundary between:

```text
docs/dev/construction_loop/
LOOP.md
loop-engineering scaffold
scientific symbolic-simplification loop
```

### Why

The audit found a naming collision: two different “loops” exist.

### Expected edits

```text
docs/dev/construction_loop/naming_boundary.md
docs/dev/construction_loop/README.md
reports/TASK_035_LOOP_NAMING_BOUNDARY/
```

### Required definitions

```text
scientific loop
construction loop
meta-loop
loop-engineering scaffold
probe worktree
main branch
audit branch
```

⸻

## Phase 2 — Role-card and file-location contract hardening

Goal:

Make role contracts explicit enough to be checked by humans and scripts.

This phase is mostly docs, with no runtime behavior change unless explicitly planned.

⸻

## TASK_036_ROLE_CARD_COMPLETENESS_POLICY

### Goal

Define the required fields for every role card.

### Expected edits

```text
docs/dev/construction_loop/role_card_schema.md
docs/dev/construction_loop/checklist.md
reports/TASK_036_ROLE_CARD_COMPLETENESS_POLICY/
```

### Required fields

```text
role_name
layer
purpose
manual_read_paths
manual_write_paths
agent_bus_read_paths
agent_bus_write_paths
ready_marker
failed_artifact
stop_condition
forbidden_actions
handoff_target
human_gate
output_format
```

⸻

## TASK_037_ROLE_CARD_BACKFILL

### Goal

Backfill missing or weak role-card fields based on the schema from TASK_036.

### Expected edits

```text
docs/dev/construction_loop/planner.role.md
docs/dev/construction_loop/executor.role.md
docs/dev/construction_loop/reviewer.role.md
docs/dev/construction_loop/human_integrator.role.md
reports/TASK_037_ROLE_CARD_BACKFILL/
```

### Requirements

Each role file should clearly declare:

```text
manual mode
agent-bus mode, if applicable
read paths
write paths
ready marker
failed artifact
stop condition
forbidden actions
handoff
output_format
```

The `output_format` backfill must include optional LaTeX/PDF outputs for tasks that require human-readable engineering audit PDFs or theoretical derivation supplement PDFs.

### Non-goals

Do not modify agent_bus/ implementation.

⸻

## TASK_038_FILE_LOCATION_CONTRACT

### Goal

Create a repo-wide file-location contract.

### Expected edits

```text
docs/dev/construction_loop/file_location_contract.md
docs/dev/construction_loop/README.md
reports/TASK_038_FILE_LOCATION_CONTRACT/
```

### Must cover

```text
task specs
executor reports
review JSON
landing reports
ready markers
failed artifacts
human approvals/rejections
diagnosis outputs
next_action_report.json
checkpoint artifacts
human signoff artifacts
loop-engineering state files
loop-engineering safety files
loop-engineering skill/agent files
LaTeX / human reports
```

⸻

## TASK_039_TASK_REGISTRY_AND_INDEX_POLICY

### Goal

Define a task registry/index convention.

### Expected edits

```text
tasks/README.md
tasks/TASK_INDEX.md
reports/TASK_039_TASK_REGISTRY_AND_INDEX_POLICY/
```

### Requirements

TASK_INDEX.md should track:

```text
task_id
title
status
branch
report_dir
commit_sha, if committed
review_verdict
landing_status
notes
```

### Non-goals

Do not create automation yet.

⸻

## Phase 3 — Machine-checkable validators

Goal:

Turn docs conventions into lightweight checks.

This phase may introduce scripts, but only after Phase 1 and Phase 2 are complete.

⸻

## TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER

### Goal

Add a script that checks whether current dirty files touch forbidden paths.

### Expected edits

```text
scripts/check_forbidden_paths.py
reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/
```

### Requirements

The script should:

```text
read git status --short
match forbidden-path denylist
print human-readable result
return nonzero if forbidden path is dirty
```

### Must not

Modify files.
Freeze artifacts.
Sign off.
Commit.

⸻

## TASK_041_REPORT_SCHEMA_CHECKER

### Goal

Add a checker for reports/TASK_XXX/ structure.

### Expected edits

```text
scripts/check_task_report_schema.py
reports/TASK_041_REPORT_SCHEMA_CHECKER/
```

### Requirements

Check for expected files:

```text
PLAN.md
executor_report.md
review_result.json
landing_report.md
audit_evidence.md, if applicable
final_summary.md, if applicable
build.log, if applicable
```

The checker should eventually validate declared human-readable outputs:

```text
human_review/
engineering_audit.tex/pdf
supplement/theoretical_derivation_supplement.tex/pdf
```

when a task declares those outputs.

⸻

## TASK_042_ROLE_CARD_COMPLETENESS_CHECKER

### Goal

Add a script that checks whether role cards contain required sections.

### Expected edits

```text
scripts/check_role_cards.py
reports/TASK_042_ROLE_CARD_COMPLETENESS_CHECKER/
```

### Requirements

Check role files for:

```text
Purpose
Manual session mode
Agent-bus mode
Read from
Write to
Ready marker
Failed artifact
Stop condition
Forbidden actions
Handoff
```

⸻

## TASK_043_TASK_INDEX_CHECKER

### Goal

Add a checker that validates tasks/TASK_INDEX.md.

### Expected edits

```text
scripts/check_task_index.py
reports/TASK_043_TASK_INDEX_CHECKER/
```

### Requirements

Check:

```text
TASK_INDEX.md exists
every tasks/TASK_*.md appears in index
every reports/TASK_* directory appears in index or is marked audit-only
status values are valid
```

⸻

## Phase 4 — Automation dry-run and loop hardening

Goal:

Allow automation to run in dry-run mode before real execution.

This phase should only begin after Phase 3 checkers exist.

⸻

## TASK_044_AGENT_BUS_DRY_RUN_VALIDATION

### Goal

Validate the existing agent_bus lifecycle without executing real task modifications.

### Expected edits

```text
reports/TASK_044_AGENT_BUS_DRY_RUN_VALIDATION/
```

Possible code edits only if explicitly planned and reviewed:

```text
agent_bus/
loop_engine/
```

### Requirements

Dry-run should validate:

```text
planner inbox/outbox
executor inbox/outbox
reviewer inbox/outbox
human approval boundary
ready markers
failed artifacts
round summary
no forbidden path changes
```

### Risk

Medium. Requires stricter Reviewer.

⸻

## TASK_045_LOOP_ENGINEERING_AUDIT_WRAPPER

### Goal

Create a wrapper that runs loop-engineering audit/cost in a repo-safe way.

### Expected edits

```text
scripts/run_loop_engineering_audit.py
reports/TASK_045_LOOP_ENGINEERING_AUDIT_WRAPPER/
```

### Requirements

Wrapper should:

```text
only run in probe worktree unless explicitly overridden
check branch name
check dirty status
run loop-audit
run loop-cost
capture output into reports/TASK_XXX/
refuse if forbidden paths are dirty
```

### Must not

Run loop-init.
Run ci-sweeper.
Modify scaffold.
Commit.

⸻

## TASK_046_CONSTRUCTION_LOOP_RUNNER_PROTOTYPE

### Goal

Prototype a safe construction-loop runner.

### Expected status

Do not start until:

```text
TASK_040 complete
TASK_041 complete
TASK_042 complete
TASK_045 complete
```

### Expected behavior

Runner may:

```text
read a task plan
invoke a worker
collect executor report
run checkers
stop before staging
```

Runner must not:

```text
auto-commit
auto-signoff
auto-freeze
edit scientific/runtime paths
run unattended
```

⸻

## Phase 5 — GitHub and CI integration

Goal:

Make safety checks reproducible outside local sessions.

Do not begin until Phase 3 scripts are stable.

⸻

## TASK_047_GITHUB_ACTIONS_SAFETY_SMOKE

### Goal

Add GitHub Actions for lightweight safety checks.

### Expected edits

```text
.github/workflows/safety-smoke.yml
reports/TASK_047_GITHUB_ACTIONS_SAFETY_SMOKE/
```

### Checks

```text
forbidden-path checker
report schema checker
role-card checker
task-index checker
```

### Risk

Medium. .github/ was previously not merged. Needs explicit approval.

⸻

## TASK_048_PR_REVIEW_TEMPLATE

### Goal

Add a PR template aligned with construction-loop safety.

### Expected edits

```text
.github/pull_request_template.md
reports/TASK_048_PR_REVIEW_TEMPLATE/
```

### Required fields

```text
task_id
changed_files
forbidden_path_check
tests_run
reviewer_verdict
human approval required
checkpoint/signoff impact
```

⸻

## Phase 6 — Meta-loop integration policy

Goal:

Decide how loop-engineering collaborates with humans and main repo.

This phase should remain policy-first.

⸻

## TASK_049_LOOP_ENGINEERING_HUMAN_COLLABORATION_GUIDE

### Goal

Write the human collaboration guide for the cloned/probe loop-engineering scaffold.

### Expected edits

```text
docs/dev/construction_loop/loop_engineering_human_collaboration.md
reports/TASK_049_LOOP_ENGINEERING_HUMAN_COLLABORATION_GUIDE/
```

### Must explain

```text
how to run in probe worktree
how to interpret loop-audit
how to interpret loop-cost
when to call Planner
when to call Executor
when to call Reviewer
when HumanIntegrator stages
when human says commit now
what never crosses into main automatically
```

⸻

## TASK_050_LOOP_ENGINEERING_SCAFFOLD_IMPORT_DECISION

### Goal

Make a formal decision on whether any scaffold files should enter main.

### Expected edits

```text
docs/dev/construction_loop/loop_engineering_scaffold_decision.md
reports/TASK_050_LOOP_ENGINEERING_SCAFFOLD_IMPORT_DECISION/
```

### Candidate files

```text
LOOP.md
STATE.md
loop-budget.md
loop-constraints.md
loop-run-log.md
.claude/skills/
.claude/agents/
patterns/registry.yaml
.github/
```

### Default recommendation

Do not merge wholesale.
Only import narrow files after separate review.

⸻

## Phase 7 — Cockpit / Langflow readiness

Goal:

Prepare for visualization only after schemas and state lifecycle stabilize.

Do not begin until automation dry-run and reporting schema are stable.

⸻

## TASK_051_LANGFLOW_COCKPIT_READINESS

### Goal

Define what Langflow or another cockpit would visualize.

### Expected edits

```text
docs/dev/construction_loop/langflow_cockpit_readiness.md
reports/TASK_051_LANGFLOW_COCKPIT_READINESS/
```

### Must define

```text
state schema
task lifecycle
role outputs
review verdicts
human approval state
forbidden-path state
checkpoint/signoff boundary state
report links
```

### Non-goal

Do not integrate Langflow yet.

⸻

## Recommended execution order

### Immediate sequence

```text
TASK_031
TASK_032
TASK_033
TASK_034
TASK_035
```

### Then

```text
TASK_036
TASK_037
TASK_038
TASK_039
```

### Then

```text
TASK_040
TASK_041
TASK_042
TASK_043
```

### Then

```text
TASK_044
TASK_045
TASK_046
```

### Then

```text
TASK_047
TASK_048
TASK_049
TASK_050
```

### Last

```text
TASK_051
```

⸻

## Human decision gates

The human must explicitly decide before:

```text
copying docs/safety.md from probe to main
importing any loop-engineering scaffold
creating .github/
adding scripts/
touching agent_bus/
touching loop_engine/
running automation in non-dry-run mode
allowing any scientific/runtime path edit
starting Langflow/cockpit integration
```

⸻

## Current recommended next task

Start with:

```text
TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS
```

Reason:

It establishes the main safety policy and report convention.
All later tasks depend on this safety/reporting baseline.
It is docs-only and low risk.

Do not start Phase 2 or Phase 3 before TASK_031 is completed, reviewed, and committed.

⸻

## Status legend

```text
NOT_STARTED
PLANNED
EXECUTED
REVIEW_PASS
REVIEW_PASS_WITH_CAVEAT
REVIEW_FAIL
LANDED
COMMITTED
BLOCKED
DEFERRED
```

Each task should update tasks/TASK_INDEX.md after the task-index convention exists.

Before TASK_039 exists, task status may be tracked manually in the task report directory.

⸻

## Definition of done for the whole repair program

The repair program is complete only when:

```text
main safety policy exists
reporting convention exists
TASK_028 and TASK_029 are backfilled
role-card schema exists
role cards pass completeness review
file-location contract exists
task registry exists
forbidden-path checker exists
report schema checker exists
role-card checker exists
agent_bus dry-run passes
loop-engineering audit wrapper exists
human collaboration guide exists
merge policy for scaffold exists
CI safety smoke tests are available, if approved
Langflow/cockpit readiness is documented, not necessarily implemented
```

Until then:

```text
loop-engineering remains probe-only
construction-loop automation remains human-gated
scientific verifier/signoff/checkpoint remains authoritative
no unattended automation is allowed
```
