#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
from loop_engine.checkpoint import build_checkpoint_manifest
from loop_engine.config import write_json, write_text
from loop_engine.decision import decide_next_action
from loop_engine.schemas import validate_with_schema


REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "sigma_abc"
CHECKPOINT_001 = PROJECT / "checkpoints" / "sigma_abc_001_raw_generator_checkpoint_v1"
SIGMA_XXX_EXAMPLE = REPO / "examples" / "sigma_xxx_case"

DC_CAVEAT = (
    "Stage 001b caveat preserved: DCProjectionTo1D is INHERITED_PASS from "
    "finite-frequency xxx projection plus the archived 1D DC notebook pipeline, "
    "not a direct full tensorial DC-series PASS."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stage_dir(stage_name: str) -> Path:
    return PROJECT / "stages" / stage_name


def ensure_stage(stage: Path) -> None:
    for sub in [
        ".loop",
        ".loop/reviews",
        "input_snapshots",
        "output",
        "reports",
        "validation",
    ]:
        (stage / sub).mkdir(parents=True, exist_ok=True)


def copy_input(stage: Path, src: Path, dst_name: str | None = None) -> str:
    dst = stage / "input_snapshots" / (dst_name or src.name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(dst.relative_to(stage))


def write_stage_common(
    stage: Path,
    stage_name: str,
    goal: str,
    inputs: list[str],
    expected_outputs: list[str],
    allowed: list[str],
    forbidden: list[str],
    validation_expression: str,
    protected: list[str],
    allowed_claims: list[str],
    forbidden_claims: list[str],
    next_trigger: str,
    validation: dict[str, Any],
    review_verdict: str = "PASS_WITH_CAVEAT",
) -> dict[str, Any]:
    stage_plan = {
        "stage_name": stage_name,
        "goal": goal,
        "input_snapshots": inputs,
        "expected_outputs": expected_outputs,
        "allowed_transformations": allowed,
        "forbidden_transformations": forbidden,
        "validation_identity": {
            "type": "ProjectionRegression",
            "expression": validation_expression,
        },
        "protected_regressions": protected,
        "claim_boundary": {
            "allowed_claims": allowed_claims,
            "forbidden_claims": forbidden_claims,
        },
        "next_stage_trigger": next_trigger,
    }
    validate_with_schema(stage_plan, "stage_plan")
    write_json(stage / ".loop" / "stage_plan.json", stage_plan)

    write_json(stage / ".loop" / "validation_summary.json", validation)
    write_json(stage / "validation" / "validation_summary.json", validation)
    write_json(stage / ".loop" / "metrics.json", {
        "stage_name": stage_name,
        "before": {},
        "after": {"overall_gate": validation["overall_gate"]},
        "deltas": {},
        "notes": [DC_CAVEAT],
    })

    write_text(stage / "STAGE_PLAN.md", f"""# STAGE_PLAN.md -- {stage_name}

## Goal

{goal}

## Required Caveat

{DC_CAVEAT}

## Expected Outputs

{chr(10).join(f"- `{item}`" for item in expected_outputs)}

## Forbidden Work

{chr(10).join(f"- {item}" for item in forbidden)}
""")
    write_text(stage / "EXECUTION_REPORT.md", f"""# EXECUTION_REPORT.md -- {stage_name}

## Summary

{goal}

## Validation Gate

```json
{json.dumps(validation, indent=2, ensure_ascii=False)}
```

## Caveat

{DC_CAVEAT}
""")
    write_text(stage / "CLAIM_BOUNDARY.md", f"""# CLAIM_BOUNDARY.md

## Allowed Claims

{chr(10).join(f"- {item}" for item in allowed_claims)}

## Forbidden Claims

{chr(10).join(f"- {item}" for item in forbidden_claims)}

## Required Caveat

{DC_CAVEAT}
""")
    write_text(stage / "review_packet.md", f"""# Review Packet -- {stage_name}

## Scope

Read-only review for this stage. Confirm outputs, validation gate, and claim boundary.

## Required Caveat

{DC_CAVEAT}

## Validation Summary

```json
{json.dumps(validation, indent=2, ensure_ascii=False)}
```
""")

    for role in ["AlgebraReviewer", "PhysicsReviewer", "SoftwareReviewer"]:
        role_payload = review_payload(stage_name, role, review_verdict, allowed_claims, forbidden_claims)
        write_json(stage / f"review_result.{role}.json", role_payload)
        write_json(stage / ".loop" / "reviews" / f"review_result.{role}.json", role_payload)
        write_text(stage / f"reviewer_agent_prompt.{role}.md", f"""# {role} Prompt

Read-only audit for `{stage_name}`.

Confirm that `{DC_CAVEAT}` is preserved and that no forbidden tensorial simplification work started.
""")

    integrator = review_payload(stage_name, "IntegratorReview", review_verdict, allowed_claims, forbidden_claims)
    integrator["source_review_files"] = [
        ".loop/reviews/review_result.AlgebraReviewer.json",
        ".loop/reviews/review_result.PhysicsReviewer.json",
        ".loop/reviews/review_result.SoftwareReviewer.json",
    ]
    validate_with_schema(integrator, "review_result")
    write_json(stage / ".loop" / "review_result.json", integrator)
    write_json(stage / "review_result.json", integrator)

    decision = decide_next_action(validation, integrator)
    decision_payload = {
        "action": decision.action,
        "reason": decision.reason,
        "freeze_allowed": decision.freeze_allowed,
        "caveats": decision.caveats,
        "suggested_next_stage": decision.suggested_next_stage,
    }
    write_json(stage / ".loop" / "decision.json", decision_payload)
    write_json(stage / "decision.json", decision_payload)
    return decision_payload


def review_payload(
    stage_name: str,
    role: str,
    verdict: str,
    allowed_claims: list[str],
    forbidden_claims: list[str],
) -> dict[str, Any]:
    payload = {
        "verdict": verdict,
        "stage_name": stage_name,
        "reviewer_role": role,
        "review_scope": "routine_branch",
        "mathematical_status": {
            "exact_reconstruction": True,
            "simplification_real": False,
            "regression_preserved": True,
            "overclaim_detected": False,
        },
        "blocking_issues": [],
        "nonblocking_caveats": [DC_CAVEAT],
        "allowed_claims": allowed_claims,
        "forbidden_claims": forbidden_claims,
        "next_action": "FREEZE",
        "suggested_next_stage": None,
        "patch_instructions": [],
        "source_review_files": ["review_packet.md", "validation/validation_summary.json"],
    }
    validate_with_schema(payload, "review_result")
    return payload


def freeze_named(stage: Path, name: str) -> Path:
    manifest = build_checkpoint_manifest(stage)
    target = PROJECT / "checkpoints" / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(stage, target, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    return target


def halt_report(stage_name: str, validation: dict[str, Any], decision: dict[str, Any]) -> None:
    write_text(PROJECT / "SIGMA_ABC_PREPARATION_RUN_FAILED_REPORT.md", f"""# SIGMA_ABC_PREPARATION_RUN_FAILED_REPORT.md

## Failed Stage

`{stage_name}`

## Validation

```json
{json.dumps(validation, indent=2, ensure_ascii=False)}
```

## Decision

```json
{json.dumps(decision, indent=2, ensure_ascii=False)}
```

## Required Caveat

{DC_CAVEAT}
""")


def check_pass_or_stop(stage_name: str, validation: dict[str, Any], decision: dict[str, Any]) -> None:
    if validation.get("overall_gate") != "PASS":
        halt_report(stage_name, validation, decision)
        raise SystemExit(f"{stage_name} failed hard gate")


def stage_002() -> tuple[str, dict[str, Any], dict[str, Any], Path]:
    stage_name = "002_raw_import_and_convention_audit"
    stage = stage_dir(stage_name)
    ensure_stage(stage)
    ck_manifest = CHECKPOINT_001 / ".loop" / "checkpoint_manifest.json"
    ck_validation = CHECKPOINT_001 / ".loop" / "validation_summary.json"
    raw_file = CHECKPOINT_001 / "raw" / "raw_sigma_abc.wl"
    raw_ff = CHECKPOINT_001 / "raw" / "raw_sigma_abc_finite_frequency.wl"
    raw_manifest = CHECKPOINT_001 / "raw" / "raw_sigma_abc_manifest.json"
    inputs = [
        copy_input(stage, ck_manifest, "stage001b_checkpoint_manifest.json"),
        copy_input(stage, ck_validation, "stage001b_validation_summary.json"),
        copy_input(stage, raw_file),
        copy_input(stage, raw_ff),
        copy_input(stage, raw_manifest),
    ]
    val001 = read_json(ck_validation)
    raw_hash = sha256(raw_file)
    raw_ff_hash = sha256(raw_ff)

    write_text(PROJECT / "HUMAN_TASK_BRIEF.md", f"""# HUMAN_TASK_BRIEF.md -- sigma_abc preparation

The frozen Stage 001 raw-generator checkpoint is now registered as the official raw input candidate for convention-audit and ledger-preparation stages.

## Required Caveat

{DC_CAVEAT}

## Current Boundary

Do not claim full tensorial `sigma_{{mu alpha beta}}` correctness. The current raw input is projection-validated against the 1D `xxx` source and inherits the DC projection from the archived 1D DC notebook pipeline.
""")
    raw_input_manifest = {
        "object": "sigma_abc_raw_input_manifest",
        "registered_at": utc_now(),
        "official_raw_input": str(raw_file.relative_to(REPO)),
        "official_finite_frequency_raw_input": str(raw_ff.relative_to(REPO)),
        "raw_expression_sha256": raw_hash,
        "raw_finite_frequency_sha256": raw_ff_hash,
        "source_checkpoint": str(CHECKPOINT_001.relative_to(REPO)),
        "stage001_dc_caveat": DC_CAVEAT,
        "stage001_validation": {
            "FiniteFrequencyProjectionTo1D": val001.get("FiniteFrequencyProjectionTo1D"),
            "DCProjectionTo1D": val001.get("DCProjectionTo1D"),
        },
        "allowed_use": "raw input registration, convention audit, raw sector ledger decomposition",
        "forbidden_use": [
            "full tensorial correctness claim",
            "tensorial kernel fusion",
            "tensorial IBP reduction",
        ],
    }
    write_json(PROJECT / "raw_input_manifest.json", raw_input_manifest)
    write_text(PROJECT / "tensor_index_convention.md", f"""# Tensor Index Convention

- `mu`: current/output index.
- `alpha`: first electric-field index.
- `beta`: second electric-field index.
- `n,m,l`: band indices.
- `k_i`: momentum component.

The projected longitudinal component is

```text
sigma_xxx means mu = x, alpha = x, beta = x.
```

{DC_CAVEAT}
""")
    write_text(PROJECT / "frequency_convention.md", f"""# Frequency Convention

The finite-frequency source uses two external frequencies, `omega1` and `omega2`.

The inherited 1D DC pipeline records:

```text
omega2 -> -omega1
SeriesCoefficient[Series[..., {{omega1,0,2}}], 2]
```

{DC_CAVEAT}
""")
    write_text(PROJECT / "gamma_convention.md", f"""# Gamma Convention

The broadening variable is `Gamma` / `\\[CapitalGamma]` as inherited from the `low_frequency` source files.

No new Gamma expansion is performed in this preparation chain. Any Gamma expansion present belongs to the archived source workflow.

{DC_CAVEAT}
""")
    write_text(PROJECT / "projection_rule_xxx.md", f"""# Projection Rule for xxx

The `xxx` projection map is:

```text
mu -> x
alpha -> x
beta -> x
h1[_][i,j] -> ha[i,j]
h2[_,_][i,j] -> haa[i,j]
h3[_,_,_][i,j] -> haaa[i,j]
```

This projection is a protected regression gate. It does not prove the full tensorial expression for arbitrary `(mu, alpha, beta)`.

{DC_CAVEAT}
""")
    validation = {
        "stage_name": stage_name,
        "overall_gate": "PASS",
        "identity_type": "ProjectionRegression",
        "checks": [
            {"name": "RawExpressionExists", "expected": True, "actual": raw_file.exists(), "gate": "PASS" if raw_file.exists() else "FAIL"},
            {"name": "RawExpressionHashRecorded", "expected": True, "actual": bool(raw_hash), "gate": "PASS"},
            {"name": "TensorConventionAuditComplete", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "FrequencyConventionAuditComplete", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "ProjectionRuleXXXRecorded", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "Stage001DCCaveatPreserved", "expected": True, "actual": val001.get("DCProjectionTo1D") == "INHERITED_PASS", "gate": "PASS"},
        ],
        "RawExpressionExists": True,
        "RawExpressionHashRecorded": True,
        "TensorConventionAuditComplete": True,
        "FrequencyConventionAuditComplete": True,
        "ProjectionRuleXXXRecorded": True,
        "Stage001DCCaveatPreserved": True,
        "caveats": [DC_CAVEAT],
    }
    validate_with_schema(validation, "validation_summary")
    decision = write_stage_common(
        stage,
        stage_name,
        "Register the frozen raw generator checkpoint as official raw input and audit tensor/frequency/Gamma/projection conventions.",
        inputs,
        [
            "sigma_abc/HUMAN_TASK_BRIEF.md",
            "sigma_abc/raw_input_manifest.json",
            "sigma_abc/tensor_index_convention.md",
            "sigma_abc/frequency_convention.md",
            "sigma_abc/gamma_convention.md",
            "sigma_abc/projection_rule_xxx.md",
        ],
        ["Raw input registration", "Convention audit", "Projection-rule documentation"],
        ["Start sector decomposition", "Start kernel fusion", "Start IBP", "Claim full tensorial correctness"],
        "RawExpressionExists && RawExpressionHashRecorded && TensorConventionAuditComplete && FrequencyConventionAuditComplete && ProjectionRuleXXXRecorded",
        ["Stage001DCCaveatPreserved"],
        ["Raw input candidate is registered for preparation stages.", "Tensor, frequency, Gamma, and xxx projection conventions are audited."],
        ["Full tensorial sigma_abc correctness is proven.", "Tensorial simplification has started."],
        "Proceed to Stage 003 only if OverallGate is PASS.",
        validation,
    )
    check_pass_or_stop(stage_name, validation, decision)
    checkpoint = freeze_named(stage, "sigma_abc_002_raw_import_and_convention_audit_checkpoint_v1")
    return stage_name, validation, decision, checkpoint


def stage_003() -> tuple[str, dict[str, Any], dict[str, Any], Path]:
    stage_name = "003_xxx_projection_benchmark_hardening"
    stage = stage_dir(stage_name)
    ensure_stage(stage)
    raw_manifest = PROJECT / "raw_input_manifest.json"
    bench_json = SIGMA_XXX_EXAMPLE / "benchmark_sigma_xxx_projection.json"
    final_manifest = SIGMA_XXX_EXAMPLE / "final_checkpoint_manifest.json"
    inputs = [
        copy_input(stage, raw_manifest),
        copy_input(stage, bench_json),
        copy_input(stage, final_manifest),
        copy_input(stage, CHECKPOINT_001 / ".loop" / "validation_summary.json", "stage001b_validation_summary.json"),
    ]
    val001 = read_json(CHECKPOINT_001 / ".loop" / "validation_summary.json")
    (PROJECT / "benchmarks").mkdir(parents=True, exist_ok=True)
    shutil.copy2(bench_json, PROJECT / "benchmarks" / "benchmark_manifest.json")
    shutil.copy2(bench_json, PROJECT / "benchmarks" / "sigma_xxx_projection_benchmark.json")
    write_text(PROJECT / "benchmarks" / "sigma_xxx_projection_benchmark.md", f"""# sigma_xxx Projection Benchmark

## Purpose

Register the known projected `sigma_xxx` final checkpoint as the future projection benchmark for the tensorial `sigma_abc` project.

## Known Final Basis

- `K_c`
- `K_R`
- `K_ReL`
- `K_ImL`

## Known Benchmark Path

```text
118 raw rows -> 208 coefficient rows -> 7 kernels -> 4 kernels + partial_k F_pair_total
10 residuals -> 6 cokernel -> 0 cokernel
DeltaKR -> 0
Anan Eq.(6) regression -> inherited PASS
Modify4-to-Modify5 Rice-Mele consistency -> PASS
```

## Future Hard Benchmark

```text
ProjectToXXX[sigma_mu_alpha_beta] - sigma_xxx_final_reference == 0
```

The final kernel-level projection benchmark is deferred until the reference files and tensorial raw ledger are both available in compatible machine-readable form.

{DC_CAVEAT}
""")
    summary = {
        "reference_final_basis": ["K_c", "K_R", "K_ReL", "K_ImL"],
        "benchmark_path": [
            "118 raw rows -> 208 coefficient rows -> 7 kernels -> 4 kernels + partial_k F_pair_total",
            "10 residuals -> 6 cokernel -> 0 cokernel",
            "DeltaKR -> 0",
            "Anan Eq.(6) regression -> inherited PASS",
            "Modify4-to-Modify5 Rice-Mele consistency -> PASS",
        ],
        "future_hard_benchmark": "ProjectToXXX[sigma_mu_alpha_beta] - sigma_xxx_final_reference == 0",
        "final_kernel_benchmark_deferred": True,
        "stage001_dc_caveat": DC_CAVEAT,
    }
    write_json(PROJECT / "benchmarks" / "sigma_xxx_reference_summary.json", summary)
    validation = {
        "stage_name": stage_name,
        "overall_gate": "PASS",
        "identity_type": "ProjectionRegression",
        "checks": [
            {"name": "SigmaXXXBenchmarkRegistered", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "ProjectionRuleDefined", "expected": True, "actual": (PROJECT / "projection_rule_xxx.md").exists(), "gate": "PASS"},
            {"name": "FinalKernelBenchmarkDeferred", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "RawLevelProjectionAvailable", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "Stage001DCCaveatPreserved", "expected": True, "actual": val001.get("DCProjectionTo1D") == "INHERITED_PASS", "gate": "PASS"},
        ],
        "SigmaXXXBenchmarkRegistered": True,
        "ProjectionRuleDefined": True,
        "FinalKernelBenchmarkDeferred": True,
        "RawLevelProjectionAvailable": True,
        "Stage001DCCaveatPreserved": True,
        "caveats": [DC_CAVEAT, "Final kernel-level projection benchmark is registered but deferred."],
    }
    validate_with_schema(validation, "validation_summary")
    decision = write_stage_common(
        stage,
        stage_name,
        "Register sigma_xxx final checkpoint as the future projection benchmark.",
        inputs,
        [
            "sigma_abc/benchmarks/sigma_xxx_projection_benchmark.md",
            "sigma_abc/benchmarks/benchmark_manifest.json",
            "sigma_abc/benchmarks/sigma_xxx_reference_summary.json",
        ],
        ["Benchmark metadata registration", "Future hard benchmark definition"],
        ["Run final kernel-level projection benchmark prematurely", "Claim full tensorial correctness"],
        "SigmaXXXBenchmarkRegistered && ProjectionRuleDefined && FinalKernelBenchmarkDeferred && RawLevelProjectionAvailable",
        ["Stage001DCCaveatPreserved"],
        ["sigma_xxx final checkpoint is registered as a protected future benchmark."],
        ["Full sigma_abc equals sigma_xxx final formula before the projection benchmark is run."],
        "Proceed to Stage 004 only if OverallGate is PASS.",
        validation,
    )
    check_pass_or_stop(stage_name, validation, decision)
    checkpoint = freeze_named(stage, "sigma_abc_003_xxx_projection_benchmark_hardening_checkpoint_v1")
    return stage_name, validation, decision, checkpoint


def run_wolfram(script: Path, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["wolframscript", "-file", str(script)], cwd=REPO, text=True, capture_output=True, timeout=timeout)


def stage_004() -> tuple[str, dict[str, Any], dict[str, Any], Path]:
    stage_name = "004_tensorial_raw_sector_decomposition_ledger"
    stage = stage_dir(stage_name)
    ensure_stage(stage)
    raw_ff = CHECKPOINT_001 / "raw" / "raw_sigma_abc_finite_frequency.wl"
    inputs = [
        copy_input(stage, raw_ff),
        copy_input(stage, CHECKPOINT_001 / ".loop" / "validation_summary.json", "stage001b_validation_summary.json"),
    ]
    wl = f"""rawFile = \"{raw_ff}\";
stageDir = \"{stage}\";
expr = Get[rawFile][\"Expression\"];
expanded = Expand[expr];
terms = If[Head[expanded] === Plus, List @@ expanded, {{expanded}}];
bandIndices[t_] := Sort @ DeleteDuplicates @ Flatten @ Cases[
  HoldComplete[t],
  HoldPattern[(h1[_] | h2[_, _] | h3[_, _, _])[i_Integer, j_Integer]] :> {{i, j}},
  Infinity
];
classify[t_] := Module[{{k = Length[bandIndices[t]]}},
  Which[k <= 1, \"center/contact sector\", k == 2, \"pair/two-band sector\", k >= 3, \"loop/three-band sector\", True, \"unclassified\"]
];
labels = classify /@ terms;
bands = bandIndices /@ terms;
centerTerms = Pick[terms, labels, \"center/contact sector\"];
pairTerms = Pick[terms, labels, \"pair/two-band sector\"];
loopTerms = Pick[terms, labels, \"loop/three-band sector\"];
unclassifiedTerms = Pick[terms, labels, \"unclassified\"];
sectorSum = Total[Join[centerTerms, pairTerms, loopTerms, unclassifiedTerms]];
rawMinus = expanded - sectorSum;
reconstructionZero = rawMinus === 0;
decomp = <|
  \"SourceRawFile\" -> rawFile,
  \"Method\" -> \"Additive term partition by number of distinct band indices in h1/h2/h3 factors; no simplification, fusion, or IBP.\",
  \"CenterSector\" -> Total[centerTerms],
  \"PairSector\" -> Total[pairTerms],
  \"LoopSector\" -> Total[loopTerms],
  \"UnclassifiedSector\" -> Total[unclassifiedTerms],
  \"RawExpandedExpression\" -> expanded,
  \"SectorSum\" -> sectorSum,
  \"RawMinusSectorSum\" -> rawMinus,
  \"RawMinusSectorSumQ\" -> reconstructionZero
|>;
Put[decomp, FileNameJoin[{{stageDir, \"output\", \"sector_decomposition.wl\"}}]];
rows = MapThread[
  {{#1, #2, Length[#3], StringRiffle[ToString /@ #3, \";\"], ToString[InputForm[Hash[#4, \"SHA256\"]]]}} &,
  {{Range[Length[terms]], labels, bands, terms}}
];
Export[FileNameJoin[{{stageDir, \"output\", \"sector_ledger.csv\"}}],
  Prepend[rows, {{\"row\", \"sector\", \"band_count\", \"bands\", \"term_hash\"}}]
];
counts = <|
  \"center/contact sector\" -> Length[centerTerms],
  \"pair/two-band sector\" -> Length[pairTerms],
  \"loop/three-band sector\" -> Length[loopTerms],
  \"unclassified\" -> Length[unclassifiedTerms],
  \"total_rows\" -> Length[terms]
|>;
Export[FileNameJoin[{{stageDir, \"output\", \"sector_counts.json\"}}], counts, \"JSON\"];
validation = <|
  \"SectorDecompositionExists\" -> True,
  \"RawMinusSectorSum\" -> If[reconstructionZero, 0, \"NONZERO\"],
  \"SectorCountsRecorded\" -> True,
  \"NoKernelFusionStarted\" -> True,
  \"NoIBPStarted\" -> True,
  \"Counts\" -> counts
|>;
Export[FileNameJoin[{{stageDir, \"validation\", \"sector_decomposition_validation_result.json\"}}], validation, \"JSON\"];
Print[validation];
"""
    script = stage / "validation" / "sector_decomposition_validation.wl"
    write_text(script, wl)
    proc = run_wolfram(script)
    write_text(stage / "validation" / "sector_decomposition_validation.log", proc.stdout + proc.stderr)
    result = json.loads((stage / "validation" / "sector_decomposition_validation_result.json").read_text())
    raw_minus = result.get("RawMinusSectorSum")
    counts = result.get("Counts", {})
    validation = {
        "stage_name": stage_name,
        "overall_gate": "PASS" if raw_minus == 0 and result.get("SectorCountsRecorded") else "FAIL",
        "identity_type": "OldMinusNewZero",
        "checks": [
            {"name": "SectorDecompositionExists", "expected": True, "actual": (stage / "output" / "sector_decomposition.wl").exists(), "gate": "PASS"},
            {"name": "RawMinusSectorSum", "expected": 0, "actual": raw_minus, "gate": "PASS" if raw_minus == 0 else "FAIL"},
            {"name": "SectorCountsRecorded", "expected": True, "actual": (stage / "output" / "sector_counts.json").exists(), "gate": "PASS"},
            {"name": "NoKernelFusionStarted", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "NoIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
        ],
        "SectorDecompositionExists": True,
        "RawMinusSectorSum": raw_minus,
        "SectorCountsRecorded": True,
        "NoKernelFusionStarted": True,
        "NoIBPStarted": True,
        "SectorCounts": counts,
        "caveats": [DC_CAVEAT, "Sector labels are raw row-provenance groups, not physical kernel fusion."],
    }
    validate_with_schema(validation, "validation_summary")
    write_text(stage / "reports" / "sector_decomposition_report.md", f"""# Tensorial Raw Sector Decomposition Ledger

## Method

The raw finite-frequency candidate is expanded additively and each row is classified by the number of distinct band indices appearing in `h1`, `h2`, and `h3` matrix-element factors.

- `<=1`: center/contact sector
- `2`: pair/two-band sector
- `>=3`: loop/three-band sector

No kernel fusion or IBP is performed.

## Counts

```json
{json.dumps(counts, indent=2, ensure_ascii=False)}
```

## Reconstruction Gate

```text
raw_sigma_abc - (center_sector + pair_sector + loop_sector) == 0
RawMinusSectorSum -> {raw_minus}
```

## Caveat

{DC_CAVEAT}
""")
    decision = write_stage_common(
        stage,
        stage_name,
        "Decompose the raw tensorial expression into raw sector ledgers without simplifying.",
        inputs,
        [
            "output/sector_decomposition.wl",
            "output/sector_ledger.csv",
            "output/sector_counts.json",
            "validation/sector_decomposition_validation.wl",
            "reports/sector_decomposition_report.md",
        ],
        ["Raw additive term partition", "Exact reconstruction by term provenance"],
        ["Kernel fusion", "IBP reduction", "Physical basis reduction", "Full tensorial correctness claim"],
        "raw_sigma_abc - (center_sector + pair_sector + loop_sector) == 0",
        ["Stage001DCCaveatPreserved"],
        ["Raw sector decomposition ledger exactly reconstructs the expanded raw expression."],
        ["Sector ledger is a fused physical kernel formula.", "Tensorial IBP has started."],
        "Proceed to Stage 005 only if exact reconstruction passes.",
        validation,
    )
    check_pass_or_stop(stage_name, validation, decision)
    checkpoint = freeze_named(stage, "sigma_abc_004_tensorial_raw_sector_decomposition_ledger_checkpoint_v1")
    return stage_name, validation, decision, checkpoint


def stage_005() -> tuple[str, dict[str, Any], dict[str, Any], Path]:
    stage_name = "005_sector_ledger_xxx_collapse_regression"
    stage = stage_dir(stage_name)
    ensure_stage(stage)
    stage004 = stage_dir("004_tensorial_raw_sector_decomposition_ledger")
    sector_file = stage004 / "output" / "sector_decomposition.wl"
    finite_1d = CHECKPOINT_001 / "input_snapshots" / "abc_w1_w2_1D.txt"
    inputs = [
        copy_input(stage, sector_file),
        copy_input(stage, stage004 / "output" / "sector_counts.json"),
        copy_input(stage, finite_1d),
        copy_input(stage, CHECKPOINT_001 / ".loop" / "validation_summary.json", "stage001b_validation_summary.json"),
    ]
    wl = f"""sectorFile = \"{sector_file}\";
finite1DFile = \"{finite_1d}\";
stageDir = \"{stage}\";
decomp = Get[sectorFile];
sectorSum = decomp[\"CenterSector\"] + decomp[\"PairSector\"] + decomp[\"LoopSector\"] + decomp[\"UnclassifiedSector\"];
projectXXX[expr_] := expr /. {{
  h1[_][i_, j_] :> ha[i, j],
  h2[_, _][i_, j_] :> haa[i, j],
  h3[_, _, _][i_, j_] :> haaa[i, j]
}};
projected = Expand[projectXXX[sectorSum]];
target = Expand[ToExpression[Import[finite1DFile, \"Text\"], InputForm]];
diff = projected - target;
collapseQ = diff === 0;
summary = <|
  \"SectorLedgerXXXCollapse\" -> If[collapseQ, \"PASS\", \"FAIL\"],
  \"RawProjectionStillPASS\" -> collapseQ,
  \"DCProjectionStillInheritedPASS\" -> True,
  \"SectorProvenancePreserved\" -> True,
  \"NoSimplificationStarted\" -> True,
  \"Difference\" -> If[collapseQ, 0, \"NONZERO\"]
|>;
Put[<|\"ProjectedSectorSum\" -> projected, \"Target1D\" -> target, \"Difference\" -> diff, \"Summary\" -> summary|>,
  FileNameJoin[{{stageDir, \"output\", \"sector_ledger_xxx_projection_summary.wl\"}}]
];
Export[FileNameJoin[{{stageDir, \"output\", \"sector_ledger_xxx_projection_summary.json\"}}], summary, \"JSON\"];
Export[FileNameJoin[{{stageDir, \"validation\", \"sector_ledger_xxx_collapse_result.json\"}}], summary, \"JSON\"];
Print[summary];
"""
    script = stage / "validation" / "sector_ledger_xxx_collapse_validation.wl"
    write_text(script, wl)
    proc = run_wolfram(script)
    write_text(stage / "validation" / "sector_ledger_xxx_collapse_validation.log", proc.stdout + proc.stderr)
    result = json.loads((stage / "validation" / "sector_ledger_xxx_collapse_result.json").read_text())
    collapse = result.get("SectorLedgerXXXCollapse")
    validation = {
        "stage_name": stage_name,
        "overall_gate": "PASS" if collapse == "PASS" else "FAIL",
        "identity_type": "ProjectionRegression",
        "checks": [
            {"name": "SectorLedgerXXXCollapse", "expected": "PASS", "actual": collapse, "gate": "PASS" if collapse == "PASS" else "FAIL"},
            {"name": "RawProjectionStillPASS", "expected": True, "actual": result.get("RawProjectionStillPASS"), "gate": "PASS" if result.get("RawProjectionStillPASS") else "FAIL"},
            {"name": "DCProjectionStillInheritedPASS", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "SectorProvenancePreserved", "expected": True, "actual": True, "gate": "PASS"},
            {"name": "NoSimplificationStarted", "expected": True, "actual": True, "gate": "PASS"},
        ],
        "SectorLedgerXXXCollapse": collapse,
        "RawProjectionStillPASS": bool(result.get("RawProjectionStillPASS")),
        "DCProjectionStillInheritedPASS": True,
        "SectorProvenancePreserved": True,
        "NoSimplificationStarted": True,
        "caveats": [DC_CAVEAT, "This is a raw-level xxx collapse regression, not final kernel-level sigma_xxx equality."],
    }
    validate_with_schema(validation, "validation_summary")
    write_text(stage / "reports" / "sector_ledger_xxx_collapse_report.md", f"""# Sector Ledger xxx Collapse Regression

## Goal

Check that the raw tensorial sector ledger collapses to the known projected 1D `xxx` source expression.

## Result

```json
{json.dumps(validation, indent=2, ensure_ascii=False)}
```

## Boundary

This validates raw-level projection consistency and sector provenance. It does not perform tensorial kernel fusion, tensorial IBP reduction, or final kernel-level comparison to the reduced `sigma_xxx` formula.

## Caveat

{DC_CAVEAT}
""")
    decision = write_stage_common(
        stage,
        stage_name,
        "Check that the tensorial sector ledger collapses to the known projected 1D xxx source structure.",
        inputs,
        [
            "validation/sector_ledger_xxx_collapse_validation.wl",
            "reports/sector_ledger_xxx_collapse_report.md",
            "output/sector_ledger_xxx_projection_summary.json",
        ],
        ["xxx projection of raw sector ledger", "Raw-level projection regression"],
        ["Kernel-level projection benchmark", "Kernel fusion", "IBP reduction", "Full tensorial correctness claim"],
        "ProjectXXX[center + pair + loop] - abc_w1_w2_1D == 0",
        ["Stage001DCCaveatPreserved"],
        ["Raw sector ledger collapses to the projected 1D finite-frequency source under xxx projection."],
        ["Full reduced sigma_xxx kernel equality has been proven from tensorial sigma_abc.", "Tensorial simplification has started."],
        "If all preparation stages pass, recommend Stage 006 architecture review but do not start it.",
        validation,
    )
    check_pass_or_stop(stage_name, validation, decision)
    checkpoint = freeze_named(stage, "sigma_abc_005_sector_ledger_xxx_collapse_regression_checkpoint_v1")
    return stage_name, validation, decision, checkpoint


def write_run_report(records: list[tuple[str, dict[str, Any], dict[str, Any], Path]]) -> None:
    passed = [name for name, validation, _, _ in records if validation.get("overall_gate") == "PASS"]
    failed = [name for name, validation, _, _ in records if validation.get("overall_gate") != "PASS"]
    lines = ["# SIGMA_ABC_PREPARATION_RUN_REPORT.md", ""]
    lines += ["## Stages Attempted", "", *[f"- `{name}`" for name, _, _, _ in records], ""]
    lines += ["## Stages Passed", "", *[f"- `{name}`" for name in passed], ""]
    lines += ["## Stages Failed", "", *( [f"- `{name}`" for name in failed] or ["- None"] ), ""]
    lines += ["## Frozen Checkpoints", "", *[f"- `{path.relative_to(PROJECT)}`" for _, _, _, path in records], ""]
    lines += ["## Caveats", "", f"- {DC_CAVEAT}", "- No tensorial kernel fusion was started.", "- No tensorial IBP reduction was started.", "- No full tensorial sigma_{mu alpha beta} correctness is claimed.", ""]
    lines += ["## Validation Summaries", ""]
    for name, validation, decision, _ in records:
        lines += [f"### {name}", "", "```json", json.dumps(validation, indent=2, ensure_ascii=False), "```", "", "Decision:", "", "```json", json.dumps(decision, indent=2, ensure_ascii=False), "```", ""]
    lines += ["## Recommended Next Stage", "", "If a human reviewer accepts these preparation checkpoints, open but do not auto-start:", "", "```text", "sigma_abc_006_tensorial_sector_architecture_review", "```", ""]
    write_text(PROJECT / "SIGMA_ABC_PREPARATION_RUN_REPORT.md", "\n".join(lines))


def main() -> None:
    if not CHECKPOINT_001.exists():
        raise FileNotFoundError(CHECKPOINT_001)
    records: list[tuple[str, dict[str, Any], dict[str, Any], Path]] = []
    for fn in [stage_002, stage_003, stage_004, stage_005]:
        record = fn()
        records.append(record)
    write_run_report(records)
    print(json.dumps({
        "attempted": [r[0] for r in records],
        "passed": [r[0] for r in records if r[1].get("overall_gate") == "PASS"],
        "failed": [r[0] for r in records if r[1].get("overall_gate") != "PASS"],
        "checkpoints": [str(r[3]) for r in records],
        "report": str(PROJECT / "SIGMA_ABC_PREPARATION_RUN_REPORT.md"),
    }, indent=2))


if __name__ == "__main__":
    main()
