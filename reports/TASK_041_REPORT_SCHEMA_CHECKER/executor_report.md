# Executor Report — TASK_041_REPORT_SCHEMA_CHECKER

## task_id

TASK_041_REPORT_SCHEMA_CHECKER

## current_pwd_branch_head

- pwd: `/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-loop-audit-report`
- branch: `task-030-loop-meta-loop-audit`
- HEAD: `35870f5 TASK_040 add forbidden path smoke checker`

## plan_md_path_read

`reports/TASK_041_REPORT_SCHEMA_CHECKER/PLAN.md`

(Note: `reports/` is gitignored at `.gitignore:23`, so PLAN.md does
not appear in `git status --short`. The file exists at the explicit
path above and was read in full before any work began.)

## changed_files

- `scripts/check_task_report_schema.py` (created; chmod +x)
- `reports/TASK_041_REPORT_SCHEMA_CHECKER/executor_report.md`
  (this file, created; untracked because `reports/` is gitignored)

No other files were modified. `scripts/check_forbidden_paths.py`
was not touched. No other `scripts/` path was created or modified.
No TASK_031 / TASK_032 / TASK_033 / TASK_040 artifacts were touched.
No TASK_042 / TASK_043 work was started. The TASK_041 PLAN.md was
not modified.

## summary_of_changes

Added a read-only, stdlib-only Python 3 CLI at
`scripts/check_task_report_schema.py` that validates the expected
shape of a single `reports/TASK_XXX_<NAME>/` directory. The script:

1. Accepts the report directory path as a positional argument.
2. Verifies that the four required artifacts exist:

   ```text
   PLAN.md
   executor_report.md
   review_result.json
   landing_report.md
   ```

3. Recognizes the three optional artifacts without requiring them:

   ```text
   audit_evidence.md
   final_summary.md
   build.log
   ```

4. Inspects optional `human_review/` and `supplement/` subdirectories
   **only when they exist** and reports the recognized files present
   inside. They are never required for ordinary tasks.

5. Parses `review_result.json` as JSON and verifies the
   `verdict` field is one of `PASS`, `PASS_WITH_CAVEAT`, or `FAIL`.

6. Prints a reviewer-readable summary (counts, per-file `[OK] /
   [MISS]` markers, subdirectory findings, review_result problems,
   final `RESULT: PASS|FAIL`).

7. Exits:

   - `0` when all required files are present, no structural issue
     detected, and `review_result.json` carries a valid verdict.
   - `1` when any required file is missing or `review_result.json`
     is missing/invalid.
   - `2` when the target path is missing or is not a directory.

The script also supports `--self-test`, which runs an internal
behavior smoke test in a temp directory and asserts:

- full directory → 0
- directory with only `PLAN.md` → 1 (lists missing required files)
- directory with full required files plus `human_review/engineering_audit.pdf`
  → 0, with the audit file surfaced
- full required files with `verdict: MAYBE` → 1 (invalid verdict)
- non-existent path → 2

The script is non-mutating by construction:

- It uses only Python standard-library modules
  (`argparse`, `json`, `shutil`, `sys`, `pathlib`, `tempfile`).
- It does not import or invoke `git`, does not call `git status`,
  `git add`, `git commit`, `git push`, `git merge`, `git reset`,
  `git rebase`, or `git cherry-pick`.
- It does not write into the worktree, does not write into the
  target report directory, and only writes into a `tempfile.mkdtemp`
  prefix inside `run_self_test()`, which is removed in `finally`.
- It performs no network I/O.

## commands_run

```bash
pwd
git branch --show-current
git status --short
git log --oneline -5

# Source-of-truth reads
sed -n '965,1020p' docs/dev/construction_loop/loop_meta_loop_repair_framework.md
sed -n '1,200p' docs/safety.md
sed -n '1,260p' docs/dev/construction_loop/reporting_convention.md
sed -n '1,120p' docs/dev/construction_loop/README.md
sed -n '1,40p' scripts/check_forbidden_paths.py
sed -n '1,30p' scripts/check_pre_run_gate.py
sed -n '1,80p' scripts/audit_loop_report_consistency.py
sed -n '1,40p' reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/PLAN.md
sed -n '1,40p' reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/landing_report.md

# Compile, chmod, --help
python3 -m py_compile scripts/check_task_report_schema.py
chmod +x scripts/check_task_report_schema.py
python3 scripts/check_task_report_schema.py --help

# Self-test
python3 scripts/check_task_report_schema.py --self-test

# Run on a full historical report directory
python3 scripts/check_task_report_schema.py reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER

# Run on the in-flight TASK_041 directory (intentionally missing
# review_result.json and landing_report.md -- those are Reviewer and
# HumanIntegrator responsibilities, not Executor)
python3 scripts/check_task_report_schema.py reports/TASK_041_REPORT_SCHEMA_CHECKER

# PLAN-mandated missing-required smoke test
tmpdir="$(mktemp -d)"
mkdir -p "$tmpdir/reports/TASK_999_SMOKE"
touch "$tmpdir/reports/TASK_999_SMOKE/PLAN.md"
python3 <repo>/scripts/check_task_report_schema.py "$tmpdir/reports/TASK_999_SMOKE" && echo "UNEXPECTED PASS" || echo "expected missing-report failure"
rm -rf "$tmpdir"

# Final scope checks
git diff --stat
git diff --check
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' | grep -v 'scripts/check_task_report_schema.py' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe except approved checker path"
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\.claude/|patterns/|\.github/|loop-constraints.md' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
test ! -f .gitmodules
find . -maxdepth 3 -type d -name 'loop-engineering*'
git diff --cached --name-only
git diff -- scripts/check_task_report_schema.py
```

No `audit_evidence.md`, `final_summary.md`, or `build.log` was
created — the executor report captures command evidence and no
parallel build/render artifact was produced.

## tests_passed

- `python3 -m py_compile scripts/check_task_report_schema.py` — pass
- `python3 scripts/check_task_report_schema.py --help` — pass
- Internal `--self-test`: pass (`self-test: OK (full=0, missing=1,
  hr=0, bad-verdict=1, missing-dir=2)`)
- Run on `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER`: pass
  (`required present : 4/4`, `RESULT: PASS`, exit 0)
- Run on `reports/TASK_041_REPORT_SCHEMA_CHECKER`: pass (`RESULT:
  FAIL`, exit 1, expected because the Reviewer / HumanIntegrator
  artifacts have not been written yet by Executor)
- PLAN-mandated temp-dir missing-required smoke test: pass
  (`RESULT: FAIL`, exit 1, message `expected missing-report failure`)
- `git diff --stat` — pass (no tracked file modified)
- `git diff --check` — pass (silent)
- Forbidden-path dirty check — `scope looks safe except approved
  checker path`
- Scaffold-path dirty check — `no scaffold merge`
- `test ! -f .gitmodules` — pass
- `find . -maxdepth 3 -type d -name 'loop-engineering*'` — empty
- `git diff --cached --name-only` — empty (nothing staged)
- `git diff -- scripts/check_task_report_schema.py` — empty
  (untracked file)

## tests_failed

None. All applicable acceptance commands passed.

## forbidden_path_check

```bash
git status --short | grep -E 'sigma_abc/|checkpoints/|human_signoff|docs/devlog/audits/|agent_bus/|loop_engine/|schemas/|scripts/' | grep -v 'scripts/check_task_report_schema.py' && echo "FORBIDDEN PATH TOUCHED" || echo "scope looks safe except approved checker path"
```

Result: `scope looks safe except approved checker path`. The only
dirty path is `scripts/check_task_report_schema.py`, which is the
explicit, scoped, narrow TASK_041 scripts exception per PLAN
§In-scope Files. The PLAN itself notes that the checker is itself a
dirty `scripts/` path while unstaged and authorizes that as the
only permitted scripts exception for this task. `scripts/check_forbidden_paths.py`
was not modified.

Scaffold-path check:

```bash
git status --short | grep -E 'LOOP.md|STATE.md|loop-budget.md|loop-run-log.md|\.claude/|patterns/|\.github/|loop-constraints.md' && echo "SCAFFOLD OR AUTOMATION PATH TOUCHED" || echo "no scaffold merge"
```

Result: `no scaffold merge`.

## scope_deviation

Empty. The executor created only files inside the `Allowed edits`
set listed in PLAN.md:

- `scripts/check_task_report_schema.py`
- `reports/TASK_041_REPORT_SCHEMA_CHECKER/executor_report.md`

No file under `docs/safety.md`, `docs/dev/construction_loop/`,
`docs/dev/construction_loop/loop_meta_loop_repair_framework.md`,
`reports/TASK_031_*/`, `reports/TASK_032_*/`,
`reports/TASK_033_*/`, `reports/TASK_040_*/`, or any other
`scripts/` path was created or modified. `scripts/check_forbidden_paths.py`
was read but not modified. No test or fixture was added — the PLAN
explicitly notes tests are out of scope unless a future human-approved
plan expands the task. No local runner, GitHub automation,
ci-sweeper, provider integration, scaffold import, or TASK_042 /
TASK_043 work was started.

## unresolved_issues

- **Self-exclusion not needed.** Unlike TASK_040, the
  `scripts/` directory is not in the report-shape denylist this
  checker enforces, so the checker does not self-exclude. The
  forbidden-path dirty check is still `scope looks safe except
  approved checker path` because the global policy treats `scripts/`
  as forbidden, and the TASK_041 plan authorizes exactly
  `scripts/check_task_report_schema.py`.
- **TASK_041 directory currently fails the schema check by design.**
  The in-flight `reports/TASK_041_REPORT_SCHEMA_CHECKER/` directory
  contains only `PLAN.md` and (now) `executor_report.md`; it is
  expected to fail the schema check until Reviewer writes
  `review_result.json` and HumanIntegrator writes `landing_report.md`.
  The `RESULT: FAIL` produced by running the checker on its own
  report directory is therefore an artifact of the workflow sequence
  (Planner → Executor → Reviewer → HumanIntegrator), not a defect in
  the checker.
- **Human-readable output validation is presence-only.** The
  checker inspects `human_review/` and `supplement/` only when they
  exist and reports which recognized files are present. It does not
  validate the content of engineering audit PDFs or theoretical
  derivation supplements; that is owned by the audit / supplement
  task families per `reporting_convention.md` and is explicitly
  out of scope here per PLAN §Goal.
- **`reports/` tree is gitignored.** The TASK_041 PLAN.md and this
  executor report do not appear in normal `git status --short`.
  Matches the precedent set by TASK_030, TASK_031, TASK_032,
  TASK_033, and TASK_040. HumanIntegrator may need explicit path
  force-staging for the executor report; recursive add-dot staging
  remains forbidden.
- **Optional verdict strings are not configurable.** The
  `review_result.json` verdict is hardcoded to the three strings
  declared in `reporting_convention.md` (`PASS`, `PASS_WITH_CAVEAT`,
  `FAIL`). If the convention later adds additional allowed verdict
  strings, this checker must be updated alongside the convention.
  Per the `Source of truth` rule in `docs/safety.md`, the convention
  wins.
- **No tests added.** Per PLAN `Assumptions` and `Stop Conditions`,
  no test framework or fixtures were introduced. Behavior validation
  is provided by the `--self-test` flag and the PLAN-mandated
  temp-dir smoke test.

## deviations_from_plan

None of substance. Three minor procedural notes:

1. The PLAN's `Acceptance Commands` lists both `python` and
   `python3` invocations interchangeably. The host system has
   `python3` on `PATH`; `python` is not guaranteed to exist. The
   executor used `python3` consistently and noted this in
   `commands_run`. The script itself uses
   `#!/usr/bin/env python3` so behavior is identical.
2. The PLAN's `--self-test` interaction with the required positional
   `report_dir` is not specified. The executor implemented
   `--self-test` as a flag that is intercepted before argparse so
   it does not require `report_dir`. This is the smallest safe
   implementation consistent with the existing TASK_040
   `--self-test` convention.
3. PLAN.md was not modified. No clerical correction was required.

## risks_and_caveats

- **Path semantics.** `report_dir` is treated as a filesystem path;
  it is not validated to be inside `reports/` or to match the
  canonical `reports/TASK_XXX_<NAME>/` directory naming pattern.
  Restricting to the canonical prefix would couple the checker to
  `git rev-parse --show-toplevel` semantics that the PLAN does not
  authorize. The reviewer / human integrator is responsible for
  pointing the checker at the right directory. The PLAN's
  acceptance invocation already does this correctly.
- **JSON validity vs semantic validity.** The checker validates that
  `review_result.json` parses as JSON and contains a recognized
  `verdict` string. It does not validate the rest of the schema
  (blocking_issues, caveats, recommended_next_action,
  safe_to_continue, test_results). A future bounded task may extend
  this checker if the convention becomes more structured, but
  anything beyond that scope must not be added here.
- **No network, no subprocess.** The checker is pure-stdlib. It
  does not shell out to `git`, does not read environment variables,
  and does not load remote schemas.
- **Subdirectories never required.** `human_review/` and
  `supplement/` are inspected only when present. The checker will
  not produce a `RESULT: FAIL` because those subdirectories are
  missing. This is per PLAN §11 and the explicit guidance in
  `reporting_convention.md`.
- **No scripts/ subdirectory creation.** The PLAN does not
  authorize the creation of a new subdirectory under `scripts/`.
  The script lives directly at
  `scripts/check_task_report_schema.py`.
- **Reviewer reproducibility.** The PLAN's temp-dir smoke test is
  fully reproducible by the Reviewer. The executor recorded the
  exact commands and observed exit codes above.

## recommended_next_action

1. **Reviewer** reads `scripts/check_task_report_schema.py` and this
   report and emits
   `reports/TASK_041_REPORT_SCHEMA_CHECKER/review_result.json`
   with verdict `PASS`, `PASS_WITH_CAVEAT`, or `FAIL`.
2. The Reviewer may independently rerun the PLAN-mandated temp-dir
   smoke test and/or
   `python3 scripts/check_task_report_schema.py --self-test` to
   verify behavior. The Reviewer may also run the checker against
   the historical `reports/TASK_040_FORBIDDEN_PATH_SMOKE_CHECKER/`
   directory to confirm a known-good full report directory returns
   exit 0.
3. On `PASS` or `PASS_WITH_CAVEAT` with no blocking issues,
   **HumanIntegrator** stages only:
   - `scripts/check_task_report_schema.py`
   individually (no `git add .`). The executor report under
   `reports/` may need explicit path force-staging because the
   parent directory is gitignored; recursive add-dot staging remains
   forbidden.
4. **Commit** happens only after the human explicitly says
   `commit now`.
5. After commit, the next bounded task in the checker phase is
   TASK_042 (`TASK_042_ROLE_CARD_COMPLETENESS_CHECKER`). TASK_041
   must not start TASK_042 itself.

## confirmation

- Nothing was staged (`git add` was not used in any form).
- Nothing was committed.
- No push, merge, reset, rebase, cherry-pick, auto-freeze, or
  auto-signoff was performed.
- No provider, Langflow, ci-sweeper, vendored loop-engineering, or
  git submodule was introduced.
- No local runner, automated loop, GitHub automation, or
  TASK_042 / TASK_043 work was started.
- No file under `docs/safety.md`, `docs/dev/construction_loop/`,
  `reports/TASK_031_*/`, `reports/TASK_032_*/`,
  `reports/TASK_033_*/`, `reports/TASK_040_*/`, or any other
  `scripts/` path was created or modified.
- `scripts/check_forbidden_paths.py` was read but not modified.
- The TASK_041 PLAN.md was not modified.