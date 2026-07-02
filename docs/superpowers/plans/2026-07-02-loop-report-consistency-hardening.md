# Loop Report Consistency Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent execution reports from claiming PASS when independent benchmark gates fail or were not actually run.

**Architecture:** Add a lightweight report-audit layer for loop infrastructure patches. The audit is not a physics verifier; it checks report identity, presence of command evidence, consistency between claimed results and machine-readable benchmark evidence, and correct use of caveat verdicts. This should be usable by Codex after Claude Code execution and by future autonomous loops.

**Tech Stack:** Python 3.12, pytest, JSON/Markdown reports, existing `docs/devlog/loop_engine`, existing `scripts` directory.

---

## Context

During `loop_skill_repo_integration_patch`, Claude's report claimed:

```text
pytest -> 265 passed, 0 failed
```

Codex independent verification found:

```text
python3 -m pytest -q -> 1 failed, 264 passed, 1 warning
```

A follow-up patch fixed the order-dependent test failure. The process gap remains: the repo should provide a small, deterministic way to audit report claims against recorded benchmark evidence.

## Hard Boundaries

Do not modify `sigma_abc` physics.

Do not start:

```text
012C promotion
Stage 013
tensorial IBP
total-derivative reduction
```

Do not claim full tensorial correctness.

Preserve:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

---

## File Structure

Create:

```text
scripts/audit_loop_report_consistency.py
tests/test_loop_report_consistency.py
docs/devlog/loop_engine/LOOP_REPORT_CONSISTENCY_HARDENING_REPORT.md
```

Modify only if useful:

```text
docs/user_guide/QUICKSTART.md
README.md
```

Do not modify symbolic outputs, `sigma_abc/`, or frozen checkpoint payloads.

---

### Task 1: Write Failing Tests For Report Consistency Audit

**Files:**

- Create: `tests/test_loop_report_consistency.py`

- [ ] **Step 1: Create tests for matching PASS evidence**

Add:

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
    report.write_text("""
# Patch Report

## Verdict

PASS

## Verification

python3 -m pytest -q
266 passed, 1 warning

python3 -m compileall loop_engine scripts tests
No errors
""", encoding="utf-8")
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({
        "pytest": {"status": "PASS", "summary": "266 passed, 1 warning"},
        "compileall": {"status": "PASS", "summary": "No errors"},
    }), encoding="utf-8")

    result = run_audit(report, evidence)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["overall_gate"] == "PASS"
```

- [ ] **Step 2: Create tests for overclaiming PASS with failed evidence**

Add:

```python
def test_report_audit_fails_when_report_claims_pass_but_evidence_failed(tmp_path: Path):
    report = tmp_path / "report.md"
    report.write_text("""
# Patch Report

## Verdict

PASS

## Verification

python3 -m pytest -q
265 passed, 0 failed
""", encoding="utf-8")
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({
        "pytest": {"status": "FAIL", "summary": "1 failed, 264 passed, 1 warning"},
        "compileall": {"status": "PASS", "summary": "No errors"},
    }), encoding="utf-8")

    result = run_audit(report, evidence)
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["overall_gate"] == "FAIL"
    assert any("claims PASS" in issue for issue in payload["issues"])
```

- [ ] **Step 3: Create tests for caveat verdicts**

Add:

```python
def test_report_audit_allows_followup_verdict_when_evidence_failed(tmp_path: Path):
    report = tmp_path / "report.md"
    report.write_text("""
# Patch Report

## Verdict

PASS_WITH_FOLLOWUP_REQUIRED

## Verification

python3 -m pytest -q
1 failed, 264 passed, 1 warning
""", encoding="utf-8")
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({
        "pytest": {"status": "FAIL", "summary": "1 failed, 264 passed, 1 warning"},
        "compileall": {"status": "PASS", "summary": "No errors"},
    }), encoding="utf-8")

    result = run_audit(report, evidence)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["overall_gate"] == "PASS_WITH_CAVEAT"
```

- [ ] **Step 4: Run tests and verify they fail before implementation**

Run:

```bash
python3 -m pytest -q tests/test_loop_report_consistency.py -vv
```

Expected:

```text
FAIL because scripts/audit_loop_report_consistency.py does not exist
```

---

### Task 2: Implement `audit_loop_report_consistency.py`

**Files:**

- Create: `scripts/audit_loop_report_consistency.py`

- [ ] **Step 1: Add the script**

Create:

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
    patterns = [
        r"\b(PASS_WITH_FOLLOWUP_REQUIRED|PASS_WITH_CAVEAT|BLOCKED_BY_RUNTIME_LIMIT|NEEDS_PATCH|HARD_STOP|PASS|FAIL)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return "MISSING"


def load_evidence(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def failed_evidence(evidence: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    for name, entry in evidence.items():
        if isinstance(entry, dict) and str(entry.get("status", "")).upper() not in {"PASS", "OK"}:
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

- [ ] **Step 2: Run targeted tests**

Run:

```bash
python3 -m pytest -q tests/test_loop_report_consistency.py -vv
```

Expected:

```text
PASS
```

---

### Task 3: Add A Real Evidence Snapshot For The Current Follow-Up Patch

**Files:**

- Create: `docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_EVIDENCE.json`

- [ ] **Step 1: Create evidence JSON**

Create:

```json
{
  "pytest": {
    "status": "PASS",
    "summary": "266 passed, 1 warning"
  },
  "compileall": {
    "status": "PASS",
    "summary": "No errors"
  },
  "two_test_reproducer": {
    "status": "PASS",
    "summary": "2 passed, 1 warning"
  }
}
```

- [ ] **Step 2: Run report audit against current follow-up report**

Run:

```bash
python3 scripts/audit_loop_report_consistency.py \
  --report docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_REPORT.md \
  --evidence docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_EVIDENCE.json
```

Expected:

```text
"overall_gate": "PASS"
```

---

### Task 4: Document The Benchmark Protocol

**Files:**

- Modify: `docs/superpowers/plans/2026-07-02-claude-execution-codex-review-loop-protocol.md`
- Modify: `docs/user_guide/QUICKSTART.md` only if useful

- [ ] **Step 1: Add report audit command to protocol**

Append to the protocol's Standard Benchmark Gates section:

```markdown
### Report Consistency Gate

When a Claude execution report claims PASS, create or locate a JSON evidence
file and run:

```bash
python3 scripts/audit_loop_report_consistency.py \
  --report <report.md> \
  --evidence <evidence.json>
```

A strict PASS report must not coexist with failed evidence. If evidence failed
but the report honestly says `PASS_WITH_FOLLOWUP_REQUIRED`, the audit may return
`PASS_WITH_CAVEAT`.
```

---

### Task 5: Final Verification And Report

**Files:**

- Create: `docs/devlog/loop_engine/LOOP_REPORT_CONSISTENCY_HARDENING_REPORT.md`

- [ ] **Step 1: Run full pytest**

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
No errors
```

- [ ] **Step 3: Write report**

Create `docs/devlog/loop_engine/LOOP_REPORT_CONSISTENCY_HARDENING_REPORT.md` with:

```markdown
# Loop Report Consistency Hardening Report

## Verdict

PASS as report-consistency benchmark hardening.

## What Changed

- Added `scripts/audit_loop_report_consistency.py`.
- Added tests for strict PASS, failed evidence, and follow-up caveat verdicts.
- Added evidence JSON for the current follow-up patch.
- Documented the report consistency gate in the Claude/Codex loop protocol.

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
- DCProjectionTo1D inherited-pass caveat preserved.
```

---

## Acceptance Criteria

This patch is complete only if:

```text
python3 -m pytest -q -> PASS
python3 -m compileall loop_engine scripts tests -> PASS
report audit catches PASS overclaim with failed evidence
report audit permits honest PASS_WITH_FOLLOWUP_REQUIRED with failed evidence
current follow-up report audits as PASS
no sigma_abc physics modified
no 012C / Stage 013 / tensorial IBP / total derivative artifacts generated
```

## Suggested Branch Name

```text
loop_report_consistency_hardening
```
