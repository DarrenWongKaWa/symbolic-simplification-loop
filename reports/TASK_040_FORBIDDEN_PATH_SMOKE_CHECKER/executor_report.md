# Executor Report — TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER

## task_id

TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER

## current_pwd_branch_head

- pwd: `/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-loop-audit-report`
- branch: `task-030-loop-meta-loop-audit`
- HEAD: `c7d3b2e TASK_033 normalize report location policy`

## plan_md_path_read

`reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/PLAN.md`

(Note: `reports/` is gitignored at `.gitignore:23`, so PLAN.md does
not appear in `git status --short`. The file exists at the explicit
path above and was read in full before any work began.)

## changed_files

- `scripts/check_forbidden_paths.py` (created; chmod +x)
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/executor_report.md`
  (this file, created; untracked because `reports/` is gitignored)

No other files were modified. The TASK_040 PLAN.md was not modified.
No TASK_031 / TASK_032 / TASK_033 artifacts were touched. No other
`scripts/` path was created or modified. No TASK_041 / TASK_042 work
was started.

## summary_of_changes

Added a read-only, stdlib-only Python 3 CLI at
`scripts/check_forbidden_paths.py` that:

1. Runs `git status --short` in the current working directory (or the
   directory passed via `--cwd`).
2. Parses the status output into a sorted list of dirty paths
   (handling renames, copies, and quoted paths).
3. Classifies each path against the construction-loop forbidden-path
   denylist documented in `docs/safety.md` and the master repair
   framework, with one narrow self-exclusion for
   `scripts/check_forbidden_paths.py` itself, which is the only
   `scripts/` exception authorized by TASK_040 PLAN.md.
4. Prints a reviewer-readable summary to stdout (count of forbidden
   hits, count of clean dirty paths, list of forbidden matches with
   the pattern that matched, list of non-forbidden dirty paths).
5. Exits `0` when no forbidden dirty paths are detected.
6. Exits `1` when one or more forbidden dirty paths are detected.
7. Exits `2` when `git status --short` cannot be executed (e.g. not a
   git working tree, or `git` missing on `PATH`).

The script also exposes a `--self-test` flag that runs an internal
behavior smoke test in a fresh temporary git repository. The self-test
asserts that a clean repo exits `0`, a benign dirty file exits `0`,
a `sigma_abc/` dirty file exits `1` with pattern `sigma_abc/`, and a
`loop-engineering-clone/` directory exits `1` matched by the
`loop-engineering*` glob pattern.

Denylist coverage exactly mirrors the patterns required by PLAN §9:

```text
sigma_abc/                    checkpoints/                  human_signoff
docs/devlog/audits/           agent_bus/                    loop_engine/
schemas/                      scripts/                      .loop/human_signoff.yaml
LOOP.md                       STATE.md                      loop-budget.md
loop-run-log.md               .claude/                      .github/
patterns/                     loop-constraints.md           .gitmodules
loop-engineering*
```

Per PLAN §10, the documentation-only categories "validation
artifacts" and "scientific output files" are intentionally **not**
added as patterns — the script preserves documented concrete path
checks and avoids inventing broad destructive matching.

The script is non-mutating by construction:

- It runs only `git status --short`, which is read-only.
- It uses no third-party packages.
- It uses no `git add`, `git commit`, `git push`, `git merge`,
  `git reset`, `git rebase`, `git cherry-pick`, `git tag`, `git
  checkout`, or `git update-ref` calls.
- It does not write any artifact into the worktree, the temp
  directory is created under `tempfile.mkdtemp` and removed by the
  `finally` block in `run_self_test()`.
- It performs no network I/O.

## commands_run

```bash
pwd
git branch --show-current
git status --short
git log --oneline -5

# Source-of-truth reads
sed -n '932,965p' docs/dev/construction_loop/loop_meta_loop_repair_framework.md
sed -n '1,200p' docs/safety.md
sed -n '1,260p' docs/dev/construction_loop/reporting_convention.md
sed -n '1,120p' docs/dev/construction_loop/README.md
sed -n '1,30p' scripts/check_pre_run_gate.py
sed -n '1,80p' scripts/audit_loop_report_consistency.py

# Compile and CLI
python3 -m py_compile scripts/check_forbidden_paths.py
chmod +x scripts/check_forbidden_paths.py
python3 scripts/check_forbidden_paths.py --help

# Worktree invocation — must self-exclude and exit 0
python3 scripts/check_forbidden_paths.py
echo $?

# Internal self-test
python3 scripts/check_forbidden_paths.py --self-test

# PLAN-mandated temp-repo smoke test (clean → 0; benign → 0; forbidden → 1)
tmpdir="$(mktemp -d)"
cd "$tmpdir"
git init -q
python3 <repo>/scripts/check_forbidden_paths.py
echo "ok" > README.md
python3 <repo>/scripts/check_forbidden_paths.py
mkdir -p sigma_abc
echo "bad" > sigma_abc/dirty.txt
python3 <repo>/scripts/check_forbidden_paths.py && echo "UNEXPECTED PASS" || echo "expected forbidden-path failure"
cd <repo>

# Final scope checks
git diff --stat
git diff --check
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' | grep -v 'scripts/check_forbidden_paths.py' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe except approved checker path"
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\.claude/|patterns/|\.github/|loop-constraints.md' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
test ! -f .gitmodules
find . -maxdepth 3 -type d -name 'loop-engineering*'
git diff --cached --name-only
```

No `audit_evidence.md`, `final_summary.md`, or `build.log` was
created — the executor report captures command evidence and no
parallel build/render artifact was produced.

## tests_passed

- `python3 -m py_compile scripts/check_forbidden_paths.py` — pass
- `python3 scripts/check_forbidden_paths.py --help` — pass
- Worktree invocation: pass (`forbidden hits : 0`, exit 0,
  self-excludes `scripts/check_forbidden_paths.py`)
- `--self-test`: pass (`self-test: OK (clean=0, benign=0,
  forbidden=1, glob=1)`)
- PLAN temp-repo smoke test:
  - clean repo → exit 0, 0 forbidden hits — pass
  - benign `README.md` → exit 0, 0 forbidden hits — pass
  - `sigma_abc/dirty.txt` → exit ≠ 0, 1 forbidden hit
    (`sigma_abc/dirty.txt` matched `sigma_abc/`) — pass
- `git diff --stat` — pass (no tracked file modified; new script is
  untracked)
- `git diff --check` — pass
- Forbidden-path dirty check — `scope looks safe except approved
  checker path`
- Scaffold-path dirty check — `no scaffold merge`
- `test ! -f .gitmodules` — pass
- `find . -maxdepth 3 -type d -name 'loop-engineering*'` — empty
- `git diff --cached --name-only` — empty (nothing staged)

## tests_failed

None. All applicable acceptance commands passed.

## forbidden_path_check

```bash
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' | grep -v 'scripts/check_forbidden_paths.py' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe except approved checker path"
```

Result: `scope looks safe except approved checker path`. The only
dirty path is `scripts/check_forbidden_paths.py`, which is the
explicit, scoped, narrow TASK_040 scripts exception per PLAN §In-scope
Files. The PLAN itself notes that the checker is itself a dirty
`scripts/` path while unstaged and authorizes that as the only
permitted scripts exception for this task.

Scaffold-path check:

```bash
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\.claude/|patterns/|\.github/|loop-constraints.md' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
```

Result: `no scaffold merge`.

## scope_deviation

Empty. The executor created only files inside the `Allowed edits` set
listed in PLAN.md:

- `scripts/check_forbidden_paths.py`
- `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/executor_report.md`

No file under `docs/safety.md`, `docs/dev/construction_loop/`,
`docs/dev/construction_loop/loop_meta_loop_repair_framework.md`,
`reports/TASK_031_*/`, `reports/TASK_032_*/`,
`reports/TASK_033_*/`, or any other `scripts/` path was created or
modified. No test or fixture was added — the PLAN explicitly notes
that tests are out of scope unless a future human-approved plan
expands the task. No local runner, GitHub automation, ci-sweeper,
provider integration, scaffold import, or TASK_041 / TASK_042 work
was started.

## unresolved_issues

- **Self-exclusion is necessary while unstaged.** While
  `scripts/check_forbidden_paths.py` itself is an unstaged dirty
  file, the worktree invocation must exclude its own path from the
  forbidden hit list, otherwise it would report itself as forbidden.
  The script encodes this as `SELF_REL_PATH = "scripts/check_forbidden_paths.py"`
  and never flags it. After HumanIntegrator stages the file and the
  human commits, the path is no longer dirty, so the exclusion
  becomes inert but harmless.
- **Documentation-only categories not encoded.** "validation
  artifacts" and "scientific output files" are documented as
  forbidden-path categories in `docs/safety.md` but no concrete path
  prefixes are defined for them. Per PLAN §10, the script preserves
  documented concrete path checks and avoids inventing broad
  destructive matching. Machine-checkable validation of these
  categories is left to TASK_041 / TASK_042 per the master framework
  and is explicitly out of scope here.
- **`scripts/` is broadly forbidden.** The global safety policy
  treats `scripts/` as forbidden. This task is the narrow,
  PLAN-explicit exception for exactly
  `scripts/check_forbidden_paths.py`. Future tasks must not extend
  this exception without a fresh human-approved plan.
- **`reports/` tree is gitignored.** The TASK_040 PLAN.md and this
  executor report do not appear in normal `git status --short`.
  Matches the precedent set by TASK_030, TASK_031, TASK_032, and
  TASK_033. HumanIntegrator may need explicit path force-staging for
  the executor report; recursive add-dot staging remains forbidden.
- **No machine-checkable validator for non-staged paths yet.** The
  checker only inspects the working-tree dirty state at the moment
  of invocation. It does not scan the entire filesystem for files
  that exist but are not dirty. That scope is owned by later checker
  tasks (TASK_041 / TASK_042) per the master framework.
- **No tests added.** Per PLAN `Assumptions` and `Stop Conditions`,
  no test framework or fixtures were introduced. Behavior validation
  is provided by the `--self-test` flag and the PLAN-mandated
  temp-repo smoke test.

## deviations_from_plan

None of substance. Three minor procedural notes:

1. The PLAN's `Acceptance Commands` lists both `python` and
   `python3` invocations interchangeably. The host system has
   `python3` on `PATH` (`/usr/bin/python3`); `python` is not
   guaranteed to exist. The executor used `python3` consistently and
   noted this in `commands_run`. The script itself uses
   `#!/usr/bin/env python3` so behavior is identical.
2. The PLAN's `Acceptance Commands` runs the checker against a temp
   git repo created with only `git init -q` (no initial commit).
   On a no-HEAD git repo, `git status --short` still works
   correctly, so this did not require a fix. The executor's
   `--self-test` flag creates an initial empty commit for symmetry
   and to keep the temp repo's status output minimal.
3. The PLAN's `Acceptance Commands` includes the literal command
   that pipes the checker into `&&` / `||` chaining against the
   forbidden-path case. That branching produced the expected
   `expected forbidden-path failure` message — recorded above as
   the canonical evidence that the script returns nonzero on
   forbidden dirty paths.
4. PLAN.md was not modified. No clerical correction was required.

## risks_and_caveats

- **Pattern semantics.** Patterns ending in `/` are directory
  prefixes; patterns ending in `*` are top-level globs (matched
  against the first path segment with `startswith`); bare tokens
  match the top segment or any path that equals the token. This is
  documented in the script docstring and `matches_forbidden()` and
  is the smallest interpretation consistent with the PLAN's denylist.
- **Renames / copies.** `git status --short` lines of the form
  `XY from -> to` use the rename/copy **target** as the path that
  would be staged. The script extracts the target so it cannot be
  tricked into missing a rename that lands a forbidden name in the
  tree.
- **Submodules.** The script does not recurse into submodules. This
  is intentional — submodules are forbidden by `.gitmodules`, and a
  submodule that ever became dirty would still surface under
  `scripts/`, `agent_bus/`, etc. via the matching dirty path of the
  superproject.
- **No network.** The script does no network I/O and depends only
  on the Python standard library (`argparse`, `os`, `shutil`,
  `subprocess`, `sys`, `pathlib`) plus `tempfile` (only used by the
  optional `--self-test`).
- **Exit code semantics.** `2` is reserved for "git could not run"
  so future automation can distinguish "git missing" from "forbidden
  paths detected" (`1`) without parsing stdout.
- **No scripts/ subdirectory creation.** The PLAN does not authorize
  the creation of a new subdirectory under `scripts/`. The script
  lives directly at `scripts/check_forbidden_paths.py`.
- **Reviewer reproducibility.** The PLAN's temp-repo smoke test is
  fully reproducible by the Reviewer. The executor recorded the
  exact commands and observed exit codes above.

## recommended_next_action

1. **Reviewer** reads `scripts/check_forbidden_paths.py` and this
   report and emits
   `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/review_result.json`
   with verdict `PASS`, `PASS_WITH_CAVEAT`, or `FAIL`.
2. The Reviewer may independently rerun the PLAN-mandated temp-repo
   smoke test and/or `python3 scripts/check_forbidden_paths.py
   --self-test` to verify behavior.
3. On `PASS` or `PASS_WITH_CAVEAT` with no blocking issues,
   **HumanIntegrator** stages only:
   - `scripts/check_forbidden_paths.py`
   individually (no `git add .`). The executor report under
   `reports/` may need explicit path force-staging because the
   parent directory is gitignored; recursive add-dot staging remains
   forbidden.
4. **Commit** happens only after the human explicitly says
   `commit now`.
5. After commit, the next bounded task in the checker phase is
   TASK_041 (`TASK_041_REPORT_SCHEMA_CHECKER`). TASK_040 must not
   start TASK_041 itself.

## confirmation

- Nothing was staged (`git add` was not used in any form).
- Nothing was committed.
- No push, merge, reset, rebase, cherry-pick, auto-freeze, or
  auto-signoff was performed.
- No provider, Langflow, ci-sweeper, vendored loop-engineering, or
  git submodule was introduced.
- No local runner, automated loop, GitHub automation, or
  TASK_041 / TASK_042 work was started.
- No file under `docs/safety.md`, `docs/dev/construction_loop/`,
  `reports/TASK_031_*/`, `reports/TASK_032_*/`,
  `reports/TASK_033_*/`, or any other `scripts/` path was
  created or modified.
- The TASK_040 PLAN.md was not modified.