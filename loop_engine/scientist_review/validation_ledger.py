from __future__ import annotations

from typing import Any


def render_validation_ledger(dossiers: list[dict[str, Any]]) -> str:
    rows = "\n".join(
        "| `{stage}` | {vtype} | `{identity}` | `{expected}` | `{actual}` | {gate} | {evidence} | {boundary} |".format(
            stage=dossier["stage_id"],
            vtype=dossier["verification"]["type"],
            identity=dossier["verification"]["identity_plaintext"],
            expected=dossier["verification"]["expected_result"],
            actual=dossier["verification"]["actual_result"],
            gate=dossier["verification"]["gate"],
            evidence=", ".join(f"`{path}`" for path in dossier["verification"]["evidence_paths"]),
            boundary="; ".join(dossier["claim_boundary"]["caveats"][:2]),
        )
        for dossier in dossiers
    )
    return f"""# Validation Ledger

| Stage | Verification type | Identity checked | Expected | Actual | Gate | Evidence | Claim boundary |
| --- | --- | --- | --- | --- | --- | --- | --- |
{rows}

## Notes

- `inventory_only` and `preparation_gate` stages are not exact-zero identities.
- `inherited_pass` is allowed only with documented provenance and preserved caveats.
- This ledger is human-facing and does not replace `validation_summary.json`.
"""
