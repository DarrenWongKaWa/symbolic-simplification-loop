#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
from loop_engine.config import REPO_ROOT, read_json, write_json, write_text
from loop_engine.schemas import load_and_validate, validate_with_schema


PROJECT_NAME = "mock_polynomial_loop"
STAGE_NAME = "000_polynomial_identity"
OLD_EXPR = "x^2 + 2 x + 1"
NEW_EXPR = "(x + 1)^2"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def run_command(args: list[str], cwd: Path = REPO_ROOT) -> dict[str, Any]:
    completed = subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True)
    return {
        "command": " ".join(args),
        "cwd": rel(cwd),
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def polynomial_identity_difference() -> dict[str, Any]:
    old_coefficients = {"x^2": 1, "x": 2, "1": 1}
    new_expanded_coefficients = {"x^2": 1, "x": 2, "1": 1}
    difference = {
        key: old_coefficients.get(key, 0) - new_expanded_coefficients.get(key, 0)
        for key in sorted(set(old_coefficients) | set(new_expanded_coefficients))
    }
    return {
        "old": OLD_EXPR,
        "new": NEW_EXPR,
        "expanded_new": "x^2 + 2 x + 1",
        "difference_coefficients": difference,
        "difference": "0" if all(value == 0 for value in difference.values()) else str(difference),
        "gate": "PASS" if all(value == 0 for value in difference.values()) else "FAIL",
    }


def stage_plan_json(stage: Path) -> dict[str, Any]:
    return {
        "stage_name": STAGE_NAME,
        "goal": "Verify a mock symbolic identity through the full loop lifecycle.",
        "input_snapshots": ["input_snapshots/mock_old_expression.txt"],
        "expected_outputs": [
            "output/mock_new_expression.txt",
            "output/mock_identity_difference.json",
            ".loop/validation_summary.json",
        ],
        "allowed_transformations": ["Exact polynomial expansion."],
        "forbidden_transformations": [
            "Do not perform any sigma_abc physics simplification.",
            "Do not discard terms by intuition.",
        ],
        "validation_identity": {
            "type": "OldMinusNewZero",
            "expression": "Old - New == 0 for Old=x^2+2x+1 and New=(x+1)^2",
        },
        "protected_regressions": [
            "sigma_xxx benchmark metadata remains registered for future tensorial projects."
        ],
        "claim_boundary": {
            "allowed_claims": [
                "The mock polynomial identity validates through the loop infrastructure.",
                "The stage lifecycle can build packet, review, decide, and freeze.",
            ],
            "forbidden_claims": [
                "sigma_abc simplification has started.",
                "The framework has performed any physics simplification.",
            ],
        },
        "next_stage_trigger": "Freeze only after validation PASS and reviewer PASS.",
    }


def write_stage_files(project: Path, stage: Path) -> dict[str, Any]:
    identity = polynomial_identity_difference()

    write_text(stage / "input_snapshots" / "mock_old_expression.txt", OLD_EXPR + "\n")
    write_text(stage / "output" / "mock_new_expression.txt", NEW_EXPR + "\n")
    write_json(stage / "output" / "mock_identity_difference.json", identity)

    plan = stage_plan_json(stage)
    write_json(stage / ".loop" / "stage_plan.json", plan)
    validate_with_schema(plan, "stage_plan")

    write_text(
        stage / "STAGE_PLAN.md",
        f"""# Stage Plan

## Stage

`{STAGE_NAME}`

## Goal

Verify the mock symbolic identity

```text
Old = {OLD_EXPR}
New = {NEW_EXPR}
Old - New = 0
```

through the full symbolic-simplification loop lifecycle.

## Input Snapshots

- `input_snapshots/mock_old_expression.txt`
- `input_snapshots/sigma_xxx_benchmark_metadata.json`

## Expected Outputs

- `output/mock_new_expression.txt`
- `output/mock_identity_difference.json`
- `.loop/validation_summary.json`
- `review_packet.md`
- `.loop/review_result.json`
- `.loop/decision.json`
- `.loop/checkpoint_manifest.json`

## Allowed Transformations

- Exact polynomial expansion.

## Forbidden Transformations

- Do not perform `sigma_abc` simplification.
- Do not claim physics progress from this smoke test.

## Validation Identity

```text
OldExpression - NewExpression == 0
```

## Protected Regressions

- `examples/sigma_xxx_case/benchmark_sigma_xxx_projection.json` is registered as benchmark metadata.

## Claim Boundary

Allowed:

- The loop infrastructure validates, reviews, decides, and freezes a mock stage.

Forbidden:

- The `sigma_abc` symbolic simplification has started.
- The smoke test proves any physics simplification identity.

## Next-Stage Trigger

No next scientific stage is opened by this smoke test.
""",
    )

    write_text(
        stage / "EXECUTION_REPORT.md",
        f"""# Execution Report

## Stage Name

`{STAGE_NAME}`

## Files Created

- `input_snapshots/mock_old_expression.txt`
- `output/mock_new_expression.txt`
- `output/mock_identity_difference.json`
- `.loop/validation_summary.json`

## Scripts Run

- `scripts/run_full_loop_smoke_test.py`

## Input Snapshots Used

- `input_snapshots/mock_old_expression.txt`
- `input_snapshots/sigma_xxx_benchmark_metadata.json`

## Main Outputs

- `{NEW_EXPR}`

## Validation Results

```text
Old - New = {identity["difference"]}
overall_gate: {identity["gate"]}
```

## Metrics Before / After

```json
{json.dumps({"before": {"terms": 3}, "after": {"expanded_terms": 3, "difference": 0}}, indent=2)}
```

## Known Caveats

- This is an infrastructure smoke test, not a physics simplification.

## Next Recommended Action

`BUILD_REVIEW_PACKET`
""",
    )

    write_text(
        stage / "CLAIM_BOUNDARY.md",
        """# Claim Boundary

## Allowed Claims

- The mock polynomial stage validates exactly.
- The loop infrastructure can generate review packets, structured review results, decisions, and checkpoints.

## Forbidden Claims

- `sigma_abc` simplification has started.
- Any physical conductivity formula has been simplified by this smoke test.

## Caveats

- This stage uses a toy polynomial identity only.
""",
    )

    validation_summary = {
        "stage_name": STAGE_NAME,
        "overall_gate": identity["gate"],
        "identity_type": "OldMinusNewZero",
        "checks": [
            {
                "name": "mock_polynomial_identity",
                "expected": "0",
                "actual": identity["difference"],
                "gate": identity["gate"],
                "old": OLD_EXPR,
                "new": NEW_EXPR,
            }
        ],
        "protected_regressions": [
            {
                "name": "sigma_xxx_benchmark_metadata_registered",
                "source": "examples/sigma_xxx_case/benchmark_sigma_xxx_projection.json",
                "gate": "PASS",
            }
        ],
        "caveats": ["Infrastructure-only smoke test; no physics simplification was run."],
    }
    validate_with_schema(validation_summary, "validation_summary")
    write_json(stage / ".loop" / "validation_summary.json", validation_summary)
    write_json(stage / "validation" / "validation_summary.json", validation_summary)

    metrics = {
        "stage_name": STAGE_NAME,
        "before": {"expression": OLD_EXPR, "terms": 3},
        "after": {"expression": NEW_EXPR, "expanded_terms": 3, "difference": identity["difference"]},
        "deltas": {"identity_difference": identity["difference"]},
        "notes": ["Toy exact identity used to smoke-test loop lifecycle."],
    }
    validate_with_schema(metrics, "metrics")
    write_json(stage / ".loop" / "metrics.json", metrics)

    benchmark_source = REPO_ROOT / "examples" / "sigma_xxx_case" / "benchmark_sigma_xxx_projection.json"
    manifest_source = REPO_ROOT / "examples" / "sigma_xxx_case" / "final_checkpoint_manifest.json"
    benchmark = read_json(benchmark_source)
    manifest = read_json(manifest_source)
    (project / "benchmarks").mkdir(exist_ok=True)
    write_json(project / "benchmarks" / "sigma_xxx_benchmark_metadata.json", benchmark)
    write_json(stage / "input_snapshots" / "sigma_xxx_benchmark_metadata.json", benchmark)
    write_text(
        stage / "reports" / "sigma_xxx_benchmark_registration.md",
        f"""# Sigma XXX Benchmark Registration

The smoke project registers the completed projected `sigma_xxx` case as benchmark metadata for future tensorial projects.

## Source Files

- `{rel(benchmark_source)}`
- `{rel(manifest_source)}`

## Protected Identity

```text
{benchmark.get("identity", "ProjectToXXX[...] - reference == 0")}
```

## Final Basis

```json
{json.dumps(manifest.get("final_basis", []), indent=2)}
```

## Boundary

This registration does not start `sigma_abc` simplification.
""",
    )
    return identity


def write_repo_audit(file_count: int, directory_count: int) -> Path:
    audit = f"""# Repository Audit

## Scope

This audit covers the `symbolic-simplification-loop` infrastructure repo. It does not audit or run any `sigma_abc` physics simplification.

## Structure

- Python package: `loop_engine/`
- CLI scripts: `scripts/`
- JSON schemas: `schemas/`
- Markdown/JSON templates: `templates/`
- Role instructions: `skill/`
- Reference benchmark: `examples/sigma_xxx_case/`
- Future-project template: `examples/sigma_abc_template/`
- Tests: `tests/`

## Inventory

- Files discovered: {file_count}
- Directories discovered: {directory_count}

## Lifecycle Coverage

- Stage initialization: present.
- Validation summary schema: present.
- Structured review packet generation: present.
- Read-only reviewer role prompts: present for AlgebraReviewer, PhysicsReviewer, and SoftwareReviewer.
- Decision engine: present.
- Checkpoint freezer: present.
- Sigma_xxx benchmark metadata: present.
- Sigma_abc project template: present.

## Boundary

The repo is an orchestration framework. It does not perform symbolic physics simplification by itself.
"""
    target = REPO_ROOT / "REPO_AUDIT.md"
    write_text(target, audit)
    return target


def schema_validation_report(stage: Path, aggregate_review: Path, manifest_path: Path) -> dict[str, Any]:
    checks = []
    schema_targets = [
        (stage / ".loop" / "stage_plan.json", "stage_plan"),
        (stage / ".loop" / "validation_summary.json", "validation_summary"),
        (stage / ".loop" / "metrics.json", "metrics"),
        (aggregate_review, "review_result"),
        (manifest_path, "checkpoint_manifest"),
    ]
    for path, schema in schema_targets:
        load_and_validate(path, schema)
        checks.append({"file": rel(path), "schema": schema, "gate": "PASS"})
    return {"overall_gate": "PASS", "checks": checks}


def write_smoke_report(
    commands: list[dict[str, Any]],
    generated_files: list[Path],
    pytest_result: dict[str, Any],
    schema_result: dict[str, Any],
    identity: dict[str, Any],
    review_result: dict[str, Any],
    decision: dict[str, Any],
    checkpoint_target: Path,
) -> Path:
    command_lines = "\n".join(
        f"- `{item['command']}` -> rc={item['returncode']}" for item in commands
    )
    file_lines = "\n".join(f"- `{rel(path)}`" for path in generated_files)
    schema_lines = "\n".join(
        f"- `{check['file']}` against `{check['schema']}`: {check['gate']}"
        for check in schema_result["checks"]
    )
    report = f"""# Loop Smoke Test Report

## Commands Run

{command_lines}

## Files Generated

{file_lines}

## Pytest Result

```text
command: {pytest_result['command']}
returncode: {pytest_result['returncode']}
stdout:
{pytest_result['stdout']}
stderr:
{pytest_result['stderr']}
```

## Schema Validation Result

Overall gate: `{schema_result['overall_gate']}`

{schema_lines}

## Mock Stage Validation Result

```json
{json.dumps(identity, indent=2, sort_keys=True)}
```

## Reviewer Result

```json
{json.dumps(review_result, indent=2, sort_keys=True)}
```

## Decision Result

```json
{json.dumps(decision, indent=2, sort_keys=True)}
```

## Checkpoint Freezing

- Freeze target: `{rel(checkpoint_target)}`
- `checkpoint_manifest.json` created: `yes`

## Reviewer Subagent Mode

Routine review is represented by three read-only reviewer roles:

- `AlgebraReviewer`
- `PhysicsReviewer`
- `SoftwareReviewer`

Each role returns structured JSON that is aggregated into `.loop/review_result.json`.

## Boundary

No `sigma_abc` simplification was run.
"""
    target = REPO_ROOT / "LOOP_SMOKE_TEST_REPORT.md"
    write_text(target, report)
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Remove previous mock smoke project before running.")
    args = parser.parse_args()

    project = REPO_ROOT / "smoke_projects" / PROJECT_NAME
    if args.clean and project.exists():
        shutil.rmtree(project)
    if project.exists():
        raise FileExistsError(f"{project} already exists; rerun with --clean")

    file_count = sum(1 for path in REPO_ROOT.rglob("*") if path.is_file() and ".pytest_cache" not in path.parts and "__pycache__" not in path.parts)
    directory_count = sum(1 for path in REPO_ROOT.rglob("*") if path.is_dir() and ".pytest_cache" not in path.parts and "__pycache__" not in path.parts)
    repo_audit = write_repo_audit(file_count, directory_count)

    commands: list[dict[str, Any]] = []
    pytest_result = run_command([sys.executable, "-m", "pytest", "-q"])
    commands.append(pytest_result)
    commands.append(
        run_command(
            [
                sys.executable,
                "scripts/init_project.py",
                "--root",
                "smoke_projects",
                "--name",
                PROJECT_NAME,
            ]
        )
    )
    commands.append(
        run_command(
            [
                sys.executable,
                "scripts/init_stage.py",
                "--project",
                str(project),
                "--stage",
                STAGE_NAME,
                "--goal",
                "Verify Old=x^2+2x+1 and New=(x+1)^2 through the full loop lifecycle.",
            ]
        )
    )

    stage = project / "stages" / STAGE_NAME
    identity = write_stage_files(project, stage)

    commands.append(run_command([sys.executable, "scripts/build_review_packet.py", "--stage", str(stage)]))
    commands.append(
        run_command(
            [
                sys.executable,
                "scripts/build_reviewer_agent_prompts.py",
                "--stage",
                str(stage),
                "--mode",
                "codex_subagent",
                "--scope",
                "routine_branch",
            ]
        )
    )
    commands.append(
        run_command(
            [
                sys.executable,
                "scripts/run_reviewer_agents.py",
                "--stage",
                str(stage),
                "--mode",
                "codex_subagent",
                "--scope",
                "routine_branch",
            ]
        )
    )

    commands.append(run_command([sys.executable, "scripts/aggregate_review_results.py", "--stage", str(stage)]))
    aggregate_review = stage / ".loop" / "review_result.json"
    shutil.copy2(aggregate_review, stage / "review_result.json")
    commands.append(run_command([sys.executable, "scripts/decide_next_action.py", "--stage", str(stage)]))
    decision_path = stage / ".loop" / "decision.json"
    shutil.copy2(decision_path, stage / "decision.json")
    commands.append(run_command([sys.executable, "scripts/freeze_checkpoint.py", "--stage", str(stage)]))

    decision = read_json(decision_path)
    review_result = read_json(aggregate_review)
    checkpoint_manifest = stage / ".loop" / "checkpoint_manifest.json"
    checkpoint_target = Path(commands[-1]["stdout"])
    schema_result = schema_validation_report(stage, aggregate_review, checkpoint_manifest)
    schema_target = REPO_ROOT / "archive" / "local_runs" / (
        f"{REPO_ROOT.parent.name}_"  # dummy timestamp anchor; helper ensures fresh
        ""
    )
    # Use the same helper logic as run_autonomous_loop; mirror its _report_path
    # without an import cycle by reading archive target inline.
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S+00-00")
    schema_target = (
        REPO_ROOT / "archive" / "local_runs" / f"{ts}_SCHEMA_VALIDATION_RESULT.json"
    )
    schema_target.parent.mkdir(parents=True, exist_ok=True)
    write_json(schema_target, schema_result)
    if getattr(args, "write_root_report", False) if "args" in locals() else False:
        write_json(REPO_ROOT / "SCHEMA_VALIDATION_RESULT.json", schema_result)

    generated_files = [
        repo_audit,
        schema_target,
        project / "README.md",
        project / "benchmarks" / "sigma_xxx_benchmark_metadata.json",
        stage / "STAGE_PLAN.md",
        stage / "EXECUTION_REPORT.md",
        stage / "CLAIM_BOUNDARY.md",
        stage / "input_snapshots" / "mock_old_expression.txt",
        stage / "input_snapshots" / "sigma_xxx_benchmark_metadata.json",
        stage / "output" / "mock_new_expression.txt",
        stage / "output" / "mock_identity_difference.json",
        stage / ".loop" / "validation_summary.json",
        stage / "validation" / "validation_summary.json",
        stage / "review_packet.md",
        stage / "reviewer_agent_prompt.AlgebraReviewer.md",
        stage / "reviewer_agent_prompt.PhysicsReviewer.md",
        stage / "reviewer_agent_prompt.SoftwareReviewer.md",
        stage / ".loop" / "reviewer_results" / "algebra_reviewer.json",
        stage / ".loop" / "reviewer_results" / "physics_reviewer.json",
        stage / ".loop" / "reviewer_results" / "software_reviewer.json",
        aggregate_review,
        stage / "review_result.json",
        decision_path,
        stage / "decision.json",
        checkpoint_manifest,
        checkpoint_target / ".loop" / "checkpoint_manifest.json",
    ]

    smoke_report = write_smoke_report(
        commands=commands,
        generated_files=generated_files,
        pytest_result=pytest_result,
        schema_result=schema_result,
        identity=identity,
        review_result=review_result,
        decision=decision,
        checkpoint_target=checkpoint_target,
    )
    print(smoke_report)


if __name__ == "__main__":
    main()
