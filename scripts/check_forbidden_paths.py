#!/usr/bin/env python3
"""TASK_040 forbidden-path smoke checker.

Read-only CLI that runs ``git status --short`` in the current working
directory (or ``--cwd``) and reports whether any dirty path matches the
construction-loop forbidden-path denylist documented in
``docs/safety.md`` and the master repair framework.

This is a smoke checker, not a runner. It must not modify, stage,
commit, sign off, freeze, or push anything.

Exit codes:

* ``0`` — no forbidden dirty paths detected.
* ``1`` — one or more forbidden dirty paths detected.
* ``2`` — ``git status --short`` could not be executed (e.g. not a git
  working tree, git missing).

The script intentionally avoids non-stdlib dependencies so it can run
in a fresh clone or in a temporary smoke-test repository.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

# Self-exclusion: when this script is itself a dirty path under
# ``scripts/`` (which is forbidden by default), running it from the
# worktree would report itself. The PLAN explicitly notes this is the
# only permitted scripts exception for TASK_040. We never flag our own
# path.
SELF_REL_PATH = "scripts/check_forbidden_paths.py"


# Denylist mirroring the construction-loop forbidden-path policy in
# ``docs/safety.md`` and the master repair framework. Categories that
# are documentation-only (e.g. ``validation artifacts``, ``scientific
# output files``) are intentionally omitted — per PLAN §10 we must not
# invent broad destructive matching beyond the documented path denylist.
FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "sigma_abc/",
    "checkpoints/",
    "human_signoff",
    "docs/devlog/audits/",
    "agent_bus/",
    "loop_engine/",
    "schemas/",
    "scripts/",
    ".loop/human_signoff.yaml",
    "LOOP.md",
    "STATE.md",
    "loop-budget.md",
    "loop-run-log.md",
    ".claude/",
    ".github/",
    "patterns/",
    "loop-constraints.md",
    ".gitmodules",
    "loop-engineering*",
)


def parse_status_lines(stdout: str) -> list[str]:
    """Parse ``git status --short`` output into a sorted list of paths.

    Status lines look like ``XY path`` or ``XY path -> otherpath`` for
    renames/copies. We extract the source path, which is the path that
    would be staged or written, not the rename target.
    """

    paths: set[str] = set()
    for raw_line in stdout.splitlines():
        if not raw_line.strip():
            continue
        # Status format: XY <path>  (or "XY <from> -> <to>" for renames).
        # Strip the leading 2-byte status, plus optional rename score.
        # Position 3 is the first space; everything after is the path(s).
        if len(raw_line) < 3 or raw_line[2] != " ":
            continue
        payload = raw_line[3:].strip()
        if " -> " in payload:
            payload = payload.split(" -> ", 1)[1]
        # Unquote if git used octal-escaped quoting.
        payload = payload.strip('"')
        if payload:
            paths.add(payload)
    return sorted(paths)


def matches_forbidden(rel_posix: str) -> str | None:
    """Return the first pattern matching ``rel_posix``, else ``None``.

    ``rel_posix`` must be a forward-slash path relative to the repo
    root, with no leading ``./``.
    """

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.endswith("/"):
            # Directory pattern: match any path starting with the dir.
            prefix = pattern.rstrip("/")
            if rel_posix == prefix or rel_posix.startswith(prefix + "/"):
                return pattern
        elif pattern.endswith("*"):
            # Glob-style suffix (e.g. ``loop-engineering*``).
            stem = pattern[:-1]
            top = rel_posix.split("/", 1)[0]
            if top.startswith(stem):
                return pattern
        else:
            # Exact or prefix token (e.g. ``human_signoff``,
            # ``.loop/human_signoff.yaml``, ``LOOP.md``).
            top = rel_posix.split("/", 1)[0]
            if top == pattern or rel_posix.startswith(pattern + "/"):
                return pattern
            if rel_posix == pattern:
                return pattern
    return None


def classify(
    paths: list[str], repo_root: Path
) -> tuple[list[tuple[str, str]], list[str]]:
    """Split dirty paths into forbidden hits and clean paths.

    Self-excludes ``scripts/check_forbidden_paths.py`` per the TASK_040
    narrow exception.
    """

    forbidden: list[tuple[str, str]] = []
    clean: list[str] = []
    for raw in paths:
        rel = PurePosixPath(raw.replace(os.sep, "/"))
        try:
            rel_posix = rel.relative_to(
                PurePosixPath(repo_root.as_posix())
            ).as_posix()
        except ValueError:
            # Path outside repo root — treat as its raw form.
            rel_posix = rel.as_posix()
        if rel_posix == SELF_REL_PATH:
            clean.append(raw)
            continue
        match = matches_forbidden(rel_posix)
        if match is None:
            clean.append(raw)
        else:
            forbidden.append((raw, match))
    return forbidden, clean


def run_git_status(cwd: Path) -> tuple[int, str, str]:
    """Run ``git status --short`` in ``cwd``. Returns (rc, stdout, stderr)."""

    if shutil.which("git") is None:
        return 127, "", "git executable not found on PATH"
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def format_report(
    forbidden: list[tuple[str, str]],
    clean: list[str],
    cwd: Path,
) -> str:
    """Render a reviewer-readable summary."""

    lines: list[str] = []
    lines.append("TASK_040 forbidden-path smoke checker")
    lines.append(f"  cwd            : {cwd}")
    lines.append(f"  forbidden hits : {len(forbidden)}")
    lines.append(f"  clean dirty    : {len(clean)}")
    if forbidden:
        lines.append("")
        lines.append("Forbidden dirty paths:")
        for path, pattern in forbidden:
            lines.append(f"  - {path}  (matched: {pattern})")
    else:
        lines.append("")
        lines.append("No forbidden dirty paths detected.")
    if clean:
        lines.append("")
        lines.append("Non-forbidden dirty paths (informational only):")
        for path in clean:
            lines.append(f"  - {path}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_forbidden_paths.py",
        description=(
            "Read-only smoke checker: reports whether current "
            "git dirty paths match the construction-loop "
            "forbidden-path denylist."
        ),
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Working directory (default: current directory).",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help=(
            "Run an internal behavior smoke test using a temp "
            "git repo and exit. Does not touch the worktree."
        ),
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    cwd = Path(args.cwd).resolve()
    rc, stdout, stderr = run_git_status(cwd)
    if rc != 0:
        sys.stderr.write(
            f"check_forbidden_paths: git status --short failed "
            f"(rc={rc}): {stderr.strip()}\n"
        )
        return 2

    paths = parse_status_lines(stdout)
    forbidden, clean = classify(paths, cwd)
    sys.stdout.write(format_report(forbidden, clean, cwd))
    return 1 if forbidden else 0


def run_self_test() -> int:
    """Internal behavior smoke test in a temp git repo.

    Verifies: clean repo -> 0; benign dirty -> 0; forbidden dirty -> 1.
    Does not modify the worktree.
    """

    import tempfile

    tmp = tempfile.mkdtemp(prefix="check_forbidden_paths_selftest_")
    try:
        cwd = Path(tmp)
        # git init + initial commit so HEAD exists.
        for args in (
            ("init", "-q"),
            ("config", "user.email", "selftest@example.com"),
            ("config", "user.name", "selftest"),
            ("commit", "--allow-empty", "-q", "-m", "init"),
        ):
            subprocess.run(
                ["git", *args],
                cwd=str(cwd),
                check=True,
                capture_output=True,
                text=True,
            )

        # 1) Clean repo -> 0.
        rc, out, err = run_git_status(cwd)
        assert rc == 0, (rc, out, err)
        paths = parse_status_lines(out)
        forbidden, clean = classify(paths, cwd)
        assert forbidden == [], forbidden
        assert paths == [], paths

        # 2) Benign dirty -> 0.
        (cwd / "README.md").write_text("hi\n", encoding="utf-8")
        rc, out, err = run_git_status(cwd)
        assert rc == 0, (rc, out, err)
        paths = parse_status_lines(out)
        forbidden, clean = classify(paths, cwd)
        assert forbidden == [], forbidden
        assert clean == ["README.md"], clean

        # 3) Forbidden dirty -> 1.
        (cwd / "sigma_abc").mkdir()
        (cwd / "sigma_abc" / "dirty.txt").write_text("x", encoding="utf-8")
        rc, out, err = run_git_status(cwd)
        assert rc == 0, (rc, out, err)
        paths = parse_status_lines(out)
        forbidden, clean = classify(paths, cwd)
        assert len(forbidden) == 1, forbidden
        assert forbidden[0][1] == "sigma_abc/", forbidden

        # 4) Loop-engineering dir (glob pattern) -> 1.
        (cwd / "sigma_abc" / "dirty.txt").unlink()
        (cwd / "sigma_abc").rmdir()
        (cwd / "loop-engineering-clone").mkdir()
        (cwd / "loop-engineering-clone" / "a.txt").write_text(
            "x", encoding="utf-8"
        )
        rc, out, err = run_git_status(cwd)
        assert rc == 0, (rc, out, err)
        paths = parse_status_lines(out)
        forbidden, clean = classify(paths, cwd)
        assert len(forbidden) == 1, forbidden
        assert forbidden[0][1] == "loop-engineering*", forbidden

        sys.stdout.write(
            "self-test: OK (clean=0, benign=0, forbidden=1, glob=1)\n"
        )
        return 0
    except AssertionError as exc:  # pragma: no cover - diagnostics only
        sys.stderr.write(f"self-test FAILED: {exc!r}\n")
        return 1
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        sys.stderr.write(
            f"self-test: git failed: {exc.stderr or exc.stdout}\n"
        )
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())