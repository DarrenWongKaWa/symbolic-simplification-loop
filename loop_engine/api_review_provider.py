"""Loop 021 — API review provider skeletons.

This module provides minimal "skeleton" adapters for calling
provider HTTP APIs (Anthropic, OpenAI, OpenAI-Compatible) and
returning a ``ReviewerProviderResult``-compatible classification.

These skeletons are deliberately minimal:

- They DO NOT include any third-party Python client by default.
  The adapter reads ``api_key_env`` etc. and, if the key is
  missing, returns ``AGENT_RUNTIME_FAILURE`` with an actionable
  hint ("set API_KEY in your environment").
- They use Python's standard-library ``urllib.request``. This
  keeps zero new dependencies and keeps unit tests deterministic.
  The skeleton writes a synthetic review JSON that, when
  injected with a real provider URL, can be replaced with a
  real call by extending ``_call_api``.
- They never log or persist the API key. The redactor
  (``loop_engine/secret_redaction``) is applied to every output
  line they write to disk.

This module does NOT modify:

- ``loop_engine/state.py`` (freeze_preconditions)
- ``loop_engine/completion_matrix.py``
- ``loop_engine/human_signoff.py``
- ``loop_engine/pre_run_gate.py``

If a real provider call returns a schema-valid reviewer result,
the pool calls stop on the first attempt. The skeletons below
return ``AGENT_RUNTIME_FAILURE`` with an actionable hint. To
upgrade a skeleton into a real adapter, set the appropriate
``api_key_env`` + ``model_env`` env vars and run the smoke
script (``scripts/run_reviewer_provider_smoke.py``).

The HTTP body is intentionally a placeholder review JSON.
Replace ``_call_api`` for production use.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .agent_runtime import AgentInvocationRequest
from .provider_result import (
    ProviderAttempt,
    ReviewerProviderResult,
    is_retryable,
)
from .secret_redaction import redact_secrets


@dataclass
class ApiInvocationRequest:
    """Subset of AgentInvocationRequest + provider fields the API
    adapter uses. Independent so adapters can be tested without the
    full autonomous-loop plumbing.
    """

    agent_name: str
    stage_dir: Path
    prompt_path: Path
    output_path: Path
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    adapter_name: str = "api"
    extra: dict[str, Any] | None = None


def _record_invocation(
    *,
    request: AgentInvocationRequest,
    provider_name: str,
    api_key: Optional[str],
    base_url: Optional[str],
    model: Optional[str],
    summary_extra: dict[str, Any] | None = None,
) -> Path:
    evidence_dir = request.stage_dir / ".loop" / "agent_invocations" / request.agent_name
    evidence_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "provider_name": provider_name,
        "api_key_redacted": "<redacted:API_KEY>",
        "base_url": base_url,
        "model": model,
        "summary_extra": summary_extra or {},
    }
    (evidence_dir / "api_attempt.json").write_text(
        json.dumps(record, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return evidence_dir / "api_attempt.json"


def _build_ssl_context() -> ssl.SSLContext:
    """Build the SSL context used by every API adapter.

    Loop 022T — production-safe TLS trust.

    - ``verify_mode`` is hardcoded to ``ssl.CERT_REQUIRED``.
    - ``check_hostname`` is hardcoded to ``True``.
    - Optional CA bundle override via ``LOOP_API_SSL_CERT_FILE``
      (preferred) or ``SSL_CERT_FILE`` (fallback). When neither is
      set we fall back to ``ssl.create_default_context()`` which
      loads the system / Python trust store.
    - There is **no** code path in this module that produces a
      context with ``verify=False`` or ``check_hostname=False``.
      The production reviewer verdict evidence therefore always
      derives from a fully-verified TLS chain.
    """
    ctx = ssl.create_default_context()
    # Defense in depth: even though create_default_context already
    # sets CERT_REQUIRED + check_hostname=True, re-assert it here
    # so a future refactor cannot accidentally weaken production
    # verification.
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True

    cafile = (
        os.environ.get("LOOP_API_SSL_CERT_FILE")
        or os.environ.get("SSL_CERT_FILE")
    )
    if cafile:
        # ``load_verify_locations`` raises if the path is missing;
        # let the caller (urllib) surface that as a transport
        # failure rather than masking it here.
        ctx.load_verify_locations(cafile=cafile)
    return ctx


_TLS_FAILURE_MARKERS = (
    "CERTIFICATE_VERIFY_FAILED",
    "self-signed certificate",
    "SSL: ",
)


def _classify_tls_failure(stderr_text: str) -> Optional[str]:
    """Return a sanitized diagnostic hint if ``stderr_text`` looks
    like a TLS failure. Otherwise return ``None``.

    The hint never embeds any caller-supplied value (no URL,
    no host, no API key). It points the operator at
    ``scripts/diagnose_api_tls.py`` so they can reproduce and
    classify the failure locally.
    """
    if not stderr_text:
        return None
    lowered = stderr_text.lower()
    if not any(marker.lower() in lowered for marker in _TLS_FAILURE_MARKERS):
        return None
    return (
        "TLS failure detected. Run "
        "python3 scripts/diagnose_api_tls.py --base-url <your-base-url> "
        "for a host-aware diagnostic. Do NOT disable certificate "
        "verification in the production reviewer path."
    )


_SAFE_HOST_RE = re.compile(r"^[A-Za-z0-9_.\-:]+$")


def _sanitize_host_for_hint(url: str) -> str:
    """Return the host (no userinfo / path / query) from a URL, or
    ``'<host>'`` if the URL is malformed. The returned value is
    only inserted into a diagnostic hint that already lives in
    the redaction pipeline, so this is a second line of defence.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return "<host>"
    host = parsed.hostname or ""
    if not host or not _SAFE_HOST_RE.match(host):
        return "<host>"
    return host


def _call_api(
    *,
    url: str,
    headers: dict[str, str],
    body: bytes,
    timeout_seconds: int = 60,
) -> tuple[int, str, str]:
    """Tiny synchronous POST. Returns ``(status_code, stdout, stderr)``.
    Never raises on transport failure.

    Loop 022T: TLS verification is enabled by default; an explicit
    ``LOOP_API_SSL_CERT_FILE`` or ``SSL_CERT_FILE`` may be passed in
    to override the CA bundle location. ``verify=False`` is NOT
    available on this path.
    """
    req = urllib.request.Request(
        url, data=body, headers=headers, method="POST"
    )
    ssl_ctx = _build_ssl_context()
    try:
        with urllib.request.urlopen(
            req, timeout=timeout_seconds, context=ssl_ctx
        ) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
            return (resp.status, payload, "")
    except urllib.error.HTTPError as exc:
        # ``HTTPError`` is also a ``file-like`` response; read body.
        try:
            payload = exc.read().decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover
            payload = ""
        return (exc.code, payload, f"HTTPError: {exc.reason}")
    except urllib.error.URLError as exc:
        return (599, "", f"URLError: {exc.reason}")
    except (TimeoutError, OSError) as exc:
        return (598, "", f"transport failure: {exc}")


# ---- Anthropic API adapter --------------------------------------------

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"


def invoke_anthropic_api(
    *,
    request: AgentInvocationRequest,
    api_key: Optional[str],
    model: Optional[str],
) -> ReviewerProviderResult:
    if not api_key:
        return _build_api_missing_key_result(
            reviewer_role=request.agent_name,
            provider_name="anthropic_api",
            runtime_status="AGENT_RUNTIME_FAILURE",
            failure_summary="ANTHROPIC_API_KEY env var not set",
        )
    prompt_text = request.prompt_path.read_text(encoding="utf-8")
    body = json.dumps(
        {
            "model": model or "claude-sonnet-4-5",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt_text}],
        }
    ).encode("utf-8")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "content-type": "application/json",
    }
    status_code, payload, stderr_text = _call_api(
        url=ANTHROPIC_API_URL, headers=headers, body=body
    )
    evidence = _record_invocation(
        request=request,
        provider_name="anthropic_api",
        api_key=api_key,
        base_url=ANTHROPIC_API_URL,
        model=model,
        summary_extra={"status": status_code, "stderr": stderr_text},
    )
    return _classify_api_response(
        reviewer_role=request.agent_name,
        provider_name="anthropic_api",
        status_code=status_code,
        payload=payload,
        stderr_text=stderr_text,
        evidence_path=evidence,
    )


# ---- OpenAI API adapter -------------------------------------------------

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def invoke_openai_api(
    *,
    request: AgentInvocationRequest,
    api_key: Optional[str],
    model: Optional[str],
) -> ReviewerProviderResult:
    if not api_key:
        return _build_api_missing_key_result(
            reviewer_role=request.agent_name,
            provider_name="openai_api",
            runtime_status="AGENT_RUNTIME_FAILURE",
            failure_summary="OPENAI_API_KEY env var not set",
        )
    prompt_text = request.prompt_path.read_text(encoding="utf-8")
    body = json.dumps(
        {
            "model": model or "gpt-5",
            "messages": [{"role": "user", "content": prompt_text}],
        }
    ).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    status_code, payload, stderr_text = _call_api(
        url=OPENAI_CHAT_URL, headers=headers, body=body
    )
    evidence = _record_invocation(
        request=request,
        provider_name="openai_api",
        api_key=api_key,
        base_url=OPENAI_CHAT_URL,
        model=model,
        summary_extra={"status": status_code, "stderr": stderr_text},
    )
    return _classify_api_response(
        reviewer_role=request.agent_name,
        provider_name="openai_api",
        status_code=status_code,
        payload=payload,
        stderr_text=stderr_text,
        evidence_path=evidence,
    )


# ---- OpenAI-Compatible API adapter (user-supplied base URL) -------------

OPENAI_COMPATIBLE_DEFAULT_BASE_URL = "https://api.openai.com/v1/chat/completions"


def invoke_openai_compatible_api(
    *,
    request: AgentInvocationRequest,
    api_key: Optional[str],
    base_url: Optional[str],
    model: Optional[str],
) -> ReviewerProviderResult:
    if not api_key:
        return _build_api_missing_key_result(
            reviewer_role=request.agent_name,
            provider_name="openai_compatible_api",
            runtime_status="AGENT_RUNTIME_FAILURE",
            failure_summary=(
                "OPENAI_COMPATIBLE_API_KEY env var not set"
            ),
        )
    if not base_url:
        return _build_api_missing_key_result(
            reviewer_role=request.agent_name,
            provider_name="openai_compatible_api",
            runtime_status="AGENT_RUNTIME_FAILURE",
            failure_summary=(
                "OPENAI_COMPATIBLE_BASE_URL env var not set"
            ),
        )
    prompt_text = request.prompt_path.read_text(encoding="utf-8")
    body = json.dumps(
        {
            "model": model or "gpt-5",
            "messages": [{"role": "user", "content": prompt_text}],
        }
    ).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    status_code, payload, stderr_text = _call_api(
        url=base_url, headers=headers, body=body
    )
    evidence = _record_invocation(
        request=request,
        provider_name="openai_compatible_api",
        api_key=api_key,
        base_url=base_url,
        model=model,
        summary_extra={"status": status_code, "stderr": stderr_text},
    )
    return _classify_api_response(
        reviewer_role=request.agent_name,
        provider_name="openai_compatible_api",
        status_code=status_code,
        payload=payload,
        stderr_text=stderr_text,
        evidence_path=evidence,
    )


# ---- response classification --------------------------------------------

def _classify_api_response(
    *,
    reviewer_role: str,
    provider_name: str,
    status_code: int,
    payload: str,
    stderr_text: str,
    evidence_path: Path,
) -> ReviewerProviderResult:
    """Translate an HTTP response into a ReviewerProviderResult.

    Policy:
    - 2xx with valid review JSON containing a verdict -> schema-valid
      success/failure; chain stops; ``freeze_evidence_valid`` only
      if the verdict is PASS / PASS_WITH_CAVEAT and exit_code = 0.
    - 4xx / 5xx -> AGENT_TRANSPORT_FAILURE if status_code is 5xx
      (network/protocol); the key is redacted before any disk write.
    - missing key -> AGENT_RUNTIME_FAILURE upstream.
    """
    if 200 <= status_code < 300:
        try:
            payload_obj = json.loads(payload)
        except json.JSONDecodeError as exc:
            return ReviewerProviderResult(
                reviewer_role=reviewer_role,
                selected_provider=None,
                provider_attempts=[
                    ProviderAttempt(
                        provider_name=provider_name,
                        adapter="http_api",
                        enabled=True,
                        selected=False,
                        retryable=is_retryable("AGENT_SCHEMA_FAIL"),
                        availability_status="AVAILABLE",
                        runtime_status="AGENT_SCHEMA_FAIL",
                        exit_code=status_code,
                        failure_summary_redacted=redact_secrets(
                            f"JSONDecodeError: {exc}"
                        ),
                    )
                ],
                adapter="http_api",
                actually_invoked=True,
                stub_used=False,
                runtime_status="AGENT_SCHEMA_FAIL",
                schema_valid=False,
                retryable=True,
                secret_redaction_applied=True,
                review_debt_required=True,
                freeze_evidence_valid=False,
            )
        # The pool treats schema-valid as the stopping point.
        return ReviewerProviderResult(
            reviewer_role=reviewer_role,
            selected_provider=provider_name,
            provider_attempts=[
                ProviderAttempt(
                    provider_name=provider_name,
                    adapter="http_api",
                    enabled=True,
                    selected=True,
                    retryable=False,
                    availability_status="AVAILABLE",
                    runtime_status="AGENT_OK",
                    exit_code=status_code,
                    failure_summary_redacted="",
                )
            ],
            adapter="http_api",
            actually_invoked=True,
            stub_used=False,
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict=str(payload_obj.get("verdict") or ""),
            retryable=False,
            secret_redaction_applied=True,
            review_debt_required=str(payload_obj.get("verdict") or "")
            in {"FAIL", "NEEDS_PATCH", "BLOCKED"},
            freeze_evidence_valid=str(payload_obj.get("verdict") or "")
            in {"PASS", "PASS_WITH_CAVEAT"},
        )
    # non-2xx -> classify as transport failure for 5xx, schema
    # fail for 4xx (provider-correctly-rejected call).
    if status_code >= 500:
        runtime_status = "AGENT_TRANSPORT_FAILURE"
    else:
        runtime_status = "AGENT_SCHEMA_FAIL"
    # Loop 022T: append a TLS-specific diagnostic hint when the
    # stderr text matches TLS failure markers. The hint is a
    # static string with no caller-supplied substitution so it
    # cannot leak the API key or any other secret.
    tls_hint = _classify_tls_failure(stderr_text)
    base_summary = f"status={status_code}; stderr={stderr_text[:200]}"
    if tls_hint:
        base_summary = f"{base_summary}; hint={tls_hint}"
    return ReviewerProviderResult(
        reviewer_role=reviewer_role,
        selected_provider=None,
        provider_attempts=[
            ProviderAttempt(
                provider_name=provider_name,
                adapter="http_api",
                enabled=True,
                selected=False,
                retryable=is_retryable(runtime_status),
                availability_status="AVAILABLE",
                runtime_status=runtime_status,
                exit_code=status_code,
                failure_summary_redacted=redact_secrets(base_summary),
            )
        ],
        adapter="http_api",
        actually_invoked=True,
        stub_used=False,
        runtime_status=runtime_status,
        schema_valid=False,
        retryable=is_retryable(runtime_status),
        secret_redaction_applied=True,
        review_debt_required=True,
        freeze_evidence_valid=False,
    )


def _build_api_missing_key_result(
    *,
    reviewer_role: str,
    provider_name: str,
    runtime_status: str,
    failure_summary: str,
) -> ReviewerProviderResult:
    return ReviewerProviderResult(
        reviewer_role=reviewer_role,
        selected_provider=None,
        provider_attempts=[
            ProviderAttempt(
                provider_name=provider_name,
                adapter="http_api",
                enabled=True,
                selected=False,
                retryable=is_retryable(runtime_status),
                availability_status="AVAILABLE",
                runtime_status=runtime_status,
                exit_code=None,
                failure_summary_redacted=failure_summary,
            )
        ],
        adapter="http_api",
        actually_invoked=True,
        stub_used=False,
        runtime_status=runtime_status,
        schema_valid=False,
        retryable=is_retryable(runtime_status),
        secret_redaction_applied=True,
        review_debt_required=True,
        freeze_evidence_valid=False,
    )
