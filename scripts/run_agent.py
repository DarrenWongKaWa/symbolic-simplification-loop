#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

import _bootstrap  # noqa: F401
from loop_engine.agent_runtime import AgentInvocationRequest, build_adapter, resolve_agent_runtime
from loop_engine.config import REPO_ROOT, write_json, write_text
from loop_engine.reviewer import REQUIRED_REVIEWERS, build_reviewer_agent_prompt


def load_profile(profile_name: str) -> dict:
    path = REPO_ROOT / "profiles" / f"{profile_name}.yaml"
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def role_key(agent_name: str) -> str:
    for key, role in REQUIRED_REVIEWERS.items():
        if agent_name in {role, key}:
            return key
    return agent_name.lower()


def ensure_minimal_stage(stage: Path, agent_name: str) -> None:
    stage.mkdir(parents=True, exist_ok=True)
    (stage / ".loop").mkdir(parents=True, exist_ok=True)
    validation = stage / ".loop" / "validation_summary.json"
    if not validation.exists():
        write_json(
            validation,
            {
                "stage_name": stage.name,
                "overall_gate": "PASS",
                "identity_type": "OldMinusNewZero",
                "checks": [{"name": "isolated_agent_smoke", "expected": "PASS", "actual": "PASS", "gate": "PASS"}],
                "caveats": ["Isolated agent-runtime smoke test; no sigma_abc physics was run."],
            },
        )
    metrics = stage / ".loop" / "metrics.json"
    if not metrics.exists():
        write_json(
            metrics,
            {
                "stage_name": stage.name,
                "before": {},
                "after": {"agent_runtime_smoke": True},
                "deltas": {"runtime_invocation": "real command adapter"},
                "notes": ["Isolated real-agent invocation smoke test."],
            },
        )
    review_packet = stage / "review_packet.md"
    if not review_packet.exists():
        write_text(
            review_packet,
            f"""# Review Packet

## Stage

`{stage.name}`

## Purpose

Isolated real-agent runtime smoke test for `{agent_name}`.

## Boundary

No `sigma_abc` physics simplification, tensorial IBP, kernel fusion, or frozen checkpoint modification is performed.
""",
        )
    claim_boundary = stage / "CLAIM_BOUNDARY.md"
    if not claim_boundary.exists():
        write_text(
            claim_boundary,
            """# Claim Boundary

## Allowed Claims

- This stage may claim only that a real command adapter invocation was attempted and evidenced.

## Forbidden Claims

- Do not claim any `sigma_abc` physics progress.
- Do not claim tensorial IBP or kernel fusion started.
""",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke one configured agent and write invocation evidence.")
    parser.add_argument("--profile", default="sigma_abc_hypothesis_pre_ibp")
    parser.add_argument("--agent-name", "--agent", dest="agent_name", required=True)
    parser.add_argument("--stage", "--stage-dir", dest="stage", required=True)
    parser.add_argument("--prompt")
    parser.add_argument("--output")
    parser.add_argument("--schema", default="review_result")
    parser.add_argument("--protected", action="append", default=[])
    args = parser.parse_args()

    stage = Path(args.stage).resolve()
    ensure_minimal_stage(stage, args.agent_name)
    prompt = Path(args.prompt).resolve() if args.prompt else build_reviewer_agent_prompt(
        stage,
        mode="codex_subagent",
        reviewer_role=args.agent_name,
        review_scope="routine_branch",
    ).resolve()
    output = Path(args.output).resolve() if args.output else (stage / ".loop" / "reviewer_results" / f"{role_key(args.agent_name)}.json").resolve()
    profile = load_profile(args.profile)
    status = resolve_agent_runtime(profile, args.profile)
    if not status.production_run_allowed:
        raise SystemExit(f"Agent runtime unavailable: {status.reason}; missing={status.missing_agent_commands}")
    adapter = build_adapter(profile, args.profile)
    summary = adapter.invoke(
        AgentInvocationRequest(
            agent_name=args.agent_name,
            stage_dir=stage,
            prompt_path=prompt,
            output_path=output,
            schema_name=args.schema,
            protected_paths=[Path(item) for item in args.protected],
        )
    )
    print(stage / ".loop" / "agent_invocations" / args.agent_name / "invocation_summary.json")
    if not summary.get("freeze_evidence_valid"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
