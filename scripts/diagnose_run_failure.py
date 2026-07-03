#!/usr/bin/env python3
"""CLI wrapper for ``loop_engine.run_diagnosis``.

Emits a deterministic, read-only next-action report for a loop /
autonomous run. Does NOT modify scientific artifacts, signoff ledgers,
or frozen checkpoints.

Output contract (TASK_025_BACKFILL)
-----------------------------------

This CLI emits a *stable* stdout contract for automation, dispatcher
providers, and Langflow integration. The contract is:

* ``--output-mode json``    -> stdout mentions only the JSON artifact
  path (or the JSON payload itself when ``--print-json`` is set).
  Markdown paths / summaries are NEVER printed.
* ``--output-mode markdown``-> stdout mentions only the markdown
  artifact path (or the markdown payload itself when
  ``--print-markdown`` is set). JSON paths are NEVER printed unless
  an explicit print flag requests them.
* ``--output-mode both``    -> stdout reports both artifact paths in
  deterministic order: JSON first, then markdown.

Default mode is ``both`` for backward compatibility. The legacy
``--json-only`` and ``--markdown-only`` flags remain supported as
aliases for ``--output-mode json`` and ``--output-mode markdown``
respectively. They are mutually exclusive with each other and with
``--output-mode``; the CLI rejects contradictory argument combinations
with a nonzero exit.

Automation flags:

* ``--quiet``              -> suppress nonessential stdout. Explicit
  ``--print-json`` /
  ``--print-markdown`` still emit their payload.
* ``--print-json``         -> emit the JSON report payload to stdout.
  When this flag is set, the artifact path line is suppressed so
  stdout is purely parseable JSON (e.g. ``... | python -m json.tool``).
* ``--print-markdown``     -> emit the markdown report payload to
  stdout. When this flag is set, the artifact path line is
  suppressed so stdout is purely the markdown payload.
* ``--outdir``             -> alias for ``--output-dir``; both are
  accepted and rejected if combined with the other.

Exit codes
----------

* ``0``  successful diagnosis and requested report generation.
* ``2``  argument errors, including: contradictory or invalid flags;
  missing ``--output-dir`` / ``--outdir``; explicit path arguments
  (``--run-root``, ``--stage``, ``--stdout-file``, ``--stderr-file``,
  ``--command-status-json``, ``--repo-root``) that do not exist;
  ``--command-status-json`` that exists but is not parseable JSON.
* ``1``  schema validation failure or filesystem write failure.
  Diagnostic errors go to stderr so the stdout contract remains
  parseable.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

import _bootstrap  # noqa: F401  (adds repo root to sys.path)

from loop_engine.run_diagnosis import (
    diagnose_run,
    render_next_action_markdown,
    write_next_action_reports,
)


OUTPUT_MODES = ("json", "markdown", "both")
DEFAULT_OUTPUT_MODE = "both"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="diagnose_run_failure",
        description=(
            "Diagnose a loop or autonomous run and emit a deterministic "
            "next-action report (JSON + Markdown). Read-only."
        ),
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

    # Output directory: --output-dir (canonical) and --outdir (alias).
    outdir_group = parser.add_mutually_exclusive_group()
    outdir_group.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write next_action_report.{json,md} into.",
    )
    outdir_group.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Alias for --output-dir.",
    )

    # Output mode: --output-mode (canonical) and --json-only / --markdown-only (legacy aliases).
    parser.add_argument(
        "--output-mode",
        choices=OUTPUT_MODES,
        default=None,
        help=(
            f"What to emit. 'json' writes/mentions only the JSON artifact. "
            f"'markdown' writes/mentions only the markdown artifact. "
            f"'both' writes/mentions both. Default: {DEFAULT_OUTPUT_MODE}."
        ),
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Legacy alias for --output-mode json.",
    )
    parser.add_argument(
        "--markdown-only",
        action="store_true",
        help="Legacy alias for --output-mode markdown.",
    )

    # Automation flags.
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress nonessential stdout. Explicit --print-json / --print-markdown still emit.",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Emit the JSON report payload to stdout (in addition to writing the artifact).",
    )
    parser.add_argument(
        "--print-markdown",
        action="store_true",
        help="Emit the markdown report payload to stdout (in addition to writing the artifact).",
    )

    return parser


def _resolve_output_mode(args: argparse.Namespace) -> str:
    """Pick a single output mode, rejecting contradictory combinations."""
    explicit: list[str] = []
    if args.output_mode is not None:
        explicit.append("--output-mode")
    if args.json_only:
        explicit.append("--json-only")
    if args.markdown_only:
        explicit.append("--markdown-only")

    if len(explicit) > 1:
        raise SystemExit(
            f"error: contradictory output-mode flags: {', '.join(explicit)}; "
            f"use only one of --output-mode, --json-only, or --markdown-only.",
        )

    if args.output_mode is not None:
        return args.output_mode
    if args.json_only:
        return "json"
    if args.markdown_only:
        return "markdown"
    return DEFAULT_OUTPUT_MODE


def _resolve_outdir(args: argparse.Namespace) -> Path:
    outdir = args.output_dir if args.output_dir is not None else args.outdir
    if outdir is None:
        raise SystemExit(
            "error: --output-dir (or its alias --outdir) is required.",
        )
    return outdir


def _stdout_print(*, mode: str, json_path: Path | None, md_path: Path | None) -> None:
    """Print artifact paths in deterministic order based on mode.

    - json:    only JSON path.
    - markdown: only markdown path.
    - both:    JSON path first, then markdown path.
    """
    if mode == "json":
        if json_path is not None:
            print(f"next_action_report.json: {json_path}")
        return
    if mode == "markdown":
        if md_path is not None:
            print(f"next_action_report.md: {md_path}")
        return
    # both
    if json_path is not None:
        print(f"next_action_report.json: {json_path}")
    if md_path is not None:
        print(f"next_action_report.md: {md_path}")


# Explicit user-provided path arguments that must exist when set.
# (TASK_025_BACKFILL blocking issue 2: unreadable explicit inputs -> nonzero exit.)
_EXPLICIT_PATH_ARGS: tuple[str, ...] = (
    "run_root",
    "stage",
    "stdout_file",
    "stderr_file",
    "command_status_json",
    "repo_root",
)


def _validate_explicit_paths(args: argparse.Namespace) -> str | None:
    """Return an error message string for the first missing explicit path, else None.

    Each user-provided path argument must point at something that exists.
    Missing internal artifacts (e.g. ``.loop/validation_summary.json``) are
    still diagnosable and exit 0; only top-level path arguments that the
    user pointed at are treated as input contract errors.
    """
    for name in _EXPLICIT_PATH_ARGS:
        path = getattr(args, name, None)
        if path is None:
            continue
        if not path.exists():
            return f"error: --{name.replace('_', '-')} does not exist: {path}"
    if args.command_status_json is not None:
        # Argument exists; must be parseable JSON.
        try:
            json.loads(args.command_status_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return f"error: --command-status-json is not valid JSON: {exc}"
        except OSError as exc:
            return f"error: --command-status-json is unreadable: {exc}"
    return None


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        mode = _resolve_output_mode(args)
        outdir = _resolve_outdir(args)
    except SystemExit as exc:
        # argparse-style error path: message already mentions "error:"; print to stderr and exit nonzero.
        print(str(exc), file=sys.stderr)
        return 2

    # In json-only / markdown-only modes, only the corresponding print flag is allowed.
    if mode == "json" and args.print_markdown:
        print("error: --print-markdown is incompatible with --output-mode json / --json-only.", file=sys.stderr)
        return 2
    if mode == "markdown" and args.print_json:
        print("error: --print-json is incompatible with --output-mode markdown / --markdown-only.", file=sys.stderr)
        return 2

    # Explicit-input validation: each user-provided path must exist; --command-status-json
    # must be parseable JSON. Internal artifacts inside a valid --run-root / --stage are
    # still diagnosable and exit 0 with MISSING_REQUIRED_FILE.
    path_error = _validate_explicit_paths(args)
    if path_error is not None:
        print(path_error, file=sys.stderr)
        return 2

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

    # Resolve which artifacts to write. We only need to write the requested
    # artifact(s) in their respective mode. `write_next_action_reports`
    # already supports json_only / markdown_only; map mode -> flags.
    json_only = mode == "json"
    markdown_only = mode == "markdown"

    try:
        json_path, md_path = write_next_action_reports(
            report,
            outdir,
            json_only=json_only,
            markdown_only=markdown_only,
        )
    except Exception as exc:  # schema validation, OSError, etc.
        print(f"error: failed to write report: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    # Stdout contract: when an explicit print flag is set, the path line is
    # suppressed so stdout is *purely* the printed payload (or the two
    # payloads, in JSON-then-markdown order). This makes
    # `... | python -m json.tool` and `json.loads(proc.stdout)` work.
    has_print_json = bool(args.print_json) and not markdown_only
    has_print_markdown = bool(args.print_markdown) and not json_only
    if not args.quiet and not (has_print_json or has_print_markdown):
        _stdout_print(mode=mode, json_path=json_path, md_path=md_path)

    # Print payloads. Deterministic order: JSON first, then markdown.
    if has_print_json:
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"error: failed to read JSON report for --print-json: {exc}", file=sys.stderr)
            return 1
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        sys.stdout.write("\n")

    if has_print_markdown:
        try:
            md_payload = render_next_action_markdown(report)
        except Exception as exc:
            print(f"error: failed to render markdown for --print-markdown: {exc}", file=sys.stderr)
            return 1
        sys.stdout.write(md_payload)
        if not md_payload.endswith("\n"):
            sys.stdout.write("\n")

    return 0


__all__ = [
    "main",
    "_build_parser",
    "_resolve_output_mode",
    "_resolve_outdir",
    "_validate_explicit_paths",
    "_stdout_print",
    "OUTPUT_MODES",
    "DEFAULT_OUTPUT_MODE",
]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
