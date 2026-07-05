# Task ID

TASK_028_CONSTRUCTION_LOOP_DOCS

# Title

Add dev-only construction loop documentation inspired by `cobusgreyling/loop-engineering`.

# Context

Backfilled from repository evidence by TASK_032. This is a **retrospective
history record** of work that was already executed and committed. It does not
re-execute, re-plan, or re-interpret the original implementation.

Before TASK_028 the repo had no construction-loop documentation. All
construction-loop work in earlier tasks (for example TASK_024 through TASK_027)
was coordinated ad-hoc. TASK_028 introduced a dedicated dev-only
documentation folder under `docs/dev/construction_loop/` so that future
construction-loop tasks could follow a stable, reviewable workflow.

# Problem

Without an explicit construction-loop documentation set, the repo could not
consistently express:

- The four-role maker/checker split (Planner / Executor / Reviewer / HumanIntegrator).
- The lifecycle that ties a construction-loop task to its reports and to
  the human commit gate.
- The boundary between the dev-only construction loop and the scientific
  symbolic-simplification runtime (verifier, reviewer, checkpoint, signoff).
- The conceptual relationship to `cobusgreyling/loop-engineering` without
  vendoring, copying, or submoduling it.

# Goal

Add a self-contained, dev-only documentation set under
`docs/dev/construction_loop/` that:

- Documents the four-role split and the simple flow
  Planner -> Executor -> Reviewer -> HumanIntegrator -> human explicit
  `commit now`.
- Names `loop-engineering` as a conceptual reference only (not vendored).
- States clearly that the construction loop is **not part of the scientific
  runtime** and does not replace verifier / reviewer / human signoff /
  checkpoint boundaries.
- Lists the explicit safety rules already adopted at that point
  (no `git add .`, no auto-commit, no auto-freeze, no auto-signoff).
- Establishes the canonical `docs/dev/construction_loop/executor_report.md`
  location for executor reports.

# Allowed edits

The original task was scoped to:

- `docs/dev/construction_loop/README.md`
- `docs/dev/construction_loop/planner.role.md`
- `docs/dev/construction_loop/executor.role.md`
- `docs/dev/construction_loop/reviewer.role.md`
- `docs/dev/construction_loop/human_integrator.role.md`
- `docs/dev/construction_loop/task_lifecycle.md`
- `docs/dev/construction_loop/external_tools.md`
- `docs/dev/construction_loop/checklist.md` (optional, included)
- `docs/dev/construction_loop/executor_report.md` (the TASK_028 executor
  report itself)

# Forbidden edits

The original task explicitly forbade:

- Editing anything under `sigma_abc/`, `checkpoints/`,
  `.loop/human_signoff.yaml`, or `docs/devlog/audits/`.
- Editing the existing root-level `executor_report.md` (TASK_025_BACKFILL).
- Vendoring, copying, or submoduling `loop-engineering`.
- Running real Claude Code / Codex CLI providers or other automation.
- Introducing any runtime automation, schema, or script.

# Actual changed files

Captured from `git show c40622b --stat --oneline`:

```text
docs/dev/construction_loop/README.md               |  77 +++++++++++++++
docs/dev/construction_loop/checklist.md            |  54 +++++++++++
docs/dev/construction_loop/executor.role.md        |  63 ++++++++++++
docs/dev/construction_loop/executor_report.md      | 107 +++++++++++++++++++++
docs/dev/construction_loop/external_tools.md       |  61 ++++++++++++
docs/dev/construction_loop/human_integrator.role.md|  80 +++++++++++++++
docs/dev/construction_loop/planner.role.md         |  67 +++++++++++++
docs/dev/construction_loop/reviewer.role.md        |  90 +++++++++++++++++
docs/dev/construction_loop/task_lifecycle.md       | 105 ++++++++++++++++++++
9 files changed, 704 insertions(+)
```

No files outside `docs/dev/construction_loop/` were modified.

# Review result summary

The TASK_028 historical executor report (`docs/dev/construction_loop/executor_report.md`
as it existed in commit `c40622b`) recorded all checks passing:

- All seven required files exist (README, four role cards, task_lifecycle,
  external_tools).
- Optional checklist.md is present.
- Forbidden-path safety check passed: no `sigma_abc/`, `checkpoints/`,
  `human_signoff`, or `docs/devlog/audits/` paths were modified.
- "This is not part of the scientific runtime" phrase present in README.
- "Never auto-commit" present in executor.role.md, task_lifecycle.md, and
  checklist.md.
- "Never `git add .`" present in task_lifecycle.md,
  human_integrator.role.md, and checklist.md.

The original executor report ended with `Final git status --short` of
`?? docs/dev/` and the explicit instruction `Stop. Do not commit.`

A canonical `review.json` artifact for TASK_028 was not preserved in the
repo at the time. The TASK_030 audit and the master repair framework both
note this omission as a known gap that TASK_032 begins to repair.

# Commit / status note

- Implementation commit: `c40622b docs: add construction loop documentation`.
- The commit landed all nine new files under `docs/dev/construction_loop/`
  with no other directories touched.
- `docs/dev/construction_loop/executor_report.md` was subsequently
  overwritten in place by TASK_029 (commit `fa93695`); therefore the
  TASK_028 executor report is only retrievable from
  `git show c40622b:docs/dev/construction_loop/executor_report.md`.
- This backfilled task file is the durable history record for TASK_028 and
  is the recommended read source going forward.

# Lessons learned

- Construction-loop docs must explicitly state they are dev-only and not
  part of the scientific runtime. Without that statement, downstream
  readers conflated the construction loop with the agent bus / verifier
  stack.
- Naming `loop-engineering` as conceptual reference (without vendoring)
  avoided dragging an external scaffold into the repo while still
  preserving shared vocabulary.
- Storing the executor report inside the same folder
  (`docs/dev/construction_loop/executor_report.md`) made it discoverable
  but also made it easy for later tasks to overwrite it. The
  `reports/TASK_XXX_<NAME>/` convention introduced later by TASK_031 fixes
  this by giving each task its own report directory.
- The four-role split and the human commit gate were the highest-value
  parts of TASK_028; the explicit safety phrasing
  ("never `git add .`", "never auto-commit") seeded the rules that later
  became `docs/safety.md` in TASK_031.