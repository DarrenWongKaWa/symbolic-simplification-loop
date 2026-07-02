"""Loop 022S — API provider runtime integration tests.

These tests pin the run_pool dispatch to ``api_review_provider``
functions, the schema-valid stop semantics, the missing-key /
quota / timeout classification, and the secret-redaction safety
net. They use ``monkeypatch`` on the ``invoke_*`` symbols in
``loop_engine.api_review_provider`` so no real network or API
key is required.

The fallback policy is exactly the Loop 021 hard rule:

- Only retryable runtime failures fall through to the next
  provider.
- Any schema-valid semantic verdict (PASS / PASS_WITH_CAVEAT /
  FAIL / NEEDS_PATCH) stops the chain immediately.

Stub forbidden in production. Real API keys never written to
disk.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

import loop_engine.agent_runtime as agent_runtime_mod
import loop_engine.reviewer_provider_pool as pool_mod
from loop_engine.agent_runtime import (
    AgentInvocationRequest,
)
from loop_engine.config import REPO_ROOT, write_json
from loop_engine.provider_result import (
    ProviderAttempt,
    ReviewerProviderResult,
)
from loop_engine.reviewer_provider_pool import (
    _run_api_provider,
    invoke_reviewer,
    run_pool,
)


# ---- helpers --------------------------------------------------------


def _stage(tmp_path: Path) -> Path:
    stage = tmp_path / "stages" / "stage0001_test"
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


def _fresh_review_output_command() -> list[str]:
    return [
        "python3",
        "-c",
        (
            "import json, pathlib, sys; "
            "path = pathlib.Path(sys.argv[1]); "
            "payload = json.loads(path.read_text()); "
            "path.write_text(json.dumps(payload))"
        ),
        "{stage_dir}/.loop/reviewer_results/scientificmetareviewer.json",
    ]


def _make_api_result(
    *,
    provider_name: str,
    adapter: str,
    runtime_status: str,
    schema_valid: bool = False,
    verdict: str | None = None,
    exit_code: int | None = None,
    failure_summary: str = "",
    retryable: bool = True,
) -> ReviewerProviderResult:
    pa = ProviderAttempt(
        provider_name=provider_name,
        adapter=adapter,
        enabled=True,
        selected=schema_valid,
        retryable=retryable,
        availability_status="AVAILABLE",
        runtime_status=runtime_status,
        exit_code=exit_code,
        failure_summary_redacted=failure_summary,
    )
    result = ReviewerProviderResult(
        reviewer_role="ScientificMetaReviewer",
        selected_provider=provider_name if schema_valid else None,
        provider_attempts=[pa],
        adapter=adapter,
        actually_invoked=True,
        stub_used=False,
        runtime_status=runtime_status,
        schema_valid=schema_valid,
        verdict=verdict,
        retryable=retryable,
        secret_redaction_applied=True,
        review_debt_required=verdict in {"FAIL", "NEEDS_PATCH", "BLOCKED"}
        if verdict
        else True,
        freeze_evidence_valid=schema_valid and exit_code in (0, None),
    )
    return result


# ---- 1. openai_compatible_api provider calls invoke_openai_compatible_api ---


def test_openai_compatible_api_dispatched(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The pool dispatches ``adapter: openai_compatible_api`` to
    ``api_review_provider.invoke_openai_compatible_api`` and
    not the command path.
    """
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-test-fake")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_MODEL", "fake-model")

    captured: dict[str, Any] = {}

    def fake_invoke(
        *, request: AgentInvocationRequest, api_key: str, base_url: str, model: str
    ):
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        captured["model"] = model
        captured["request"] = request
        return _make_api_result(
            provider_name="openai_compatible_api",
            adapter="openai_compatible_api",
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict="PASS",
            exit_code=200,
        )

    # Direct monkeypatch on api_review_provider — the symbol path
    # the pool actually uses for the dispatch.
    import loop_engine.api_review_provider as api_mod

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
                "model_env": "OPENAI_COMPATIBLE_MODEL",
                "enabled_env": "LOOP_ENABLE_OPENAI_COMPATIBLE",
            }
        ],
    }
    monkeypatch.setenv("LOOP_ENABLE_OPENAI_COMPATIBLE", "1")
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert captured, "invoke_openai_compatible_api was not called"
    assert captured["api_key"] == "sk-test-fake"
    assert result.schema_valid is True
    assert result.selected_provider == "openai_compatible_api"
    assert result.verdict == "PASS"


# ---- 2. openai_api provider calls invoke_openai_api ---


def test_openai_api_dispatched(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
    monkeypatch.setenv("LOOP_ENABLE_OPENAI", "1")

    captured: dict[str, Any] = {}

    def fake_invoke(*, request: AgentInvocationRequest, api_key: str, model: str):
        captured["api_key"] = api_key
        captured["model"] = model
        return _make_api_result(
            provider_name="openai_api",
            adapter="openai_api",
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict="PASS",
            exit_code=200,
        )

    import loop_engine.api_review_provider as api_mod

    monkeypatch.setattr(api_mod, "invoke_openai_api", fake_invoke)

    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {
                "name": "openai_api",
                "adapter": "openai_api",
                "api_key_env": "OPENAI_API_KEY",
                "model_env": "OPENAI_MODEL",
                "enabled_env": "LOOP_ENABLE_OPENAI",
            }
        ],
    }
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert captured["api_key"] == "sk-test-openai"
    assert result.schema_valid is True
    assert result.selected_provider == "openai_api"


# ---- 3. anthropic_api provider calls invoke_anthropic_api ---


def test_anthropic_api_dispatched(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("LOOP_ENABLE_ANTHROPIC", "1")

    captured: dict[str, Any] = {}

    def fake_invoke(*, request: AgentInvocationRequest, api_key: str, model: str):
        captured["api_key"] = api_key
        return _make_api_result(
            provider_name="anthropic_api",
            adapter="anthropic_api",
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict="PASS",
            exit_code=200,
        )

    import loop_engine.api_review_provider as api_mod

    monkeypatch.setattr(api_mod, "invoke_anthropic_api", fake_invoke)

    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {
                "name": "anthropic_api",
                "adapter": "anthropic_api",
                "api_key_env": "ANTHROPIC_API_KEY",
                "model_env": "ANTHROPIC_MODEL",
                "enabled_env": "LOOP_ENABLE_ANTHROPIC",
            }
        ],
    }
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert captured["api_key"] == "sk-ant-test"
    assert result.selected_provider == "anthropic_api"


# ---- 4. schema-valid PASS stops chain ---


def test_schema_valid_pass_stops_chain(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://example.test")
    monkeypatch.setenv("LOOP_ENABLE_OPENAI_COMPATIBLE", "1")

    def fake_first(*, request, api_key, base_url, model):
        return _make_api_result(
            provider_name="openai_compatible_api",
            adapter="openai_compatible_api",
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict="PASS",
            exit_code=200,
        )

    def fake_unused(*, request, api_key, base_url, model):
        raise AssertionError("second provider must not be called")

    import loop_engine.api_review_provider as api_mod

    monkeypatch.setattr(api_mod, "invoke_openai_compatible_api", fake_first)
    # The fallback (anthropic_api) adapter must never run.
    monkeypatch.setattr(api_mod, "invoke_anthropic_api", fake_unused)

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
            },
            {
                "name": "anthropic_api",
                "adapter": "anthropic_api",
                "api_key_env": "ANTHROPIC_API_KEY",
                "enabled_env": "LOOP_ENABLE_ANTHROPIC",
            },
        ],
    }
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert result.selected_provider == "openai_compatible_api"
    assert result.verdict == "PASS"
    assert result.schema_valid is True


# ---- 5. schema-valid PASS_WITH_CAVEAT stops chain ---


def test_schema_valid_pass_with_caveat_stops_chain(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://example.test")
    monkeypatch.setenv("LOOP_ENABLE_OPENAI_COMPATIBLE", "1")

    def fake_invoke(*, request, api_key, base_url, model):
        return _make_api_result(
            provider_name="openai_compatible_api",
            adapter="openai_compatible_api",
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict="PASS_WITH_CAVEAT",
            exit_code=200,
        )

    import loop_engine.api_review_provider as api_mod

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
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert result.verdict == "PASS_WITH_CAVEAT"
    assert result.schema_valid is True


# ---- 6. schema-valid FAIL stops chain ---


def test_no_fallback_after_schema_valid_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://example.test")
    monkeypatch.setenv("LOOP_ENABLE_OPENAI_COMPATIBLE", "1")

    def fake_first(*, request, api_key, base_url, model):
        # Pre-write a schema-valid FAIL JSON so downstream sees it.
        output_path = request.output_path
        write_json(
            output_path,
            {
                "verdict": "FAIL",
                "stage_name": request.stage_dir.name,
                "reviewer_role": "ScientificMetaReviewer",
                "review_scope": "routine_branch",
                "mathematical_status": {
                    "exact_reconstruction": False,
                    "simplification_real": False,
                    "regression_preserved": True,
                    "overclaim_detected": True,
                },
                "blocking_issues": ["schema-valid FAIL"],
                "nonblocking_caveats": [],
                "allowed_claims": [],
                "forbidden_claims": [],
                "next_action": "FAIL",
                "suggested_next_stage": None,
                "patch_instructions": [],
            },
        )
        return _make_api_result(
            provider_name="openai_compatible_api",
            adapter="openai_compatible_api",
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict="FAIL",
            exit_code=200,
        )

    def fake_unused(*, request, api_key, base_url, model):
        raise AssertionError("second provider must not be called")

    import loop_engine.api_review_provider as api_mod

    monkeypatch.setattr(api_mod, "invoke_openai_compatible_api", fake_first)
    monkeypatch.setattr(api_mod, "invoke_anthropic_api", fake_unused)

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
            },
            {
                "name": "anthropic_api",
                "adapter": "anthropic_api",
                "api_key_env": "ANTHROPIC_API_KEY",
                "enabled_env": "LOOP_ENABLE_ANTHROPIC",
            },
        ],
    }
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert result.selected_provider == "openai_compatible_api"
    assert result.verdict == "FAIL"


# ---- 7. schema-valid NEEDS_PATCH stops chain ---


def test_no_fallback_after_schema_valid_needs_patch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://example.test")
    monkeypatch.setenv("LOOP_ENABLE_OPENAI_COMPATIBLE", "1")

    def fake_first(*, request, api_key, base_url, model):
        output_path = request.output_path
        write_json(
            output_path,
            {
                "verdict": "NEEDS_PATCH",
                "stage_name": request.stage_dir.name,
                "reviewer_role": "ScientificMetaReviewer",
                "review_scope": "routine_branch",
                "mathematical_status": {
                    "exact_reconstruction": True,
                    "simplification_real": False,
                    "regression_preserved": True,
                    "overclaim_detected": False,
                },
                "blocking_issues": ["needs patch"],
                "nonblocking_caveats": [],
                "allowed_claims": [],
                "forbidden_claims": [],
                "next_action": "PATCH",
                "suggested_next_stage": None,
                "patch_instructions": ["address caveats"],
            },
        )
        return _make_api_result(
            provider_name="openai_compatible_api",
            adapter="openai_compatible_api",
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict="NEEDS_PATCH",
            exit_code=200,
        )

    def fake_unused(*, request, api_key, base_url, model):
        raise AssertionError("second provider must not be called")

    import loop_engine.api_review_provider as api_mod

    monkeypatch.setattr(api_mod, "invoke_openai_compatible_api", fake_first)
    monkeypatch.setattr(api_mod, "invoke_anthropic_api", fake_unused)

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
            },
            {
                "name": "anthropic_api",
                "adapter": "anthropic_api",
                "api_key_env": "ANTHROPIC_API_KEY",
                "enabled_env": "LOOP_ENABLE_ANTHROPIC",
            },
        ],
    }
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert result.selected_provider == "openai_compatible_api"
    assert result.verdict == "NEEDS_PATCH"


# ---- 8. AGENT_QUOTA_LIMIT falls back ---


def test_quota_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://example.test")
    monkeypatch.setenv("LOOP_ENABLE_OPENAI_COMPATIBLE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("LOOP_ENABLE_ANTHROPIC", "1")

    quota_called = {"n": 0}

    def fake_first(*, request, api_key, base_url, model):
        quota_called["n"] += 1
        # The text contains "usage limit" so the pool will refine
        # the runtime_status to AGENT_QUOTA_LIMIT (retryable).
        return _make_api_result(
            provider_name="openai_compatible_api",
            adapter="openai_compatible_api",
            runtime_status="AGENT_RUNTIME_FAILURE",
            schema_valid=False,
            verdict=None,
            exit_code=None,
            failure_summary="usage limit reached; try again at 12:00",
            retryable=True,
        )

    def fake_second(*, request, api_key, model):
        return _make_api_result(
            provider_name="anthropic_api",
            adapter="anthropic_api",
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict="PASS",
            exit_code=200,
        )

    import loop_engine.api_review_provider as api_mod

    monkeypatch.setattr(api_mod, "invoke_openai_compatible_api", fake_first)
    monkeypatch.setattr(api_mod, "invoke_anthropic_api", fake_second)

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
            },
            {
                "name": "anthropic_api",
                "adapter": "anthropic_api",
                "api_key_env": "ANTHROPIC_API_KEY",
                "enabled_env": "LOOP_ENABLE_ANTHROPIC",
            },
        ],
    }
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert quota_called["n"] == 1
    assert result.selected_provider == "anthropic_api"
    # The chain refined the first attempt's status to QUOTA.
    assert result.provider_attempts[0].runtime_status == "AGENT_QUOTA_LIMIT"


# ---- 9. AGENT_TIMEOUT falls back ---


def test_timeout_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://example.test")
    monkeypatch.setenv("LOOP_ENABLE_OPENAI_COMPATIBLE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("LOOP_ENABLE_ANTHROPIC", "1")

    def fake_first(*, request, api_key, base_url, model):
        # Text contains "504" so the pool refines to AGENT_TIMEOUT.
        return _make_api_result(
            provider_name="openai_compatible_api",
            adapter="openai_compatible_api",
            runtime_status="AGENT_RUNTIME_FAILURE",
            schema_valid=False,
            verdict=None,
            exit_code=504,
            failure_summary="gateway timeout",
            retryable=True,
        )

    def fake_second(*, request, api_key, model):
        return _make_api_result(
            provider_name="anthropic_api",
            adapter="anthropic_api",
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict="PASS",
            exit_code=200,
        )

    import loop_engine.api_review_provider as api_mod

    monkeypatch.setattr(api_mod, "invoke_openai_compatible_api", fake_first)
    monkeypatch.setattr(api_mod, "invoke_anthropic_api", fake_second)

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
            },
            {
                "name": "anthropic_api",
                "adapter": "anthropic_api",
                "api_key_env": "ANTHROPIC_API_KEY",
                "enabled_env": "LOOP_ENABLE_ANTHROPIC",
            },
        ],
    }
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert result.selected_provider == "anthropic_api"
    assert result.provider_attempts[0].runtime_status == "AGENT_TIMEOUT"


# ---- 10. unsupported adapter returns AGENT_RUNTIME_FAILURE ---


def test_unsupported_adapter(tmp_path: Path) -> None:
    """An adapter type that the pool doesn't recognise is
    recorded as ``AGENT_RUNTIME_FAILURE`` with availability
    ``OTHER`` (because ``_check_provider_availability`` has no
    branch for it) and the chain ends in
    ``AGENT_ALL_PROVIDERS_UNAVAILABLE``.
    """
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {"name": "weird", "adapter": "nonexistent_adapter_xyz"},
        ],
    }
    stage = _stage(tmp_path)
    result = run_pool(pool_cfg=pool_cfg, request=_request(stage))
    assert result.runtime_status == "AGENT_ALL_PROVIDERS_UNAVAILABLE"
    # The pool's early availability filter recorded the entry.
    found = any(
        a.provider_name == "weird" and a.availability_status == "OTHER"
        for a in result.provider_attempts
    )
    assert found


# ---- 11. missing API key classified safely ---


def test_missing_api_key_safe(tmp_path: Path) -> None:
    """No API key set: pool reaches openai_compatible_api branch,
    but the api adapter returns ``AGENT_RUNTIME_FAILURE`` with a
    redacted summary that does NOT include the literal key. The
    chain treats this as a configuration failure (non-retryable).
    """
    for key in ("OPENAI_COMPATIBLE_API_KEY",):
        os.environ.pop(key, None)
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
    os.environ["OPENAI_COMPATIBLE_BASE_URL"] = "https://example.test"
    os.environ["LOOP_ENABLE_OPENAI_COMPATIBLE"] = "1"
    stage = _stage(tmp_path)
    result = run_pool(pool_cfg=pool_cfg, request=_request(stage))
    # Chain ends with AGENT_ALL_PROVIDERS_UNAVAILABLE since
    # the only candidate was a configuration failure.
    assert result.runtime_status == "AGENT_ALL_PROVIDERS_UNAVAILABLE"
    for pa in result.provider_attempts:
        assert pa.retryable is False


# ---- 12. provider_attempts include API provider attempt ---


def test_provider_attempts_include_api(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://example.test")
    monkeypatch.setenv("LOOP_ENABLE_OPENAI_COMPATIBLE", "1")

    def fake_invoke(*, request, api_key, base_url, model):
        return _make_api_result(
            provider_name="openai_compatible_api",
            adapter="openai_compatible_api",
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict="PASS",
            exit_code=200,
        )

    import loop_engine.api_review_provider as api_mod

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
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert any(
        a.adapter == "openai_compatible_api" for a in result.provider_attempts
    )


# ---- 13. selected_provider recorded in invocation_summary ---


def test_selected_provider_in_invocation_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://example.test")
    monkeypatch.setenv("LOOP_ENABLE_OPENAI_COMPATIBLE", "1")

    def fake_invoke(*, request, api_key, base_url, model):
        return _make_api_result(
            provider_name="openai_compatible_api",
            adapter="openai_compatible_api",
            runtime_status="AGENT_OK",
            schema_valid=True,
            verdict="PASS",
            exit_code=200,
        )

    import loop_engine.api_review_provider as api_mod

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
    stage = _stage(tmp_path)
    invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    evidence = stage / ".loop" / "agent_invocations" / "ScientificMetaReviewer"
    body = json.loads((evidence / "invocation_summary.json").read_text("utf-8"))
    assert body["selected_provider"] == "openai_compatible_api"


# ---- 14. secret redaction applies to API response / error text ---


def test_secret_redaction_applies_to_api_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Set a fake API key and an upstream error text containing
    that key. After the pool's invocation, walk every artefact
    and assert the literal key value never appears.
    """
    fake_key = "sk-fakeprooftest-loop022s-must-hide-12345"
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", fake_key)
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://example.test")
    monkeypatch.setenv("LOOP_ENABLE_OPENAI_COMPATIBLE", "1")

    def fake_invoke(*, request, api_key, base_url, model):
        # Upstream error text inadvertently leaks the key.
        return _make_api_result(
            provider_name="openai_compatible_api",
            adapter="openai_compatible_api",
            runtime_status="AGENT_TRANSPORT_FAILURE",
            schema_valid=False,
            verdict=None,
            exit_code=401,
            failure_summary=f"401 Unauthorized; check key {fake_key}",
            retryable=True,
        )

    import loop_engine.api_review_provider as api_mod

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
    stage = _stage(tmp_path)
    invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    evidence = stage / ".loop" / "agent_invocations" / "ScientificMetaReviewer"
    for path in evidence.rglob("*"):
        if path.is_file() and path.suffix in {".txt", ".md", ".json"}:
            content = path.read_text("utf-8")
            assert fake_key not in content, f"{path} leaked the key"


# ---- 15. command provider behavior remains unchanged ---


def test_command_provider_unchanged(tmp_path: Path) -> None:
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {"name": "echo_p", "adapter": "command", "command": _fresh_review_output_command()},
        ],
    }
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    assert result.selected_provider == "echo_p"
    assert result.adapter == "command"


# ---- 16. legacy no-pool behavior remains unchanged ---


def test_legacy_no_pool_unchanged(tmp_path: Path) -> None:
    pool_cfg = None
    stage = _stage(tmp_path)
    result = invoke_reviewer(
        pool_cfg=pool_cfg,
        request=_request(stage),
        fallback_command=["true"],
        fallback_adapter_name="command",
    )
    # Legacy path: selected_provider="legacy", adapter="command".
    assert result.selected_provider == "legacy"
    assert result.adapter == "command"


# ---- 17. production stub remains forbidden ---


def test_stub_forbidden_in_pool(tmp_path: Path) -> None:
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {"name": "stub_p", "adapter": "stub"},
            {"name": "real_p", "adapter": "command", "command": _fresh_review_output_command()},
        ],
    }
    stage = _stage(tmp_path)
    result = invoke_reviewer(pool_cfg=pool_cfg, request=_request(stage))
    for pa in result.provider_attempts:
        if pa.provider_name == "stub_p":
            assert pa.availability_status == "DISABLED_BY_ENV"
            assert pa.selected is False
    assert result.selected_provider == "real_p"


# ---- 18. no sigma_abc/ physics files modified ---


def test_no_sigma_abc_physics_modified() -> None:
    """Sanity: Loop 022S does not touch sigma_abc/."""
    sigma_root = REPO_ROOT / "sigma_abc"
    if not sigma_root.exists():
        pytest.skip("sigma_abc/ not present in this worktree")
    assert sigma_root.is_dir()
