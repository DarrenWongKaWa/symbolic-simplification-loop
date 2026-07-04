# Executor Report — TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS

## task_id

TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS

## changed_files

- `docs/safety.md` (created)
- `docs/dev/construction_loop/reporting_convention.md` (created)
- `docs/dev/construction_loop/README.md` (updated minimally — added a
  "Conventions" section pointing to the new safety and reporting docs and
  to the master repair framework)
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/executor_report.md`
  (this file)

No other files were modified.

## commands_run

The following commands were run during this task, in order:

```bash
pwd
git branch --show-current
git status --short
git log --oneline -5
```

Read-only inspection of:

- `docs/dev/construction_loop/executor.role.md`
- `docs/dev/construction_loop/loop_meta_loop_repair_framework.md`
- `reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/PLAN.md`
- `docs/dev/construction_loop/README.md` (existing — updated minimally)

Lightweight validation after edits:

```bash
test -f docs/safety.md
test -f docs/dev/construction_loop/reporting_convention.md
test -f docs/dev/construction_loop/README.md
test -f reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/executor_report.md
grep -R "Read the relevant role card first" docs/safety.md docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "Planner -> Executor -> Reviewer -> HumanIntegrator -> human explicit" docs/safety.md docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "commit now" docs/safety.md docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "git add \\." docs/safety.md docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
grep -R "reports/TASK_XXX_<NAME>" docs/dev/construction_loop/reporting_convention.md docs/dev/construction_loop/README.md
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe"
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\.claude/|patterns/|\.github/' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
test ! -f .gitmodules
find . -maxdepth 3 -type d -name 'loop-engineering*'
git diff --check
git diff --stat
```

No build, render, or test commands were run — this task is docs-only and
introduces no runnable artifact. `build.log` was therefore intentionally
not created.

## tests_passed

All acceptance commands applicable to a docs-only task passed:

- `test -f docs/safety.md` — pass
- `test -f docs/dev/construction_loop/reporting_convention.md` — pass
- `test -f docs/dev/construction_loop/README.md` — pass
- `test -f reports/TASK_031_MAIN_SAFETY_AND_REPORTING_CONVENTIONS/executor_report.md` — pass
- Required content greps — pass (each mandatory convention string is present
  in at least one of the three target docs; see *Content checks* below).
- `git diff --check` — pass (no whitespace / conflict markers).
- Forbidden-path dirty check — pass (`scope looks safe`).
- Scaffold-path dirty check — pass (`no scaffold merge`).
- `.gitmodules` absent — pass.
- No vendored `loop-engineering*` directory under the repo (top three
  levels) — pass.

### Content checks

The mandatory conventions are present as follows:

| Convention                                                                  | Where it appears                                                                                            |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Role-card-first session instruction (`Read the relevant role card first.`)  | `docs/safety.md`                                                                                            |
| Initial repo inspection (`pwd`, `git branch --show-current`, ...)           | `docs/safety.md`                                                                                            |
| Lifecycle (`Planner -> Executor -> Reviewer -> HumanIntegrator -> ...`)     | `docs/safety.md`                                                                                            |
| `git add .` forbidden                                                       | `docs/safety.md`                                                                                            |
| Commit only after exact `commit now`                                        | `docs/safety.md`                                                                                            |
| Push/merge/reset/rebase/cherry-pick/auto-freeze/auto-signoff forbidden      | `docs/safety.md`                                                                                            |
| Forbidden paths (`sigma_abc/`, `checkpoints/`, `agent_bus/`, ...)           | `docs/safety.md`                                                                                            |
| Canonical report directory `reports/TASK_XXX_<NAME>/`                       | `docs/dev/construction_loop/reporting_convention.md`, `docs/dev/construction_loop/README.md`               |
| Required report artifacts list (`PLAN.md`, `executor_report.md`, ...)       | `docs/dev/construction_loop/reporting_convention.md`                                                        |
| Human-output subdirectories `human_review/`, `supplement/`                  | `docs/dev/construction_loop/reporting_convention.md`                                                        |
| Pointer to role-card, engineering audit PDF, theoretical supplement standards | `docs/dev/construction_loop/reporting_convention.md`, `docs/dev/construction_loop/README.md`               |
| Role-card paths under `docs/dev/construction_loop/`                         | `docs/safety.md`                                                                                            |

## tests_failed

None. No acceptance command failed.

## forbidden_path_check

For this task the check was run as the literal command:

```bash
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe"
```

Result: `scope looks safe`. The only dirty paths are the four allowed files
listed in `changed_files`.

The scaffold-path check:

```bash
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\.claude/|patterns/|\.github/' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
```

Result: `no scaffold merge`.

## scope_deviation

Empty. No paths outside the `Allowed edits` set were touched.

## unresolved_issues

- The master repair framework contains both `reports/TASK_XXX/` and
  `reports/TASK_XXX_<NAME>/` examples. TASK_031 standardizes on
  `reports/TASK_XXX_<NAME>/` and documents the short form as legacy
  shorthand; a future TASK_033 may formally deprecate the short form.
- The role-card, engineering audit PDF, and theoretical derivation
  supplement standards currently live in the master repair framework.
  Later tasks may split them into dedicated docs; the reporting convention
  already points there for now.
- A previous reviewer verdict (`review_result.json`) exists in this task
  directory from the prior pre-plan review. Executor did not modify it;
  this is intentional and outside the allowed edits. Reviewer may overwrite
  it on this round if desired.

## recommended_next_action

1. Reviewer reads the four changed files plus this report and emits a fresh
   `review_result.json` with verdict `PASS`, `PASS_WITH_CAVEAT`, or `FAIL`.
2. On `PASS` or `PASS_WITH_CAVEAT` with no blocking issues, HumanIntegrator
   stages the four files individually (no `git add .`) and writes
   `landing_report.md`.
3. Commit only after the human explicitly says `commit now`.
4. After commit, proceed to TASK_032 (backfill TASK_028/029 task history).

## confirmation

- Nothing was staged (`git add` not used in any form).
- Nothing was committed.
- No push, merge, reset, rebase, cherry-pick, auto-freeze, or auto-signoff
  was performed.
- No provider, Langflow, ci-sweeper, vendored loop-engineering, or
  submodule was introduced.