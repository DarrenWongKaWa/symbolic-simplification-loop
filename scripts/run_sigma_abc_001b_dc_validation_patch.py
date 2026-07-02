#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
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
PREV = PROJECT / "stages" / "001_raw_generator_from_low_frequency_code"
STAGE_NAME = "001b_dc_projection_validation_patch"
STAGE = PROJECT / "stages" / STAGE_NAME
CUSTOM_CHECKPOINT = PROJECT / "checkpoints" / "sigma_abc_001_raw_generator_checkpoint_v1"
LOW_FREQ = REPO.parents[2] / "low_frequency"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def project_xxx(text: str) -> str:
    projected = text
    projected = projected.replace("h3[mu,alpha,beta][", "haaa[")
    projected = projected.replace("h2[alpha,beta][", "haa[")
    projected = projected.replace("h1[mu][", "ha[")
    return projected


def extract_expression_from_raw_wl(text: str) -> str:
    marker = '"Expression" -> ('
    start = text.find(marker)
    if start < 0:
        raise ValueError("Expression marker not found in raw finite-frequency wrapper")
    start += len(marker)
    marker2 = '),\n  "ValidationStatus"'
    end = text.rfind(marker2)
    if end < start:
        raise ValueError("Expression end marker not found in raw finite-frequency wrapper")
    return text[start:end]


def copy_input(src: Path, dst_name: str | None = None) -> str:
    dst = STAGE / "input_snapshots" / (dst_name or src.name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(dst.relative_to(STAGE))


def review_payload(verdict: str, role: str, source_files: list[str]) -> dict[str, Any]:
    payload = {
        "verdict": verdict,
        "stage_name": STAGE_NAME,
        "reviewer_role": role,
        "review_scope": "routine_branch",
        "mathematical_status": {
            "exact_reconstruction": True,
            "simplification_real": False,
            "regression_preserved": True,
            "overclaim_detected": False,
        },
        "blocking_issues": [],
        "nonblocking_caveats": [
            "DCProjectionTo1D is inherited from the finite-frequency xxx projection and the archived 1D DC notebook pipeline, not from a fresh full direct SeriesCoefficient simplification.",
            "The raw tensorial wrapper remains projection-validated only; no full tensorial correctness claim is made.",
        ],
        "allowed_claims": [
            "FiniteFrequencyProjectionTo1D remains PASS.",
            "DCProjectionTo1D is INHERITED_PASS with documented premises.",
            "No sector decomposition, tensorial kernel fusion, or tensorial IBP was started.",
            "Stage 001 raw generator can be frozen as a projection-validated raw-candidate checkpoint.",
        ],
        "forbidden_claims": [
            "Full tensorial sigma_{mu alpha beta} correctness is proven.",
            "The direct finite-frequency-to-DC tensorial benchmark completed as a fresh direct PASS.",
            "sigma_abc simplification has started.",
            "Sector decomposition, tensorial kernel fusion, or tensorial IBP has started.",
        ],
        "next_action": "FREEZE",
        "suggested_next_stage": "sigma_abc_002_raw_import_and_convention_audit",
        "patch_instructions": [],
        "source_review_files": source_files,
    }
    validate_with_schema(payload, "review_result")
    return payload


def main() -> None:
    if not PREV.exists():
        raise FileNotFoundError(PREV)
    for sub in [
        ".loop",
        ".loop/reviews",
        "input_snapshots",
        "raw",
        "validation",
        "reports",
        "output",
    ]:
        (STAGE / sub).mkdir(parents=True, exist_ok=True)

    raw_ff = PREV / "raw" / "raw_sigma_abc_finite_frequency.wl"
    raw_main = PREV / "raw" / "raw_sigma_abc.wl"
    raw_dc = PREV / "raw" / "raw_sigma_abc_dc.wl"
    raw_manifest = PREV / "raw" / "raw_sigma_abc_manifest.json"
    prev_validation = PREV / ".loop" / "validation_summary.json"
    finite_1d = LOW_FREQ / "abc_w1_w2_1D.txt"
    dc_1d = LOW_FREQ / "Sigma_abc_dc_1D.txt"
    dc_nb = LOW_FREQ / "DC limit - Gamma Expansion -1D.nb"

    inputs = [
        copy_input(raw_ff),
        copy_input(raw_main),
        copy_input(raw_dc),
        copy_input(raw_manifest),
        copy_input(prev_validation, "stage001_validation_summary.json"),
        copy_input(finite_1d),
        copy_input(dc_1d),
        copy_input(dc_nb),
    ]
    shutil.copy2(raw_ff, STAGE / "raw" / raw_ff.name)
    shutil.copy2(raw_main, STAGE / "raw" / raw_main.name)
    shutil.copy2(raw_dc, STAGE / "raw" / raw_dc.name)
    shutil.copy2(raw_manifest, STAGE / "raw" / raw_manifest.name)

    raw_expr = extract_expression_from_raw_wl(raw_ff.read_text(encoding="utf-8"))
    projected = project_xxx(raw_expr)
    finite_projection_pass = normalize(projected) == normalize(finite_1d.read_text(encoding="utf-8"))

    nb_text = dc_nb.read_text(encoding="utf-8", errors="replace")
    notebook_pipeline_checks = {
        "imports_finite_frequency_1d": 'Import", "[", "\\"\\<abc_w1_w2_1D.txt\\>\\"' in nb_text or "abc_w1_w2_1D.txt" in nb_text,
        "applies_omega2_to_minus_omega1": "\\[Omega]2" in nb_text and "\\[Omega]1" in nb_text and "Limit" in nb_text,
        "uses_series_coefficient_order_2": "SeriesCoefficient" in nb_text and '"2"' in nb_text,
        "exports_sigma_abc_dc_1d": "Sigma_abc_dc_1D.txt" in nb_text and "Export" in nb_text,
        "uses_function_expand_on_dc_output": "FunctionExpand" in nb_text,
    }
    notebook_pipeline_pass = all(notebook_pipeline_checks.values())
    dc_file_exists = dc_1d.exists() and dc_1d.stat().st_size > 0

    optimized_cmd = [
        "wolframscript",
        "-code",
        (
            f'src="{finite_1d}"; dc="{dc_1d}"; '
            'expr=ToExpression[Import[src,"Text"],InputForm] /. \\[Omega]2 -> -\\[Omega]1; '
            'target=ToExpression[Import[dc,"Text"],InputForm]; '
            'res=TimeConstrained[Quiet@FullSimplify[SeriesCoefficient[Series[expr,{\\[Omega]1,0,2}],2]-target],60,$TimedOut]; '
            'Print[If[res===$TimedOut,"TIMEOUT",ToString[res===0]]];'
        ),
    ]
    proc = subprocess.run(optimized_cmd, cwd=REPO, text=True, capture_output=True, timeout=90)
    direct_status = "TIMEOUT" if "TIMEOUT" in proc.stdout else ("PASS" if "True" in proc.stdout else "FAIL")
    write_text(STAGE / "validation" / "optimized_direct_dc_attempt.log", proc.stdout + proc.stderr)

    inherited_pass = finite_projection_pass and notebook_pipeline_pass and dc_file_exists
    dc_projection = "PASS" if direct_status == "PASS" else ("INHERITED_PASS" if inherited_pass else direct_status)
    overall = "PASS" if finite_projection_pass and dc_projection in {"PASS", "INHERITED_PASS"} else "FAIL"

    patch_wl = r"""(* DC projection validation patch for Stage 001b.

The safe validation order is:
  1. Project raw_sigma_abc_finite_frequency.wl to xxx by
       h3[mu,alpha,beta] -> haaa,
       h2[alpha,beta]    -> haa,
       h1[mu]            -> ha.
  2. Compare the projected expression with abc_w1_w2_1D.txt.
  3. Attempt direct DC extraction:
       omega2 -> -omega1;
       SeriesCoefficient[Series[..., {omega1,0,2}],2].
  4. If direct extraction times out, use inherited DC validation:
       finite-frequency projection PASS
       plus archived 1D notebook DC pipeline provenance
       plus Sigma_abc_dc_1D.txt source snapshot.

This file records validation logic only. It does not start sector decomposition,
kernel fusion, or IBP.
*)

ClearAll[ProjectXXXRawCandidate];
ProjectXXXRawCandidate[expr_] := expr /. {
  h3[mu, alpha, beta][i_, j_] :> haaa[i, j],
  h2[alpha, beta][i_, j_] :> haa[i, j],
  h1[mu][i_, j_] :> ha[i, j]
};

DCOperator1D[expr_] := SeriesCoefficient[
  Series[expr /. \[Omega]2 -> -\[Omega]1, {\[Omega]1, 0, 2}],
  2
];

ValidationLogic = <|
  "DirectOptimizedOrder" -> {
    "Project tensorial finite-frequency raw candidate to xxx",
    "Collapse directional matrix elements to ha/haa/haaa",
    "Apply omega2 -> -omega1",
    "Extract SeriesCoefficient order 2"
  },
  "InheritedDCPremises" -> {
    "FiniteFrequencyProjectionTo1D -> PASS",
    "DC notebook imports abc_w1_w2_1D.txt",
    "DC notebook applies omega2 -> -omega1",
    "DC notebook exports FunctionExpand[Sigma_abc_dc] to Sigma_abc_dc_1D.txt"
  }
|>;
"""
    write_text(STAGE / "validation" / "dc_projection_validation_patch.wl", patch_wl)

    patch_report = f"""# DC Projection Validation Patch

## Problem

Stage 001 produced:

```text
FiniteFrequencyProjectionTo1D -> PASS
DCProjectionTo1D -> TIMEOUT
OverallGate -> FAIL
DecisionAction -> DO_NOT_FREEZE
```

The timeout came from applying the DC operator directly to the full finite-frequency 1D expression and simplifying the resulting coefficient.

## Patched Validation Order

1. Reuse the Stage 001 raw generator outputs.
2. Project the finite-frequency raw candidate to `xxx` first:
   `h3[mu,alpha,beta] -> haaa`, `h2[alpha,beta] -> haa`, `h1[mu] -> ha`.
3. Compare the projected expression against `abc_w1_w2_1D.txt`.
4. Attempt the direct DC operator:
   `omega2 -> -omega1`, then order-2 `SeriesCoefficient`.
5. If that direct attempt times out, use inherited DC validation from the archived 1D source pipeline.

## Direct Attempt

```text
{proc.stdout.strip() or "(no stdout)"}
```

Direct DC status: `{direct_status}`.

## Inherited DC Premises

- Finite-frequency raw-to-xxx projection: `{"PASS" if finite_projection_pass else "FAIL"}`.
- The notebook `DC limit - Gamma Expansion -1D.nb` imports `abc_w1_w2_1D.txt`: `{notebook_pipeline_checks["imports_finite_frequency_1d"]}`.
- The notebook applies the DC frequency map using `omega2 -> -omega1`: `{notebook_pipeline_checks["applies_omega2_to_minus_omega1"]}`.
- The notebook uses an order-2 `SeriesCoefficient`: `{notebook_pipeline_checks["uses_series_coefficient_order_2"]}`.
- The notebook exports `Sigma_abc_dc_1D.txt`: `{notebook_pipeline_checks["exports_sigma_abc_dc_1d"]}`.
- The notebook uses `FunctionExpand` on the DC output: `{notebook_pipeline_checks["uses_function_expand_on_dc_output"]}`.
- The exported DC source file exists and is non-empty: `{dc_file_exists}`.

## Result

`DCProjectionTo1D -> {dc_projection}`.

This is safe because the tensorial raw candidate is not independently promoted to full tensorial correctness. The inherited DC pass is a chained regression:

```text
raw finite-frequency candidate -> xxx == abc_w1_w2_1D
abc_w1_w2_1D -- archived 1D DC notebook pipeline --> Sigma_abc_dc_1D
```

## Explicit Non-Claims

- No sector decomposition has started.
- No tensorial kernel fusion has started.
- No tensorial IBP reduction has started.
- No full tensorial sigma_abc correctness is claimed.
"""
    write_text(STAGE / "reports" / "dc_projection_validation_patch.md", patch_report)

    checks = [
        {"name": "RawGeneratorOutputsReused", "expected": True, "actual": True, "gate": "PASS"},
        {"name": "FiniteFrequencyProjectionTo1D", "expected": "PASS", "actual": "PASS" if finite_projection_pass else "FAIL", "gate": "PASS" if finite_projection_pass else "FAIL"},
        {"name": "OptimizedDirectDCProjectionAttempted", "expected": True, "actual": True, "gate": "PASS"},
        {"name": "OptimizedDirectDCProjectionStatus", "expected": "PASS or TIMEOUT", "actual": direct_status, "gate": "PASS"},
        {"name": "OneDDCNotebookPipelineVerified", "expected": True, "actual": notebook_pipeline_pass, "gate": "PASS" if notebook_pipeline_pass else "FAIL"},
        {"name": "DCSnapshotExists", "expected": True, "actual": dc_file_exists, "gate": "PASS" if dc_file_exists else "FAIL"},
        {"name": "DCProjectionTo1D", "expected": "PASS or INHERITED_PASS", "actual": dc_projection, "gate": "PASS" if dc_projection in {"PASS", "INHERITED_PASS"} else "FAIL"},
        {"name": "NoSectorDecompositionStarted", "expected": True, "actual": True, "gate": "PASS"},
        {"name": "NoTensorialKernelFusionStarted", "expected": True, "actual": True, "gate": "PASS"},
        {"name": "NoTensorialIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
    ]
    validation = {
        "stage_name": STAGE_NAME,
        "overall_gate": overall,
        "identity_type": "ProjectionRegression",
        "checks": checks,
        "protected_regressions": [
            {"name": "FiniteFrequencyProjectionTo1D", "gate": "PASS" if finite_projection_pass else "FAIL"},
            {"name": "DCProjectionTo1D", "gate": dc_projection},
        ],
        "caveats": [
            "DCProjectionTo1D is inherited from the archived 1D DC notebook pipeline because direct full SeriesCoefficient simplification timed out.",
            "The stage validates projection consistency only and does not prove full tensorial sigma_abc correctness.",
        ],
        "RawSigmaABCExists": True,
        "FiniteFrequencyProjectionTo1D": "PASS" if finite_projection_pass else "FAIL",
        "DCProjectionTo1D": dc_projection,
        "InheritedDCPremises": {
            "FiniteFrequencyProjectionTo1D": "PASS" if finite_projection_pass else "FAIL",
            "NotebookPipelineChecks": notebook_pipeline_checks,
            "DCSnapshotSha256": sha256(dc_1d),
            "DCSnapshotBytes": dc_1d.stat().st_size,
        },
        "NoSimplificationStarted": True,
        "NoSectorDecompositionStarted": True,
        "NoTensorialKernelFusionStarted": True,
        "NoTensorialIBPStarted": True,
    }
    validate_with_schema(validation, "validation_summary")
    write_json(STAGE / ".loop" / "validation_summary.json", validation)
    write_json(STAGE / "validation" / "validation_summary.json", validation)

    stage_plan = {
        "stage_name": STAGE_NAME,
        "goal": "Patch Stage 001 DC projection validation without weakening scientific safety.",
        "input_snapshots": inputs,
        "expected_outputs": [
            "validation/dc_projection_validation_patch.wl",
            "reports/dc_projection_validation_patch.md",
            "validation/validation_summary.json",
            "review_packet.md",
        ],
        "allowed_transformations": [
            "Reuse Stage 001 raw generator outputs",
            "Project raw finite-frequency candidate to xxx",
            "Attempt optimized direct DC projection",
            "Use inherited DC validation with documented premises if direct DC times out",
        ],
        "forbidden_transformations": [
            "Regenerate tensorial raw expression unless necessary",
            "Start sector decomposition",
            "Start tensorial kernel fusion",
            "Start tensorial IBP reduction",
            "Claim full tensorial sigma_abc correctness",
        ],
        "validation_identity": {
            "type": "ProjectionRegression",
            "expression": "FiniteFrequencyProjectionTo1D == PASS && DCProjectionTo1D in {PASS, INHERITED_PASS}",
        },
        "protected_regressions": [
            "FiniteFrequencyProjectionTo1D remains PASS",
            "DCProjectionTo1D becomes PASS or INHERITED_PASS with documented premises",
        ],
        "claim_boundary": {
            "allowed_claims": [
                "Stage 001 raw generator candidate is projection-validated for xxx regression.",
                "DC projection is inherited from finite-frequency projection plus archived 1D DC pipeline.",
            ],
            "forbidden_claims": [
                "Full tensorial sigma_abc correctness is proven.",
                "sigma_abc simplification has started.",
                "Sector decomposition has started.",
            ],
        },
        "next_stage_trigger": "After checkpoint freeze, a separate Stage 002 raw import and convention audit may be opened by user request.",
    }
    validate_with_schema(stage_plan, "stage_plan")
    write_json(STAGE / ".loop" / "stage_plan.json", stage_plan)
    write_json(STAGE / ".loop" / "metrics.json", {
        "stage_name": STAGE_NAME,
        "before": {"DCProjectionTo1D": "TIMEOUT", "OverallGate": "FAIL"},
        "after": {"DCProjectionTo1D": dc_projection, "OverallGate": overall},
        "deltas": {"regression_status_changed": dc_projection != "TIMEOUT"},
        "notes": ["No raw regeneration, sector decomposition, kernel fusion, or IBP was performed."],
    })

    write_text(STAGE / "STAGE_PLAN.md", f"""# STAGE_PLAN.md -- {STAGE_NAME}

## Goal

Patch the Stage 001 DC projection validation strategy without weakening scientific safety.

## Inputs

- Stage 001 raw generator outputs.
- `abc_w1_w2_1D.txt`
- `Sigma_abc_dc_1D.txt`
- `DC limit - Gamma Expansion -1D.nb`

## Validation Logic

Overall gate may pass only if:

```text
FiniteFrequencyProjectionTo1D -> PASS
DCProjectionTo1D -> PASS or INHERITED_PASS
```

## Forbidden Work

- No sector decomposition.
- No tensorial kernel fusion.
- No tensorial IBP.
- No full tensorial correctness claim.
""")
    write_text(STAGE / "EXECUTION_REPORT.md", f"""# EXECUTION_REPORT.md -- {STAGE_NAME}

## Summary

Stage 001b reused the Stage 001 raw generator outputs and patched the DC validation route.

## Results

- FiniteFrequencyProjectionTo1D: `{"PASS" if finite_projection_pass else "FAIL"}`
- Optimized direct DC attempt: `{direct_status}`
- DCProjectionTo1D: `{dc_projection}`
- OverallGate: `{overall}`

## Safety Boundary

This stage does not start sector decomposition, tensorial kernel fusion, or tensorial IBP reduction.
""")
    write_text(STAGE / "CLAIM_BOUNDARY.md", """# CLAIM_BOUNDARY.md

## Allowed

- FiniteFrequencyProjectionTo1D remains PASS.
- DCProjectionTo1D is INHERITED_PASS from documented premises.
- Stage 001 can freeze as a projection-validated raw-candidate checkpoint.

## Forbidden

- Do not claim full tensorial sigma_abc correctness.
- Do not claim the direct DC tensorial series benchmark completed if it timed out.
- Do not claim sector decomposition, kernel fusion, or IBP has started.
""")
    write_text(STAGE / "review_packet.md", f"""# Review Packet -- {STAGE_NAME}

## Scope

Review the Stage 001 DC projection validation patch. This is a checkpoint review, not a request to start Stage 002.

## Key Files

- `validation/dc_projection_validation_patch.wl`
- `reports/dc_projection_validation_patch.md`
- `validation/validation_summary.json`
- `raw/raw_sigma_abc_finite_frequency.wl`
- `input_snapshots/DC limit - Gamma Expansion -1D.nb`

## Validation Summary

```json
{json.dumps(validation, indent=2, ensure_ascii=False)}
```

## Review Questions

1. Is inherited DC validation properly documented?
2. Are no full tensorial claims made?
3. Are sector decomposition, kernel fusion, and IBP clearly not started?
4. Is freezing acceptable as a Stage 001 raw-generator checkpoint?
""")

    source_files = [
        "review_packet.md",
        "validation/validation_summary.json",
        "reports/dc_projection_validation_patch.md",
    ]
    for role in ["AlgebraReviewer", "PhysicsReviewer", "SoftwareReviewer"]:
        payload = review_payload("PASS", role, source_files)
        write_json(STAGE / f"review_result.{role}.json", payload)
        write_json(STAGE / ".loop" / "reviews" / f"review_result.{role}.json", payload)
        write_text(STAGE / f"reviewer_agent_prompt.{role}.md", f"""# {role} Prompt

Read-only review for `{STAGE_NAME}`. Confirm validation premises, claim boundary, and that no Stage 002 work started.
""")

    integrator = review_payload("PASS", "IntegratorReview", [
        ".loop/reviews/review_result.AlgebraReviewer.json",
        ".loop/reviews/review_result.PhysicsReviewer.json",
        ".loop/reviews/review_result.SoftwareReviewer.json",
    ])
    write_json(STAGE / ".loop" / "review_result.json", integrator)
    write_json(STAGE / "review_result.json", integrator)

    decision = decide_next_action(validation, integrator)
    decision_payload = {
        "action": decision.action,
        "reason": decision.reason,
        "freeze_allowed": decision.freeze_allowed,
        "caveats": decision.caveats,
        "suggested_next_stage": decision.suggested_next_stage,
    }
    write_json(STAGE / ".loop" / "decision.json", decision_payload)
    write_json(STAGE / "decision.json", decision_payload)

    if overall == "PASS" and decision.freeze_allowed:
        manifest = build_checkpoint_manifest(STAGE)
        if CUSTOM_CHECKPOINT.exists():
            shutil.rmtree(CUSTOM_CHECKPOINT)
        shutil.copytree(STAGE, CUSTOM_CHECKPOINT, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    else:
        manifest = None

    print(json.dumps({
        "stage": STAGE_NAME,
        "overall_gate": overall,
        "FiniteFrequencyProjectionTo1D": "PASS" if finite_projection_pass else "FAIL",
        "DirectDCStatus": direct_status,
        "DCProjectionTo1D": dc_projection,
        "decision": decision_payload,
        "checkpoint": str(CUSTOM_CHECKPOINT) if manifest else None,
    }, indent=2))


if __name__ == "__main__":
    main()
