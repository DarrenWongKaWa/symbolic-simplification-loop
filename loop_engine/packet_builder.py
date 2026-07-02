from __future__ import annotations

from pathlib import Path

from .config import read_json, read_text, write_text


def _json_block(data: dict) -> str:
    import json

    return json.dumps(data, indent=2, sort_keys=True)


def build_review_packet(stage: Path) -> Path:
    stage_name = stage.name
    plan = read_text(stage / "STAGE_PLAN.md", "(missing STAGE_PLAN.md)")
    execution = read_text(stage / "EXECUTION_REPORT.md", "(missing EXECUTION_REPORT.md)")
    claim_boundary = read_text(stage / "CLAIM_BOUNDARY.md", "(missing CLAIM_BOUNDARY.md)")

    metrics_path = stage / ".loop" / "metrics.json"
    validation_path = stage / ".loop" / "validation_summary.json"
    metrics = read_json(metrics_path) if metrics_path.exists() else {}
    validation = read_json(validation_path) if validation_path.exists() else {}

    key_files = []
    for folder in ["input_snapshots", "output", "validation", "reports"]:
        root = stage / folder
        if root.exists():
            key_files.extend(str(path.relative_to(stage)) for path in sorted(root.rglob("*")) if path.is_file())

    packet = f"""# Structured Reviewer Packet: {stage_name}

## Stage Plan

{plan}

## Execution Report

{execution}

## Key Files

{chr(10).join(f'- `{item}`' for item in key_files) if key_files else '- none recorded'}

## Metrics Before / After

```json
{_json_block(metrics)}
```

## Validation Summary

```json
{_json_block(validation)}
```

## Claim Boundary

{claim_boundary}

## Reviewer Mode

Default V1 mode:

```text
codex_subagent
```

Manual ChatGPT and OpenAI API review are optional modes.

Routine branch review should use read-only Codex subagents:

```text
AlgebraReviewer   algebraic exactness, row counts, validation gates
PhysicsReviewer   basis, symmetry, conventions, claim boundary
SoftwareReviewer  stale files, table provenance, reproducibility
```

Major checkpoints, paper claims, final scientific audits, and next-branch scientific-route decisions should also receive a separate web-GPT audit.

This symbolic reviewer-agent audit is not the same as Codex app `/review`, which is for code diffs and inline comments.

## Reviewer Hard Boundary

- Do not edit code or symbolic outputs.
- Do not replace verifier scripts.
- Audit exactness gates, stale inputs, protected regressions, claim boundary, and next action.
- If validation failed, recommend against freezing even if the narrative looks plausible.

## Reviewer Questions

1. Is the algebra exact?
2. Is the simplification real?
3. Were old or stale tables mixed in?
4. Did protected regressions survive?
5. Is the claim boundary honest?
6. Should this branch freeze, patch, fail, or open next stage?
"""
    target = stage / "review_packet.md"
    write_text(target, packet)
    return target
