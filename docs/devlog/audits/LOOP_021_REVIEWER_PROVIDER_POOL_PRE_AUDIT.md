# Loop 021 — Reviewer Provider Pool Pre-Audit

## Status

CODEBASE_MAPPED_ARCHITECTURE_DESIGNED.

Loop 021 is provider-pool abstraction work. The trust stack
itself is unchanged: `ScientificMetaReviewer` remains a
required reviewer role; only the way that role is invoked
(provider + adapter + retry policy) is being abstracted.

`sigma_abc` physics NOT modified. No 012C / 013 / IBP / total
derivative started. No full tensorial sigma_abc correctness
claim.

Permanent caveat preserved:
`DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial
DC-series PASS.`

## Current Reviewer Invocation Path (Verbatim)

```text
scripts/run_autonomous_loop.py
  -> profiles/*.yaml              -- declares runtime.adapter=command + command list
  -> agents/runtime.local.yaml   -- user-overrides the same command list
  -> loop_engine/agent_runtime.py
       -> CommandAgentAdapter.invoke(request)
            -> subprocess.run(rendered_command, timeout=timeout_seconds)
            -> classify runtime_status via _runtime_status_from_result(...)
       -> returns summary dict (runtime_status, schema_valid, ...)
  -> writes agent_invocations/<agent>/invocation_summary.json
       (loops back into review_result.json via reviewer_role)
```

Single-provider-only today. If `command -v codex` is missing,
the wrapper self-aborts (`exit 127`). If Codex CLI returns
`usage limit`, that gets classified as
`runtime_status = "AGENT_QUOTA_LIMIT"`. There is no
provider-pool fallback: a single `CommandAgentAdapter` instance
is built at the call site.

## Runtime Status Classification (in `loop_engine/agent_runtime.py`)

`_runtime_status_from_result` returns one of:

```text
AGENT_QUOTA_LIMIT      if "usage limit"/"quota"/"try again at" appears in stdout/stderr
AGENT_TIMEOUT          if subprocess.TimeoutExpired
AGENT_NO_OUTPUT        if output file does not exist
AGENT_SCHEMA_FAIL      if schema_valid = False
AGENT_OK               if exit_code == 0 and schema_valid
```

These are the **only** retryable failure codes. Any other
runtime / non-zero exit_code is also classified as
`AGENT_SCHEMA_FAIL` per the existing code's `if exit_code != 0`
fallback path. **This means the current code already
distinguishes runtime failures from semantic reviewer
verdicts**; the schema separates them by the
`schema_valid` boolean and the parsed JSON
`verdict ∈ {PASS, FAIL, ...}`. Loop 021 will preserve this
distinction.

## Reviewer Result Consumption (`review_result.json`)

`review_result.json` is consumed by `loop_engine/state.py::freeze_preconditions`:

```text
if review.get("verdict") not in FREEZABLE_REVIEW_VERDICTS:  # {"PASS", "PASS_WITH_CAVEAT"}
    missing.append("review_result.verdict must be PASS or PASS_WITH_CAVEAT")
```

The provider-pool result must preserve this contract exactly.
Semantic verdict PASS / PASS_WITH_CAVEAT still freezes the gate;
FAIL / NEEDS_PATCH still does not.

## Existing Provider Path In `agents/runtime.local.yaml`

Today the file (gitignored) contains per-profile `runtime.command`
arrays. Each profile's first entry is `bash scripts/codex_resolver.sh
{agent_name} ...`. The Codex CLI binary lives outside PATH; the
resolver script does PATH-fallback. After Loop 019R this works
end-to-end and the Codex CLI v0.142.5 is actually invoked.
**The remaining blocker is external Codex CLI quota** —
`AGENT_QUOTA_LIMIT`.

Loop 021's job is to make this single dependency optional by
adding:

1. The Anthropic API path (real `anthropic` Python package or
   curl-style HTTP).
2. The OpenAI API path (real `openai` Python package or curl-style
   HTTP).
3. An OpenAI-compatible HTTP path for user-provided base URLs
   (e.g. a locally hosted LLM).
4. A Claude Code CLI adapter (an alternative process-style
   provider similar to the Codex CLI adapter).

The pool does **not** introduce stubs. The codebase already has a
`DryRunStubAdapter` keyed on `adapter: stub`. Production profiles
that disallow stub (`forbid_stub_in_production: true`) continue
to reject it; the pool must honour this invariant.

## Class Hierarchy (Loop 021 Targets)

```text
AgentAdapter (existing)
  |- CommandAgentAdapter         (existing; keep)
  |- CodexSubagentAdapter        (existing; keep)
  |- DryRunStubAdapter          (existing; never use in production)
  |- ManualAdapter              (existing; keep)
  |- new AnthropicApiAdapter
  |- new OpenAIApiAdapter
  |- new OpenAICompatibleApiAdapter
  |- new ClaudeCodeCliAdapter   (a CommandAgentAdapter variant)

ReviewerProviderPool (new)
  - select_providers(role)       -- in declared order, only enabled
  - run_chain(role, request)     -- invokes, attempts, normalizes
  - retryable?(runtime_status)   -- AGENT_QUOTA_LIMIT/TIMEOUT/COMMAND_NOT_FOUND/etc.
  - stop_on_schema_valid_verdict -- PASS / PASS_WITH_CAVEAT / FAIL / NEEDS_PATCH
  - never retry semantic failure -- by design

ReviewerProviderResult (new)
  - reviewer_role
  - selected_provider
  - provider_attempts: list[ProviderAttempt]
  - adapter, actually_invoked, stub_used
  - runtime_status
  - schema_valid
  - verdict                (extracted from review_result.json)
  - retryable               (True only for runtime_failure statuses)
  - fallback_reason
  - secret_redaction_applied

SecretRedactor (new)
  - redact_api_keys(text) -> str
  - is_api_key(secret) -> bool
```

## Fallback Policy (Hard Rule)

**Fallback only on retryable runtime failures:**

```text
RETRYABLE (allowed to advance to next provider):
  - AGENT_QUOTA_LIMIT
  - AGENT_TIMEOUT
  - AGENT_NO_OUTPUT
  - AGENT_COMMAND_NOT_FOUND
  - AGENT_RUNTIME_FAILURE   (e.g. missing Python dep at import-time)
  - AGENT_TRANSPORT_FAILURE (e.g. HTTP connection refused)

STOP IMMEDIATELY (no fallback):
  - any verdict from a schema-valid result
    (PASS / PASS_WITH_CAVEAT / FAIL / NEEDS_PATCH)
  - boundary audit unsafe (boundary_audit.* == true)
  - full tensorial claim detected
  - IBP started without approval
  - any review_result whose schema_valid == True regardless
    of verdict
```

This rule is encoded in `ReviewerProviderPool.run_chain()`'s
`should_continue_to_next_provider()` predicate. The existing
`decision.action = PROVISIONAL_FREEZE_WITH_REVIEW_DEBT` path is
preserved for the case where **all** providers fail with
retryable errors — that becomes
`AGENT_ALL_PROVIDERS_UNAVAILABLE`. The review debt then opens
exactly as today.

## Secret Redaction

`scripts/codex_resolver.sh` and the command adapter write
`command.txt`, `stdout.txt`, `stderr.txt`, `prompt.md`, and
`input_manifest.json` to
`.loop/agent_invocations/<agent>/`. None of these currently
contain an API key because the Codex resolver only writes
paths and stage metadata.

API providers will introduce API key arguments (e.g.
`ANTHROPIC_API_KEY` header). The provider must never write a
full key to disk; the secret redactor must strip keys from
everywhere they could otherwise land:

```text
- env vars in logs
- API request/response in stdout/stderr
- invocation_summary.json
- command.txt (when --show is on)
- prompt.md (only if the user pasted a key into the prompt)
```

The redactor will detect by **pattern** (key patterns like
`sk-...`, `sk-ant-...`, `Bearer ...`) and by **env var name**
(when the prompt reads e.g. `$ANTHROPIC_API_KEY`). Default
on. Cannot be disabled in production.

The example `agents/runtime.local.example.yaml` will contain
**only** env var names like `ANTHROPIC_API_KEY`, **never** a
real key, because:
- the example file is committed and must not store secrets;
- users set the real keys in their shell / .env / CI vault.

`agents/runtime.local.yaml` remains **gitignored** because users
may legitimately set `enabled: false` and a non-secret
provider-specific `command:` override there.

## Files To Touch In This Loop

```text
loop_engine/reviewer_provider_pool.py          # NEW
loop_engine/provider_result.py                # NEW
loop_engine/secret_redaction.py               # NEW

schemas/reviewer_provider_pool.schema.json    # NEW
schemas/reviewer_provider_result.schema.json  # NEW

agents/runtime.local.example.yaml             # add provider-pool example

scripts/probe_reviewer_providers.py           # NEW
scripts/run_reviewer_provider_smoke.py        # NEW

loop_engine/agent_runtime.py                   # integrate provider pool; preserve legacy
tests/test_loop021_*.py                        # NEW (3 files)
docs/user_guide/REVIEWER_PROVIDER_POOL.md      # NEW
docs/user_guide/API_KEYS.md                   # NEW
docs/devlog/audits/LOOP_021_REVIEWER_PROVIDER_POOL_REPORT.md  # NEW
```

## Files Explicitly NOT To Touch

```text
loop_engine/state.py                           # freeze_preconditions
loop_engine/completion_matrix.py               # completion matrix
loop_engine/human_signoff.py                   # human signoff
loop_engine/checkpoint.py                     # freeze_checkpoint
loop_engine/identity_traceability.py           # identity traceability gate
loop_engine/scientific_identities.py           # scientific identities rendering
loop_engine/pre_run_gate.py                    # pre_run_gate
loop_engine/pre_run_brief.py                   # pre_run_brief
schemas/completion_matrix.schema.json
schemas/human_signoff.schema.json
schemas/review_result.codex.schema.json
schemas/pre_run_gate_result.schema.json
schemas/pre_run_brief.schema.json
sigma_abc/                                    # physics
profiles/*                                    # profile.allowed_stage_ids / forbidden_actions
templates/*                                   # prompt templates
loop_engine/runtime_failures.py                # existing failure reporting
agents/runtime.local.yaml                      # gitignored; not modified
```

## Real-Mode Caveats For Adapter Implementation

Per the user's recommendation, the API adapters will be **skeleton
+ configurable**. Each adapter:

- Reads its env var(s) at invoke time.
- If the dependency is missing (e.g. `anthropic` package), returns
  `AGENT_RUNTIME_FAILURE` with a clear "install anthropic" hint
  — never silently substitutes a stub.
- Treats HTTP 4xx as `AGENT_TRANSPORT_FAILURE` (when appropriate)
  or as a schema-valid 4xx-result — the pool's
  `should_continue_to_next_provider` only retries on
  `runtime_status` failures, **not** on schema-valid 4xx.
- Does **not** make a network call inside a pytest unit test.
  Tests inject a fake adapter via dependency injection (a
  constructor-injected callable) so the API path is exercised
  with a deterministic mock.

`--write-root-report` from Loop 020A is preserved. New probe and
smoke scripts default to writing reports under
`archive/local_runs/<ts>_<name>.md`.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
