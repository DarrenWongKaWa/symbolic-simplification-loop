# Loop Skill / Repo Integration Follow-Up Test Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the order-dependent pytest failure left by `loop_skill_repo_integration_patch`, without changing `sigma_abc` physics or advancing any symbolic stage.

**Architecture:** Keep the previous infrastructure patch. Patch only test-run isolation and, if needed, the dry-run report identity expectation. The core issue is that `tests/test_autonomous_loop_runner.py` now uses a module-level shared `TEST_RUN_ROOT = REPO_ROOT / "autonomous_runs_test"`; tests that execute the runner mutate that shared directory, so subsequent dry-runs can see already-frozen stages and return `NextStage -> none`.

**Tech Stack:** Python 3.12, pytest, existing `scripts/run_autonomous_loop.py` CLI, existing `LOOP_RUN_ROOT` environment override.

---

## Current Evidence

Codex re-ran verification after Claude's patch.

Full suite currently fails:

```text
python3 -m pytest -q
1 failed, 264 passed, 1 warning
```

Failing test:

```text
tests/test_autonomous_loop_runner.py::test_sigma_abc_dry_run_reports_profile_driven_next_stage
```

Order-dependent reproduction:

```bash
python3 -m pytest -q \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008 \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_dry_run_reports_profile_driven_next_stage \
  -vv
```

Observed:

```text
first test: PASS
second test: FAIL
```

Second test output contains:

```text
Current checkpoint: sigma_abc_005_sector_ledger_xxx_collapse_regression_checkpoint_v1
NextStage -> none
Next allowed stage: none
```

Why this is not a physics failure:

- The first test freezes 006/007/008 into the shared `autonomous_runs_test/sigma_abc` run root.
- The second test runs `--dry-run --from-current-checkpoint` against the same shared run root.
- The runner therefore sees no remaining safe-pre-fusion stages and reports `NextStage -> none`.
- The old assertion expects a fresh run root where 006 is still next.

Single-test check still passes:

```bash
python3 -m pytest -q \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_dry_run_reports_profile_driven_next_stage \
  -vv
```

Observed:

```text
PASS
```

## Hard Boundaries

Do not modify `sigma_abc` physics.

Do not start:

```text
012C promotion
Stage 013
tensorial IBP
total-derivative reduction
```

Do not claim full tensorial `sigma_{\mu\alpha\beta}` correctness.

Preserve:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

Do not edit frozen checkpoints in place.

---

## File Structure

Modify:

```text
tests/test_autonomous_loop_runner.py
tests/test_loop020a_runner_path_hygiene.py   # only if it shares the same static run root problem
tests/test_loop_skill_repo_integration_patch.py # only if needed for helper consistency
docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_PATCH_REPORT.md
```

Create:

```text
docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_REPORT.md
```

Do not modify symbolic outputs, `sigma_abc/`, frozen checkpoint payloads, or physics ledgers.

---

### Task 1: Add a Regression Test For Order-Independent Runner Tests

**Files:**

- Modify: `tests/test_autonomous_loop_runner.py`

- [ ] **Step 1: Add a regression test that reproduces the order dependency in-process**

Add this test near the two existing sigma_abc safe-prefusion tests:

```python
def test_safe_prefusion_run_does_not_pollute_dry_run_expectations(tmp_path: Path):
    first_root = tmp_path / "first_run"
    second_root = tmp_path / "second_run"

    first = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_safe_pre_fusion",
        "--from-current-checkpoint",
        "--clean",
        run_root=first_root,
    )
    assert first.returncode == 0, first.stderr[-1000:]

    second = run_runner(
        "--project",
        "sigma_abc",
        "--profile",
        "sigma_abc_safe_pre_fusion",
        "--dry-run",
        "--from-current-checkpoint",
        run_root=second_root,
    )
    assert second.returncode == 0, second.stderr[-1000:]
    assert "Next allowed stage: sigma_abc_006_tensorial_sector_architecture_review" in second.stdout
```

This test assumes Task 2 changes `run_runner` to accept `run_root`.

- [ ] **Step 2: Run the new regression test before implementation**

Run:

```bash
python3 -m pytest -q tests/test_autonomous_loop_runner.py::test_safe_prefusion_run_does_not_pollute_dry_run_expectations -vv
```

Expected before Task 2:

```text
FAIL because run_runner does not accept run_root
```

---

### Task 2: Make `run_runner` Use Per-Test Run Roots By Default

**Files:**

- Modify: `tests/test_autonomous_loop_runner.py`

- [ ] **Step 1: Replace the static shared helper with an explicit run-root helper**

Current helper is roughly:

```python
TEST_RUN_ROOT = REPO_ROOT / "autonomous_runs_test"


def run_runner(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["LOOP_RUN_ROOT"] = str(TEST_RUN_ROOT)
    return subprocess.run(...)
```

Replace with:

```python
DEFAULT_TEST_RUN_ROOT = REPO_ROOT / "autonomous_runs_test"


def run_runner(
    *args: str,
    check: bool = True,
    run_root: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Spawn the autonomous runner in an isolated run root.

    Pass the same ``run_root`` explicitly for tests that need multiple runner
    invocations to share checkpoint state. If omitted, use a fresh temporary
    directory so tests do not pollute each other.
    """
    import tempfile

    env = os.environ.copy()
    selected_root = run_root or Path(tempfile.mkdtemp(prefix="loop-runner-test-"))
    env["LOOP_RUN_ROOT"] = str(selected_root)
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=REPO_ROOT,
        check=check,
        text=True,
        capture_output=True,
        env=env,
    )
```

- [ ] **Step 2: Update tests that intentionally inspect runner output paths**

For tests that currently read from `TEST_RUN_ROOT / project`, create a local root and pass it to `run_runner`.

Example conversion:

```python
def test_autonomous_runner_mock_two_stages_freezes_without_long_prompt(tmp_path: Path):
    run_root = tmp_path / "runs"
    result = run_runner("--project", "mock", "--profile", "test_safe_loop", "--clean", run_root=run_root)
    assert result.returncode == 0

    root = run_root / "mock"
    report = root / "AUTONOMOUS_LOOP_RUN_REPORT.md"
    assert report.exists()
```

Apply this pattern to all tests in `tests/test_autonomous_loop_runner.py` that inspect generated files.

Tests that need sequential state, such as `test_from_current_checkpoint_also_skips_existing_frozen_stages`, must reuse the same `run_root` variable across both calls:

```python
run_root = tmp_path / "runs"
result = run_runner(..., run_root=run_root)
result = run_runner(..., run_root=run_root)
```

- [ ] **Step 3: Remove or demote `TEST_RUN_ROOT`**

If no test needs the module-level static path, remove `TEST_RUN_ROOT` entirely.

If a few tests still need a predictable path, rename it to:

```python
LEGACY_TEST_RUN_ROOT = REPO_ROOT / "autonomous_runs_test"
```

and use it only in the explicit test for `LOOP_RUN_ROOT` behavior.

---

### Task 3: Patch Any Other Static Test Run Roots

**Files:**

- Modify: `tests/test_loop020a_runner_path_hygiene.py`
- Modify: `tests/test_loop_skill_repo_integration_patch.py` only if needed

- [ ] **Step 1: Inspect static `autonomous_runs_test` usage**

Run:

```bash
rg "autonomous_runs_test|TEST_RUN_ROOT|LOOP_RUN_ROOT" tests
```

- [ ] **Step 2: Ensure tests are isolated by default**

For each helper that sets `LOOP_RUN_ROOT` to a static repo path, either:

1. Add a `run_root: Path | None = None` parameter and use a temporary directory by default; or
2. Use `tmp_path` fixture in each test and pass the path explicitly.

Do not allow one test's runner output to determine another test's expected `NextStage`.

- [ ] **Step 3: Keep `.gitignore` entry**

Keep:

```text
autonomous_runs_test/
```

This is still useful for manual smoke tests, but pytest should not depend on a shared persistent directory.

---

### Task 4: Verify The Exact Failure Is Gone

**Files:** none

- [ ] **Step 1: Run the order-dependent reproducer**

Run:

```bash
python3 -m pytest -q \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008 \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_dry_run_reports_profile_driven_next_stage \
  -vv
```

Expected:

```text
2 passed
```

- [ ] **Step 2: Run the new regression test**

Run:

```bash
python3 -m pytest -q tests/test_autonomous_loop_runner.py::test_safe_prefusion_run_does_not_pollute_dry_run_expectations -vv
```

Expected:

```text
PASS
```

---

### Task 5: Run Full Verification

**Files:** none

- [ ] **Step 1: Run full pytest**

Run:

```bash
python3 -m pytest -q
```

Expected:

```text
265 passed, 0 failed
```

The exact pass count may increase if a new regression test was added. If so, record the new count in the report.

- [ ] **Step 2: Run compileall**

Run:

```bash
python3 -m compileall loop_engine scripts tests
```

Expected:

```text
No errors
```

- [ ] **Step 3: Confirm no forbidden artifacts**

Run:

```bash
find autonomous_runs sigma_abc -maxdepth 5 -type d \
  \( -iname '*012c*promotion*' -o -iname '*013*' -o -iname '*ibp*' -o -iname '*total_derivative*' \) \
  | sort
```

Expected:

```text
No newly created forbidden artifacts from this follow-up patch.
```

Do not delete historical artifacts unless explicitly instructed.

---

### Task 6: Update Patch Report With Follow-Up Finding

**Files:**

- Modify: `docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_PATCH_REPORT.md`
- Create: `docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_REPORT.md`

- [ ] **Step 1: Add a short caveat/update to the original patch report**

Append:

```markdown
## Follow-up Test Isolation Patch

A post-patch Codex audit found that the first integration patch still had an
order-dependent pytest failure: the static `autonomous_runs_test/` run root let
one safe-prefusion test freeze 006/007/008 before the dry-run test executed.
The follow-up patch changes runner tests to use per-test run roots by default.
See `docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_REPORT.md`.
```

- [ ] **Step 2: Write the follow-up report**

Create `docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_REPORT.md`:

```markdown
# Loop Skill / Repo Integration Follow-Up Test Isolation Report

## Verdict

PASS as test-isolation follow-up for `loop_skill_repo_integration_patch`.

## Issue

The previous patch routed pytest runner subprocesses to a shared
`autonomous_runs_test/` root. This fixed live-root pollution but allowed test
order pollution. If `test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`
ran before `test_sigma_abc_dry_run_reports_profile_driven_next_stage`, the
second test saw all allowed safe-prefusion stages already completed and reported
`NextStage -> none`.

## Fix

Runner tests now use per-test run roots by default. Tests that intentionally
need persistent state pass the same `run_root` explicitly.

## Verification

```text
python3 -m pytest -q
<paste final result>
```

```text
python3 -m compileall loop_engine scripts tests
<paste final result>
```

## Boundaries

- sigma_abc physics unchanged.
- 012C promotion not started.
- Stage 013 not started.
- Tensorial IBP not started.
- Total-derivative reduction not introduced.
- Full tensorial correctness not claimed.
- DCProjectionTo1D inherited-pass caveat preserved.
```

---

## Acceptance Criteria

This follow-up patch is complete only if:

```text
python3 -m pytest -q
PASS

python3 -m compileall loop_engine scripts tests
PASS
```

And:

```text
The two-test reproducer passes.
The new order-isolation regression test passes.
Runner tests no longer share a persistent run root unless explicitly requested.
No sigma_abc physics was modified.
No 012C / Stage 013 / tensorial IBP / total derivative artifacts were generated.
```

## Suggested Branch Name

```text
loop_skill_repo_integration_followup_test_isolation
```
