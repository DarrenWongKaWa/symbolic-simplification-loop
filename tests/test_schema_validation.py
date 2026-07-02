from __future__ import annotations

import jsonschema
import pytest

from loop_engine.schemas import validate_with_schema


def test_review_result_schema_accepts_valid_payload():
    validate_with_schema(
        {
            "verdict": "PASS",
            "stage_name": "000_raw_import",
            "mathematical_status": {
                "exact_reconstruction": True,
                "simplification_real": True,
                "regression_preserved": True,
                "overclaim_detected": False,
            },
            "blocking_issues": [],
            "nonblocking_caveats": [],
            "allowed_claims": ["stage-local claim"],
            "forbidden_claims": ["global overclaim"],
            "next_action": "FREEZE",
            "suggested_next_stage": None,
            "patch_instructions": [],
        },
        "review_result",
    )


def test_review_result_schema_rejects_unknown_verdict():
    with pytest.raises(jsonschema.ValidationError):
        validate_with_schema(
            {
                "verdict": "KINDA_OK",
                "stage_name": "bad",
                "mathematical_status": {
                    "exact_reconstruction": True,
                    "simplification_real": True,
                    "regression_preserved": True,
                    "overclaim_detected": False,
                },
                "blocking_issues": [],
                "nonblocking_caveats": [],
                "allowed_claims": [],
                "forbidden_claims": [],
                "next_action": "FREEZE",
                "suggested_next_stage": None,
                "patch_instructions": [],
            },
            "review_result",
        )


def test_validation_summary_schema_requires_checks():
    with pytest.raises(jsonschema.ValidationError):
        validate_with_schema({"stage_name": "x", "overall_gate": "PASS"}, "validation_summary")

