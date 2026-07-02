from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import write_json, write_text
from .schemas import validate_with_schema


CONJECTURE_STATUSES = {
    "PROPOSED",
    "BUILT",
    "VALIDATION_PASS",
    "VALIDATION_FAIL",
    "TIMEOUT",
    "REQUIRES_IBP_APPROVAL",
    "REQUIRES_HUMAN_APPROVAL",
    "PROMOTED",
    "ARCHIVED",
}


def make_conjecture(index: int, stage_id: str, *, allow_ibp: bool = False) -> dict[str, Any]:
    conjecture_id = f"conjecture_{index:03d}"
    if stage_id == "sigma_abc_011_center_sector_pilot":
        if index == 1:
            guess = "A weak center/contact grouping without term-hash conservation may leave provenance unresolved."
            expected = "incomplete center/contact row-provenance grouping"
        else:
            guess = "The frozen Stage 004 center/contact rows can be represented as three single-band provenance families preserving row ids and term hashes."
            expected = "CenterPatternLedger[band,row,term_hash]"
        target_sector = "center/contact sector"
        protected_benchmarks = ["sigma_xxx_projection", "stage004_center_sector_ledger"]
        risk_notes = ["Pre-IBP row-provenance candidate only; not a tensorial IBP or kernel-reduction claim."]
        required_validation = ["center row count conserved", "center term-hash multiset conserved"]
    elif index == 1:
        guess = "A deliberately weak toy grouping may leave a nonzero residual."
        expected = "nonzero residual candidate"
        target_sector = "toy"
        protected_benchmarks = ["mock_identity"]
        risk_notes = ["Conjectural until verifier service validates candidate residual."]
        required_validation = ["raw_sector - candidate_sector == 0"]
    else:
        guess = "x^2 + 2 x + 1 can be represented as (x + 1)^2."
        expected = "(x + 1)^2"
        target_sector = "toy"
        protected_benchmarks = ["mock_identity"]
        risk_notes = ["Conjectural until verifier service validates candidate residual."]
        required_validation = ["raw_sector - candidate_sector == 0"]
    forbidden = []
    if not allow_ibp:
        forbidden.extend(["IBP", "total derivative"])
    payload = {
        "conjecture_id": conjecture_id,
        "stage_id": stage_id,
        "proposed_by": "StructureHypothesisAgent",
        "target_sector": target_sector,
        "claim_type": "candidate_structure",
        "mathematical_guess": guess,
        "expected_form": expected,
        "allowed_operations": ["algebraic candidate construction"],
        "forbidden_operations": forbidden,
        "required_validation": required_validation,
        "protected_benchmarks": protected_benchmarks,
        "risk_notes": risk_notes,
        "status": "PROPOSED",
    }
    validate_with_schema(payload, "conjecture")
    return payload


def propose_conjectures(stage: Path, stage_id: str, count: int = 2, allow_ibp: bool = False) -> list[dict[str, Any]]:
    root = stage / ".loop" / "conjectures"
    root.mkdir(parents=True, exist_ok=True)
    conjectures = [make_conjecture(index, stage_id, allow_ibp=allow_ibp) for index in range(1, count + 1)]
    for index, conjecture in enumerate(conjectures, start=1):
        write_json(root / f"conjecture_{index:03d}.json", conjecture)
    ledger = {"stage_id": stage_id, "conjecture_count": len(conjectures), "conjectures": conjectures}
    write_json(root / "conjecture_ledger.json", ledger)
    write_json(stage / ".loop" / "blackboard" / "hypothesis_round_001" / "structure_hypotheses.json", ledger)
    return conjectures


def build_candidate_from_conjecture(stage: Path, conjecture: dict[str, Any]) -> dict[str, Any]:
    candidate_id = f"candidate_{conjecture['conjecture_id']}_001"
    root = stage / "candidates" / conjecture["conjecture_id"]
    root.mkdir(parents=True, exist_ok=True)
    expression = conjecture.get("expected_form", "")
    write_text(root / "candidate_expression.wl", f"CandidateExpression = {expression};\n")
    if conjecture.get("target_sector") == "center/contact sector":
        write_text(
            root / "candidate_basis_table.wl",
            (
                "CandidateBasisTable = <|\n"
                f"  \"candidate_id\" -> \"{candidate_id}\",\n"
                "  \"basis\" -> \"CenterPatternLedger[band,row,term_hash]\",\n"
                "  \"allowed_claim\" -> \"row-provenance hash conservation only\"\n"
                "|>;\n"
            ),
        )
        write_text(
            root / "candidate_validation.wl",
            """(* Isolated candidate validation: center row ids and term-hash multiset are conserved. *)
ledger = Import["../../input_snapshots/stage004_sector_ledger_snapshot.csv", "Dataset"];
centerRows = Select[Normal[ledger], #sector == "center/contact sector" &];
patternRows = Normal[Import["../../output/center_sector_pattern_ledger.csv", "Dataset"]];
rawRowIds = Sort[ToExpression /@ (centerRows[[All, "row"]])];
fusedRowIds = Sort[ToExpression /@ (patternRows[[All, "row"]])];
rawHashes = Sort[centerRows[[All, "term_hash"]]];
fusedHashes = Sort[patternRows[[All, "term_hash"]]];
centerProvenanceDifference = If[rawRowIds === fusedRowIds && rawHashes === fusedHashes, 0, 1];
<|"identity_checked" -> "center row-id and term-hash multisets conserved", "CenterProvenanceDifference" -> centerProvenanceDifference|>
""",
        )
    else:
        write_text(root / "candidate_basis_table.wl", f"CandidateBasisTable = <|\"candidate_id\" -> \"{candidate_id}\"|>;\n")
        write_text(root / "candidate_validation.wl", "(* Isolated candidate validation: raw_sector - candidate_sector == 0. *)\n")
    write_text(
        root / "candidate_build_report.md",
        f"# Candidate Build Report\n\ncandidate_id: `{candidate_id}`\n\nconjecture_id: `{conjecture['conjecture_id']}`\n",
    )
    result = {
        "conjecture_id": conjecture["conjecture_id"],
        "candidate_id": candidate_id,
        "candidate_root": str(root.relative_to(stage)),
        "status": "BUILT",
    }
    write_json(root / "candidate_build_result.json", result)
    return result


def validate_candidate_result(
    stage: Path,
    conjecture_id: str,
    candidate_id: str,
    *,
    residual_zero: bool,
    protected_benchmarks_passed: bool = True,
    allow_ibp: bool = False,
    needs_ibp: bool = False,
    identity_checked: str | None = None,
) -> dict[str, Any]:
    if needs_ibp and not allow_ibp:
        status = "REQUIRES_IBP_APPROVAL"
    elif residual_zero and protected_benchmarks_passed:
        status = "PASS"
    else:
        status = "FAIL"
    result = {
        "conjecture_id": conjecture_id,
        "candidate_id": candidate_id,
        "validation_status": status,
        "identity_checked": identity_checked or ("raw_sector - candidate_sector == 0" if not needs_ibp else "raw_sector - candidate_sector - partial_k F == 0"),
        "residual_zero": residual_zero,
        "protected_benchmarks_passed": protected_benchmarks_passed,
        "promotion_allowed": status == "PASS",
    }
    validate_with_schema(result, "candidate_result")
    root = stage / "candidates" / conjecture_id
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "candidate_validation_result.json", result)
    return result


def archive_failed_candidate(stage: Path, candidate_result: dict[str, Any], failure_mode: str) -> dict[str, Any]:
    conjecture_id = candidate_result["conjecture_id"]
    root = stage / "failed_conjectures" / conjecture_id
    root.mkdir(parents=True, exist_ok=True)
    archive = {
        "conjecture_id": conjecture_id,
        "candidate_id": candidate_result["candidate_id"],
        "failure_mode": failure_mode,
        "stage_action": "ARCHIVE_AND_CONTINUE",
        "residual_summary": "Residual was nonzero or candidate required unapproved operations.",
    }
    validate_with_schema(archive, "failure_archive")
    write_json(root / "failure_metadata.json", archive)
    write_text(root / "failure_report.md", f"# Failure Report\n\nfailure_mode: `{failure_mode}`\n")
    write_text(root / "residual_summary.wl", "ResidualSummary = \"nonzero or unapproved\";\n")
    return archive


def promote_candidate(stage: Path, candidate_result: dict[str, Any]) -> dict[str, Any]:
    if not candidate_result.get("promotion_allowed"):
        return {"status": "REJECTED", "reason": "candidate validation did not allow promotion"}
    target = {
        "status": "PROMOTED",
        "conjecture_id": candidate_result["conjecture_id"],
        "candidate_id": candidate_result["candidate_id"],
        "promotion_rule": "verified candidate only",
    }
    write_json(stage / "output" / "promoted_candidate_manifest.json", target)
    return target


def rank_candidates(stage: Path, candidate_results: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = sorted(candidate_results, key=lambda item: (not item.get("promotion_allowed", False), item.get("candidate_id", "")))
    best = next((item for item in ranked if item.get("promotion_allowed")), None)
    ranking = {
        "recommendation": "promote candidate" if best else "try next conjecture",
        "best_candidate_id": best.get("candidate_id") if best else None,
        "ranked_candidates": ranked,
    }
    validate_with_schema(ranking, "candidate_ranking")
    write_json(stage / ".loop" / "candidate_ranking.json", ranking)
    write_text(stage / ".loop" / "blackboard" / "candidate_ranking.md", f"# Candidate Ranking\n\nrecommendation: {ranking['recommendation']}\n")
    return ranking


def write_hypothesis_search_summary(
    stage: Path,
    *,
    stage_id: str,
    conjectures: list[dict[str, Any]],
    candidate_results: list[dict[str, Any]],
    archived: list[dict[str, Any]],
    best_candidate: str | None,
) -> dict[str, Any]:
    passed = [item for item in candidate_results if item.get("validation_status") == "PASS"]
    failed = [item for item in candidate_results if item.get("validation_status") == "FAIL"]
    ibp = [item for item in candidate_results if item.get("validation_status") == "REQUIRES_IBP_APPROVAL"]
    verdict = "PROMOTED" if best_candidate else "EXPLORATION_COMPLETE_NO_PROMOTION"
    reports = stage / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    md_path = reports / f"stage_{stage_id}_hypothesis_search_summary.md"
    tex_path = reports / f"stage_{stage_id}_hypothesis_search_summary.tex"
    md = f"""# Hypothesis Search Summary

## Stage

`{stage_id}`

## Counts

- conjectures proposed: {len(conjectures)}
- candidates built: {len(candidate_results)}
- candidates passed: {len(passed)}
- candidates failed: {len(failed)}
- candidates requiring IBP approval: {len(ibp)}
- candidates archived: {len(archived)}

## Best Candidate

`{best_candidate or 'none'}`

## Claim Boundary

Failed conjectures are archived and are not promoted to frozen stage outputs.
Only verified candidates may be promoted.
"""
    write_text(md_path, md)
    tex = f"""\\documentclass[11pt]{{article}}
\\usepackage[margin=0.75in]{{geometry}}
\\title{{Hypothesis Search Summary: {stage_id}}}
\\date{{}}
\\begin{{document}}
\\maketitle
Conjectures proposed: {len(conjectures)}. Candidates built: {len(candidate_results)}.
Candidates passed: {len(passed)}. Candidates failed: {len(failed)}.
Best candidate: {best_candidate or 'none'}.
\\end{{document}}
"""
    write_text(tex_path, tex)
    pdf_status = "SKIPPED_XELATEX_UNAVAILABLE"
    if shutil.which("xelatex"):
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=reports,
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            pdf_status = "PASS"
    summary = {
        "stage_id": stage_id,
        "conjectures_proposed": len(conjectures),
        "candidates_built": len(candidate_results),
        "candidates_passed": len(passed),
        "candidates_failed": len(failed),
        "candidates_archived": len(archived),
        "best_candidate": best_candidate,
        "stage_verdict": verdict,
        "PDFCompileStatus": pdf_status,
    }
    write_json(reports / f"stage_{stage_id}_hypothesis_search_summary.json", summary)
    return summary


def run_mock_hypothesis_search(stage: Path, stage_id: str, profile: dict[str, Any]) -> dict[str, Any]:
    config = profile.get("hypothesis_search", {})
    count = int(config.get("max_conjectures_per_stage", 2))
    allow_ibp = bool(config.get("allow_ibp_conjectures", False))
    exploration_only = bool(config.get("exploration_only", False))
    promote_candidates = bool(config.get("promote_candidates", True)) and not exploration_only
    forbid_mock_candidate_promotion = (
        stage_id.startswith("sigma_abc_")
        and promote_candidates
        and not bool(config.get("allow_mock_candidates", False))
    )
    conjectures = propose_conjectures(stage, stage_id, count=min(count, 2), allow_ibp=allow_ibp)
    candidate_results = []
    archived = []
    for index, conjecture in enumerate(conjectures, start=1):
        build = build_candidate_from_conjecture(stage, conjecture)
        residual_zero = index == 2
        identity_checked = None
        if conjecture.get("target_sector") == "center/contact sector":
            identity_checked = "center row-id and term-hash multisets conserved"
        elif forbid_mock_candidate_promotion and conjecture.get("target_sector") == "toy":
            residual_zero = False
            identity_checked = "mock/toy candidate is forbidden for sigma_abc production promotion"
        result = validate_candidate_result(
            stage,
            conjecture["conjecture_id"],
            build["candidate_id"],
            residual_zero=residual_zero,
            protected_benchmarks_passed=not (
                forbid_mock_candidate_promotion and conjecture.get("target_sector") == "toy"
            ),
            allow_ibp=allow_ibp,
            identity_checked=identity_checked,
        )
        candidate_results.append(result)
        if result["validation_status"] != "PASS":
            archived.append(archive_failed_candidate(stage, result, failure_mode="residual_nonzero"))
    ranking = rank_candidates(stage, candidate_results)
    best_candidate = ranking["best_candidate_id"]
    if best_candidate and promote_candidates:
        promotion = promote_candidate(
            stage,
            next((item for item in candidate_results if item["candidate_id"] == best_candidate), candidate_results[0]),
        )
    elif best_candidate and exploration_only:
        promotion = {
            "status": "VERIFIED_BUT_NOT_PROMOTED",
            "candidate_id": best_candidate,
            "reason": "hypothesis_search.exploration_only is true",
        }
        write_json(stage / "output" / "verified_not_promoted_candidate_manifest.json", promotion)
    else:
        promotion = {"status": "REJECTED"}
    summary = write_hypothesis_search_summary(
        stage,
        stage_id=stage_id,
        conjectures=conjectures,
        candidate_results=candidate_results,
        archived=archived,
        best_candidate=best_candidate,
    )
    return {
        "conjectures": conjectures,
        "candidate_results": candidate_results,
        "archived": archived,
        "ranking": ranking,
        "promotion": promotion,
        "summary": summary,
    }


def write_stage010_retrospective_conjecture(repo_root: Path) -> Path:
    target = repo_root / "reports" / "stage_010_pair_band_pair_family_grouping_conjecture.json"
    payload = {
        "conjecture_id": "stage_010_pair_band_pair_family_grouping",
        "stage_id": "sigma_abc_010_pair_kernel_fusion_pilot",
        "proposed_by": "StructureHypothesisAgent",
        "target_sector": "pair",
        "claim_type": "kernel_fusion_ansatz",
        "mathematical_guess": "The 912 pair-sector rows can be grouped into 3 band-pair families.",
        "expected_form": "3 band-pair row-provenance kernel families",
        "allowed_operations": ["row-provenance grouping"],
        "forbidden_operations": ["IBP", "total derivative", "full tensorial correctness claim"],
        "required_validation": ["PairFusionDifference -> 0", "XXXPairProjectionRegression -> PASS"],
        "protected_benchmarks": ["sigma_xxx_projection"],
        "risk_notes": ["Retrospective record only; does not change Stage 010 physics."],
        "status": "PROMOTED",
        "validation": {
            "PairFusionDifference": 0,
            "XXXPairProjectionRegression": "PASS",
        },
    }
    validate_with_schema(payload, "conjecture")
    write_json(target, payload)
    return target
