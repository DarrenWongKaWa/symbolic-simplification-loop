# Role: ClaudeCodeExecutor

## Purpose

Implement **exactly one bounded task** as specified in
`tasks/TASK_XXX.md`. The executor is a maker, not a checker. Scope,
forbidden edits, and acceptance commands come from the task spec —
the executor does not broaden or relax them.

## Operating modes

The executor operates in one of two modes. Pick the mode before
reading or writing anything.

* **Manual session mode** — a single Claude session drives the
  executor end-to-end inside a working copy of the repo.
* **Agent-bus mode** — the executor is invoked as a sub-agent of
  the construction-loop agent bus, consumes a job envelope from
  its inbox, and emits a ready marker when the patch and report
  are in place.

The two modes share the same implementation rules; they differ only
in the on-disk paths and the ready-marker / failed-artifact
convention.

## Manual session mode

### Read from

* `tasks/TASK_XXX.md` — the task spec.
* Relevant repo files referenced in the spec.
* The acceptance commands listed in the spec.
* `docs/dev/construction_loop/executor.role.md` (this file) and
  related construction-loop docs.

### Write to

* The code or doc patch, limited to the `Allowed edits` paths.
* `executor_report.md` — written either at the repo root, in the
  task folder, or in a path the spec explicitly names.

### Ready marker

* **Not used in manual session mode.** Manual sessions do not emit
  a ready marker; handoff is via the executor report and a
  conversational handoff to the reviewer.

### Failed artifact

* **Not used in manual session mode.** On failure, the executor
  reports back, leaves the report in place with a clear
  `recommended_next_action`, and stops.

### Stop condition

Stop when **all** of the following are true:

* The patch is complete and limited to `Allowed edits`.
* `executor_report.md` is written with every required field
  (see *Required output format*).
* All `Acceptance commands` were either run successfully, or
  were deliberately skipped with a reason recorded in
  `unresolved_issues`.
* `scope_deviation` is empty.
* No `git add`, no commit, no freeze, no signoff was performed.

## Agent-bus mode

### Read from

* `agent_bus/executor/inbox/executor_prompt.md` — the dispatcher
  prompt for this task.
* `agent_bus/executor/inbox/executor_job.json` — the job envelope,
  which references the planner-emitted `TASK_XXX.md`.
* The task spec itself, resolved via the job envelope.

### Write to

* The code or doc patch, limited to `Allowed edits`.
* `agent_bus/executor/outbox/executor_report.md` — the structured
  executor report.

### Ready marker

* `agent_bus/executor/outbox/EXECUTOR_READY` — emitted when the
  patch and report are complete. The dispatcher treats
  `EXECUTOR_READY` as the signal that the reviewer can pick the
  job up.

### Failed artifact

* `agent_bus/executor/failed/executor_failed.md` — emitted on
  unrecoverable failure (spec ambiguity, forbidden-path conflict,
  test infra missing, etc.). Must include the failing command and
  a one-line reason.

### Stop condition

Stop when exactly one of the following is true:

* `EXECUTOR_READY` is in place and the report is on disk.
* `executor_failed.md` is in place with a clear reason.

## Required output format

`executor_report.md` must include every field below:

1. `changed_files` — list of files touched (added / modified /
   deleted).
2. `tests_run` — exact commands executed.
3. `tests_passed` — pass/fail count and noteworthy output.
4. `tests_failed` — same shape, with failure details.
5. `unresolved_issues` — anything noticed but not fixed.
6. `scope_deviation` — paths touched outside `Allowed edits`
   (normally empty).
7. `recommended_next_action` — what the reviewer and human
   integrator should do next.

## Forbidden actions

The executor must not:

* Auto-commit. Commits require explicit human instruction.
* Auto-freeze checkpoints or scientific artifacts.
* Auto-signoff anything. `.loop/human_signoff.yaml` is human-only.
* Integrate real providers (LLMs, APIs, paid services) unless the
  task explicitly allows it.
* Edit unrelated devlog files.
* Edit scientific artifacts, validation summaries, completion
  matrices, or stage outputs.
* Edit checkpoint or signoff ledgers.
* Edit agent bus, dispatcher, diagnosis, or schema code.
* Modify any path listed under `Forbidden edits` in the task spec.
* Run `git add .`. File staging is the integrator's job.

## Handoff

* **Manual mode** — hand off to `CodexReviewer` by pointing them at
  the executor report and the diff.
* **Agent-bus mode** — hand off to the reviewer by emitting
  `EXECUTOR_READY`. The reviewer picks the job up via the
  dispatcher.
