# Construction-Loop Safety Policy

> Authoritative for the cobusgreyling/loop-engineering probe in this repo.
> Read this file at the start of every construction-loop run.
> Constraints here are **binding** — the agent MUST follow them.

## Forbidden-path denylist

Construction loops (planner, executor, reviewer, human-integrator, sub-agents,
dispatcher, verifiers) **must not modify** any of the following paths unless a
bounded task explicitly allows the change **and** a human approves:

- `sigma_abc/`
- `checkpoints/`
- validation artifacts (any file under `docs/devlog/`, `validation/`, or
  `*_validation.*` produced by a run)
- human signoff ledgers, history, and YAML (e.g. `human_signoff*.yaml`,
  `signoff_history.*`, `.loop/signoff.*`)
- `.loop/human_signoff.yaml`
- scientific output files (anything produced by the symbolic-simplification
  runtime, e.g. outputs of `sigma_abc_*` runs, autoloop artefacts, generated
  reports under `docs/devlog/`)
- `agent_bus/`
- `loop_engine/`
- `schemas/`
- `scripts/`
- `docs/devlog/audits/`

If a path is ambiguous, treat it as forbidden. Escalate to the human before
touching it.

## Authoritative boundaries

The following boundaries **remain authoritative** and are not overridable by
any construction-loop directive:

- the scientific verifier (CodexReviewer / human scientist) is the final
  arbiter of correctness for any patch touching scientific or runtime code
- the human signoff ledger is the only record of "the human approved this"
- the checkpoint layer is the only source of truth for "this run produced
  this artefact"
- a human "commit now" (or equivalent) is the **only** valid commit signal

## Forbidden actions

The following actions are forbidden for any construction loop, dispatcher, or
sub-agent unless a human explicitly approves **in the current session**:

- **No auto-freeze.** No agent may freeze a run, branch, or tag.
- **No auto-signoff.** No agent may append, mutate, or interpret a signoff
  record on behalf of a human.
- **No auto-commit.** No agent may create a commit. Commits happen only when
  the human types `commit now` (or equivalent) after reviewing the patch.
- **No push without explicit human approval.** A push is never implied by a
  commit, a green CI, or a "ready" marker.
- **No `git add .`.** Stage only the files named in the task spec. Staging
  the whole tree is forbidden because it bypasses the forbidden-path check.
- **No vendor / submodule install of loop-engineering.** The probe uses
  `npx` only. The package is never copied, vendored, or wired in as a
  dependency.
- **No `ci-sweeper` pattern in L1 probes.** CI sweeping is an L2+ activity
  and is explicitly out of scope for this probe.

## Pre-flight and pre-landing checks

Run the following before any construction-loop run starts and before any
landing:

```bash
# Forbidden-path check
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe"

# No vendoring
test ! -f .gitmodules && echo "no .gitmodules"
find . -maxdepth 3 -type d -name 'loop-engineering*'
```

If either check fails, stop, report, and route the work back to the human.
