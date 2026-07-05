# Construction Loop (dev-only)

This folder documents the **dev-only construction loop** used to maintain and
improve this repository.

It is inspired by
[`cobusgreyling/loop-engineering`](https://github.com/cobusgreyling/loop-engineering)
and borrows ideas such as skills, sub-agents, maker/checker split, state, budget,
run logs, and human gates. The `loop-engineering` repository is **not vendored,
copied, or submoduled** into this project; it is a conceptual reference only.

> **This is not part of the scientific runtime.** The construction loop is a
> meta-development workflow. It does **not** replace the verifier, the
> reviewer, human signoff, or checkpoint boundaries that govern the scientific
> symbolic-simplification loop.

## What this folder is for

* Coordinating the four development sessions that improve this repo.
* Defining bounded tasks (`tasks/TASK_XXX.md`) that are small enough to
  review and easy to revert.
* Keeping dev-only workflow documentation separate from the scientific
  runtime contracts.

## What this folder is **not** for

* Scientific artifact generation, validation, or review.
* Modifying checkpoints, frozen artifacts, or human signoff ledgers.
* Replacing the agent bus, dispatcher, or schema-validated state used by
  the scientific loop.
* Replacing the verifier, the reviewer, or any human gate.

## The four development roles

| Role                  | Responsibility                                              |
| --------------------- | ----------------------------------------------------------- |
| `CodexPlanner`        | Turn a repo-improvement goal into a bounded `TASK_XXX.md`.  |
| `ClaudeCodeExecutor`  | Implement exactly one bounded task.                         |
| `CodexReviewer`       | Review the patch against task, scope, tests, and safety.     |
| `HumanIntegrator`     | Stage, test, and land reviewed patches under human control.|

See the individual role cards for inputs, outputs, and forbidden actions:

* [`planner.role.md`](./planner.role.md)
* [`executor.role.md`](./executor.role.md)
* [`reviewer.role.md`](./reviewer.role.md)
* [`human_integrator.role.md`](./human_integrator.role.md)

Each role card documents two operating modes: **manual session
mode** (a single human or single Claude/Codex session drives the
role) and **agent-bus mode** (the role runs as a sub-agent of the
construction-loop agent bus, with explicit inbox / outbox / ready
marker / failed artifact paths). The HumanIntegrator's
`LANDING_READY` marker is advisory only — the commit gate remains
human-only.

## Simple flow

```text
Problem / gap
  -> CodexPlanner writes TASK_XXX.md
  -> ClaudeCodeExecutor implements
  -> CodexReviewer reviews
  -> HumanIntegrator stages/tests/lands
  -> human explicitly approves commit
```

The full lifecycle, including repair loops, is documented in
[`task_lifecycle.md`](./task_lifecycle.md).

## Related docs

* [`task_lifecycle.md`](./task_lifecycle.md) — full task lifecycle and safety rules.
* [`external_tools.md`](./external_tools.md) — how this repo relates to
  `loop-engineering` and Langflow.
* [`checklist.md`](./checklist.md) — quick pre-flight / pre-landing checks
  (optional, lightweight).

## Conventions

Construction-loop work in this repo follows the main-branch safety policy and
the canonical reporting layout. Both are required reading before starting any
task:

* [`../../../safety.md`](../../safety.md) — main safety policy: role-card-first
  session startup, initial repo inspection, task lifecycle, forbidden paths
  and forbidden actions, and the human commit gate (`commit now`).
* [`reporting_convention.md`](./reporting_convention.md) — canonical
  `reports/TASK_XXX_<NAME>/` layout, expected report artifacts, the
  task-dependent `human_review/` and `supplement/` subdirectories, and
  the report-location normalization policy that deprecates the legacy
  report paths (`root executor_report.md` = legacy / discouraged,
  `docs/dev/construction_loop/executor_report.md` = bootstrap history only,
  `docs/dev/construction_loop/loop_engineering_probe_report.md` = probe
  evidence only).

The deeper role-card, engineering audit PDF, and theoretical derivation
supplement standards live in the master repair framework:

* [`loop_meta_loop_repair_framework.md`](./loop_meta_loop_repair_framework.md)
  — source of truth for the repair sequence after the TASK_030 audit.

## Where the canonical scientific contracts live

The scientific/runtime contracts remain the source of truth for running
symbolic simplification. They live elsewhere in the repo (e.g. the agent
bus, dispatcher, schemas, validation summaries, completion matrices,
checkpoints, and signoff ledgers). Construction-loop tasks must not
edit those contracts unless the task explicitly allows it.
