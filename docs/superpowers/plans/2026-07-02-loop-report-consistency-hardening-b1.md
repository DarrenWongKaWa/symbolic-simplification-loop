# Loop Report Consistency Hardening B1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the minimal report-consistency audit script and tests.

**Architecture:** One script plus one test file. Do not update broad docs in this B1 patch.

**Tech Stack:** Python 3.12, pytest.

---

## Hard Boundaries

Do not modify `sigma_abc` physics. Do not start 012C, Stage 013, tensorial IBP, or total-derivative reduction. Preserve `DCProjectionTo1D -> INHERITED_PASS`.

---

## Files

Create:

```text
scripts/audit_loop_report_consistency.py
tests/test_loop_report_consistency.py
```

Do not modify other files in B1.

---

### Task 1: Create `scripts/audit_loop_report_consistency.py`

Create the file exactly:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

STRICT_PASS = {"PASS"}
CAVEAT_VERDICTS = {"PASS_WITH_CAVEAT", "PASS_WITH_FOLLOWUP_REQUIRED", "BLOCKED_BY_RUNTIME_LIMIT"}
FAIL_VERDICTS = {"FAIL", "NEEDS_PATCH", "HARD_STOP"}


def extract_verdict(text: str) -> str:
    match = re.search(
        r"\b(PASS_WITH_FOLLOWUP_REQUIRED|PASS_WITH_CAVEAT|BLOCKED_BY_RUNTIME_LIMIT|NEEDS_PATCH|HARD_STOP|PASS|FAIL)\b",
        text,
    )
    return match.group(1) if match else "MISSING"


def load_evidence(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def failed_evidence(evidence: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    for name, entry in evidence.items():
        if isinstance(entry, dict):
            status = str(entry.get("status", "")).upper()
            if status not in {"PASS", "OK"}:
                failed.append(name)
    return failed


def audit(report_path: Path, evidence_path: Path) -> dict[str, Any]:
    text = report_path.read_text(encoding="utf-8")
    evidence = load_evidence(evidence_path)
    verdict = extract_verdict(text)
    failures = failed_evidence(evidence)
    issues: list[str] = []

    if verdict == "MISSING":
        issues.append("report verdict missing")
    if verdict in STRICT_PASS and failures:
        issues.append(f"report claims PASS but evidence failed: {', '.join(failures)}")
    if verdict in STRICT_PASS and "python3 -m pytest -q" not in text:
        issues.append("report claims PASS but pytest command evidence is missing")
    if verdict in STRICT_PASS and "python3 -m compileall" not in text:
        issues.append("report claims PASS but compileall command evidence is missing")

    if issues:
        gate = "FAIL"
    elif verdict in CAVEAT_VERDICTS:
        gate = "PASS_WITH_CAVEAT"
    elif verdict in STRICT_PASS:
        gate = "PASS"
    elif verdict in FAIL_VERDICTS:
        gate = "FAIL"
    else:
        gate = "FAIL"
        issues.append(f"unknown verdict: {verdict}")

    return {
        "report": str(report_path),
        "evidence": str(evidence_path),
        "verdict": verdict,
        "failed_evidence": failures,
        "issues": issues,
        "overall_gate": gate,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    result = audit(Path(args.report), Path(args.evidence))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["overall_gate"] in {"PASS", "PASS_WITH_CAVEAT"} else 1


if __name__ == "__main__":
    sys.exit(main())
```

---

### Task 2: Create `tests/test_loop_report_consistency.py`

Create the file exactly:

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "audit_loop_report_consistency.py"


def run_audit(report: Path, evidence: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--report", str(report), "--evidence", str(evidence)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_report_audit_passes_when_claim_matches_evidence(tmp_path: Path):
    report = tmp_path / "report.md"
    report.write_text(
        """
# Patch Report

## Verdict

PASS

## Verification

python3 -m pytest -q
266 passed, 1 warning

python3 -m compileall loop_engine scripts tests
No errors
""",
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "pytest": {"status": "PASS", "summary": "266 passed, 1 warning"},
                "compileall": {"status": "PASS", "summary": "No errors"},
            }
        ),
        encoding="utf-8",
    )

    result = run_audit(report, evidence)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["overall_gate"] == "PASS"


def test_report_audit_fails_when_report_claims_pass_but_evidence_failed(tmp_path: Path):
    report = tmp_path / "report.md"
    report.write_text(
        """
# Patch Report

## Verdict

PASS

## Verification

python3 -m pytest -q
265 passed, 0 failed

python3 -m compileall loop_engine scripts tests
No errors
""",
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "pytest": {"status": "FAIL", "summary": "1 failed, 264 passed, 1 warning"},
                "compileall": {"status": "PASS", "summary": "No errors"},
            }
        ),
        encoding="utf-8",
    )

    result = run_audit(report, evidence)
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["overall_gate"] == "FAIL"
    assert any("claims PASS" in issue for issue in payload["issues"])


def test_report_audit_allows_followup_verdict_when_evidence_failed(tmp_path: Path):
    report = tmp_path / "report.md"
    report.write_text(
        """
# Patch Report

## Verdict

PASS_WITH_FOLLOWUP_REQUIRED

## Verification

python3 -m pytest -q
1 failed, 264 passed, 1 warning
""",
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "pytest": {"status": "FAIL", "summary": "1 failed, 264 passed, 1 warning"},
                "compileall": {"status": "PASS", "summary": "No errors"},
            }
        ),
        encoding="utf-8",
    )

    result = run_audit(report, evidence)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["overall_gate"] == "PASS_WITH_CAVEAT"
```

---

### Task 3: Verify B1

Run:

```bash
python3 -m pytest -q tests/test_loop_report_consistency.py -vv
python3 -m compileall scripts tests
```

Expected:

```text
3 passed
compileall no errors
```

Stop after B1. Do not run full pytest in Claude. Codex will run full pytest independently.
