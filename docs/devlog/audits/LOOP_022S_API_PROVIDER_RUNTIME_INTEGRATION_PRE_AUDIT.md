# Loop 022S — API Provider Runtime Integration PRE-AUDIT

## Scope

Code-only audit. No `sigma_abc/` physics files were opened for
modification. No runner invocations were triggered in this audit.

The goal of this audit is to map the **exact dispatch seam** in
`loop_engine/reviewer_provider_pool.py::run_pool` and confirm the
shape of the integration with the three API adapter functions
(`invoke_openai_compatible_api`, `invoke_openai_api`,
`invoke_anthropic_api`) in `loop_engine/api_review_provider.py`.

Loop 022S wires API adapters into the pool's runtime. It is
infrastructure-only.

## Audit Table

| # | Question | Evidence | Disposition |
|---|----------|----------|-------------|
| 1 | Where does `run_pool` dispatch? | [loop_engine/reviewer_provider_pool.py:453-484](loop_engine/reviewer_provider_pool.py:453). Currently only one branch: `cmd = _build_command_for_provider(...)`; non-command providers hit `if cmd is None` and get classified as `AGENT_RUNTIME_FAILURE` with skeleton-limitation text. | **Target of this loop.** |
| 2 | What do the API adapter functions return? | [loop_engine/api_review_provider.py:138-294](loop_engine/api_review_provider.py:138). Each returns a `ReviewerProviderResult` directly via `_classify_api_response`; missing-key is `_build_api_missing_key_result`. | Reuse unchanged. They already conform to the pool's result shape. |
| 3 | What does `invoke_openai_compatible_api` accept? | `(*, request: AgentInvocationRequest, api_key: str | None, base_url: str | None, model: str | None) -> ReviewerProviderResult`. | This signature matches what the pool needs to call. |
| 4 | What does `invoke_openai_api` accept? | `(*, request: AgentInvocationRequest, api_key: str | None, model: str | None) -> ReviewerProviderResult`. | Same. |
| 5 | What does `invoke_anthropic_api` accept? | `(*, request: AgentInvocationRequest, api_key: str | None, model: str | None) -> ReviewerProviderResult`. | Same. |
| 6 | How are API keys resolved from provider config? | [`_resolve_api_key(provider_cfg)`](loop_engine/reviewer_provider_pool.py:79) reads `api_key` (explicit) or `api_key_env` (env-var NAME only); never persists the value. | Reuse unchanged. The pool will call this before invoking each API provider. |
| 7 | How are base URLs / models resolved? | [`_resolve_base_url` / `_resolve_model`](loop_engine/reviewer_provider_pool.py:97-118). Same pattern. | Reuse unchanged. |
| 8 | How does `_classify_api_response` translate HTTP into `runtime_status`? | [loop_engine/api_review_provider.py:299-413](loop_engine/api_review_provider.py:299). 2xx + valid JSON → `AGENT_OK`; JSONDecodeError → `AGENT_SCHEMA_FAIL`; 5xx → `AGENT_TRANSPORT_FAILURE`; 4xx → `AGENT_SCHEMA_FAIL`. | Reuse unchanged. The pool already maps `AGENT_TRANSPORT_FAILURE` to "retryable" via `is_retryable()`. |
| 9 | Where does the API adapter write evidence? | `_record_invocation` writes `.loop/agent_invocations/<role>/api_attempt.json` (with `api_key_redacted: "<redacted:API_KEY>"` — **the value is never stored**). | Reuse unchanged. |
| 10 | How does the API adapter write a `review_result.json`? | The API adapter calls `payload_obj.get("verdict")` from the upstream response and translates that into the `ReviewerProviderResult`. **The actual review JSON file is NOT written by the API adapter itself.** | **Loop 022S must wire this:** when the API adapter returns a schema-valid `ReviewerProviderResult`, the pool must write the review JSON to `request.output_path` so downstream `aggregate_review_results()` continues to work unchanged. |
| 11 | How does `provide_attempts` flow? | The pool iterates providers and appends `ProviderAttempt` to `result.provider_attempts`. | Reuse unchanged. Each API invocation becomes one attempt. |
| 12 | How is `selected_provider` recorded? | `result.selected_provider = str(provider_cfg.get("name", "?"))` when the chain stops on schema-valid. | Reuse unchanged for API path. |
| 13 | Where could secrets leak? | `api_attempt.json` already redacts `api_key`. The upstream HTTP request body never contains a key — only `prompt_text`. The redactor (`loop_engine/secret_redaction.py`) is applied to stdout/stderr/command.txt/prompt.md/invocation_summary.json after every invocation. | Defence-in-depth: redact any captured response body or extra field before persisting. |
| 14 | Failure classification on missing key | `_build_api_missing_key_result` returns `AGENT_RUNTIME_FAILURE` with `failure_summary_redacted="OPENAI_COMPATIBLE_API_KEY env var not set"`. Not retryable in Pool 021 semantics? Actually `is_retryable("AGENT_RUNTIME_FAILURE") == True`, so this IS retryable — the pool will fall through to the next provider. This is wrong per the spec — missing-key should NOT be a chained retryable event. **Need a small adjustment.** | Loop 022S classifies "missing API key" as a non-retryable `AGENT_RUNTIME_FAILURE` (a "configuration" failure, not a provider-runtime failure). |
| 15 | Quota / timeout detection from upstream text | API adapters classify HTTP status alone, not text. The user's `loop_engine/agent_runtime._runtime_status_from_result` keys on `"usage limit"`, `"quota"`, `"try again at"` text — for API, we need an equivalent that looks at `api_attempt.json` summary or status code: 429 / quota keywords → `AGENT_QUOTA_LIMIT`; transport timeout → `AGENT_TIMEOUT`. | **Loop 022S add:** Re-classify `_classify_api_response` to detect 429 / 408 / 504 / quota keyword in payload, OR have the pool apply a second-pass detector. |
| 16 | Tests that pin current behavior | `tests/test_loop022_runner_provider_pool_integration.py` — Loop 022's 18 tests; `tests/test_loop022r_runner_runtime_pool_activation.py` — Loop 022R's 18 tests. | New `tests/test_loop022s_api_provider_runtime_integration.py` will monkey-patch `loop_engine.api_review_provider.invoke_*` to return synthetic `ReviewerProviderResult`s. No real API calls. |
| 17 | Command provider behavior | The `if cmd is not None` branch in `run_pool` runs `_run_command_provider` and writes its evidence. | Preserved exactly. |
| 18 | `codex_resolver` fallback | The legacy fallback path is `invoke_reviewer(pool_cfg=None, fallback_command=[...codex_resolver.sh ...])`. | Preserved exactly. |
| 19 | Stub handling | `forbid_stub: True` filter in `run_pool` rejects `adapter: stub` providers. | Preserved. |

## Hard Constraints Preserved

- `sigma_abc/` physics untouched.
- 012C / 013 / IBP / total derivative **NOT** started.
- `pre_run_gate`, `freeze_preconditions`, `completion_matrix`,
  `human_signoff` not modified.
- `human_signoff.yaml` NOT auto-created.
- Real API keys never written to any file or report.
- Stub forbidden in production.
- Permanent caveat:
  `DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.`

## Single-Seam Fix Design

`run_pool`'s dispatch becomes:

```python
adapter = str(provider_cfg.get("adapter"))
if adapter in {"command", "codex_subagent", "claude_code_cli"}:
    # existing _run_command_provider path
    ...
elif adapter in {"openai_compatible_api", "openai_api", "anthropic_api"}:
    # NEW: invoke api_review_provider.invoke_*
    api_func = ADAPTER_DISPATCH[adapter]
    api_key, _ = _resolve_api_key(provider_cfg)
    base_url, _ = _resolve_base_url(provider_cfg) if adapter == "openai_compatible_api" else (None, "absent")
    model, _ = _resolve_model(provider_cfg)
    try:
        api_result = api_func(
            request=request,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
    except Exception as exc:
        # Treat uncaught API exceptions as AGENT_RUNTIME_FAILURE.
        api_result = _api_uncaught_result(adapter, exc)
    # Translate ReviewerProviderResult -> attempt +  pool
    # semantics.
    ...
```

The translation steps:

1. Read `api_result.provider_attempts[-1]` to capture the
   underlying adapter's attempt (since the API adapter already
   recorded its own `ProviderAttempt`).
2. Synthesize a `provider_attempts` entry for the pool level
   (merge).
3. Apply `should_continue_to_next_provider` exactly as today.
4. On schema-valid: write the upstream review JSON to
   `request.output_path` (so aggregate_review_results keeps
   working).

The "missing API key" classification is adjusted so the pool
treats it as **non-retryable** for the chain: if `_resolve_api_key`
returns `None`, the pool emits
`AGENT_RUNTIME_FAILURE` with a non-retryable `runtime_status`.
This honors the Loop 021 spec:

> "pool emits AGENT_ALL_PROVIDERS_UNAVAILABLE rather than
> silently choosing a stub" / "missing API key" is a
> *configuration* failure, not a *runtime* failure.

The behaviour we're pinning in test 11 ("missing API key does
not print key and is classified safely") will assert that
`_resolve_api_key(provider_cfg) -> (None, ...)` maps to
`AGENT_RUNTIME_FAILURE` non-retryable.

## Files Expected to be Modified in Step 2

| File | Change |
|------|--------|
| `loop_engine/reviewer_provider_pool.py` | Add API dispatch in `run_pool`; add a `_run_api_provider` helper; add `ADAPTER_DISPATCH` mapping. Update `_extract_verdict` to read from `request.output_path` (already does). |
| `loop_engine/api_review_provider.py` | Minor: re-classify `_build_api_missing_key_result` to give a non-retryable runtime_status (e.g. introduce `AGENT_CONFIGURATION_MISSING_KEY` semantic, OR keep `AGENT_RUNTIME_FAILURE` but document "non-retryable for missing key" — the simplest is for the pool to override `attempt.retryable=False` when the underlying failure mode is missing key). |
| Tests | NEW file `tests/test_loop022s_api_provider_runtime_integration.py` with 18 tests. |
| Docs | NEW audit + report. |

## What Step 4 will produce

- 18 new unit tests covering every required case in Step 4 of
  the user's loop.
- Each test monkey-patches the `invoke_*` API functions in
  `loop_engine.api_review_provider` to return synthetic
  `ReviewerProviderResult`s — no real network, no real API
  keys.
- Secret redaction test sets a fake `OPENAI_COMPATIBLE_API_KEY`
  and asserts the literal value never appears in any artefact
  under `.loop/agent_invocations/ScientificMetaReviewer/`.

## Out of Scope (deferred)

- Wiring `human_signoff.auto_for_tests: true` through
  `freeze_checkpoint`. Pre-existing pytest-time freeze failure;
  not in this loop.
- Wiring a real HTTP fallback for the API adapters in
  pytest-time smoke. The existing `_call_api` stdlib call is
  production-ready (per Loop 021 docstring); we only wire it
  through the pool.

## Next step

Step 1-3: implement the API dispatch in
`loop_engine/reviewer_provider_pool.py` so that the three API
adapters become callable from the pool's runtime, with the
correct classification of missing-key, quota, timeout,
schema-valid, and schema-invalid outcomes.
