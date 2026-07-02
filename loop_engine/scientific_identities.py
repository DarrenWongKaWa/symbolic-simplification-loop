from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .config import REPO_ROOT, read_json, read_text, write_json, write_text
from .schemas import validate_with_schema


def load_identity_library(project: str = "sigma_abc") -> dict[str, Any]:
    path = REPO_ROOT / "identities" / f"{project}.default_identities.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    validate_with_schema(data, "scientific_identity_library")
    return data


def _parse_stage_specific_identities(stage: Path) -> list[dict[str, Any]]:
    plan = read_text(stage / "STAGE_PLAN.yaml")
    if plan:
        data = yaml.safe_load(plan) or {}
        return list(data.get("scientific_identities", []) or [])
    text = read_text(stage / "STAGE_PLAN.md")
    if "scientific_identities:" not in text:
        return []
    # Markdown plans in this repo are intentionally lightweight.  Stage-specific
    # identity YAML should live in STAGE_PLAN.yaml for machine use.
    return []


def _identity_lines(identities: list[dict[str, Any]]) -> str:
    lines = []
    for identity in identities:
        check = identity.get("check", "informational")
        if isinstance(check, list):
            check = ", ".join(check)
        lines.append(f"- **{identity.get('label')}** ({identity.get('role')}): check `{check}`")
        lines.append("")
        lines.append(identity.get("latex", ""))
    return "\n".join(lines)


def _identity_tex(identities: list[dict[str, Any]]) -> str:
    chunks = []
    for identity in identities:
        chunks.append(rf"\paragraph{{{identity.get('label')}}}")
        chunks.append(identity.get("latex", ""))
        check = identity.get("check", "informational")
        if isinstance(check, list):
            check = ", ".join(check)
        chunks.append(rf"\emph{{Linked check:}} \texttt{{{str(check).replace('_', r'\_')}}}")
    return "\n\n".join(chunks)


def render_stage_scientific_identities(stage: Path, *, project: str = "sigma_abc") -> dict[str, Any]:
    before = read_json(stage / ".loop" / "validation_summary.json") if (stage / ".loop" / "validation_summary.json").exists() else {}
    library = load_identity_library(project)
    identities = list(library.get("identities", [])) + _parse_stage_specific_identities(stage)
    payload = {
        "stage_id": stage.name,
        "project": project,
        "identities": identities,
    }
    md = "# Scientific Identities\n\n" + _identity_lines(identities) + "\n"
    tex = "\\section*{Scientific Identities}\n\n" + _identity_tex(identities) + "\n"
    after = read_json(stage / ".loop" / "validation_summary.json") if (stage / ".loop" / "validation_summary.json").exists() else {}
    return {
        "payload": payload,
        "markdown": md,
        "tex": tex,
        "validation_status_changed": before != after,
    }


def write_stage_scientific_identities(stage: Path, *, project: str = "sigma_abc") -> dict[str, Any]:
    rendered = render_stage_scientific_identities(stage, project=project)
    slug = stage.name
    md_path = stage / "reports" / f"stage_{slug}_scientific_identities.md"
    tex_path = stage / "reports" / f"stage_{slug}_scientific_identities.tex"
    json_path = stage / ".loop" / "scientific_identities.json"
    write_text(md_path, rendered["markdown"])
    write_text(tex_path, rendered["tex"])
    write_json(json_path, rendered["payload"])
    return {"markdown": md_path, "tex": tex_path, "json": json_path, "payload": rendered["payload"]}
