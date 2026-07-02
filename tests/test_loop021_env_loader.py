"""Loop 021 — minimal .env loader tests.

The loader reads a `.env` at the repo root and exports each
``KEY=VALUE`` line into ``os.environ``. It is intentionally
small:

- never performs shell expansion,
- never overwrites env vars that are already set
  (interactive-shell exports take precedence),
- never prints or persists the value.

These tests pin the loader contract so a future change cannot
inadvertently start logging secrets or substituting shell
expansion.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from loop_engine.config import _ENV_LOADED, load_dotenv
import loop_engine.config as config


@pytest.fixture
def clear_env_loader_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the loader singleton between tests."""
    monkeypatch.setattr(config, "_ENV_LOADED", False)
    for key in (
        "PROVAULT_TEST_KEY_A",
        "PROVAULT_TEST_KEY_B",
        "PROVAULT_QUOTED",
        "PROVAULT_HASHED",
        "PROVAULT_EXPORTED",
        "PROVAULT_INLINE_HASH",
    ):
        monkeypatch.delenv(key, raising=False)


def test_missing_dotenv_file_returns_not_loaded(
    tmp_path: Path, clear_env_loader_cache: None
) -> None:
    loaded, count = load_dotenv(tmp_path / ".env.missing")
    assert loaded is False
    assert count == 0


def test_basic_key_value_pairs_loaded(
    tmp_path: Path, clear_env_loader_cache: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "PROVAULT_TEST_KEY_A=value-a\n"
        "PROVAULT_TEST_KEY_B=value-b\n",
        encoding="utf-8",
    )
    loaded, count = load_dotenv(env_file)
    assert loaded is True
    assert count == 2
    # The loader mutates `os.environ`, so we read it back here.
    assert os.environ["PROVAULT_TEST_KEY_A"] == "value-a"
    assert os.environ["PROVAULT_TEST_KEY_B"] == "value-b"


def test_existing_env_var_is_not_overwritten_by_default(
    tmp_path: Path, clear_env_loader_cache: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PROVAULT_TEST_KEY_A", "interactive-shell")
    env_file = tmp_path / ".env"
    env_file.write_text("PROVAULT_TEST_KEY_A=dotenv-should-not-win\n", encoding="utf-8")
    loaded, count = load_dotenv(env_file)
    assert loaded is True
    assert count == 0  # nothing was applied
    assert os.environ["PROVAULT_TEST_KEY_A"] == "interactive-shell"


def test_override_true_does_overwrite(
    tmp_path: Path, clear_env_loader_cache: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PROVAULT_TEST_KEY_A", "interactive")
    env_file = tmp_path / ".env"
    env_file.write_text("PROVAULT_TEST_KEY_A=dotenv\n", encoding="utf-8")
    loaded, count = load_dotenv(env_file, override=True)
    assert loaded is True
    assert count == 1
    assert os.environ["PROVAULT_TEST_KEY_A"] == "dotenv"


def test_quoted_double_quoted_values_unquoted(
    tmp_path: Path, clear_env_loader_cache: None
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        'PROVAULT_QUOTED="with quotes"\n', encoding="utf-8"
    )
    load_dotenv(env_file)
    assert os.environ["PROVAULT_QUOTED"] == "with quotes"


def test_values_with_hash_in_them_kept(
    tmp_path: Path, clear_env_loader_cache: None
) -> None:
    """`#`-bearing values survive unless preceded by whitespace."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "PROVAULT_HASHED=abc#def\nPROVAULT_INLINE_HASH=abc #comment\n",
        encoding="utf-8",
    )
    load_dotenv(env_file)
    assert os.environ["PROVAULT_HASHED"] == "abc#def"
    # Trailing-inline-`#` becomes a comment because of whitespace
    # before it; we strip the comment.
    assert os.environ["PROVAULT_INLINE_HASH"] == "abc"


def test_export_prefix_tolerated(
    tmp_path: Path, clear_env_loader_cache: None
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("export PROVAULT_EXPORTED=ok\n", encoding="utf-8")
    load_dotenv(env_file)
    assert os.environ["PROVAULT_EXPORTED"] == "ok"


def test_comments_and_blanks_ignored(
    tmp_path: Path, clear_env_loader_cache: None
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n"
        "# leading comment\n"
        "  # indented comment\n"
        "\n"
        "PROVAULT_TEST_KEY_A=ok\n"
        "\n",
        encoding="utf-8",
    )
    loaded, count = load_dotenv(env_file)
    assert loaded is True
    assert count == 1
    assert os.environ["PROVAULT_TEST_KEY_A"] == "ok"


def test_dollar_signs_are_not_expanded(
    tmp_path: Path, clear_env_loader_cache: None
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("PROVAULT_TEST_KEY_A=sk-ant-$$literal$$\n", encoding="utf-8")
    load_dotenv(env_file)
    assert os.environ["PROVAULT_TEST_KEY_A"] == "sk-ant-$$literal$$"


def test_loader_is_idempotent_within_a_process(
    tmp_path: Path, clear_env_loader_cache: None
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("PROVAULT_TEST_KEY_A=first\n", encoding="utf-8")
    a_loaded, a_count = load_dotenv(env_file)
    # Second call within the same process is a no-op (returns
    # ``loaded=False, count=0``) so the loader is a singleton and
    # cannot double-count.
    b_loaded, b_count = load_dotenv(env_file)
    assert a_loaded is True and a_count == 1
    assert b_loaded is False and b_count == 0
