#!/usr/bin/env python3
"""CLI wrapper for ``loop_engine.run_diagnosis``.

Emits a deterministic, read-only next-action report for a loop /
autonomous run. Does NOT modify scientific artifacts, signoff ledgers,
or frozen checkpoints.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401  (adds repo root to sys.path)

from loop_engine.run_diagnosis import (
    diagnose_run,
    write_next_action_reports,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose a loop or autonomous run and emit a deterministic "
            "next-action report (JSON + Markdown). Read-only."
        )
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        default=None,
        help=(
            "Run root directory. When provided without --stage, the tool will "
            "discover run-level artifacts (stages/, checkpoints/, "
            "AUTONOMOUS_LOOP_RUN_REPORT.md) and select a target stage "
            "deterministically."
        ),
    )
    parser.add_argument("--stage", type=Path, default=None, help="Stage directory. Takes precedence over --run-root stage selection.")
    parser.add_argument("--project", default=None, help="Project name. Used to resolve projects/<project>/loop.yaml stage order.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repo root for loop.yaml lookup. Defaults to auto-detect.",
    )
    parser.add_argument(
        "--command-return-code",
        type=int,
        default=None,
        help="Nonzero exit code from the command being diagnosed.",
    )
    parser.add_argument("--stdout-file", type=Path, default=None, help="Path to stdout capture.")
    parser.add_argument("--stderr-file", type=Path, default=None, help="Path to stderr capture.")
    parser.add_argument(
        "--command-status-json",
        type=Path,
        default=None,
        help="Path to a JSON file with command return_code/exit_code.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write next_action_report.{json,md} into.",
    )
    parser.add_argument("--json-only", action="store_true", help="Skip the markdown output.")
    parser.add_argument("--markdown-only", action="store_true", help="Skip the JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = diagnose_run(
        run_root=args.run_root,
        stage=args.stage,
        project=args.project,
        command_return_code=args.command_return_code,
        stdout_file=args.stdout_file,
        stderr_file=args.stderr_file,
        command_status_json=args.command_status_json,
        repo_root=args.repo_root,
    )
    json_path, md_path = write_next_action_reports(
        report,
        args.output_dir,
        json_only=args.json_only,
        markdown_only=args.markdown_only,
    )
    print(f"next_action_report.json: {json_path}")
    print(f"next_action_report.md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))