from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import read_json, write_json, write_text
from .schemas import validate_with_schema


def _checks(stage: Path) -> set[str]:
    validation_path = stage / ".loop" / "validation_summary.json"
    if not validation_path.exists():
        return set()
    validation = read_json(validation_path)
    names = {str(check.get("name")) for check in validation.get("checks", []) if check.get("name")}
    names.update(str(item.get("name")) for item in validation.get("protected_regressions", []) if item.get("name"))
    names.update(key for key in validation.keys() if key[0:1].isupper())
    return names


def _wanted_checks(identity: dict[str, Any]) -> list[str]:
    check = identity.get("check")
    if check is None:
        return []
    if isinstance(check, list):
        return [str(item) for item in check]
    return [str(check)]


def audit_identity_traceability(stage: Path, *, identities: dict[str, Any]) -> dict[str, Any]:
    available = _checks(stage)
    items: list[dict[str, Any]] = []
    failures: list[str] = []
    for identity in identities.get("identities", []):
        wanted = _wanted_checks(identity)
        linked = [name for name in wanted if name in available]
        role = identity.get("role")
        blocking = bool(identity.get("blocking", role not in {"caveat", "informational"}))
        if role == "caveat":
            status = "INFORMATIONAL_ONLY"
        elif linked:
            status = "LINKED"
        elif wanted and not blocking:
            status = "REGISTERED"
        else:
            status = "MISSING_CHECK"
        if blocking and status == "MISSING_CHECK":
            failures.append(str(identity.get("label")))
        items.append(
            {
                "identity_label": str(identity.get("label")),
                "latex": str(identity.get("latex")),
                "linked_checks": linked,
                "trace_status": status,
                "blocking_if_unlinked": blocking,
                "requested_checks": wanted,
            }
        )
    payload = {
        "stage_id": stage.name,
        "identity_traceability_gate": "FAIL" if failures else "PASS",
        "items": items,
        "blocking_failures": failures,
    }
    validate_with_schema(payload, "identity_traceability")
    return payload


def render_traceability_md(trace: dict[str, Any]) -> str:
    lines = [
        "# Identity Traceability",
        "",
        f"IdentityTraceabilityGate -> {trace.get('identity_traceability_gate')}",
        "",
        "| Identity | Status | Linked checks | Blocking |",
        "|---|---|---|---|",
    ]
    for item in trace.get("items", []):
        lines.append(
            f"| {item.get('identity_label')} | {item.get('trace_status')} | {', '.join(item.get('linked_checks', [])) or 'none'} | {item.get('blocking_if_unlinked')} |"
        )
    return "\n".join(lines) + "\n"


def write_identity_traceability(stage: Path, *, identities: dict[str, Any]) -> Path:
    payload = audit_identity_traceability(stage, identities=identities)
    path = stage / ".loop" / "identity_traceability.json"
    write_json(path, payload)
    write_text(stage / "reports" / "identity_traceability.md", render_traceability_md(payload))
    return path
