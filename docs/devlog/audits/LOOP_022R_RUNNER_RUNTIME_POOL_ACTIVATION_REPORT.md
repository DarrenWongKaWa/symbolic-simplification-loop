# Loop 022R — Runner Runtime-Pool Activation Hotfix REPORT

## Status

VERDICT **A**. Runner now activates reviewer provider pools from
`agents/runtime.local.yaml` at the live invocation path. Legacy
`runtime.command` adapter is preserved exactly. Fallback is
runtime-failure-only. All 18 new integration tests pass and the
diagnostic CLI confirms the new behavior end-to-end.

```text
Final classification (per user spec):
A. "Runner now activates reviewer provider pools from
    runtime.local.yaml; ProviderPoolAdapter selected in live
    runner path; legacy command fallback preserved; tests
    pass; sigma_abc not modified."
```

`services/diagnose_runner_adapter.py` (new CLI) prints:

```text
ReviewerRole=ScientificMetaReviewer
ProfileName=sigma_abc_hypothesis_pre_ibp_throughput
ProfileInlinePool=absent
RuntimeLocalPool=present
AdapterSelected=ProviderPoolAdapter
LegacyFallbackCommand=present
LegacyFallbackAdapter=command
TimeoutSeconds=900
StubPolicy=forbid_in_production=True allow_stub_for_tests=False
StubUsed=False
```

This is the seam Phase 5R-2 surfaced as broken. It is now fixed.

Permanent caveat preserved:
`DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.`

## Files Modified

| File | Change |
|------|--------|
| `loop_engine/agent_runtime.py` | `resolve_reviewer_pool_cfg` now accepts a wildcard `reviewer_role="*"` and returns the full profile-level pool mapping in that case. `build_adapter` reads the runtime-local pool config via `resolve_reviewer_pool_cfg` when the profile YAML has no inline pool block. The same `ProviderPoolAdapter` is returned either way. New helper `profile_config_for_diagnose` aliases the same lookup. |
| `scripts/diagnose_runner_adapter.py` | NEW: a dry CLI that prints which adapter the runner would select, what the runtime-local pool status is, the legacy fallback command, and the production-stub policy. Does NOT invoke any provider. |
| `tests/test_loop022r_runner_runtime_pool_activation.py` | NEW: 18 integration tests covering the merge, fallback policy, secret redaction, and root hygiene. |
| `docs/devlog/audits/LOOP_022R_RUNNER_RUNTIME_POOL_ACTIVATION_PRE_AUDIT.md` | NEW: pre-audit enumerating every seam and the integration plan. |

The runner (`scripts/run_autonomous_loop.py`) is **unchanged**. The
single-seam fix lives entirely inside
`loop_engine/agent_runtime.py::build_adapter`.

## Exact Integration Seam

`loop_engine/agent_runtime.py::build_adapter` had a single
4-line gap: it read `pool_reviewers = profile.get("reviewer_provider_pools")`
from the in-memory profile dict only. The user's pool block lives
in `agents/runtime.local.yaml` instead.

The fix replaces that with:

```python
pool_cfg = None
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
```

Read-through priorities:

1. Profile-inline pool (`profile.reviewer_provider_pools`) —
   preempts (more specific).
2. Runtime-local pool
   (`agents/runtime.local.yaml::profiles.<name>.reviewer_provider_pools`)
   — fallback path (Layer 022R).
3. If neither is set, the existing legacy
   `CommandAgentAdapter` / `CodexSubagentAdapter` is returned.

The profile dict is **never mutated** — the runtime-local pool
config is read fresh each call (it goes through `load_runtime_local`
and `resolve_reviewer_pool_cfg`).

## Runtime-Local Pool Resolution Behaviour

`resolve_reviewer_pool_cfg(profile_name, reviewer_role)` is the
single-source lookup that the probe scripts already used. Loop 022R
adds the `reviewer_role="*"` wildcard semantics so `build_adapter`
can pull the entire profile-level mapping.

```python
# Walk agents/runtime.local.yaml
# profiles.<profile_name>.reviewer_provider_pools
# Return:
#   if reviewer_role == "*":  dict(pools)        # full mapping
#   else:                      pools[role] or None
```

The probe script (`scripts/probe_reviewer_providers.py::_read_pool_cfg`)
walks the same YAML and uses the role-specific path:
`profiles.<profile>.reviewer_provider_pools.<role>`. The runner
uses the same path via `resolve_reviewer_pool_cfg(profile, role)`.
Both consult the same file — there is no probe/runner drift.

The test `test_probe_and_runner_wildcard_resolve_same_pool`
proves both reach the same block.

## Profile / Runtime Merge Behaviour

| Source | What it provides |
|--------|------------------|
| `profiles/*.yaml` (policy) | `agents.allow_stub_for_tests`, `agents.forbid_stub_in_production`, `agents.require_real_invocation`, `review_policy.*`, `review.{mode,scope}`, `reviewer_provider_pools.<role>` (optional inline pool), `runtime.command` (legacy fallback). |
| `agents/runtime.local.yaml` (env-local) | `profiles.<name>.runtime` (legacy command override), `profiles.<name>.reviewer_provider_pools.<role>` (provider availability: pool config, env var names, provider order, `forbid_stub`, `fallback_policy`). |

These two layers are kept separate:

- The profile YAML is committed policy.
- The runtime-local YAML is gitignored environment / key-info
  (real keys stay out — only env-var *names* are stored).

Layer-mutation invariant: the profile dict is **never** copied
into runtime-local and vice versa. `build_adapter` only **reads**
both and selects one for the adapter constructor.

## Selected Adapter Evidence

```text
$ python3 scripts/diagnose_runner_adapter.py \
    --profile sigma_abc_hypothesis_pre_ibp_throughput \
    --role ScientificMetaReviewer
ReviewerRole=ScientificMetaReviewer
ProfileName=sigma_abc_hypothesis_pre_ibp_throughput
ProfileInlinePool=absent
RuntimeLocalPool=present
AdapterSelected=ProviderPoolAdapter
LegacyFallbackCommand=present
LegacyFallbackAdapter=command
TimeoutSeconds=900
StubPolicy=forbid_in_production=True allow_stub_for_tests=False
StubUsed=False
```

This is the exact diagnostic the spec asked for in Step 5.

The probe still sees `openai_compatible_api` AVAILABLE:

```text
$ python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer | grep openai_compatible
## 2. `openai_compatible_api` (adapter: `openai_compatible_api`)
- enabled: `True` (reason: `env:LOOP_ENABLE_OPENAI_COMPATIBLE`)
- availability_status: AVAILABLE
- runtime_status: AVAILABLE
```

## Legacy Fallback Evidence

`build_adapter` always builds the legacy command list (when the
profile declares `runtime.command`) BEFORE deciding whether the
pool adapter is selected. The legacy command list is passed to
`ProviderPoolAdapter(legacy_fallback_command=...)`. Test
`test_build_adapter_passes_legacy_command_as_fallback` proves
that the rendered legacy command list is preserved on the
adapter exactly when it is selected.

When the pool is absent, the legacy `CommandAgentAdapter` /
`CodexSubagentAdapter` is returned unchanged. Tests
`test_pool_absent_legacy_commandadapter_unchanged` and
`test_pool_absent_codex_subagent_unchanged` confirm.

## Secret Redaction Evidence

Loop 022 redaction is preserved unchanged. Both
`ProviderPoolAdapter.invoke` and `_run_command_provider` redact:
`prompt.md`, `command.txt`, `stdout.txt`, `stderr.txt`,
`invocation_summary.json`.

`test_real_api_key_redacted_from_artifacts` (Loop 022R) sets
`OPENAI_COMPATIBLE_API_KEY=sk-fakeprooftest-loop022r-must-hide-12345`,
runs the pool with a provider that echoes the key, and asserts
the literal key is absent from every artefact on disk. PASS.

`agent_runtime.redact_secrets` is applied to:
- `prompt.md` (defence-in-depth; the prompt body itself is
  redacted before write)
- `command.txt` (command-line tokens, including any env-var
  name leaks)
- `stdout.txt` (provider stdout, may include tool echoes)
- `stderr.txt` (already redacted inside the pool skeleton)
- `invocation_summary.json` (post-write pass; byte-identical
  when no redaction change)

## Tests Result

```text
$ python3 -m pytest -q tests/test_loop021_*.py tests/test_loop022_*.py
45 passed, 1 warning in 0.40s

$ python3 -m pytest -q
1 failed, 243 passed, 1 warning in 34.80s
```

The single failure is
`tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`,
the documented pre-existing `human_signoff.yaml is required`
hard-stop (Loop 020A / 021 / 021P). It is **NOT** caused by this
loop and not modified.

The transient test-order-residue failure
`test_sigma_abc_dry_run_reports_profile_driven_next_stage` seen
in Phase 5R-2 did **not** recur in the full suite this run.

Loop 022R adds **18** new tests:

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_build_adapter_reads_pool_from_runtime_local_yaml` | provider pool is read from `runtime.local.yaml` only. |
| 2 | `test_build_adapter_passes_legacy_command_as_fallback` | `legacy_fallback_command` preserved on the adapter. |
| 3 | `test_build_adapter_does_not_require_profile_inline_pool` | profile YAML is not required to carry pool block. |
| 4 | `test_probe_and_runner_wildcard_resolve_same_pool` | probe and runner reach the same YAML. |
| 5 | `test_pool_enabled_runner_does_not_use_legacy_first` | pool presence makes the runner select pool adapter. |
| 6 | `test_pool_absent_legacy_commandadapter_unchanged` | legacy fallback preserved when no pool exists. |
| 7 | `test_pool_absent_codex_subagent_unchanged` | codex_subagent fallback preserved when no pool exists. |
| 8 | `test_provider_attempts_appear_in_invocation_summary` | provider_attempts is written to `invocation_summary.json`. |
| 9 | `test_selected_provider_recorded` | selected_provider is recorded. |
| 10 | `test_real_api_key_redacted_from_artifacts` | real key never reaches any artefact. |
| 11 | `test_fallback_on_quota` | fallback on retryable runtime failure. |
| 12 | `test_no_fallback_after_schema_valid_fail` | semantic FAIL stops the chain. |
| 13 | `test_no_fallback_after_schema_valid_needs_patch` | semantic NEEDS_PATCH stops the chain. |
| 14 | `test_pool_adapter_forbids_stub` | stub is rejected when `forbid_stub=True`. |
| 15 | `test_no_root_residue_from_pool_invocation` | runner writes no repo-root files. |
| 16 | `test_no_sigma_abc_physics_modified` | sigma_abc untouched. |
| 17 | `test_profile_inline_pool_wins_over_runtime_local_pool` | profile-inline pool takes precedence. |
| 18 | `test_diagnose_adapter_selection` | diagnostic captures `ProviderPoolAdapter` + legacy fallback. |

## Compileall Result

```text
$ python3 -m compileall loop_engine scripts tests
(no errors)
```

## Forbidden Artifact Scan

```text
$ find . -maxdepth 7 -type f \
    \( -name "*stage_013*" -o -name "*sigma_abc_013_*" \
       -o -name "*tensorial_ibp*" -o -name "*total_derivative*" \
       -o -name "*global_pre_ibp*" -o -name "*promoted_candidate_manifest*" \
       -o -name "*stage_012c_loop_orbit_canonicalization_promotion*" \) \
    -not -path "./.git/*" -not -path "./archive/*"
-> (no output)
```

No 012C / 013 / IBP / total-derivative / promotion artifacts.

## Root Hygiene Result

```text
$ ls *.md *.json
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
loop_config.json
```

Five curated root files. No runner residue at the repo root.

## Boundary Constraints Honored

- `sigma_abc/` physics untouched.
- 012C / 013 / IBP / total derivative NOT started.
- `pre_run_gate`, `freeze_preconditions`, `completion_matrix`,
  `human_signoff` unchanged.
- `human_signoff.yaml` was NOT auto-created.
- Real API keys NEVER written to any file or report.
- Stub forbidden in production (Loop 021 contract preserved).
- Permanent caveat preserved.

## Fallback Policy Evidence (preserved)

`loop_engine/provider_result.py::should_continue_to_next_provider`
is the single-source predicate:

- Schema-valid result (PASS / PASS_WITH_CAVEAT / FAIL /
  NEEDS_PATCH / BLOCKED) → stop.
- AGENT_OK → stop.
- Retryable runtime failure → next provider.
- Non-retryable → stop, write blocking review.

Tests 12 & 13 (`test_no_fallback_after_schema_valid_fail` /
`_needs_patch`) directly exercise the schema-valid stop
semantics with the new `ProviderPoolAdapter` instance built
from `runtime.local.yaml`.

## Next Safe Action

The runner now activates the pool from `runtime.local.yaml`. The
seam Phase 5R-2 surfaced is closed. Two remaining follow-ups
from the Phase 5R-2 report are still pending — both are out of
scope for this loop:

1. **Auto-signoff for pytest-style runs.** The
   `sigma_abc_safe_pre_fusion` profile declares
   `human_signoff.auto_for_tests: true`, but `freeze_checkpoint`
   in the runner does not honour it. This affects the pre-existing
   `test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`
   failure in CI only.

2. **Completion-matrix blocking-item resolution.**
   `XXXCenterProjectionRegression` and `Stage010PairFusionRegression`
   are flagged by `completion_matrix` for any attempt to freeze
   Stage 011. They are honest blockings per the protective
   contract; resolving either requires: (a) a registered
   `sigma_xxx_projection` kernel that explicitly extends to the
   center sector, or (b) explicit inherit-from-Stage-008 deferred
   registration. Either path is a separate loop.

If you approve a follow-up:

- `approved: integrate auto_for_tests into freeze_checkpoint for
  pytest-time freezes` — would unblock the pre-existing pytest
  failure and is not yet wired.
- `approved: retry Phase 5R-2 sigma_abc throughput with this hotfix
  applied` — the runner will now route `ScientificMetaReviewer`
  through the provider pool rather than the legacy Codex CLI.
  This is the next concrete unblocking path to a Phase 5R-3
  verdict A.

No throughput was triggered in this loop. Awaiting user direction.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
