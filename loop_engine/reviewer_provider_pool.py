"""Loop 021 — reviewer provider pool.

Pipeline::

    Profile.runtime -> pool-or-legacy
    Pool OR legacy: invocation returns an invocation_summary.json
    Pool additionally writes pool_result.json sibling

The pool itself is intentionally minimal:

- loads provider configs from ``agents/runtime.local.yaml`` (which
  is gitignored) or from the profile's own ``runtime`` block,
- resolves each provider's availability via env-var probe,
- runs each enabled provider in declared order using an injected
  adapter,
- falls through to the next provider **only when** the just-finished
  attempt classified as a retryable runtime failure
  (``provider_result.is_retryable``),
- freezes on the first attempt that produces a schema-valid
  reviewer result, regardless of verdict,
- never substitutes a stub when ``forbid_stub`` is true,
- writes a ``pool_result.json`` next to each ``invocation_summary.json``.

This module does NOT replace the existing
``loop_engine/agent_runtime.py::CommandAgentAdapter``. It uses it
when ``adapter: command`` is configured for a pool provider.

Loop behavior, freeze_preconditions, completion_matrix,
human_signoff are NOT modified by this module. The pool is an
ADDITIVE availability layer.

No network calls happen at import time. Providers are
probed only when an attempt is run.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

from .agent_runtime import (
    AgentInvocationRequest,
    CommandAgentAdapter,
    _runtime_status_from_result,
    file_sha256,
    hash_protected_files,
    verify_read_only_contract,
    write_invocation_summary,
)
from .config import REPO_ROOT, read_text, utc_now, write_json, write_text
from .provider_result import (
    ProviderAttempt,
    ReviewerProviderResult,
    is_retryable,
    should_continue_to_next_provider,
)
from .schemas import load_and_validate
from .secret_redaction import redact_secrets


# ---- API adapter dispatch (Loop 022S) -----------------------------

#: Names of non-command adapters the pool skeleton can now drive.
API_ADAPTERS = frozenset(
    {
        "openai_compatible_api",
        "openai_api",
        "anthropic_api",
    }
)


def _detect_quota_or_timeout(
    *,
    runtime_status: str,
    failure_summary: str,
) -> str:
    """Refine an API runtime_status into
    AGENT_QUOTA_LIMIT / AGENT_TIMEOUT when the upstream error text
    matches quota / "try again at" / "usage limit" / "rate limit"
    keywords.

    The classification precedence matches the existing
    ``_runtime_status_from_result`` policy in
    ``loop_engine/agent_runtime`` — quota keywords win over
    generic timeout, so the chain's retryable behaviour is
    consistent.
    """
    text = (failure_summary or "").lower()
    if any(
        marker in text
        for marker in (
            "usage limit",
            "rate limit",
            "ratelimit",
            "quota",
            "try again at",
            "429",
            "insufficient_quota",
        )
    ):
        return "AGENT_QUOTA_LIMIT"
    if "timeout" in text or "timed out" in text or "504" in text or "408" in text:
        return "AGENT_TIMEOUT"
    return runtime_status


def _exit_code_for_api(api_result: Any) -> Any:
    """Return the upstream HTTP status code from a
    ReviewerProviderResult, or ``None``.

    ``ReviewerProviderResult`` does not carry an ``exit_code``
    field directly; the API adapter records it on the
    ``ProviderAttempt.exit_code`` instead. Pool-level bookkeeping
    needs the HTTP status as a single scalar for
    ``invocation_summary.json`` and ``exit_code.txt``.
    """
    if api_result is None:
        return None
    attempts = list(getattr(api_result, "provider_attempts", []) or [])
    if not attempts:
        return None
    return getattr(attempts[-1], "exit_code", None)


def _run_api_provider(
    *,
    request: AgentInvocationRequest,
    provider_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Run an API adapter (openai_compatible / openai / anthropic).

    Returns a dict shaped like ``_run_command_provider``:

    - ``stdout``, ``stderr`` (empty; API path uses request.output_path)
    - ``exit_code`` (int | None)
    - ``runtime_status``
    - ``timeout_expired``
    - ``output_exists`` (True iff an ``api_attempt.json`` was written)
    - ``schema_valid`` (True iff the resulting review JSON is
      schema-valid)
    - ``readonly``
    - ``evidence_dir``
    - ``output_path``
    - ``api_result`` (the underlying ``ReviewerProviderResult``,
      used by the pool's run_pool for further downstream
      translation)
    """
    from . import api_review_provider

    evidence_dir = request.stage_dir / ".loop" / "agent_invocations" / request.agent_name
    evidence_dir.mkdir(parents=True, exist_ok=True)
    before = hash_protected_files(request.protected_paths or [])

    adapter = str(provider_cfg.get("adapter", ""))
    api_key, _src = _resolve_api_key(provider_cfg)
    base_url, _bsrc = (
        _resolve_base_url(provider_cfg) if adapter == "openai_compatible_api" else (None, "absent")
    )
    model, _msrc = _resolve_model(provider_cfg)

    # Wire the prompt + manifest, like _run_command_provider.
    write_text(evidence_dir / "prompt.md", redact_secrets(read_text(request.prompt_path)))
    write_json(
        evidence_dir / "input_manifest.json",
        {
            "agent_name": request.agent_name,
            "prompt_path": str(request.prompt_path),
            "output_path": str(request.output_path),
            "schema_name": request.schema_name,
            "protected_paths": [str(path) for path in (request.protected_paths or [])],
            "timestamp": utc_now(),
            "pool_provider": provider_cfg.get("name"),
            "pool_adapter": adapter,
            "api_provider": True,
        },
    )
    write_text(
        evidence_dir / "command.txt",
        redact_secrets(f"POOL API adapter={adapter} role={request.agent_name}\n"),
    )

    api_result = None
    runtime_status = "AGENT_RUNTIME_FAILURE"
    failure_summary = ""
    try:
        if adapter == "openai_compatible_api":
            if not api_key:
                api_result = api_review_provider._build_api_missing_key_result(
                    reviewer_role=request.agent_name,
                    provider_name=str(provider_cfg.get("name", "openai_compatible_api")),
                    runtime_status="AGENT_RUNTIME_FAILURE",
                    failure_summary="OPENAI_COMPATIBLE_API_KEY env var not set",
                )
            elif not base_url:
                api_result = api_review_provider._build_api_missing_key_result(
                    reviewer_role=request.agent_name,
                    provider_name=str(provider_cfg.get("name", "openai_compatible_api")),
                    runtime_status="AGENT_RUNTIME_FAILURE",
                    failure_summary="OPENAI_COMPATIBLE_BASE_URL env var not set",
                )
            else:
                api_result = api_review_provider.invoke_openai_compatible_api(
                    request=request,
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                )
        elif adapter == "openai_api":
            if not api_key:
                api_result = api_review_provider._build_api_missing_key_result(
                    reviewer_role=request.agent_name,
                    provider_name=str(provider_cfg.get("name", "openai_api")),
                    runtime_status="AGENT_RUNTIME_FAILURE",
                    failure_summary="OPENAI_API_KEY env var not set",
                )
            else:
                api_result = api_review_provider.invoke_openai_api(
                    request=request,
                    api_key=api_key,
                    model=model,
                )
        elif adapter == "anthropic_api":
            if not api_key:
                api_result = api_review_provider._build_api_missing_key_result(
                    reviewer_role=request.agent_name,
                    provider_name=str(provider_cfg.get("name", "anthropic_api")),
                    runtime_status="AGENT_RUNTIME_FAILURE",
                    failure_summary="ANTHROPIC_API_KEY env var not set",
                )
            else:
                api_result = api_review_provider.invoke_anthropic_api(
                    request=request,
                    api_key=api_key,
                    model=model,
                )
        else:
            # Not a recognised API adapter. Should not happen —
            # run_pool only routes here for known API adapter names.
            api_result = None
    except Exception as exc:  # pragma: no cover — defensive
        failure_summary = f"uncaught: {exc!r}"
        runtime_status = "AGENT_RUNTIME_FAILURE"

    if api_result is None:
        return {
            "stdout": "",
            "stderr": failure_summary or "no api adapter matched",
            "exit_code": None,
            "runtime_status": runtime_status,
            "timeout_expired": False,
            "output_exists": False,
            "schema_valid": False,
            "readonly": verify_read_only_contract(before),
            "evidence_dir": evidence_dir,
            "output_path": request.output_path,
            "api_result": None,
        }

    # Refine the runtime_status using the upstream text.
    last_attempt_summary = ""
    if api_result.provider_attempts:
        last_attempt_summary = (
            api_result.provider_attempts[-1].failure_summary_redacted or ""
        )
    refined_status = _detect_quota_or_timeout(
        runtime_status=api_result.runtime_status or "AGENT_RUNTIME_FAILURE",
        failure_summary=last_attempt_summary,
    )
    if refined_status != api_result.runtime_status:
        # Mutate the last attempt in-place so it's clear.
        api_result.provider_attempts[-1].runtime_status = refined_status
        api_result.runtime_status = refined_status

    # Write stdout/stderr (the API adapter's stderr/stdout are
    # empty; we capture the api_attempt.json's summary for audit
    # traceability, with redaction).
    write_text(evidence_dir / "stdout.txt", redact_secrets(""))
    api_attempt_path = evidence_dir / "api_attempt.json"
    if api_attempt_path.exists():
        write_text(evidence_dir / "stderr.txt", redact_secrets(""))
    else:
        write_text(evidence_dir / "stderr.txt", redact_secrets(""))
    write_text(
        evidence_dir / "exit_code.txt",
        f"{_exit_code_for_api(api_result)}\n",
    )

    output_hash = file_sha256(request.output_path) if request.output_path.exists() else ""
    write_text(evidence_dir / "output_hash.txt", f"{output_hash}\n")

    readonly = verify_read_only_contract(before)
    return {
        "stdout": "",
        "stderr": "",
        "exit_code": _exit_code_for_api(api_result),
        "runtime_status": api_result.runtime_status or "AGENT_RUNTIME_FAILURE",
        "timeout_expired": False,
        "output_exists": request.output_path.exists(),
        "schema_valid": bool(api_result.schema_valid),
        "readonly": readonly,
        "evidence_dir": evidence_dir,
        "output_path": request.output_path,
        "api_result": api_result,
    }


# ---- availability / fallback policy -------------------------------

def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    if isinstance(value, str):
        stripped = value.strip().lower()
        if not stripped:
            return default
        return stripped in {"1", "true", "yes", "on"}
    return bool(value)


def _resolve_api_key(provider_cfg: dict[str, Any]) -> tuple[str | None, str]:
    """Read API key from explicit ``api_key`` or env var.

    Returns ``(value, source)``. ``source`` is ``"env:<name>"``
    when the env var was used, ``"explicit"`` when the value was
    in the YAML, or ``"absent"`` when no key was available.
    """
    explicit = provider_cfg.get("api_key")
    if isinstance(explicit, str) and explicit:
        return explicit, "explicit"
    env_name = provider_cfg.get("api_key_env")
    if isinstance(env_name, str) and env_name:
        value = os.environ.get(env_name)
        if value:
            return value, f"env:{env_name}"
    return None, "absent"


def _resolve_base_url(provider_cfg: dict[str, Any]) -> tuple[str | None, str]:
    explicit = provider_cfg.get("base_url")
    if isinstance(explicit, str) and explicit:
        return explicit, "explicit"
    env_name = provider_cfg.get("base_url_env")
    if isinstance(env_name, str) and env_name:
        value = os.environ.get(env_name)
        if value:
            return value, f"env:{env_name}"
    return None, "absent"


def _resolve_model(provider_cfg: dict[str, Any]) -> tuple[str | None, str]:
    explicit = provider_cfg.get("model")
    if isinstance(explicit, str) and explicit:
        return explicit, "explicit"
    env_name = provider_cfg.get("model_env")
    if isinstance(env_name, str) and env_name:
        value = os.environ.get(env_name)
        if value:
            return value, f"env:{env_name}"
    return None, "absent"


def _is_provider_enabled(provider_cfg: dict[str, Any]) -> tuple[bool, str]:
    """Compute the (enabled, reason) tuple for one provider_cfg."""
    enabled_field = provider_cfg.get("enabled")
    if isinstance(enabled_field, bool):
        return enabled_field, "explicit_bool"
    env_name = provider_cfg.get("enabled_env")
    if isinstance(env_name, str) and env_name:
        value = os.environ.get(env_name)
        if value:
            return _coerce_bool(value, True), f"env:{env_name}"
        return False, f"missing_env:{env_name}"
    return _coerce_bool(enabled_field, True), "default"


def _availability_command_adapter(provider_cfg: dict[str, Any]) -> tuple[bool, str]:
    cmd = provider_cfg.get("command")
    if not isinstance(cmd, list) or not cmd:
        return False, "OTHER"
    # First entry is the executable. Use shutil.which to check PATH;
    # for resolved absolute paths, just check existence + executable.
    exe = cmd[0]
    found = shutil.which(exe) if not os.path.isabs(exe) else (
        exe if os.path.isfile(exe) and os.access(exe, os.X_OK) else None
    )
    return (found is not None), ("MISSING_BINARY" if not found else "AVAILABLE")


def _availability_api_adapter(
    provider_cfg: dict[str, Any], *, key_name: str
) -> tuple[bool, str]:
    key, _source = _resolve_api_key(provider_cfg)
    if not key:
        return False, "MISSING_ENV"
    return True, "AVAILABLE"


def _check_provider_availability(
    provider_cfg: dict[str, Any]
) -> tuple[str, str]:
    """Return ``(availability_status, runtime_status)`` for a provider."""
    adapter = provider_cfg.get("adapter")
    if not adapter:
        return ("OTHER", "NOT_INVOKED")

    enabled, _why = _is_provider_enabled(provider_cfg)
    if not enabled:
        return ("DISABLED_BY_ENV", "NOT_INVOKED")

    def _normalise(adapter_result: tuple[Any, str] | tuple[str, str]) -> tuple[str, str]:
        # Helper: coerce the first element to a string status.
        status, runtime = adapter_result
        if not isinstance(status, str):
            status = "AVAILABLE" if status else "MISSING_ENV"
        return (status, runtime)

    if adapter in {"command", "codex_subagent", "claude_code_cli"}:
        return _normalise(_availability_command_adapter(provider_cfg))
    if adapter == "anthropic_api":
        return _normalise(_availability_api_adapter(provider_cfg, key_name="ANTHROPIC_API_KEY"))
    if adapter == "openai_api":
        return _normalise(_availability_api_adapter(provider_cfg, key_name="OPENAI_API_KEY"))
    if adapter == "openai_compatible_api":
        return _normalise(
            _availability_api_adapter(provider_cfg, key_name="OPENAI_COMPATIBLE_API_KEY")
        )
    if adapter == "stub":
        return ("AVAILABLE", "STUB_NOT_PRODUCTION")
    if adapter == "manual":
        return ("AVAILABLE", "OTHER")
    return ("OTHER", "NOT_INVOKED")


def _classify_runtime_from_command(
    *,
    command_list: list[str],
    cwd: Path,
    timeout_seconds: int,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a command adapter via subprocess and return a classification dict.

    Always returns a dict, never raises on timeout / not-found.
    """
    timeout_expired = False
    try:
        completed = subprocess.run(
            command_list,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            env=env if env is not None else None,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code: int | str | None = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timeout_expired = True
        stdout = (exc.stdout or "")
        stderr = (exc.stderr or "")
        for attr, target in (("stdout", "stdout"), ("stderr", "stderr")):
            value = getattr(exc, attr, "")
            if isinstance(value, bytes):
                value = value.decode("utf-8", errors="replace")
            if target == "stdout":
                stdout = value
            else:
                stderr = value
        stderr = f"{stderr}\nCommand timed out after {timeout_seconds} seconds.\n"
        exit_code = None
    except FileNotFoundError as exc:
        # Missing executable in cmd[0]. Classify as command-not-found.
        return {
            "stdout": "",
            "stderr": f"FileNotFoundError: {exc}\n",
            "exit_code": 127,
            "runtime_status": "AGENT_COMMAND_NOT_FOUND",
            "timeout_expired": False,
            "output_exists": False,
            "schema_valid": False,
        }

    runtime_status = _runtime_status_from_result(
        exit_code=exit_code,
        timeout_expired=timeout_expired,
        output_exists=True,  # measured below by file presence; placeholder
        schema_valid=False,  # measured below; computed at pool level
        stdout=stdout,
        stderr=stderr,
    )
    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "runtime_status": runtime_status,
        "timeout_expired": timeout_expired,
        "output_exists": True,
        "schema_valid": False,
    }


def _run_command_provider(
    *,
    request: AgentInvocationRequest,
    provider_cfg: dict[str, Any],
    command_template: list[str],
    cwd: Path,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    """Run a single command provider. Returns a classification dict
    that includes the standard invocation summary fields plus the
    provider's runtime_status string.
    """
    evidence_dir = request.stage_dir / ".loop" / "agent_invocations" / request.agent_name
    evidence_dir.mkdir(parents=True, exist_ok=True)
    protected_paths = request.protected_paths or []
    before = hash_protected_files(protected_paths)
    output_existed_before = request.output_path.exists()
    output_hash_before = file_sha256(request.output_path) if output_existed_before else ""
    output_mtime_before = request.output_path.stat().st_mtime_ns if output_existed_before else None

    # Write prompt + manifest, similar to CommandAgentAdapter.
    write_text(evidence_dir / "prompt.md", read_text(request.prompt_path))
    write_json(
        evidence_dir / "input_manifest.json",
        {
            "agent_name": request.agent_name,
            "prompt_path": str(request.prompt_path),
            "output_path": str(request.output_path),
            "schema_name": request.schema_name,
            "protected_paths": [str(path) for path in protected_paths],
            "timestamp": utc_now(),
            "pool_provider": provider_cfg.get("name"),
            "pool_adapter": provider_cfg.get("adapter"),
        },
    )
    write_text(
        evidence_dir / "command.txt",
        redact_secrets(" ".join(command_template) + "\n"),
    )

    runtime = _classify_runtime_from_command(
        command_list=command_template,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
    )

    stdout_text = runtime["stdout"]
    stderr_text = runtime["stderr"]
    write_text(evidence_dir / "stdout.txt", redact_secrets(stdout_text))
    write_text(evidence_dir / "stderr.txt", redact_secrets(stderr_text))
    write_text(
        evidence_dir / "exit_code.txt",
        f"{'TIMEOUT' if runtime['timeout_expired'] else runtime['exit_code']}\n",
    )

    output_hash = file_sha256(request.output_path) if request.output_path.exists() else ""
    write_text(evidence_dir / "output_hash.txt", f"{output_hash}\n")
    output_exists = request.output_path.exists()
    output_mtime_after = request.output_path.stat().st_mtime_ns if output_exists else None
    output_fresh = output_exists and (
        not output_existed_before
        or output_hash != output_hash_before
        or output_mtime_after != output_mtime_before
    )
    schema_valid = False
    if output_fresh:
        try:
            load_and_validate(request.output_path, request.schema_name)
            schema_valid = True
        except Exception:
            schema_valid = False

    readonly = verify_read_only_contract(before)
    runtime_status = _runtime_status_from_result(
        exit_code=runtime["exit_code"],
        timeout_expired=runtime["timeout_expired"],
        output_exists=output_exists,
        schema_valid=schema_valid,
        stdout=stdout_text,
        stderr=stderr_text,
    )
    return {
        "stdout": stdout_text,
        "stderr": stderr_text,
        "exit_code": runtime["exit_code"],
        "timeout_expired": runtime["timeout_expired"],
        "runtime_status": runtime_status,
        "output_exists": output_exists,
        "output_fresh": output_fresh,
        "schema_valid": schema_valid,
        "readonly": readonly,
        "evidence_dir": evidence_dir,
        "output_path": request.output_path,
    }


def _build_command_for_provider(
    provider_cfg: dict[str, Any],
    *,
    fallback_request: AgentInvocationRequest | None = None,
) -> list[str] | None:
    """Return the merged CLI command list for ``adapter: command``.

    If the provider has ``command`` set, expand any ``{prompt_path}``
    / ``{output_path}`` / ``{stage_dir}`` / ``{agent_name}`` tokens
    using the fallback request.
    """
    cmd = provider_cfg.get("command")
    if not isinstance(cmd, list) or not cmd:
        return None
    rendered: list[str] = []
    replacements: dict[str, str] = {}
    if fallback_request is not None:
        replacements = {
            "{agent_name}": fallback_request.agent_name,
            "{prompt_path}": str(fallback_request.prompt_path),
            "{output_path}": str(fallback_request.output_path),
            "{stage_dir}": str(fallback_request.stage_dir),
        }
    for token in cmd:
        if not isinstance(token, str):
            rendered.append(str(token))
            continue
        if fallback_request is None:
            rendered.append(token)
            continue
        value = token
        for marker, replacement in replacements.items():
            value = value.replace(marker, replacement)
        rendered.append(value)
    return rendered


def run_pool(
    *,
    pool_cfg: dict[str, Any],
    request: AgentInvocationRequest,
) -> ReviewerProviderResult:
    """Run a reviewer role through the configured provider pool.

    The pool is a list of provider configs. The pool's
    ``fallback_policy`` defaults to ``runtime_failure_only`` which
    is exactly the Loop 021 hard rule: only retryable runtime
    failures fall through to the next provider.

    Pool-wide behaviour:

    - ``forbid_stub`` (default True) makes the pool refuse any
      stub provider, even if the profile permits stub in tests.
      This is the Loop 021 production safety contract.
    - ``require_real_provider`` (default True) makes the pool
      fail with ``AGENT_ALL_PROVIDERS_UNAVAILABLE`` rather than
      silently choosing a stub.
    - ``secret_redaction_applied`` is always True; the redactor
      is non-negotiable.

    The returned ``ReviewerProviderResult`` instance exposes
    ``review_debt_required`` so the runner can persist the
    ``PROVISIONAL_FREEZE_WITH_REVIEW_DEBT`` semantics unchanged.
    """
    forbid_stub = _coerce_bool(pool_cfg.get("forbid_stub"), True)
    require_real = _coerce_bool(pool_cfg.get("require_real_provider"), True)
    fallback_policy = pool_cfg.get("fallback_policy", "runtime_failure_only")
    providers = pool_cfg.get("providers", []) or []

    result = ReviewerProviderResult(
        reviewer_role=request.agent_name,
        selected_provider=None,
        secret_redaction_applied=True,
        retryable=False,
        stub_used=False,
        runtime_status="NOT_INVOKED",
    )

    # 1. Probe all providers. Disabled / unavailable providers are
    # recorded as attempts but skipped.
    candidates: list[dict[str, Any]] = []
    for provider_cfg in providers:
        if provider_cfg.get("adapter") == "stub" and forbid_stub:
            att = ProviderAttempt(
                provider_name=str(provider_cfg.get("name", "stub")),
                adapter="stub",
                enabled=False,
                selected=False,
                retryable=False,
                availability_status="DISABLED_BY_ENV",
                runtime_status="STUB_NOT_PRODUCTION",
                failure_summary_redacted="stub forbidden in production",
            )
            result.provider_attempts.append(att)
            continue
        availability, runtime = _check_provider_availability(provider_cfg)
        enabled, _why = _is_provider_enabled(provider_cfg)
        # If availability_check is "MISSING_ENV" / "MISSING_BINARY" /
        # "OTHER" - record and skip
        if availability != "AVAILABLE" or not enabled:
            att = ProviderAttempt(
                provider_name=str(provider_cfg.get("name", "?")),
                adapter=str(provider_cfg.get("adapter", "?")),
                enabled=enabled,
                selected=False,
                retryable=False,
                availability_status=availability,
                runtime_status=runtime if runtime != "NOT_INVOKED" else "AGENT_RUNTIME_FAILURE",
                failure_summary_redacted=f"availability={availability}",
            )
            result.provider_attempts.append(att)
            continue
        candidates.append(provider_cfg)

    # 2. Walk candidates in declared order. Stop on first
    # schema-valid result. Fall through on retryable runtime
    # failure only.
    if not candidates and require_real:
        result.runtime_status = "AGENT_ALL_PROVIDERS_UNAVAILABLE"
        result.retryable = True
        result.review_debt_required = True
        result.fallback_reason = "no enabled and available providers"
        return result

    for idx, provider_cfg in enumerate(candidates):
        adapter_name = str(provider_cfg.get("adapter", "?"))
        # Dispatch path (Loop 022S):
        # - command-family adapters -> _run_command_provider
        # - API adapters              -> _run_api_provider
        # - other                    -> AGENT_RUNTIME_FAILURE
        if adapter_name in {"command", "codex_subagent", "claude_code_cli"}:
            cmd = _build_command_for_provider(provider_cfg, fallback_request=request)
            if cmd is None:
                attempt_meta = ProviderAttempt(
                    provider_name=str(provider_cfg.get("name", "?")),
                    adapter=adapter_name,
                    enabled=True,
                    selected=False,
                    retryable=False,
                    availability_status="AVAILABLE",
                    runtime_status="AGENT_RUNTIME_FAILURE",
                    exit_code=None,
                    failure_summary_redacted=(
                        "command adapter requires a 'command' list"
                    ),
                )
                result.provider_attempts.append(attempt_meta)
                result.fallback_reason = attempt_meta.runtime_status
                continue
            attempt = _run_command_provider(
                request=request,
                provider_cfg=provider_cfg,
                command_template=cmd,
                cwd=request.stage_dir,
            )
        elif adapter_name in API_ADAPTERS:
            attempt = _run_api_provider(
                request=request,
                provider_cfg=provider_cfg,
            )
        else:
            # Unknown adapter type -- record + continue. Non-retryable.
            attempt_meta = ProviderAttempt(
                provider_name=str(provider_cfg.get("name", "?")),
                adapter=adapter_name,
                enabled=True,
                selected=False,
                retryable=False,
                availability_status="AVAILABLE",
                runtime_status="AGENT_RUNTIME_FAILURE",
                exit_code=None,
                failure_summary_redacted=(
                    f"unsupported adapter type: {adapter_name!r}"
                ),
            )
            result.provider_attempts.append(attempt_meta)
            result.fallback_reason = attempt_meta.runtime_status
            continue

        # Merge the upstream provider_attempts (the API adapter records its own
        # ProviderAttempt via ReviewerProviderResult.provider_attempts). For
        # command adapters this is a no-op (empty list).
        if attempt.get("api_result") is not None:
            api_provider_attempts = list(
                getattr(attempt["api_result"], "provider_attempts", []) or []
            )
            for pa in api_provider_attempts:
                if (
                    "env var not set"
                    in (pa.failure_summary_redacted or "").lower()
                ):
                    # Missing key is a configuration failure, not a runtime
                    # failure -- do NOT retry past it.
                    pa.retryable = False
                result.provider_attempts.append(pa)

        attempt_meta = ProviderAttempt(
            provider_name=str(provider_cfg.get("name", "?")),
            adapter=adapter_name,
            enabled=True,
            selected=True,
            retryable=is_retryable(attempt["runtime_status"]),
            availability_status="AVAILABLE",
            runtime_status=attempt["runtime_status"],
            exit_code=attempt["exit_code"],
            failure_summary_redacted=redact_secrets(
                (attempt.get("stderr") or "")[-200:]
            ),
        )
        result.provider_attempts.append(attempt_meta)
        result.runtime_status = attempt["runtime_status"]
        result.exit_code = attempt["exit_code"]
        result.adapter = adapter_name
        result.actually_invoked = True

        # Continue / stop?
        if not should_continue_to_next_provider(
            runtime_status=attempt["runtime_status"],
            schema_valid=attempt["schema_valid"],
        ):
            # Stop the chain. Set the selected_provider only if schema-valid;
            # otherwise honour the running semantics.
            if attempt["schema_valid"]:
                result.selected_provider = str(provider_cfg.get("name", "?"))
                if attempt.get("api_result") is not None:
                    result.verdict = (
                        getattr(attempt["api_result"], "verdict", None)
                        or _extract_verdict(request)
                    )
                    result.review_debt_required = (
                            (result.verdict in {"FAIL", "FAILED", "NEEDS_PATCH", "BLOCKED"})
                        if result.verdict is not None
                        else True
                    )
                else:
                    result.verdict = _extract_verdict(request)
                    result.review_debt_required = _requires_review_debt(result)
                result.freeze_evidence_valid = (
                    attempt["exit_code"] in (0, None)
                    and attempt["schema_valid"]
                    and not attempt["readonly"]["ReviewerModifiedProtectedFiles"]
                )
                result.schema_valid = True
                _write_invocation_summary(attempt, result)
                return result
            # Non-retryable non-schema: stop immediately.
            result.fallback_reason = (
                f"non-retryable: {attempt['runtime_status']}"
            )
            result.review_debt_required = True
            _write_invocation_summary(attempt, result)
            return result

        # Otherwise, fall through to the next provider.
        result.fallback_reason = attempt["runtime_status"]

    # Loop exhausted without a successful schema-valid attempt.
    if not candidates:
        # Defensive: this case is handled by the early return above
        # when require_real is True. Kept here for clarity if a future
        # caller relaxes that flag.
        result.fallback_reason = "no enabled providers"
    else:
        result.fallback_reason = result.fallback_reason or "all providers retryable-failed"
    result.retryable = True
    result.runtime_status = "AGENT_ALL_PROVIDERS_UNAVAILABLE"
    result.review_debt_required = True
    return result


def _extract_verdict(request: AgentInvocationRequest) -> str | None:
    if not request.output_path.exists():
        return None
    try:
        payload = json.loads(request.output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    verdict = payload.get("verdict")
    if not isinstance(verdict, str):
        return None
    return verdict


def _requires_review_debt(result: ReviewerProviderResult) -> bool:
    """Mirror the Loop 014–017 convention: schema-valid semantic
    failure or schema-valid pass still requires human signoff if
    the human decides that. We do not invent debt here; the
    boolean here reflects ONLY whether a schema-valid verdict
    was produced.
    """
    verdict = result.verdict
    if verdict is None:
        return True
    return verdict in {"FAIL", "FAILED", "NEEDS_PATCH", "BLOCKED"}


def _write_invocation_summary(
    attempt: dict[str, Any], result: ReviewerProviderResult
) -> None:
    """Write ``invocation_summary.json`` in the existing format.

    This is an additive sibling to ``pool_result.json``. The
    runner's existing callers (which read
    ``invocation_summary.json``) keep working unchanged.
    """
    summary = {
        "agent_name": result.reviewer_role,
        "adapter": result.adapter,
        "actually_invoked": result.actually_invoked,
        "stub_used": False,
        "exit_code": attempt["exit_code"],
        "timeout_expired": attempt["timeout_expired"],
        "schema_valid": result.schema_valid,
        "review_debt_required": result.review_debt_required,
        "read_only_contract_enforced": not attempt["readonly"]["ReviewerModifiedProtectedFiles"],
        "ReviewerModifiedProtectedFiles": attempt["readonly"]["ReviewerModifiedProtectedFiles"],
        "modified_protected_files": attempt["readonly"]["ModifiedProtectedFiles"],
        "output_hash": file_sha256(attempt["output_path"]) if attempt["output_path"].exists() else "",
        "freeze_evidence_valid": result.freeze_evidence_valid,
        "runtime_status": attempt["runtime_status"],
        "selected_provider": result.selected_provider,
        "provider_attempts": [a.to_dict() for a in result.provider_attempts],
        "pool_retryable": result.retryable,
        "fallback_reason": result.fallback_reason,
    }
    write_invocation_summary(attempt["evidence_dir"], summary)
    write_json(
        attempt["evidence_dir"] / "pool_result.json", result.to_dict()
    )


# A simple function form so callers (the runner) can pass an
# agent invocation request and get back either a pool result or
# a "legacy single-provider invocation" when no pool is
# configured. Tests build on this.

def invoke_reviewer(
    *,
    pool_cfg: dict[str, Any] | None,
    request: AgentInvocationRequest,
    fallback_command: list[str] | None = None,
    fallback_adapter_name: str = "command",
) -> ReviewerProviderResult:
    if pool_cfg is None:
        # Legacy single-provider invocation. The pool emits
        # result-shaped metadata so callers do not need to branch
        # on the presence of a pool config.
        if fallback_command is None:
            raise ValueError(
                "fallback_command is required when no provider pool is configured"
            )
        result = ReviewerProviderResult(
            reviewer_role=request.agent_name,
            selected_provider="legacy",
            adapter=fallback_adapter_name,
            actually_invoked=True,
            stub_used=False,
            secret_redaction_applied=True,
            retryable=False,
            runtime_status="NOT_INVOKED",
        )
        attempt = _run_command_provider(
            request=request,
            provider_cfg={"name": "legacy", "adapter": fallback_adapter_name},
            command_template=fallback_command,
            cwd=request.stage_dir,
        )
        result.runtime_status = attempt["runtime_status"]
        result.exit_code = attempt["exit_code"]
        # Reuse existing CommandAgentAdapter's classification for
        # ``schema_valid`` and ``runtime_status`` mapping so legacy
        # semantics are preserved exactly.
        if attempt["output_exists"]:
            from .agent_runtime import _schema_valid as _rsv
            attempt["schema_valid"] = _rsv(attempt["output_path"], request.schema_name)
        result.schema_valid = attempt["schema_valid"]
        if attempt["schema_valid"]:
            result.verdict = _extract_verdict(request)
            result.selected_provider = "legacy"
        result.provider_attempts.append(
            ProviderAttempt(
                provider_name="legacy",
                adapter=fallback_adapter_name,
                enabled=True,
                selected=attempt["schema_valid"],
                retryable=is_retryable(attempt["runtime_status"]),
                availability_status="AVAILABLE",
                runtime_status=attempt["runtime_status"],
                exit_code=attempt["exit_code"],
                failure_summary_redacted=redact_secrets(attempt["stderr"][-200:]),
            )
        )
        result.review_debt_required = (
            not attempt["schema_valid"]
            or attempt["runtime_status"]
            in {"AGENT_QUOTA_LIMIT", "AGENT_TIMEOUT", "AGENT_NO_OUTPUT", "AGENT_COMMAND_NOT_FOUND"}
        )
        result.freeze_evidence_valid = (
            attempt["exit_code"] == 0
            and attempt["schema_valid"]
            and not attempt["readonly"]["ReviewerModifiedProtectedFiles"]
        )
        # Persist invocation summary + pool_result so legacy-path
        # callers can also consume pool-shaped metadata.
        _write_invocation_summary(attempt, result)
        return result
    return run_pool(pool_cfg=pool_cfg, request=request)
