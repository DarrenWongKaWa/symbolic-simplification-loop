from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import read_json, read_text, write_text


def _json_block(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _key_outputs(stage: Path) -> list[str]:
    outputs: list[str] = []
    for folder in ["output", "validation", "reports"]:
        root = stage / folder
        if root.exists():
            outputs.extend(str(path.relative_to(stage)) for path in sorted(root.rglob("*")) if path.is_file())
    return outputs[:80]


def build_compact_review_packet(stage: Path, profile: dict[str, Any] | None = None) -> Path:
    profile = profile or {}
    validation = read_json(stage / ".loop" / "validation_summary.json") if (stage / ".loop" / "validation_summary.json").exists() else {}
    metrics = read_json(stage / ".loop" / "metrics.json") if (stage / ".loop" / "metrics.json").exists() else {}
    risk = read_json(stage / ".loop" / "risk_classification.json") if (stage / ".loop" / "risk_classification.json").exists() else {}
    plan = read_text(stage / "STAGE_PLAN.md")
    first_goal_lines = "\n".join(line for line in plan.splitlines()[:20])
    claim = read_text(stage / "CLAIM_BOUNDARY.md", "(missing CLAIM_BOUNDARY.md)")
    checks = validation.get("checks", [])
    check_summary = [
        {
            "name": item.get("name"),
            "expected": item.get("expected"),
            "actual": item.get("actual"),
            "gate": item.get("gate"),
        }
        for item in checks[:30]
    ]
    stage_id = stage.name
    stage_slug = stage.name
    if stage_slug.startswith("sigma_abc_"):
        stage_slug = stage_slug.removeprefix("sigma_abc_")
    forbidden_status = {
        "NoIBPStarted": validation.get("NoIBPStarted"),
        "NoTotalDerivativeIntroduced": validation.get("NoTotalDerivativeIntroduced"),
        "NoFullTensorialClaim": validation.get("NoFullTensorialClaim"),
    }
    claimed_output = {
        "identity_type": validation.get("identity_type"),
        "overall_gate": validation.get("overall_gate"),
    }
    not_claimed_output = {
        key: validation.get(key)
        for key in ["CenterFusionDifference", "XXXCenterProjectionRegression", "LoopFusionDifference"]
        if key in validation
    }
    packet = f"""# Compact Review Packet: {stage.name}

## Stage Identity

- stage id: `{stage_id}`
- stage slug: `{stage_slug}`

## Stage Goal

{first_goal_lines}

## Review Lane

```json
{_json_block(risk)}
```

## Validation Gate Summary

```json
{_json_block({
    "overall_gate": validation.get("overall_gate"),
    "identity_type": validation.get("identity_type"),
    "checks": check_summary,
    "protected_regressions": validation.get("protected_regressions", []),
    "caveats": validation.get("caveats", []),
})}
```

## Identity Type

`{validation.get("identity_type", "UNKNOWN")}`

## Claimed Output

```json
{_json_block(claimed_output)}
```

## Not-Claimed Output

```json
{_json_block(not_claimed_output)}
```

## Caveats

{chr(10).join(f"- {item}" for item in validation.get("caveats", [])) or "- none recorded"}

## Forbidden Actions Status

```json
{_json_block(forbidden_status)}
```

## Protected Benchmark Status

```json
{_json_block(validation.get("protected_regressions", []))}
```

## Changed Outputs

{chr(10).join(f"- `{item}`" for item in _key_outputs(stage)) or "- none recorded"}

## Metrics Summary

```json
{_json_block({
    "before": metrics.get("before", {}),
    "after": metrics.get("after", {}),
    "deltas": metrics.get("deltas", {}),
    "notes": metrics.get("notes", []),
})}
```

## Claim Boundary

{claim}

## Exact Reviewer Questions

1. Does the exported validation gate justify the stage-local claim?
2. Are protected caveats and benchmarks preserved?
3. Did this stage avoid forbidden actions such as IBP, total derivatives, or full tensorial correctness claims?
4. PASS as what?
5. NOT PASS as what?
6. What was actually validated, and what was inherited/deferred?
7. Should this stage freeze, remain pending review, or patch?
"""
    max_words = int(((profile.get("review_policy", {}) or {}).get("lanes", {}) or {}).get("L1_COMPACT_META", {}).get("max_input_tokens", 2500))
    words = packet.split()
    if len(words) > max_words:
        packet = " ".join(words[:max_words]) + "\n\n[compact packet truncated at configured word budget]\n"
    target = stage / "review_minipacket.md"
    write_text(target, packet)
    return target
