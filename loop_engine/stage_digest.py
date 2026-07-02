from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import REPO_ROOT, read_json, read_text, write_json, write_text


def _escape_tex(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in str(text))


def _list_files(stage: Path, folder: str) -> list[str]:
    root = stage / folder
    if not root.exists():
        return []
    return sorted(str(path.relative_to(stage)) for path in root.rglob("*") if path.is_file())


def _validation_lines(validation: dict[str, Any]) -> list[str]:
    lines = [f"OverallGate -> {validation.get('overall_gate', 'UNKNOWN')}"]
    for check in validation.get("checks", []):
        name = check.get("name")
        actual = check.get("actual")
        gate = check.get("gate")
        lines.append(f"{name} -> {actual} ({gate})")
    for key in [
        "DCProjectionTo1D",
        "RawMinusSectorSum",
        "SectorLedgerXXXCollapse",
        "NoIBPStarted",
        "NoFullTensorialClaim",
        "PairFusionDifference",
        "CenterFusionDifference",
        "XXXPairProjectionRegression",
        "XXXCenterProjectionRegression",
    ]:
        if key in validation:
            lines.append(f"{key} -> {validation[key]}")
    return lines


def _bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- none"


def _tex_bullets(items: list[str]) -> str:
    if not items:
        return r"\begin{itemize}\item none\end{itemize}"
    body = "\n".join(rf"\item {_escape_tex(item)}" for item in items)
    return "\\begin{itemize}\n" + body + "\n\\end{itemize}"


def _stage_report_basename(stage: Path) -> str:
    name = stage.name
    if name.startswith("sigma_abc_"):
        return "stage_" + name.removeprefix("sigma_abc_")
    return f"stage_{name}"


def _completion_matrix_lines(stage: Path) -> list[str]:
    path = stage / "reports" / "completion_matrix.json"
    if not path.exists():
        return ["Completion matrix -> MISSING"]
    matrix = read_json(path)
    blocking = [
        str(item.get("id"))
        for item in matrix.get("items", [])
        if item.get("blocking") and item.get("status") in {"MISSING", "FAILED", "BLOCKED"}
    ]
    lines = [
        f"Overall completion -> {matrix.get('overall_completion')}",
        f"Evidence-level freeze eligible -> {'YES' if matrix.get('freeze_eligible') else 'NO'}",
        f"Recommended human action -> {matrix.get('recommended_human_action')}",
        f"Blocking items -> {len(blocking)}",
    ]
    lines.extend(f"  - {item}" for item in blocking[:10])
    return lines


def _human_signoff_lines(stage: Path) -> list[str]:
    path = stage / ".loop" / "human_signoff.yaml"
    if not path.exists():
        return ["Human signoff -> MISSING"]
    import yaml

    signoff = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    permission = signoff.get("permission", {})
    lines = [
        f"Decision -> {signoff.get('decision')}",
        f"Signed by -> {signoff.get('signed_by')}",
        f"Signed at -> {signoff.get('signed_at')}",
        f"Permission.freeze_checkpoint -> {permission.get('freeze_checkpoint')}",
        f"Permission.continue_patch_loop -> {permission.get('continue_patch_loop')}",
        f"Permission.promote_claim -> {permission.get('promote_claim')}",
        f"Permission.start_ibp -> {permission.get('start_ibp')}",
        f"Permission.start_total_derivative -> {permission.get('start_total_derivative')}",
    ]
    lines.extend(f"Blocking reason -> {reason}" for reason in signoff.get("blocking_reason", []))
    lines.extend(f"Accepted caveat -> {caveat}" for caveat in signoff.get("accepted_caveats", []))
    return lines


def _pre_run_brief_lines(stage: Path) -> list[str]:
    path = stage / ".loop" / "pre_run_brief.json"
    audit_path = stage / ".loop" / "pre_run_brief_audit.json"
    if not path.exists():
        return ["Pre-run brief -> MISSING"]
    brief = read_json(path)
    audit = read_json(audit_path) if audit_path.exists() else {}
    task = brief.get("task_understanding", {})
    return [
        f"PreRunBriefGate -> {audit.get('gate', 'UNKNOWN')}",
        f"StageId -> {brief.get('stage_id')}",
        f"ProfileId -> {brief.get('profile_id')}",
        f"ClaimBoundaryAcknowledged -> {task.get('claim_boundary_acknowledged')}",
        f"ExpectedOutputs -> {len(task.get('expected_outputs', []))}",
        f"DependenciesAcknowledged -> {len(task.get('dependencies_acknowledged', []))}",
        f"CaveatsAcknowledged -> {len(task.get('caveats_acknowledged', []))}",
    ]


def _scientific_identity_lines(stage: Path) -> list[str]:
    path = stage / ".loop" / "scientific_identities.json"
    if not path.exists():
        return ["Scientific identities -> MISSING"]
    payload = read_json(path)
    return [
        f"Identity -> {identity.get('label')} ({identity.get('role')})"
        for identity in payload.get("identities", [])
    ] or ["Scientific identities -> none"]


def _identity_traceability_lines(stage: Path) -> list[str]:
    path = stage / ".loop" / "identity_traceability.json"
    if not path.exists():
        return ["Identity traceability -> MISSING"]
    trace = read_json(path)
    lines = [f"IdentityTraceabilityGate -> {trace.get('identity_traceability_gate')}"]
    lines.extend(
        f"{item.get('identity_label')} -> {item.get('trace_status')}"
        for item in trace.get("items", [])[:10]
    )
    return lines


def build_stage_digest(stage: Path, *, title: str | None = None) -> dict[str, Any]:
    validation = read_json(stage / ".loop" / "validation_summary.json") if (stage / ".loop" / "validation_summary.json").exists() else {}
    review = read_json(stage / ".loop" / "review_result.json") if (stage / ".loop" / "review_result.json").exists() else {}
    meta = read_json(stage / ".loop" / "meta_review_result.json") if (stage / ".loop" / "meta_review_result.json").exists() else {}
    quality = read_json(stage / ".loop" / "review_quality.json") if (stage / ".loop" / "review_quality.json").exists() else {}
    metrics = read_json(stage / ".loop" / "metrics.json") if (stage / ".loop" / "metrics.json").exists() else {}

    stage_name = title or stage.name
    slug = stage.name
    named = _stage_report_basename(stage)
    goal = read_text(stage / "STAGE_PLAN.md", "No stage plan found.").splitlines()
    goal_text = next((line for line in goal if line and not line.startswith("#")), "See STAGE_PLAN.md.")
    inputs = _list_files(stage, "input_snapshots")
    outputs = _list_files(stage, "output") + _list_files(stage, "reports") + _list_files(stage, "validation")
    validation_lines = _validation_lines(validation)
    reviewer_lines = [
        f"Ordinary review -> {review.get('verdict', 'MISSING')}",
        f"Meta review -> {meta.get('verdict', 'MISSING')}",
    ]
    caveats = list(dict.fromkeys([*validation.get("caveats", []), *meta.get("caveats_to_preserve", [])]))
    if not caveats and "DCProjectionTo1D -> INHERITED_PASS" in read_text(stage / "review_packet.md"):
        caveats.append("DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.")

    next_action = meta.get("next_safe_stage") or review.get("suggested_next_stage") or "Freeze checkpoint or wait for explicit human approval."
    completion_lines = _completion_matrix_lines(stage)
    signoff_lines = _human_signoff_lines(stage)
    pre_run_lines = _pre_run_brief_lines(stage)
    scientific_identity_lines = _scientific_identity_lines(stage)
    traceability_lines = _identity_traceability_lines(stage)
    md = f"""# Stage Summary: `{stage_name}`

## 1. Stage identity

`{stage.name}`

## 2. Goal

{goal_text}

## 3. Inputs

{_bullet(inputs)}

## 4. Outputs

{_bullet(outputs)}

## 5. Validation gates

{_bullet(validation_lines)}

## 6. Reviewer verdicts

{_bullet(reviewer_lines)}

## 6a. Review lane and quality

- ReviewLane -> {quality.get('review_lane', 'UNKNOWN')}
- RiskLevel -> {read_json(stage / '.loop' / 'risk_classification.json').get('risk_level', 'UNKNOWN') if (stage / '.loop' / 'risk_classification.json').exists() else 'UNKNOWN'}
- FullPanelRequired -> {read_json(stage / '.loop' / 'risk_classification.json').get('full_panel_required', 'UNKNOWN') if (stage / '.loop' / 'risk_classification.json').exists() else 'UNKNOWN'}
- ReviewerTokensSavedReason -> {quality.get('review_lane_justification', 'not recorded')}
- PASS as -> {quality.get('pass_as', 'not recorded')}
- NOT PASS as -> {', '.join(quality.get('not_pass_as', [])) or 'not recorded'}
- Next safe action -> {quality.get('next_safe_stage', next_action)}

## 7. Scientific status

{meta.get('scientific_status', 'Meta review not available.')}

## 8. Caveats and claim boundary

{_bullet(caveats)}

## 9. Next recommended action

{next_action}

## 10. Completion matrix summary

{_bullet(completion_lines)}

## 11. Human signoff

{_bullet(signoff_lines)}

## 12. Pre-run brief

{_bullet(pre_run_lines)}

## 13. Scientific identities

{_bullet(scientific_identity_lines)}

## 14. Identity traceability

{_bullet(traceability_lines)}

## Representative identity

\\[
\\mathrm{{stage}}_{{\\rm old}}-\\mathrm{{stage}}_{{\\rm new}}=0.
\\]
"""
    reports = stage / "reports"
    write_text(reports / "stage_summary.md", md)
    write_text(reports / f"{slug}_summary.md", md)
    write_text(reports / f"{named}_summary.md", md)

    tex = f"""\\documentclass[11pt]{{article}}
\\usepackage[margin=0.75in]{{geometry}}
\\usepackage{{amsmath}}
\\usepackage{{hyperref}}
\\title{{Stage Summary: {_escape_tex(stage_name)}}}
\\date{{}}
\\begin{{document}}
\\maketitle
\\section*{{1. Stage identity}}
\\texttt{{{_escape_tex(stage.name)}}}
\\section*{{2. Goal}}
{_escape_tex(goal_text)}
\\section*{{3. Inputs}}
{_tex_bullets(inputs)}
\\section*{{4. Outputs}}
{_tex_bullets(outputs[:30])}
\\section*{{5. Validation gates}}
{_tex_bullets(validation_lines)}
\\section*{{6. Reviewer verdicts}}
{_tex_bullets(reviewer_lines)}
\\section*{{7. Scientific status}}
{_escape_tex(meta.get('scientific_status', 'Meta review not available.'))}
\\section*{{8. Caveats and claim boundary}}
{_tex_bullets(caveats)}
\\section*{{9. Next recommended action}}
{_escape_tex(next_action)}
\\section*{{10. Completion matrix summary}}
{_tex_bullets(completion_lines)}
\\section*{{11. Human signoff}}
{_tex_bullets(signoff_lines)}
\\section*{{12. Pre-run brief}}
{_tex_bullets(pre_run_lines)}
\\section*{{13. Scientific identities}}
{_tex_bullets(scientific_identity_lines)}
\\section*{{14. Identity traceability}}
{_tex_bullets(traceability_lines)}
\\section*{{Representative identity}}
\\[
\\mathrm{{stage}}_{{\\rm old}}-\\mathrm{{stage}}_{{\\rm new}}=0.
\\]
\\end{{document}}
"""
    tex_path = reports / "stage_summary.tex"
    write_text(tex_path, tex)
    named_tex_path = reports / f"{slug}_summary.tex"
    write_text(named_tex_path, tex)
    plan_named_tex_path = reports / f"{named}_summary.tex"
    write_text(plan_named_tex_path, tex)

    compile_status = "SKIPPED_XELATEX_UNAVAILABLE"
    pdf_path = reports / "stage_summary.pdf"
    if shutil.which("xelatex"):
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=reports,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            write_text(reports / "stage_summary_xelatex.log", result.stdout + "\n" + result.stderr)
            raise RuntimeError("xelatex failed while building stage summary")
        compile_status = "PASS"
        named_pdf = reports / f"{slug}_summary.pdf"
        if pdf_path.exists():
            named_pdf.write_bytes(pdf_path.read_bytes())
            (reports / f"{named}_summary.pdf").write_bytes(pdf_path.read_bytes())

    summary = {
        "stage_name": stage.name,
        "markdown": "reports/stage_summary.md",
        "named_markdown": f"reports/{slug}_summary.md",
        "plan_named_markdown": f"reports/{named}_summary.md",
        "tex": "reports/stage_summary.tex",
        "named_tex": f"reports/{slug}_summary.tex",
        "plan_named_tex": f"reports/{named}_summary.tex",
        "pdf": "reports/stage_summary.pdf" if pdf_path.exists() else None,
        "named_pdf": f"reports/{slug}_summary.pdf" if (reports / f"{slug}_summary.pdf").exists() else None,
        "plan_named_pdf": f"reports/{named}_summary.pdf" if (reports / f"{named}_summary.pdf").exists() else None,
        "PDFCompileStatus": compile_status,
        "metrics_seen": bool(metrics),
    }
    write_json(stage / "reports" / "stage_summary_build.json", summary)
    return summary


def build_stage010_retrospective(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    reports = repo_root / "reports"
    reports.mkdir(exist_ok=True)
    source = repo_root / "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md"
    source_text = read_text(source, "# Missing Stage 010 source report\n")
    md = f"""# Stage 010 Retrospective Summary

Stage 010 PASS as pair-sector-only row-provenance kernel-family fusion pilot.
It grouped 912 pair rows into 3 band-pair families.

```text
PairFusionDifference -> 0
XXXPairProjectionRegression -> PASS
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
NoFullTensorialClaim -> True
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Source Report Excerpt

{source_text}
"""
    md_path = reports / "stage_010_retrospective_summary.md"
    write_text(md_path, md)
    tex_path = reports / "stage_010_retrospective_summary.tex"
    tex = f"""\\documentclass[11pt]{{article}}
\\usepackage[margin=0.75in]{{geometry}}
\\usepackage{{amsmath}}
\\title{{Stage 010 Retrospective Summary}}
\\date{{}}
\\begin{{document}}
\\maketitle
Stage 010 PASS as pair-sector-only row-provenance kernel-family fusion pilot.
It grouped 912 pair rows into 3 band-pair families.

\\begin{{itemize}}
\\item PairFusionDifference -> 0.
\\item XXXPairProjectionRegression -> PASS.
\\item No IBP was started.
\\item No total derivative was introduced.
\\item No full tensorial sigma mu alpha beta correctness was claimed.
\\item DCProjectionTo1D -> INHERITED\\_PASS, not direct full tensorial DC-series PASS.
\\end{{itemize}}
\\end{{document}}
"""
    write_text(tex_path, tex)
    compile_status = "SKIPPED_XELATEX_UNAVAILABLE"
    pdf_path = reports / "stage_010_retrospective_summary.pdf"
    if shutil.which("xelatex"):
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=reports,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            write_text(reports / "stage_010_retrospective_summary_xelatex.log", result.stdout + "\n" + result.stderr)
            raise RuntimeError("xelatex failed while building Stage 010 retrospective")
        compile_status = "PASS"
    return {
        "markdown": str(md_path.relative_to(repo_root)),
        "tex": str(tex_path.relative_to(repo_root)),
        "pdf": str(pdf_path.relative_to(repo_root)) if pdf_path.exists() else None,
        "PDFCompileStatus": compile_status,
    }
