"""Loop 021 — secret redaction tests.

These tests pin the redaction contract. They do NOT exercise any
real network call; the redactor is pure text transformation.

Loop behavior, freeze_preconditions, completion_matrix, and
human_signoff are NOT modified by these tests.
"""

from __future__ import annotations

import os

import pytest

from loop_engine.secret_redaction import (
    is_secret_pattern,
    redact_secrets,
)


def test_redacts_anthropic_env_value_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-this-is-a-secret-1234567890abcdef")
    text = "Authorization header was sk-ant-this-is-a-secret-1234567890abcdef and call succeeded"
    out = redact_secrets(text)
    assert "sk-ant-this-is-a-secret-1234567890abcdef" not in out
    assert "ANTHROPIC_API_KEY" in out
    assert "redacted" in out


def test_redacts_openai_env_value_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-this-is-a-secret-1234567890abcdef")
    text = "openai_call body contains sk-proj-this-is-a-secret-1234567890abcdef as bearer token"
    out = redact_secrets(text)
    assert "sk-proj-this-is-a-secret-1234567890abcdef" not in out
    assert "OPENAI_API_KEY" in out


def test_redacts_openai_compatible_env_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "OPENAI_COMPATIBLE_API_KEY", "sk-openc-this-is-a-secret-1234567890abcdef"
    )
    text = "we call openai compatible at sk-openc-this-is-a-secret-1234567890abcdef"
    out = redact_secrets(text)
    assert "sk-openc-this-is-a-secret-1234567890abcdef" not in out
    assert "OPENAI_COMPATIBLE_API_KEY" in out


def test_redacts_bearer_token_in_text() -> None:
    text = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789"
    out = redact_secrets(text)
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in out
    assert "Bearer <redacted:bearer>" in out


def test_redacts_key_value_pattern() -> None:
    text = "OPENAI_API_KEY=sk-proj-supersecret1234567890123456"
    out = redact_secrets(text)
    assert "sk-proj-supersecret1234567890123456" not in out
    assert "OPENAI_API_KEY=<redacted:OPENAI_API_KEY>" in out


def test_redacts_provider_prefix_token() -> None:
    text = "raw sk-ant-api03-the-token-with-enough-entropy-abcdef-1234"
    out = redact_secrets(text)
    assert "the-token-with-enough-entropy-abcdef-1234" not in out
    # The prefix itself (sk-) becomes "<redacted:sk-...>"
    assert "sk-" in out  # the prefix marker survives
    assert "redacted" in out


def test_no_redaction_when_no_secrets_present(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure no other env vars confuse it.
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENAI_COMPATIBLE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    text = "summarize the latest review and proceed"
    out = redact_secrets(text)
    assert out == text


def test_empty_input_returns_empty() -> None:
    assert redact_secrets("") == ""


def test_is_secret_pattern_detects_key_value() -> None:
    assert is_secret_pattern("API_KEY=abcdefghijklmnopqrstuv")
    assert is_secret_pattern("bearer abcdefghijklmnopqrstuvwxyz0123")
    assert is_secret_pattern("sk-ant-abcdefghijklmnop1234")
    assert not is_secret_pattern("plain text without secrets")
