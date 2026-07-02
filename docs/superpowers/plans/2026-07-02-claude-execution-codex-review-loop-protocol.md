# Claude Execution / Codex Review Loop Protocol

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement task plans. Claude Code executes patch plans. Codex reviews outputs, runs benchmarks, and writes the next plan.

**Goal:** Establish a repeatable autonomous-ish loop where Claude Code executes bounded infrastructure patches and Codex performs independent review, benchmark verification, verdict classification, and next-plan generation.

**Architecture:** Keep roles separate. Claude Code is the executor. Codex is the reviewer/planner. Every iteration must have a saved plan, a Claude report, a Codex independent benchmark run, a verdict, and either a freeze recommendation or a follow-up plan. Reports alone are never accepted as proof.

**Tech Stack:** Claude Code CLI (`claude --bare`), Python 3.12, pytest, compileall, `symbolic-simplification-loop` repo profiles, existing validation JSON/review/checkpoint manifests.

---

## Role Contract

### Claude Code Executor

Claude may:

```text
read the current plan
patch files named in the plan
run the verification commands requested in the plan
write an execution report
```

Claude must not:

```text
modify sigma_abc physics unless explicitly allowed by the plan
start 012C promotion unless explicitly allowed
start Stage 013 unless explicitly allowed
start tensorial IBP unless explicitly allowed
introduce total-derivative reductions unless explicitly allowed
claim full tensorial correctness
hide failed tests or failed commands
```

### Codex Reviewer / Planner

Codex must:

```text
read Claude's execution report
run independent verification commands
compare actual results against benchmark gates
classify verdict
write a next plan if anything fails or is incomplete
stop on hard-stop boundaries
```

Codex must not:

```text
accept a Claude report without local verification
let a report override a failed gate
silently continue after a hard stop
convert inherited caveats into direct PASS claims
```

---

## Iteration Lifecycle

Each loop iteration follows:

```text
1. Codex writes plan under docs/superpowers/plans/.
2. Claude Code reads plan and executes patch.
3. Claude writes report under docs/devlog/loop_engine/ or docs/devlog/audits/.
4. Codex runs independent benchmark commands.
5. Codex writes review verdict.
6. Codex either:
   a. freezes/marks stable checkpoint recommendation; or
   b. writes follow-up patch plan; or
   c. stops with human approval required.
```

---

## Standard Benchmark Gates

### Global Infrastructure Gates

Run after every infrastructure patch:

```bash
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
```

Required:

```text
pytest -> PASS
compileall -> PASS
```

### Report / Artifact Gates

Check that the claimed report exists and has the expected identity:

```bash
test -f <claimed_report_path>
rg "PASS|FAIL|CAVEAT|pytest|compileall" <claimed_report_path>
```

Required:

```text
ReportIdentity matches branch/plan.
Report does not overclaim beyond validation.
```

### Loop-Engine Trust Gates

For any patch touching freeze/checkpoint/review behavior, verify:

```text
failed validation blocks freeze
missing reviewer blocks freeze
missing required human signoff blocks freeze
failed freeze leaves no checkpoint_manifest.json residue
checkpoint_manifest.json exists only after successful freeze
```

### Sigma-Abc Safety Gates

Always preserve:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS
```

Always forbid unless explicitly approved:

```text
012C promotion
Stage 013 global assembly
tensorial IBP
total-derivative reduction
full tensorial sigma_{mu alpha beta} correctness claim
```

Recommended audit command:

```bash
find autonomous_runs sigma_abc -maxdepth 5 -type d \
  \( -iname '*012c*promotion*' -o -iname '*013*' -o -iname '*ibp*' -o -iname '*total_derivative*' \) \
  | sort
```

Interpretation:

```text
Historical artifacts may exist. New artifacts from the current patch must be explained.
```

### Test-Isolation Gates

For runner/test patches:

```bash
python3 -m pytest -q \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008 \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_dry_run_reports_profile_driven_next_stage \
  -vv
```

Required:

```text
2 passed
```

If a test mutates run state, it must use an isolated `LOOP_RUN_ROOT`.

### Claude-Handoff Gate

Before asking Claude to execute a plan, Codex should run a read-only handshake:

```bash
claude --bare -p --permission-mode plan --tools Read --max-budget-usd 0.60 --output-format json \
  'Read <plan_path> only. Do not edit files. Return JSON with can_read_plan, branch_name, ready_to_execute.'
```

Required:

```text
can_read_plan -> true
ready_to_execute -> true
```

### Claude Allowed-Tools Gate

Before invoking Claude for an execution patch, generate the exact
`--allowedTools` value from the plan itself:

```bash
python3 scripts/build_claude_allowed_tools.py --plan <plan_path>
```

Use the `claude_allowed_tools_arg` field as the Claude `--allowedTools`
argument. Do not manually broaden the command list just because a previous run
attempted an undeclared command.

Required behavior:

```text
Only commands declared in fenced Run bash blocks become Bash(...) tools.
Undeclared commands are denied and classified as EXECUTOR_UNAUTHORIZED_COMMAND.
Executor timeout is classified as EXECUTOR_TIMEOUT, not as a physics failure.
```

When Claude needs an undeclared command, write a smaller follow-up plan that
declares that command explicitly, then regenerate `--allowedTools`.

---

## Verdict Vocabulary

Use only these verdicts:

```text
PASS
PASS_WITH_CAVEAT
PASS_WITH_FOLLOWUP_REQUIRED
NEEDS_PATCH
BLOCKED_BY_RUNTIME_LIMIT
HARD_STOP
HUMAN_APPROVAL_REQUIRED
```

Meanings:

```text
PASS: all required benchmark gates pass.
PASS_WITH_CAVEAT: gates pass, but claim boundary/caveat remains.
PASS_WITH_FOLLOWUP_REQUIRED: main patch works, but a non-hard-stop benchmark fails or is incomplete.
NEEDS_PATCH: benchmark failure requires code/test/doc patch.
BLOCKED_BY_RUNTIME_LIMIT: quota/timeout prevents review; do not patch code just for quota.
HARD_STOP: protected benchmark/caveat/hard boundary violated.
HUMAN_APPROVAL_REQUIRED: next useful step needs user approval, usually IBP or total derivative.
```

---

## Current Active Loop State

Current Claude patch status:

```text
loop_skill_repo_integration_patch -> PASS_WITH_FOLLOWUP_REQUIRED
```

Reason:

```text
Claude report claimed pytest PASS, but Codex independent verification found:
python3 -m pytest -q -> 1 failed, 264 passed, 1 warning
```

Follow-up plan:

```text
docs/superpowers/plans/2026-07-02-loop-skill-repo-integration-followup-test-isolation.md
```

Current failure reproducer:

```bash
python3 -m pytest -q \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008 \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_dry_run_reports_profile_driven_next_stage \
  -vv
```

Expected before follow-up patch:

```text
first test PASS; second test FAIL with NextStage -> none
```

---

## Stop Conditions

Codex must stop the loop and ask for human approval if:

```text
protected sigma_xxx benchmark fails
DC inherited-pass caveat is lost or rewritten as direct PASS
Claude modifies frozen checkpoint payloads directly
Claude starts 012C/013/IBP/total-derivative without explicit plan permission
same patch fails twice for the same reason
next useful step is scientific promotion/IBP rather than infrastructure hygiene
```

---

### Report Consistency Gate

When a Claude execution report claims PASS, create or locate a JSON evidence
file and run:

```bash
python3 scripts/audit_loop_report_consistency.py \
  --report <report.md> \
  --evidence <evidence.json>
```

A strict PASS report must not coexist with failed evidence. If evidence failed
but the report honestly says `PASS_WITH_FOLLOWUP_REQUIRED`, the audit may return
`PASS_WITH_CAVEAT`.

## Recommended Next Action

Ask Claude Code to execute:

```text
docs/superpowers/plans/2026-07-02-loop-skill-repo-integration-followup-test-isolation.md
```

Then Codex should independently run:

```bash
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
python3 -m pytest -q \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008 \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_dry_run_reports_profile_driven_next_stage \
  -vv
```
