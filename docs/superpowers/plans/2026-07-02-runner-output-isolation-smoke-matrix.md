# Runner Output Isolation Smoke Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans.

**Goal:** Add a reusable smoke script that verifies runner side-channel reports honor `LOOP_RUN_ROOT` and do not leak to repo root by default.

**Architecture:** One Python smoke script plus one pytest wrapper. The smoke creates a temporary run root, runs a small matrix of dry-run commands, checks expected reports under the isolated root, and checks known root-level report names are absent unless explicitly requested.

**Tech Stack:** Python 3.12, pytest, existing `scripts/run_autonomous_loop.py`.

---

## Hard Boundaries

Do not modify `sigma_abc` physics. Do not start 012C, Stage 013, tensorial IBP, or total-derivative reduction. Preserve `DCProjectionTo1D -> INHERITED_PASS`.

---

## Files

Create:

```text
scripts/smoke_runner_output_isolation.py
tests/test_runner_output_isolation_smoke.py
docs/devlog/loop_engine/RUNNER_OUTPUT_ISOLATION_SMOKE_MATRIX_REPORT.md
```

Do not modify symbolic outputs or `sigma_abc/`.

---

### Task 1: Create Smoke Script

Create `scripts/smoke_runner_output_isolation.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "run_autonomous_loop.py"
ROOT_REPORTS = [
    "AUTONOMOUS_LOOP_RUN_REPORT.md",
    "PROFILE_RUNNER_DRY_RUN.md",
    "PROFILE_RUNNER_AUDIT.md",
    "SIGMA_ABC_CENTER_SECTOR_PILOT_REPORT.md",
    "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md",
    "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md",
    "SIGMA_ABC_AGENT_RUNTIME_REQUIRED.md",
]


def remove_root_reports() -> None:
    for name in ROOT_REPORTS:
        path = REPO_ROOT / name
        if path.exists():
            path.unlink()


def run_case(run_root: Path, args: list[str], expected: list[str]) -> dict[str, object]:
    env = os.environ.copy()
    env["LOOP_RUN_ROOT"] = str(run_root)
    result = subprocess.run(
        [sys.executable, str(RUNNER), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=300,
        env=env,
    )
    missing = [rel for rel in expected if not (run_root / rel).exists()]
    leaked = [name for name in ROOT_REPORTS if (REPO_ROOT / name).exists()]
    return {
        "args": args,
        "returncode": result.returncode,
        "expected": expected,
        "missing": missing,
        "root_leaks": leaked,
        "stdout_tail": result.stdout[-800:],
        "stderr_tail": result.stderr[-800:],
        "gate": "PASS" if result.returncode == 0 and not missing and not leaked else "FAIL",
    }


def main() -> int:
    remove_root_reports()
    run_root = Path(tempfile.mkdtemp(prefix="runner-output-isolation-"))
    cases = [
        {
            "args": ["--project", "mock", "--profile", "test_hypothesis_search_loop", "--dry-run"],
            "expected": ["mock/PROFILE_RUNNER_DRY_RUN.md"],
        },
        {
            "args": [
                "--project", "sigma_abc",
                "--profile", "sigma_abc_safe_pre_fusion",
                "--dry-run",
                "--from-current-checkpoint",
            ],
            "expected": ["sigma_abc/PROFILE_RUNNER_DRY_RUN.md"],
        },
    ]
    results = [run_case(run_root, case["args"], case["expected"]) for case in cases]
    gate = "PASS" if all(item["gate"] == "PASS" for item in results) else "FAIL"
    payload = {"run_root": str(run_root), "cases": results, "overall_gate": gate}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if gate == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

### Task 2: Create Pytest Wrapper

Create `tests/test_runner_output_isolation_smoke.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke_runner_output_isolation.py"


def test_runner_output_isolation_smoke_matrix_passes():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["overall_gate"] == "PASS"
    assert all(case["gate"] == "PASS" for case in payload["cases"])
```

### Task 3: Verify Script

Run:

```bash
python3 scripts/smoke_runner_output_isolation.py
python3 -m pytest -q tests/test_runner_output_isolation_smoke.py -vv
```

Expected:

```text
overall_gate -> PASS
1 passed
```

### Task 4: Write Report

Create `docs/devlog/loop_engine/RUNNER_OUTPUT_ISOLATION_SMOKE_MATRIX_REPORT.md`:

```markdown
# Runner Output Isolation Smoke Matrix Report

## Verdict

PASS as runner-output isolation smoke matrix.

## What Changed

- Added `scripts/smoke_runner_output_isolation.py`.
- Added `tests/test_runner_output_isolation_smoke.py`.

## Verification

```text
python3 scripts/smoke_runner_output_isolation.py
overall_gate -> PASS
```

```text
python3 -m pytest -q tests/test_runner_output_isolation_smoke.py -vv
1 passed
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

### Task 5: Stop

Do not run full pytest in Claude. Codex will run full pytest independently.
