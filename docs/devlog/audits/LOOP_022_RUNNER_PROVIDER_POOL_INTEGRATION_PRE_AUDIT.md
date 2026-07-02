# Loop 022 — Runner Provider-Pool Integration PRE-AUDIT

## Scope

Code-only audit. No `sigma_abc/` physics files were opened for
modification. No runner invocations were triggered in this audit.

The goal of this audit is to map every site where the runner
**currently** invokes an external reviewer/LLM agent, compare that
to where the Loop 021 provider pool machinery is **actually wired
in**, and identify exactly which integration points Loop 022 must
touch.

The audit is intentionally narrow:

- Probe / smoke scripts: out of scope (already wired in Loop 021).
- Pool skeleton (`run_pool`, `invoke_reviewer`): out of scope.
- Trust-stack: out of scope (Loop 013 invariants preserved).

Only the **runner → adapter** seam is in scope.

## Audit Table

| # | Question | Evidence | Disposition |
|---|----------|----------|-------------|
| 1 | Where does `scripts/run_autonomous_loop.py` invoke reviewers? | `run_review_cycle()` and its `run_runtime_reviewer_agents()` helper, both at [scripts/run_autonomous_loop.py:1433-1593](scripts/run_autonomous_loop.py:1433). `run_runtime_reviewer_agents()` (line 1530) builds prompts, then calls `adapter.invoke(...)` for each role (line 1571). | Integration target. |
| 2 | Where does `adapter.invoke` come from? | `from loop_engine.agent_runtime import build_adapter, AgentInvocationRequest` ([scripts/run_autonomous_loop.py:17](scripts/run_autonomous_loop.py:17)). `adapter = build_adapter(profile, profile.get("profile", ""))` ([scripts/run_autonomous_loop.py:1539](scripts/run_autonomous_loop.py:1539)). | Single seam — `build_adapter`. |
| 3 | What does `build_adapter` produce? | Defined in [loop_engine/agent_runtime.py:306-316](loop_engine/agent_runtime.py:306). Currently produces one of: `CommandAgentAdapter`, `CodexSubagentAdapter`, `ManualAdapter`, or `DryRunStubAdapter`. Decision is based on `runtime.get("adapter")`. | **The single integration point.** Loop 022 will introduce a `ProviderPoolAdapter` here. |
| 4 | Where does `runtime.local.yaml` get loaded? | `load_runtime_local()` ([loop_engine/agent_runtime.py:245-260](loop_engine/agent_runtime.py:245)). Reads `agents/runtime.local.yaml`, surfaces `.env` first via `load_dotenv()` (Loop 021 fix). `runtime_config_for_profile()` ([line 263](loop_engine/agent_runtime.py:263)) merges profile-local runtime config. | Already loads both. Loop 022 needs to also surface `reviewer_provider_pools` from the same source. |
| 5 | How is `ScientificMetaReviewer` selected in `L1_COMPACT_META`? | Two locations: (a) `aggregate_review_results()` reads `scientific_metareviewer.json` if present ([loop_engine/reviewer.py:117-121](loop_engine/reviewer.py:117)). (b) `run_runtime_reviewer_agents()` is parameterized by `reviewer_names` (line 1535) — it accepts a curated list from `risk_classification.json.reviewers`. Currently the L1 path does NOT call `run_runtime_reviewer_agents()` for `ScientificMetaReviewer`; that role is produced by a separate `run_scientific_metareview()` call in `loop_engine/meta_review.py`. | Loop 022 unifies these via the pool, but the L1 role-selection logic in `risk_classifier.classify_stage_risk` is **out of scope**. The integration delivers a `ProviderPoolAdapter` that any agent role can adopt. |
| 6 | Where is `reviewer_provider_pools` consumed today? | Only inside [`scripts/probe_reviewer_providers.py::_read_pool_cfg`](scripts/probe_reviewer_providers.py:38) (the Phase 5R probe). The runner reads **only** `runtime.command`/`runtime.adapter`; it never reads `reviewer_provider_pools.<role>`. | Confirmed gap. |
| 7 | Why does probe see the pool but runner does not? | The probe explicitly walks `profiles.*.reviewer_provider_pools` ([probe_reviewer_providers.py:64-69](scripts/probe_reviewer_providers.py:64)) and reports it. The runner, in contrast, only reads `runtime.command` via `runtime_config_for_profile()` ([loop_engine/agent_runtime.py:263](loop_engine/agent_runtime.py:263)). The runner therefore inherits Codex / CodexSubagent timeout/quota behaviour. | Fixed by adding `ProviderPoolAdapter` in `build_adapter`. |
| 8 | How is `invocation_summary.json` written? | `write_invocation_summary(evidence_dir, summary)` in [loop_engine/agent_invocation.py:39-42](loop_engine/agent_invocation.py:39). It is called by both `CommandAgentAdapter.invoke()` ([loop_engine/agent_runtime.py:200](loop_engine/agent_runtime.py:200)) and by `_write_invocation_summary` inside `run_pool` ([loop_engine/reviewer_provider_pool.py:573-604](loop_engine/reviewer_provider_pool.py:573)) — meaning the pool already writes the same shape (`adapter`, `runtime_status`, `schema_valid`, `freeze_evidence_valid`). | Loop 022's `ProviderPoolAdapter` simply returns the pool's summary dict unchanged. No new artefact schema needed. |
| 9 | How is `review_result.json` produced? | In `run_runtime_reviewer_agents()`, if the adapter's `freeze_evidence_valid` is False, the existing code writes a `FAILED`/`NEEDS_PATCH` review_result.json via `_blocking_runtime_review` ([scripts/run_autonomous_loop.py:1487-1527](scripts/run_autonomous_loop.py:1487)), using `classify_agent_runtime_failure` ([loop_engine/runtime_failures.py](loop_engine/runtime_failures.py)) to attribute the failure. | The new adapter must **return** the same summary shape (so this code path keeps working unchanged). |
| 10 | How is the existing per-agent timeout override applied? | `run_runtime_reviewer_agents()` overrides `adapter.timeout_seconds` for `L1_COMPACT_META`/`L2_FULL_PANEL` via `review_policy.l1_timeout_seconds`/`l2_timeout_seconds` ([scripts/run_autonomous_loop.py:1543-1547](scripts/run_autonomous_loop.py:1543)). | Provider-pool adapter needs to expose a mutable `timeout_seconds`. |
| 11 | How does review debt open on AGENT_TIMEOUT / AGENT_QUOTA_LIMIT? | `summary["review_debt_required"] = runtime_status in {"AGENT_TIMEOUT", "AGENT_QUOTA_LIMIT", "AGENT_NO_OUTPUT"}` is computed inside `CommandAgentAdapter.invoke()` ([loop_engine/agent_runtime.py:189](loop_engine/agent_runtime.py:189)). The pool does the same via `ReviewerProviderResult.review_debt_required`. | Preserved unchanged. |
| 12 | Where can secrets be written to disk? | Anywhere `invoke()` writes: `prompt.md`, `stdout.txt`, `stderr.txt`, `command.txt`, `invocation_summary.json`. The pool already redacts `stderr.txt` ([loop_engine/reviewer_provider_pool.py:309](loop_engine/reviewer_provider_pool.py:309)). `stdout.txt` is **not** redacted by the pool (it contains the model's JSON, not a secret). `command.txt` carries the rendered shell command (typically no secret). `prompt.md` is the prompt text (could contain `Bearer …` only if the upstream template chose to; this loop adds a redaction pass there too). | Loop 022 adds `redact_secrets` to `prompt.md` and `stdout.txt` for safety, and asserts the redactor is applied in tests. **Real key values never enter code, configs, or reports.** |
| 13 | Does root stay clean after probe/runner? | Yes (Loop 020A & Loop 021 confirmed). The probe writes to `archive/local_runs/<UTC>_PROBE_REVIEWER_PROVIDERS_<role>.md`. The runner writes `AUTONOMOUS_LOOP_RUN_REPORT.md` under `run_root`, never at the repo root (defaults). | Loop 022 must not regress this. The new adapter must NOT emit any report to the repo root. |
| 14 | Pre-existing failure: `test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008` | This test triggers `prepare_completion_and_optional_test_signoff` and `freeze_checkpoint` on a profile that requires `human_signoff`. The runner's `auto_for_tests` path is documented in [scripts/run_autonomous_loop.py:1639-1657](scripts/run_autonomous_loop.py:1639) but **not** honoured by `freeze_checkpoint`. | Pre-existing, **out of scope** for Loop 022 (per spec). |
| 15 | Where is `runtime.command` consumed? | Inside `CommandAgentAdapter.invoke()` ([loop_engine/agent_runtime.py:128-141](loop_engine/agent_runtime.py:128)). Tokens like `{prompt_path}`, `{output_path}`, `{stage_dir}`, `{agent_name}` and `${REPO_ROOT}` are substituted via `_format_command`. | Must remain backward-compatible. New `ProviderPoolAdapter` must NOT remove `CommandAgentAdapter`. |
| 16 | Where is the existing `codex_resolver.sh` wrapper? | Outside the Python module graph — invoked by the configured `runtime.command` list. `scripts/codex_resolver.sh` resolves `codex` from PATH/aliases. | Loop 022 does not change the resolver. When the pool selects a non-Codex provider, the resolver never runs. |
| 17 | What guarantees that the pool does not silently replace a real agent with a stub? | `forbid_stub` in pool config ([loop_engine/reviewer_provider_pool.py:393](loop_engine/reviewer_provider_pool.py:393)). `require_real_provider=True` ([line 394](loop_engine/reviewer_provider_pool.py:394)) makes the pool fail with `AGENT_ALL_PROVIDERS_UNAVAILABLE` instead of selecting a stub. | Preserved. The new adapter must NOT override these. |
| 18 | Are deterministic tests at risk? | Loop 021 already covered env-loader tests ([tests/test_loop021_env_loader.py](tests/test_loop021_env_loader.py)). Loop 022's new tests must avoid network calls, must use monkeypatching of `_run_command_provider` and the subprocess layer, and must NOT depend on `OPENAI_COMPATIBLE_API_KEY`/`OPENAI_API_KEY`/`ANTHROPIC_API_KEY` being present. | Out-of-scope to network; in-scope to mock. |
| 19 | Where is the loop-engine guarantee that `freeze_evidence_valid` reflects read-only contract? | Both `CommandAgentAdapter.invoke()` ([loop_engine/agent_runtime.py:194-198](loop_engine/agent_runtime.py:194)) and `_write_invocation_summary` ([loop_engine/reviewer_provider_pool.py:582-600](loop_engine/reviewer_provider_pool.py:582)) compute `freeze_evidence_valid` from `exit_code == 0 and schema_valid and not readonly.ReviewerModifiedProtectedFiles`. | Preserved. |

## Discovered integration points

Three files need editing in step 2:

1. `loop_engine/agent_runtime.py`
   * Add a new `ProviderPoolAdapter` (subclass of `AgentAdapter`).
   * Update `build_adapter()` to return it when the loop finds a
     `reviewer_provider_pools.<role>` block for the requested
     reviewer role AND a legacy fallback command exists (i.e.
     pool-or-legacy: pool takes precedence, but never silently).

2. `loop_engine/agent_invocation.py`
   * No new functions needed (the helpers are stable). Loop 022's
     new adapter may call these unchanged.

3. `scripts/run_autonomous_loop.py`
   * Minimal change: `run_runtime_reviewer_agents` must read
     `reviewer_provider_pools.<role>` once and pass it down. The
     cleanest seam is to read it inside `build_adapter()` itself.
     That keeps the runner unchanged.

## Hard constraints preserved

- `sigma_abc/` physics untouched.
- 012C / 013 / IBP / total derivative not started.
- `pre_run_gate`, `freeze_preconditions`, `completion_matrix`,
  `human_signoff` are not modified.
- `human_signoff.yaml` is NOT auto-created.
- Real API keys NEVER written to any file or report.
- Permanent caveat: `DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.`

## What Step 1 + Step 2 will produce

A new `ProviderPoolAdapter` in `loop_engine/agent_runtime.py`:

- Detects the pool config by reading
  `agents/runtime.local.yaml::profiles.<profile>.reviewer_provider_pools[<role>]`
  via a new helper `_resolve_pool_cfg(profile, role)`,
- Calls `loop_engine.reviewer_provider_pool.invoke_reviewer`,
- Maps the resulting `ReviewerProviderResult` into the same
  summary dict shape used by `CommandAgentAdapter.invoke()`,
- Applies `redact_secrets` to `prompt.md` and `stdout.txt` before
  writing, never to `invocation_summary.json` itself (the pool
  already keeps the values sanitised),
- Has a mutable `timeout_seconds` attribute (used by L1/L2 override),
- Falls back to the existing `CommandAgentAdapter` exactly when
  no pool config is found (legacy `runtime.command` preserved),
- Does NOT modify any trust-stack invariant.

## Out of scope (deferred)

- Wiring `auto_for_tests` into `freeze_checkpoint`. Documented as
  the second follow-up by the Phase 5R final report. **Not** in
  this loop.
- API adapter skeletons becoming real HTTP calls. Already
  classified as out-of-scope by `api_review_provider.py`. The pool
  in this loop uses `adapter: command` providers only; api_adapter
  paths return `AGENT_RUNTIME_FAILURE` until wired by a future
  loop (this matches Loop 021's intentional narrow scope).

## Next step

Step 1-2: implement `ProviderPoolAdapter` and `invoke_reviewer`
adapter at the runner seam.
