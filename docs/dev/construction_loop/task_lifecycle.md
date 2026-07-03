# Task lifecycle

This document describes the full lifecycle of a `tasks/TASK_XXX.md`
under the construction loop, plus the safety rules that apply at every
step.

> The construction loop is dev-only. It improves this repo. It does
> not run the scientific symbolic-simplification loop and does not
> replace its verifier, reviewer, or human-signoff gates.

## Lifecycle

```text
1. Identify gap
2. CodexPlanner writes tasks/TASK_XXX.md
3. ClaudeCodeExecutor implements the patch
4. CodexReviewer reviews the patch
5. Executor repairs if verdict == FAIL
6. CodexReviewer re-reviews
7. HumanIntegrator stages exact files only
8. Tests run
9. Human explicitly approves commit ("commit now")
10. Commit lands
```

### Step 1 — Identify gap

A user, a developer, or a meta-reviewer surfaces a gap. The gap is
expressed as a small improvement, refactor, or doc addition to this
repo.

### Step 2 — CodexPlanner writes the task

The planner fills out **all** required sections of
`tasks/TASK_XXX.md` (see `planner.role.md`). `Allowed edits` and
`Forbidden edits` are the most important sections: they define the
patch's blast radius.

### Step 3 — ClaudeCodeExecutor implements

The executor applies the smallest patch that satisfies the spec,
restricted to `Allowed edits`. The executor writes
`executor_report.md` with the required fields.

### Step 4 — CodexReviewer reviews

The reviewer reads the spec, the report, the diff, and the test
output. The reviewer writes a single `review.json` with a verdict of
`PASS`, `PASS_WITH_CAVEAT`, or `FAIL`.

### Step 5 — Repair loop (only on FAIL)

If the verdict is `FAIL`, the executor repairs the patch and produces
a new `executor_report.md`. The lifecycle returns to step 4.

### Step 6 — Re-review

The reviewer re-reads the patched diff and writes a new `review.json`.
This loop continues until the verdict is `PASS` or
`PASS_WITH_CAVEAT`.

### Step 7 — HumanIntegrator stages

The integrator stages **only** files in `Allowed edits`, using
explicit `git add <path>` calls. The integrator never uses
`git add .`.

### Step 8 — Tests run

The integrator (or the executor, per spec) re-runs the acceptance
commands listed in the task. If tests fail, the lifecycle returns to
step 5.

### Step 9 — Human explicit approval

The integrator presents the landing report. The human reads it. The
commit only proceeds after the human explicitly says `commit now` (or
equivalent). Silence is not consent.

### Step 10 — Commit lands

The integrator lands the commit using the recommended commit message.
A push happens only if separately requested.

## Safety rules (apply at every step)

* **Never `git add .`** (or `git add -A`, `git add --all`). Stage
  files one at a time.
* **Never auto-commit.** Commits require explicit human instruction.
* **Never auto-freeze** checkpoints or scientific artifacts.
* **Never auto-signoff** anything. `.loop/human_signoff.yaml` is
  human-only.
* **Never modify scientific artifacts** unless the task spec
  explicitly allows it.
* **Never modify checkpoint or signoff ledgers** unless the task
  spec explicitly allows it.
* **Never edit agent bus, dispatcher, diagnosis, or schema code**
  from a construction-loop task unless the task spec explicitly
  allows it.
* **Keep the construction loop separate from the scientific
  runtime.** If a change would alter scientific behavior, route it
  through the scientific loop's verifier/reviewer/signoff gates,
  not this construction loop.
* **Prefer the smallest possible patch.** A task that needs a
  large patch is usually two tasks.
