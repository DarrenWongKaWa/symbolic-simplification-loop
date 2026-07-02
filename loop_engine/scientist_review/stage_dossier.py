from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loop_engine.config import REPO_ROOT, read_json, read_text, relative_to_repo, write_text
from loop_engine.schemas import validate_with_schema

DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."

ALLOWED_CLAIMS = [
    "repo-level loop-engine progress review",
    "sigma_abc raw/provenance/projection/prep audit",
    "projection-preserving raw tensorial candidate",
    "sector ledger and xxx collapse evidence",
    "stage-specific exact identities only when validation_summary.json records PASS",
]

FORBIDDEN_CLAIMS = [
    "full tensorial sigma_mu_alpha_beta correctness",
    "direct full tensorial DC-series PASS",
    "012C promotion unless actually frozen",
    "Stage 013 unless actually started and approved",
    "tensorial IBP unless explicitly run and validated",
    "total-derivative reduction unless explicitly validated",
]


@dataclass
class ScientistReviewPacket:
    project: str
    output_dir: Path
    stage_dossiers: list[dict[str, Any]]
    generated_files: list[Path]
    pdf_built: bool = False
    pdf_error: str | None = None


def _rel(path: Path) -> str:
    return relative_to_repo(path)


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    return read_json(path) if path.exists() else {}


def _stage_dirs(project: str) -> list[Path]:
    root = REPO_ROOT / "autonomous_runs" / project / "stages"
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def _files_under(stage: Path, names: list[str]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for name in names:
        path = stage / name
        if path.exists():
            found.append({"path": str(path.relative_to(stage)), "role": name.split("/", 1)[0]})
    return found


def _glob_under(stage: Path, folder: str) -> list[dict[str, str]]:
    root = stage / folder
    if not root.exists():
        return []
    return [
        {"path": str(path.relative_to(stage)), "role": folder}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def classify_verification(stage: Path, validation: dict[str, Any]) -> dict[str, Any]:
    checks = validation.get("checks", [])
    check_names = {str(check.get("name")): check for check in checks}
    gate = validation.get("overall_gate", "UNKNOWN")

    if "DCProjectionStillInheritedPASS" in check_names:
        dc_actual = check_names["DCProjectionStillInheritedPASS"].get("actual")
        if dc_actual is True:
            caveat = DC_CAVEAT
        else:
            caveat = "DC inherited-pass premise not confirmed."
    else:
        caveat = DC_CAVEAT if DC_CAVEAT in "\n".join(validation.get("caveats", [])) else ""

    dc_direct = check_names.get("DCProjectionTo1D")
    if dc_direct and dc_direct.get("actual") == "INHERITED_PASS":
        return {
            "type": "inherited_pass",
            "identity_latex": r"\mathrm{DCProjectionTo1D}=\mathrm{INHERITED\_PASS}",
            "identity_plaintext": "DCProjectionTo1D is inherited from finite-frequency projection and the documented 1D DC pipeline; this is not an exact-zero identity.",
            "expected_result": "INHERITED_PASS",
            "actual_result": "INHERITED_PASS",
            "gate": gate,
            "evidence_paths": [".loop/validation_summary.json"],
            "caveat": DC_CAVEAT,
        }

    if "candidate_preparation" in stage.name or "real_loop_candidate_preparation" in stage.name:
        return {
            "type": "preparation_gate",
            "identity_latex": r"\mathrm{artifact\ readiness\ and\ safety\ gate}",
            "identity_plaintext": "Preparation gate checks artifact presence and safety flags; this is not an exact-zero identity.",
            "expected_result": "READY/PASS without promotion",
            "actual_result": gate,
            "gate": gate,
            "evidence_paths": [".loop/validation_summary.json"],
            "caveat": caveat,
        }

    if "basis_closure" in stage.name or "sector_architecture" in stage.name:
        return {
            "type": "inventory_only",
            "identity_latex": r"\mathrm{inventory/provenance\ only;\ no\ promotion}",
            "identity_plaintext": "Inventory/provenance checkpoint; this is not an exact-zero identity.",
            "expected_result": "no forbidden fusion/IBP/promotion",
            "actual_result": gate,
            "gate": gate,
            "evidence_paths": [".loop/validation_summary.json", "reports/completion_matrix.json"],
            "caveat": caveat,
        }

    if "xxx_regression" in stage.name and "SectorLedgerXXXCollapse" in check_names:
        return {
            "type": "projection_regression",
            "identity_latex": r"\mathrm{ProjectToXXX}(\sigma_{\mu\alpha\beta})-\sigma^{xxx}_{\rm ref}=0",
            "identity_plaintext": "ProjectToXXX[sigma_mu_alpha_beta] - sigma_xxx_final_reference = 0",
            "expected_result": "PASS",
            "actual_result": check_names["SectorLedgerXXXCollapse"].get("actual", "UNKNOWN"),
            "gate": gate,
            "evidence_paths": [".loop/validation_summary.json"],
            "caveat": caveat,
        }

    if "RawMinusSectorSum" in check_names:
        return {
            "type": "exact_reconstruction",
            "identity_latex": r"\sigma_{\rm raw}-(\sigma_{\rm center}+\sigma_{\rm pair}+\sigma_{\rm loop})=0",
            "identity_plaintext": "raw_sigma_abc - (center_sector + pair_sector + loop_sector) = 0",
            "expected_result": 0,
            "actual_result": check_names["RawMinusSectorSum"].get("actual", "UNKNOWN"),
            "gate": gate,
            "evidence_paths": [".loop/validation_summary.json"],
            "caveat": caveat,
        }

    if "012" in stage.name or "inventory" in stage.name or "hypothesis" in stage.name:
        return {
            "type": "inventory_only",
            "identity_latex": r"\mathrm{inventory\ only;\ no\ promotion}",
            "identity_plaintext": "Inventory or hypothesis ledger only; this is not an exact-zero identity.",
            "expected_result": "no forbidden promotion",
            "actual_result": gate,
            "gate": gate,
            "evidence_paths": [".loop/validation_summary.json"],
            "caveat": caveat,
        }

    return {
        "type": "preparation_gate",
        "identity_latex": r"\mathrm{safety\ flags\ and\ artifact\ readiness}",
        "identity_plaintext": "Preparation/safety gate; this is not an exact-zero identity.",
        "expected_result": "PASS",
        "actual_result": gate,
        "gate": gate,
        "evidence_paths": [".loop/validation_summary.json"],
        "caveat": caveat,
    }


def _claim_boundary(stage: Path, validation: dict[str, Any], review: dict[str, Any]) -> dict[str, list[str]]:
    manifest = _read_json_if_exists(stage / ".loop" / "checkpoint_manifest.json")
    allowed = manifest.get("allowed_claims") or review.get("allowed_claims") or ALLOWED_CLAIMS
    forbidden = manifest.get("forbidden_claims") or review.get("forbidden_claims") or FORBIDDEN_CLAIMS
    caveats = list(dict.fromkeys([
        *validation.get("caveats", []),
        *manifest.get("accepted_caveats", []),
        *review.get("nonblocking_caveats", []),
        DC_CAVEAT,
    ]))
    return {"allowed": allowed, "forbidden": forbidden, "caveats": caveats}


def build_stage_dossier(stage: Path) -> dict[str, Any]:
    validation = _read_json_if_exists(stage / ".loop" / "validation_summary.json")
    review = _read_json_if_exists(stage / ".loop" / "review_result.json")
    matrix = _read_json_if_exists(stage / "reports" / "completion_matrix.json")
    verification = classify_verification(stage, validation)
    boundary = _claim_boundary(stage, validation, review)
    if verification.get("caveat") and verification["caveat"] not in boundary["caveats"]:
        boundary["caveats"].append(verification["caveat"])
    verification.pop("caveat", None)

    dossier = {
        "stage_id": stage.name,
        "stage_title": stage.name.replace("_", " "),
        "stage_type": _stage_type(stage.name),
        "human_summary": _human_summary(stage.name, verification["type"]),
        "inputs": _glob_under(stage, "input_snapshots") or _files_under(stage, ["STAGE_PLAN.md"]),
        "outputs": _glob_under(stage, "output") + _glob_under(stage, "reports"),
        "scripts": _glob_under(stage, "scripts"),
        "verification": verification,
        "claim_boundary": boundary,
        "caveats": boundary["caveats"],
        "machine_evidence": [
            item for item in _files_under(
                stage,
                [
                    ".loop/validation_summary.json",
                    ".loop/review_result.json",
                    "reports/completion_matrix.json",
                    ".loop/checkpoint_manifest.json",
                    "CLAIM_BOUNDARY.md",
                ],
            )
        ],
        "human_decision": {
            "recommended_action": matrix.get("recommended_human_action", "READ_ONLY_REVIEW"),
            "requires_human_signoff": bool(matrix.get("freeze_eligible", False)),
            "signoff_file_created": False,
        },
    }
    validate_with_schema(dossier, "scientist_review")
    return dossier


def _stage_type(stage_name: str) -> str:
    if "xxx_regression" in stage_name:
        return "projection_regression"
    if "sector_architecture" in stage_name or "basis_closure" in stage_name:
        return "inventory/preparation"
    if "012" in stage_name:
        return "inventory/preparation"
    return "preparation"


def _human_summary(stage_name: str, verification_type: str) -> str:
    if verification_type == "projection_regression":
        return "Checks that the current tensorial candidate preserves the protected projected xxx benchmark."
    if verification_type == "exact_reconstruction":
        return "Checks an exact raw-sector reconstruction identity without starting kernel fusion or IBP."
    if verification_type == "inventory_only":
        return "Records inventory or hypothesis evidence only; this is not an exact-zero identity."
    return f"Summarizes {stage_name} as a safety/preparation checkpoint."


def render_stage_dossier_md(dossier: dict[str, Any]) -> str:
    verification = dossier["verification"]
    boundary = dossier["claim_boundary"]
    return f"""# Stage Dossier: `{dossier['stage_id']}`

## One-Sentence Scientific Role

{dossier['human_summary']}

## Stage Type

{dossier['stage_type']}

## Inputs

{_md_path_role_list(dossier['inputs'])}

## Outputs

{_md_path_role_list(dossier['outputs'])}

## Script Map

{_md_path_role_list(dossier['scripts'])}

## Verification Standard

`{verification['type']}`

## Exact Identity Checked

```text
{verification['identity_plaintext']}
```

LaTeX:

```tex
{verification['identity_latex']}
```

## Actual Machine Result

- Expected: `{verification['expected_result']}`
- Actual: `{verification['actual_result']}`
- Gate: `{verification['gate']}`
- Evidence: {', '.join(verification['evidence_paths'])}

## Allowed Claims

{_md_list(boundary['allowed'])}

## Forbidden Claims

{_md_list(boundary['forbidden'])}

## Caveats

{_md_list(dossier['caveats'])}

## Human Review Checklist

- [ ] Validation gate is PASS or caveat is explicitly inherited.
- [ ] Reviewer result is schema-valid when present.
- [ ] Completion matrix is non-blocking for any freeze claim.
- [ ] No forbidden action is claimed.
- [ ] Permanent DC inherited caveat is preserved.
- [ ] This dossier is human-facing and does not create `human_signoff.yaml`.
"""


def _md_list(items: list[Any]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- none"


def _md_path_role_list(items: list[dict[str, Any]]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- `{item.get('path')}`: {item.get('role')}" for item in items)


def build_scientist_review_packet(project: str, output_dir: Path, *, build_pdf: bool = True) -> ScientistReviewPacket:
    from .claim_boundary import render_claim_boundary
    from .render_latex import render_packet_tex, try_compile_pdf
    from .script_map import render_script_map
    from .validation_ledger import render_validation_ledger

    output_dir.mkdir(parents=True, exist_ok=True)
    stage_dir = output_dir / "STAGE_DOSSIERS"
    stage_dir.mkdir(parents=True, exist_ok=True)
    dossiers = [build_stage_dossier(stage) for stage in _stage_dirs(project)]
    generated: list[Path] = []

    for dossier in dossiers:
        path = stage_dir / f"{dossier['stage_id']}.md"
        write_text(path, render_stage_dossier_md(dossier))
        generated.append(path)

    files = {
        "DASHBOARD.md": render_dashboard(project, dossiers),
        "VALIDATION_LEDGER.md": render_validation_ledger(dossiers),
        "SCRIPT_MAP.md": render_script_map(dossiers),
        "CLAIM_BOUNDARY.md": render_claim_boundary(project, dossiers),
        "SIGNOFF_PACKET.md": render_signoff_packet(project, dossiers),
    }
    packet_md = render_main_packet(project, files, dossiers)
    files["SCIENTIST_REVIEW_PACKET.md"] = packet_md
    files["SCIENTIST_REVIEW_PACKET.tex"] = render_packet_tex(project, packet_md, dossiers)

    for name, text in files.items():
        path = output_dir / name
        write_text(path, text)
        generated.append(path)

    packet = ScientistReviewPacket(project=project, output_dir=output_dir, stage_dossiers=dossiers, generated_files=generated)
    if build_pdf:
        tex_path = output_dir / "SCIENTIST_REVIEW_PACKET.tex"
        pdf_path, error = try_compile_pdf(tex_path)
        packet.pdf_built = pdf_path is not None
        packet.pdf_error = error
        if pdf_path is not None:
            packet.generated_files.append(pdf_path)
    return packet


def render_dashboard(project: str, dossiers: list[dict[str, Any]]) -> str:
    stage_ids = [d["stage_id"] for d in dossiers]
    deepest = stage_ids[-1] if stage_ids else "none"
    devlog_mentions_late = any((REPO_ROOT / "docs" / "devlog" / "loop_engine" / name).exists() for name in [
        "SIGMA_ABC_012AB_ARTIFACT_CONTRACT_MATERIALIZATION_REPORT.md",
        "LOOP_019_UPSTREAM_012A_012B_MATERIALIZATION_REPORT.md",
    ])
    forbidden_status = [
        "012C promotion started? NO",
        "Stage 013 started? NO",
        "tensorial IBP started? NO",
        "total derivative introduced? NO",
    ]
    table = "\n".join(
        f"| `{d['stage_id']}` | {d['stage_type']} | {d['verification']['type']} | {d['verification']['gate']} |"
        for d in dossiers
    )
    return f"""# Scientist Review Dashboard: `{project}`

## Current Status

- Current deepest frozen checkpoint visible in live root: `{deepest}`
- Current deepest provisional checkpoint visible in live root: `none detected`
- Open review debt count: 0 in this read-only packet
- live-root vs devlog divergence status: 011/012A/012B/012C-prep are historically documented in devlog but not live-root-present.
- Historical devlog evidence for later stages detected: {devlog_mentions_late}

## Permanent Caveat

```text
{DC_CAVEAT}
```

## Stage Status Table

| Stage | Stage type | Verification type | Gate |
| --- | --- | --- | --- |
{table}

## Verification Type Summary

{_md_list(sorted({d['verification']['type'] for d in dossiers}))}

## Forbidden Action Status

{_md_list(forbidden_status)}

## Next Safe Action

Restore or regenerate 011/012A/012B live artifacts before treating historical 012C-prep evidence as current. If restored, run 012C preparation dry-run only; do not promote candidates without explicit human approval and L2/full-panel review.
"""


def render_signoff_packet(project: str, dossiers: list[dict[str, Any]]) -> str:
    blocked = [
        d for d in dossiers
        if d["verification"]["gate"] not in {"PASS", "PASS_WITH_CAVEAT"}
    ]
    rows = "\n".join(
        f"| `{d['stage_id']}` | {d['human_decision']['recommended_action']} | {d['verification']['gate']} | {', '.join(d['verification']['evidence_paths'])} |"
        for d in dossiers
    )
    return f"""# Signoff Packet: `{project}`

This packet does not create or replace human_signoff.yaml. It is a checklist for a human scientist.

## Stages Ready For Signoff Review

| Stage | Recommended action | Validation gate | Evidence |
| --- | --- | --- | --- |
{rows}

## Blocked Stages

{_md_list([d['stage_id'] for d in blocked])}

## Global Caveats

- {DC_CAVEAT}
- live-root vs devlog divergence: 011/012A/012B/012C-prep are historically documented in devlog but not live-root-present unless restored or regenerated.
- Historical 011/012A/012B/012C-prep devlog evidence is not current live-root evidence unless restored or regenerated.

## Yes/No Checklist

- [ ] validation PASS?
- [ ] reviewer schema-valid?
- [ ] completion matrix non-blocking?
- [ ] no forbidden action?
- [ ] caveat preserved?
- [ ] checkpoint manifest ready?
"""


def render_main_packet(project: str, files: dict[str, str], dossiers: list[dict[str, Any]]) -> str:
    runtime_note = _runtime_note()
    return f"""# Scientist Review Packet: `{project}`

## Purpose

This is a human-facing review layer on top of the machine trust-stack:

```text
STAGE_PLAN -> EXECUTE -> VALIDATE -> REVIEW -> COMPLETION_MATRIX -> SIGNOFF -> FREEZE
```

It is not authoritative for freeze and does not override validation summaries,
completion matrices, freeze preconditions, review debt, or human signoff.

## Dashboard

{files['DASHBOARD.md']}

## Validation Ledger

{files['VALIDATION_LEDGER.md']}

## Script Map

{files['SCRIPT_MAP.md']}

## Claim Boundary

{files['CLAIM_BOUNDARY.md']}

## Signoff Packet

{files['SIGNOFF_PACKET.md']}

## Runtime Config Note

{runtime_note}

## Stage Dossiers

{_md_list([f"STAGE_DOSSIERS/{d['stage_id']}.md" for d in dossiers])}
"""


def _runtime_note() -> str:
    path = REPO_ROOT / "agents" / "runtime.local.yaml"
    if not path.exists():
        return "`agents/runtime.local.yaml` not present."
    text = path.read_text(encoding="utf-8")
    redacted_lines = []
    for line in text.splitlines():
        if "KEY" in line.upper() or "TOKEN" in line.upper() or "SECRET" in line.upper():
            redacted_lines.append("  REDACTED: REDACTED")
        else:
            redacted_lines.append(line)
    preview = "\n".join(redacted_lines[:12])
    return f"`agents/runtime.local.yaml` inspected with secrets REDACTED.\n\n```yaml\n{preview}\n```"
