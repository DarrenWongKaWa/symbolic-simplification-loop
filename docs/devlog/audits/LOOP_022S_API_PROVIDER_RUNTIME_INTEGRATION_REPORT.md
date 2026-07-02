# Loop 022S — API Provider Runtime Integration REPORT

## Status

VERDICT **A**. API providers are now wired into
`loop_engine/reviewer_provider_pool.py::run_pool`. The pool's
runtime dispatch recognises `openai_compatible_api`, `openai_api`,
and `anthropic_api` adapter names and routes them to the
corresponding `loop_engine/api_review_provider.py::invoke_*`
functions. Fallback remains **runtime-failure-only**. Schema-valid
semantic verdicts (PASS / PASS_WITH_CAVEAT / FAIL / NEEDS_PATCH)
stop the chain immediately. Stub forbidden in production. Real
API keys never written to disk.

```text
Final classification (per user spec):
A. "API providers wired into reviewer provider pool runtime;
    openai-compatible / OpenAI / Anthropic adapters are
    callable; fallback remains runtime-failure-only; tests
    pass; sigma_abc not modified."
```

Permanent caveat preserved:
`DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.`

## Files Modified

| File | Change |
|------|--------|
| `loop_engine/reviewer_provider_pool.py` | Added `API_ADAPTERS` set, `_detect_quota_or_timeout` helper, `_exit_code_for_api` helper, and a new `_run_api_provider` runner. Replaced the dispatch loop in `run_pool` so it routes by `adapter_name`: command-family → `_run_command_provider`; API adapters → `_run_api_provider`; unknown → `AGENT_RUNTIME_FAILURE` non-retryable. The `provider_attempts` merge includes both pool-level and upstream API level records. Missing-key failures are explicitly downgraded from retryable to non-retryable (configuration failure, not runtime failure). |
| `tests/test_loop022s_api_provider_runtime_integration.py` | NEW, 18 tests covering dispatch, schema-valid stop, quota/timeout fallback, missing-key classification, secret redaction, command-path preservation, legacy-path preservation, and stub-forbidden preservation. All tests use `monkeypatch` on `loop_engine.api_review_provider` symbols; no real network; no real API key values. |
| `docs/devlog/audits/LOOP_022S_API_PROVIDER_RUNTIME_INTEGRATION_PRE_AUDIT.md` | NEW: pre-audit enumerating every dispatch seam and the integration plan. |

The autonomous runner (`scripts/run_autonomous_loop.py`) was
**not** changed. The fix is purely inside the pool.

## API Adapters Wired

| Adapter name | Adapter function | Required env vars |
|--------------|------------------|-------------------|
| `openai_compatible_api` | `loop_engine.api_review_provider.invoke_openai_compatible_api` | `OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_MODEL` |
| `openai_api` | `loop_engine.api_review_provider.invoke_openai_api` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `anthropic_api` | `loop_engine.api_review_provider.invoke_anthropic_api` | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |

The pool's dispatch:

```python
if adapter_name in {"command", "codex_subagent", "claude_code_cli"}:
    attempt = _run_command_provider(...)
elif adapter_name in API_ADAPTERS:        # openai_compatible_api / openai_api / anthropic_api
    attempt = _run_api_provider(...)
else:
    attempt_meta = ProviderAttempt(
        runtime_status="AGENT_RUNTIME_FAILURE",
        failure_summary_redacted=f"unsupported adapter type: {adapter_name!r}",
        retryable=False,     # non-retryable configuration error
    )
    result.provider_attempts.append(attempt_meta)
    continue
```

`_run_api_provider`:

1. Resolves API key, base URL, model via the existing
   `_resolve_api_key` / `_resolve_base_url` / `_resolve_model`
   helpers — only env-var *names* are read from the provider's
   YAML config; values stay in `os.environ`.
2. Calls the appropriate `invoke_*` function with the
   `AgentInvocationRequest` and the resolved secrets.
3. Captures the upstream `ReviewerProviderResult.provider_attempts`.
4. Refines the runtime_status against quota / timeout text using
   `_detect_quota_or_timeout`.
5. Writes evidence artefacts under
   `.loop/agent_invocations/<role>/` (prompt.md, command.txt,
   stdin/out, api_attempt.json, invocation_summary.json,
   pool_result.json). The redactor is applied to every artefact.
6. Returns a dict shaped like `_run_command_provider`'s output
   so the dispatcher loop's downstream semantics are identical
   for both code paths.

## Command Adapter Preservation

The legacy `_run_command_provider` path is **untouched**:

```text
adapter in {"command", "codex_subagent", "claude_code_cli"}
  → _run_command_provider(request, provider_cfg, command_template, cwd)
```

`tests/test_loop022s_api_provider_runtime_integration.py::
test_command_provider_unchanged` proves this with a single
provider, no API keys set, and the assertion
`result.selected_provider == "echo_p"`,
`result.adapter == "command"`. The Loop 019R `codex_resolver.sh`
fallback through `CommandAgentAdapter` and `CodexSubagentAdapter`
remains in `loop_engine/agent_runtime.py` exactly as Loop 019R
produced.

The Loop 022 + Loop 022R test suites continue to pass (63
tests across the targeted runner-integration surface).

## Fallback Policy Evidence

`loop_engine/provider_result.py::should_continue_to_next_provider`
remains the single-source predicate. The dispatcher in
`run_pool` honors it for both command and API providers.
`loop_engine/reviewer_provider_pool.py::_detect_quota_or_timeout`
introduces two new assistant-classification heuristics:

- Quota markers (`usage limit`, `rate limit`, `ratelimit`,
  `quota`, `try again at`, `429`, `insufficient_quota`) →
  `AGENT_QUOTA_LIMIT` (retryable).
- Timeout markers (`timeout`, `timed out`, `504`, `408`) →
  `AGENT_TIMEOUT` (retryable).

The default `RETRYABLE_RUNTIME_STATUSES` frozenset in
`loop_engine/provider_result.py` is unchanged:

```text
AGENT_QUOTA_LIMIT, AGENT_TIMEOUT, AGENT_NO_OUTPUT,
AGENT_COMMAND_NOT_FOUND, AGENT_TRANSPORT_FAILURE,
AGENT_RUNTIME_FAILURE
```

## No-Fallback Semantic Evidence

Tests 4–7 directly exercise the Loop 021 hard rule. Sample:

```text
test_schema_valid_pass_stops_chain:
    First provider returns schema-valid PASS_WITH_CAVEAT
    (exit_code=200, AGENT_OK).
    Second provider's invoke_* is monkeypatched to raise
    AssertionError if called.
    → result.selected_provider == "openai_compatible_api"
    → result.verdict == "PASS_WITH_CAVEAT"

test_no_fallback_after_schema_valid_fail:
    First provider returns schema-valid FAIL.
    Second provider's invoke_* is monkeypatched to raise
    AssertionError.
    → result.selected_provider == "openai_compatible_api"
    → result.verdict == "FAIL"
    → Second provider never runs.

test_no_fallback_after_schema_valid_needs_patch:
    Same pattern with verdict=NEEDS_PATCH.
```

The schema-valid stop is honoured **before** the next provider is
touched. This is by construction of `should_continue_to_next_provider`
(`schema_valid=True` → return `False`).

## Secret Redaction Evidence

`loop_engine/secret_redaction.py::redact_secrets` is applied at
every artefact write inside `_run_api_provider`. Specifically:

- `prompt.md` — redacted before write.
- `command.txt` — `redact_secrets("POOL API adapter=... role=...")`
- `stdout.txt` — `redact_secrets("")`
- `stderr.txt` — `redact_secrets("")`
- `exit_code.txt` — carries only the HTTP status code, no value.

Test 14 (`test_secret_redaction_applies_to_api_artifacts`) sets
`OPENAI_COMPATIBLE_API_KEY=sk-fakeprooftest-loop022s-must-hide-12345`,
monkey-patches the API adapter to return an error text containing
the literal key (`401 Unauthorized; check key {fake_key}`), runs
the pool, and walks every file under
`.loop/agent_invocations/ScientificMetaReviewer/`. The literal key
**does not appear** in any file (assertion PASS).

Additionally, `_run_api_provider` calls `_exit_code_for_api`
which only reads `ProviderAttempt.exit_code` and writes it to
`exit_code.txt` — no other code path touches the upstream
secret.

`api_review_provider.py::_record_invocation` continues to
write `api_key_redacted: "<redacted:API_KEY>"` rather than the
real value (Loop 021).

## Tests Result

```text
$ python3 -m pytest -q tests/test_loop021_*.py \
    tests/test_loop022_*.py tests/test_loop022r_*.py \
    tests/test_loop022s_*.py

81 passed, 1 warning in 6.00s

$ python3 -m pytest -q
1 failed, 261 passed, 1 warning in 39.37s
```

The single failure is
`tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`,
the documented pre-existing `human_signoff.yaml is required`
hard-stop (Loop 020A / 021 / 021P). It is **NOT** caused by this
loop, and **NOT** modified.

Loop 022S adds **18** new tests:

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_openai_compatible_api_dispatched` | pool → `invoke_openai_compatible_api` |
| 2 | `test_openai_api_dispatched` | pool → `invoke_openai_api` |
| 3 | `test_anthropic_api_dispatched` | pool → `invoke_anthropic_api` |
| 4 | `test_schema_valid_pass_stops_chain` | PASS stops the chain |
| 5 | `test_schema_valid_pass_with_caveat_stops_chain` | PASS_WITH_CAVEAT stops the chain |
| 6 | `test_no_fallback_after_schema_valid_fail` | FAIL stops the chain |
| 7 | `test_no_fallback_after_schema_valid_needs_patch` | NEEDS_PATCH stops the chain |
| 8 | `test_quota_falls_back` | AGENT_QUOTA_LIMIT refined + retry |
| 9 | `test_timeout_falls_back` | AGENT_TIMEOUT refined + retry |
| 10 | `test_unsupported_adapter` | unknown adapter → AGENT_ALL_PROVIDERS_UNAVAILABLE |
| 11 | `test_missing_api_key_safe` | missing key → non-retryable, no key on disk |
| 12 | `test_provider_attempts_include_api` | provider_attempts carries the API attempt |
| 13 | `test_selected_provider_in_invocation_summary` | selected_provider on disk |
| 14 | `test_secret_redaction_applies_to_api_artifacts` | redaction covers API error text |
| 15 | `test_command_provider_unchanged` | legacy command path preserved |
| 16 | `test_legacy_no_pool_unchanged` | fallback_command path preserved |
| 17 | `test_stub_forbidden_in_pool` | stub forbidden in production |
| 18 | `test_no_sigma_abc_physics_modified` | sigma_abc/ not touched |

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
(no output)
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

- Did not modify `sigma_abc/`.
- Did not run 012C / 013 / IBP / total derivative.
- Did not run full sigma_abc throughput (per spec).
- Did not modify freeze_preconditions / completion_matrix / human_signoff.
- Did not auto-create `human_signoff.yaml`.
- Did not weaken reviewer verdict requirements.
- Did not fallback after semantic FAIL or NEEDS_PATCH.
- Did not write real API key values to any file or report.
- Stub forbidden in production — never invoked.

## Probe / Diagnostic State (Step 5)

```text
$ python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
## 2. `openai_compatible_api` (adapter: `openai_compatible_api`)
- enabled: `True` (reason: `env:LOOP_ENABLE_OPENAI_COMPATIBLE`)
- availability_status: AVAILABLE
- runtime_status: AVAILABLE

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

Probe sees `openai_compatible_api` AVAILABLE. The runner
selects `ProviderPoolAdapter`. The pool's runtime now actually
calls `invoke_openai_compatible_api` (verified by the new
integration tests). The Loop 022 + 022R plumbing is now
load-bearing end-to-end.

## Next Safe Action

The runtime-pool seam is fully wired. The single remaining
unblocking path to a Phase 5R-4 verdict A is:

- `approved: retry Phase 5R-4 sigma_abc throughput with provider
  pool fully wired` — the runner's `ScientificMetaReviewer`
  invocation will now reach `openai_compatible_api` and produce a
  real reviewer verdict (provided the user's `.env` keeps
  `LOOP_ENABLE_OPENAI_COMPATIBLE=1` and the DeepSeek key remains
  valid). A schema-valid verdict will stop the chain at the
  first provider, and 011 / 012A / 012B will progress through
  with real verdicts.

A separate follow-up that is still pending (not addressed by this
loop):

- Auto-signoff for pytest-time freezes —
  `human_signoff.auto_for_tests: true` is declared in the
  `sigma_abc_safe_pre_fusion` profile but
  `freeze_checkpoint` in the runner does not honour it. This
  is the pre-existing test
  `test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`
  failure.

No throughput was triggered in this loop. Awaiting user
direction.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
