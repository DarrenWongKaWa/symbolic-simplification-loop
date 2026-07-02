from __future__ import annotations

import re
from typing import Any


def _retry_after_from_text(text: str) -> str | None:
    patterns = [
        r"RetryAfter\s*(?:->|:)\s*([^\n.]+(?:\.[^\n.]+)?)",
        r"try again at\s+([^\n.]+(?:\.[^\n.]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().rstrip(".")
    return None


def classify_agent_runtime_failure(summary: dict[str, Any], stdout: str = "", stderr: str = "") -> dict[str, Any]:
    text = f"{stdout}\n{stderr}\n{summary}".strip()
    lowered = text.lower()
    runtime_status = str(summary.get("runtime_status", "")).upper()
    if "usage limit" in lowered or "quota" in lowered or "try again at" in lowered:
        retry_after = _retry_after_from_text(text)
        issue = "AGENT_QUOTA_LIMIT / AGENT_RUNTIME_QUOTA_EXHAUSTED: agent runtime quota or usage limit blocked invocation."
        if retry_after:
            issue += f" RetryAfter -> {retry_after}"
        return {
            "kind": "AGENT_RUNTIME_QUOTA_EXHAUSTED",
            "issue": issue,
            "patch_required": False,
            "retry_after": retry_after,
        }
    if runtime_status == "AGENT_TIMEOUT" or "timeout_expired" in lowered or "timed out" in lowered or "exit_code': 'timeout'" in lowered or '"exit_code": "timeout"' in lowered:
        return {
            "kind": "AGENT_TIMEOUT",
            "issue": "AGENT_TIMEOUT: real agent invocation timed out before producing valid freeze evidence.",
            "patch_required": False,
            "retry_after": None,
        }
    if runtime_status == "AGENT_NO_OUTPUT":
        return {
            "kind": "AGENT_NO_OUTPUT",
            "issue": "AGENT_NO_OUTPUT: real agent invocation completed without a structured reviewer output.",
            "patch_required": False,
            "retry_after": None,
        }
    if runtime_status == "AGENT_SCHEMA_FAIL":
        return {
            "kind": "AGENT_SCHEMA_FAIL",
            "issue": "AGENT_SCHEMA_FAIL: real agent output failed schema validation.",
            "patch_required": False,
            "retry_after": None,
        }
    return {
        "kind": "AGENT_RUNTIME_FAILURE",
        "issue": f"Invalid real agent invocation evidence: {summary}",
        "patch_required": True,
        "retry_after": None,
    }
