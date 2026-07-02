#!/usr/bin/env python3
from __future__ import annotations

import argparse

import yaml
import _bootstrap  # noqa: F401
from loop_engine.agent_runtime import resolve_agent_runtime
from loop_engine.config import REPO_ROOT


def profile_config(profile: str) -> dict:
    path = REPO_ROOT / "profiles" / f"{profile}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Missing profile: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Check configured agent runtime availability.")
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    profile = profile_config(args.profile)
    status = resolve_agent_runtime(profile, args.profile)
    print(f"AgentRuntimeStatus -> {'AVAILABLE' if status.available else 'UNAVAILABLE'}")
    print(f"Adapter -> {status.adapter}")
    print(f"ProductionRunAllowed -> {status.production_run_allowed}")
    print(f"StubUsed -> {status.adapter == 'stub'}")
    print(f"MissingAgentCommands -> {status.missing_agent_commands}")
    if status.reason:
        print(f"Reason -> {status.reason}")


if __name__ == "__main__":
    main()
