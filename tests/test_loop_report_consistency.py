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
