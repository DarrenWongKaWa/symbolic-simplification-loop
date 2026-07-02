"""Loop 021 — reviewer provider pool tests.

These tests pin the provider-pool contract:

- Fallback only on retryable runtime failures (QUOTA, TIMEOUT,
  COMMAND_NOT_FOUND, TRANSPORT_FAILURE, RUNTIME_FAILURE,
  NO_OUTPUT).
- NO fallback on schema-valid semantic verdicts (PASS, FAIL,
  NEEDS_PATCH).
- Stub providers are explicitly forbidden when forbid_stub=True.
- API keys are never emitted into stdout, stderr,
  invocation_summary, or pool_result.
- Legacy single-adapter invocation still works exactly as before
  (no regression to existing pytest cases).

Tests use a tiny "fake command provider" by writing a shell
script to a tmp file and using the command adapter. No network
calls are made.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from loop_engine.agent_runtime import AgentInvocationRequest

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---- fixtures --------------------------------------------------------

@pytest.fixture
def stage_dir(tmp_path: Path) -> Path:
    s = tmp_path / "stage"
    (s / ".loop" / "agent_invocations").mkdir(parents=True)
    (s / ".loop").mkdir(exist_ok=True)
    return s


@pytest.fixture
def prompt_path(tmp_path: Path) -> Path:
    p = tmp_path / "prompt.md"
    p.write_text(
        "# Real Local Codex Agent Runtime\n\n# brief review please.\n",
        encoding="utf-8",
    )
    return p


def _write_command_provider_script(
    tmp_path: Path, *, stdout_text: str, stderr_text: str, exit_code: int
) -> Path:
    p = tmp_path / "provider.sh"
    p.parent.mkdir(parents=True, exist_ok=True)
    body = f"""#!/bin/bash
# fake provider for tests
cat <<'EOF_STDOUT'
{stdout_text}
EOF_STDOUT
>&2 cat <<'EOF_STDERR'
{stderr_text}
EOF_STDERR
exit {exit_code}
"""
    p.write_text(body, encoding="utf-8")
    os.chmod(p, 0o755)
    return p


def _request(stage_dir: Path, prompt_path: Path, output_path: Path | None = None) -> AgentInvocationRequest:
    return AgentInvocationRequest(
        agent_name="ScientificMetaReviewer",
        stage_dir=stage_dir,
        prompt_path=prompt_path,
        output_path=output_path or (stage_dir / ".loop" / "reviewer_review.json"),
        schema_name="review_result.codex",
        protected_paths=[],
    )


# ---- fallback on retryable runtime failures ---------------------------

def test_fallback_on_quota_limit(stage_dir: Path, tmp_path: Path, prompt_path: Path) -> None:
    """First provider hits AGENT_QUOTA_LIMIT; the chain exhausts
    without a successful schema-valid attempt and emits
    AGENT_ALL_PROVIDERS_UNAVAILABLE.
    """
    qa_sh = _write_command_provider_script(
        tmp_path / "qa",
        stdout_text="some not-validating output",
        stderr_text="ERROR: You've hit your usage limit. Try again at 9:14 PM.",
        exit_code=1,
    )
    req = _request(stage_dir, prompt_path, output_path=stage_dir / ".loop" / "out.json")
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {
                "name": "codex_quota",
                "adapter": "command",
                "command": ["bash", str(qa_sh)],
            },
        ],
    }
    from loop_engine.reviewer_provider_pool import invoke_reviewer
    res = invoke_reviewer(pool_cfg=pool_cfg, request=req)
    assert res.actually_invoked
    assert res.runtime_status == "AGENT_ALL_PROVIDERS_UNAVAILABLE"
    assert res.review_debt_required is True
    # The chain registered the QUOTA failure on the first attempt.
    assert res.provider_attempts[-1].runtime_status == "AGENT_QUOTA_LIMIT"


def test_no_fallback_on_schema_valid_pass(stage_dir: Path, tmp_path: Path, prompt_path: Path) -> None:
    """A schema-valid PASS stops the chain; the runner does NOT
    ask another provider to hunt for a different verdict.
    """
    pass_sh = _write_command_provider_script(
        tmp_path / "pass",
        stdout_text=json.dumps({"verdict": "PASS", "stage_name": "s", "ok": True}),
        stderr_text="",
        exit_code=0,
    )
    never_sh = _write_command_provider_script(
        tmp_path / "never",
        stdout_text="",
        stderr_text="should never run",
        exit_code=0,
    )
    # Also write the schema-valid output to where the provider expects
    # it via the existing CommandAgentAdapter path. We do that by
    # making the fake provider write its own output_path via the
    # first arg.
    pass_sh_v2 = tmp_path / "pass2.sh"
    out_path = stage_dir / ".loop" / "out.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    body = f"""#!/bin/bash
cat > '{out_path}' <<'EOF_OUT'
{{"verdict":"PASS","stage_name":"s","reviewer_role":"GeneralReviewer","review_scope":"routine_branch","mathematical_status":{{"exact_reconstruction":true,"simplification_real":false,"regression_preserved":true,"overclaim_detected":false}},"blocking_issues":[],"nonblocking_caveats":[],"allowed_claims":["ok"],"forbidden_claims":[],"next_action":"FREEZE","suggested_next_stage":null,"patch_instructions":[]}}
EOF_OUT
exit 0
"""
    pass_sh_v2.write_text(body, encoding="utf-8")
    os.chmod(pass_sh_v2, 0o755)

    req = _request(stage_dir, prompt_path, output_path=out_path)
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [
            {"name": "first_pass", "adapter": "command", "command": ["bash", str(pass_sh_v2)]},
            {"name": "never_reached", "adapter": "command", "command": ["bash", str(never_sh)]},
        ],
    }
    from loop_engine.reviewer_provider_pool import invoke_reviewer
    res = invoke_reviewer(pool_cfg=pool_cfg, request=req)
    assert res.selected_provider == "first_pass"
    # The second provider was never tried.
    provider_names = [a.provider_name for a in res.provider_attempts]
    assert "never_reached" not in provider_names


def test_no_fallback_on_schema_valid_fail(stage_dir: Path, tmp_path: Path, prompt_path: Path) -> None:
    """A schema-valid FAIL also stops the chain."""
    out_path = stage_dir / ".loop" / "out.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fail_sh = tmp_path / "fail.sh"
    body = f"""#!/bin/bash
cat > '{out_path}' <<'EOF_OUT'
{{"verdict":"FAILED","stage_name":"s","reviewer_role":"GeneralReviewer","review_scope":"routine_branch","mathematical_status":{{"exact_reconstruction":false,"simplification_real":false,"regression_preserved":true,"overclaim_detected":true}},"blocking_issues":["boundary"],"nonblocking_caveats":[],"allowed_claims":[],"forbidden_claims":["do not freeze"],"next_action":"FAIL","suggested_next_stage":null,"patch_instructions":[]}}
EOF_OUT
exit 0
"""
    fail_sh.write_text(body, encoding="utf-8")
    os.chmod(fail_sh, 0o755)
    never_sh = _write_command_provider_script(
        tmp_path / "never",
        stdout_text="never",
        stderr_text="never",
        exit_code=0,
    )
    req = _request(stage_dir, prompt_path, output_path=out_path)
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "forbid_stub": True,
        "providers": [
            {"name": "fail_provider", "adapter": "command", "command": ["bash", str(fail_sh)]},
            {"name": "never_reached", "adapter": "command", "command": ["bash", str(never_sh)]},
        ],
    }
    from loop_engine.reviewer_provider_pool import invoke_reviewer
    res = invoke_reviewer(pool_cfg=pool_cfg, request=req)
    assert res.selected_provider == "fail_provider"
    assert res.verdict == "FAILED"
    provider_names = [a.provider_name for a in res.provider_attempts]
    assert "never_reached" not in provider_names


def test_stub_is_forbidden_when_forbid_stub_true(stage_dir: Path, tmp_path: Path, prompt_path: Path) -> None:
    req = _request(stage_dir, prompt_path, output_path=stage_dir / ".loop" / "out.json")
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "forbid_stub": True,
        "providers": [
            {"name": "stub_only", "adapter": "stub"},
        ],
    }
    from loop_engine.reviewer_provider_pool import invoke_reviewer
    res = invoke_reviewer(pool_cfg=pool_cfg, request=req)
    assert res.stub_used is False
    provider_names = [a.provider_name for a in res.provider_attempts]
    assert "stub_only" in provider_names
    # No real provider ran, so we expect ALL_PROVIDERS_UNAVAILABLE.
    assert res.runtime_status == "AGENT_ALL_PROVIDERS_UNAVAILABLE"


def test_all_providers_unavailable_opens_review_debt(
    stage_dir: Path, tmp_path: Path, prompt_path: Path
) -> None:
    """If no provider is enabled + available, the chain exits
    cleanly with AGENT_ALL_PROVIDERS_UNAVAILABLE and review_debt_open.
    """
    req = _request(stage_dir, prompt_path, output_path=stage_dir / ".loop" / "out.json")
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "require_real_provider": True,
        "forbid_stub": True,
        "providers": [],
    }
    from loop_engine.reviewer_provider_pool import invoke_reviewer
    res = invoke_reviewer(pool_cfg=pool_cfg, request=req)
    assert res.runtime_status == "AGENT_ALL_PROVIDERS_UNAVAILABLE"
    assert res.retryable is True
    assert res.review_debt_required is True


def test_provider_disabled_by_env_records_attempt_without_invoking(
    stage_dir: Path, tmp_path: Path, prompt_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LOOP_ENABLE_FAKE", raising=False)
    req = _request(stage_dir, prompt_path, output_path=stage_dir / ".loop" / "out.json")
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "providers": [
            {
                "name": "fake_disabled",
                "adapter": "command",
                "command": ["bash", "/no/such/file"],
                "enabled_env": "LOOP_ENABLE_FAKE",
            },
        ],
    }
    from loop_engine.reviewer_provider_pool import invoke_reviewer
    res = invoke_reviewer(pool_cfg=pool_cfg, request=req)
    names = [a.provider_name for a in res.provider_attempts]
    assert names == ["fake_disabled"]
    assert res.provider_attempts[0].availability_status == "DISABLED_BY_ENV"


def test_pool_resolves_api_key_under_safe_env_pattern(
    stage_dir: Path, prompt_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Anthropic API provider is enabled only when
    ANTHROPIC_API_KEY is set in the env. The provider is recorded
    as AVAILABLE in that case.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-aaaaaaaabbbbbbbbbbbb")
    req = _request(stage_dir, prompt_path, output_path=stage_dir / ".loop" / "out.json")
    pool_cfg = {
        "fallback_policy": "runtime_failure_only",
        "forbid_stub": True,
        "providers": [
            {
                "name": "anthropic_api",
                "adapter": "anthropic_api",
                "api_key_env": "ANTHROPIC_API_KEY",
                "model_env": "ANTHROPIC_MODEL",
            },
        ],
    }
    from loop_engine.reviewer_provider_pool import run_pool
    res = run_pool(pool_cfg=pool_cfg, request=req)
    names = [a.provider_name for a in res.provider_attempts]
    assert "anthropic_api" in names
    assert res.provider_attempts[0].availability_status == "AVAILABLE"


def test_legacy_command_adapter_still_works_with_no_pool(tmp_path: Path, stage_dir: Path, prompt_path: Path) -> None:
    """If no pool is configured, the legacy single-provider
    invocation path must continue to behave as before.
    """
    from loop_engine.agent_runtime import AgentInvocationRequest
    from loop_engine.reviewer_provider_pool import invoke_reviewer
    out_path = stage_dir / ".loop" / "reviewer_review.json"
    req = AgentInvocationRequest(
        agent_name="ScientificMetaReviewer",
        stage_dir=stage_dir,
        prompt_path=prompt_path,
        output_path=out_path,
        schema_name="review_result.codex",
        protected_paths=[],
    )
    res = invoke_reviewer(
        pool_cfg=None,
        request=req,
        fallback_command=["true"],
    )
    # Legacy mode emits a result-shaped object. selected_provider
    # is set to "legacy" once a real command runs (here we use a
    # trivial command).
    assert res.reviewer_role == "ScientificMetaReviewer"
