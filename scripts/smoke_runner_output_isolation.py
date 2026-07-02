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
