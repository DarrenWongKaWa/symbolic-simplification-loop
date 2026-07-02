from __future__ import annotations

from loop_engine.schemas import validate_with_schema


def _base_dossier(verification_type: str) -> dict:
    return {
        "stage_id": "sigma_abc_999_mock_stage",
        "stage_title": "Mock stage",
        "stage_type": "preparation",
        "human_summary": "Mock scientist-facing dossier for schema validation.",
        "inputs": [{"path": "input/a.wl", "role": "source"}],
        "outputs": [{"path": "output/b.wl", "role": "candidate"}],
        "scripts": [{"path": "scripts/check.wl", "role": "validation"}],
        "verification": {
            "type": verification_type,
            "identity_latex": r"\mathrm{Old}-\mathrm{New}=0",
            "identity_plaintext": "Old - New = 0",
            "expected_result": "0",
            "actual_result": "0",
            "gate": "PASS",
            "evidence_paths": [".loop/validation_summary.json"],
        },
        "claim_boundary": {
            "allowed": ["PASS as a mock stage."],
            "forbidden": ["Do not claim full tensorial sigma_abc correctness."],
            "caveats": [
                "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."
            ],
        },
        "caveats": [
            "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."
        ],
        "machine_evidence": [{"path": ".loop/review_result.json", "role": "review"}],
        "human_decision": {
            "recommended_action": "READ_ONLY_REVIEW",
            "requires_human_signoff": False,
            "signoff_file_created": False,
        },
    }


def test_scientist_review_schema_accepts_exact_zero_dossier():
    validate_with_schema(_base_dossier("exact_zero"), "scientist_review")


def test_scientist_review_schema_accepts_modulo_total_derivative_dossier():
    dossier = _base_dossier("modulo_total_derivative")
    dossier["verification"]["identity_plaintext"] = "Old - New - d_k F = 0"
    dossier["verification"]["identity_latex"] = r"\mathrm{Old}-\mathrm{New}-\partial_kF=0"
    validate_with_schema(dossier, "scientist_review")


def test_scientist_review_schema_accepts_inherited_pass_dossier():
    dossier = _base_dossier("inherited_pass")
    dossier["verification"]["identity_plaintext"] = "Inherited pass from finite-frequency projection and 1D DC pipeline."
    dossier["verification"]["identity_latex"] = r"\mathrm{DCProjectionTo1D}=\mathrm{INHERITED\_PASS}"
    dossier["verification"]["actual_result"] = "INHERITED_PASS"
    validate_with_schema(dossier, "scientist_review")

