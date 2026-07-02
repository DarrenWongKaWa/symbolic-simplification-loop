from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from .config import read_json, utc_now, write_json
from .human_signoff import load_signoff
from .schemas import validate_with_schema
from .state import freeze_preconditions


IGNORE_SUFFIXES = {".aux", ".log", ".out", ".toc"}
IGNORE_NAMES = {"__pycache__", ".DS_Store"}


def file_record(path: Path, root: Path) -> dict:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": str(path.relative_to(root)),
        "bytes": path.stat().st_size,
        "sha256": digest,
    }


def collect_stage_files(stage: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(stage.rglob("*")):
        if not path.is_file():
            continue
        if path.name in IGNORE_NAMES or path.suffix in IGNORE_SUFFIXES:
            continue
        records.append(file_record(path, stage))
    return records


def build_checkpoint_manifest(stage: Path) -> dict:
    validation = read_json(stage / ".loop" / "validation_summary.json")
    review = read_json(stage / ".loop" / "review_result.json")
    metrics_path = stage / ".loop" / "metrics.json"
    metrics = read_json(metrics_path) if metrics_path.exists() else {}
    meta_path = stage / ".loop" / "meta_review_result.json"
    meta_review = read_json(meta_path) if meta_path.exists() else None
    review_quality_path = stage / ".loop" / "review_quality.json"
    review_quality = read_json(review_quality_path) if review_quality_path.exists() else None
    review_debt_path = stage / ".loop" / "review_debt.json"
    review_debt = read_json(review_debt_path) if review_debt_path.exists() else None
    completion_matrix_path = stage / "reports" / "completion_matrix.json"
    completion_matrix = read_json(completion_matrix_path) if completion_matrix_path.exists() else None
    human_signoff = load_signoff(stage)
    pre_run_brief_path = stage / ".loop" / "pre_run_brief.json"
    pre_run_brief = read_json(pre_run_brief_path) if pre_run_brief_path.exists() else None
    pre_run_gate_path = stage / ".loop" / "pre_run_gate_result.json"
    pre_run_gate = read_json(pre_run_gate_path) if pre_run_gate_path.exists() else None
    scientific_identities_path = stage / ".loop" / "scientific_identities.json"
    scientific_identities = read_json(scientific_identities_path) if scientific_identities_path.exists() else None
    identity_traceability_path = stage / ".loop" / "identity_traceability.json"
    identity_traceability = read_json(identity_traceability_path) if identity_traceability_path.exists() else None
    digest_paths = [
        stage / ".loop" / "meta_review_result.json",
        stage / ".loop" / f"{stage.name}_meta_review.json",
        stage / ".loop" / "review_quality.json",
        stage / "reports" / "human_readable_review.md",
        stage / "reports" / f"{stage.name}_human_review.md",
        stage / "reports" / f"{stage.name}_review_quality.md",
        stage / "reports" / "stage_summary.md",
        stage / "reports" / "stage_summary.tex",
        stage / "reports" / "stage_summary.pdf",
        stage / "reports" / f"{stage.name}_summary.md",
        stage / "reports" / f"{stage.name}_summary.tex",
        stage / "reports" / f"{stage.name}_summary.pdf",
        stage / "reports" / "stage_summary_build.json",
        stage / ".loop" / "pre_run_brief.json",
        stage / ".loop" / "pre_run_gate_result.json",
        stage / ".loop" / "scientific_identities.json",
        stage / ".loop" / "identity_traceability.json",
        stage / "reports" / "agent_self_understanding.md",
        stage / "reports" / "identity_traceability.md",
        stage / ".loop" / "review_quality.json",
    ]
    stage_digest_artifacts = [
        str(path.relative_to(stage)) for path in digest_paths if path.exists()
    ]

    manifest = {
        "stage_name": stage.name,
        "timestamp": utc_now(),
        "input_snapshots": sorted(str(p.relative_to(stage)) for p in (stage / "input_snapshots").rglob("*") if p.is_file()) if (stage / "input_snapshots").exists() else [],
        "output_artifacts": sorted(str(p.relative_to(stage)) for p in (stage / "output").rglob("*") if p.is_file()) if (stage / "output").exists() else [],
        "validation_summary": validation,
        "review_result": review,
        "allowed_claims": review.get("allowed_claims", []),
        "forbidden_claims": review.get("forbidden_claims", []),
        "metrics": metrics,
        "known_caveats": review.get("nonblocking_caveats", []) + validation.get("caveats", []),
        "files": collect_stage_files(stage),
        "meta_review_result": meta_review,
        "review_quality": review_quality,
        "review_debt": review_debt,
        "completion_matrix": "reports/completion_matrix.json" if completion_matrix_path.exists() else None,
        "completion_matrix_result": completion_matrix,
        "human_signoff": ".loop/human_signoff.yaml" if human_signoff is not None else None,
        "human_signoff_ledger": ".loop/human_signoff_ledger.jsonl" if (stage / ".loop" / "human_signoff_ledger.jsonl").exists() else None,
        "human_signoff_decision": human_signoff.get("decision") if human_signoff else None,
        "accepted_caveats": human_signoff.get("accepted_caveats", []) if human_signoff else [],
        "human_signoff_basis_hashes": human_signoff.get("basis_hashes", {}) if human_signoff else {},
        "pre_run_brief": ".loop/pre_run_brief.json" if pre_run_brief_path.exists() else None,
        "pre_run_gate_result": pre_run_gate,
        "scientific_identities": ".loop/scientific_identities.json" if scientific_identities_path.exists() else None,
        "identity_traceability": ".loop/identity_traceability.json" if identity_traceability_path.exists() else None,
        "identity_traceability_result": identity_traceability,
        "stage_digest_artifacts": stage_digest_artifacts,
    }
    validate_with_schema(validation, "validation_summary")
    validate_with_schema(review, "review_result")
    if meta_review is not None:
        validate_with_schema(meta_review, "meta_review_result")
    if review_quality is not None:
        validate_with_schema(review_quality, "review_quality")
    if review_debt is not None:
        validate_with_schema(review_debt, "review_debt")
    if completion_matrix is not None:
        validate_with_schema(completion_matrix, "completion_matrix")
    if human_signoff is not None:
        validate_with_schema(human_signoff, "human_signoff")
    if pre_run_brief is not None:
        validate_with_schema(pre_run_brief, "pre_run_brief")
    if pre_run_gate is not None:
        validate_with_schema(pre_run_gate, "pre_run_gate_result")
    if scientific_identities is not None:
        validate_with_schema(scientific_identities, "scientific_identity_library")
    if identity_traceability is not None:
        validate_with_schema(identity_traceability, "identity_traceability")
    validate_with_schema(manifest, "checkpoint_manifest")
    write_json(stage / ".loop" / "checkpoint_manifest.json", manifest)
    return manifest


def freeze_checkpoint(stage: Path, checkpoints_root: Path | None = None) -> Path:
    manifest = build_checkpoint_manifest(stage)
    validation = manifest["validation_summary"]
    review = manifest["review_result"]
    missing = freeze_preconditions(stage, validation, review)
    if missing:
        # Patch (Loop Skill / Repo Integration Patch): if any
        # freeze precondition is unsatisfied, the build side of
        # build_checkpoint_manifest may have already written
        # ``.loop/checkpoint_manifest.json``. Per the
        # ``$symbolic-simplification-loop`` invariant, that
        # artefact is only valid when freeze is allowed; remove
        # it now before raising. This is the minimal safe fix
        # — a larger refactor can later split manifest
        # construction from manifest writing.
        manifest_path = stage / ".loop" / "checkpoint_manifest.json"
        if manifest_path.exists():
            manifest_path.unlink()
        raise RuntimeError("Cannot freeze checkpoint: " + "; ".join(missing))

    checkpoints_root = checkpoints_root or stage.parents[1] / "checkpoints"
    target = checkpoints_root / f"{stage.name}_{manifest['timestamp'].replace(':', '-')}"
    if target.exists():
        raise FileExistsError(target)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            path = Path(name)
            if name in IGNORE_NAMES or path.suffix in IGNORE_SUFFIXES:
                ignored.add(name)
        return ignored

    shutil.copytree(stage, target, ignore=ignore)
    return target
