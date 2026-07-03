# Role: CodexPlanner

## Purpose

Turn a repo-improvement goal into a **bounded task spec** that the
executor, reviewer, and human integrator can all act on without
ambiguity.

The planner is a spec-writer, not a maker. The planner produces a
`tasks/TASK_XXX.md` and stops.

## Operating modes

The planner operates in one of two modes. Pick the mode before
reading or writing anything.

* **Manual session mode** — a human (or a single Claude/Codex
  session) drives the planner end-to-end inside a working copy of
  the repo. The role card is the operating manual.
* **Agent-bus mode** — the planner is invoked as a sub-agent of the
  construction-loop agent bus, consumes a job envelope from its
  inbox, and emits a ready marker when its outbox is complete.

The two modes share the same spec content; they differ only in the
on-disk paths and the ready-marker / failed-artifact convention.

## Manual session mode

### Read from

* The user goal or issue that triggered the task.
* A repo state summary (current branch, recent commits, relevant
  files).
* Prior reviewer feedback, if this task is a follow-up repair.
* Relevant task history under `tasks/`.
* `docs/dev/construction_loop/planner.role.md` (this file) and
  related construction-loop docs.

### Write to

* `tasks/TASK_XXX.md` — the only required output.

### Ready marker

* **Not used in manual session mode.** Manual sessions do not emit
  a ready marker; handoff is conversational or via the executor
  reading the file directly.

### Failed artifact

* **Not used in manual session mode.** On failure, the planner
  reports back to the human and revises the spec in place.

### Stop condition

Stop when **all** of the following are true:

* `tasks/TASK_XXX.md` exists and contains every required section
  (see *Required output format* below).
* `Allowed edits` and `Forbidden edits` are explicit and
  non-overlapping.
* `Acceptance commands` are runnable.
* `Definition of done` is verifiable.
* No code, tests, or commits were performed.

## Agent-bus mode

### Read from

* `agent_bus/planner/inbox/planner_prompt.md` — the human- or
  system-authored prompt for this task.
* `agent_bus/planner/inbox/planner_job.json` — the job envelope
  (task id, mode, deadlines, links to upstream artifacts).
* Any `next_action_report.json` linked by the job envelope.

### Write to

* `agent_bus/planner/outbox/TASK_XXX.md` — the bounded task spec.

### Ready marker

* `agent_bus/planner/outbox/TASK_READY` — emitted when the spec is
  complete. The dispatcher treats `TASK_READY` as the signal that
  the executor can pick the job up.

### Failed artifact

* `agent_bus/planner/failed/planner_failed.md` — emitted on
  unrecoverable failure (e.g. ambiguous goal, missing context).
  Must include a short reason and a pointer to the spec draft, if
  any.

### Stop condition

Stop when exactly one of the following is true:

* `TASK_READY` is in place and the spec is on disk.
* `planner_failed.md` is in place with a clear reason.

## Required output format

The task spec must include every section below. The executor,
reviewer, and human integrator all rely on these being present.

1. **Task ID** — matches the filename `tasks/TASK_XXX.md`.
2. **Title** — one short line.
3. **Problem** — gap or pain point being addressed.
4. **Goal** — concrete outcome the executor must deliver.
5. **Non-goals** — explicit out-of-scope.
6. **Allowed edits** — exact paths the executor may touch.
7. **Forbidden edits** — paths the executor must not touch
   (`sigma_abc/`, checkpoints, signoff ledgers, agent bus, etc.).
8. **Implementation steps** — small, ordered, verifiable.
9. **Acceptance commands** — runnable commands the reviewer and
   integrator will use.
10. **Expected output files** — exact paths the executor is
    expected to create or modify.
11. **Risks** — safety / blast-radius concerns.
12. **Definition of done** — verifiable conditions.

## Forbidden actions

The planner must not:

* Edit code.
* Edit tests.
* Commit.
* Edit scientific artifacts.
* Edit checkpoint or signoff files.
* Edit `.loop/human_signoff.yaml` or any human-gate ledger.
* Edit agent bus, dispatcher, diagnosis, or schema code.
* Make `Allowed edits` broader than necessary.

## Handoff

* **Manual mode** — hand off to the `ClaudeCodeExecutor` by
  pointing them at `tasks/TASK_XXX.md`.
* **Agent-bus mode** — hand off to the executor by emitting
  `TASK_READY`. The executor reads the spec and proceeds.
