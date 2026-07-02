from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import yaml

from .config import read_json, utc_now, write_text
from .schemas import validate_with_schema


DECISIONS = {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT", "DO_NOT_FREEZE_PATCH", "REJECT_AND_STOP"}

PERMISSION_DEFAULTS = {
    "APPROVE_FREEZE": {
        "freeze_checkpoint": True,
        "continue_patch_loop": False,
        "promote_claim": False,
        "start_ibp": False,
        "start_total_derivative": False,
    },
    "APPROVE_FREEZE_WITH_CAVEAT": {
        "freeze_checkpoint": True,
        "continue_patch_loop": False,
        "promote_claim": False,
        "start_ibp": False,
        "start_total_derivative": False,
    },
    "DO_NOT_FREEZE_PATCH": {
        "freeze_checkpoint": False,
        "continue_patch_loop": True,
        "promote_claim": False,
        "start_ibp": False,
        "start_total_derivative": False,
    },
    "REJECT_AND_STOP": {
        "freeze_checkpoint": False,
        "continue_patch_loop": False,
        "promote_claim": False,
        "start_ibp": False,
        "start_total_derivative": False,
    },
}

BASIS = {
    "completion_matrix": "reports/completion_matrix.json",
    "validation_summary": ".loop/validation_summary.json",
    "review_result": ".loop/review_result.json",
    "claim_boundary": "CLAIM_BOUNDARY.md",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _basis_hashes(stage: Path, basis: dict[str, str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key, rel in basis.items():
        path = stage / rel
        hashes[key] = _sha256(path) if path.exists() else "MISSING"
    return hashes


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)


def _known_caveats(stage: Path) -> list[str]:
    caveats: list[str] = []
    validation_path = stage / ".loop" / "validation_summary.json"
    review_path = stage / ".loop" / "review_result.json"
    if validation_path.exists():
        validation = read_json(validation_path)
        caveats.extend(validation.get("caveats", []))
    if review_path.exists():
        review = read_json(review_path)
        caveats.extend(review.get("nonblocking_caveats", []))
    return list(dict.fromkeys(caveats))


def build_signoff_from_decision(
    stage: Path,
    decision: str,
    reason: str | None,
    signed_by: str,
    signed_via: str = "chat",
    accepted_caveats: list[str] | None = None,
) -> dict[str, Any]:
    if decision not in DECISIONS:
        raise ValueError(f"Unknown human signoff decision: {decision}")
    permission = PERMISSION_DEFAULTS[decision].copy()
    caveats = _known_caveats(stage)
    accepted_caveats = accepted_caveats if accepted_caveats is not None else (caveats if decision == "APPROVE_FREEZE_WITH_CAVEAT" else [])
    blocking_reason = [reason] if reason else []
    if decision == "DO_NOT_FREEZE_PATCH" and not blocking_reason:
        blocking_reason = ["Human requested patch before freeze."]
    if decision == "REJECT_AND_STOP" and not blocking_reason:
        blocking_reason = ["Human rejected this stage."]
    return {
        "stage_id": stage.name,
        "signed_by": signed_by,
        "signed_at": utc_now(),
        "decision": decision,
        "basis": BASIS.copy(),
        "basis_hashes": _basis_hashes(stage, BASIS),
        "human_scientific_judgment": {
            "completion_understood": True,
            "blocking_items_understood": True,
            "boundary_audit_understood": True,
            "caveats_understood": True,
        },
        "accepted_caveats": accepted_caveats,
        "blocking_reason": blocking_reason,
        "permission": permission,
        "reject_propagates_to": [],
        "supersedes": None,
        "signed_via": signed_via,
    }


def validate_signoff(signoff: dict[str, Any], profile: dict | None = None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    try:
        validate_with_schema(signoff, "human_signoff")
    except Exception as exc:  # jsonschema gives detailed errors; keep function boolean-friendly.
        reasons.append(str(exc))
        return False, reasons

    decision = signoff.get("decision")
    permission = signoff.get("permission", {})
    if decision in {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT"} and not permission.get("freeze_checkpoint"):
        reasons.append(f"{decision} requires permission.freeze_checkpoint=true")
    if decision == "APPROVE_FREEZE_WITH_CAVEAT" and not signoff.get("accepted_caveats"):
        reasons.append("APPROVE_FREEZE_WITH_CAVEAT requires non-empty accepted_caveats")
    if decision == "DO_NOT_FREEZE_PATCH":
        if permission.get("freeze_checkpoint"):
            reasons.append("DO_NOT_FREEZE_PATCH requires permission.freeze_checkpoint=false")
        if not permission.get("continue_patch_loop"):
            reasons.append("DO_NOT_FREEZE_PATCH requires permission.continue_patch_loop=true")
    if decision == "REJECT_AND_STOP" and any(permission.values()):
        reasons.append("REJECT_AND_STOP requires all permissions false")

    defaults = (profile or {}).get("default_permissions", {})
    for key, allowed in defaults.items():
        if allowed is False and permission.get(key) is True:
            reasons.append(f"permission.{key}=true exceeds profile.default_permissions")
    return not reasons, reasons


def write_signoff(stage: Path, signoff: dict[str, Any]) -> Path:
    ok, reasons = validate_signoff(signoff)
    if not ok:
        raise ValueError("Invalid human signoff: " + "; ".join(reasons))
    loop_dir = stage / ".loop"
    target = loop_dir / "human_signoff.yaml"
    history = loop_dir / "human_signoff_history"
    history.mkdir(parents=True, exist_ok=True)
    if target.exists():
        old = _read_yaml(target)
        old_decision = old.get("decision", "UNKNOWN")
        stamp = str(old.get("signed_at", utc_now())).replace(":", "").replace("-", "").replace("+", "Z")
        archive = history / f"{stamp}_{old_decision}.yaml"
        shutil.copy2(target, archive)
        signoff["supersedes"] = str(archive.relative_to(stage))
    _write_yaml(target, signoff)
    ledger = loop_dir / "human_signoff_ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"signed_at": signoff.get("signed_at"), "decision": signoff.get("decision"), "signed_by": signoff.get("signed_by"), "path": ".loop/human_signoff.yaml"}, sort_keys=True))
        handle.write("\n")
    write_text(stage / "reports" / "human_signoff_summary.md", render_human_signoff_summary(signoff))
    return target


def render_human_signoff_summary(signoff: dict[str, Any]) -> str:
    permission = signoff.get("permission", {})
    return f"""# Human Signoff

- Decision: {signoff.get('decision')}
- Signed by: {signoff.get('signed_by')}
- Signed at: {signoff.get('signed_at')}
- Permission: freeze={permission.get('freeze_checkpoint')}, patch={permission.get('continue_patch_loop')}, promote={permission.get('promote_claim')}, ibp={permission.get('start_ibp')}, total_derivative={permission.get('start_total_derivative')}
- Blocking reason: {', '.join(signoff.get('blocking_reason', [])) or 'none'}
- Accepted caveats: {', '.join(signoff.get('accepted_caveats', [])) or 'none'}
"""


def load_signoff(stage: Path) -> dict[str, Any] | None:
    path = stage / ".loop" / "human_signoff.yaml"
    return _read_yaml(path) if path.exists() else None


def validate_signoff_freshness(stage: Path, signoff: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for key, rel in (signoff.get("basis") or {}).items():
        path = stage / rel
        expected = (signoff.get("basis_hashes") or {}).get(key)
        actual = _sha256(path) if path.exists() else "MISSING"
        if expected != actual:
            reasons.append(f"{rel} hash changed: expected {expected}, actual {actual}")
    return not reasons, reasons


def check_signoff_freeze_eligible(signoff: dict[str, Any], profile: dict | None = None) -> tuple[bool, list[str]]:
    ok, reasons = validate_signoff(signoff, profile=profile)
    if not ok:
        return False, reasons
    decision = signoff.get("decision")
    if decision not in {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT"}:
        return False, [f"human_signoff.decision blocks freeze: got {decision!r}"]
    permission = signoff.get("permission", {})
    if not permission.get("freeze_checkpoint"):
        return False, ["human_signoff.permission.freeze_checkpoint must be true"]
    judgment = signoff.get("human_scientific_judgment", {})
    missing = [key for key in ["completion_understood", "boundary_audit_understood", "caveats_understood"] if not judgment.get(key)]
    if missing:
        return False, [f"human_signoff.human_scientific_judgment.{key} must be true" for key in missing]
    return True, []


def apply_reject(stage: Path, signoff: dict[str, Any]) -> None:
    if signoff.get("decision") != "REJECT_AND_STOP":
        return
    loop_dir = stage / ".loop"
    write_text(loop_dir / "STOP", "REJECT_AND_STOP\n")
    with (loop_dir / "human_signoff_ledger.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"signed_at": signoff.get("signed_at", utc_now()), "decision": "REJECT_AND_STOP", "reject_propagates_to": signoff.get("reject_propagates_to", [])}, sort_keys=True))
        handle.write("\n")


def supersedes_chain(stage: Path) -> list[dict[str, Any]]:
    current = load_signoff(stage)
    if current is None:
        return []
    chain = [current]
    seen: set[str] = set()
    pointer = current.get("supersedes")
    while pointer and pointer not in seen:
        seen.add(pointer)
        path = stage / pointer
        if not path.exists() or path.suffix not in {".yaml", ".yml"}:
            break
        previous = _read_yaml(path)
        chain.append(previous)
        pointer = previous.get("supersedes")
    return list(reversed(chain))
