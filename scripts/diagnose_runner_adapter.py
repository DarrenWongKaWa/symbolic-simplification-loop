#!/usr/bin/env python3
"""Loop 022R — diagnose which adapter the runner would select
for a given reviewer role.

This is a *dry* diagnostic; it does NOT invoke any provider or
agent. It only walks the same configuration sources the
runner reads:

- the profile YAML (``profiles/<profile>.yaml``)
- ``agents/runtime.local.yaml`` (for the runtime-local pool
  block that Loop 022R activates)

and reports which adapter the runner would build, what would
be the legacy fallback command, and whether a stub would be
selected in production.

Example:

    python3 scripts/diagnose_runner_adapter.py \
      --profile sigma_abc_hypothesis_pre_ibp_throughput

The output is text only; nothing is written to disk.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from loop_engine.agent_runtime import (
    CodexSubagentAdapter,
    CommandAgentAdapter,
    DryRunStubAdapter,
    ProviderPoolAdapter,
    build_adapter,
    profile_config_for_diagnose,
)
from loop_engine.config import REPO_ROOT


def _load_profile(profile_name: str) -> dict:
    """Read a profile YAML directly (no schema validation needed
    for diagnostics).
    """
    import yaml as _yaml

    path = REPO_ROOT / "profiles" / f"{profile_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Missing profile: {path}")
    return _yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose which adapter the runner would select.",
    )
    parser.add_argument(
        "--profile",
        default="sigma_abc_hypothesis_pre_ibp_throughput",
        help="Profile name to diagnose against.",
    )
    parser.add_argument(
        "--role",
        default="ScientificMetaReviewer",
        help="Reviewer role to focus on (informational only; "
             "build_adapter builds one adapter that all roles use).",
    )
    args = parser.parse_args()

    profile = _load_profile(args.profile)
    profile_name = profile.get("profile", args.profile)
    adapter = build_adapter(profile, profile_name)

    lines: list[str] = []
    lines.append(f"ReviewerRole={args.role}")
    lines.append(f"ProfileName={profile_name}")
    lines.append(f"ProfileInlinePool={'present' if isinstance(profile.get('reviewer_provider_pools'), dict) else 'absent'}")
    runtime_local_pool = profile_config_for_diagnose(
        profile_name=profile_name,
        reviewer_role="*",
    )
    lines.append(
        f"RuntimeLocalPool={'present' if runtime_local_pool else 'absent'}",
    )
    if isinstance(adapter, ProviderPoolAdapter):
        legacy = adapter.legacy_fallback_command
        lines.append("AdapterSelected=ProviderPoolAdapter")
        lines.append(
            "LegacyFallbackCommand="
            + ("present" if legacy else "absent"),
        )
        lines.append(f"LegacyFallbackAdapter={adapter.legacy_fallback_adapter_name}")
        lines.append(f"TimeoutSeconds={adapter.timeout_seconds}")
    elif isinstance(adapter, CommandAgentAdapter):
        lines.append("AdapterSelected=CommandAgentAdapter")
    elif isinstance(adapter, CodexSubagentAdapter):
        lines.append("AdapterSelected=CodexSubagentAdapter")
    elif isinstance(adapter, DryRunStubAdapter):
        lines.append("AdapterSelected=DryRunStubAdapter")
    else:
        lines.append(f"AdapterSelected={type(adapter).__name__}")

    # Production-stub policy from the profile.
    agents_cfg = profile.get("agents", {}) or {}
    forbid_stub = bool(agents_cfg.get("forbid_stub_in_production"))
    allow_stub = bool(agents_cfg.get("allow_stub_for_tests"))
    lines.append(
        f"StubPolicy=forbid_in_production={forbid_stub} allow_stub_for_tests={allow_stub}",
    )
    lines.append("StubUsed=False")

    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
