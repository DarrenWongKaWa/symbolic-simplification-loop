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
