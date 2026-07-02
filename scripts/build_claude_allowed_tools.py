#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.executor_permission_policy import build_permission_policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Claude --allowedTools value from a bounded patch plan.")
    parser.add_argument("--plan", required=True, help="Path to the plan markdown file.")
    parser.add_argument(
        "--shell",
        action="store_true",
        help="Print only the comma-separated value suitable for Claude --allowedTools.",
    )
    parser.add_argument(
        "--require-bash",
        action="store_true",
        help="Fail if the generated tool list contains no Bash(...) entries.",
    )
    args = parser.parse_args()

    plan_path = Path(args.plan)
    policy = build_permission_policy(plan_path.read_text(encoding="utf-8"))
    issues: list[str] = []
    if args.require_bash and not any(tool.startswith("Bash(") for tool in policy.allowed_tools):
        issues.append("no Bash tools were generated from fenced Run bash blocks")
    overall_gate = "FAIL" if issues else "PASS"
    if args.shell:
        if issues:
            print("; ".join(issues), file=sys.stderr)
            raise SystemExit(1)
        print(policy.claude_allowed_tools_arg)
        return
    print(
        json.dumps(
            {
                "overall_gate": overall_gate,
                "plan": str(plan_path),
                "declared_commands": policy.declared_commands,
                "allowed_tools": policy.allowed_tools,
                "claude_allowed_tools_arg": policy.claude_allowed_tools_arg,
                "issues": issues,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
