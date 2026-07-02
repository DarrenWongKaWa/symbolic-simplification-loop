#!/usr/bin/env python3
"""Loop 021 — reviewer provider smoke test.

Invokes one provider end-to-end against a benign prompt and
records the outcome to ``archive/local_runs/<UTC-timestamp>_REVIEWER_PROVIDER_SMOKE.md``.

Does NOT touch sigma_abc stages, does NOT promote 012C, does
NOT run IBP / total derivative.

Examples::

    python3 scripts/run_reviewer_provider_smoke.py \
      --role ScientificMetaReviewer \
      --prompt "Return a valid PASS reviewer JSON for smoke test only."
    python3 scripts/run_reviewer_provider_smoke.py \
      --role ScientificMetaReviewer \
      --provider anthropic_api \
      --prompt-file scripts/run_reviewer_provider_smoke.py
    python3 scripts/run_reviewer_provider_smoke.py \
      --role ScientificMetaReviewer \
      --provider codex_cli_resolver \
      --write-root-report  # also emit at repo root (off by default)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from loop_engine.agent_runtime import AgentInvocationRequest
from loop_engine.api_review_provider import (
    invoke_anthropic_api,
    invoke_openai_api,
    invoke_openai_compatible_api,
)
from loop_engine.config import REPO_ROOT, write_text
from loop_engine.reviewer_provider_pool import (
    _check_provider_availability,
    _is_provider_enabled,
    _resolve_api_key,
    _resolve_base_url,
    _resolve_model,
)
from loop_engine.secret_redaction import redact_secrets


def _build_provider_request(
    *,
    role: str,
    prompt: str,
    stage_dir: Path,
) -> AgentInvocationRequest:
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / ".loop" / "agent_invocations").mkdir(parents=True, exist_ok=True)
    prompt_path = stage_dir / ".loop" / "smoke_prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    output_path = stage_dir / ".loop" / "smoke_review_result.json"
    return AgentInvocationRequest(
        agent_name=role,
        stage_dir=stage_dir,
        prompt_path=prompt_path,
        output_path=output_path,
        schema_name="review_result.codex",
        protected_paths=[],
    )


def _invoke_for_adapter(adapter: str, request: AgentInvocationRequest, *, env: dict[str, str]):
    if adapter == "anthropic_api":
        return invoke_anthropic_api(
            request=request,
            api_key=env.get("api_key"),
            model=env.get("model"),
        )
    if adapter == "openai_api":
        return invoke_openai_api(
            request=request,
            api_key=env.get("api_key"),
            model=env.get("model"),
        )
    if adapter == "openai_compatible_api":
        return invoke_openai_compatible_api(
            request=request,
            api_key=env.get("api_key"),
            base_url=env.get("base_url"),
            model=env.get("model"),
        )
    raise SystemExit(f"unsupported adapter for smoke: {adapter!r}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test one reviewer provider."
    )
    parser.add_argument(
        "--role", default="ScientificMetaReviewer",
        help="Reviewer role to smoke (default: ScientificMetaReviewer)."
    )
    parser.add_argument(
        "--provider",
        default="anthropic_api",
        choices=("anthropic_api", "openai_api", "openai_compatible_api"),
        help="Which adapter to smoke."
    )
    parser.add_argument(
        "--prompt", default=None,
        help="Prompt text (default: a fixed benign prompt)."
    )
    parser.add_argument(
        "--prompt-file", default=None,
        help="Read prompt from a file (takes priority over --prompt)."
    )
    parser.add_argument(
        "--write-root-report",
        action="store_true",
        help="Also emit a copy at REPO_ROOT / <basename>."
    )
    args = parser.parse_args()

    if args.prompt_file:
        prompt_text = Path(args.prompt_file).read_text(encoding="utf-8")
    elif args.prompt:
        prompt_text = args.prompt
    else:
        prompt_text = (
            "# Reviewer smoke test\n\n"
            "Return a valid PASS reviewer JSON only.\n"
        )

    stage_dir = REPO_ROOT / "autonomous_runs" / "provider_smoke" / args.role
    if stage_dir.exists():
        # Don't wipe a real run root.
        from datetime import datetime, timezone
        ts_unique = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        stage_dir = stage_dir.with_name(f"{stage_dir.name}_{ts_unique}")

    request = _build_provider_request(
        role=args.role,
        prompt=prompt_text,
        stage_dir=stage_dir,
    )

    # Read provider env from the appropriate variables.
    if args.provider == "anthropic_api":
        api_key, _ = _resolve_api_key({"api_key_env": "ANTHROPIC_API_KEY"})
        model, _ = _resolve_model({"model_env": "ANTHROPIC_MODEL"})
        env = {"api_key": api_key, "model": model, "base_url": None}
    elif args.provider == "openai_api":
        api_key, _ = _resolve_api_key({"api_key_env": "OPENAI_API_KEY"})
        model, _ = _resolve_model({"model_env": "OPENAI_MODEL"})
        env = {"api_key": api_key, "model": model, "base_url": None}
    else:  # openai_compatible_api
        api_key, _ = _resolve_api_key({"api_key_env": "OPENAI_COMPATIBLE_API_KEY"})
        base_url, _ = _resolve_base_url({"base_url_env": "OPENAI_COMPATIBLE_BASE_URL"})
        model, _ = _resolve_model({"model_env": "OPENAI_COMPATIBLE_MODEL"})
        env = {
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
        }

    if not env.get("api_key"):
        print(
            f"ERROR: api_key for {args.provider} is not set in env; "
            f"please set the appropriate *_API_KEY env var.",
            file=sys.stderr,
        )
        # Still write the report so the smoke leaves a trace.
        body = (
            f"# Reviewer Provider Smoke\n\n"
            f"role: `{args.role}`\n"
            f"provider: `{args.provider}`\n"
            f"result: **skipped (no api_key in env)**\n"
        )
        ts = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H-%M-%S+00-00"
        )
        target = (
            REPO_ROOT / "archive" / "local_runs"
            / f"{ts}_REVIEWER_PROVIDER_SMOKE_{args.role}.md"
        )
        if getattr(args, "write_root_report", False):
            target = REPO_ROOT / f"REVIEWER_PROVIDER_SMOKE_{args.role}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        write_text(target, body)
        print(f"--- report written to: {target}", file=sys.stderr)
        return 1

    result = _invoke_for_adapter(args.provider, request, env=env)

    body = (
        f"# Reviewer Provider Smoke\n\n"
        f"role: `{args.role}`\n"
        f"provider: `{args.provider}`\n"
        f"actually_invoked: `{result.actually_invoked}`\n"
        f"stub_used: `{result.stub_used}`\n"
        f"runtime_status: `{result.runtime_status}`\n"
        f"schema_valid: `{result.schema_valid}`\n"
        f"verdict: `{result.verdict}`\n"
        f"retryable: `{result.retryable}`\n"
        f"review_debt_required: `{result.review_debt_required}`\n"
        f"freeze_evidence_valid: `{result.freeze_evidence_valid}`\n"
        f"provider_attempts:\n"
    )
    for attempt in result.provider_attempts:
        body += (
            f"  - {attempt.provider_name} ({attempt.adapter}): "
            f"runtime_status={attempt.runtime_status}, "
            f"retryable={attempt.retryable}, "
            f"selected={attempt.selected}, "
            f"fail={attempt.failure_summary_redacted!r}\n"
        )

    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H-%M-%S+00-00"
    )
    if getattr(args, "write_root_report", False):
        target = REPO_ROOT / f"REVIEWER_PROVIDER_SMOKE_{args.role}.md"
    else:
        target = (
            REPO_ROOT / "archive" / "local_runs"
            / f"{ts}_REVIEWER_PROVIDER_SMOKE_{args.role}.md"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    write_text(target, redact_secrets(body))
    print(body)
    print(f"--- report written to: {target}", file=sys.stderr)
    return 0 if result.schema_valid or not result.review_debt_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
