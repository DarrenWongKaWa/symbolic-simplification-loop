# Construction-loop checklist

A small pre-flight and pre-landing checklist. Keep it short; the goal
is to catch the obvious mistakes (staging the wrong files, editing a
forbidden path, auto-committing) before they happen.

> Each role runs in either **manual session mode** or
> **agent-bus mode**. Pick the mode before reading or writing
> anything; the role cards document both. The HumanIntegrator's
> ready marker (`LANDING_READY`) is advisory only — the commit
> gate remains human-only.

## Pre-flight (planner)

* [ ] `Task ID` matches the filename `tasks/TASK_XXX.md`.
* [ ] `Allowed edits` lists exact paths (no broad globs).
* [ ] `Forbidden edits` lists every path that must not be touched
      (e.g. `sigma_abc/`, `checkpoints/`, `.loop/human_signoff.yaml`,
      `agent_bus/`, dispatcher code, schemas, devlog audits).
* [ ] `Acceptance commands` are runnable and deterministic.
* [ ] `Definition of done` is verifiable, not aspirational.

## Pre-handoff (executor)

* [ ] Patch is limited to `Allowed edits`.
* [ ] `executor_report.md` lists every changed file.
* [ ] All `Acceptance commands` were run and their results captured.
* [ ] `scope_deviation` is empty.
* [ ] No `git add` was performed.

## Pre-handoff (reviewer)

* [ ] `verdict` is one of `PASS`, `PASS_WITH_CAVEAT`, `FAIL`.
* [ ] `FAIL` ⇒ `blocking_issues` is non-empty.
* [ ] `PASS_WITH_CAVEAT` ⇒ `caveats` is non-empty.
* [ ] `safe_to_continue` is `false` whenever a forbidden path was
      touched, even if the rest of the patch looks fine.

## Pre-landing (human integrator)

* [ ] Reviewer verdict is `PASS` or `PASS_WITH_CAVEAT`.
* [ ] `git status --short` shows only files in `Allowed edits`.
* [ ] No file from `Forbidden edits` is staged or modified.
* [ ] No `git add .` / `git add -A` / `git add --all` was used.
* [ ] Tests were re-run after staging and passed.
* [ ] Human has explicitly said `commit now`.
* [ ] Push is **not** included unless separately requested.
* [ ] Landing report has all required fields, including
      `forbidden_path_check` and `recommended_commit_message`.

## Forbidden-path quick scan

A one-liner the integrator can paste into a terminal to confirm no
forbidden path slipped into the diff:

```bash
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/'
```

If that prints anything, stop and route the work back to the planner.

## Agent-bus mode (when applicable)

* [ ] Operating mode (`manual` / `agent-bus`) is recorded in the
      task spec.
* [ ] Inbox paths exist and were read; outbox paths are
      write-clean.
* [ ] The right ready marker is emitted on the success path
      (`TASK_READY`, `EXECUTOR_READY`, `REVIEW_READY`,
      `LANDING_READY`).
* [ ] The matching failed artifact is emitted on the failure
      path (`planner_failed.md`, `executor_failed.md`,
      `reviewer_failed.md`, `landing_blocked.md`).
* [ ] `LANDING_READY` is **not** treated as a commit green light
      by the dispatcher or any other agent.
* [ ] No dispatcher, agent-bus, or schema code was modified by
      the executor, reviewer, or integrator.
