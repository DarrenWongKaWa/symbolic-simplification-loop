"""Loop 019R — ScientificMetaReviewer runtime resolution tests.

These tests assert that the reviewer command can be resolved on this
machine where `codex` exists but is not in PATH. The runtime must:
- find a real codex binary via PATH or known absolute paths
- surface an actionable error when nothing resolves
- never silently fall back to a stub (ProductionStubForbidden=True)
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RESOLVER = REPO_ROOT / "scripts" / "codex_resolver.sh"

# Always invoke via /bin/bash so the test never depends on a PATH-resolved
# `bash`. (Some sandboxes do not put `bash` on PATH.)
_BASH = "/bin/bash"


def _find_real_codex_anywhere() -> Path | None:
    """Locate a real codex binary on disk; this is discovery, not policy."""
    shutil_which = shutil.which("codex")
    if shutil_which:
        return Path(shutil_which)
    candidates = []
    vscode_root = Path.home() / ".vscode/extensions"
    if vscode_root.exists():
        for path in vscode_root.rglob("codex"):
            if path.is_file() and os.access(path, os.X_OK):
                candidates.append(path)
    for absolute in (
        Path("/Applications/Codex.app/Contents/Resources/codex"),
        Path.home() / ".codex/plugins/.plugin-appserver/codex",
    ):
        if absolute.exists() and os.access(absolute, os.X_OK):
            candidates.append(absolute)
    if candidates:
        return candidates[0]
    return None


def test_resolver_script_exists_and_is_executable() -> None:
    assert RESOLVER.exists(), f"resolver script missing at {RESOLVER}"
    assert os.access(RESOLVER, os.X_OK), f"resolver script not executable: {RESOLVER}"


def test_resolver_emits_actionable_error_when_no_codex_found(tmp_path: Path) -> None:
    """If neither PATH nor fallback paths have codex, exit 127 with path list."""
    fake_path = tmp_path / "empty_path_bin"
    fake_path.mkdir()
    env = {
        "PATH": str(fake_path),
        "HOME": str(tmp_path),
        "USER": "test",
    }
    result = subprocess.run(
        [_BASH, str(RESOLVER)],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode != 0, (
        f"resolver unexpectedly succeeded with no codex; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "codex" in combined, (
        f"error message should mention codex; got: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    # The error message should list at least one searched location
    # so a human can fix the path on their machine.
    assert any(marker in combined for marker in ("searched", "path", "not found")), (
        f"error message should be actionable; got: stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_resolver_runs_real_codex_when_present() -> None:
    """If a real codex binary exists, the resolver must use it (no stub fallback).

    Skipped when there is no real binary on the test machine; otherwise
    the resolver must NOT report a 'not found' diagnostic.
    """
    if _find_real_codex_anywhere() is None:
        pytest.skip("no real codex binary on this machine; cannot verify positive path")
    env = os.environ.copy()
    env["HOME"] = str(Path.home())  # do not hide fallback
    env.pop("LOOP_CODEX_STUB", None)
    result = subprocess.run(
        [_BASH, str(RESOLVER), "--probe"],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if "not found" in (result.stdout + result.stderr).lower():
        pytest.fail(
            "resolver reports codex not found despite a real binary on disk: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )


def test_runtime_local_yaml_references_resolver_script() -> None:
    """agents/runtime.local.yaml must point at the resolver, not the raw wrapper."""
    rt = (REPO_ROOT / "agents" / "runtime.local.yaml").read_text(encoding="utf-8")
    assert "codex_resolver.sh" in rt, (
        f"runtime.local.yaml must invoke codex_resolver.sh; got:\n{rt}"
    )


def test_production_stub_remains_forbidden_in_runtime_local() -> None:
    """The runtime config must NOT embed a stub command in any `command:` block.

    We extract only the lines under each `runtime:` block (i.e. the
    YAML command lines, not annotations) and check those for stub
    indicators like `echo`, `cat`, `/bin/echo`, or a hard-coded exit
    code hack.
    """
    rt = (REPO_ROOT / "agents" / "runtime.local.yaml").read_text(encoding="utf-8")
    in_runtime_block = False
    command_block_lines: list[str] = []
    for line in rt.splitlines():
        if line.startswith("runtime:"):
            in_runtime_block = True
            continue
        if in_runtime_block and line and not line.startswith(" ") and line.endswith(":"):
            in_runtime_block = False
            continue
        if in_runtime_block:
            command_block_lines.append(line)
    blob = "\n".join(command_block_lines)
    for forbidden in ("- echo", '["echo', "/bin/echo", "exit 0", "True always"):
        assert forbidden not in blob, (
            f"runtime.local.yaml command block contains forbidden stub: {forbidden!r}\n{blob}"
        )

