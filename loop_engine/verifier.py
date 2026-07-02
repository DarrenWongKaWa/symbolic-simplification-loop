from __future__ import annotations

from pathlib import Path

from .config import read_json, write_json


def load_validation_summary(stage: Path) -> dict:
    candidates = [
        stage / ".loop" / "validation_summary.json",
        stage / "validation" / "validation_summary.json",
    ]
    for path in candidates:
        if path.exists():
            return read_json(path)
    raise FileNotFoundError(f"No validation_summary.json found for stage {stage}")


def validation_passed(summary: dict) -> bool:
    return summary.get("overall_gate") == "PASS"


def run_stage_verifier(stage: Path) -> dict:
    summary = load_validation_summary(stage)
    result = {
        "stage_name": stage.name,
        "VerifierServicePassed": validation_passed(summary),
        "overall_gate": summary.get("overall_gate"),
        "checks_seen": len(summary.get("checks", [])),
        "source": ".loop/validation_summary.json"
        if (stage / ".loop" / "validation_summary.json").exists()
        else "validation/validation_summary.json",
    }
    write_json(stage / ".loop" / "verifier_service_result.json", result)
    return result


def run_verifier_agent_audit(stage: Path) -> dict:
    service_path = stage / ".loop" / "verifier_service_result.json"
    service = read_json(service_path) if service_path.exists() else run_stage_verifier(stage)
    summary = load_validation_summary(stage)
    passed = service.get("VerifierServicePassed") is True and summary.get("overall_gate") == "PASS"
    caveats = summary.get("caveats", [])
    result = {
        "stage_name": stage.name,
        "VerifierAgentAuditPassed": passed,
        "VerifierServicePassed": service.get("VerifierServicePassed") is True,
        "CannotOverrideValidationFailure": summary.get("overall_gate") != "PASS",
        "weak_validation_flags": [
            caveat for caveat in caveats if "INHERITED_PASS" in str(caveat) or "TIMEOUT" in str(caveat)
        ],
        "caveats_to_preserve": caveats,
    }
    write_json(stage / ".loop" / "verifier_agent_result.json", result)
    write_json(stage / ".loop" / "blackboard" / "verifier_agent_result.json", result)
    return result
