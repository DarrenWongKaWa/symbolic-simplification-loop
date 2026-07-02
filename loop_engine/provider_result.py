"""Loop 021 — provider result normalization.

A single dataclass-style builder for the ``reviewer_provider_pool``
chain. The fields here are the ones ``review_result.json`` and
the runner actually consume; nothing more.

This module deliberately does NOT define a runtime or an
adapter — those live in ``loop_engine/agent_runtime.py`` (the
existing adapter machinery) and
``loop_engine/reviewer_provider_pool.py`` (the new pool).

Loop behavior, freeze_preconditions, completion_matrix,
human_signoff are NOT modified by this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---- retryable runtime statuses (allowed to fall through to next provider) ----
RETRYABLE_RUNTIME_STATUSES = frozenset(
    {
        "AGENT_QUOTA_LIMIT",
        "AGENT_TIMEOUT",
        "AGENT_NO_OUTPUT",
        "AGENT_COMMAND_NOT_FOUND",
        "AGENT_TRANSPORT_FAILURE",
        "AGENT_RUNTIME_FAILURE",
    }
)


# ---- runtime status values recognized across the pool ----
RUNTIME_STATUSES = frozenset(
    RETRYABLE_RUNTIME_STATUSES
    | {
        "AGENT_OK",
        "AGENT_SCHEMA_FAIL",
        "AGENT_ALL_PROVIDERS_UNAVAILABLE",
        "STUB_NOT_PRODUCTION",
        "NOT_INVOKED",
        "OTHER",
    }
)


# ---- verdict values recognized across the pool ----
REVIEWER_VERDICTS = frozenset(
    {"PASS", "PASS_WITH_CAVEAT", "FAIL", "NEEDS_PATCH", "BLOCKED"}
)


def is_retryable(runtime_status: str) -> bool:
    return runtime_status in RETRYABLE_RUNTIME_STATUSES


@dataclass
class ProviderAttempt:
    """One attempt of one provider inside a provider pool."""

    provider_name: str
    adapter: str
    enabled: bool
    selected: bool
    retryable: bool
    availability_status: str = "OTHER"
    runtime_status: str = "NOT_INVOKED"
    exit_code: int | str | None = None
    failure_summary_redacted: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "adapter": self.adapter,
            "enabled": self.enabled,
            "availability_status": self.availability_status,
            "runtime_status": self.runtime_status,
            "exit_code": self.exit_code,
            "retryable": self.retryable,
            "selected": self.selected,
            "failure_summary_redacted": self.failure_summary_redacted,
        }


@dataclass
class ReviewerProviderResult:
    """The pool-level outcome of running a reviewer-role invocation.

    This is the canonical shape written to
    ``.loop/agent_invocations/<role>/pool_result.json``. The
    runner adapters continue to write the existing
    ``invocation_summary.json`` for backwards compatibility; the
    pool result is an ADDITIONAL sibling artefact.
    """

    reviewer_role: str
    selected_provider: str | None
    provider_attempts: list[ProviderAttempt] = field(default_factory=list)
    adapter: str = ""
    actually_invoked: bool = False
    stub_used: bool = False
    runtime_status: str = "NOT_INVOKED"
    schema_valid: bool = False
    verdict: str | None = None
    retryable: bool = False
    fallback_reason: str | None = None
    secret_redaction_applied: bool = True
    review_debt_required: bool = False
    freeze_evidence_valid: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer_role": self.reviewer_role,
            "selected_provider": self.selected_provider,
            "provider_attempts": [a.to_dict() for a in self.provider_attempts],
            "adapter": self.adapter,
            "actually_invoked": self.actually_invoked,
            "stub_used": self.stub_used,
            "runtime_status": self.runtime_status,
            "schema_valid": self.schema_valid,
            "verdict": self.verdict,
            "retryable": self.retryable,
            "fallback_reason": self.fallback_reason,
            "secret_redaction_applied": self.secret_redaction_applied,
            "review_debt_required": self.review_debt_required,
            "freeze_evidence_valid": self.freeze_evidence_valid,
        }


def should_continue_to_next_provider(
    *,
    runtime_status: str,
    schema_valid: bool,
) -> bool:
    """The single source of truth for "fall through to next provider".

    Returns ``True`` ONLY when the chain should keep going
    because the just-completed attempt is a retryable runtime
    failure. Returns ``False`` for:

    - any schema-valid result (regardless of verdict),
    - any non-retryable failure,
    - AGENT_OK (no need to fall through).
    """
    if schema_valid:
        return False
    if runtime_status == "AGENT_OK":
        return False
    return is_retryable(runtime_status)
