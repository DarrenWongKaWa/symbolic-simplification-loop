# Main Safety Policy

This document defines the **main-branch safety policy** for the
`symbolic-simplification-loop` repository. It is the canonical reference for
every construction-loop task, role, and human-gated action.

It is intentionally docs-only: no runtime automation, dispatcher, validator,
schema, or scientific runtime is introduced here. Behavior lives in code and
scripts; safety lives here.

## Purpose

The TASK_030 audit concluded that the main branch needed its own safety policy
before any stronger automation, probe-scaffold import, or unattended execution
could be considered. This policy establishes the minimum baseline so that
later tasks can build on top of it without re-debating fundamentals.

## Session-start conventions

### 1. Read the relevant role card first

Every new Codex / Claude Code session, regardless of role, must begin with the
instruction:

```text
Read the relevant role card first.
```

Construction-loop role cards live under:

```text
docs/dev/construction_loop/
```

Specifically:

```text
docs/dev/construction_loop/planner.role.md
docs/dev/construction_loop/executor.role.md
docs/dev/construction_loop/reviewer.role.md
docs/dev/construction_loop/human_integrator.role.md
```

If the expected role card for the current task is missing, the session must
report the gap and continue only with actions that remain safe without it.

### 2. Initial repo inspection

Before any task-specific work, every session must run and record:

```bash
pwd
git branch --show-current
git status --short
git log --oneline -5
```

These outputs make scope, branch, dirty state, and recent history explicit
before any edit.

## Task lifecycle

Every construction-loop task must move through exactly the following sequence:

```text
Planner -> Executor -> Reviewer -> HumanIntegrator -> human explicit `commit now`
```

- **Planner** writes a bounded plan.
- **Executor** implements only that plan, within its `Allowed edits`.
- **Reviewer** checks the patch and emits a verdict of `PASS`,
  `PASS_WITH_CAVEAT`, or `FAIL`.
- **HumanIntegrator** stages exact allowed files after a non-`FAIL` verdict.
- **Commit** happens only after the human explicitly says `commit now`.

No role may skip a step, merge steps together, or self-approve.

## Global forbidden actions

Unless a future human-approved plan explicitly narrows or extends these rules,
the following are forbidden in every construction-loop task and every
session:

### Staging and commits

- `git add .` is forbidden. Recursive add-dot staging is never allowed.
- Commits require the exact human instruction `commit now`. Any other
  wording — including "commit", "save", "land", "ship" — does not authorize
  a commit.
- No task may auto-commit on behalf of the human.

### Git history and remote operations

The following are forbidden for every session and every task:

- push
- merge
- reset
- rebase
- cherry-pick
- any history rewrite

The commit gate is the human's. No session may bypass it.

### Automated freeze and signoff

- No auto-freeze of scientific artifacts, validation summaries, completion
  matrices, or checkpoint contents.
- No auto-signoff. `.loop/human_signoff.yaml` and any human signoff ledger,
  history, or YAML file are human-only.

### Vendoring and integration

- No vendored `loop-engineering*` repository inside this repo.
- No git submodule unless explicitly approved by a human-approved plan.
- No provider integration (paid LLMs, APIs, external services) unless the
  task explicitly allows it.
- No Langflow or other cockpit integration unless explicitly approved.
- No ci-sweeper or other automation that runs unattended against this repo.

## Forbidden paths

The following paths are protected. No construction-loop task may create,
modify, or delete files under these paths unless the task's plan explicitly
authorizes the change:

```text
sigma_abc/
checkpoints/
validation artifacts
scientific output files
.loop/human_signoff.yaml
human signoff ledgers, histories, or YAML files
agent_bus/
loop_engine/
schemas/
scripts/
docs/devlog/audits/
```

Tasks that need to touch any forbidden path must stop, report the conflict,
and request an updated human-approved plan.

## Required checks before landing

Every Executor and HumanIntegrator must, at minimum, run:

```bash
git status --short
git diff --stat
git diff
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe"
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\.claude/|patterns/|\.github/' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
test ! -f .gitmodules
find . -maxdepth 3 -type d -name 'loop-engineering*'
```

If any of the above reports a forbidden or scaffold path, the session must
stop, report the conflict, and hand off to the human.

## Human gates

The human must explicitly approve before any of the following:

- Copying `docs/safety.md` from a probe branch into main.
- Importing any `loop-engineering` scaffold file.
- Creating `.github/`, `scripts/`, or `schemas/` content.
- Touching `agent_bus/`, `loop_engine/`, or any dispatcher.
- Running automation in non-dry-run mode.
- Allowing any scientific or runtime path edit.
- Starting any Langflow or cockpit integration.

## What this policy does not do

- It does not implement or run automation. That belongs to later tasks
  (Phase 3 onward) and only after this baseline is committed.
- It does not replace the scientific runtime contracts. The verifier,
  reviewer, checkpoint, and signoff boundaries remain authoritative.
- It does not import the `loop-engineering` probe scaffold. Import decisions
  are deferred to a separate merge-policy task.

## Source of truth

If this document conflicts with a later human-approved plan, the later plan
wins for the specific task it covers. If this document conflicts with the
master repair framework
(`docs/dev/construction_loop/loop_meta_loop_repair_framework.md`), the master
framework wins for the repair sequence; report the conflict in the task
report.