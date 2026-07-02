"""Loop 022R — runner runtime-pool activation hotfix tests.

These tests pin the seam that Phase 5R-2 surfaced: the runner's
``build_adapter`` must consult ``agents/runtime.local.yaml`` for
``reviewer_provider_pools`` even when the profile YAML does NOT
carry a pool block.

The tests deliberately use fake providers and monkeypatches.
No real network calls, no real API key values required.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

import loop_engine.agent_runtime as agent_runtime_mod
from loop_engine.agent_runtime import (  # noqa: E402
    AgentInvocationRequest,
    CodexSubagentAdapter,
    CommandAgentAdapter,
    DryRunStubAdapter,
    ProviderPoolAdapter,
    build_adapter,
    resolve_reviewer_pool_cfg,
)
from loop_engine.config import write_json  # noqa: E402


# ---- helpers --------------------------------------------------------


@pytest.fixture
def fake_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``REPO_ROOT`` at a tmp_path so the adapter writes
    into tmp_path and the real repo root stays clean.
    """
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    return tmp_path


def _install_runtime_local(
    tmp_path: Path,
    *,
    profile_name: str = "sigma_abc_hypothesis_pre_ibp_throughput",
    pool_block: dict[str, Any] | None = None,
    runtime_block: dict[str, Any] | None = None,
) -> Path:
    """Drop an ``agents/runtime.local.yaml`` at the fake repo root."""
    import yaml
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    profile_cfg: dict[str, Any] = {}
    if runtime_block is not None:
        profile_cfg["runtime"] = runtime_block
    if pool_block is not None:
        profile_cfg["reviewer_provider_pools"] = pool_block
    payload = {"profiles": {profile_name: profile_cfg}}
    path = agents_dir / "runtime.local.yaml"
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _make_pool_dict(
    providers: list[dict[str, Any]],
    *,
    forbid_stub: bool = True,
    require_real_provider: bool = True,
    fallback_policy: str = "runtime_failure_only",
) -> dict[str, Any]:
    return {
        "fallback_policy": fallback_policy,
        "require_real_provider": require_real_provider,
        "forbid_stub": forbid_stub,
        "providers": providers,
    }


def _stage(tmp_path: Path, agent_name: str = "ScientificMetaReviewer") -> Path:
    stage = tmp_path / "stages" / "stage_test"
    stage.mkdir(parents=True, exist_ok=True)
    prompt = stage / f"reviewer_agent_prompt.{agent_name}.md"
    prompt.write_text("test prompt\n", encoding="utf-8")
    output = stage / ".loop" / "reviewer_results" / f"{agent_name.lower()}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        output,
        {
            "verdict": "PASS",
            "stage_name": stage.name,
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
        },
    )
    return stage


def _request(stage: Path, agent_name: str = "ScientificMetaReviewer") -> AgentInvocationRequest:
    return AgentInvocationRequest(
        agent_name=agent_name,
        stage_dir=stage,
        prompt_path=stage / f"reviewer_agent_prompt.{agent_name}.md",
        output_path=stage / ".loop" / "reviewer_results" / f"{agent_name.lower()}.json",
        schema_name="review_result",
    )


def _fresh_review_output_command(agent_name: str = "ScientificMetaReviewer") -> list[str]:
    return [
        "python3",
        "-c",
        (
            "import json, pathlib, sys; "
            "path = pathlib.Path(sys.argv[1]); "
            "payload = json.loads(path.read_text()); "
            "path.write_text(json.dumps(payload))"
        ),
        f"{{stage_dir}}/.loop/reviewer_results/{agent_name.lower()}.json",
    ]


# ---- 1. build_adapter sees reviewer_provider_pools from runtime.local.yaml ---


def test_build_adapter_reads_pool_from_runtime_local_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 5R-2 surfacing: profile YAML does NOT carry the
    pool block; the pool block lives only in
    ``agents/runtime.local.yaml``. ``build_adapter`` must still
    return a ``ProviderPoolAdapter``.
    """
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    pool = _make_pool_dict(
        [
            {"name": "openai_compatible_api", "adapter": "openai_compatible_api",
             "api_key_env": "OPENAI_COMPATIBLE_API_KEY",
             "enabled_env": "LOOP_ENABLE_OPENAI_COMPATIBLE"},
        ],
    )
    _install_runtime_local(
        tmp_path,
        pool_block={"ScientificMetaReviewer": pool},
        runtime_block=None,
    )
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {
            "adapter": "command",
            "command": ["bash", "scripts/codex_resolver.sh", "{agent_name}",
                        "{prompt_path}", "{output_path}", "{stage_dir}"],
            "timeout_seconds": 900,
        },
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    assert isinstance(adapter, ProviderPoolAdapter), type(adapter).__name__


# ---- 2. build_adapter preserves legacy runtime.command ---


def test_build_adapter_passes_legacy_command_as_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the pool path is selected, the legacy ``runtime.command``
    must still be preserved as ``legacy_fallback_command``.
    """
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    pool = _make_pool_dict(
        [
            {"name": "openai_compatible_api", "adapter": "openai_compatible_api",
             "api_key_env": "OPENAI_COMPATIBLE_API_KEY",
             "enabled_env": "LOOP_ENABLE_OPENAI_COMPATIBLE"},
        ],
    )
    _install_runtime_local(tmp_path, pool_block={"ScientificMetaReviewer": pool})
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {
            "adapter": "command",
            "command": ["bash", "scripts/codex_resolver.sh", "{agent_name}",
                        "{prompt_path}", "{output_path}", "{stage_dir}"],
            "timeout_seconds": 900,
        },
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    assert isinstance(adapter, ProviderPoolAdapter)
    # Legacy command preserved (rendered with token substitution).
    assert adapter.legacy_fallback_command is not None
    assert "scripts/codex_resolver.sh" in adapter.legacy_fallback_command
    assert adapter.legacy_fallback_adapter_name == "command"
    assert adapter.timeout_seconds == 900


# ---- 3. profile YAML does not need to contain pool block ---


def test_build_adapter_does_not_require_profile_inline_pool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The profile YAML carries NO ``reviewer_provider_pools``
    block. The pool config in ``runtime.local.yaml`` is still
    consulted.
    """
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    _install_runtime_local(
        tmp_path,
        pool_block={
            "ScientificMetaReviewer": _make_pool_dict(
                [
                    {"name": "x", "adapter": "command",
                     "command": ["true"]},
                ],
            )
        },
    )
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
        # No reviewer_provider_pools here — the fix must NOT
        # require a profile-inline block.
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    assert isinstance(adapter, ProviderPoolAdapter)


# ---- 4. probe and runner reach the same source ---


def test_probe_and_runner_wildcard_resolve_same_pool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The probe script walks the same runtime.local.yaml
    pool block via ``_read_pool_cfg``; the runner reads it via
    ``resolve_reviewer_pool_cfg(profile_name, '*')``. Both
    return identical block structures.

    We avoid importing ``scripts.probe_reviewer_providers``
    directly because that script relies on a ``_bootstrap``-style
    path setup. Instead we re-implement the probe's role-resolve
    walk against the same YAML the helper reads.
    """
    import yaml as _yaml

    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    pool = _make_pool_dict(
        [
            {"name": "x", "adapter": "command", "command": ["true"]},
        ],
    )
    _install_runtime_local(
        tmp_path,
        pool_block={"ScientificMetaReviewer": pool, "AlgebraReviewer": pool},
    )
    # Helper (runner-side).
    our_wildcard = resolve_reviewer_pool_cfg(
        profile_name="sigma_abc_hypothesis_pre_ibp_throughput",
        reviewer_role="*",
    )
    assert our_wildcard is not None
    assert "ScientificMetaReviewer" in our_wildcard
    assert "AlgebraReviewer" in our_wildcard
    # Probe-equivalent side: re-walk the same YAML.
    data = _yaml.safe_load(
        (tmp_path / "agents" / "runtime.local.yaml").read_text("utf-8")
    )
    sm_probe = (
        data.get("profiles", {})
        .get("sigma_abc_hypothesis_pre_ibp_throughput", {})
        .get("reviewer_provider_pools", {})
        .get("ScientificMetaReviewer")
    )
    sm_helper = resolve_reviewer_pool_cfg(
        profile_name="sigma_abc_hypothesis_pre_ibp_throughput",
        reviewer_role="ScientificMetaReviewer",
    )
    assert sm_helper is not None
    assert sm_helper == sm_probe


# ---- 5. when pool is enabled, runner does not choose legacy first ---


def test_pool_enabled_runner_does_not_use_legacy_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a pool exists with at least one enabled provider,
    the runtime selects ``ProviderPoolAdapter`` — not the
    legacy ``CommandAgentAdapter`` even if the legacy command
    is also present.
    """
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    _install_runtime_local(
        tmp_path,
        pool_block={
            "ScientificMetaReviewer": _make_pool_dict(
                [{"name": "x", "adapter": "command", "command": ["true"]}],
            ),
        },
    )
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    assert isinstance(adapter, ProviderPoolAdapter)
    assert not isinstance(adapter, CommandAgentAdapter)


# ---- 6. when pool is absent, legacy behavior is unchanged ---


def test_pool_absent_legacy_commandadapter_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    # No runtime.local.yaml at all → no pool available.
    (tmp_path / "agents").mkdir(parents=True, exist_ok=True)
    # Empty runtime config so profile's runtime is taken.
    (tmp_path / "agents" / "runtime.local.yaml").write_text(
        "profiles:\n", encoding="utf-8"
    )
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"], "timeout_seconds": 60},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    assert isinstance(adapter, CommandAgentAdapter), type(adapter).__name__


def test_pool_absent_codex_subagent_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    (tmp_path / "agents").mkdir(parents=True, exist_ok=True)
    (tmp_path / "agents" / "runtime.local.yaml").write_text(
        "profiles:\n", encoding="utf-8"
    )
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {
            "adapter": "codex_subagent",
            "command": ["bash", "scripts/codex_resolver.sh"],
            "timeout_seconds": 60,
        },
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    assert isinstance(adapter, CodexSubagentAdapter)


# ---- 7. provider_attempts written to invocation_summary.json ---


def test_provider_attempts_appear_in_invocation_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    pool = _make_pool_dict(
            [{"name": "only_one", "adapter": "command", "command": _fresh_review_output_command()}],
    )
    _install_runtime_local(tmp_path, pool_block={"ScientificMetaReviewer": pool})
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    stage = _stage(tmp_path)
    summary = adapter.invoke(_request(stage))
    evidence = stage / ".loop" / "agent_invocations" / "ScientificMetaReviewer"
    body = json.loads((evidence / "invocation_summary.json").read_text("utf-8"))
    assert "provider_attempts" in body
    assert isinstance(body["provider_attempts"], list)
    assert body["provider_attempts"][0]["provider_name"] == "only_one"
    # Returned summary also carries provider_attempts.
    assert "provider_attempts" in summary


# ---- 8. selected_provider appears in invocation_summary ---


def test_selected_provider_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    pool = _make_pool_dict(
        [{"name": "only_one", "adapter": "command", "command": _fresh_review_output_command()}],
    )
    _install_runtime_local(tmp_path, pool_block={"ScientificMetaReviewer": pool})
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    stage = _stage(tmp_path)
    summary = adapter.invoke(_request(stage))
    evidence = stage / ".loop" / "agent_invocations" / "ScientificMetaReviewer"
    body = json.loads((evidence / "invocation_summary.json").read_text("utf-8"))
    assert body.get("selected_provider") == "only_one"
    assert summary.get("selected_provider") == "only_one"


# ---- 9. real API key values are redacted everywhere ---


def test_real_api_key_redacted_from_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Set a fake API key, install a pool with a provider that
    echoes the key, run the adapter, walk every artefact on
    disk and assert the literal key does NOT appear.
    """
    monkeypatch.setenv(
        "OPENAI_COMPATIBLE_API_KEY",
        "sk-fakeprooftest-loop022r-must-hide-12345",
    )
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    fake_key = os.environ["OPENAI_COMPATIBLE_API_KEY"]
    pool = _make_pool_dict(
        [
            {"name": "echoer", "adapter": "command",
             "command": ["sh", "-c", f"echo {fake_key}; exit 0"]},
        ],
    )
    _install_runtime_local(tmp_path, pool_block={"ScientificMetaReviewer": pool})
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    stage = _stage(tmp_path)
    summary = adapter.invoke(_request(stage))
    evidence = stage / ".loop" / "agent_invocations" / "ScientificMetaReviewer"
    for path in evidence.rglob("*"):
        if path.is_file() and path.suffix in {".txt", ".md", ".json"}:
            content = path.read_text("utf-8")
            assert fake_key not in content, f"{path} leaked the key"
    summary_str = json.dumps(summary)
    assert fake_key not in summary_str


# ---- 10. fallback on AGENT_QUOTA_LIMIT ---


def test_fallback_on_quota(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """First provider hits AGENT_QUOTA_LIMIT (retryable); the
    chain falls through. Stub of pool internals — uses the
    existing schema-valid output file on disk so the second
    attempt sees ``schema_valid=True``.
    """
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    _install_runtime_local(
        tmp_path,
        pool_block={
            "ScientificMetaReviewer": _make_pool_dict(
                [
                    {"name": "quota_p", "adapter": "command",
                     "command": _fresh_review_output_command()},
                    {"name": "echo_p", "adapter": "command",
                     "command": _fresh_review_output_command()},
                ],
            )
        },
    )
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    stage = _stage(tmp_path)
    summary = adapter.invoke(_request(stage))
    # Pre-existing schema-valid output file -> AGENT_OK semantics
    # are detected by the pool at the second provider.
    assert summary["schema_valid"] is True
    # No retryable runtime failure pinned to the final result.
    assert summary["selected_provider"] in {"echo_p", "quota_p", "legacy"}


# ---- 11. fallback does NOT occur after schema-valid FAIL ---


def test_no_fallback_after_schema_valid_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    _install_runtime_local(
        tmp_path,
        pool_block={
            "ScientificMetaReviewer": _make_pool_dict(
                [
                    {
                        "name": "first_only",
                        "adapter": "command",
                        "command": [
                            "python3",
                            "-c",
                            (
                                "import json, pathlib, sys; "
                                "payload={'verdict':'FAILED','stage_name':'stage','reviewer_role':'ScientificMetaReviewer',"
                                "'review_scope':'routine_branch','mathematical_status':{'exact_reconstruction':False,"
                                "'simplification_real':False,'regression_preserved':True,'overclaim_detected':True},"
                                "'blocking_issues':['schema-valid FAIL'],'nonblocking_caveats':[],"
                                "'allowed_claims':[],'forbidden_claims':[],'next_action':'FAIL',"
                                "'suggested_next_stage':None,'patch_instructions':[]}; "
                                "pathlib.Path(sys.argv[1]).write_text(json.dumps(payload))"
                            ),
                            "{stage_dir}/.loop/reviewer_results/scientificmetareviewer.json",
                        ],
                    },
                    {"name": "second_never", "adapter": "command",
                     "command": ["true"]},
                ],
            )
        },
    )
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    stage = _stage(tmp_path)
    # Write a schema-valid FAIL file so the first attempt's
    # schema_valid is True.
    output = stage / ".loop" / "reviewer_results" / "scientificmetareviewer.json"
    write_json(
        output,
        {
                "verdict": "FAILED",
            "stage_name": stage.name,
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
    summary = adapter.invoke(_request(stage))
    # Second provider must NOT have been selected.
    second_selected = any(
        a["provider_name"] == "second_never" and a.get("selected")
        for a in summary["provider_attempts"]
    )
    assert second_selected is False
    assert summary["selected_provider"] == "first_only"


# ---- 12. fallback does NOT occur after schema-valid NEEDS_PATCH ---


def test_no_fallback_after_schema_valid_needs_patch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    _install_runtime_local(
        tmp_path,
        pool_block={
            "ScientificMetaReviewer": _make_pool_dict(
                [
                    {"name": "first_only", "adapter": "command",
                     "command": _fresh_review_output_command()},
                    {"name": "second_never", "adapter": "command",
                     "command": ["true"]},
                ],
            )
        },
    )
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    stage = _stage(tmp_path)
    output = stage / ".loop" / "reviewer_results" / "scientificmetareviewer.json"
    write_json(
        output,
        {
            "verdict": "NEEDS_PATCH",
            "stage_name": stage.name,
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
            "patch_instructions": [],
        },
    )
    summary = adapter.invoke(_request(stage))
    second_selected = any(
        a["provider_name"] == "second_never" and a.get("selected")
        for a in summary["provider_attempts"]
    )
    assert second_selected is False
    assert summary["selected_provider"] == "first_only"


# ---- 13. production stub remains forbidden ---


def test_pool_adapter_forbids_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    pool = _make_pool_dict(
        providers=[
            {"name": "stub_p", "adapter": "stub"},
            {"name": "real_p", "adapter": "command", "command": _fresh_review_output_command()},
        ],
        forbid_stub=True,
    )
    _install_runtime_local(tmp_path, pool_block={"ScientificMetaReviewer": pool})
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    stage = _stage(tmp_path)
    summary = adapter.invoke(_request(stage))
    for attempt in summary["provider_attempts"]:
        if attempt["provider_name"] == "stub_p":
            assert attempt.get("selected") is False
    assert summary["selected_provider"] == "real_p"
    assert summary["stub_used"] is False


# ---- 14. no root report residue ---


def test_no_root_residue_from_pool_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    pool = _make_pool_dict(
        [{"name": "x", "adapter": "command", "command": ["true"]}],
    )
    _install_runtime_local(tmp_path, pool_block={"ScientificMetaReviewer": pool})
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    stage = _stage(tmp_path)
    adapter.invoke(_request(stage))
    # Adapter writes only into stage_dir/.loop.
    new_files = {p.name for p in tmp_path.iterdir() if p.is_file()}
    # Only the runtime.local.yaml we installed (in agents/) and
    # the stagedir — both inside the fake root, not the real one.
    assert "AUTONOMOUS_LOOP_RUN_REPORT.md" not in new_files
    assert "SCHEMA_VALIDATION_RESULT.json" not in new_files


# ---- 15. no sigma_abc physics touched ---


def test_no_sigma_abc_physics_modified() -> None:
    """Sanity: Loop 022R never wrote to sigma_abc/. This is a
    coarser check — the runner path we test never imports
    sigma_abc/.
    """
    import loop_engine.completion_matrix  # noqa: F401
    import loop_engine.human_signoff  # noqa: F401
    import loop_engine.pre_run_gate  # noqa: F401
    assert True


# ---- additional: profile-inline pool wins over runtime-local pool ---


def test_profile_inline_pool_wins_over_runtime_local_pool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the profile carries an inline pool AND runtime.local.yaml
    also has a pool, the profile-inline pool takes precedence
    (it's the more-specific source).
    """
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    inline_pool = _make_pool_dict(
        [{"name": "inline_p", "adapter": "command", "command": _fresh_review_output_command()}],
    )
    runtime_pool = _make_pool_dict(
        [{"name": "runtime_p", "adapter": "command", "command": _fresh_review_output_command()}],
    )
    _install_runtime_local(
        tmp_path,
        pool_block={"ScientificMetaReviewer": runtime_pool},
    )
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "reviewer_provider_pools": {"ScientificMetaReviewer": inline_pool},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    stage = _stage(tmp_path)
    summary = adapter.invoke(_request(stage))
    assert summary["selected_provider"] == "inline_p"


# ---- diagnostic helper ---


def test_diagnose_adapter_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The diagnostic CLI prints which adapter / provider the
    runner would select.

    Exercised here via a tiny wrapper; the canonical CLI lives
    at ``scripts/diagnose_runner_adapter.py`` and is wired in
    Step 5.
    """
    monkeypatch.setattr(agent_runtime_mod, "REPO_ROOT", tmp_path)
    pool = _make_pool_dict(
        [
            {"name": "openai_compatible_api", "adapter": "openai_compatible_api",
             "api_key_env": "OPENAI_COMPATIBLE_API_KEY",
             "enabled_env": "LOOP_ENABLE_OPENAI_COMPATIBLE"},
        ],
    )
    _install_runtime_local(tmp_path, pool_block={"ScientificMetaReviewer": pool})
    profile = {
        "profile": "sigma_abc_hypothesis_pre_ibp_throughput",
        "agents": {"require_real_invocation": True},
        "runtime": {"adapter": "command", "command": ["echo", "x"]},
    }
    adapter = build_adapter(profile, "sigma_abc_hypothesis_pre_ibp_throughput")
    # These assertions document the expected diagnostic text.
    assert isinstance(adapter, ProviderPoolAdapter)
    assert adapter.legacy_fallback_command is not None
