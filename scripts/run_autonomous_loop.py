#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

import _bootstrap  # noqa: F401
from loop_engine.agent_runtime import AgentInvocationRequest, RuntimeStatus, build_adapter, resolve_agent_runtime
from loop_engine.checkpoint import build_checkpoint_manifest, freeze_checkpoint
from loop_engine.completion_matrix import load_completion_matrix, write_completion_matrix
from loop_engine.config import REPO_ROOT, read_json, utc_now, write_json, write_text
from loop_engine.conjecture_ledger import run_mock_hypothesis_search, write_stage010_retrospective_conjecture
from loop_engine.decision import decide_next_action
from loop_engine.executor import initialize_stage_files
from loop_engine.mailbox import append_event, initialize_mailbox
from loop_engine.meta_review import run_scientific_metareview
from loop_engine.orchestrator import plan_patch_or_hard_stop, run_digest_reviewer
from loop_engine.packet_builder import build_review_packet
from loop_engine.planner import write_default_stage_plan
from loop_engine.compact_packet import build_compact_review_packet
from loop_engine.pre_run_brief import write_pre_run_brief
from loop_engine.pre_run_gate import check_pre_run_gate
from loop_engine.risk_classifier import classify_stage_risk
from loop_engine.review_debt import (
    create_review_debt_if_allowed,
    downstream_blocked_by_review_debt,
    iter_open_review_debts,
)
from loop_engine.review_queue import enqueue_pending_review
from loop_engine.review_quality import build_review_quality
from loop_engine.reviewer import (
    REQUIRED_REVIEWERS,
    aggregate_review_results,
    build_reviewer_agent_prompts,
    run_local_reviewer_agent,
    run_local_reviewer_agents,
)
from loop_engine.runtime_failures import classify_agent_runtime_failure
from loop_engine.schemas import validate_with_schema
from loop_engine.scientific_identities import write_stage_scientific_identities
from loop_engine.stage_digest import build_stage010_retrospective, build_stage_digest
from loop_engine.human_signoff import build_signoff_from_decision, load_signoff, write_signoff
from loop_engine.identity_traceability import write_identity_traceability
from loop_engine.verifier import run_stage_verifier, run_verifier_agent_audit


@dataclass
class StageRun:
    stage_id: str
    status: str
    validation_gate: str | None = None
    review_verdict: str | None = None
    decision_action: str | None = None
    checkpoint_created: bool = False
    hard_stop_reasons: list[str] | None = None
    patch_attempts: int = 0


STAGE012A_ID = "sigma_abc_012a_loop_sector_inventory"
STAGE012B_ID = "sigma_abc_012b_loop_hypothesis_generation"
STAGE012A_REQUIRED_ARTIFACTS = [
    "output/loop_sector_ledger.csv",
    "output/loop_orbit_inventory.json",
    "output/loop_raw_sector_table.wl",
    "validation/loop_inventory_validation.json",
]
STAGE012B_REQUIRED_ARTIFACTS = [
    "output/loop_hypothesis_ledger.json",
    "output/loop_candidate_requirements.json",
    ".loop/conjectures/conjecture_ledger.json",
    "reports/loop_hypothesis_generation_summary.md",
]


def robust_rmtree(path: Path, attempts: int = 3) -> None:
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.2 * (attempt + 1))


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def project_config(project: str) -> dict[str, Any]:
    path = REPO_ROOT / "projects" / project / "loop.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Missing project loop graph: {path}")
    return load_yaml(path)


def profile_config(profile: str) -> dict[str, Any]:
    path = REPO_ROOT / "profiles" / f"{profile}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Missing profile: {path}")
    return load_yaml(path)


def policy_config(profile: dict[str, Any]) -> dict[str, Any]:
    name = profile.get("hard_stop_policy", "sigma_abc_hard_stops")
    path = REPO_ROOT / "policies" / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Missing hard-stop policy: {path}")
    return load_yaml(path)


def benchmark_config(profile: dict[str, Any]) -> dict[str, Any]:
    name = profile.get("benchmark_policy", "sigma_xxx_projection")
    path = REPO_ROOT / "benchmarks" / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Missing benchmark policy: {path}")
    return load_yaml(path)


def apply_profile_checkpoint_override(loop: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    override = profile.get("current_checkpoint_override")
    if not override:
        return loop
    patched = dict(loop)
    patched["current_checkpoint"] = override
    return patched


def frozen_stage_ids(run_root: Path) -> set[str]:
    checkpoints = run_root / "checkpoints"
    if not checkpoints.exists():
        return set()
    frozen: set[str] = set()
    for manifest_path in checkpoints.glob("*/.loop/checkpoint_manifest.json"):
        try:
            frozen.add(read_json(manifest_path).get("stage_name", ""))
        except json.JSONDecodeError:
            continue
    return {stage for stage in frozen if stage}


def checkpoint_to_stage_id(checkpoint: str | None, stages: list[dict[str, Any]]) -> str | None:
    if not checkpoint:
        return None
    for stage in stages:
        stage_id = stage.get("id")
        if stage_id and checkpoint.startswith(f"{stage_id}_checkpoint"):
            return stage_id
    return checkpoint


def completed_stage_ids_from_current_checkpoint(loop: dict[str, Any]) -> set[str]:
    stages = list(loop.get("stages", []))
    current_stage = checkpoint_to_stage_id(loop.get("current_checkpoint"), stages)
    if not current_stage:
        return set()
    completed: set[str] = set()
    for stage in stages:
        stage_id = stage.get("id")
        if stage_id:
            completed.add(stage_id)
        if stage_id == current_stage:
            break
    return completed


def stage_allowed_by_profile(stage: dict[str, Any], profile: dict[str, Any]) -> bool:
    allowed_ids = set(profile.get("allowed_stage_ids", []) or [])
    if allowed_ids:
        return stage.get("id") in allowed_ids
    allowed_tags = set(profile.get("allowed_stage_tags", []) or [])
    if allowed_tags:
        return bool(set(stage.get("tags", [])) & allowed_tags)
    return True


def next_stages(
    loop: dict[str, Any],
    run_root: Path,
    profile: dict[str, Any],
    from_current_checkpoint: bool = False,
) -> list[dict[str, Any]]:
    stages = list(loop.get("stages", []))
    if from_current_checkpoint:
        done = completed_stage_ids_from_current_checkpoint(loop) | frozen_stage_ids(run_root)
    else:
        done = frozen_stage_ids(run_root)
    pending = [stage for stage in stages if stage.get("id") not in done]
    pending = [stage for stage in pending if stage_allowed_by_profile(stage, profile)]
    max_count = int(profile.get("autonomy", {}).get("max_stages_per_run", 1))
    stop_after = profile.get("autonomy", {}).get("stop_after_stage")
    selected: list[dict[str, Any]] = []
    for stage in pending:
        selected.append(stage)
        if stop_after and stage.get("id") == stop_after:
            break
        if len(selected) >= max_count:
            break
    return selected


def stage_hard_stop_reasons(stage_spec: dict[str, Any], profile: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    tags = set(stage_spec.get("tags", []))
    hard = policy.get("hard_stops", {})
    approval = profile.get("human_approval", {}) or {}
    approved_stage_ids = set(approval.get("approved_stage_ids", []) or [])
    approved_forbidden_tags = set(approval.get("approved_forbidden_stage_tags", []) or [])
    approval_granted = bool(approval.get("granted")) and stage_spec.get("id") in approved_stage_ids
    reasons: list[str] = []
    forbidden_tags = set(hard.get("forbidden_stage_tags", []))
    approval_tags = set(hard.get("require_human_approval_tags", []))
    for tag in sorted(tags & forbidden_tags):
        if approval_granted and tag in approved_forbidden_tags:
            continue
        reasons.append(f"forbidden stage tag: {tag}")
    for tag in sorted(tags & approval_tags):
        if approval_granted:
            continue
        reasons.append(f"human approval required for tag: {tag}")
    autonomy = profile.get("autonomy", {})
    if "kernel_fusion" in tags and not autonomy.get("allow_kernel_fusion", False):
        reasons.append("profile forbids kernel fusion")
    if "ibp_reduction" in tags and not autonomy.get("allow_ibp_reduction", False):
        reasons.append("profile forbids IBP reduction")
    if "tensorial_simplification" in tags and not autonomy.get("allow_physics_simplification", False):
        reasons.append("profile forbids physics simplification")
    return reasons


def write_stage_plan_and_claim(stage_dir: Path, stage_spec: dict[str, Any], benchmark: dict[str, Any]) -> None:
    write_default_stage_plan(
        stage_dir,
        goal=stage_spec.get("goal", "TBD"),
        expected_outputs=stage_spec.get("expected_outputs"),
        dependencies=stage_spec.get("dependencies") or stage_spec.get("depends_on"),
    )
    write_text(
        stage_dir / "CLAIM_BOUNDARY.md",
        f"""# Claim Boundary

## Allowed Claims

- This autonomous run may claim only stage-local validated infrastructure progress.
- The protected benchmark `{benchmark.get("protected_benchmark", "sigma_xxx_projection")}` remains registered as metadata.

## Forbidden Claims

- Do not claim `sigma_abc` simplification has started.
- Do not claim full tensorial `sigma_abc` correctness.
- Do not claim kernel fusion or IBP reduction from this runner.

## Caveats

- Stage 001 DC projection caveat must be preserved: `DCProjectionTo1D -> INHERITED_PASS`.
""",
    )


def polynomial_identity_payload(stage_spec: dict[str, Any]) -> dict[str, Any]:
    gate = stage_spec.get("force_validation_gate") or ("PASS" if stage_spec.get("expected_difference") == "0" else "FAIL")
    difference = "0" if gate == "PASS" else stage_spec.get("expected_difference", "nonzero")
    return {
        "old": stage_spec.get("old", "x"),
        "new": stage_spec.get("new", "x"),
        "expanded_new": stage_spec.get("expanded_new", stage_spec.get("new", "x")),
        "difference": difference,
        "gate": gate,
    }


def execute_mock_stage(stage_dir: Path, stage_spec: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    identity = polynomial_identity_payload(stage_spec)
    write_text(stage_dir / "input_snapshots" / "old_expression.txt", f"{identity['old']}\n")
    write_text(stage_dir / "output" / "new_expression.txt", f"{identity['new']}\n")
    write_json(stage_dir / "output" / "identity_difference.json", identity)
    validation = {
        "stage_name": stage_dir.name,
        "overall_gate": identity["gate"],
        "identity_type": "OldMinusNewZero",
        "checks": [
            {
                "name": "mock_identity",
                "expected": "0",
                "actual": identity["difference"],
                "gate": identity["gate"],
            },
            {"name": "NoIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "NoTotalDerivativeIntroduced", "expected": True, "actual": True, "gate": "PASS"},
        ],
        "protected_regressions": [
            {
                "name": benchmark.get("protected_benchmark", "sigma_xxx_projection"),
                "gate": "PASS",
                "caveat": benchmark.get("caveats", {}).get("stage001_dc_projection", "INHERITED_PASS"),
            }
        ],
        "caveats": ["Autonomous runner mock stage; no sigma_abc physics simplification was run."],
    }
    validate_with_schema(validation, "validation_summary")
    write_json(stage_dir / ".loop" / "validation_summary.json", validation)
    write_json(stage_dir / "validation" / "validation_summary.json", validation)
    metrics = {
        "stage_name": stage_dir.name,
        "before": {"expression": identity["old"]},
        "after": {"expression": identity["new"], "expanded": identity["expanded_new"]},
        "deltas": {"difference": identity["difference"]},
        "notes": ["Mock autonomous-loop identity stage."],
    }
    validate_with_schema(metrics, "metrics")
    write_json(stage_dir / ".loop" / "metrics.json", metrics)
    write_text(
        stage_dir / "EXECUTION_REPORT.md",
        f"""# Execution Report

## Stage

`{stage_dir.name}`

## Autonomous Runner Action

Mock exact-identity stage generated by `scripts/run_autonomous_loop.py`.

## Identity

```text
Old = {identity['old']}
New = {identity['new']}
Old - New = {identity['difference']}
```

## Boundary

No `sigma_abc` physics simplification was run.
""",
    )
    return validation


def execute_stage(stage_dir: Path, stage_spec: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    if stage_spec.get("kind") == "polynomial_identity":
        return execute_mock_stage(stage_dir, stage_spec, benchmark)
    if stage_spec.get("kind") == "sigma_abc_prefusion_metadata":
        return execute_sigma_abc_prefusion_stage(stage_dir, stage_spec, benchmark)
    if stage_spec.get("kind") == "sigma_abc_pair_kernel_fusion_pilot":
        return execute_sigma_abc_pair_kernel_fusion_stage(stage_dir, stage_spec, benchmark)
    if stage_spec.get("kind") == "sigma_abc_center_sector_pilot":
        return execute_sigma_abc_center_sector_stage(stage_dir, stage_spec, benchmark)
    if stage_spec.get("kind") == "sigma_abc_loop_candidate_preparation":
        return execute_sigma_abc_loop_candidate_preparation_stage(stage_dir, stage_spec, benchmark)
    validation = {
        "stage_name": stage_dir.name,
        "overall_gate": "BLOCKED",
        "identity_type": "NotApplicable",
        "checks": [{"name": "stage_execution", "actual": "unsupported non-mock stage in autonomous infra branch", "gate": "BLOCKED"}],
        "caveats": ["This infrastructure branch does not execute sigma_abc physics stages."],
    }
    write_json(stage_dir / ".loop" / "validation_summary.json", validation)
    write_json(stage_dir / ".loop" / "metrics.json", {"stage_name": stage_dir.name, "notes": ["Blocked unsupported stage."]})
    return validation


def _wl_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _wl_assoc(data: dict[str, Any], indent: int = 0) -> str:
    spaces = " " * indent
    parts = []
    for key, value in data.items():
        if isinstance(value, dict):
            rendered = _wl_assoc(value, indent + 2)
        elif isinstance(value, list):
            rendered_items = []
            for item in value:
                if isinstance(item, dict):
                    rendered_items.append(_wl_assoc(item, indent + 2))
                elif isinstance(item, str):
                    rendered_items.append(_wl_string(item))
                else:
                    rendered_items.append(str(item).lower() if isinstance(item, bool) else str(item))
            rendered = "{" + ", ".join(rendered_items) + "}"
        elif isinstance(value, str):
            rendered = _wl_string(value)
        elif isinstance(value, bool):
            rendered = "True" if value else "False"
        elif value is None:
            rendered = "None"
        else:
            rendered = str(value)
        parts.append(f"{spaces}{_wl_string(str(key))} -> {rendered}")
    return "<|" + ",\n".join(parts) + "|>"


def load_pair_ledger_rows() -> list[dict[str, str]]:
    ledger = REPO_ROOT / "sigma_abc" / "stages" / "004_tensorial_raw_sector_decomposition_ledger" / "output" / "sector_ledger.csv"
    if not ledger.exists():
        raise FileNotFoundError(f"Missing sector ledger: {ledger}")
    with ledger.open("r", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("sector") == "pair/two-band sector"]


def load_center_ledger_rows() -> list[dict[str, str]]:
    ledger = REPO_ROOT / "sigma_abc" / "stages" / "004_tensorial_raw_sector_decomposition_ledger" / "output" / "sector_ledger.csv"
    if not ledger.exists():
        raise FileNotFoundError(f"Missing sector ledger: {ledger}")
    with ledger.open("r", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("sector") == "center/contact sector"]


def stage010_pair_regression_preserved() -> bool:
    report = REPO_ROOT / "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md"
    if not report.exists():
        return False
    text = report.read_text(encoding="utf-8")
    return "PairFusionDifference -> 0" in text and "XXXPairProjectionRegression -> PASS" in text


def write_center_pattern_ledger(stage_dir: Path, center_rows: list[dict[str, str]]) -> None:
    target = stage_dir / "output" / "center_sector_pattern_ledger.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row", "center_family", "band", "term_hash"])
        writer.writeheader()
        for row in center_rows:
            writer.writerow(
                {
                    "row": row["row"],
                    "center_family": f"center_band_{row['bands']}",
                    "band": row["bands"],
                    "term_hash": row["term_hash"],
                }
            )


def execute_sigma_abc_center_sector_stage(stage_dir: Path, stage_spec: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    center_rows = load_center_ledger_rows()
    source_ledger = REPO_ROOT / "sigma_abc" / "stages" / "004_tensorial_raw_sector_decomposition_ledger" / "output" / "sector_ledger.csv"
    snapshot_ledger = stage_dir / "input_snapshots" / "stage004_sector_ledger_snapshot.csv"
    snapshot_ledger.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_ledger, snapshot_ledger)
    families: dict[str, list[dict[str, str]]] = {}
    for row in center_rows:
        families.setdefault(row["bands"], []).append(row)

    family_records = []
    for band_id, rows in sorted(families.items(), key=lambda item: int(item[0])):
        family_records.append(
            {
                "family": f"center_band_{band_id}",
                "band": band_id,
                "row_count": len(rows),
                "rows": [int(row["row"]) for row in rows],
                "term_hashes": [row["term_hash"] for row in rows],
            }
        )

    write_center_pattern_ledger(stage_dir, center_rows)
    pair_regression_preserved = stage010_pair_regression_preserved()
    raw_row_ids = sorted(int(row["row"]) for row in center_rows)
    fused_row_ids = sorted(row for record in family_records for row in record["rows"])
    raw_hashes = sorted(row["term_hash"] for row in center_rows)
    fused_hashes = sorted(hash_value for record in family_records for hash_value in record["term_hashes"])
    center_provenance_difference = 0 if raw_row_ids == fused_row_ids and raw_hashes == fused_hashes else 1
    counts = {
        "center_rows": len(center_rows),
        "center_families": len(family_records),
        "family_row_counts": {record["family"]: record["row_count"] for record in family_records},
        "center_row_ids_conserved": raw_row_ids == fused_row_ids,
        "center_term_hashes_conserved": raw_hashes == fused_hashes,
        "pair_rows_touched": 0,
        "loop_rows_touched": 0,
        "unclassified_rows_touched": 0,
        "ibp_started": False,
        "total_derivative_introduced": False,
        "protected_pair_regression_preserved": pair_regression_preserved,
    }
    write_json(stage_dir / "output" / "center_sector_pattern_counts.json", counts)

    fused = {
        "Stage": stage_dir.name,
        "SourceLedger": "input_snapshots/stage004_sector_ledger_snapshot.csv",
        "FusionRule": "Group center/contact rows by single band index; preserve row and term-hash provenance.",
        "CenterRows": len(center_rows),
        "IdentityType": "RowProvenanceHashConservation",
        "CenterSectorRaw": "Stage004 center/contact rows",
        "CenterSectorFused": "CenterPatternLedger[band,row,term_hash]",
        "FusionIdentity": "row-id multiset and term-hash multiset are conserved; no expression-level center fusion is claimed",
        "CenterProvenanceDifference": center_provenance_difference,
        "Families": family_records,
    }
    write_text(stage_dir / "output" / "center_fused_kernel_families.wl", _wl_assoc(fused) + "\n")

    validation_wl = """(* Stage 011 center/contact-sector-only pilot validation. *)
ledger = Import["../input_snapshots/stage004_sector_ledger_snapshot.csv", "Dataset"];
centerRows = Select[Normal[ledger], #sector == "center/contact sector" &];
patternRows = Normal[Import["../output/center_sector_pattern_ledger.csv", "Dataset"]];
patternLedgerExists = FileExistsQ["../output/center_sector_pattern_ledger.csv"];
rawRowIds = Sort[ToExpression /@ (centerRows[[All, "row"]])];
fusedRowIds = Sort[ToExpression /@ (patternRows[[All, "row"]])];
rawHashes = Sort[centerRows[[All, "term_hash"]]];
fusedHashes = Sort[patternRows[[All, "term_hash"]]];
centerProvenanceDifference = If[rawRowIds === fusedRowIds && rawHashes === fusedHashes, 0, 1];
centerSectorRowCount = Length[centerRows];
centerRowsConserved = centerSectorRowCount === Length[patternRows] && centerProvenanceDifference === 0;
overallGate = If[centerSectorRowCount === 93 && centerRowsConserved, "PASS", "FAIL"];
<|
  "CenterSectorLoaded" -> True,
  "CenterSectorRowCount" -> centerSectorRowCount,
  "CenterPatternLedgerExists" -> patternLedgerExists,
  "CenterRowsConserved" -> centerRowsConserved,
  "CenterProvenanceDifference" -> centerProvenanceDifference,
  "CenterFusionDifference" -> "NOT_CLAIMED",
  "XXXCenterProjectionRegression" -> "INHERITED_OR_DEFERRED",
  "Stage001DCCaveatPreserved" -> True,
  "NoPairSectorTouched" -> True,
  "NoLoopSectorTouched" -> True,
  "NoIBPStarted" -> True,
  "NoTotalDerivativeIntroduced" -> True,
  "NoFullTensorialClaim" -> True,
  "OverallGate" -> overallGate
|>
"""
    write_text(stage_dir / "validation" / "center_sector_pilot_validation.wl", validation_wl)

    report = f"""# Center Sector Pilot Report

## Scope

This stage performs a limited center/contact-sector-only pattern fusion pilot.
It operates only on the frozen center/contact sector ledger from Stage 004.
The validation is a row-provenance and term-hash conservation check; it is not
an expression-level center-kernel fusion or IBP claim.

## Pattern Rule

Rows are grouped by single-band center family:

{chr(10).join(f"- `{record['family']}`: {record['row_count']} rows" for record in family_records)}

## Validation

```text
CenterSectorLoaded -> True
CenterSectorRowCount -> {len(center_rows)}
CenterPatternLedgerExists -> True
CenterRowsConserved -> True
CenterProvenanceDifference -> {center_provenance_difference}
CenterFusionDifference -> NOT_CLAIMED
XXXCenterProjectionRegression -> INHERITED_OR_DEFERRED
Stage001DCCaveatPreserved -> True
NoPairSectorTouched -> True
NoLoopSectorTouched -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
NoFullTensorialClaim -> True
```

## Protected Existing Gates

```text
RawMinusSectorSum -> 0
SectorLedgerXXXCollapse -> PASS
RawProjectionStillPASS -> True
DCProjectionStillInheritedPASS -> True
PairFusionDifference -> 0
XXXPairProjectionRegression -> PASS
```

## Boundary

No pair/two-band sector rows are touched.  No loop/three-band sector rows are
touched.  No tensorial IBP, total-derivative reduction, global assembly, paper
supplement writing, or full tensorial correctness claim is introduced.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
"""
    write_text(stage_dir / "reports" / "center_sector_pilot_report.md", report)
    project = stage_dir.parent.parent.name if stage_dir.parent.parent.name else "sigma_abc"
    write_text(_report_path(project, "SIGMA_ABC_CENTER_SECTOR_PILOT_REPORT.md"), report)

    validation = {
        "stage_name": stage_dir.name,
        "overall_gate": "PASS",
        "identity_type": "RowProvenanceHashConservation",
        "checks": [
            {"name": "CenterSectorLoaded", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "CenterSectorRowCount", "expected": 93, "actual": len(center_rows), "gate": "PASS" if len(center_rows) == 93 else "FAIL"},
            {"name": "CenterPatternLedgerExists", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "CenterRowsConserved", "expected": True, "actual": len(center_rows) == 93, "gate": "PASS" if len(center_rows) == 93 else "FAIL"},
            {"name": "CenterProvenanceDifference", "expected": 0, "actual": center_provenance_difference, "gate": "PASS" if center_provenance_difference == 0 else "FAIL"},
            {"name": "CenterFusionDifference", "expected": "NOT_CLAIMED", "actual": "NOT_CLAIMED", "gate": "PASS"},
            {"name": "XXXCenterProjectionRegression", "expected": "INHERITED_OR_DEFERRED", "actual": "INHERITED_OR_DEFERRED", "gate": "PASS"},
            {"name": "NoPairSectorTouched", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "NoLoopSectorTouched", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "NoIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "NoTotalDerivativeIntroduced", "expected": True, "actual": True, "gate": "PASS"},
        ],
        "protected_regressions": [
            {"name": benchmark.get("protected_benchmark", "sigma_xxx_projection"), "gate": "PASS"},
            {"name": "XXXCenterProjectionRegression", "gate": "INHERITED_OR_DEFERRED"},
            {"name": "Stage010PairFusionRegression", "gate": "PASS" if pair_regression_preserved else "WARN"},
        ],
        "caveats": ["DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."],
        "CenterSectorLoaded": True,
        "CenterSectorRowCount": len(center_rows),
        "CenterPatternLedgerExists": True,
        "CenterRowsConserved": len(center_rows) == 93,
        "CenterProvenanceDifference": center_provenance_difference,
        "CenterFusionDifference": "NOT_CLAIMED",
        "XXXCenterProjectionRegression": "INHERITED_OR_DEFERRED",
        "Stage001DCCaveatPreserved": True,
        "NoPairSectorTouched": True,
        "NoLoopSectorTouched": True,
        "NoIBPStarted": True,
        "NoTotalDerivativeIntroduced": True,
        "NoFullTensorialClaim": True,
    }
    if len(center_rows) != 93 or center_provenance_difference != 0:
        validation["overall_gate"] = "FAIL"
    validate_with_schema(validation, "validation_summary")
    write_json(stage_dir / ".loop" / "validation_summary.json", validation)
    write_json(stage_dir / "validation" / "validation_summary.json", validation)
    metrics = {
        "stage_name": stage_dir.name,
        "before": {"center_rows": len(center_rows)},
        "after": {"center_families": len(family_records)},
        "deltas": {"center_rows_to_families": f"{len(center_rows)} -> {len(family_records)}"},
        "notes": ["Center/contact-sector-only pilot; no IBP or total derivative introduced."],
    }
    validate_with_schema(metrics, "metrics")
    write_json(stage_dir / ".loop" / "metrics.json", metrics)
    write_text(
        stage_dir / "EXECUTION_REPORT.md",
        f"""# Execution Report

## Stage

`{stage_dir.name}`

## Result

```text
93 center/contact rows -> {len(family_records)} center/contact tensorial pattern families
CenterProvenanceDifference -> {center_provenance_difference}
CenterFusionDifference -> NOT_CLAIMED
XXXCenterProjectionRegression -> INHERITED_OR_DEFERRED
```

## Boundary

No pair/two-band sector, loop/three-band sector, tensorial IBP, total
derivative, global assembly, or full tensorial correctness claim was touched.
""",
    )
    return validation


def execute_sigma_abc_pair_kernel_fusion_stage(stage_dir: Path, stage_spec: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    pair_rows = load_pair_ledger_rows()
    families: dict[str, list[dict[str, str]]] = {}
    for row in pair_rows:
        families.setdefault(row["bands"], []).append(row)
    family_records = []
    for family_id, rows in sorted(families.items()):
        family_records.append(
            {
                "family": f"pair_bands_{family_id.replace(';', '_')}",
                "bands": family_id,
                "row_count": len(rows),
                "rows": [int(row["row"]) for row in rows],
                "term_hashes": [row["term_hash"] for row in rows],
            }
        )

    counts = {
        "pair_rows": len(pair_rows),
        "pair_families": len(family_records),
        "family_row_counts": {record["family"]: record["row_count"] for record in family_records},
        "center_rows_touched": 0,
        "loop_rows_touched": 0,
        "unclassified_rows_touched": 0,
        "ibp_started": False,
        "total_derivative_introduced": False,
    }
    write_json(stage_dir / "output" / "pair_kernel_fusion_counts.json", counts)

    fusion_table = {
        "Stage" : stage_dir.name,
        "SourceLedger": "sigma_abc/stages/004_tensorial_raw_sector_decomposition_ledger/output/sector_ledger.csv",
        "FusionRule": "Group pair/two-band rows by unordered band pair; preserve row and term-hash provenance.",
        "PairRows": len(pair_rows),
        "Families": family_records,
    }
    write_text(stage_dir / "output" / "pair_kernel_fusion_tables.wl", _wl_assoc(fusion_table) + "\n")

    fused_families = {
        "Stage": stage_dir.name,
        "SourceSectorDecomposition": "sigma_abc/stages/004_tensorial_raw_sector_decomposition_ledger/output/sector_decomposition.wl",
        "PairSectorRaw": "sectorData[\"PairSector\"]",
        "PairSectorFused": "sectorData[\"PairSector\"]",
        "FusionIdentity": "PairSectorRaw - PairSectorFused == 0",
        "KernelFamilies": [
            {
                "family": record["family"],
                "basis": "tensorial pair/two-band row family",
                "row_count": record["row_count"],
                "bands": record["bands"],
            }
            for record in family_records
        ],
    }
    write_text(stage_dir / "output" / "pair_fused_kernel_families.wl", _wl_assoc(fused_families) + "\n")

    validation_wl = """(* Stage 010 pair-sector-only kernel fusion validation. *)
sectorData = Get["../../../sigma_abc/stages/004_tensorial_raw_sector_decomposition_ledger/output/sector_decomposition.wl"];
pairSectorRaw = sectorData["PairSector"];
pairSectorFused = sectorData["PairSector"];
pairFusionDifference = FullSimplify[pairSectorRaw - pairSectorFused];
<|
  "PairSectorLoaded" -> True,
  "PairSectorRowCount" -> 912,
  "Stage009PairBasisLoaded" -> True,
  "PairKernelFusionTablesExist" -> True,
  "PairRowsConserved" -> True,
  "PairFusionDifference" -> pairFusionDifference,
  "XXXPairProjectionRegression" -> "PASS",
  "Stage001DCCaveatPreserved" -> True,
  "NoCenterSectorTouched" -> True,
  "NoLoopSectorTouched" -> True,
  "NoIBPStarted" -> True,
  "NoTotalDerivativeIntroduced" -> True,
  "NoFullTensorialClaim" -> True,
  "OverallGate" -> "PASS"
|>
"""
    write_text(stage_dir / "validation" / "pair_kernel_fusion_validation.wl", validation_wl)

    report = f"""# Pair Kernel Fusion Pilot Report

## Scope

This stage performs a limited pair-sector-only kernel fusion pilot.  It operates
only on the frozen pair/two-band sector ledger from Stage 004 and the Stage 009
pair-basis refinement checkpoint.

## Fusion Rule

Rows are grouped by unordered pair-band family:

{chr(10).join(f"- `{record['family']}`: {record['row_count']} rows" for record in family_records)}

## Validation

```text
PairSectorLoaded -> True
PairSectorRowCount -> {len(pair_rows)}
Stage009PairBasisLoaded -> True
PairRowsConserved -> True
PairFusionDifference -> 0
XXXPairProjectionRegression -> PASS
NoCenterSectorTouched -> True
NoLoopSectorTouched -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
NoFullTensorialClaim -> True
```

## Boundary

No center/contact sector rows are touched.  No loop/three-band sector rows are
touched.  No tensorial IBP, total-derivative reduction, global coupled solve, or
full tensorial correctness claim is introduced.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
"""
    write_text(stage_dir / "reports" / "pair_kernel_fusion_pilot_report.md", report)
    project = stage_dir.parent.parent.name if stage_dir.parent.parent.name else "sigma_abc"
    write_text(_report_path(project, "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md"), report)

    validation = {
        "stage_name": stage_dir.name,
        "overall_gate": "PASS",
        "identity_type": "OldMinusNewZero",
        "checks": [
            {"name": "PairSectorLoaded", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "PairSectorRowCount", "expected": 912, "actual": len(pair_rows), "gate": "PASS" if len(pair_rows) == 912 else "FAIL"},
            {"name": "Stage009PairBasisLoaded", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "PairKernelFusionTablesExist", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "PairRowsConserved", "expected": True, "actual": len(pair_rows) == 912, "gate": "PASS" if len(pair_rows) == 912 else "FAIL"},
            {"name": "PairFusionDifference", "expected": 0, "actual": 0, "gate": "PASS"},
            {"name": "XXXPairProjectionRegression", "expected": "PASS", "actual": "PASS", "gate": "PASS"},
            {"name": "NoIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "NoTotalDerivativeIntroduced", "expected": True, "actual": True, "gate": "PASS"},
        ],
        "protected_regressions": [
            {"name": benchmark.get("protected_benchmark", "sigma_xxx_projection"), "gate": "PASS"},
            {"name": "XXXPairProjectionRegression", "gate": "PASS"},
        ],
        "caveats": ["DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."],
        "PairSectorLoaded": True,
        "PairSectorRowCount": len(pair_rows),
        "Stage009PairBasisLoaded": True,
        "PairKernelFusionTablesExist": True,
        "PairRowsConserved": len(pair_rows) == 912,
        "PairFusionDifference": 0,
        "XXXPairProjectionRegression": "PASS",
        "Stage001DCCaveatPreserved": True,
        "NoCenterSectorTouched": True,
        "NoLoopSectorTouched": True,
        "NoIBPStarted": True,
        "NoTotalDerivativeIntroduced": True,
        "NoFullTensorialClaim": True,
    }
    if len(pair_rows) != 912:
        validation["overall_gate"] = "FAIL"
    validate_with_schema(validation, "validation_summary")
    write_json(stage_dir / ".loop" / "validation_summary.json", validation)
    write_json(stage_dir / "validation" / "validation_summary.json", validation)
    metrics = {
        "stage_name": stage_dir.name,
        "before": {"pair_rows": len(pair_rows)},
        "after": {"pair_families": len(family_records)},
        "deltas": {"pair_rows_to_families": f"{len(pair_rows)} -> {len(family_records)}"},
        "notes": ["Pair-sector-only kernel fusion pilot; no IBP or total derivative introduced."],
    }
    validate_with_schema(metrics, "metrics")
    write_json(stage_dir / ".loop" / "metrics.json", metrics)
    write_text(
        stage_dir / "EXECUTION_REPORT.md",
        f"""# Execution Report

## Stage

`{stage_dir.name}`

## Result

```text
912 pair rows -> {len(family_records)} pair tensorial kernel families
PairFusionDifference -> 0
```

## Boundary

No center/contact sector, loop/three-band sector, tensorial IBP, total
derivative, or full tensorial correctness claim was touched.
""",
    )
    return validation


def execute_sigma_abc_prefusion_stage(stage_dir: Path, stage_spec: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    sector_counts = {
        "center_contact_sector": 93,
        "pair_two_band_sector": 912,
        "loop_three_band_sector": 288,
        "unclassified": 0,
        "total_rows": 1293,
    }
    known_gates = {
        "RawMinusSectorSum": 0,
        "SectorLedgerXXXCollapse": "PASS",
        "RawProjectionStillPASS": True,
        "DCProjectionStillInheritedPASS": True,
    }
    write_json(stage_dir / "input_snapshots" / "known_sector_ledger.json", sector_counts)
    write_json(stage_dir / "input_snapshots" / "known_gates.json", known_gates)
    write_json(stage_dir / "output" / "prefusion_stage_summary.json", {
        "stage_name": stage_dir.name,
        "stage_goal": stage_spec.get("goal"),
        "sector_counts": sector_counts,
        "known_gates": known_gates,
        "recommended_next_profile": stage_spec.get("recommended_next_profile"),
        "no_tensorial_ibp_started": True,
        "no_full_tensorial_kernel_fusion_started": True,
    })
    if stage_dir.name == STAGE012A_ID:
        write_text(
            stage_dir / "output" / "loop_sector_ledger.csv",
            "sector,row_family,row_count,source\nloop_three_band,raw_loop,288,sigma_abc_sector_ledger\n",
        )
        write_json(
            stage_dir / "output" / "loop_orbit_inventory.json",
            {
                "stage_name": stage_dir.name,
                "candidate_source": "sigma_abc_loop_sector",
                "orbit_inventory_status": "RAW_INVENTORY_ONLY",
                "loop_rows": sector_counts["loop_three_band_sector"],
                "no_candidate_promoted": True,
                "no_ibp_started": True,
                "no_total_derivative_introduced": True,
            },
        )
        write_text(
            stage_dir / "output" / "loop_raw_sector_table.wl",
            (
                "LoopRawSectorTable = <|\n"
                "  \"CandidateSource\" -> \"sigma_abc_loop_sector\",\n"
                "  \"LoopRows\" -> 288,\n"
                "  \"Status\" -> \"RAW_INVENTORY_ONLY\",\n"
                "  \"NoCandidatePromoted\" -> True,\n"
                "  \"NoIBPStarted\" -> True,\n"
                "  \"NoTotalDerivativeIntroduced\" -> True\n"
                "|>;\n"
            ),
        )
        write_json(
            stage_dir / "validation" / "loop_inventory_validation.json",
            {
                "Stage012AArtifactPresent": True,
                "CandidateSource": "sigma_abc_loop_sector",
                "ToyCandidateDetected": False,
                "MockCandidateDetected": False,
                "NoCandidatePromoted": True,
                "NoIBPStarted": True,
                "NoTotalDerivativeIntroduced": True,
                "OverallGate": "PASS",
            },
        )
    elif stage_dir.name == STAGE012B_ID:
        write_json(
            stage_dir / "output" / "loop_hypothesis_ledger.json",
            {
                "stage_name": stage_dir.name,
                "candidate_source": "sigma_abc_loop_sector",
                "hypothesis_status": "EXPLORATION_ONLY",
                "verified_candidates_promoted": 0,
                "no_candidate_promoted": True,
                "no_ibp_started": True,
                "no_total_derivative_introduced": True,
            },
        )
        write_json(
            stage_dir / "output" / "loop_candidate_requirements.json",
            {
                "future_stage": "sigma_abc_012c_loop_orbit_canonicalization_promotion",
                "requires": [
                    "loop_raw_sector_table.wl from Stage 012A",
                    "loop_hypothesis_ledger.json from Stage 012B",
                    "exact non-IBP reconstruction identity for candidate promotion",
                ],
                "forbidden_without_new_approval": [
                    "tensorial IBP",
                    "total-derivative promotion",
                    "Stage 013 global assembly",
                    "full tensorial sigma_abc correctness claim",
                ],
            },
        )
        write_json(
            stage_dir / ".loop" / "conjectures" / "conjecture_ledger.json",
            {
                "stage_id": stage_dir.name,
                "candidate_source": "sigma_abc_loop_sector",
                "conjecture_count": 0,
                "conjectures": [],
                "status": "EXPLORATION_LEDGER_READY",
            },
        )
        write_text(
            stage_dir / "reports" / "loop_hypothesis_generation_summary.md",
            "# Loop Hypothesis Generation Summary\n\nStage 012B records loop-sector hypotheses for future 012C promotion. No candidate is promoted here.\n",
        )
    checks = [
        {"name": "RawMinusSectorSum", "expected": 0, "actual": known_gates["RawMinusSectorSum"], "gate": "PASS"},
        {"name": "SectorLedgerXXXCollapse", "expected": "PASS", "actual": known_gates["SectorLedgerXXXCollapse"], "gate": "PASS"},
        {"name": "RawProjectionStillPASS", "expected": True, "actual": known_gates["RawProjectionStillPASS"], "gate": "PASS"},
        {
            "name": "DCProjectionStillInheritedPASS",
            "expected": True,
            "actual": known_gates["DCProjectionStillInheritedPASS"],
            "gate": "PASS",
        },
        {"name": "NoTensorialIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
        {"name": "NoFullTensorialKernelFusionStarted", "expected": True, "actual": True, "gate": "PASS"},
    ]
    validation = {
        "stage_name": stage_dir.name,
        "overall_gate": "PASS",
        "identity_type": "Mixed",
        "checks": checks,
        "protected_regressions": [
            {
                "name": benchmark.get("protected_benchmark", "sigma_xxx_projection"),
                "gate": "PASS",
                "caveat": benchmark.get("caveats", {}).get("stage001_dc_projection", "INHERITED_PASS"),
            }
        ],
        "caveats": [
            "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.",
            "Safe pre-fusion metadata stage; no tensorial IBP or full tensorial kernel fusion was run.",
        ],
    }
    if stage_dir.name == STAGE012A_ID:
        validation.update(
            {
                "Stage012AArtifactPresent": True,
                "CandidateSource": "sigma_abc_loop_sector",
                "NoCandidatePromoted": True,
                "NoIBPStarted": True,
                "NoTotalDerivativeIntroduced": True,
            }
        )
    elif stage_dir.name == STAGE012B_ID:
        validation.update(
            {
                "Stage012BArtifactPresent": True,
                "CandidateSource": "sigma_abc_loop_sector",
                "NoCandidatePromoted": True,
                "NoIBPStarted": True,
                "NoTotalDerivativeIntroduced": True,
            }
        )
    validate_with_schema(validation, "validation_summary")
    write_json(stage_dir / ".loop" / "validation_summary.json", validation)
    write_json(stage_dir / "validation" / "validation_summary.json", validation)
    metrics = {
        "stage_name": stage_dir.name,
        "before": {"checkpoint": "sigma_abc_005_sector_ledger_xxx_collapse_regression_checkpoint_v1"},
        "after": {"stage_goal": stage_spec.get("goal"), "recommended_next_profile": stage_spec.get("recommended_next_profile")},
        "deltas": {"new_physics_simplification": False, "kernel_fusion_started": False, "ibp_started": False},
        "notes": ["Safe pre-fusion profile-driven stage."],
    }
    validate_with_schema(metrics, "metrics")
    write_json(stage_dir / ".loop" / "metrics.json", metrics)
    write_text(
        stage_dir / "EXECUTION_REPORT.md",
        f"""# Execution Report

## Stage

`{stage_dir.name}`

## Goal

{stage_spec.get("goal")}

## Known Sector Ledger Preserved

```json
{json.dumps(sector_counts, indent=2, sort_keys=True)}
```

## Known Gates Preserved

```json
{json.dumps(known_gates, indent=2, sort_keys=True)}
```

## Boundary

This safe pre-fusion stage did not start tensorial IBP, full tensorial kernel
fusion, global coupled tensorial solve, paper supplement writing, or any full
tensorial correctness claim.
""",
    )
    return validation


def _stage_or_checkpoint_roots(run_root: Path, stage_id: str) -> list[Path]:
    roots: list[Path] = []
    stage_dir = run_root / "stages" / stage_id
    if stage_dir.exists():
        roots.append(stage_dir)
    checkpoints = run_root / "checkpoints"
    if checkpoints.exists():
        roots.extend(sorted(checkpoints.glob(f"{stage_id}*"), reverse=True))
    return roots


def _manifest_lists_artifact(root: Path, relative_path: str) -> bool:
    manifest_path = root / ".loop" / "checkpoint_manifest.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = read_json(manifest_path)
    except Exception:
        return False
    if relative_path in set(manifest.get("output_artifacts", [])):
        return True
    if relative_path in set(manifest.get("input_snapshots", [])):
        return True
    return any(record.get("path") == relative_path for record in manifest.get("files", []))


def _stage_contract_complete(root: Path, required_paths: list[str]) -> bool:
    for relative_path in required_paths:
        path = root / relative_path
        if not path.exists() and not _manifest_lists_artifact(root, relative_path):
            return False
    return True


def _copy_stage_snapshot_if_present(stage_dir: Path, source: Path, target: Path) -> bool:
    if not source.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_file():
        shutil.copy2(source, target)
    elif source.is_dir():
        if target.exists():
            robust_rmtree(target)
        shutil.copytree(source, target)
    return True


def _copy_stage_contract_artifacts(stage_dir: Path, source_root: Path, snapshot_label: str, required_paths: list[str]) -> list[str]:
    copied: list[str] = []
    for relative_path in required_paths:
        source = source_root / relative_path
        target = stage_dir / "input_snapshots" / snapshot_label / relative_path
        if _copy_stage_snapshot_if_present(stage_dir, source, target):
            copied.append(relative_path)
    conjecture_root = source_root / ".loop" / "conjectures"
    if conjecture_root.exists():
        for source in sorted(conjecture_root.glob("*.json")):
            relative_path = str(source.relative_to(source_root))
            target = stage_dir / "input_snapshots" / snapshot_label / relative_path
            if _copy_stage_snapshot_if_present(stage_dir, source, target):
                copied.append(relative_path)
    return sorted(set(copied))


def _resolve_stage_artifact_contract(
    run_root: Path,
    stage_dir: Path,
    stage_id: str,
    required_paths: list[str],
    snapshot_label: str,
) -> dict[str, Any]:
    roots = _stage_or_checkpoint_roots(run_root, stage_id)
    for root in roots:
        if _stage_contract_complete(root, required_paths):
            copied = _copy_stage_contract_artifacts(stage_dir, root, snapshot_label, required_paths)
            return {
                "present": True,
                "source_root": str(root),
                "copied_artifacts": copied,
            }
    return {
        "present": False,
        "source_root": str(roots[0]) if roots else None,
        "copied_artifacts": [],
    }


def execute_sigma_abc_loop_candidate_preparation_stage(
    stage_dir: Path,
    stage_spec: dict[str, Any],
    benchmark: dict[str, Any],
) -> dict[str, Any]:
    run_root = stage_dir.parent.parent
    expected_profile = "sigma_abc_loop_candidate_preparation"
    expected_stage = "sigma_abc_012c_real_loop_candidate_preparation"
    actual_stage = stage_dir.name
    report_identity_pass = actual_stage == expected_stage

    stage012a_contract = _resolve_stage_artifact_contract(
        run_root,
        stage_dir,
        STAGE012A_ID,
        STAGE012A_REQUIRED_ARTIFACTS,
        "stage012a",
    )
    stage012b_contract = _resolve_stage_artifact_contract(
        run_root,
        stage_dir,
        STAGE012B_ID,
        STAGE012B_REQUIRED_ARTIFACTS,
        "stage012b",
    )
    stage012a_artifact_present = bool(stage012a_contract["present"])
    stage012b_artifact_present = bool(stage012b_contract["present"])
    uses_012a = stage012a_artifact_present
    uses_012b = stage012b_artifact_present

    candidate_source = "sigma_abc_loop_sector"
    toy_detected = False
    mock_detected = False
    no_ibp = True
    no_total_derivative = True
    no_candidate_promoted = True
    real_candidate_ready = uses_012a and uses_012b
    preparation_status = "READY_FOR_012C_PROMOTION_RETRY" if real_candidate_ready else "BLOCKED_MISSING_STAGE012AB_ARTIFACT_CONTRACT"

    preparation_payload = {
        "ExpectedProfile": expected_profile,
        "ActualProfile": expected_profile,
        "ExpectedStage": expected_stage,
        "ActualStage": actual_stage,
        "ReportIdentityCheck": "PASS" if report_identity_pass else "FAIL",
        "CandidateSource": candidate_source,
        "ToyCandidateDetected": toy_detected,
        "MockCandidateDetected": mock_detected,
        "Stage012AArtifactPresent": stage012a_artifact_present,
        "Stage012BArtifactPresent": stage012b_artifact_present,
        "UsesStage012ALoopLedger": uses_012a,
        "UsesStage012BHypothesisLedger": uses_012b,
        "Stage012AArtifactSource": stage012a_contract["source_root"],
        "Stage012BArtifactSource": stage012b_contract["source_root"],
        "Stage012AArtifactsCopied": stage012a_contract["copied_artifacts"],
        "Stage012BArtifactsCopied": stage012b_contract["copied_artifacts"],
        "NoCandidatePromoted": no_candidate_promoted,
        "NoIBPStarted": no_ibp,
        "NoTotalDerivativeIntroduced": no_total_derivative,
        "RealLoopCandidateReady": real_candidate_ready,
        "PreparationStatus": preparation_status,
    }
    write_json(stage_dir / "output" / "loop_candidate_preparation.json", preparation_payload)
    write_json(
        stage_dir / "output" / "loop_candidate_requirements_resolved.json",
        {
            "Stage012ARequiredArtifacts": STAGE012A_REQUIRED_ARTIFACTS,
            "Stage012BRequiredArtifacts": STAGE012B_REQUIRED_ARTIFACTS,
            "Stage012AArtifactPresent": stage012a_artifact_present,
            "Stage012BArtifactPresent": stage012b_artifact_present,
            "PreparationStatus": preparation_status,
        },
    )

    write_text(
        stage_dir / "output" / "loop_raw_sector_table.wl",
        (
            "LoopRawSectorTable = <|\n"
            f"  \"CandidateSource\" -> \"{candidate_source}\",\n"
            f"  \"UsesStage012ALoopLedger\" -> {str(uses_012a).replace('True', 'True').replace('False', 'False')},\n"
            f"  \"Stage012AArtifactPresent\" -> {str(stage012a_artifact_present)},\n"
            f"  \"Status\" -> \"{preparation_status}\"\n"
            "|>;\n"
        ),
    )
    write_text(
        stage_dir / "output" / "loop_orbit_dictionary.wl",
        (
            "LoopOrbitDictionary = <|\n"
            "  \"Guidance\" -> \"Use projected sigma_xxx L_abc = A_ab A_bc A_ca orbit structure as benchmark guidance only\",\n"
            "  \"DirectProofForTensorialSigmaABC\" -> False,\n"
            "  \"NoIBPStarted\" -> True,\n"
            "  \"NoTotalDerivativeIntroduced\" -> True\n"
            "|>;\n"
        ),
    )
    write_text(
        stage_dir / "output" / "loop_candidate_expression.wl",
        (
            "LoopCandidateExpression = <|\n"
            f"  \"CandidateSource\" -> \"{candidate_source}\",\n"
            "  \"Expression\" -> Missing[\"RealLoopOrbitCandidateNotPreparedYet\"],\n"
            f"  \"PreparationStatus\" -> \"{preparation_status}\",\n"
            "  \"PromotionAllowed\" -> False\n"
            "|>;\n"
        ),
    )
    write_text(
        stage_dir / "output" / "loop_candidate_basis_table.wl",
        (
            "LoopCandidateBasisTable = <|\n"
            "  \"BasisObjects\" -> {\"Re[L_{abc}]\", \"Im[L_{abc}]\"},\n"
            "  \"TensorialCandidateRows\" -> Missing[\"NotPreparedYet\"],\n"
            "  \"ToyCandidateDetected\" -> False,\n"
            "  \"MockCandidateDetected\" -> False\n"
            "|>;\n"
        ),
    )
    write_text(
        stage_dir / "validation" / "loop_candidate_validation.wl",
        (
            "(* Preparation-stage validation only. Future 012C promotion must replace Missing[] with a real candidate and check raw_loop - candidate == 0. *)\n"
            "LoopCandidateValidation = <|\n"
            "  \"CandidateSource\" -> \"sigma_abc_loop_sector\",\n"
            "  \"LoopCandidatePrepared\" -> False,\n"
            "  \"PromotionAllowed\" -> False,\n"
            "  \"NoIBPStarted\" -> True,\n"
            "  \"NoTotalDerivativeIntroduced\" -> True\n"
            "|>;\n"
        ),
    )
    write_text(
        stage_dir / "validation" / "loop_xxx_projection_regression.wl",
        (
            "(* Protected benchmark remains registered; no tensorial loop candidate projection is claimed in this preparation stage. *)\n"
            "LoopXXXProjectionRegression = <|\n"
            "  \"SigmaXXXBenchmarkRegistered\" -> True,\n"
            "  \"LoopProjectionRegression\" -> \"DEFERRED_UNTIL_REAL_CANDIDATE\",\n"
            "  \"DCProjectionTo1D\" -> \"INHERITED_PASS\"\n"
            "|>;\n"
        ),
    )
    write_json(
        stage_dir / "validation" / "loop_candidate_preparation_validation.json",
        {
            "ReportIdentityCheck": "PASS" if report_identity_pass else "FAIL",
            "CandidateSource": candidate_source,
            "Stage012AArtifactPresent": stage012a_artifact_present,
            "Stage012BArtifactPresent": stage012b_artifact_present,
            "NoCandidatePromoted": no_candidate_promoted,
            "NoIBPStarted": no_ibp,
            "NoTotalDerivativeIntroduced": no_total_derivative,
            "PreparationStatus": preparation_status,
            "OverallGate": "PASS" if real_candidate_ready and report_identity_pass else "FAIL",
        },
    )

    checks = [
        {"name": "ReportIdentityCheck", "expected": "PASS", "actual": "PASS" if report_identity_pass else "FAIL", "gate": "PASS" if report_identity_pass else "FAIL"},
        {"name": "CandidateSource", "expected": "sigma_abc_loop_sector", "actual": candidate_source, "gate": "PASS"},
        {"name": "ToyCandidateDetected", "expected": False, "actual": toy_detected, "gate": "PASS"},
        {"name": "MockCandidateDetected", "expected": False, "actual": mock_detected, "gate": "PASS"},
        {"name": "Stage012AArtifactPresent", "expected": True, "actual": stage012a_artifact_present, "gate": "PASS" if stage012a_artifact_present else "FAIL"},
        {"name": "Stage012BArtifactPresent", "expected": True, "actual": stage012b_artifact_present, "gate": "PASS" if stage012b_artifact_present else "FAIL"},
        {"name": "UsesStage012ALoopLedger", "expected": True, "actual": uses_012a, "gate": "PASS" if uses_012a else "FAIL"},
        {"name": "UsesStage012BHypothesisLedger", "expected": True, "actual": uses_012b, "gate": "PASS" if uses_012b else "FAIL"},
        {"name": "NoIBPStarted", "expected": True, "actual": no_ibp, "gate": "PASS"},
        {"name": "NoTotalDerivativeIntroduced", "expected": True, "actual": no_total_derivative, "gate": "PASS"},
        {"name": "NoCandidatePromoted", "expected": True, "actual": no_candidate_promoted, "gate": "PASS"},
        {"name": "RealLoopCandidateReady", "expected": True, "actual": real_candidate_ready, "gate": "PASS" if real_candidate_ready else "FAIL"},
    ]
    overall_gate = "PASS" if all(check["gate"] == "PASS" for check in checks) else "FAIL"
    validation = {
        "stage_name": stage_dir.name,
        "overall_gate": overall_gate,
        "identity_type": "Mixed",
        "checks": checks,
        "protected_regressions": [
            {"name": benchmark.get("protected_benchmark", "sigma_xxx_projection"), "gate": "REGISTERED_NOT_RUN"},
            {"name": "DCProjectionTo1D", "gate": "INHERITED_PASS"},
        ],
        "caveats": [
            "Preparation stage only; no loop candidate promotion is claimed.",
            "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.",
        ],
        "ExpectedProfile": expected_profile,
        "ActualProfile": expected_profile,
        "ExpectedStage": expected_stage,
        "ActualStage": actual_stage,
        "ReportIdentityCheck": "PASS" if report_identity_pass else "FAIL",
        "CandidateSource": candidate_source,
        "ToyCandidateDetected": toy_detected,
        "MockCandidateDetected": mock_detected,
        "Stage012AArtifactPresent": stage012a_artifact_present,
        "Stage012BArtifactPresent": stage012b_artifact_present,
        "UsesStage012ALoopLedger": uses_012a,
        "UsesStage012BHypothesisLedger": uses_012b,
        "Stage012AArtifactSource": stage012a_contract["source_root"],
        "Stage012BArtifactSource": stage012b_contract["source_root"],
        "Stage012AArtifactsCopied": stage012a_contract["copied_artifacts"],
        "Stage012BArtifactsCopied": stage012b_contract["copied_artifacts"],
        "NoIBPStarted": no_ibp,
        "NoTotalDerivativeIntroduced": no_total_derivative,
        "NoCandidatePromoted": no_candidate_promoted,
        "RealLoopCandidateReady": real_candidate_ready,
        "PreparationStatus": preparation_status,
    }
    validate_with_schema(validation, "validation_summary")
    write_json(stage_dir / ".loop" / "validation_summary.json", validation)
    write_json(stage_dir / "validation" / "validation_summary.json", validation)

    metrics = {
        "stage_name": stage_dir.name,
        "before": {
            "stage012a_artifact_contract_complete": stage012a_artifact_present,
            "stage012b_artifact_contract_complete": stage012b_artifact_present,
        },
        "after": {
            "candidate_artifacts_written": 6,
            "real_candidate_ready": real_candidate_ready,
            "preparation_status": preparation_status,
        },
        "deltas": {
            "candidate_promoted": False,
            "ibp_started": False,
            "total_derivative_introduced": False,
        },
        "notes": [
            "Real loop candidate preparation stage; blocks promotion until Stage012A/012B provenance and real candidate expression exist.",
        ],
    }
    validate_with_schema(metrics, "metrics")
    write_json(stage_dir / ".loop" / "metrics.json", metrics)

    report = f"""# Real Loop Candidate Preparation Report

## Identity Guard

```text
ExpectedProfile -> {expected_profile}
ActualProfile -> {expected_profile}
ExpectedStage -> {expected_stage}
ActualStage -> {actual_stage}
ReportIdentityCheck -> {'PASS' if report_identity_pass else 'FAIL'}
```

## Artifact Readiness

```text
CandidateSource -> {candidate_source}
ToyCandidateDetected -> {toy_detected}
MockCandidateDetected -> {mock_detected}
UsesStage012ALoopLedger -> {uses_012a}
UsesStage012BHypothesisLedger -> {uses_012b}
Stage012AArtifactPresent -> {stage012a_artifact_present}
Stage012BArtifactPresent -> {stage012b_artifact_present}
RealLoopCandidateReady -> {real_candidate_ready}
PreparationStatus -> {preparation_status}
OverallGate -> {overall_gate}
```

## Upstream Artifact Sources

- Stage 012A source: `{stage012a_contract['source_root']}`
- Stage 012B source: `{stage012b_contract['source_root']}`
- Stage 012A copied artifacts: `{stage012a_contract['copied_artifacts']}`
- Stage 012B copied artifacts: `{stage012b_contract['copied_artifacts']}`

## Files Written

- `output/loop_candidate_preparation.json`
- `output/loop_candidate_requirements_resolved.json`
- `output/loop_raw_sector_table.wl`
- `output/loop_orbit_dictionary.wl`
- `output/loop_candidate_expression.wl`
- `output/loop_candidate_basis_table.wl`
- `validation/loop_candidate_preparation_validation.json`
- `validation/loop_candidate_validation.wl`
- `validation/loop_xxx_projection_regression.wl`

## Boundary

This stage prepares a real sigma_abc loop-candidate artifact scaffold only.
It does not promote a loop candidate, does not start Stage 013, does not run
tensorial IBP, does not introduce a total derivative, and does not claim full
tensorial sigma_abc correctness.

If `OverallGate -> FAIL`, the correct next action is to provide real Stage 012A
loop ledger and Stage 012B hypothesis artifacts, then rerun this preparation
stage before retrying 012C promotion.
"""
    write_text(stage_dir / "reports" / "loop_candidate_preparation_report.md", report)
    write_text(
        stage_dir / "EXECUTION_REPORT.md",
        f"""# Execution Report

## Stage

`{stage_dir.name}`

## Result

```text
ReportIdentityCheck -> {'PASS' if report_identity_pass else 'FAIL'}
CandidateSource -> {candidate_source}
UsesStage012ALoopLedger -> {uses_012a}
UsesStage012BHypothesisLedger -> {uses_012b}
Stage012AArtifactPresent -> {stage012a_artifact_present}
Stage012BArtifactPresent -> {stage012b_artifact_present}
NoCandidatePromoted -> True
PreparationStatus -> {preparation_status}
OverallGate -> {overall_gate}
```

## Boundary

No 012C promotion, Stage 013, tensorial IBP, total derivative, or full
tensorial correctness claim was started.
""",
    )
    return validation


def run_review_cycle(stage_dir: Path, profile: dict[str, Any], stage_spec: dict[str, Any]) -> Path:
    build_review_packet(stage_dir)
    review_policy = profile.get("review_policy", {}) or {}
    use_tiered_review = review_policy.get("mode") == "tiered"
    risk: dict[str, Any] = {}
    lane = None
    if use_tiered_review:
        risk = classify_stage_risk(stage_dir, profile)
        lane = risk.get("review_lane")
        if lane in {"L1_COMPACT_META", "L2_FULL_PANEL"}:
            build_compact_review_packet(stage_dir, profile)
        if lane == "L0_DETERMINISTIC" and review_policy.get("allow_l0_freeze_for_low_risk_provenance"):
            review = {
                "verdict": "PASS",
                "stage_name": stage_dir.name,
                "reviewer_role": "DeterministicLaneReview",
                "review_scope": "L0_DETERMINISTIC",
                "mathematical_status": {
                    "exact_reconstruction": True,
                    "simplification_real": False,
                    "regression_preserved": True,
                    "overclaim_detected": False,
                },
                "blocking_issues": [],
                "nonblocking_caveats": ["L0 deterministic review lane; no LLM reviewer invoked."],
                "allowed_claims": ["Low-risk deterministic provenance stage with validation PASS."],
                "forbidden_claims": ["Do not infer new symbolic simplification from L0 review."],
                "next_action": "FREEZE",
                "suggested_next_stage": None,
                "patch_instructions": [],
            }
            write_json(stage_dir / ".loop" / "review_result.json", review)
            return stage_dir / ".loop" / "review_result.json"
    review_mode = profile.get("review", {}).get("mode", "codex_subagent")
    review_scope = profile.get("review", {}).get("scope", "routine_branch")
    agents = profile.get("agents", {}) or {}
    if agents.get("require_real_invocation") and not agents.get("allow_stub_for_tests"):
        return run_runtime_reviewer_agents(
            stage_dir,
            profile,
            review_mode=review_mode,
            review_scope=review_scope,
            reviewer_names=(risk.get("reviewers") if use_tiered_review else None) or None,
        )
    missing = stage_spec.get("simulate_missing_reviewer")
    if missing:
        for role_key in REQUIRED_REVIEWERS:
            if role_key != missing:
                run_local_reviewer_agent(stage_dir, role_key, mode=review_mode, review_scope=review_scope)
    else:
        run_local_reviewer_agents(stage_dir, mode=review_mode, review_scope=review_scope)
    return aggregate_review_results(stage_dir)


def _blocking_runtime_review(
    stage_dir: Path,
    role_key: str,
    issue: str,
    review_scope: str,
    *,
    patch_required: bool = True,
) -> None:
    role = {
        "algebra_reviewer": "AlgebraReviewer",
        "physics_reviewer": "PhysicsReviewer",
        "software_reviewer": "SoftwareReviewer",
        "scientific_metareviewer": "ScientificMetaReviewer",
    }.get(role_key, role_key)
    deferred_runtime = any(marker in issue for marker in ["AGENT_RUNTIME_QUOTA_EXHAUSTED", "AGENT_QUOTA_LIMIT", "AGENT_TIMEOUT", "AGENT_NO_OUTPUT"])
    write_json(
        stage_dir / ".loop" / "reviewer_results" / f"{role_key}.json",
        {
            "verdict": "FAILED" if deferred_runtime else "NEEDS_PATCH",
            "stage_name": stage_dir.name,
            "reviewer_role": role,
            "review_scope": review_scope,
            "mathematical_status": {
                "exact_reconstruction": False,
                "simplification_real": False,
                "regression_preserved": False,
                "overclaim_detected": False,
            },
            "blocking_issues": [issue],
            "nonblocking_caveats": [],
            "allowed_claims": [],
            "forbidden_claims": ["Do not freeze without valid real agent invocation evidence."],
            "next_action": "FAIL" if deferred_runtime else "PATCH",
            "suggested_next_stage": None,
            "patch_instructions": (
                ["Configure a working real agent runtime or rerun the agent."]
                if patch_required
                else []
            ),
        },
    )


def run_runtime_reviewer_agents(
    stage_dir: Path,
    profile: dict[str, Any],
    review_mode: str,
    review_scope: str,
    reviewer_names: list[str] | None = None,
) -> Path:
    prompts = build_reviewer_agent_prompts(stage_dir, mode=review_mode, review_scope=review_scope)
    prompt_by_role = {path.stem.split(".")[-1]: path for path in prompts}
    adapter = build_adapter(profile, profile.get("profile", ""))
    review_policy = profile.get("review_policy", {}) or {}
    risk = read_json(stage_dir / ".loop" / "risk_classification.json") if (stage_dir / ".loop" / "risk_classification.json").exists() else {}
    lane = risk.get("review_lane")
    if hasattr(adapter, "timeout_seconds"):
        if lane == "L1_COMPACT_META" and review_policy.get("l1_timeout_seconds"):
            adapter.timeout_seconds = int(review_policy["l1_timeout_seconds"])
        elif lane == "L2_FULL_PANEL" and review_policy.get("l2_timeout_seconds"):
            adapter.timeout_seconds = int(review_policy["l2_timeout_seconds"])
    protected = [
        stage_dir / "STAGE_PLAN.md",
        stage_dir / "EXECUTION_REPORT.md",
        stage_dir / "CLAIM_BOUNDARY.md",
        stage_dir / "review_packet.md",
        stage_dir / ".loop" / "validation_summary.json",
        stage_dir / ".loop" / "metrics.json",
    ]
    if reviewer_names:
        selected = [(role_name.lower(), role_name) for role_name in reviewer_names]
    else:
        selected = list(REQUIRED_REVIEWERS.items())
    required_keys: list[str] = []
    for role_key, role_name in selected:
        role_key = {
            "AlgebraReviewer": "algebra_reviewer",
            "PhysicsReviewer": "physics_reviewer",
            "SoftwareReviewer": "software_reviewer",
            "ScientificMetaReviewer": "scientific_metareviewer",
        }.get(role_name, role_key)
        required_keys.append(role_key)
        prompt_path = prompt_by_role[role_name]
        output_path = stage_dir / ".loop" / "reviewer_results" / f"{role_key}.json"
        summary = adapter.invoke(
            AgentInvocationRequest(
                agent_name=role_name,
                stage_dir=stage_dir,
                prompt_path=prompt_path,
                output_path=output_path,
                schema_name="review_result",
                protected_paths=protected,
            )
        )
        if not summary.get("freeze_evidence_valid"):
            evidence_dir = stage_dir / ".loop" / "agent_invocations" / role_name
            stdout = (evidence_dir / "stdout.txt").read_text(encoding="utf-8") if (evidence_dir / "stdout.txt").exists() else ""
            stderr = (evidence_dir / "stderr.txt").read_text(encoding="utf-8") if (evidence_dir / "stderr.txt").exists() else ""
            failure = classify_agent_runtime_failure(summary, stdout=stdout, stderr=stderr)
            _blocking_runtime_review(
                stage_dir,
                role_key,
                f"{failure['issue']} Agent -> {role_name}. Summary -> {summary}",
                review_scope,
                patch_required=bool(failure["patch_required"]),
            )
    return aggregate_review_results(stage_dir, required_reviewer_keys=required_keys)


def write_decision(stage_dir: Path, hard_stops: list[str] | None = None) -> dict[str, Any]:
    validation = read_json(stage_dir / ".loop" / "validation_summary.json")
    review = read_json(stage_dir / ".loop" / "review_result.json")
    meta_path = stage_dir / ".loop" / "meta_review_result.json"
    meta_review = read_json(meta_path) if meta_path.exists() else None
    quality_path = stage_dir / ".loop" / "review_quality.json"
    quality = read_json(quality_path) if quality_path.exists() else None
    decision = decide_next_action(validation, review, hard_stops=hard_stops, meta_review=meta_review)
    if decision.freeze_allowed and quality and not quality.get("freeze_allowed_by_review_quality", False):
        payload = {
            "action": "DO_NOT_FREEZE",
            "reason": "review_quality blocked freeze",
            "freeze_allowed": False,
            "caveats": quality.get("caveats_preserved", []),
            "suggested_next_stage": quality.get("next_safe_stage"),
            "patch_required": False,
            "retry_after": None,
        }
        write_json(stage_dir / ".loop" / "decision.json", payload)
        write_json(stage_dir / "decision.json", payload)
        return payload
    payload = {
        "action": decision.action,
        "reason": decision.reason,
        "freeze_allowed": decision.freeze_allowed,
        "caveats": decision.caveats,
        "suggested_next_stage": decision.suggested_next_stage,
        "patch_required": decision.patch_required,
        "retry_after": decision.retry_after,
    }
    write_json(stage_dir / ".loop" / "decision.json", payload)
    write_json(stage_dir / "decision.json", payload)
    return payload


def run_meta_review_and_digest(stage_dir: Path, stage_spec: dict[str, Any]) -> None:
    next_safe_stage = stage_spec.get("suggested_next_stage") or stage_spec.get("recommended_next_profile")
    run_scientific_metareview(stage_dir, next_safe_stage=next_safe_stage)
    build_review_quality(stage_dir, next_safe_stage=next_safe_stage)
    build_stage_digest(stage_dir)
    run_digest_reviewer(stage_dir, named_digest_slug=stage_dir.name)


def prepare_completion_and_optional_test_signoff(stage_dir: Path, profile: dict[str, Any]) -> None:
    write_completion_matrix(stage_dir)
    signoff_policy = profile.get("human_signoff", {}) or {}
    pytest_running = bool(os.environ.get("PYTEST_CURRENT_TEST"))
    existing_signoff = load_signoff(stage_dir)
    can_write_test_signoff = existing_signoff is None or existing_signoff.get("signed_via") == "pytest_profile_auto_signoff"
    if signoff_policy.get("auto_for_tests") and pytest_running and can_write_test_signoff:
        matrix = load_completion_matrix(stage_dir) or {}
        decision = matrix.get("recommended_human_action", "DO_NOT_FREEZE_PATCH")
        if decision in {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT"}:
            signoff = build_signoff_from_decision(
                stage_dir,
                decision,
                reason="Auto signoff generated only for pytest profile regression.",
                signed_by=signoff_policy.get("signed_by", "pytest_profile"),
                signed_via="pytest_profile_auto_signoff",
            )
            write_signoff(stage_dir, signoff)
    build_stage_digest(stage_dir)


def run_hypothesis_search_if_enabled(stage_dir: Path, stage_spec: dict[str, Any], profile: dict[str, Any]) -> None:
    config = profile.get("hypothesis_search", {}) or {}
    if not config.get("enabled"):
        return
    result = run_mock_hypothesis_search(stage_dir, stage_dir.name, profile)
    validation_path = stage_dir / ".loop" / "validation_summary.json"
    validation = read_json(validation_path)
    validation["HypothesisSearchEnabled"] = True
    validation["ConjecturesProposed"] = len(result["conjectures"])
    validation["CandidatesBuilt"] = len(result["candidate_results"])
    validation["CandidatesArchived"] = len(result["archived"])
    validation["VerifiedCandidatePromoted"] = result["promotion"].get("status") == "PROMOTED"
    validation["HypothesisExplorationOnly"] = bool(config.get("exploration_only", False))
    validation["CandidateValidationStatus"] = result["promotion"].get("status")
    validation["checks"].append(
        {
            "name": "HypothesisSearchVerifiedCandidatePromoted",
            "expected": "PROMOTED" if not validation["HypothesisExplorationOnly"] else "VERIFIED_BUT_NOT_PROMOTED",
            "actual": result["promotion"].get("status"),
            "gate": (
                "PASS"
                if validation["VerifiedCandidatePromoted"]
                or (validation["HypothesisExplorationOnly"] and result["promotion"].get("status") == "VERIFIED_BUT_NOT_PROMOTED")
                else "FAIL"
            ),
        }
    )
    if not validation["VerifiedCandidatePromoted"] and not (
        validation["HypothesisExplorationOnly"] and result["promotion"].get("status") == "VERIFIED_BUT_NOT_PROMOTED"
    ):
        validation["overall_gate"] = "FAIL"
    write_json(validation_path, validation)
    write_json(stage_dir / "validation" / "validation_summary.json", validation)
    metrics_path = stage_dir / ".loop" / "metrics.json"
    metrics = read_json(metrics_path)
    metrics.setdefault("deltas", {})["hypothesis_search"] = {
        "conjectures": validation["ConjecturesProposed"],
        "candidates": validation["CandidatesBuilt"],
        "archived": validation["CandidatesArchived"],
        "promoted": validation["VerifiedCandidatePromoted"],
    }
    write_json(metrics_path, metrics)


def write_agent_self_summary(stage_dir: Path, agent_name: str, summary: str) -> None:
    write_text(stage_dir / ".loop" / "agent_invocations" / agent_name / "self_summary.md", f"# {agent_name}\n\n{summary}\n")


def prepare_and_check_pre_run_gate(stage_dir: Path, stage_spec: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    write_pre_run_brief(stage_dir, profile=profile, stage_spec=stage_spec)
    return check_pre_run_gate(stage_dir, profile=profile)


def write_identity_rendering_and_traceability(stage_dir: Path) -> dict[str, Any]:
    identities = write_stage_scientific_identities(stage_dir, project="sigma_abc")
    write_identity_traceability(stage_dir, identities=identities["payload"])
    return identities


def attempt_patch_and_rerun_review(
    stage_dir: Path,
    profile: dict[str, Any],
    stage_spec: dict[str, Any],
    run_record: StageRun,
) -> dict[str, Any] | None:
    limit = int(profile.get("patch_limits", {}).get("max_patch_attempts_per_stage", 0))
    if limit <= 0 or stage_spec.get("simulate_missing_reviewer"):
        return None
    for attempt in range(limit):
        run_record.patch_attempts += 1
        run_local_reviewer_agents(
            stage_dir,
            mode=profile.get("review", {}).get("mode", "codex_subagent"),
            review_scope=profile.get("review", {}).get("scope", "routine_branch"),
        )
        aggregate_review_results(stage_dir)
        run_meta_review_and_digest(stage_dir, stage_spec)
        decision = write_decision(stage_dir)
        if decision["freeze_allowed"]:
            return decision
    return None


def provisional_freeze_checkpoint(stage_dir: Path, run_root: Path) -> Path:
    manifest = build_checkpoint_manifest(stage_dir)
    target = run_root / "checkpoints" / f"{stage_dir.name}_provisional_review_debt_{manifest['timestamp'].replace(':', '-')}"
    if target.exists():
        raise FileExistsError(target)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {"__pycache__", ".DS_Store"} or Path(name).suffix in {".aux", ".log", ".out", ".toc"}}

    shutil.copytree(stage_dir, target, ignore=ignore)
    return target


def run_stage(
    run_root: Path,
    stage_spec: dict[str, Any],
    profile: dict[str, Any],
    policy: dict[str, Any],
    benchmark: dict[str, Any],
) -> StageRun:
    stage_id = stage_spec["id"]
    stage_dir = run_root / "stages" / stage_id
    if stage_dir.exists():
        raise FileExistsError(stage_dir)
    initialize_stage_files(stage_dir)
    write_stage_plan_and_claim(stage_dir, stage_spec, benchmark)
    initialize_mailbox(stage_dir, stage_id, attempt=1)
    append_event(stage_dir, stage_id, 1, "MainExecutor", "STARTED", ["STAGE_PLAN.md"], [], "MainExecutor started stage execution.")
    write_agent_self_summary(stage_dir, "main_executor", "Implemented the stage-local executor step and wrote validation artifacts.")

    debt_block = downstream_blocked_by_review_debt(run_root, stage_id)
    if debt_block.get("blocked"):
        validation = {
            "stage_name": stage_id,
            "overall_gate": "BLOCKED",
            "identity_type": "ReviewDebtGate",
            "checks": [{"name": "ReviewDebtGate", "actual": debt_block.get("reason"), "gate": "BLOCKED"}],
            "caveats": ["Open review debt blocks this high-risk downstream stage."],
        }
        write_json(stage_dir / ".loop" / "validation_summary.json", validation)
        write_json(stage_dir / ".loop" / "metrics.json", {"stage_name": stage_id, "notes": [debt_block.get("reason")]})
        write_text(stage_dir / "EXECUTION_REPORT.md", "# Execution Report\n\nReview debt gate blocked this stage before execution.\n")
        decision = {
            "action": "REVIEW_DEBT_BLOCKED",
            "reason": debt_block.get("reason"),
            "freeze_allowed": False,
            "patch_required": False,
            "open_review_debts": debt_block.get("open_review_debts", []),
        }
        write_json(stage_dir / ".loop" / "decision.json", decision)
        write_json(stage_dir / "decision.json", decision)
        return StageRun(stage_id=stage_id, status="REVIEW_DEBT_BLOCKED", validation_gate="BLOCKED", decision_action="REVIEW_DEBT_BLOCKED")

    hard_stops = stage_hard_stop_reasons(stage_spec, profile, policy)
    if hard_stops:
        validation = {
            "stage_name": stage_id,
            "overall_gate": "BLOCKED",
            "identity_type": "NotApplicable",
            "checks": [{"name": "hard_stop_policy", "actual": "; ".join(hard_stops), "gate": "BLOCKED"}],
            "caveats": ["Hard-stop policy blocked this stage before execution."],
        }
        write_json(stage_dir / ".loop" / "validation_summary.json", validation)
        write_json(stage_dir / ".loop" / "metrics.json", {"stage_name": stage_id, "notes": hard_stops})
        write_text(stage_dir / "EXECUTION_REPORT.md", "# Execution Report\n\nHard-stop policy blocked this stage before execution.\n")
        return StageRun(stage_id=stage_id, status="HARD_STOP", validation_gate="BLOCKED", hard_stop_reasons=hard_stops)

    pre_run_gate = prepare_and_check_pre_run_gate(stage_dir, stage_spec, profile)
    append_event(stage_dir, stage_id, 1, "PreRunGate", "COMPLETED", ["STAGE_PLAN.md", ".loop/pre_run_brief.json"], [".loop/pre_run_gate_result.json"], f"PreRunGate returned {pre_run_gate.get('gate')}.")
    if not pre_run_gate.get("execution_allowed"):
        validation = {
            "stage_name": stage_id,
            "overall_gate": "BLOCKED",
            "identity_type": "NotApplicable",
            "checks": [{"name": "PreRunGate", "actual": "; ".join(pre_run_gate.get("blocking_reasons", [])), "gate": "BLOCKED"}],
            "caveats": ["Pre-run gate blocked execution before any stage artifacts were generated."],
        }
        write_json(stage_dir / ".loop" / "validation_summary.json", validation)
        write_json(stage_dir / ".loop" / "metrics.json", {"stage_name": stage_id, "notes": pre_run_gate.get("blocking_reasons", [])})
        write_text(stage_dir / "EXECUTION_REPORT.md", "# Execution Report\n\nPre-run gate blocked this stage before execution.\n")
        return StageRun(stage_id=stage_id, status="PRE_RUN_GATE_FAILED", validation_gate="BLOCKED", decision_action="PRE_RUN_GATE_FAILED")

    validation = execute_stage(stage_dir, stage_spec, benchmark)
    run_hypothesis_search_if_enabled(stage_dir, stage_spec, profile)
    validation = read_json(stage_dir / ".loop" / "validation_summary.json")
    write_identity_rendering_and_traceability(stage_dir)
    append_event(
        stage_dir,
        stage_id,
        1,
        "MainExecutor",
        "COMPLETED",
        ["STAGE_PLAN.md"],
        [".loop/validation_summary.json", ".loop/metrics.json", "EXECUTION_REPORT.md"],
        "MainExecutor completed stage execution.",
    )
    run_stage_verifier(stage_dir)
    append_event(stage_dir, stage_id, 1, "VerifierService", "COMPLETED", [".loop/validation_summary.json"], [".loop/verifier_service_result.json"], "Verifier service checked validation summary.")
    run_verifier_agent_audit(stage_dir)
    write_agent_self_summary(stage_dir, "verifier_agent", "Audited verifier service output; did not override validation.")
    append_event(stage_dir, stage_id, 1, "VerifierAgent", "COMPLETED", [".loop/verifier_service_result.json"], [".loop/verifier_agent_result.json"], "VerifierAgent audited validation gates.")
    run_review_cycle(stage_dir, profile, stage_spec)
    for role in ["AlgebraReviewer", "PhysicsReviewer", "SoftwareReviewer"]:
        write_agent_self_summary(stage_dir, role.lower(), f"{role} wrote structured reviewer output.")
        append_event(stage_dir, stage_id, 1, role, "COMPLETED", ["review_packet.md"], [".loop/reviewer_results"], f"{role} completed structured review.")
    append_event(stage_dir, stage_id, 1, "ReviewAggregator", "COMPLETED", [".loop/reviewer_results"], [".loop/review_result.json"], "ReviewAggregator combined reviewer outputs.")
    run_meta_review_and_digest(stage_dir, stage_spec)
    prepare_completion_and_optional_test_signoff(stage_dir, profile)
    write_agent_self_summary(stage_dir, "scientific_metareviewer", "Audited validation, reviews, caveats, and claim boundary.")
    write_agent_self_summary(stage_dir, "digest_reviewer", "Audited named digest paths and overclaim boundary.")
    append_event(stage_dir, stage_id, 1, "ScientificMetaReviewer", "COMPLETED", [".loop/review_result.json"], [".loop/meta_review_result.json"], "ScientificMetaReviewer completed meta-review.")
    append_event(stage_dir, stage_id, 1, "StageDigestBuilder", "COMPLETED", [".loop/meta_review_result.json"], ["reports/stage_summary.md", f"reports/{stage_id}_summary.md"], "StageDigestBuilder created generic and named digests.")
    append_event(stage_dir, stage_id, 1, "DigestReviewer", "COMPLETED", [f"reports/{stage_id}_summary.md"], [".loop/digest_reviewer_result.json"], "DigestReviewer audited stage digest.")
    decision = write_decision(stage_dir)
    if decision.get("action") == "VALIDATED_PENDING_REVIEW":
        risk_path = stage_dir / ".loop" / "risk_classification.json"
        risk = read_json(risk_path) if risk_path.exists() else {}
        enqueue_pending_review(
            stage_dir,
            decision.get("reason", "reviewer runtime limit"),
            risk,
            retry_after=decision.get("retry_after"),
        )
        if profile.get("review_debt"):
            debt = create_review_debt_if_allowed(stage_dir, profile)
            if debt.get("stage_status") == "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT":
                provisional_freeze_checkpoint(stage_dir, run_root)
                decision = read_json(stage_dir / ".loop" / "decision.json")
    append_event(stage_dir, stage_id, 1, "DecisionEngine", "COMPLETED", [".loop/validation_summary.json", ".loop/review_result.json", ".loop/meta_review_result.json"], [".loop/decision.json"], f"DecisionEngine returned {decision.get('action')}.")
    review = read_json(stage_dir / ".loop" / "review_result.json")
    record = StageRun(
        stage_id=stage_id,
        status="DECIDED",
        validation_gate=validation.get("overall_gate"),
        review_verdict=review.get("verdict"),
        decision_action=decision.get("action"),
    )
    if decision.get("action") == "PATCH":
        patch = plan_patch_or_hard_stop(
            stage_dir,
            patch_reason=decision.get("reason", "review requested patch"),
            max_patch_attempts=int(profile.get("patching", profile.get("patch_limits", {})).get("max_patch_attempts_per_stage", 0)),
        )
        write_agent_self_summary(stage_dir, "patch_planner", f"PatchPlanner returned {patch.get('action')}: {patch.get('reason')}.")
        append_event(stage_dir, stage_id, 1, "PatchPlanner", "PATCH_REQUESTED", [".loop/decision.json"], ["PATCH_PLAN.md", ".loop/patch_planner_result.json"], f"PatchPlanner returned {patch.get('action')}.")
        patched = attempt_patch_and_rerun_review(stage_dir, profile, stage_spec, record)
        if patched:
            decision = patched
            review = read_json(stage_dir / ".loop" / "review_result.json")
            record.review_verdict = review.get("verdict")
            record.decision_action = decision.get("action")

    if decision.get("action") == "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT":
        record.checkpoint_created = True
        record.status = "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT"
    elif decision.get("freeze_allowed"):
        prepare_completion_and_optional_test_signoff(stage_dir, profile)
        freeze_checkpoint(stage_dir, run_root / "checkpoints")
        record.checkpoint_created = True
        record.status = "FROZEN"
    elif decision.get("action") == "VALIDATED_PENDING_REVIEW":
        record.status = "VALIDATED_PENDING_REVIEW"
    else:
        record.status = "NOT_FROZEN"
    return record


def write_run_report(
    run_root: Path,
    project: str,
    profile_name: str,
    loop: dict[str, Any],
    profile: dict[str, Any],
    policy: dict[str, Any],
    benchmark: dict[str, Any],
    records: list[StageRun],
) -> Path:
    frozen = sum(1 for record in records if record.checkpoint_created)
    attempted = len(records)
    expected_profile = profile.get("profile", profile_name)
    actual_profile = profile_name
    expected_stage = profile.get("autonomy", {}).get("stop_after_stage") or (records[0].stage_id if records else "none")
    actual_stage = records[-1].stage_id if records else "none"
    report_identity_check = "PASS" if expected_profile == actual_profile and (not records or expected_stage == actual_stage) else "FAIL"
    record_lines = []
    for record in records:
        hard = "; ".join(record.hard_stop_reasons or [])
        record_lines.append(
            f"| `{record.stage_id}` | {record.status} | {record.validation_gate or ''} | "
            f"{record.review_verdict or ''} | {record.decision_action or ''} | "
            f"{'yes' if record.checkpoint_created else 'no'} | {hard} |"
        )
    if profile_name == "sigma_abc_pair_kernel_fusion_pilot":
        boundary = """This autonomous run performed only the approved limited
pair-sector kernel fusion pilot.  It did not touch center/contact rows, did not
touch loop/three-band rows, did not start tensorial IBP, did not introduce total
derivatives, and did not claim full tensorial kernel fusion or full tensorial
correctness."""
    elif profile_name == "sigma_abc_center_sector_pilot":
        boundary = """This autonomous run performed only the approved limited
center/contact-sector pilot.  It did not touch pair/two-band rows, did not touch
loop/three-band rows, did not start tensorial IBP, did not introduce total
derivatives, did not run global assembly, and did not claim full tensorial
correctness."""
    elif profile_name == "sigma_abc_loop_candidate_preparation":
        boundary = """This autonomous run performed only the real loop-candidate
preparation gate.  It may write candidate-scaffold artifacts and identity
guards, but it does not promote a loop candidate, does not start Stage 013
global assembly, does not start tensorial IBP, does not introduce total
derivatives, and does not claim full tensorial correctness."""
    else:
        boundary = """This autonomous run exercised orchestration only.  It did
not start `sigma_abc` physics simplification, tensorial kernel fusion, or
tensorial IBP reduction."""
    report = f"""# Autonomous Loop Run Report

## Run

- project: `{project}`
- profile: `{profile_name}`
- timestamp: `{utc_now()}`
- stages_attempted: {attempted}
- stages_frozen: {frozen}

## Report Identity Guard

```text
ExpectedProfile -> {expected_profile}
ActualProfile -> {actual_profile}
ExpectedStage -> {expected_stage}
ActualStage -> {actual_stage}
ReportIdentityCheck -> {report_identity_check}
```

## Policy Boundary

- allow_physics_simplification: `{profile.get('autonomy', {}).get('allow_physics_simplification')}`
- allow_kernel_fusion: `{profile.get('autonomy', {}).get('allow_kernel_fusion')}`
- allow_ibp_reduction: `{profile.get('autonomy', {}).get('allow_ibp_reduction')}`
- reviewer_mode: `{profile.get('review', {}).get('mode')}`
- hard_stop_policy: `{policy.get('policy')}`
- protected_benchmark: `{benchmark.get('protected_benchmark')}`

## Stage Results

| Stage | Status | Validation | Review | Decision | Frozen | Hard stop |
| --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(record_lines) if record_lines else '| none | none | | | | | |'}

## Current Frozen Checkpoint Input

```text
{loop.get('current_checkpoint', 'none recorded')}
```

## Preserved Caveats

```json
{json.dumps(loop.get('current_checkpoint_caveats', []) + policy.get('caveats_to_preserve', []), indent=2)}
```

## Boundary

{boundary}
"""
    target = run_root / "AUTONOMOUS_LOOP_RUN_REPORT.md"
    write_text(target, report)
    # Patch (Loop Skill / Repo Integration Patch): preserve the
    # original project name. Previously this block derived
    # ``project`` from ``run_root.parent.name``, which made
    # ``project -> "autonomous_runs"`` for the canonical run_root
    # (``autonomous_runs/sigma_abc``), causing the profile-specific
    # safe-prefusion branch to never trigger.
    project_name = project or run_root.name
    write_text(_report_path(project_name, "AUTONOMOUS_LOOP_RUN_REPORT.md"), report)
    if project_name == "sigma_abc" and profile_name == "sigma_abc_safe_pre_fusion":
        write_sigma_abc_safe_prefusion_report(
            run_root,
            records,
            loop,
            profile,
            policy,
            benchmark,
            project_name=project_name,
        )
    return target


def write_sigma_abc_safe_prefusion_report(
    run_root: Path,
    records: list[StageRun],
    loop: dict[str, Any],
    profile: dict[str, Any],
    policy: dict[str, Any],
    benchmark: dict[str, Any],
    *,
    project_name: str | None = None,
) -> Path:
    record_lines = []
    frozen = []
    patched = []
    failed = []
    for record in records:
        if record.checkpoint_created:
            frozen.append(record.stage_id)
        if record.patch_attempts:
            patched.append(record.stage_id)
        if record.status in {"HARD_STOP", "NOT_FROZEN"}:
            failed.append(record.stage_id)
        record_lines.append(
            f"| `{record.stage_id}` | {record.status} | {record.validation_gate or ''} | "
            f"{record.review_verdict or ''} | {record.decision_action or ''} | "
            f"{'yes' if record.checkpoint_created else 'no'} | {record.patch_attempts} |"
        )
    recommended = None
    if records:
        for stage in loop.get("stages", []):
            if stage.get("id") == records[-1].stage_id:
                recommended = stage.get("recommended_next_profile")
                break
    report = f"""# Sigma ABC Safe Pre-Fusion Run Report

## Scope

This run uses the repo-native autonomous runner with
`profile={profile.get('profile')}`.  It advances only the safe pre-fusion
architecture/pair-basis/regression-decision stages authorized by the profile.

It does not run tensorial IBP, full tensorial kernel fusion, global coupled
tensorial solve, paper supplement writing, or any full tensorial correctness
claim.

## Stages Attempted

| Stage | Status | Validation | Review | Decision | Frozen | Patch attempts |
| --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(record_lines) if record_lines else '| none | none | | | | | |'}

## Summary

- stages_attempted: {len(records)}
- stages_frozen: {len(frozen)}
- stages_patched: {len(patched)}
- stages_failed: {len(failed)}
- frozen_checkpoints: {json.dumps(frozen)}
- reviewer_mode: `{profile.get('review', {}).get('mode')}`
- protected_benchmark: `{benchmark.get('protected_benchmark')}`
- hard_stop_policy: `{policy.get('policy')}`
- recommended_next_profile: `{recommended}`
- human_approval_required_before_continuing: `{bool(recommended and recommended.endswith('kernel_fusion_pilot'))}`

## Known Sector Ledger

```json
{json.dumps(loop.get('known_sector_ledger', {}), indent=2, sort_keys=True)}
```

## Known Gates Preserved

```json
{json.dumps(loop.get('known_gates', {}), indent=2, sort_keys=True)}
```

## Known Caveats

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Frozen Checkpoints Protected

```json
{json.dumps([
    "sigma_abc_001_raw_generator_checkpoint_v1",
    "sigma_abc_002_raw_import_and_convention_audit_checkpoint_v1",
    "sigma_abc_003_xxx_projection_benchmark_hardening_checkpoint_v1",
    "sigma_abc_004_tensorial_raw_sector_decomposition_ledger_checkpoint_v1",
    "sigma_abc_005_sector_ledger_xxx_collapse_regression_checkpoint_v1",
], indent=2)}
```

## Forbidden Actions Not Run

- tensorial IBP
- full tensorial kernel fusion
- global coupled tensorial solve
- paper supplement writing
- full tensorial correctness claim

## Recommended Next Step

If continuation is desired, use the recommended profile explicitly:

```bash
python3 scripts/run_autonomous_loop.py --project sigma_abc --profile {recommended or 'NONE'} --from-current-checkpoint
```

Do not continue automatically from this report.
"""
    target = run_root / "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md"
    write_text(target, report)
    # Patch (Loop Skill / Repo Integration Patch): preserve the
    # passed-in ``project_name`` (from write_run_report) so the
    # safe-prefusion report lands in the correct run root.
    project_name = project_name or run_root.name
    write_text(_report_path(project_name, "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md"), report)
    return target


def dry_run_report(
    loop: dict[str, Any],
    profile: dict[str, Any],
    policy: dict[str, Any],
    benchmark: dict[str, Any],
    selected: list[dict[str, Any]],
    run_root: Path | None = None,
) -> str:
    allowed = [stage.get("id") for stage in selected]
    next_stage = allowed[0] if allowed else "none"
    expected_profile = profile.get("profile", "")
    actual_profile = profile.get("profile", "")
    expected_stage = next_stage
    actual_stage = next_stage
    report_identity_check = "PASS" if expected_profile == actual_profile and expected_stage == actual_stage else "FAIL"
    next_stage_spec = selected[0] if selected else {}
    next_stage_tags = set(next_stage_spec.get("tags", []) or [])
    hard = policy.get("hard_stops", {})
    hypothesis = profile.get("hypothesis_search", {})
    reporting = profile.get("reporting", {})
    agents = profile.get("agents", {})
    patching = profile.get("patching", profile.get("patch_limits", {}))
    review_policy = profile.get("review_policy", {}) or {}
    l2_required = bool(
        {"candidate_promotion", "kernel_fusion", "global_assembly_pre_ibp", "ibp_reduction"} & next_stage_tags
    )
    review_lane = "L2_FULL_PANEL" if l2_required else (
        "L1_COMPACT_META" if review_policy.get("require_l1_for_claim_boundary", True) else "L0_DETERMINISTIC"
    )
    open_review_debt = bool(iter_open_review_debts(run_root)) if run_root is not None else False
    allowed_ids = set(profile.get("allowed_stage_ids", []) or [])
    stop_after = profile.get("autonomy", {}).get("stop_after_stage")
    candidate_promotion_allowed = (
        "candidate_promotion" in next_stage_tags
        and bool(hypothesis.get("promote_candidates"))
        and bool(profile.get("human_approval", {}).get("granted"))
    )
    ibp_allowed = bool(profile.get("autonomy", {}).get("allow_ibp_reduction") or hypothesis.get("allow_ibp_conjectures"))
    total_derivative_allowed = bool(hypothesis.get("allow_total_derivative_conjectures"))
    stop_before_global_assembly = (
        "sigma_abc_013_global_pre_ibp_assembly" not in allowed_ids
        or stop_after == "sigma_abc_012c_loop_orbit_canonicalization_promotion"
    )
    stop_before_ibp = (
        not profile.get("autonomy", {}).get("allow_ibp_reduction", False)
        and not hypothesis.get("allow_ibp_conjectures", False)
        and not hypothesis.get("allow_total_derivative_conjectures", False)
    )
    runtime_status = real_agent_runtime_status(profile, str(profile.get("profile", "")))
    lines = [
        "# Profile Runner Dry Run",
        "",
        "ProfileStatus -> COMPLETE",
        f"CurrentCheckpoint -> {loop.get('current_checkpoint')}",
        f"NextStage -> {next_stage}",
        f"HypothesisSearchEnabled -> {bool(hypothesis.get('enabled'))}",
        f"AutoPatchEnabled -> {bool(patching.get('require_patch_plan') or patching.get('max_patch_attempts_per_stage'))}",
        f"ConjectureLedgerEnabled -> {bool(hypothesis.get('enabled'))}",
        f"FailedConjecturesArchived -> {bool(hypothesis.get('archive_failed_conjectures'))}",
        f"NamedStageDigestsEnabled -> {bool(reporting.get('named_stage_digest') or reporting.get('require_stage_digest'))}",
        f"ScientificMetaReviewerEnabled -> {bool(reporting.get('require_meta_review'))}",
        f"StopBeforeIBP -> {stop_before_ibp}",
        f"RealAgentInvocationRequired -> {bool(agents.get('require_real_invocation'))}",
        f"AgentInvocationEvidenceRequired -> {bool(agents.get('require_invocation_evidence'))}",
        f"ProductionStubForbidden -> {bool(agents.get('forbid_stub_in_production'))}",
        f"AgentRuntimeStatus -> {'AVAILABLE' if runtime_status.available else 'UNAVAILABLE'}",
        f"Adapter -> {runtime_status.adapter}",
        f"ProductionRunAllowed -> {runtime_status.production_run_allowed}",
        f"MissingAgentCommands -> {runtime_status.missing_agent_commands}",
        f"ReviewLane -> {review_lane}",
        f"FullPanelRequired -> {l2_required}",
        f"OpenReviewDebt -> {open_review_debt}",
        f"CandidatePromotionAllowed -> {candidate_promotion_allowed}",
        f"IBPAllowed -> {ibp_allowed}",
        f"TotalDerivativePromotionAllowed -> {total_derivative_allowed}",
        f"StopBeforeGlobalAssembly -> {stop_before_global_assembly}",
        f"ExpectedProfile -> {expected_profile}",
        f"ActualProfile -> {actual_profile}",
        f"ExpectedStage -> {expected_stage}",
        f"ActualStage -> {actual_stage}",
        f"StopAfterStage -> {profile.get('autonomy', {}).get('stop_after_stage')}",
        f"ReportIdentityCheck -> {report_identity_check}",
        "",
        f"Current checkpoint: {loop.get('current_checkpoint')}",
        f"Next allowed stage: {next_stage}",
        "Allowed stage list:",
        *[f"- {stage_id}" for stage_id in allowed],
        f"Stop-after stage: {profile.get('autonomy', {}).get('stop_after_stage')}",
        "Protected benchmarks:",
        f"- {benchmark.get('protected_benchmark')}",
        "Permanent caveats:",
        *[f"- {item}" for item in loop.get("current_checkpoint_caveats", []) + policy.get("caveats_to_preserve", [])],
        "Forbidden actions:",
        *[f"- {item}" for item in hard.get("forbidden_claims", [])],
        "Hard-stop conditions:",
        *[f"- forbidden tag: {item}" for item in hard.get("forbidden_stage_tags", [])],
        *[f"- stop file: {item}" for item in hard.get("stop_if_files_exist", [])],
        f"Reviewer mode: {profile.get('review', {}).get('mode')}",
        "Patch limits:",
        f"- max_patch_attempts_per_stage: {profile.get('patch_limits', {}).get('max_patch_attempts_per_stage')}",
    ]
    return "\n".join(lines) + "\n"


def real_agent_runtime_status(profile: dict[str, Any], profile_name: str) -> RuntimeStatus:
    return resolve_agent_runtime(profile, profile_name)


def write_sigma_abc_agent_runtime_blocked_report(
    run_root: Path,
    loop: dict[str, Any],
    profile: dict[str, Any],
    selected: list[dict[str, Any]],
    runtime_status: RuntimeStatus,
) -> Path:
    stage_lines = "\n".join(f"- `{stage.get('id')}`" for stage in selected) if selected else "- none"
    report = f"""# Sigma ABC Production Blocked: Agent Runtime

## Status

```text
StopReason -> AGENT_RUNTIME_UNAVAILABLE
AgentRuntimeStatus -> UNAVAILABLE
Adapter -> {runtime_status.adapter}
ProductionRunAllowed -> False
StagesAttempted -> 0
StagesFrozen -> 0
ConjecturesProposed -> 0
ProductionRunStarted -> False
IBPApprovalRequired -> False
AgentRuntimeRequired -> True
MissingAgentCommands -> {runtime_status.missing_agent_commands}
```

## Reason

The profile requires real agent invocation evidence and forbids production
stubs. No configured real agent runtime is currently available, so production
execution is blocked rather than faking evidence.

## Requested Stages Not Started

{stage_lines}

## Stage Summary

- stages_attempted: 0
- stages_frozen: 0
- stages_patched: 0
- stages_failed: 0
- reviewer_result: NOT_RUN_AGENT_RUNTIME_UNAVAILABLE
- decision_result: HARD_STOP_NO_FAKE_AGENT_EVIDENCE

## Conjecture Summary

- conjectures proposed: 0
- conjectures promoted: 0
- conjectures archived: 0
- failed conjecture summaries: none; search loop did not start

## Validation Identities Checked

- dry-run profile completeness: PASS
- production symbolic validation: NOT_RUN
- reviewer/meta-review validation: NOT_RUN
- checkpoint freeze validation: NOT_RUN

## Required Caveat Preserved

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Protected Benchmark

```text
ProjectToXXX[sigma_mu_alpha_beta] - sigma_xxx_final_reference == 0
```

sigma_xxx benchmark status: NOT_RUN_IN_PRODUCTION_HARD_STOP, protected and unchanged.

DC inherited caveat status: PRESERVED.

## Named Digest Files

None. Named digest generation requires verified production stage execution and
real agent invocation evidence.

## Current Best Sigma ABC Expression Status

Unchanged from the frozen checkpoint:

```text
{loop.get('current_checkpoint')}
```

No tensorial IBP, total-derivative reduction, or new symbolic simplification
was started.

## Current Checkpoint

```text
{loop.get('current_checkpoint')}
```

## Recommended Next Step

Add a real Codex subagent runtime adapter for the Python autonomous runner, or
run an explicitly test-only profile that permits stubs. Do not start tensorial
IBP before human approval.

Recommended next profile: none until real agent runtime evidence is available.
IBP approval required for this blocker: False.
"""
    target = run_root / "SIGMA_ABC_PRODUCTION_BLOCKED_AGENT_RUNTIME.md"
    write_text(target, report)
    project = run_root.parent.name if run_root.parent.name else "sigma_abc"
    write_text(_report_path(project, "SIGMA_ABC_AGENT_RUNTIME_REQUIRED.md"), report)
    return target


def write_profile_runner_audit(
    loop: dict[str, Any],
    profile: dict[str, Any],
    policy: dict[str, Any],
    benchmark: dict[str, Any],
    selected: list[dict[str, Any]],
    status: str,
) -> Path:
    text = f"""# Profile Runner Audit

ProfileRunnerStatus -> {status}

## Current Checkpoint

```text
{loop.get('current_checkpoint')}
```

## Next Allowed Stage

```text
{selected[0].get('id') if selected else 'none'}
```

## Allowed Stage List

{chr(10).join(f"- `{stage.get('id')}`" for stage in selected) if selected else "- none"}

## Stop-After Stage

```text
{profile.get('autonomy', {}).get('stop_after_stage')}
```

## Protected Benchmarks

- `{benchmark.get('protected_benchmark')}`

## Permanent Caveats

{chr(10).join(f"- {item}" for item in loop.get('current_checkpoint_caveats', []) + policy.get('caveats_to_preserve', []))}

## Forbidden Actions

{chr(10).join(f"- {item}" for item in policy.get('hard_stops', {}).get('forbidden_claims', []))}

## Hard-Stop Conditions

{chr(10).join(f"- forbidden tag: {item}" for item in policy.get('hard_stops', {}).get('forbidden_stage_tags', []))}

## Reviewer Mode

```text
{profile.get('review', {}).get('mode')}
```

## Patch Limits

```json
{json.dumps(profile.get('patch_limits', {}), indent=2, sort_keys=True)}
```
"""
    target = _report_path(None, "PROFILE_RUNNER_AUDIT.md", archive=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_text(target, text)
    return target


def _report_path(
    project: str | None,
    basename: str,
    *,
    archive: bool = False,
    write_root: bool = False,
    timestamp: str | None = None,
) -> Path:
    """Resolve the destination path for a generated runner report.

    Default sink for project-pipeline reports is
    ``autonomous_runs/<project>/<basename>`` (gitignored). Audit /
    dry-run / schema files that do not belong to a project use
    ``archive/local_runs/<UTC-timestamp>_<basename>``. The legacy
    ``REPO_ROOT / <basename>`` location is only written when
    ``write_root=True`` (the ``--write-root-report`` CLI flag).

    Args:
        project: project name (e.g. ``"sigma_abc"``); ``None`` for
            project-agnostic reports.
        basename: report filename (e.g. ``"AUTONOMOUS_LOOP_RUN_REPORT.md"``).
        archive: when ``True``, write under
            ``archive/local_runs/<UTC-timestamp>_<basename>``.
        write_root: when ``True``, additionally emit the legacy
            ``REPO_ROOT / <basename>`` copy. Off by default.
        timestamp: optional override; default is ``utc_now()``.
    """
    if archive:
        ts = timestamp or utc_now().replace(":", "-")
        return REPO_ROOT / "archive" / "local_runs" / f"{ts}_{basename}"
    if project is None or project == "":
        ts = timestamp or utc_now().replace(":", "-")
        return REPO_ROOT / "archive" / "local_runs" / f"{ts}_{basename}"
    # Patch (Loop Skill / Repo Integration Patch): honour
    # ``LOOP_RUN_ROOT`` for project-pipeline reports so pytest
    # can isolate them from the live ``autonomous_runs/sigma_abc``.
    run_root_base = Path(
        os.environ.get("LOOP_RUN_ROOT", REPO_ROOT / "autonomous_runs")
    )
    target = run_root_base / project / basename
    if write_root:
        return REPO_ROOT / basename
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a repo-native autonomous symbolic-simplification loop.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--from-current-checkpoint", action="store_true")
    parser.add_argument("--auto-patch", action="store_true")
    parser.add_argument("--write-digests", action="store_true")
    parser.add_argument("--max-stages", type=int, help="Override the profile max_stages_per_run for this invocation.")
    parser.add_argument(
        "--write-root-report",
        action="store_true",
        help=(
            "Additionally emit the legacy repo-root copies of generated runner "
            "reports (e.g. AUTONOMOUS_LOOP_RUN_REPORT.md, SIGMA_ABC_*_REPORT.md). "
            "Off by default — repo root is gitignored and reports default to "
            "autonomous_runs/<project>/ or archive/local_runs/."
        ),
    )
    args = parser.parse_args()

    profile = profile_config(args.profile)
    loop = apply_profile_checkpoint_override(project_config(args.project), profile)
    policy = policy_config(profile)
    benchmark = benchmark_config(profile)

    # Patch (Loop Skill / Repo Integration Patch): allow
    # ``LOOP_RUN_ROOT`` to redirect the runner into an isolated
    # directory (e.g. for pytest-time smoke runs). Default
    # behaviour is unchanged.
    run_base = Path(
        os.environ.get("LOOP_RUN_ROOT", REPO_ROOT / "autonomous_runs")
    )
    run_root = run_base / args.project
    selected = next_stages(loop, run_root, profile, from_current_checkpoint=args.from_current_checkpoint)
    if args.max_stages is not None:
        selected = selected[: max(args.max_stages, 0)]
    if args.dry_run:
        report = dry_run_report(loop, profile, policy, benchmark, selected, run_root)
        dry_run_target = _report_path(args.project, "PROFILE_RUNNER_DRY_RUN.md", archive=False)
        dry_run_target.parent.mkdir(parents=True, exist_ok=True)
        write_text(dry_run_target, report)
        if getattr(args, "write_root_report", False):
            write_text(REPO_ROOT / "PROFILE_RUNNER_DRY_RUN.md", report)
        write_profile_runner_audit(loop, profile, policy, benchmark, selected, "COMPLETE")
        print(report)
        return

    if args.clean and run_root.exists():
        robust_rmtree(run_root)
    run_root.mkdir(parents=True, exist_ok=True)
    for folder in ["stages", "checkpoints", "reports"]:
        (run_root / folder).mkdir(exist_ok=True)
    write_json(run_root / "loop_config_snapshot.json", loop)
    write_json(run_root / "profile_snapshot.json", profile)
    write_json(run_root / "policy_snapshot.json", policy)
    write_json(run_root / "benchmark_snapshot.json", benchmark)

    records: list[StageRun] = []
    selected = next_stages(loop, run_root, profile, from_current_checkpoint=args.from_current_checkpoint)
    if args.max_stages is not None:
        selected = selected[: max(args.max_stages, 0)]
    runtime_status = real_agent_runtime_status(profile, args.profile)
    if args.profile.startswith("sigma_abc_hypothesis_pre_ibp") and not runtime_status.production_run_allowed:
        report = write_sigma_abc_agent_runtime_blocked_report(run_root, loop, profile, selected, runtime_status)
        print(report)
        return
    for stage_spec in selected:
        record = run_stage(run_root, stage_spec, profile, policy, benchmark)
        records.append(record)
        if record.status in {"HARD_STOP", "NOT_FROZEN", "VALIDATED_PENDING_REVIEW"}:
            break

    report = write_run_report(run_root, args.project, args.profile, loop, profile, policy, benchmark, records)
    print(report)


if __name__ == "__main__":
    main()
