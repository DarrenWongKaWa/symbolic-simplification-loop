from __future__ import annotations

from typing import Any


def render_script_map(dossiers: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for dossier in dossiers:
        scripts = dossier.get("scripts") or [{"path": "no stage-local script recorded", "role": "not recorded"}]
        for script in scripts:
            rows.append(
                "| `{path}` | {role} | `{identity}` | `{stage}` | {evidence} |".format(
                    path=script.get("path"),
                    role=_role_to_human(script.get("role", "script")),
                    identity=dossier["verification"]["identity_plaintext"],
                    stage=dossier["stage_id"],
                    evidence=", ".join(f"`{path}`" for path in dossier["verification"]["evidence_paths"]),
                )
            )
    return f"""# Script Map

| Script/output file | Human derivation role | Mathematical identity represented | Stage | Evidence path |
| --- | --- | --- | --- | --- |
{chr(10).join(rows)}

## Engineering Evidence

Runner, digest, provider, and TLS scripts are engineering evidence. They do not
replace mathematical validation identities.
"""


def _role_to_human(role: str) -> str:
    if "validation" in role:
        return "validation script"
    if "script" in role:
        return "stage helper script"
    return role
