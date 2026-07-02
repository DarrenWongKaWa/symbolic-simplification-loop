# Loop Skill / Repo Integration Patch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the infrastructure regressions found while integrating the installed `$symbolic-simplification-loop` skill with the updated repo, without changing `sigma_abc` physics.

**Architecture:** Keep the installed skill as the compact workflow entry point and keep this repo as the detailed implementation/source of truth. Patch only loop-infrastructure behavior: report routing, checkpoint-manifest write ordering, test run isolation, and stale repo-local skill references. No symbolic formulas, physics ledgers, IBP logic, or candidate-promotion logic should be modified.

**Tech Stack:** Python 3.12, pytest, YAML/JSON schemas, existing `loop_engine` modules and `scripts/run_autonomous_loop.py`.

---

## Context And Current Failure

The installed Codex skill lives at:

```text
/Users/wangjiahua/.codex/skills/symbolic-simplification-loop/
```

The repo under patch is:

```text
/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-simplification-loop/
```

Audit report already written:

```text
docs/devlog/audits/SKILL_REPO_INTEGRATION_AUDIT_2026-07-02.md
```

Current verification result from the audit:

```text
python3 -m compileall loop_engine scripts tests
PASS

python3 -m pytest -q
1 failed, 243 passed, 1 warning
```

Failing test:

```text
tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008
```

Failure:

```text
assert (REPO_ROOT / "autonomous_runs" / "sigma_abc" / "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md").exists()
```

Root cause:

In `scripts/run_autonomous_loop.py::write_run_report`, the `project` argument is overwritten:

```python
project = run_root.parent.name if run_root.parent.name else "sigma_abc"
```

For `run_root = autonomous_runs/sigma_abc`, this makes:

```text
project -> autonomous_runs
```

Therefore this branch never triggers:

```python
if project == "sigma_abc" and profile_name == "sigma_abc_safe_pre_fusion":
    write_sigma_abc_safe_prefusion_report(...)
```

Second infrastructure bug:

`loop_engine/checkpoint.py::freeze_checkpoint` calls `build_checkpoint_manifest(stage)` before `freeze_preconditions(...)`. `build_checkpoint_manifest` writes `.loop/checkpoint_manifest.json`, so a failed freeze can leave a manifest behind. This violates the `$symbolic-simplification-loop` rule that `checkpoint_manifest.json` should appear only when freeze is allowed.

Third repo/skill integration issue:

Repo-local `skill/reviewer.md` says role-specific review JSON should be under `.loop/reviews/`, while the README and current runner use `.loop/reviewer_results/`.

Fourth hygiene issue:

Tests and manual runs currently mutate `autonomous_runs/sigma_abc`, which is also used as a live case-study run root. This can make test commands overwrite current scientific run state.

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
scripts/run_autonomous_loop.py
loop_engine/checkpoint.py
tests/test_autonomous_loop_runner.py
tests/test_checkpoint_manifest.py
tests/test_loop020a_runner_path_hygiene.py
skill/reviewer.md
README.md
docs/user_guide/QUICKSTART.md
```

Create:

```text
tests/test_loop_skill_repo_integration_patch.py
docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_PATCH_REPORT.md
```

Optional if useful:

```text
loop_engine/run_paths.py
```

Only create `loop_engine/run_paths.py` if it meaningfully removes duplicated path logic. Otherwise keep the patch local to `scripts/run_autonomous_loop.py`.

---

### Task 1: Add Regression Tests For Safe-Prefusion Report Routing

**Files:**

- Modify: `tests/test_autonomous_loop_runner.py`
- Or create: `tests/test_loop_skill_repo_integration_patch.py`

- [ ] **Step 1: Add a failing test for the project-name bug**

Add this test to `tests/test_loop_skill_repo_integration_patch.py`:

```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_runner(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=300,
    )


def test_safe_prefusion_report_is_written_under_sigma_abc_run_root():
    result = run_runner(
        "--project", "sigma_abc",
        "--profile", "sigma_abc_safe_pre_fusion",
        "--from-current-checkpoint",
        "--clean",
    )
    assert result.returncode == 0, result.stderr[-1000:]
    report = REPO_ROOT / "autonomous_runs" / "sigma_abc" / "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "sigma_abc_006_tensorial_sector_architecture_review" in text
    assert "sigma_abc_007_pair_sector_basis_closure_pilot" in text
    assert "sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision" in text
    assert "DCProjectionTo1D -> INHERITED_PASS" in text
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python3 -m pytest -q tests/test_loop_skill_repo_integration_patch.py::test_safe_prefusion_report_is_written_under_sigma_abc_run_root
```

Expected before patch:

```text
FAIL: SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md does not exist
```

---

### Task 2: Fix Safe-Prefusion Report Routing

**Files:**

- Modify: `scripts/run_autonomous_loop.py`

- [ ] **Step 1: Patch `write_run_report` to preserve project name**

Replace the block around lines currently like:

```python
target = run_root / "AUTONOMOUS_LOOP_RUN_REPORT.md"
write_text(target, report)
project = run_root.parent.name if run_root.parent.name else "sigma_abc"
write_text(_report_path(project, "AUTONOMOUS_LOOP_RUN_REPORT.md"), report)
if project == "sigma_abc" and profile_name == "sigma_abc_safe_pre_fusion":
    write_sigma_abc_safe_prefusion_report(run_root, records, loop, profile, policy, benchmark)
return target
```

with:

```python
target = run_root / "AUTONOMOUS_LOOP_RUN_REPORT.md"
write_text(target, report)
project_name = project or run_root.name
write_text(_report_path(project_name, "AUTONOMOUS_LOOP_RUN_REPORT.md"), report)
if project_name == "sigma_abc" and profile_name == "sigma_abc_safe_pre_fusion":
    write_sigma_abc_safe_prefusion_report(
        run_root,
        records,
        loop,
        profile,
        policy,
        benchmark,
        project_name=project_name,
    )
return target
```

- [ ] **Step 2: Update `write_sigma_abc_safe_prefusion_report` signature**

Change:

```python
def write_sigma_abc_safe_prefusion_report(
    run_root: Path,
    records: list[StageRun],
    loop: dict[str, Any],
    profile: dict[str, Any],
    policy: dict[str, Any],
    benchmark: dict[str, Any],
) -> Path:
```

to:

```python
def write_sigma_abc_safe_prefusion_report(
    run_root: Path,
    records: list[StageRun],
    loop: dict[str, Any],
    profile: dict[str, Any],
    policy: dict[str, Any],
    benchmark: dict[str, Any],
    *,
    project_name: str | None = None,
) -> Path:
```

- [ ] **Step 3: Patch report write path inside `write_sigma_abc_safe_prefusion_report`**

Replace:

```python
project = run_root.parent.name if run_root.parent.name else "sigma_abc"
write_text(_report_path(project, "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md"), report)
```

with:

```python
project_name = project_name or run_root.name
write_text(_report_path(project_name, "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md"), report)
```

- [ ] **Step 4: Run targeted test**

Run:

```bash
python3 -m pytest -q tests/test_loop_skill_repo_integration_patch.py::test_safe_prefusion_report_is_written_under_sigma_abc_run_root
```

Expected:

```text
PASS
```

---

### Task 3: Prevent Checkpoint Manifest From Being Written On Failed Freeze

**Files:**

- Modify: `loop_engine/checkpoint.py`
- Modify: `tests/test_checkpoint_manifest.py`
- Or add: `tests/test_loop_skill_repo_integration_patch.py`

- [ ] **Step 1: Add a failing test for failed freeze manifest residue**

Add this to `tests/test_loop_skill_repo_integration_patch.py`:

```python
import json

from loop_engine.checkpoint import freeze_checkpoint
from loop_engine.config import write_json, write_text


def make_freeze_ready_but_unsigned_stage(tmp_path: Path) -> Path:
    stage = tmp_path / "project" / "stages" / "unsigned_stage"
    for folder in [".loop", "reports", "output", "validation"]:
        (stage / folder).mkdir(parents=True, exist_ok=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n\nGoal: unsigned freeze test.\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\nNo full tensorial claim.\n")
    write_text(stage / "review_packet.md", "# Review Packet\n")
    write_json(
        stage / ".loop" / "validation_summary.json",
        {
            "stage_name": stage.name,
            "overall_gate": "PASS",
            "identity_type": "OldMinusNewZero",
            "checks": [{"name": "exact", "expected": 0, "actual": 0, "gate": "PASS"}],
            "protected_regressions": [],
            "caveats": [],
        },
    )
    write_json(
        stage / ".loop" / "review_result.json",
        {
            "verdict": "PASS",
            "stage_name": stage.name,
            "reviewer_role": "IntegratorReview",
            "review_scope": "routine_branch",
            "mathematical_status": {
                "exact_reconstruction": True,
                "simplification_real": True,
                "regression_preserved": True,
                "overclaim_detected": False,
            },
            "blocking_issues": [],
            "nonblocking_caveats": [],
            "allowed_claims": ["PASS as unsigned test."],
            "forbidden_claims": [],
            "next_action": "FREEZE",
            "suggested_next_stage": None,
            "patch_instructions": [],
        },
    )
    write_json(stage / ".loop" / "metrics.json", {"stage_name": stage.name})
    from loop_engine.completion_matrix import write_completion_matrix

    write_completion_matrix(stage)
    return stage


def test_failed_freeze_does_not_leave_checkpoint_manifest(tmp_path: Path):
    stage = make_freeze_ready_but_unsigned_stage(tmp_path)
    try:
        freeze_checkpoint(stage, tmp_path / "checkpoints")
    except RuntimeError as exc:
        assert "human_signoff.yaml is required" in str(exc)
    else:
        raise AssertionError("freeze_checkpoint unexpectedly succeeded")
    assert not (stage / ".loop" / "checkpoint_manifest.json").exists()
```

- [ ] **Step 2: Run test and verify it fails before patch**

Run:

```bash
python3 -m pytest -q tests/test_loop_skill_repo_integration_patch.py::test_failed_freeze_does_not_leave_checkpoint_manifest
```

Expected before patch:

```text
FAIL: checkpoint_manifest.json exists
```

- [ ] **Step 3: Patch `freeze_checkpoint` to remove residue on failure**

Minimal safe patch in `loop_engine/checkpoint.py`:

```python
def freeze_checkpoint(stage: Path, checkpoints_root: Path | None = None) -> Path:
    manifest = build_checkpoint_manifest(stage)
    validation = manifest["validation_summary"]
    review = manifest["review_result"]
    missing = freeze_preconditions(stage, validation, review)
    if missing:
        manifest_path = stage / ".loop" / "checkpoint_manifest.json"
        if manifest_path.exists():
            manifest_path.unlink()
        raise RuntimeError("Cannot freeze checkpoint: " + "; ".join(missing))
    ...
```

This is intentionally minimal. A larger refactor can later split build/write, but this patch restores the invariant immediately.

- [ ] **Step 4: Run the targeted test**

Run:

```bash
python3 -m pytest -q tests/test_loop_skill_repo_integration_patch.py::test_failed_freeze_does_not_leave_checkpoint_manifest
```

Expected:

```text
PASS
```

---

### Task 4: Isolate Pytest Runner State From Live `autonomous_runs/sigma_abc`

**Files:**

- Modify: `scripts/run_autonomous_loop.py`
- Modify: `tests/test_autonomous_loop_runner.py`
- Modify or add tests in: `tests/test_loop_skill_repo_integration_patch.py`

- [ ] **Step 1: Add runner support for `LOOP_RUN_ROOT` env override**

In `scripts/run_autonomous_loop.py`, near:

```python
run_root = REPO_ROOT / "autonomous_runs" / args.project
```

replace with:

```python
run_base = Path(os.environ.get("LOOP_RUN_ROOT", REPO_ROOT / "autonomous_runs"))
run_root = run_base / args.project
```

`os` is already imported in this script.

- [ ] **Step 2: Add a failing/passing test for isolated run root**

Add to `tests/test_loop_skill_repo_integration_patch.py`:

```python
def test_runner_respects_loop_run_root_env(tmp_path: Path):
    env = dict(**__import__("os").environ)
    env["LOOP_RUN_ROOT"] = str(tmp_path / "isolated_runs")
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"),
            "--project", "mock",
            "--profile", "test_hypothesis_search_loop",
            "--clean",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env=env,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-1000:]
    assert (tmp_path / "isolated_runs" / "mock" / "AUTONOMOUS_LOOP_RUN_REPORT.md").exists()
```

- [ ] **Step 3: Update test helper in `tests/test_autonomous_loop_runner.py`**

Change `run_runner` to isolate generated run roots by default during pytest.

Add imports:

```python
import os
import tempfile
```

Then update:

```python
def run_runner(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=REPO_ROOT,
        check=check,
        text=True,
        capture_output=True,
    )
```

to:

```python
def run_runner(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if "LOOP_RUN_ROOT" not in env:
        env["LOOP_RUN_ROOT"] = tempfile.mkdtemp(prefix="loop-runner-test-")
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_autonomous_loop.py"), *args],
        cwd=REPO_ROOT,
        check=check,
        text=True,
        capture_output=True,
        env=env,
    )
```

Important: tests that inspect `REPO_ROOT / "autonomous_runs" / ...` will need to read the run root from `env["LOOP_RUN_ROOT"]`. If changing all those tests is too large, instead add a pytest fixture scoped to this file that sets `LOOP_RUN_ROOT` to `REPO_ROOT / "autonomous_runs_test"` and update expected paths to that fixture.

Recommended lower-friction option:

```python
TEST_RUN_ROOT = REPO_ROOT / "autonomous_runs_test"
```

and use that in tests. Add `autonomous_runs_test/` to `.gitignore`.

- [ ] **Step 4: Add `.gitignore` entry**

Add:

```text
autonomous_runs_test/
```

- [ ] **Step 5: Run affected tests**

Run:

```bash
python3 -m pytest -q tests/test_autonomous_loop_runner.py tests/test_loop020a_runner_path_hygiene.py tests/test_loop_skill_repo_integration_patch.py
```

Expected:

```text
PASS
```

---

### Task 5: Sync Repo-Local Skill Docs With Installed Skill

**Files:**

- Modify: `skill/reviewer.md`
- Modify: `README.md`
- Modify: `docs/user_guide/QUICKSTART.md`

- [ ] **Step 1: Patch stale reviewer directory name**

In `skill/reviewer.md`, replace:

```text
Role-specific review JSON should be saved under `.loop/reviews/` and then aggregated into `.loop/review_result.json`.
```

with:

```text
Role-specific review JSON should be saved under `.loop/reviewer_results/` and then aggregated into `.loop/review_result.json`. Older `.loop/reviews/` paths may appear in legacy notes only.
```

- [ ] **Step 2: Add installed-skill invocation note to README**

Add near the top of `README.md` after the opening description:

```markdown
## Codex Skill Entry Point

When working from Codex, invoke the installed skill first:

```text
Use $symbolic-simplification-loop.
```

The installed skill is the compact agent-facing protocol. This repository is
the detailed implementation, schemas, tests, and case-study source of truth.
```
```

- [ ] **Step 3: Add `--clean` warning to Quickstart**

In `docs/user_guide/QUICKSTART.md`, add a warning under the case-study run command:

```markdown
Warning: `--clean` deletes the selected run root. Do not use it on a live
case-study run root unless you intentionally want to start that run over.
For pytest or smoke work, use an isolated `LOOP_RUN_ROOT`.
```

- [ ] **Step 4: Run grep checks**

Run:

```bash
rg -n "\\.loop/reviews/" skill README.md docs/user_guide || true
rg -n "Use \\$symbolic-simplification-loop" README.md
rg -n "LOOP_RUN_ROOT|--clean deletes" docs/user_guide/QUICKSTART.md
```

Expected:

```text
No active `.loop/reviews/` recommendation remains.
README contains the installed skill invocation.
Quickstart contains the run-root warning.
```

---

### Task 6: Final Verification And Report

**Files:**

- Create: `docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_PATCH_REPORT.md`

- [ ] **Step 1: Run full test suite**

Run:

```bash
python3 -m pytest -q
```

Expected:

```text
PASS
```

- [ ] **Step 2: Run compileall**

Run:

```bash
python3 -m compileall loop_engine scripts tests
```

Expected:

```text
PASS
```

- [ ] **Step 3: Run targeted runner smoke**

Run with an isolated root:

```bash
LOOP_RUN_ROOT="$(mktemp -d)" python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_safe_pre_fusion \
  --from-current-checkpoint \
  --clean
```

Expected:

```text
SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md exists under the isolated run root.
Stages 006, 007, 008 are present.
No 009/010/012C/013/IBP/total derivative artifacts are created.
```

- [ ] **Step 4: Write patch report**

Create `docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_PATCH_REPORT.md` with:

```markdown
# Loop Skill / Repo Integration Patch Report

## Verdict

PASS as infrastructure integration patch.

## Changes

- Fixed safe-prefusion report routing.
- Prevented failed freeze from leaving checkpoint manifest residue.
- Added isolated runner root support via `LOOP_RUN_ROOT`.
- Synced repo-local skill docs with `.loop/reviewer_results/`.
- Added installed `$symbolic-simplification-loop` entrypoint note.

## Verification

```text
python3 -m pytest -q
<paste result>
```

```text
python3 -m compileall loop_engine scripts tests
<paste result>
```

## Boundaries

- sigma_abc physics unchanged.
- 012C promotion not started.
- Stage 013 not started.
- Tensorial IBP not started.
- Total-derivative reduction not introduced.
- Full tensorial correctness not claimed.

## Caveat

DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

- [ ] **Step 5: Confirm no forbidden artifacts**

Run:

```bash
find autonomous_runs sigma_abc -maxdepth 4 -type d \
  \( -name '*012c*promotion*' -o -name '*013*' -o -name '*ibp*' -o -name '*total_derivative*' \) \
  | sort
```

Expected:

```text
No newly created forbidden artifacts from this patch.
```

Do not delete existing historical/devlog files unless explicitly instructed.

---

## Acceptance Criteria

The patch is complete only if:

```text
python3 -m pytest -q
PASS

python3 -m compileall loop_engine scripts tests
PASS
```

And:

```text
SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md is generated in the correct run root.
Failed freeze does not leave `.loop/checkpoint_manifest.json`.
Pytest can run without mutating live `autonomous_runs/sigma_abc`.
Repo-local skill docs no longer recommend `.loop/reviews/`.
README points Codex users to `$symbolic-simplification-loop`.
No sigma_abc physics was modified.
No 012C promotion / Stage 013 / tensorial IBP / total derivative started.
```

## Suggested Branch Name

```text
loop_skill_repo_integration_patch
```

