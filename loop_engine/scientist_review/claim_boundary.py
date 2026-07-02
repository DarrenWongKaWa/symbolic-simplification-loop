from __future__ import annotations

from typing import Any

from .stage_dossier import ALLOWED_CLAIMS, DC_CAVEAT, FORBIDDEN_CLAIMS


def render_claim_boundary(project: str, dossiers: list[dict[str, Any]]) -> str:
    stage_allowed = sorted({item for dossier in dossiers for item in dossier["claim_boundary"]["allowed"]})
    stage_forbidden = sorted({item for dossier in dossiers for item in dossier["claim_boundary"]["forbidden"]})
    stage_caveats = sorted({item for dossier in dossiers for item in dossier["claim_boundary"]["caveats"]})
    return f"""# Claim Boundary: `{project}`

## Allowed

{_md_list(list(dict.fromkeys([*ALLOWED_CLAIMS, *stage_allowed])))}

## Forbidden

{_md_list(list(dict.fromkeys([*FORBIDDEN_CLAIMS, *stage_forbidden])))}

## Caveat

```text
{DC_CAVEAT}
```

## Stage Caveats

{_md_list(stage_caveats)}

## Boundary Rule

This review packet can summarize a validated stage, but it cannot upgrade a
claim. Full tensorial correctness, 012C promotion, Stage 013, tensorial IBP, and
total-derivative reduction require their own validated stages.
"""


def _md_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- none"
