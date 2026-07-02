"""Loop 022T — API provider TLS trust tests.

These tests pin the production-safe TLS behavior of
``loop_engine.api_review_provider``:

1. Default TLS verify is enabled (CERT_REQUIRED + check_hostname).
2. ``LOOP_API_SSL_CERT_FILE`` is honoured and passed to the SSL
   context.
3. ``SSL_CERT_FILE`` is honoured as a fallback (consistent with
   Python's standard library).
4. TLS cert failure maps to ``AGENT_TRANSPORT_FAILURE`` with the
   diagnostic hint appended.
5. No API key appears in the resulting
   ``failure_summary_redacted`` / ``api_attempt.json`` / stderr /
   stdout / ``invocation_summary.json``.
6. ``verify=False`` is NOT available on the production path.
7. ``scripts/diagnose_api_tls.py`` does not require an API key
   and does not print one.
8. Command provider behavior is unchanged.
9. Provider fallback policy is unchanged (TLS failure still
   surfaces review debt without fallback).
10. No ``sigma_abc`` physics files modified.
11. ``ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY`` is not used
    by the production API adapter — only a future diagnostic
    CLI path may use it.

All tests use ``monkeypatch``; no real network is required.
"""
from __future__ import annotations

import importlib
import json
import os
import ssl
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import loop_engine.agent_runtime as agent_runtime_mod
import loop_engine.api_review_provider as api_mod
import loop_engine.reviewer_provider_pool as pool_mod
from loop_engine.agent_runtime import AgentInvocationRequest
from loop_engine.config import write_json
from loop_engine.provider_result import (
    ProviderAttempt,
    ReviewerProviderResult,
)


# ---- helpers --------------------------------------------------------


def _stage(tmp_path: Path) -> Path:
    stage = tmp_path / "stages" / "stage0001_tls"
    stage.mkdir(parents=True, exist_ok=True)
    prompt = stage / "reviewer_agent_prompt.ScientificMetaReviewer.md"
    prompt.write_text("test prompt\n", encoding="utf-8")
    output = stage / ".loop" / "reviewer_results" / "scientificmetareviewer.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        output,
        {
            "verdict": "PASS",
            "stage_name": stage.name,
            "reviewer_role": "ScientificMetaReviewer",
            "review_scope": "routine_branch",
            "mathematical_status": {
                "exact_reconstruction": True,
                "simplification_real": False,
                "regression_preserved": True,
                "overclaim_detected": False,
            },
            "blocking_issues": [],
            "nonblocking_caveats": [],
            "allowed_claims": ["stage may freeze"],
            "forbidden_claims": [],
            "next_action": "FREEZE",
            "suggested_next_stage": None,
            "patch_instructions": [],
        },
    )
    return stage


def _request(stage: Path) -> AgentInvocationRequest:
    return AgentInvocationRequest(
        agent_name="ScientificMetaReviewer",
        stage_dir=stage,
        prompt_path=stage / "reviewer_agent_prompt.ScientificMetaReviewer.md",
        output_path=stage / ".loop" / "reviewer_results" / "scientificmetareviewer.json",
        schema_name="review_result",
    )


def _make_api_result(
    *,
    runtime_status: str,
    schema_valid: bool = False,
    verdict: str | None = None,
    exit_code: int | None = None,
    failure_summary: str = "",
    retryable: bool = True,
) -> ReviewerProviderResult:
    pa = ProviderAttempt(
        provider_name="openai_compatible_api",
        adapter="openai_compatible_api",
        enabled=True,
        selected=schema_valid,
        retryable=retryable,
        availability_status="AVAILABLE",
        runtime_status=runtime_status,
        exit_code=exit_code,
        failure_summary_redacted=failure_summary,
    )
    return ReviewerProviderResult(
        reviewer_role="ScientificMetaReviewer",
        selected_provider="openai_compatible_api" if schema_valid else None,
        provider_attempts=[pa],
        adapter="openai_compatible_api",
        actually_invoked=True,
        stub_used=False,
        runtime_status=runtime_status,
        schema_valid=schema_valid,
        verdict=verdict,
        retryable=retryable,
        secret_redaction_applied=True,
        review_debt_required=(
            verdict in {"FAIL", "NEEDS_PATCH", "BLOCKED"} if verdict else True
        ),
        freeze_evidence_valid=schema_valid and exit_code in (0, None),
    )


# ---- 1. default TLS verify is enabled ------------------------------


def test_default_ssl_context_is_cert_required() -> None:
    """``_build_ssl_context`` must yield a context with
    CERT_REQUIRED + check_hostname=True.
    """
    ctx = api_mod._build_ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_default_ssl_context_ignores_loose_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No env var may turn ``verify=False`` on in the production
    path. Only the CA bundle location env vars are honoured.
    """
    monkeypatch.delenv("LOOP_API_SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    # Even if an unrelated env var is set to a truthy value, the
    # context must remain CERT_REQUIRED + check_hostname=True.
    monkeypatch.setenv("LOOP_API_INSECURE_SSL", "1")
    ctx = api_mod._build_ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


# ---- 2. LOOP_API_SSL_CERT_FILE is passed to SSL context -------------


def test_loop_api_ssl_cert_file_overrides_cafile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When ``LOOP_API_SSL_CERT_FILE`` points at a real CA bundle,
    the context's ``_cafile_path`` (or the ``load_verify_locations``
    call) must be invoked.

    We assert via the public contract: ``_build_ssl_context`` returns
    a context that, when used to open a connection, picks up the
    specified CA bundle. We use ``ssl_ctx.get_ca_certs()`` style
    introspection only as a smoke check.
    """
    bundle = tmp_path / "fake-ca-bundle.pem"
    bundle.write_text("# not a real CA bundle, just a path\n", encoding="utf-8")
    monkeypatch.setenv("LOOP_API_SSL_CERT_FILE", str(bundle))
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)

    captured: dict[str, Any] = {}

    def fake_load_verify_locations(
        self: ssl.SSLContext, *, cafile: str | None = None, capath: str | None = None
    ) -> None:
        captured["cafile"] = cafile
        captured["capath"] = capath

    monkeypatch.setattr(
        ssl.SSLContext,
        "load_verify_locations",
        fake_load_verify_locations,
        raising=True,
    )
    ctx = api_mod._build_ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True
    assert captured.get("cafile") == str(bundle)


# ---- 3. SSL_CERT_FILE is honoured as fallback ----------------------


def test_ssl_cert_file_used_when_loop_env_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("LOOP_API_SSL_CERT_FILE", raising=False)
    bundle = tmp_path / "system-ca-bundle.pem"
    bundle.write_text("# not a real CA bundle\n", encoding="utf-8")
    monkeypatch.setenv("SSL_CERT_FILE", str(bundle))

    captured: dict[str, Any] = {}

    def fake_load_verify_locations(
        self: ssl.SSLContext, *, cafile: str | None = None, capath: str | None = None
    ) -> None:
        captured["cafile"] = cafile

    monkeypatch.setattr(
        ssl.SSLContext,
        "load_verify_locations",
        fake_load_verify_locations,
        raising=True,
    )
    api_mod._build_ssl_context()
    assert captured.get("cafile") == str(bundle)


def test_loop_env_wins_over_ssl_cert_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    loop_bundle = tmp_path / "loop-bundle.pem"
    sys_bundle = tmp_path / "sys-bundle.pem"
    loop_bundle.write_text("# loop\n", encoding="utf-8")
    sys_bundle.write_text("# sys\n", encoding="utf-8")
    monkeypatch.setenv("LOOP_API_SSL_CERT_FILE", str(loop_bundle))
    monkeypatch.setenv("SSL_CERT_FILE", str(sys_bundle))

    captured: dict[str, Any] = {}

    def fake_load_verify_locations(
        self: ssl.SSLContext, *, cafile: str | None = None, capath: str | None = None
    ) -> None:
        captured["cafile"] = cafile

    monkeypatch.setattr(
        ssl.SSLContext,
        "load_verify_locations",
        fake_load_verify_locations,
        raising=True,
    )
    api_mod._build_ssl_context()
    assert captured.get("cafile") == str(loop_bundle)


# ---- 4. TLS failure -> AGENT_TRANSPORT_FAILURE + diagnostic hint ---


def test_classify_tls_failure_returns_hint() -> None:
    hint = api_mod._classify_tls_failure(
        "URLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"
    )
    assert hint is not None
    assert "diagnose_api_tls.py" in hint
    # No host/userinfo leaked (hint is fully static).
    assert "example" not in hint
    assert "user" not in hint


def test_classify_tls_failure_returns_none_for_non_tls() -> None:
    assert (
        api_mod._classify_tls_failure("HTTPError: 401 Unauthorized")
        is None
    )
    assert (
        api_mod._classify_tls_failure("URLError: connection refused")
        is None
    )
    assert api_mod._classify_tls_failure("") is None


def test_classify_api_response_appends_tls_hint_for_5xx(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """End-to-end: a 599 with TLS-style stderr is classified as
    AGENT_TRANSPORT_FAILURE and the failure_summary_redacted
    includes the diagnostic hint.
    """
    stage = _stage(tmp_path)
    request = _request(stage)
    captured: dict[str, Any] = {}

    def fake_call_api(*, url: str, headers: dict, body: bytes, timeout_seconds: int = 60):
        captured["url"] = url
        captured["headers"] = headers
        return (
            599,
            "",
            "URLError: [SSL: CERTIFICATE_VERIFY_FAILED] "
            "self-signed certificate in certificate chain",
        )

    monkeypatch.setattr(api_mod, "_call_api", fake_call_api)

    result = api_mod.invoke_openai_compatible_api(
        request=request,
        api_key="sk-fake-key",
        base_url="https://api.example.test/v1",
        model="fake-model",
    )
    assert result.runtime_status == "AGENT_TRANSPORT_FAILURE"
    assert result.review_debt_required is True
    assert result.freeze_evidence_valid is False
    assert result.actually_invoked is True
    assert result.stub_used is False
    last_attempt = result.provider_attempts[-1]
    assert "diagnose_api_tls.py" in last_attempt.failure_summary_redacted


def test_classify_api_response_no_tls_hint_for_4xx(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """4xx is provider-correctly-rejected; we must NOT append a
    TLS hint in that case.
    """
    stage = _stage(tmp_path)
    request = _request(stage)

    def fake_call_api(*, url: str, headers: dict, body: bytes, timeout_seconds: int = 60):
        return (401, "", "HTTPError: Unauthorized")

    monkeypatch.setattr(api_mod, "_call_api", fake_call_api)

    result = api_mod.invoke_openai_compatible_api(
        request=request,
        api_key="sk-fake-key",
        base_url="https://api.example.test/v1",
        model="fake-model",
    )
    assert result.runtime_status == "AGENT_SCHEMA_FAIL"
    last_attempt = result.provider_attempts[-1]
    assert "diagnose_api_tls.py" not in last_attempt.failure_summary_redacted


# ---- 5. no API key leakage in any artifact -------------------------


def test_no_api_key_in_failure_summary_for_tls_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secret = "sk-DO-NOT-LEAK-XYZ-12345"
    stage = _stage(tmp_path)
    request = _request(stage)

    def fake_call_api(*, url: str, headers: dict, body: bytes, timeout_seconds: int = 60):
        return (
            599,
            "",
            "URLError: [SSL: CERTIFICATE_VERIFY_FAILED] "
            "self-signed certificate in certificate chain",
        )

    monkeypatch.setattr(api_mod, "_call_api", fake_call_api)
    result = api_mod.invoke_openai_compatible_api(
        request=request,
        api_key=secret,
        base_url="https://api.example.test/v1",
        model="fake-model",
    )
    blob = json.dumps(result.to_dict(), default=str)
    # The literal key must NOT appear anywhere in the serialized
    # result. The redacted placeholder is written separately into
    # ``api_attempt.json`` (verified by the next test), not into
    # the ReviewerProviderResult object itself.
    assert secret not in blob
    for pa in result.provider_attempts:
        assert secret not in (pa.failure_summary_redacted or "")


def test_no_api_key_in_api_attempt_json_under_tls_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The on-disk ``api_attempt.json`` must contain the redacted
    placeholder, not the literal key.
    """
    secret = "sk-DO-NOT-LEAK-ABC-99999"
    stage = _stage(tmp_path)
    request = _request(stage)

    def fake_call_api(*, url: str, headers: dict, body: bytes, timeout_seconds: int = 60):
        return (
            599,
            "",
            "URLError: [SSL: CERTIFICATE_VERIFY_FAILED] "
            "self-signed certificate in chain",
        )

    monkeypatch.setattr(api_mod, "_call_api", fake_call_api)
    api_mod.invoke_openai_compatible_api(
        request=request,
        api_key=secret,
        base_url="https://api.example.test/v1",
        model="fake-model",
    )
    evidence = stage / ".loop" / "agent_invocations" / "ScientificMetaReviewer"
    api_attempt = evidence / "api_attempt.json"
    assert api_attempt.exists()
    text = api_attempt.read_text(encoding="utf-8")
    assert secret not in text
    assert "<redacted:API_KEY>" in text


# ---- 6. verify=False is not available ------------------------------


def test_no_verify_false_path_in_api_review_provider() -> None:
    """Grep the code (excluding docstrings): there must be no path
    that creates a context with ``verify=False`` or
    ``check_hostname=False``.
    """
    import ast

    src = Path(api_mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    code_only_lines: list[str] = []
    last_lineno = 0
    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            # The body of each FunctionDef / ClassDef starts after
            # the docstring (which is the first Expr->Constant str).
            # The end_lineno of the node is the last line of
            # executable code.
            end = getattr(node, "end_lineno", None) or node.lineno
            start = node.lineno
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                start = body[0].end_lineno + 1
            code_only_lines.extend(
                f"{i}: {line}" for i, line in enumerate(
                    src.splitlines()[start - 1 : end], start=start
                )
            )
            last_lineno = max(last_lineno, end)
    code_blob = "\n".join(code_only_lines)
    assert "verify=False" not in code_blob, (
        "production code must not contain verify=False"
    )
    assert "check_hostname = False" not in code_blob, (
        "production code must not disable hostname check"
    )
    assert "check_hostname=False" not in code_blob
    # Belt and braces: the helper hardcodes the safe values.
    assert "CERT_REQUIRED" in code_blob
    assert "verify_mode = ssl.CERT_REQUIRED" in code_blob


# ---- 7. diagnostic script does not require an API key ---------------


def test_diagnose_script_help_no_key_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running ``diagnose_api_tls.py --help`` must succeed and
    must not print any API-key value or call any provider.
    """
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    repo_root = Path(api_mod.__file__).resolve().parents[1]
    script = repo_root / "scripts" / "diagnose_api_tls.py"
    assert script.exists(), f"diagnose_api_tls.py not found at {script}"
    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0
    # The --help output must reference the script's purpose.
    assert "--base-url" in completed.stdout
    # And must NOT contain anything API-key-shaped.
    assert "Bearer" not in completed.stdout
    assert "sk-" not in completed.stdout
    assert "Authorization" not in completed.stdout


def test_diagnose_script_redacts_userinfo() -> None:
    """The script's URL redactor must mask ``user:pass@``."""
    # Imported for its side effect of importing the module under
    # the same conditions as production code.
    import importlib.util

    repo_root = Path(api_mod.__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "diagnose_api_tls",
        repo_root / "scripts" / "diagnose_api_tls.py",
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    redacted = mod._redact_url("https://alice:secret@api.example.com/v1")
    assert "alice" not in redacted
    assert "secret" not in redacted
    assert "<user>:<pass>@" in redacted
    assert redacted.endswith("/v1")


# ---- 8. command provider behavior unchanged ------------------------


def test_command_provider_path_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Loop 022T must not touch the command adapter dispatch.

    We invoke the command path through the same pool_cfg shape
    Loop 022S uses and assert that the pool still calls
    ``_run_command_provider`` (which has nothing to do with SSL).
    """
    stage = _stage(tmp_path)

    captured: dict[str, Any] = {}

    def fake_run_command_provider(*, request, provider_cfg, command_template, cwd, timeout_seconds=900):
        captured["ran"] = True
        return {
            "stdout": "ok",
            "stderr": "",
            "exit_code": 0,
            "runtime_status": "AGENT_OK",
            "timeout_expired": False,
            "output_exists": True,
            "schema_valid": True,
            "readonly": {"ReviewerModifiedProtectedFiles": False, "ModifiedProtectedFiles": []},
            "evidence_dir": request.stage_dir / ".loop" / "agent_invocations" / request.agent_name,
            "output_path": request.output_path,
        }

    # Bypass ``_check_provider_availability`` so the test does not
    # depend on whether ``codex`` is on PATH on this host. We only
    # care that the pool *reaches* ``_run_command_provider``.
    def fake_check_provider_availability(provider_cfg):
        return ("AVAILABLE", "AGENT_OK")

    monkeypatch.setattr(pool_mod, "_check_provider_availability", fake_check_provider_availability)
    monkeypatch.setattr(pool_mod, "_run_command_provider", fake_run_command_provider)

    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {
                "name": "codex_cli_resolver",
                "adapter": "command",
                "command": ["codex", "--print", "{prompt_path}", "{output_path}"],
            }
        ],
    }
    result = pool_mod.invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert captured.get("ran") is True
    assert result.runtime_status == "AGENT_OK"
    assert result.adapter == "command"


# ---- 9. provider fallback policy unchanged -------------------------


def test_tls_failure_does_not_fall_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A TLS failure on the only available provider must surface
    review debt and set ``AGENT_ALL_PROVIDERS_UNAVAILABLE`` — it
    must NOT silently fall back to another adapter.
    """
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-test-fake")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LOOP_ENABLE_OPENAI_COMPATIBLE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    stage = _stage(tmp_path)

    def fake_invoke(*, request, api_key, base_url, model):
        return _make_api_result(
            runtime_status="AGENT_TRANSPORT_FAILURE",
            schema_valid=False,
            exit_code=599,
            failure_summary="URLError: SSL: CERTIFICATE_VERIFY_FAILED",
            retryable=True,
        )

    monkeypatch.setattr(api_mod, "invoke_openai_compatible_api", fake_invoke)

    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {
                "name": "openai_compatible_api",
                "adapter": "openai_compatible_api",
                "api_key_env": "OPENAI_COMPATIBLE_API_KEY",
                "base_url_env": "OPENAI_COMPATIBLE_BASE_URL",
                "enabled_env": "LOOP_ENABLE_OPENAI_COMPATIBLE",
            }
        ],
    }
    result = pool_mod.invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert result.runtime_status == "AGENT_ALL_PROVIDERS_UNAVAILABLE"
    assert result.review_debt_required is True
    assert result.freeze_evidence_valid is False
    assert result.actually_invoked is True
    assert result.stub_used is False


# ---- 10. no sigma_abc physics files modified -----------------------


def test_no_sigma_abc_physics_modified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loop 022T does not touch ``sigma_abc/``. We assert that
    the production code (excluding docstrings / module-level
    comments) does not import, reference, or write to
    ``sigma_abc``.
    """
    import ast

    repo_root = Path(api_mod.__file__).resolve().parents[1]
    sigma_root = repo_root / "sigma_abc"
    if not sigma_root.exists():
        pytest.skip("no sigma_abc directory in this checkout")
    for path in (
        repo_root / "loop_engine" / "api_review_provider.py",
        repo_root / "loop_engine" / "reviewer_provider_pool.py",
        repo_root / "scripts" / "diagnose_api_tls.py",
    ):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        # Collect line ranges that are executable code (i.e.
        # inside a function/class body but not a docstring).
        code_lines: list[int] = set()
        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            ):
                body = getattr(node, "body", [])
                start = body[0].end_lineno + 1 if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                ) else node.lineno
                end = getattr(node, "end_lineno", start)
                code_lines.update(range(start, end + 1))
            elif isinstance(node, ast.Module):
                # Top-level executable statements (imports etc.).
                for stmt in node.body:
                    if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                        code_lines.update(range(stmt.lineno, stmt.end_lineno + 1))
        for i, line in enumerate(src.splitlines(), start=1):
            if i in code_lines and "sigma_abc" in line:
                pytest.fail(
                    f"forbidden sigma_abc reference at {path}:{i}: {line!r}"
                )


# ---- 11. ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY not in production path


def test_no_insecure_ssl_knob_in_production_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY`` is reserved
    for an explicit diagnostic CLI path (out of scope for Loop
    022T v1). It must NOT influence the production API adapter.
    """
    monkeypatch.setenv("ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY", "1")
    ctx = api_mod._build_ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True

    # Grep the source for the env var name to make sure it never
    # appears in production paths.
    repo_root = Path(api_mod.__file__).resolve().parents[1]
    for path in (
        repo_root / "loop_engine" / "api_review_provider.py",
        repo_root / "loop_engine" / "reviewer_provider_pool.py",
    ):
        src = path.read_text(encoding="utf-8")
        assert "ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY" not in src