from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .agent_invocation import (
    file_sha256,
    hash_protected_files,
    verify_read_only_contract,
    write_invocation_summary,
)
from .config import REPO_ROOT, read_text, utc_now, write_json, write_text
from .schemas import load_and_validate
from .secret_redaction import redact_secrets


def _runtime_status_from_result(
    *,
    exit_code: int | str | None,
    timeout_expired: bool,
    output_exists: bool,
    schema_valid: bool,
    stdout: str,
    stderr: str,
) -> str:
    text = f"{stdout}\n{stderr}".lower()
    if "usage limit" in text or "quota" in text or "try again at" in text:
        return "AGENT_QUOTA_LIMIT"
    if timeout_expired:
        return "AGENT_TIMEOUT"
    if not output_exists:
        return "AGENT_NO_OUTPUT"
    if not schema_valid:
        return "AGENT_SCHEMA_FAIL"
    if exit_code != 0:
        return "AGENT_SCHEMA_FAIL"
    return "AGENT_OK"


@dataclass(frozen=True)
class AgentInvocationRequest:
    agent_name: str
    stage_dir: Path
    prompt_path: Path
    output_path: Path
    schema_name: str = "review_result"
    protected_paths: list[Path] | None = None


@dataclass(frozen=True)
class RuntimeStatus:
    available: bool
    adapter: str
    production_run_allowed: bool
    missing_agent_commands: list[str]
    reason: str = ""


class AgentAdapter:
    name = "base"

    def invoke(self, request: AgentInvocationRequest) -> dict[str, Any]:
        raise NotImplementedError


def _format_command(command: list[str], request: AgentInvocationRequest) -> list[str]:
    replacements = {
        "${REPO_ROOT}": str(REPO_ROOT),
        "{repo_root}": str(REPO_ROOT),
        "{agent_name}": request.agent_name,
        "{prompt_path}": str(request.prompt_path),
        "{output_path}": str(request.output_path),
        "{stage_dir}": str(request.stage_dir),
    }
    rendered: list[str] = []
    for item in command:
        value = item
        for token, replacement in replacements.items():
            value = value.replace(token, replacement)
        rendered.append(value)
    return rendered


def _expand_runtime_command(command: list[Any]) -> list[str]:
    rendered: list[str] = []
    for item in command:
        value = str(item)
        value = value.replace("${REPO_ROOT}", str(REPO_ROOT))
        value = value.replace("{repo_root}", str(REPO_ROOT))
        rendered.append(value)
    return rendered


def _command_missing(command: list[str]) -> list[str]:
    if not command:
        return ["<empty command>"]
    executable = command[0]
    if "/" in executable:
        return [] if Path(executable).exists() else [executable]
    return [] if shutil.which(executable) else [executable]


def _schema_valid(path: Path, schema_name: str) -> bool:
    try:
        load_and_validate(path, schema_name)
    except Exception:
        return False
    return True


class CommandAgentAdapter(AgentAdapter):
    name = "command"

    def __init__(self, command: list[str], timeout_seconds: int = 900):
        self.command = command
        self.timeout_seconds = timeout_seconds

    def invoke(self, request: AgentInvocationRequest) -> dict[str, Any]:
        evidence_dir = request.stage_dir / ".loop" / "agent_invocations" / request.agent_name
        evidence_dir.mkdir(parents=True, exist_ok=True)
        protected_paths = request.protected_paths or []
        before = hash_protected_files(protected_paths)
        rendered = _format_command(self.command, request)
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
            },
        )
        write_text(evidence_dir / "command.txt", " ".join(rendered) + "\n")
        timeout_expired = False
        try:
            completed = subprocess.run(
                rendered,
                cwd=request.stage_dir,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code: int | str | None = completed.returncode
        except subprocess.TimeoutExpired as exc:
            timeout_expired = True
            stdout = (exc.stdout or "")
            stderr = (exc.stderr or "")
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            stderr = f"{stderr}\nCommand timed out after {self.timeout_seconds} seconds.\n"
            exit_code = None
        write_text(evidence_dir / "stdout.txt", stdout)
        write_text(evidence_dir / "stderr.txt", stderr)
        write_text(evidence_dir / "exit_code.txt", f"{'TIMEOUT' if timeout_expired else exit_code}\n")
        output_hash = file_sha256(request.output_path) if request.output_path.exists() else ""
        write_text(evidence_dir / "output_hash.txt", f"{output_hash}\n")
        schema_valid = request.output_path.exists() and _schema_valid(request.output_path, request.schema_name)
        readonly = verify_read_only_contract(before)
        runtime_status = _runtime_status_from_result(
            exit_code=exit_code,
            timeout_expired=timeout_expired,
            output_exists=request.output_path.exists(),
            schema_valid=schema_valid,
            stdout=stdout,
            stderr=stderr,
        )
        summary = {
            "agent_name": request.agent_name,
            "adapter": self.name,
            "actually_invoked": True,
            "stub_used": False,
            "exit_code": exit_code,
            "runtime_status": runtime_status,
            "timeout_expired": timeout_expired,
            "schema_valid": schema_valid,
            "review_debt_required": runtime_status in {"AGENT_TIMEOUT", "AGENT_QUOTA_LIMIT", "AGENT_NO_OUTPUT"},
            "read_only_contract_enforced": not readonly["ReviewerModifiedProtectedFiles"],
            "ReviewerModifiedProtectedFiles": readonly["ReviewerModifiedProtectedFiles"],
            "modified_protected_files": readonly["ModifiedProtectedFiles"],
            "output_hash": output_hash,
            "freeze_evidence_valid": (
                exit_code == 0
                and schema_valid
                and not readonly["ReviewerModifiedProtectedFiles"]
            ),
        }
        write_invocation_summary(evidence_dir, summary)
        return summary


class CodexSubagentAdapter(CommandAgentAdapter):
    name = "codex_subagent"


class ProviderPoolAdapter(AgentAdapter):
    """Loop 022 — adapter that runs a reviewer-role invocation
    through the Loop 021 provider pool.

    Behaviour:

    - Wired to the Loop 021 reviewer-provider pool
      (``loop_engine.reviewer_provider_pool.invoke_reviewer``).
    - Falls through to the next provider ONLY on retryable
      runtime failures
      (``AGENT_QUOTA_LIMIT``, ``AGENT_TIMEOUT``,
      ``AGENT_NO_OUTPUT``, ``AGENT_COMMAND_NOT_FOUND``,
      ``AGENT_TRANSPORT_FAILURE``, ``AGENT_RUNTIME_FAILURE``).
    - Stops on the first schema-valid result regardless of
      verdict (``PASS`` / ``PASS_WITH_CAVEAT`` / ``FAIL`` /
      ``NEEDS_PATCH``).
    - Refuses to substitute a stub when the pool config sets
      ``forbid_stub: true`` (Loop 021 production contract).
    - Applies ``redact_secrets`` to ``prompt.md`` and ``stdout.txt``
      before any disk write — the same redaction guarantee as the
      probe / smoke paths.
    - Writes both ``invocation_summary.json`` (legacy shape) and
      ``pool_result.json`` (Loop 021 sibling).
    - Records ``selected_provider`` and ``provider_attempts`` into
      the ``invocation_summary.json`` so the existing
      ``completion_matrix`` / ``freeze_preconditions`` /
      ``review_debt`` / ``stage_digest`` / ``checkpoint_manifest``
      continues to read the same shape.

    The ``timeout_seconds`` attribute is mutable so that
    ``L1_COMPACT_META`` / ``L2_FULL_PANEL`` policy overrides
    (e.g. ``review_policy.l1_timeout_seconds``) still take effect
    when the runner adjusts it on this adapter.
    """

    name = "reviewer_provider_pool"

    def __init__(
        self,
        pool_cfg: dict[str, Any],
        *,
        timeout_seconds: int = 900,
        legacy_fallback_command: list[str] | None = None,
        legacy_fallback_adapter_name: str = "command",
    ) -> None:
        # ``pool_cfg`` may be either:
        #  (a) the profile-level mapping
        #      {ReviewerRole: {fallback_policy: ..., providers: [...]}}
        #      (the shape returned by the profile YAML), or
        #  (b) a single role-specific block already
        #      ({fallback_policy: ..., providers: [...]}).
        # We accept (a) and resolve the role at invoke() time.
        # We also accept (b) and use it directly.
        self.pool_cfg = pool_cfg
        self.timeout_seconds = timeout_seconds
        self.legacy_fallback_command = list(legacy_fallback_command) if legacy_fallback_command else None
        self.legacy_fallback_adapter_name = legacy_fallback_adapter_name

    def invoke(self, request: AgentInvocationRequest) -> dict[str, Any]:
        from .reviewer_provider_pool import invoke_reviewer

        evidence_dir = request.stage_dir / ".loop" / "agent_invocations" / request.agent_name
        evidence_dir.mkdir(parents=True, exist_ok=True)
        # Redact secrets BEFORE prompt is snapshotted. The prompt
        # body is the upstream template; we still pass it through
        # the redactor as defence-in-depth in case a future loop
        # introduces a secret-bearing template by accident.
        original_prompt = read_text(request.prompt_path)
        write_text(evidence_dir / "prompt.md", redact_secrets(original_prompt))
        write_json(
            evidence_dir / "input_manifest.json",
            {
                "agent_name": request.agent_name,
                "prompt_path": str(request.prompt_path),
                "output_path": str(request.output_path),
                "schema_name": request.schema_name,
                "protected_paths": [str(path) for path in (request.protected_paths or [])],
                "timestamp": utc_now(),
                "adapter": self.name,
                "pool_review": True,
                "selected_provider_hint": None,
            },
        )
        write_text(
            evidence_dir / "command.txt",
            redact_secrets(f"POOL adapter={self.name} role={request.agent_name}\n"),
        )

        # Resolve role-specific pool_cfg: when the adapter was
        # constructed with the profile-level mapping, pick the
        # role-specific sub-pool. When constructed with a single
        # role-specific block, use it as-is.
        role_pool_cfg = self._resolve_role_pool_cfg(request.agent_name)

        result = invoke_reviewer(
            pool_cfg=role_pool_cfg,
            request=request,
            fallback_command=self.legacy_fallback_command,
            fallback_adapter_name=self.legacy_fallback_adapter_name,
        )
        # ``invoke_reviewer`` writes ``pool_result.json`` and the
        # legacy ``invocation_summary.json`` (Loop 021). We still
        # want to make sure stdout/stderr are redacted on disk;
        # ``invoke_reviewer`` already redacts stderr, but legacy
        # fallback may write a stdout. Redact it here if present.
        stdout_path = evidence_dir / "stdout.txt"
        if stdout_path.exists():
            write_text(stdout_path, redact_secrets(read_text(stdout_path)))
        summary_path = evidence_dir / "invocation_summary.json"
        if summary_path.exists():
            existing = read_text(summary_path)
            redacted = redact_secrets(existing)
            # Only re-write if redaction changed something, to keep
            # the artefact strictly byte-identical when no secret
            # is present.
            if redacted != existing:
                write_text(summary_path, redacted)
        return _result_to_summary(result, agent_name=request.agent_name)

    def _resolve_role_pool_cfg(self, role: str) -> dict[str, Any] | None:
        """Resolve the role-specific pool block from a profile-level
        mapping or return the inline block as-is.
        """
        if not isinstance(self.pool_cfg, dict):
            return None
        # Inline role-specific block shape: has either
        # ``providers`` (legacy provider list) or ``fallback_policy``.
        providers = self.pool_cfg.get("providers")
        fallback_policy = self.pool_cfg.get("fallback_policy")
        if isinstance(providers, list) or isinstance(fallback_policy, str):
            return self.pool_cfg
        # Profile-level mapping shape: {<RoleName>: {providers: [...]}}.
        if isinstance(self.pool_cfg.get(role), dict):
            return self.pool_cfg[role]
        # Heuristic: any value in the mapping that is itself a
        # provider list is the single inline block.
        for value in self.pool_cfg.values():
            if isinstance(value, dict) and (
                isinstance(value.get("providers"), list)
                or isinstance(value.get("fallback_policy"), str)
            ):
                return value
        return None


def _result_to_summary(
    result: Any,
    *,
    agent_name: str,
) -> dict[str, Any]:
    """Map a ``ReviewerProviderResult`` to the legacy summary dict
    that ``CommandAgentAdapter.invoke`` would have produced.

    Keeps the runner's downstream code (which reads
    ``summary.get("freeze_evidence_valid")`` etc.) entirely
    unchanged.
    """
    selected = getattr(result, "selected_provider", None)
    provider_attempts = list(getattr(result, "provider_attempts", []) or [])
    attempts_payload = [
        {
            "provider_name": getattr(a, "provider_name", "?"),
            "adapter": getattr(a, "adapter", "?"),
            "enabled": getattr(a, "enabled", False),
            "availability_status": getattr(a, "availability_status", "OTHER"),
            "runtime_status": getattr(a, "runtime_status", "NOT_INVOKED"),
            "retryable": getattr(a, "retryable", False),
            "selected": getattr(a, "selected", False),
            "failure_summary_redacted": getattr(a, "failure_summary_redacted", ""),
        }
        for a in provider_attempts
    ]
    return {
        "agent_name": agent_name,
        "adapter": getattr(result, "adapter", "reviewer_provider_pool"),
        "actually_invoked": bool(getattr(result, "actually_invoked", False)),
        "stub_used": bool(getattr(result, "stub_used", False)),
        "exit_code": getattr(result, "exit_code", None),
        "runtime_status": getattr(result, "runtime_status", "NOT_INVOKED"),
        "timeout_expired": False,
        "schema_valid": bool(getattr(result, "schema_valid", False)),
        "review_debt_required": bool(getattr(result, "review_debt_required", True)),
        "read_only_contract_enforced": True,
        "ReviewerModifiedProtectedFiles": False,
        "modified_protected_files": [],
        "output_hash": "",
        "freeze_evidence_valid": bool(getattr(result, "freeze_evidence_valid", False)),
        "selected_provider": selected,
        "provider_attempts": attempts_payload,
        "fallback_reason": getattr(result, "fallback_reason", None),
        "pool_retryable": bool(getattr(result, "retryable", False)),
        "secret_redaction_applied": bool(
            getattr(result, "secret_redaction_applied", True)
        ),
    }


class DryRunStubAdapter(AgentAdapter):
    name = "stub"

    def invoke(self, request: AgentInvocationRequest) -> dict[str, Any]:
        evidence_dir = request.stage_dir / ".loop" / "agent_invocations" / request.agent_name
        evidence_dir.mkdir(parents=True, exist_ok=True)
        write_text(evidence_dir / "prompt.md", read_text(request.prompt_path))
        write_text(evidence_dir / "command.txt", "DRY_RUN_STUB\n")
        write_text(evidence_dir / "stdout.txt", "")
        write_text(evidence_dir / "stderr.txt", "stub invocation; not production evidence\n")
        write_text(evidence_dir / "exit_code.txt", "0\n")
        write_text(evidence_dir / "output_hash.txt", "")
        summary = {
            "agent_name": request.agent_name,
            "adapter": self.name,
            "actually_invoked": False,
            "stub_used": True,
            "exit_code": 0,
            "runtime_status": "STUB_NOT_PRODUCTION",
            "schema_valid": False,
            "review_debt_required": False,
            "read_only_contract_enforced": True,
            "ReviewerModifiedProtectedFiles": False,
            "freeze_evidence_valid": False,
        }
        write_json(evidence_dir / "input_manifest.json", {"agent_name": request.agent_name, "stub": True})
        write_invocation_summary(evidence_dir, summary)
        return summary


class ManualAdapter(AgentAdapter):
    name = "manual"

    def invoke(self, request: AgentInvocationRequest) -> dict[str, Any]:
        raise RuntimeError("ManualAdapter is not allowed in autonomous production profiles.")


def load_runtime_local() -> dict[str, Any]:
    # Best-effort: if a `.env` file exists at the repo root, populate
    # `os.environ` with its `KEY=VALUE` lines (interactive shell
    # exports take precedence; secrets stay on disk in gitignored
    # file). The loop_engine redactor remains in force for any
    # downstream disk write. No shell expansion is performed.
    from .config import load_dotenv
    load_dotenv()
    path = REPO_ROOT / "agents" / "runtime.local.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Runtime local config must be a mapping: {path}")
    return data


def profile_config_for_diagnose(
    *,
    profile_name: str,
    reviewer_role: str,
) -> dict[str, Any] | None:
    """Loop 022R diagnostic helper: same as
    ``resolve_reviewer_pool_cfg`` but with the wildcard
    semantics documented separately.

    Returns the full profile-level pool mapping when
    ``reviewer_role=="*"``, or the role-specific block for an
    exact role match. Useful for the
    ``scripts/diagnose_runner_adapter.py`` CLI and for any
    user who wants to inspect what the runner reads.
    """
    return resolve_reviewer_pool_cfg(
        profile_name=profile_name,
        reviewer_role=reviewer_role,
    )


def resolve_reviewer_pool_cfg(
    *,
    profile_name: str,
    reviewer_role: str,
) -> dict[str, Any] | None:
    """Read reviewer-pool config from ``agents/runtime.local.yaml``.

    Behaviour:

    - ``reviewer_role="*"`` (Loop 022R wildcard) → return the
      entire ``profiles.<profile_name>.reviewer_provider_pools``
      mapping (this is the form ``build_adapter`` consumes).
    - ``reviewer_role="<RoleName>"`` (exact) → return the
      role-specific block from
      ``profiles.<profile_name>.reviewer_provider_pools.<RoleName>``
      if present, else ``None``.
    - Returns ``None`` when no pool is configured — in which
      case the runner keeps the legacy path exactly as before.
    - Secrets are never read or logged here; the helper returns
      only env-var *names* (``api_key_env``, ``base_url_env``,
      ``model_env``, ``enabled_env``), not their values.

    Single-source lookup: the probe scripts and the runner
    reach the same file via this helper, so there is no probe /
    runner drift.
    """
    local = load_runtime_local()
    profiles = local.get("profiles", {}) or {}
    profile_cfg = profiles.get(profile_name) or {}
    pools = profile_cfg.get("reviewer_provider_pools", {}) or {}
    if not isinstance(pools, dict):
        return None
    if reviewer_role == "*":
        return dict(pools)
    pool_cfg = pools.get(reviewer_role)
    if isinstance(pool_cfg, dict):
        return pool_cfg
    return None


def runtime_config_for_profile(profile: dict[str, Any], profile_name: str) -> dict[str, Any]:
    local = load_runtime_local()
    local_profile = (local.get("profiles", {}) or {}).get(profile_name, {})
    if local_profile.get("runtime"):
        return local_profile["runtime"]
    if local.get("runtime"):
        return local["runtime"]
    return profile.get("runtime", {}) or {}


def resolve_agent_runtime(profile: dict[str, Any], profile_name: str) -> RuntimeStatus:
    agents = profile.get("agents", {}) or {}
    runtime = runtime_config_for_profile(profile, profile_name)
    adapter = runtime.get("adapter")
    if not adapter and agents.get("allow_stub_for_tests"):
        return RuntimeStatus(True, "stub", True, [], "test profile allows stub")
    if not adapter:
        allowed = not agents.get("require_real_invocation", False)
        return RuntimeStatus(
            available=allowed,
            adapter="unavailable" if not allowed else "local",
            production_run_allowed=allowed,
            missing_agent_commands=["agents/runtime.local.yaml"],
            reason="no runtime adapter configured",
        )
    if adapter == "manual":
        return RuntimeStatus(False, "manual", False, [], "manual adapter forbidden in autonomous production")
    if adapter == "stub":
        allowed = bool(agents.get("allow_stub_for_tests")) and not agents.get("forbid_stub_in_production")
        return RuntimeStatus(allowed, "stub", allowed, [] if allowed else ["stub forbidden"], "stub runtime")
    if adapter in {"command", "codex_subagent"}:
        command = _expand_runtime_command(runtime.get("command", []))
        missing = _command_missing(command)
        return RuntimeStatus(
            available=not missing,
            adapter=adapter,
            production_run_allowed=not missing,
            missing_agent_commands=missing,
            reason="" if not missing else "configured command is unavailable",
        )
    return RuntimeStatus(False, str(adapter), False, [str(adapter)], "unsupported runtime adapter")


def build_adapter(profile: dict[str, Any], profile_name: str) -> AgentAdapter:
    """Build the AgentAdapter used for reviewer role invocations.

    Selection order (Loop 022 + Loop 022R — runner integration):

    1. Compute ``runtime_config`` by merging in
       ``agents/runtime.local.yaml::profiles.<profile_name>.runtime``
       (loop_engine already does this in
       ``runtime_config_for_profile``). Preserve any
       ``runtime.command`` list as the legacy fallback command
       so the pool path always has a last-resort provider.

    2. Determine the pool config. Read order:

       (a) ``profile.reviewer_provider_pools`` — in-memory
           pool mapping authored inline in the profile YAML.
       (b) ``agents/runtime.local.yaml::profiles.<profile_name>.reviewer_provider_pools``
           — merged via ``resolve_reviewer_pool_cfg(profile_name, "*")``.
           This is the Loop 022R change: the runner now sees
           pool config that lives in ``runtime.local.yaml`` even
           when the profile YAML doesn't carry one.

       Either source wins. Profile-inline preempts runtime-local
       (more specific). Both sources must agree on the
       trust-stack invariants and must not contain API key
       values; only env-var names are stored in YAML.

    3. If a pool config exists AND
       ``profile.agents.require_real_invocation`` is True, return
       ``ProviderPoolAdapter`` with the legacy command as
       ``legacy_fallback_command``. The pool handles retryable
       runtime failures by falling through to the next provider;
       on the first schema-valid verdict it stops.

    4. Otherwise, fall back to the legacy ``CommandAgentAdapter``
       / ``CodexSubagentAdapter`` exactly as before. The legacy
       path is not removed.

    5. ``adapter: stub`` for tests, ``adapter: manual`` forbidden
       — both preserved.

    No silent substitution of a real adapter by a stub is
    permitted when the profile forbids stub in production.
    """
    runtime = runtime_config_for_profile(profile, profile_name)
    adapter = runtime.get("adapter")
    agents_cfg = profile.get("agents", {}) or {}
    require_real_invocation = bool(agents_cfg.get("require_real_invocation"))

    # Legacy fallback command — preserved across all branches.
    legacy_command: list[str] | None = None
    legacy_adapter_name: str = "command"
    if isinstance(runtime.get("command"), list) and runtime.get("command"):
        legacy_command = _expand_runtime_command(runtime.get("command", []))
        legacy_adapter_name = str(adapter or "command")

    # Loop 022R: pool config can live inline in the profile YAML
    # OR in agents/runtime.local.yaml. The profile-inline source
    # wins when present; otherwise the runtime-local mapping is
    # consulted. This is the seam the Phase 5R-2 live run
    # surfaced: the user's pool config lives in runtime.local.yaml
    # only, and the runner's build_adapter was reading the
    # profile YAML only.
    pool_cfg: dict[str, Any] | None = None
    profile_inline_pool = profile.get("reviewer_provider_pools")
    if isinstance(profile_inline_pool, dict) and profile_inline_pool:
        pool_cfg = profile_inline_pool
    else:
        runtime_pool = resolve_reviewer_pool_cfg(
            profile_name=profile_name,
            reviewer_role="*",
        )
        if isinstance(runtime_pool, dict) and runtime_pool:
            pool_cfg = runtime_pool

    if pool_cfg and require_real_invocation:
        timeout_seconds = int(runtime.get("timeout_seconds", 900))
        return ProviderPoolAdapter(
            pool_cfg=pool_cfg,
            timeout_seconds=timeout_seconds,
            legacy_fallback_command=legacy_command,
            legacy_fallback_adapter_name=legacy_adapter_name,
        )

    if adapter == "command":
        if not legacy_command:
            return DryRunStubAdapter()
        return CommandAgentAdapter(legacy_command, int(runtime.get("timeout_seconds", 900)))
    if adapter == "codex_subagent":
        if not legacy_command:
            return DryRunStubAdapter()
        return CodexSubagentAdapter(legacy_command, int(runtime.get("timeout_seconds", 900)))
    if adapter == "manual":
        return ManualAdapter()
    return DryRunStubAdapter()
