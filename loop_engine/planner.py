from __future__ import annotations

from pathlib import Path

from .config import write_text


CONDUCTIVITY_STAGES = [
    "000_raw_import",
    "010_sector_decomposition",
    "020_basis_closure",
    "030_kernel_fusion",
    "040_targeted_ibp",
    "050_residual_driven_ibp",
    "060_global_coupled_solve",
    "070_final_integration",
    "080_projection_or_model_regression",
]


def write_default_stage_plan(
    stage_dir: Path,
    goal: str = "TBD",
    *,
    expected_outputs: list[str] | None = None,
    dependencies: list[str] | None = None,
) -> Path:
    stage_name = stage_dir.name
    expected_outputs = expected_outputs or ["output/", ".loop/validation_summary.json"]
    dependencies = dependencies or ["input_snapshots/"]
    plan = f"""# Stage Plan

## Stage

`{stage_name}`

## Goal

{goal}

## Input Snapshots

{chr(10).join(f"- `{item}`" for item in dependencies)}

## Expected Outputs

{chr(10).join(f"- `{item}`" for item in expected_outputs)}

## Allowed Transformations

- Exact symbolic transformations with exported evidence.

## Forbidden Transformations

- Dropping terms by intuition.
- Mixing stale pre-IBP and post-IBP tables.

## Validation Identity

```text
OldExpression - NewExpression == 0
```

## Protected Regressions

- `sigma_xxx` projection benchmark when applicable.

## Claim Boundary

Allowed:

- Stage-local validated claims only.

Forbidden:

- Full-project success before final regression.

## Next-Stage Trigger

Validation PASS and review PASS/PASS_WITH_CAVEAT.
"""
    target = stage_dir / "STAGE_PLAN.md"
    write_text(target, plan)
    return target
