# Loop 022R — Runner Runtime-Pool Activation Hotfix PRE-AUDIT

## Scope

Code-only audit. No `sigma_abc/` physics files are opened for
modification. No runner invocations are triggered in this audit.

The goal of this audit is to lay out the **specific seam** that
the Phase 5R-2 live run surfaced as broken: the runner's
`build_adapter()` reads reviewer pool config from the in-memory
`profile` dict (i.e., `profiles/*.yaml`) but the user keeps
`reviewer_provider_pools.<ReviewerRole>` in
`agents/runtime.local.yaml`. The runner therefore never sees
the pool and falls back to the legacy `runtime.command` path.

Loop 022R fixes that seam — without copying pool config into
profile YAML.

## Audit Table

| # | Question | Evidence | Disposition |
|---|----------|----------|-------------|
| 1 | Where does `build_adapter()` live? | [loop_engine/agent_runtime.py:533-616](loop_engine/agent_runtime.py:533). Reads `runtime = runtime_config_for_profile(profile, profile_name)` (which merges in `runtime.local.yaml`'s `runtime:` block); then reads `pool_reviewers = profile.get("reviewer_provider_pools")` from the in-memory profile dict only. | **Bug source.** Fix in this loop. |
| 2 | What does `runtime_config_for_profile()` do? | [loop_engine/agent_runtime.py:490-497](loop_engine/agent_runtime.py:490). Reads `profiles.<profile_name>.runtime` from `runtime.local.yaml` (if present), then top-level `runtime`, then `profile.get("runtime")`. It does NOT read `reviewer_provider_pools`. | Already half-merged. Extend it. |
| 3 | How does `run_autonomous_loop.py` load the profile? | `profile_config(profile)` at [scripts/run_autonomous_loop.py:110-114](scripts/run_autonomous_loop.py:110) calls `load_yaml(REPO_ROOT / "profiles" / f"{profile}.yaml")`. Returns the YAML mapping. | Profile YAML only. |
| 4 | How does `run_autonomous_loop.py` pass the profile to `build_adapter`? | [scripts/run_autonomous_loop.py:1539](scripts/run_autonomous_loop.py:1539): `adapter = build_adapter(profile, profile.get("profile", ""))`. The `profile_name` is the value of the YAML's `profile:` key (e.g. `sigma_abc_hypothesis_pre_ibp_throughput`). | Correct signature. No runner edit needed for the merge itself. |
| 5 | Where is `reviewer_provider_pools` visible today? | Only in two places: (a) [`scripts/probe_reviewer_providers.py::_read_pool_cfg`](scripts/probe_reviewer_providers.py:38) which walks `profiles.<name>.reviewer_provider_pools` from `runtime.local.yaml`; (b) [`loop_engine/agent_runtime.py::resolve_reviewer_pool_cfg`](loop_engine/agent_runtime.py:461) (a helper added in Loop 022 — *defined* but **never called** from `build_adapter`). | The helper exists; the integration just doesn't call it. |
| 6 | Why does probe see `openai_compatible_api` AVAILABLE but runner chooses legacy `command`? | `build_adapter` reads `pool_reviewers = profile.get("reviewer_provider_pools")`. The profile YAML for `sigma_abc_hypothesis_pre_ibp_throughput` does NOT carry a `reviewer_provider_pools` block (only `runtime.command` and `runtime.timeout_seconds`). The pool block lives in `agents/runtime.local.yaml::profiles.sigma_abc_hypothesis_pre_ibp_throughput.reviewer_provider_pools.ScientificMetaReviewer`, but `build_adapter` reads the profile dict only. So `pool_reviewers` is `None` → the legacy path is taken. | Confirmed gap. Fix in this loop. |
| 7 | How is `runtime.command` preserved as legacy fallback? | Inside `build_adapter`: `legacy_command = _expand_runtime_command(runtime.get("command", []))`. This is **already** computed from the merged runtime config (which DOES read `runtime.local.yaml`). So the legacy command path is correctly preserved; only the pool-resolution path is missing. | Preserved exactly. |
| 8 | Where does `invocation_summary.json` record `adapter` / `provider_attempts`? | `invoke_reviewer` (legacy path) and `ProviderPoolAdapter.invoke` both write `invocation_summary.json` with the same shape. Loop 022's `_write_invocation_summary` adds `provider_attempts` to the JSON. When the pool never runs, the field is absent (legacy command adapter doesn't know about it). | Once the merge is wired, the pool adapter writes `provider_attempts` correctly. |
| 9 | Where could API key values end up? | `command.txt`, `stdout.txt`, `stderr.txt`, `prompt.md`, `input_manifest.json`. Loop 022 wired `redact_secrets` into all of these (in both `ProviderPoolAdapter.invoke` and `_run_command_provider`). The legacy `CommandAgentAdapter.invoke` does NOT redact; the pool path is the safer one. | Switching to the pool path actually improves redaction coverage for 011's run. |
| 10 | Root hygiene state | `loop_config.json`, `AGENTS.md`, `README.md`, `REPO_CLASSIFICATION_PRE_AUDIT.md`, `REPO_REORGANIZATION_REPORT.md`. Five curated files. | Out-of-scope to change; runner must not regress this. |
| 11 | Pre-existing failure | `test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008` (human_signoff.yaml invariant). Pre-existing, Loop 020A-documented. | Out of scope (per spec). |
| 12 | The exact integration seam | `build_adapter` (single function, 4-line edit) plus a small merge helper inside `runtime_config_for_profile` (or a new sibling helper). Both are local to `loop_engine/agent_runtime.py`. Runner does not need an edit. | Local fix. |
| 13 | Profile YAML / runtime YAML separation | Profile YAML is policy: review lanes, required roles, autonomy flags, hard-stop mapping. Runtime YAML is environment: provider pool, enabled_env, api_key_env, model_env, base_url_env. Merging the pool config in `build_adapter` is a *read* merge — the profile dict is not modified, the runtime config is read fresh each call. | Merge read-only; no mutation. |
| 14 | Does any test exercise this seam today? | `tests/test_loop022_runner_provider_pool_integration.py::test_build_adapter_selects_provider_pool_when_pool_configured` passes the pool via the in-memory `profile` dict directly. It does not exercise the `runtime.local.yaml` merge. | NEW tests needed in Loop 022R. |
| 15 | Probe vs runner source | Probe walks `runtime.local.yaml::profiles.<name>.reviewer_provider_pools.<role>`. Runner will, after the fix, read the same path via `resolve_reviewer_pool_cfg(profile_name, reviewer_role)`. Both reach the same source. | Confirmed. Same source → same answer → no probe/runner drift. |

## Single-seam fix

```python
# in loop_engine/agent_runtime.py::build_adapter
runtime = runtime_config_for_profile(profile, profile_name)
# ... existing legacy_command / adapter resolution ...

# NEW: pull the runtime-local pool mapping INTO the decision,
# without mutating the in-memory profile dict.
pool_cfg_from_runtime: dict[str, Any] = {}
if require_real_invocation:
    runtime_pool_profile = resolve_reviewer_pool_cfg(
        profile_name=profile_name,
        reviewer_role="*",   # role-agnostic, will be resolved at invoke()
    )
    if isinstance(runtime_pool_profile, dict):
        pool_cfg_from_runtime = runtime_pool_profile

# Precedence: profile-level block > runtime-local block.
pool_reviewers = profile.get("reviewer_provider_pools")
if not isinstance(pool_reviewers, dict) or not pool_reviewers:
    pool_reviewers = pool_cfg_from_runtime if pool_cfg_from_runtime else None

if pool_reviewers and require_real_invocation:
    # Existing path
    return ProviderPoolAdapter(
        pool_cfg=pool_reviewers,
        timeout_seconds=int(runtime.get("timeout_seconds", 900)),
        legacy_fallback_command=legacy_command,
        legacy_fallback_adapter_name=legacy_adapter_name,
    )
```

Also update `resolve_reviewer_pool_cfg` to accept a wildcard role
(it currently expects an exact role string). The helper will
return either:

- the single role-specific block when `reviewer_role="<Role>"`
- the full profile pool mapping when `reviewer_role="*"`

This is the minimum needed to activate the pool from
`runtime.local.yaml`. No runner edits.

## Hard Constraints Preserved

- `sigma_abc/` physics untouched.
- 012C / 013 / IBP / total derivative NOT started.
- `pre_run_gate`, `freeze_preconditions`, `completion_matrix`,
  `human_signoff` not modified.
- `human_signoff.yaml` NOT auto-created.
- Real API keys NEVER written to any file or report.
- Permanent caveat preserved:
  `DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.`

## What Step 4 will produce

A new test file `tests/test_loop022r_runner_runtime_pool_activation.py`
that places `agents/runtime.local.yaml` content into a fixture
tmp_path, monkey-patches `REPO_ROOT`, and proves:

- `build_adapter` returns `ProviderPoolAdapter` when the pool
  config is only in `runtime.local.yaml` (and absent from the
  profile dict).
- `build_adapter` preserves `runtime.command` as
  `legacy_fallback_command`.
- `build_adapter` returns `CommandAgentAdapter` (or
  `CodexSubagentAdapter`) when no pool is configured.
- `ProviderPoolAdapter.invoke` writes `provider_attempts` and
  `selected_provider` to `invocation_summary.json`.

These are new tests, not replacements for the Loop 022 ones.

## Out of Scope (deferred)

- Profile YAML gaining a pool config (deprecated by spec —
  pool config lives in runtime.local.yaml only).
- Changing `freeze_checkpoint` to honour
  `human_signoff.auto_for_tests`. This is the second Phase 5R-2
  follow-up; **not** in this loop.
- Auto-resolving `XXXCenterProjectionRegression` /
  `Stage010PairFusionRegression` blocking items. **Not** in this loop.

## Next step

Step 1-3: implement the merge in
`loop_engine/agent_runtime.py::build_adapter` and adjust
`resolve_reviewer_pool_cfg` to accept a wildcard role.
