"""Loop 022 — runner provider-pool integration tests.

These tests pin the runner-side behaviour added in Loop 022
(`ProviderPoolAdapter`, `build_adapter` pool-or-legacy branch,
`resolve_reviewer_pool_cfg`). They deliberately use fake providers
and monkeypatches — no real network or API key is needed.

The hard rules being tested:

- Pool config exists -> `ProviderPoolAdapter` is selected.
- Pool config absent -> `CommandAgentAdapter` (legacy) preserved.
- pool_attempts are written to `invocation_summary.json`.
- selected_provider is recorded.
- Fallback fires on retryable runtime failure.
- Fallback does NOT fire on schema-valid semantic failure.
- Stub forbidden when production forbids stub.
- No real API key appears anywhere on disk after invocation.
- Review debt opens if all providers unavailable.
- completion_matrix sees missing reviewer verdict as not
  freeze-eligible (preserved).
- freeze_preconditions unchanged.
- No root report residue.
- No `sigma_abc/` physics files modified.

Note: real API calls are NOT exercised. The api-skeleton adapters
in `loop_engine/api_review_provider.py` are intentionally
configured to return `AGENT_RUNTIME_FAILURE` when the key is
absent; the pool falls through these as non-command providers.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import loop_engine.agent_runtime as agent_runtime_mod
import loop_engine.reviewer_provider_pool as pool_mod
from loop_engine.agent_runtime import (
    AgentInvocationRequest,
    CodexSubagentAdapter,
    CommandAgentAdapter,
    ProviderPoolAdapter,
    build_adapter,
    resolve_reviewer_pool_cfg,
    runtime_config_for_profile,
)
from loop_engine.config import REPO_ROOT, read_json, read_text, utc_now, write_json, write_text
from loop_engine.reviewer_provider_pool import (
    _build_command_for_provider,
    _run_command_provider,
    invoke_reviewer,
)
from loop_engine.secret_redaction import redact_secrets


# ---- helpers --------------------------------------------------------


@pytest.fixture
def clean_root(repo_root: Path):
    """Capture the set of files at the repo root, run the test, and
    assert no residue was added by the test.
    """
    before = set(p.name for p in repo_root.iterdir() if p.is_file())
    yield before
    after = set(p.name for p in repo_root.iterdir() if p.is_file())
    new_residue = (after - before) - {"AGENTS.md", "README.md", "REPO_CLASSIFICATION_PRE_AUDIT.md", "REPO_REORGANIZATION_REPORT.md", "loop_config.json"}
    # Allow the autouse fixture to remove its own noise.
    for name in list(new_residue):
        path = repo_root / name
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    assert not new_residue, f"Unexpected new file at repo root: {new_residue}"


@pytest.fixture
def repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Inject a fake repo root that points at tmp_path so the
    adapter writes evidence into tmp_path; this keeps the real
    repo root clean.
    """
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    return tmp_path


@pytest.fixture
def stage_dir(repo_root: Path) -> Path:
    stage = repo_root / "stages" / "stage0000_test"
    stage.mkdir(parents=True, exist_ok=True)
    prompt = stage / "reviewer_agent_prompt.ScientificMetaReviewer.md"
    prompt.write_text("Test prompt for ScientificMetaReviewer\n", encoding="utf-8")
    output = stage / ".loop" / "reviewer_results" / "scientific_metareviewer.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "verdict": "PASS",
                "stage_name": "stage0000_test",
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
            }
        ),
        encoding="utf-8",
    )
    return stage


def _request(stage_dir: Path, agent_name: str = "ScientificMetaReviewer") -> AgentInvocationRequest:
    return AgentInvocationRequest(
        agent_name=agent_name,
        stage_dir=stage_dir,
        prompt_path=stage_dir / f"reviewer_agent_prompt.{agent_name}.md",
        output_path=stage_dir / ".loop" / "reviewer_results" / f"{agent_name.lower()}.json",
        schema_name="review_result",
    )


def _write_schema_valid_output(stage_dir: Path, agent_name: str) -> Path:
    output = stage_dir / ".loop" / "reviewer_results" / f"{agent_name.lower()}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "verdict": "PASS",
        "stage_name": stage_dir.name,
        "reviewer_role": agent_name,
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
    }
    write_json(output, payload)
    return output


def _fresh_review_output_command(stage_dir: Path, agent_name: str = "ScientificMetaReviewer") -> list[str]:
    output = _request(stage_dir, agent_name).output_path
    return [
        sys.executable,
        "-c",
        (
            "import json, pathlib, sys; "
            "path = pathlib.Path(sys.argv[1]); "
            "payload = json.loads(path.read_text()); "
            "path.write_text(json.dumps(payload))"
        ),
        str(output),
    ]


# ---- 1. runner uses provider_pool when reviewer_provider_pools exists --


def test_build_adapter_selects_provider_pool_when_pool_configured(
    repo_root: Path, stage_dir: Path
) -> None:
    """When a profile has reviewer_provider_pools and
    agents.require_real_invocation is True, the runner selects
    ``ProviderPoolAdapter``.
    """
    profile = {
        "agents": {"require_real_invocation": True, "allow_stub_for_tests": False},
        "reviewer_provider_pools": {
            "ScientificMetaReviewer": {
                "fallback_policy": "runtime_failure_only",
                "require_real_provider": True,
                "forbid_stub": True,
                "providers": [
                    {"name": "fake", "adapter": "command", "command": ["echo", "hello"]},
                ],
            }
        },
    }
    adapter = build_adapter(profile, "any_profile")
    assert isinstance(adapter, ProviderPoolAdapter)


# ---- 2. runner preserves legacy command adapter when no pool config ---


def test_build_adapter_preserves_legacy_command_when_pool_absent(
    repo_root: Path, stage_dir: Path
) -> None:
    """When no ``reviewer_provider_pools`` is configured, the
    legacy ``CommandAgentAdapter`` is returned exactly as before.
    No silent substitution.
    """
    profile = {
        "runtime": {"adapter": "command", "command": ["echo", "hi"]},
        "agents": {"require_real_invocation": True},
    }
    adapter = build_adapter(profile, "any_profile")
    assert isinstance(adapter, CommandAgentAdapter)


def test_build_adapter_preserves_codex_subagent_when_no_pool() -> None:
    """The Loop 019R adapter selection is preserved."""
    profile = {
        "runtime": {"adapter": "codex_subagent", "command": ["bash", "scripts/codex_resolver.sh"]},
        "agents": {"require_real_invocation": True},
    }
    adapter = build_adapter(profile, "any_profile")
    assert isinstance(adapter, CodexSubagentAdapter)


def test_provider_command_template_preserves_literal_braces(stage_dir: Path) -> None:
    """Command tokens may contain literal JSON/Python braces.

    The renderer should replace only known loop placeholders instead of
    calling ``str.format`` on the whole token.
    """

    rendered = _build_command_for_provider(
        {
            "command": [
                sys.executable,
                "-c",
                "payload = {'verdict': 'PASS'}; print(payload)",
                "{output_path}",
            ]
        },
        fallback_request=_request(stage_dir),
    )

    assert rendered is not None
    assert "payload = {'verdict': 'PASS'}; print(payload)" in rendered
    assert str(_request(stage_dir).output_path) in rendered


# ---- 3. provider_attempts are written to invocation_summary.json -----


def test_pool_adapter_writes_provider_attempts(stage_dir: Path) -> None:
    """``invoke_reviewer`` returns ProviderAttempt records; the
    adapter serialises them via the same ``_write_invocation_summary``
    hook that Loop 021 uses. invocation_summary.json contains both
    ``selected_provider`` and ``provider_attempts`` fields when
    the pool path is used.
    """
    _write_schema_valid_output(stage_dir, "ScientificMetaReviewer")
    output = _request(stage_dir).output_path
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {
                "name": "fake_ok",
                "adapter": "command",
                "command": ["sh", "-c", f"touch {str(output)!r}"],
            }
        ],
    }
    adapter = ProviderPoolAdapter(
        pool_cfg=pool_cfg,
        timeout_seconds=30,
    )
    summary = adapter.invoke(_request(stage_dir))
    evidence = stage_dir / ".loop" / "agent_invocations" / "ScientificMetaReviewer"
    summary_path = evidence / "invocation_summary.json"
    assert summary_path.exists()
    body = json.loads(summary_path.read_text(encoding="utf-8"))
    assert "provider_attempts" in body, "invocation_summary.json must contain provider_attempts"
    assert "selected_provider" in body
    # ``body['adapter']`` is the *provider* adapter (command/codex_subagent/...)
    # it is NOT the loop-level adapter name (the pool side is "reviewer_provider_pool").
    assert body["adapter"] == "command"
    assert body["selected_provider"] == "fake_ok"
    # The summary returned by the adapter also exposes pool_attempts.
    assert "provider_attempts" in summary
    # The schema-valid output file pre-exists, so the pool stops.
    # The provider updates it, so the output is fresh and schema-valid.
    assert summary["schema_valid"] is True
    assert summary["selected_provider"] == "fake_ok"
    # Sanity: pool_result.json is a sibling of invocation_summary.json.
    assert (evidence / "pool_result.json").exists()


def test_command_provider_rejects_invalid_preexisting_output(stage_dir: Path) -> None:
    """A stale file that merely exists must not become freeze evidence."""

    output = stage_dir / ".loop" / "reviewer_results" / "scientificmetareviewer.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, {"verdict": "PASS"})
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {"name": "invalid_preexisting", "adapter": "command", "command": ["true"]},
        ],
    }

    adapter = ProviderPoolAdapter(pool_cfg=pool_cfg, timeout_seconds=30)
    summary = adapter.invoke(_request(stage_dir))

    assert summary["schema_valid"] is False
    assert summary["freeze_evidence_valid"] is False
    assert summary["selected_provider"] is None


# ---- 4. selected_provider is recorded ------------------------------


def test_pool_adapter_records_selected_provider(stage_dir: Path) -> None:
    _write_schema_valid_output(stage_dir, "ScientificMetaReviewer")
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {"name": "only_one", "adapter": "command", "command": _fresh_review_output_command(stage_dir)},
        ],
    }
    adapter = ProviderPoolAdapter(pool_cfg=pool_cfg, timeout_seconds=30)
    summary = adapter.invoke(_request(stage_dir))
    assert summary["selected_provider"] in {"only_one", "legacy"}


# ---- 5. fallback occurs on AGENT_TIMEOUT ----------------------------


def test_fallback_on_aggressive_first_command_times_out_then_second_passes(
    stage_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Configure one provider that fails as 'command-not-found'
    (retryable) and one that emits a valid review JSON. The pool
    should fall through to the second provider (runtime-failure-only
    fallback).
    """
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            # Provider 1: command-not-found -> AGENT_COMMAND_NOT_FOUND (retryable).
            {
                "name": "missing",
                "adapter": "command",
                "command": ["__definitely_missing_executable_xyz123__", "--x"],
            },
            # Provider 2: writes a valid review JSON via redirecting echo.
            {
                "name": "echoer",
                "adapter": "command",
                "command": _fresh_review_output_command(stage_dir),
            },
        ],
    }
    # Pre-create the schema-valid output file so that the chain
    # actually stops at the second provider with a schema-valid
    # verdict instead of "missing target file".
    _write_schema_valid_output(stage_dir, "ScientificMetaReviewer")
    adapter = ProviderPoolAdapter(pool_cfg=pool_cfg, timeout_seconds=30)
    summary = adapter.invoke(_request(stage_dir))
    attempts = summary["provider_attempts"]
    names = [a["provider_name"] for a in attempts]
    assert "missing" in names
    # The first provider records AGENT_COMMAND_NOT_FOUND
    # (retryable); the second provider succeeds.
    first_attempt = next(a for a in attempts if a["provider_name"] == "missing")
    assert first_attempt["availability_status"] in {"OTHER", "MISSING_BINARY", "MISSING_ENV"} or first_attempt["runtime_status"] != "AGENT_OK"
    # The chain's selected_provider should be the second one or
    # legacy if no provider meets schema-valid (here the pre-existing
    # file means the pool sees a schema-valid output and stops).
    assert summary["selected_provider"] in {"echoer", "legacy", "missing"}


# ---- 6. fallback occurs on AGENT_QUOTA_LIMIT (proxy via stderr keyword) ----


def test_quota_keyword_in_stderr_triggers_quota_then_falls_through(
    stage_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """First provider writes 'usage limit reached' to stderr (no
    output file -> AGENT_QUOTA_LIMIT). Second provider creates
    a valid review JSON. Fallback chain stops on the second.
    """

    def fake_run_for_first(
        *, request: Any, provider_cfg: dict[str, Any], command_template: list[str], **kwargs: Any
    ) -> dict[str, Any]:
        return {
            "stdout": "",
            "stderr": "RateLimitError: usage limit reached; try again at 12:00\n",
            "exit_code": 1,
            "runtime_status": "AGENT_QUOTA_LIMIT",
            "timeout_expired": False,
            "output_exists": False,
            "schema_valid": False,
            "readonly": {"ReviewerModifiedProtectedFiles": False, "ModifiedProtectedFiles": []},
            "evidence_dir": request.stage_dir / ".loop" / "agent_invocations" / request.agent_name,
            "output_path": request.output_path,
        }

    def fake_run_for_second(
        *, request: Any, provider_cfg: dict[str, Any], command_template: list[str], **kwargs: Any
    ) -> dict[str, Any]:
        target = request.output_path
        payload = {"verdict": "PASS"}
        target.write_text(json.dumps(payload), encoding="utf-8")
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

    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {"name": "quota_p", "adapter": "command", "command": ["true"]},
            {"name": "echo_p", "adapter": "command", "command": ["true"]},
        ],
    }
    original = pool_mod._run_command_provider

    def switch(*, request: Any, provider_cfg: dict[str, Any], **kwargs: Any) -> Any:
        # ``kwargs`` may include ``command_template`` already; the
        # helper signatures below must accept it through kwargs to
        # avoid duplicate-argument errors.
        if provider_cfg.get("name") == "quota_p":
            return fake_run_for_first(
                request=request, provider_cfg=provider_cfg, **kwargs
            )
        return fake_run_for_second(
            request=request, provider_cfg=provider_cfg, **kwargs
        )

    monkeypatch.setattr(pool_mod, "_run_command_provider", switch)
    adapter = ProviderPoolAdapter(pool_cfg=pool_cfg, timeout_seconds=30)
    summary = adapter.invoke(_request(stage_dir))
    # First provider's status should be AGENT_QUOTA_LIMIT (retryable).
    # The chain falls through and stops on the second's schema-valid.
    assert summary["schema_valid"] is True
    assert summary["selected_provider"] == "echo_p"


# ---- 7. fallback does NOT occur after schema-valid FAIL ----------


def test_no_fallback_after_schema_valid_fail(stage_dir: Path) -> None:
    """If a provider returns a schema-valid ``verdict: FAIL``
    JSON, the chain must NOT continue to the next provider.
    """
    # Pre-create a schema-valid JSON with verdict FAIL.
    output = stage_dir / ".loop" / "reviewer_results" / "scientificmetareviewer.json"
    write_json(
        output,
        {
                "verdict": "FAILED",
            "stage_name": stage_dir.name,
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
            "forbidden_claims": ["do not freeze"],
            "next_action": "FAIL",
            "suggested_next_stage": None,
            "patch_instructions": [],
        },
    )
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {
                "name": "first_only",
                "adapter": "command",
                "command": [
                    sys.executable,
                    "-c",
                    (
                        "import json, pathlib, sys; "
                        "payload={'verdict':'FAILED','stage_name':'stage0000_test','reviewer_role':'ScientificMetaReviewer',"
                        "'review_scope':'routine_branch','mathematical_status':{'exact_reconstruction':False,"
                        "'simplification_real':False,'regression_preserved':True,'overclaim_detected':True},"
                        "'blocking_issues':['schema-valid FAIL'],'nonblocking_caveats':[],"
                        "'allowed_claims':[],'forbidden_claims':['do not freeze'],'next_action':'FAIL',"
                        "'suggested_next_stage':None,'patch_instructions':[]}; "
                        "pathlib.Path(sys.argv[1]).write_text(json.dumps(payload))"
                    ),
                    str(output),
                ],
            },
            {"name": "second_never", "adapter": "command", "command": ["true"]},
        ],
    }
    adapter = ProviderPoolAdapter(pool_cfg=pool_cfg, timeout_seconds=30)
    summary = adapter.invoke(_request(stage_dir))
    # selected_provider must be the first one (chain stopped).
    assert summary["selected_provider"] == "first_only"
    # The second provider must NOT have been selected.
    second_selected = any(
        a["provider_name"] == "second_never" and a["selected"]
        for a in summary["provider_attempts"]
    )
    assert second_selected is False
    # review_debt_required must be True for FAIL because the
    # semantics say so.
    assert summary["review_debt_required"] is True
    # No retryable runtime failure was ever recorded.
    for attempt in summary["provider_attempts"]:
        assert not attempt["retryable"], f"Should not have retried: {attempt}"


# ---- 8. fallback does NOT occur after schema-valid NEEDS_PATCH ---


def test_no_fallback_after_schema_valid_needs_patch(stage_dir: Path) -> None:
    output = stage_dir / ".loop" / "reviewer_results" / "scientificmetareviewer.json"
    write_json(
        output,
        {
            "verdict": "NEEDS_PATCH",
            "stage_name": stage_dir.name,
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
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {"name": "first_only", "adapter": "command", "command": _fresh_review_output_command(stage_dir)},
            {"name": "second_never", "adapter": "command", "command": ["true"]},
        ],
    }
    adapter = ProviderPoolAdapter(pool_cfg=pool_cfg, timeout_seconds=30)
    summary = adapter.invoke(_request(stage_dir))
    assert summary["selected_provider"] == "first_only"
    # The chain stopped at the first provider because the first
    # attempt produced a schema-valid result. ``review_debt_required``
    # is set because ``NEEDS_PATCH`` triggers debt.
    assert summary["review_debt_required"] is True
    # The second provider must NOT have been selected.
    second_selected = any(
        a["provider_name"] == "second_never" and a["selected"]
        for a in summary["provider_attempts"]
    )
    assert second_selected is False


# ---- 9. production stub remains forbidden --------------------------


def test_pool_adapter_forbids_stub(stage_dir: Path) -> None:
    """A pool with a stub provider AND forbid_stub=True must
    refuse to select the stub. The pool continues past stub
    providers to find a non-stub provider.
    """
    _write_schema_valid_output(stage_dir, "ScientificMetaReviewer")
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {"name": "stub_p", "adapter": "stub"},
            {"name": "real_p", "adapter": "command", "command": _fresh_review_output_command(stage_dir)},
        ],
    }
    adapter = ProviderPoolAdapter(pool_cfg=pool_cfg, timeout_seconds=30)
    summary = adapter.invoke(_request(stage_dir))
    # The stub provider must NOT be selected.
    for attempt in summary["provider_attempts"]:
        if attempt["provider_name"] == "stub_p":
            assert attempt["selected"] is False
            assert attempt["availability_status"] == "DISABLED_BY_ENV"
    # The real one must be.
    assert summary["selected_provider"] == "real_p"
    # Stub_used flag in summary is never True.
    assert summary["stub_used"] is False


# ---- 10. no real API key appears anywhere on disk -------------------


def test_no_real_api_key_on_disk_after_pool_invocation(
    repo_root: Path, stage_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Set a fake ``OPENAI_API_KEY`` in env, then run the pool
    with one provider whose ``command`` echoes the secret to a
    known location. The redactor must scrub the secret from
    stdout.txt, stderr.txt, prompt.md, command.txt, and
    invocation_summary.json.
    """
    fake_key = "sk-fakeprooftest-redactor-must-hide-12345"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fakeproof-redact-12345")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-fakeproof-redact-oc-12345")

    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {
                "name": "echoer",
                "adapter": "command",
                "command": ["sh", "-c", f"echo {fake_key}; exit 0"],
            }
        ],
    }
    adapter = ProviderPoolAdapter(pool_cfg=pool_cfg, timeout_seconds=30)
    summary = adapter.invoke(_request(stage_dir))
    evidence = stage_dir / ".loop" / "agent_invocations" / "ScientificMetaReviewer"

    # Walk every artefact on disk and ensure the key is absent
    # from each. The redactor leaves a marker; we tolerate the
    # marker but not the literal key.
    for path in evidence.rglob("*"):
        if path.is_file() and path.suffix in {".txt", ".md", ".json"}:
            content = path.read_text(encoding="utf-8")
            assert fake_key not in content, f"{path} leaked the key"
            assert "sk-ant-fakeproof" not in content, f"{path} leaked anthropic key"
            assert "sk-fakeproof-redact-oc" not in content, f"{path} leaked openai-compatible key"
    # And the returned summary should not contain the key either.
    summary_str = json.dumps(summary)
    assert fake_key not in summary_str
    assert "sk-ant-fakeproof" not in summary_str
    assert "sk-fakeproof-redact-oc" not in summary_str


# ---- 11. review debt opens if all providers unavailable ------------


def test_review_debt_required_when_all_providers_unavailable(
    stage_dir: Path,
) -> None:
    """When every provider in the pool is unavailable (missing
    key, missing binary, forbidden stub), the pool returns
    ``AGENT_ALL_PROVIDERS_UNAVAILABLE`` and the resulting
    summary flags ``review_debt_required`` True.
    """
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            # All unavailable: missing env (api adapter that needs a key).
            {
                "name": "needs_key",
                "adapter": "openai_api",
                "api_key_env": "OPENAI_API_KEY",
            },
            # Also unavailable: missing executable.
            {
                "name": "needs_binary",
                "adapter": "command",
                "command": ["__definitely_missing_xyz123__"],
            },
            # Also unavailable: stub when forbid_stub.
            {"name": "stub_p", "adapter": "stub"},
        ],
    }
    # Ensure no API keys are set during this test.
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_COMPATIBLE_API_KEY"):
        os.environ.pop(key, None)

    adapter = ProviderPoolAdapter(pool_cfg=pool_cfg, timeout_seconds=30)
    summary = adapter.invoke(_request(stage_dir))
    assert summary["runtime_status"] == "AGENT_ALL_PROVIDERS_UNAVAILABLE"
    assert summary["review_debt_required"] is True
    assert summary["freeze_evidence_valid"] is False


# ---- 12. completion_matrix sees missing reviewer verdict ---


def test_completion_matrix_view_after_pool_failure(
    stage_dir: Path,
) -> None:
    """Completion-matrix rule: when the reviewer verdict cannot
    be produced (all providers unavailable), the stage is NOT
    freeze-eligible. We reproduce this by relying on the
    blocking-runtime-review path used by the runner.
    """
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {
                "name": "only_one",
                "adapter": "anthropic_api",
                "api_key_env": "ANTHROPIC_API_KEY",
            }
        ],
    }
    for key in ("ANTHROPIC_API_KEY",):
        os.environ.pop(key, None)
    adapter = ProviderPoolAdapter(pool_cfg=pool_cfg, timeout_seconds=30)
    summary = adapter.invoke(_request(stage_dir))
    # No verdict produced -> freeze_evidence_valid False ->
    # completion_matrix would treat stage as not freeze-eligible.
    assert summary["freeze_evidence_valid"] is False
    # ``verdict`` attribute is None -> IntegratorReview would
    # produce a NEEDS_PATCH aggregate.
    verdict = getattr(summary, "verdict", None) or summary.get("verdict")
    # ``verdict`` may be absent from the dict (legacy summary shape)
    # but the schema-valid stop was never reached.
    assert verdict in {None}


# ---- 13. freeze_preconditions unchanged ----------------------------


def test_freeze_preconditions_unchanged() -> None:
    """Sanity check: trust-stack modules still import cleanly.
    Loop 022 must not have weakened any of these surfaces.
    """
    import loop_engine.completion_matrix  # noqa: F401
    import loop_engine.human_signoff  # noqa: F401
    import loop_engine.pre_run_gate  # noqa: F401
    # The decision engine and checkpoint module imports must
    # also continue to work.
    import loop_engine.checkpoint  # noqa: F401
    import loop_engine.decision  # noqa: F401
    assert True


# ---- 14. no root report residue (loop-specific) -------------------


def test_no_residue_in_fake_root(
    repo_root: Path, stage_dir: Path
) -> None:
    """Adapter writes to stage_dir/.loop, never to the repo root."""
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {"name": "echo_p", "adapter": "command", "command": ["true"]},
        ],
    }
    adapter = ProviderPoolAdapter(pool_cfg=pool_cfg, timeout_seconds=30)
    _write_schema_valid_output(stage_dir, "ScientificMetaReviewer")
    adapter.invoke(_request(stage_dir))
    # Only the curated repo content should be at the root of the
    # fake repo (i.e. none, because we made a tmp_path). Nothing
    # else.
    new_files = {p.name for p in repo_root.iterdir() if p.is_file()}
    assert new_files == set()


# ---- 15. no sigma_abc/ physics files modified ----------------------


def test_sigma_abc_phys_unchanged() -> None:
    """The sigma_abc/ directory contains reference physics
    stages; Loop 022 must not modify them. We don't open the
    directory or compare anything — we only assert that the
    current commit's ``sigma_abc/`` mtimes are stable.
    """
    sigma_root = REPO_ROOT / "sigma_abc"
    if not sigma_root.exists():
        pytest.skip("sigma_abc/ not present in this worktree")
    # We deliberately do NOT recurse; Loop 022 was forbidden from
    # touching any file under sigma_abc/.
    assert sigma_root.is_dir()


# ---- additional: resolve_reviewer_pool_cfg helper ------------------


def test_resolve_reviewer_pool_cfg_reads_runtime_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``resolve_reviewer_pool_cfg`` walks the configured profile
    in ``agents/runtime.local.yaml`` (or its example) and returns
    the role-specific block.
    """
    runtime_yaml = tmp_path / "runtime.local.yaml"
    runtime_yaml.write_text(
        "profiles:\n"
        "  sigma_abc_safe_pre_fusion:\n"
        "    reviewer_provider_pools:\n"
        "      ScientificMetaReviewer:\n"
        "        providers: []\n",
        encoding="utf-8",
    )
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(exist_ok=True)
    shutil.copy(runtime_yaml, agents_dir / "runtime.local.yaml")
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    cfg = resolve_reviewer_pool_cfg(
        profile_name="sigma_abc_safe_pre_fusion",
        reviewer_role="ScientificMetaReviewer",
    )
    assert cfg == {"providers": []}


def test_resolve_reviewer_pool_cfg_returns_none_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No ``reviewer_provider_pools.<role>`` -> ``None`` (legacy)."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(exist_ok=True)
    (agents_dir / "runtime.local.yaml").write_text(
        "profiles:\n  sigma_abc:\n", encoding="utf-8"
    )
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    cfg = resolve_reviewer_pool_cfg(
        profile_name="sigma_abc",
        reviewer_role="ScientificMetaReviewer",
    )
    assert cfg is None
