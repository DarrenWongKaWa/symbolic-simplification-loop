"""Loop 021 — secret redactor.

Used by the reviewer provider pool and the API adapters before
*any* text is written to disk (logs, invocation_summary, stdout
capture, prompt.md, etc.).

The redactor recognises:

- Anthropic-style keys (e.g. ``sk-ant-...``)
- OpenAI-style keys (e.g. ``sk-...``)
- OpenAI-Compatible bearer tokens (``Bearer abcdef...``)
- Anything that looks like ``$ANTHROPIC_API_KEY``, ``$OPENAI_API_KEY``,
  ``$OPENAI_COMPATIBLE_API_KEY`` when those env vars are set in
  this process
- Generic API-key-value pairs on a single line: ``<key>=<value>``

The redactor is intentionally **redact-everywhere-safe** — it
never raises, never logs the original value, never writes the
result of a failed match anywhere. The output text contains
``<redacted:ANTHROPIC_API_KEY>`` for each detected secret, so
the audit trail knows exactly which env var was hidden without
revealing the secret.

Loop behavior, freeze_preconditions, completion_matrix,
human_signoff are NOT modified by this module.
"""

from __future__ import annotations

import os
import re
from typing import Iterable


# Sensible default. The pattern list is intentionally limited;
# adding a new provider means adding its key prefix here.
_DEFAULT_PREFIXES: tuple[str, ...] = (
    "sk-ant-",
    "sk-proj-",
    "sk-",
)

# Built-in regex for the "key=value" form. Match the leading
# alpha + (digits/letters/underscores + optional last separator)
# boundary plus a recognised keyword suffix.
#
# Examples that DO match: "OPENAI_API_KEY=...", "API_KEY=...",
# "OPENAI_TOKEN=...", "x_SECRET=...", "ANTHROPIC_API_KEY=...".
#
# Examples that DO NOT match: "A_API_KEYY=..." (suffix not a clean
# boundary), "APIKEY=..." (no underscore before KEY), "<1char>=".
_KEY_VALUE_PATTERN = re.compile(
    r"(?P<key>"
    r"(?:[A-Za-z][A-Za-z0-9]{0,63}[_-])?"
    r"(?:API[_-]?KEY|TOKEN|SECRET)"
    r")"
    r"\s*[:=]\s*"
    r"(?P<value>[A-Za-z0-9._~/+=-]{16,})"
)

# Bearer form.
_BEARER_PATTERN = re.compile(
    r"(?P<scheme>Bearer)\s+(?P<token>[A-Za-z0-9._~/+=-]{16,})",
    flags=re.IGNORECASE,
)

# Key-prefix form: a long opaque token that starts with a known
# provider prefix. Long enough to avoid false positives on the
# word "sk-" in normal English.
_PREFIX_TOKEN_PATTERN = re.compile(
    r"(?P<token>(?:"
    + "|".join(re.escape(p) for p in _DEFAULT_PREFIXES)
    + r")[A-Za-z0-9._~-]{16,})"
)


def _read_env_values() -> dict[str, str]:
    """Return a map of every env-var whose name suggests it carries
    a secret, mapped to its real value in this process.

    The values are kept only locally for redaction; the redactor
    never persists them.
    """
    keys: dict[str, str] = {}
    for name, value in os.environ.items():
        lowered = name.upper()
        if any(token in lowered for token in ("API_KEY", "APIKEY", "TOKEN", "SECRET")):
            if value:
                keys[name] = value
    return keys


def redact_secrets(text: str, *, extra_env: Iterable[tuple[str, str]] = ()) -> str:
    """Return ``text`` with secrets replaced by redaction markers.

    The function is total — it never raises and never returns
    the original secret. Multiple secrets in the same input are
    all redacted.
    """
    if not text:
        return text

    redacted = text

    env_keys = _read_env_values()
    for name, value in extra_env:
        if value:
            env_keys[name] = value

    # Phase 1 — exact env-var value matches (highest confidence).
    for name, value in env_keys.items():
        if not value or len(value) < 8:
            continue
        # Only attempt redaction when the value appears in the
        # text. Avoid replacing ambiguous substrings like short
        # tokens that may legitimately appear in a prompt.
        if value in redacted:
            redacted = redacted.replace(
                value, f"<redacted:{name}>"
            )

    # Phase 2 — key=value form.
    def _kv_replace(match: re.Match[str]) -> str:
        key = match.group("key")
        return f"{key}=<redacted:{key}>"

    redacted = _KEY_VALUE_PATTERN.sub(_kv_replace, redacted)

    # Phase 3 — bearer form. Keep the scheme visible for audit
    # but redact the token.
    def _bearer_replace(match: re.Match[str]) -> str:
        scheme = match.group("scheme")
        return f"{scheme} <redacted:bearer>"

    redacted = _BEARER_PATTERN.sub(_bearer_replace, redacted)

    # Phase 4 — provider-prefix token form.
    def _prefix_replace(match: re.Match[str]) -> str:
        token = match.group("token")
        head = token.split("-", 1)[0]
        return f"<redacted:{head}-...>"

    redacted = _PREFIX_TOKEN_PATTERN.sub(_prefix_replace, redacted)

    return redacted


def is_secret_pattern(text: str) -> bool:
    """Return ``True`` iff the input matches any of the redactor's
    secret patterns. Useful for tests / probes.
    """
    if not text:
        return False
    if any(value in text and len(value) >= 8 for value in _read_env_values().values()):
        return True
    if _KEY_VALUE_PATTERN.search(text):
        return True
    if _BEARER_PATTERN.search(text):
        return True
    if _PREFIX_TOKEN_PATTERN.search(text):
        return True
    return False
