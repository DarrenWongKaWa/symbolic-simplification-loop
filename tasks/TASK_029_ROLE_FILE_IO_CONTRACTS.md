# Task ID

TASK_029_ROLE_FILE_IO_CONTRACTS

# Title

Harden construction-loop role files with explicit input/output contracts.

# Context

Backfilled from repository evidence by TASK_032. This is a **retrospective
history record** of work that was already executed and committed. It does not
re-execute, re-plan, or re-interpret the original implementation.

TASK_029 followed TASK_028 directly. TASK_028 created the construction-loop
documentation set but left each role card as a prose description of purpose
and forbidden actions. The role cards did not yet spell out exactly what
each role may read, what it must write, what completion signal it emits, or
what failure artifact it should produce. TASK_029 added that explicit
contract so that role sessions — manual or agent-bus — could be checked by
humans and by future scripts.

# Problem

The construction-loop role cards created in TASK_028 were sufficient as
human-readable descriptions but were not yet machine-checkable contracts:

- They did not name a single canonical manual-session output path per role.
- They did not separate manual-session mode from a possible agent-bus mode.
- They did not name a ready-marker file or a failed-artifact file for each
  role.
- They did not state an explicit stop condition per role.
- They did not state a per-role handoff target.

This made it easy for a role session to drift: e.g., an executor might
write a report to an arbitrary path and forget to signal completion, or a
reviewer might forget to declare its verdict shape.

# Goal

Extend the four TASK_028 role cards (and the supporting task_lifecycle,
checklist, and README docs) so that each one declares:

- Operating modes: Manual session mode and (where applicable) Agent-bus
  mode.
- Manual-session Read paths.
- Manual-session Write paths.
- Ready marker file name.
- Failed artifact file name and shape.
- Stop condition.
- Forbidden actions.
- Handoff target.
- Required output format.

Also make explicit that the HumanIntegrator's `LANDING_READY` is **advisory
only** — the commit gate remains human-only — and that the HumanIntegrator
does not use the same ready-marker handoff pattern as the other three
roles.

# Allowed edits

The original task was scoped to:

- `docs/dev/construction_loop/planner.role.md`
- `docs/dev/construction_loop/executor.role.md`
- `docs/dev/construction_loop/reviewer.role.md`
- `docs/dev/construction_loop/human_integrator.role.md`
- `docs/dev/construction_loop/task_lifecycle.md`
- `docs/dev/construction_loop/checklist.md`
- `docs/dev/construction_loop/README.md`
- `docs/dev/construction_loop/executor_report.md` (overwrites TASK_028
  report in place)

# Forbidden edits

The original task explicitly forbade:

- Editing `agent_bus/`, `loop_engine/`, `schemas/`, `scripts/`,
  `sigma_abc/`, `checkpoints/`, validation outputs, human signoff ledgers,
  or `.loop/human_signoff.yaml`.
- Editing `docs/dev/construction_loop/external_tools.md` (no clarification
  was needed because the role-card I/O contracts are clearly scoped to the
  construction loop).
- Editing the existing root-level `executor_report.md` (TASK_025_BACKFILL).
- Implementing any runtime automation, provider integration, or
  loop-engineering scaffold import.

# Actual changed files

Captured from `git show fa93695 --stat --oneline`:

```text
docs/dev/construction_loop/README.md               |   8 +
docs/dev/construction_loop/checklist.md            |  23 +++
docs/dev/construction_loop/executor.role.md        | 139 ++++++++++++----
docs/dev/construction_loop/executor_report.md      | 133 +++++++++------
docs/dev/construction_loop/human_integrator.role.md| 178 +++++++++++++++------
docs/dev/construction_loop/planner.role.md         | 142 ++++++++++++----
docs/dev/construction_loop/reviewer.role.md        | 153 +++++++++++++-----
docs/dev/construction_loop/task_lifecycle.md       |  20 +++
8 files changed, 592 insertions(+), 204 deletions(-)
```

No files outside `docs/dev/construction_loop/` were modified.

# Review result summary

The TASK_029 executor report
(`docs/dev/construction_loop/executor_report.md` as it exists today)
recorded all checks passing:

- All seven required files exist.
- Each of the four role files contains the required section headers
  (`Operating modes`, `Read from`, `Write to`, `Ready marker`,
  `Failed artifact`, `Stop condition`, `Required output format`,
  `Forbidden actions`, `Handoff`).
- `human_integrator.role.md` explicitly states that `LANDING_READY` is
  advisory only and that the integrator does not use the same
  ready-marker handoff pattern as the other three roles.
- `task_lifecycle.md` and `checklist.md` reference the two operating modes
  and the integrator's advisory marker.
- `README.md` documents the two operating modes at the top of the
  role-cards section.
- `external_tools.md` was deliberately left untouched.
- Forbidden-path safety check passed: no `sigma_abc/`, `checkpoints/`,
  `human_signoff`, or `docs/devlog/audits/` paths were modified.

`scope_deviation` was empty. `tests_failed` was `None`.

A canonical `review.json` artifact for TASK_029 was not preserved in the
repo at the time. The TASK_030 audit and the master repair framework
both note this omission as a known gap that TASK_032 begins to repair.

# Commit / status note

- Implementation commit: `fa93695 Harden construction loop role file
  contracts`.
- The commit modified all four role files plus task_lifecycle, checklist,
  README, and the executor_report (which was overwritten in place).
- The executor report ended with `Final git status --short` of
  `?? docs/dev/` and the explicit instruction `Stop. Do not commit.`
- This backfilled task file is the durable history record for TASK_029.

# Lessons learned

- A role card that lists purpose and forbidden actions is not enough; it
  must also name read paths, write paths, completion signals, and handoff
  targets. Without those, downstream automation cannot reliably drive the
  role.
- The HumanIntegrator's handoff is fundamentally different from the other
  three roles because the commit gate is human-only. Spelling this out
  (with an explicit `LANDING_READY` is advisory only note) prevents
  future readers from assuming symmetry across the four roles.
- Overwriting `executor_report.md` in place across tasks makes the file
  cheap to maintain but makes per-task history lossy. TASK_031's
  `reports/TASK_XXX_<NAME>/` convention fixes this going forward by
  giving each task its own executor report location; this backfill
  re-establishes the per-task history for TASK_028 and TASK_029 that was
  lost to in-place overwrites.
- Future role-card work can lean on the section shape established by
  TASK_029 (`Operating modes` / `Read from` / `Write to` / etc.) as a
  stable template. The master repair framework's `Role-card standard`
  section formalizes this further in a later phase.