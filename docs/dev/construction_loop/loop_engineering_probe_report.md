# Loop-Engineering Probe Report — cobusgreyling/loop-engineering × symbolic-simplification-loop

**Date:** 2026-07-03
**Probe branch:** `loop-engineering-probe` (worktree: `../symbolic-loop-probe`)
**Branched from:** `fa93695` on `sigma_abc_012c_preparation_intent_and_expected_outputs_patch` (TASK_029 HEAD)
**Pattern:** `daily-triage` · **Tool:** `claude` · **Level:** L1
**Status:** Report-only · no commits · no push · no scientific/runtime edits

---

## 1. repo_state_before

- **branch:** `sigma_abc_012c_preparation_intent_and_expected_outputs_patch`
- **HEAD:** `fa93695 Harden construction loop role file contracts` (TASK_029)
- **status:** clean
- **existing construction_loop docs:** `docs/dev/construction_loop/` — 9 role-card files (README, checklist, 4 role cards, executor_report, task_lifecycle, external_tools)
- **existing tasks/:** `TASK_024`, `TASK_025_BACKFILL`, `TASK_026`, `TASK_027` (no `TASK_028.md` / `TASK_029.md` — those iterations are tracked only via `executor_report.md`)

## 2. worktree_created

- **path:** `../symbolic-loop-probe`
- **branch:** `loop-engineering-probe` (new)
- **branched from:** `fa93695` (TASK_029)
- **status at creation:** clean
- No prior branch/worktree conflict.

## 3. loop_init_result

```
loop-init: daily-triage → <worktree> (claude)
✓ Loop Ready: 100/100 (L3)
Strong loop readiness — good candidate for L3 with explicit gates.
```

No submodule, no vendoring, no ci-sweeper pattern.

## 4. loop_audit_result

```
Score: 100/100  Level: L3
```

**Checks (9 / 11 ✓):**
- ✓ `STATE.md` present
- ✓ Triage skill present
- ✓ Verifier skill present
- ✓ `loop-constraints.md` present
- ✓ `loop-budget.md` present
- ✓ `loop-run-log.md` present
- ✓ `loop-budget` skill present
- ✓ Loop activity detected (4 sources — see §6 gap #6)
- ! No `safety.md` or `docs/safety.md`
- ! No `.github/` directory (templates / workflows for dogfooding)
- ! No `patterns/registry.yaml` (machine-readable index for future tools)

## 5. loop_cost_result

```
Cadence: 1d-2h → 12 runs/day
Level: L1 · Registry tier: low
Suggested daily cap: 100k tokens
```

| Mode | tokens/day |
|---|---|
| Early-exit / no-op | 60k (5k/run) |
| Full triage | 600k (50k/run) |
| Action every run | 2.4M (200k/run) |
| **Realistic blend** | **276k** (L1: 60% no-op, 40% full triage) |

**Warnings:**
- Worst case (action every run) exceeds suggested cap.
- Realistic estimate exceeds suggested daily cap — slow cadence or tighten scope.

## 6. generated_files

All untracked, worktree-local:

| Path | Source |
|---|---|
| `LOOP.md` | `starters/minimal-loop-claude/LOOP.md` |
| `STATE.md` | `starters/minimal-loop-claude/STATE.md.example` |
| `loop-budget.md` | created by loop-init |
| `loop-constraints.md` | `templates/loop-constraints.md` |
| `loop-run-log.md` | `templates/loop-run-log.md.template` |
| `.claude/skills/loop-triage/SKILL.md` | starter |
| `.claude/skills/loop-budget/SKILL.md` | template |
| `.claude/skills/loop-constraints/SKILL.md` | template |
| `.claude/agents/loop-verifier.md` | starter |

## 7. changed_files

`git diff --stat` is empty (no tracked file modified). `git status --short` (probe worktree):

```
?? LOOP.md
?? STATE.md
?? loop-budget.md
?? loop-constraints.md
?? loop-run-log.md
```

Plus untracked `.claude/{agents,skills}/` tree (4 files).

## 8. forbidden_path_check

```
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/'
→ scope looks safe
```

- `test ! -f .gitmodules` → `no .gitmodules` ✓
- `find . -maxdepth 3 -type d -name 'loop-engineering*'` → no `loop-engineering*` directories ✓
- `.claude/` is the agent harness root, not a runtime path.
- `scripts/` is on the forbidden list. The probe did **not** touch `scripts/` — pre-existing scripts (`scripts/audit_loop_report_consistency.py`, `scripts/run_*.py`) are tracked HEAD files.

## 9. construction_loop_readiness_gaps

The audit scores 100/100 L3 by the loop-engineering framework's own rubric, but reading the scaffold alongside the existing repo surfaces several real gaps:

1. **No `docs/safety.md`.** Audit explicitly flags this. The repo *has* a hardcoded forbidden-path list in `docs/dev/construction_loop/checklist.md` and in `task_lifecycle.md`'s "Safety rules", but it lives inline in role cards, not as a standalone denylist that an L2/L3 loop can read in one shot.
2. **No `patterns/registry.yaml`.** The audit's machine-readable index is missing. This repo has `loop_config.json`, `profiles/*.yaml`, `projects/*/loop.yaml` — repo-specific, not the loop-engineering registry format.
3. **No `.github/` directory.** No issue / PR templates, no CI workflows. Loop-engineering expects "dogfooding" of the loop inside the repo's own GitHub surface.
4. **Naming collision / ambiguity.** The probe added `LOOP.md` at repo root, while the repo already has `docs/dev/construction_loop/` (a *different* construction loop — the planner / executor / reviewer / human_integrator flow with manual session vs agent-bus modes). Two different "loops" in the same repo, both labelled "loop", and the role-card docs (TASK_028 + TASK_029) never mention `LOOP.md` from cobusgreyling. A future operator will be confused about which `LOOP.md` they are reading.
5. **TASK_028 and TASK_029 are not in `tasks/`.** `ls tasks/` shows only TASK_024 through TASK_027. The last two iterations of the in-repo construction loop are tracked only via `docs/dev/construction_loop/executor_report.md`. The `loop-triage` skill expects to read tasks from a discoverable place.
6. **Loop activity count = 4 sources** is inherited from pre-existing repo content (`scripts/run_*.py`, `tests/test_loop*.py`, `projects/sigma_abc/loop.yaml`, `skill/symbolic_simplification_loop.md`) — i.e. the existing scientific runtime loop, not anything the probe added. The 100/100 score is largely inherited, not earned by the probe.
7. **`loop-budget.md` is a template.** It still says "YOUR_PROJECT" and has no concrete number for this repo's actual `Max tokens/day` (audit recommended 100k; `loop-cost` said realistic blend is 276k — those numbers already disagree).
8. **No `docs/safety.md` denylist for the new probe.** `LOOP.md` does not name the forbidden paths. If loop-engineering ever auto-runs, it has no awareness of `sigma_abc/`, `checkpoints/`, `human_signoff`, etc.
9. **Cadence mismatch.** `loop-cost` recommends "1d-2h" cadence (12 runs/day) for daily-triage, but the immediate suggestion printed by `loop-init` is `/loop 1d Run $loop-triage` (1 run/day). Contradict each other.

## 10. safest_next_improvement

**Docs-only: add `docs/safety.md` denylist** that consolidates the forbidden paths and `loop-pause-all` semantics, then point `loop-constraints.md` at it.

Why this is the safest:
- Pure docs change, no scientific/runtime code touched.
- Addresses an audit-flagged gap (the only `!` that is clearly additive, not architectural).
- Closes the largest *concrete* failure mode for any future L2+ loop run: a loop-engineering agent that doesn't know `sigma_abc/`, `checkpoints/`, `human_signoff` are off-limits.
- Smallest blast radius: a single new markdown file, no edits to anything else.
- Required before any L2+ work in this repo per the audit's own recommendation.

What it is **not**:
- Not the highest-impact gap (the naming collision and missing `tasks/TASK_028.md` are higher-impact).
- Does not unify the two "loops" (cobusgreyling `LOOP.md` vs in-repo `docs/dev/construction_loop/`).
- Does not produce a real `loopActivity` event, so the 100/100 score will not improve (the score is already inflated by pre-existing repo content).

## 11. recommended_next_action

Docs-only, single file:

1. Create `docs/safety.md` listing the forbidden paths verbatim (the eight directories plus `.loop/human_signoff.yaml` if that exists).
2. Add a one-line cross-reference from `loop-constraints.md` ("See `docs/safety.md` for the project denylist").
3. Re-run `npx @cobusgreyling/loop-audit . --suggest` to confirm the `! No safety.md` warning clears.
4. Manually update `STATE.md` with the run timestamp and outcome (per loop-engineering v1.4 — this is the only state-file write the probe protocol allows).
5. Stop. Do not commit (probe protocol says: do not commit). Hand off for human review.

Then, in a separate task (not this probe), a planner can decide whether to:
- unify the two "loop" namespaces (rename `LOOP.md` to `LOOP_ENGINEERING.md` or fold `docs/dev/construction_loop/` into a `docs/loop/` tree),
- write `tasks/TASK_028.md` and `tasks/TASK_029.md` so the loop-triage skill can find them,
- adopt a `patterns/registry.yaml` for tool routing.

## 12. unresolved_issues

1. **Did the audit pass too easily?** Score 100/100 L3 with three `!`s still showing feels inconsistent. Either the rubric is lenient, or "loop activity detected" is doing heavy lifting from pre-existing repo content. Worth flagging upstream to cobusgreyling.
2. **TASK_028 and TASK_029 not in `tasks/`.** Either intentional (the construction loop is meta and lives in `docs/dev/`) or an oversight. The probe cannot tell.
3. **Cadence printed twice with different values.** `loop-init` said `/loop 1d`; `loop-cost` said `1d-2h → 12 runs/day`. Need to pick one before any L2 work.
4. **No MCP server was tested.** The probe did not connect any external provider, and `LOOP.md` says "MCP optional for L1 report-only loops." Correct for L1, but the loop-budget MCP-cost numbers are theoretical.
5. **`loop-budget.md` is unedited.** Still says "YOUR_PROJECT" placeholder; the audit's 100k/day cap and `loop-cost`'s 276k/day realistic estimate are not reconciled. Out of scope for the probe.
6. **No probe follow-up scheduled.** Per single-writer memory rule, no tmux runner was started. The probe is one-shot; the next time a loop runs, it would be a human-initiated `/loop 1d Run $loop-triage`.

---

## Probe safety summary

| Check | Result |
|---|---|
| Clean tree precondition | ✓ met |
| Worktree / branch conflict | ✓ none |
| `loop-init` completed | ✓ |
| `loop-audit` completed | ✓ |
| `loop-cost` completed | ✓ |
| Forbidden paths in `git status` | ✓ none |
| `.gitmodules` created | ✓ no |
| `loop-engineering*` dirs created | ✓ none |
| Tracked files modified | ✓ none |
| `sigma_abc/`, `checkpoints/`, `human_signoff`, `docs/devlog/audits/`, `agent_bus/`, `loop_engine/`, `schemas/`, `scripts/` | ✓ untouched |
| Commits made | ✓ none |
| Pushes made | ✓ none |
| Auto-freeze | ✓ not invoked |
| Auto-signoff | ✓ not invoked |
| Scientific / runtime files | ✓ unmodified |
| `ci-sweeper` pattern | ✓ not run |
| Langflow integration | ✓ none |
| Real provider integration | ✓ none |

## Decision pending

The probe report itself lives at `docs/dev/construction_loop/loop_engineering_probe_report.md` (this file), uncommitted, in the parent worktree. The probe worktree at `../symbolic-loop-probe/` and branch `loop-engineering-probe` remain as-is for human review. No commit, no push, no merge. Awaiting human decision on:
- whether to land any of the generated scaffold onto the main branch,
- whether to adopt the recommended next action (add `docs/safety.md`),
- whether to keep, rename, or delete the `loop-engineering-probe` worktree.
