#!/usr/bin/env python3
"""CLI for the artifact-based agent dispatcher (TASK_026 + TASK_027).

Manual-provider-only. Does NOT invoke Claude or Codex CLI on its own.
Supports ``--watch --poll-interval N`` for safe repeated one-phase
advancement that idles at waiting states and stops at the human
boundary.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from loop_engine import agent_bus


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Artifact-based agent dispatcher. Manual providers only; never "
            "invokes Claude or Codex CLI on its own."
        ),
    )
    parser.add_argument(
        "--bus-root",
        default="agent_bus",
        type=Path,
        help="Bus root directory (default: agent_bus).",
    )
    parser.add_argument("--next-action-report", type=Path, default=None)
    parser.add_argument("--round-id", default=None)
    parser.add_argument(
        "--acceptance-command",
        action="append",
        default=[],
        help="Acceptance command to run; repeatable.",
    )
    parser.add_argument("--advance", action="store_true", help="Advance exactly one phase.")
    parser.add_argument("--status", action="store_true", help="Print current status JSON.")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Rebuild summaries from existing artifacts (no phase advance).",
    )
    parser.add_argument("--no-command-run", action="store_true")
    parser.add_argument("--fail-reason", default=None, help="Move current pending item to failed/.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repo root for git diff evidence (default: cwd).",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run safe watch mode (TASK_027): repeated one-phase advance, "
             "idles when artifacts are missing, stops at human boundary.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Watch poll interval in seconds (default 1.0, floor 0.05).",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Optional cap on watch poll iterations.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    bus_root = Path(args.bus_root)

    if args.status:
        out = agent_bus.status(bus_root)
        print(json.dumps(out, indent=2, default=str))
        return 0

    if args.summary_only:
        out = agent_bus.summarize_only(bus_root, repo_root=args.repo_root)
        print(json.dumps(out, indent=2, default=str))
        return 0

    if args.fail_reason is not None:
        out = agent_bus.fail_pending(bus_root, args.fail_reason)
        print(json.dumps(out, indent=2, default=str))
        return 0

    if args.watch:
        agent_bus.ensure_bus_layout(bus_root)
        if args.next_action_report is not None:
            agent_bus.start_round(
                bus_root,
                next_action_report=args.next_action_report,
                round_id=args.round_id,
                force=args.force,
            )
        observations = agent_bus.watch(
            bus_root,
            poll_interval=args.poll_interval,
            max_iterations=args.max_iterations,
            repo_root=args.repo_root,
            acceptance_commands=args.acceptance_command or None,
            no_command_run=args.no_command_run,
        )
        print(json.dumps(observations, indent=2, default=str))
        return 0

    if args.advance or args.next_action_report is not None or args.round_id is not None:
        # Ensure layout on every advance invocation.
        agent_bus.ensure_bus_layout(bus_root)
        if args.round_id is not None and args.next_action_report is not None:
            state = agent_bus.start_round(
                bus_root,
                next_action_report=args.next_action_report,
                round_id=args.round_id,
                force=args.force,
            )
            agent_bus.write_round_state(bus_root, state)
        out = agent_bus.advance(
            bus_root,
            repo_root=args.repo_root,
            acceptance_commands=args.acceptance_command or None,
            no_command_run=args.no_command_run,
            force=args.force,
            next_action_report=args.next_action_report,
        )
        print(json.dumps(out, indent=2, default=str))
        return 0

    # Default: ensure layout + show status (idempotent).
    agent_bus.ensure_bus_layout(bus_root)
    out = agent_bus.status(bus_root)
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
