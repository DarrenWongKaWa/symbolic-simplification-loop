from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def relative_to_repo(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


# A minimal, non-shell-executing .env loader. Loop 021P + 021
# bring shell-only env var contract; many development harnesses do
# not propagate interactive exports into subprocess environments.
# To keep secrets out of git, users keep real keys in a local
# .env at the repo root (gitignored) and rely on this loader.
#
# The loader is deliberately small and explicit:
#
# - Only fills env vars that are NOT already set in os.environ;
#   the user's interactive shell takes precedence.
# - Parses only `KEY=VALUE` and `KEY="quoted value"` lines. Lines
#   starting with `#` are comments. Lines starting with `export `
#   are tolerated and the prefix is stripped.
# - Does NOT perform shell expansion (no ``$VAR`` substitution,
#   no backticks, no command substitution).
# - Loads the file ONCE per process; subsequent calls return
#   the same boolean result.
#
# Real values are never logged or persisted by this loader.

_ENV_LOADED: bool = False
_ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _parse_env_line(line: str) -> tuple[str, str] | None:
    """Parse a single .env line; return (key, value) or None.

    Strips inline comments only when the line uses ``#`` preceded
    by whitespace, so values containing ``#`` survive intact.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export ") :].lstrip()
    if "=" not in line:
        return None
    key, raw_value = line.split("=", 1)
    key = key.strip()
    if not _ENV_KEY_PATTERN.match(key):
        return None
    value = raw_value.strip()
    # Strip a trailing inline comment only when preceded by whitespace.
    # This avoids breaking values that include '#' (e.g. API key hashes).
    if not (value.startswith('"') or value.startswith("'")):
        hash_idx = -1
        in_quotes = False
        quote_char = ""
        for idx, ch in enumerate(value):
            if in_quotes:
                if ch == quote_char:
                    in_quotes = False
                continue
            if ch in ('"', "'"):
                in_quotes = True
                quote_char = ch
                continue
            if ch == "#":
                if idx > 0 and value[idx - 1].isspace():
                    hash_idx = idx
                    break
        if hash_idx >= 0:
            value = value[:hash_idx].rstrip()
    # Strip wrapping quote pair if present (no shell expansion).
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    return key, value


def load_dotenv(
    path: Path | None = None,
    *,
    override: bool = False,
) -> tuple[bool, int]:
    """Load ``.env`` into os.environ.

    Args:
        path: explicit file path (default: ``<repo_root>/.env``).
        override: when True, an existing env var IS overwritten.
            Default False so interactive exports take precedence.

    Returns:
        ``(loaded, count)``: whether the file was loaded and how
        many keys it contributed. Values are NEVER returned.
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        return (False, 0)
    if path is None:
        path = REPO_ROOT / ".env"
    if not path.exists():
        return (False, 0)
    count = 0
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        if not override and key in os.environ:
            continue
        # Value is set on os.environ; nothing here persists the value to disk.
        os.environ[key] = value
        count += 1
    _ENV_LOADED = True
    return (True, count)


def env_loader_already_run() -> bool:
    return _ENV_LOADED

