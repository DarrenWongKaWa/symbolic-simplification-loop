# Reviewer Provider Pool

Loop 021 replaces the implicit single-provider dependency with a
configurable **reviewer provider pool**. Reviewer roles in
profiles (e.g. `ScientificMetaReviewer`) are satisfied by one of
several **providers** in declared order. The pool falls through
to the next provider ONLY on retryable runtime failures:

```text
RETRYABLE (allowed to fall through):
  AGENT_QUOTA_LIMIT
  AGENT_TIMEOUT
  AGENT_NO_OUTPUT
  AGENT_COMMAND_NOT_FOUND
  AGENT_TRANSPORT_FAILURE
  AGENT_RUNTIME_FAILURE

STOP IMMEDIATELY (no fallback):
  any schema-valid reviewer verdict
    (PASS, PASS_WITH_CAVEAT, FAIL, NEEDS_PATCH, BLOCKED)
  boundary-audit unsafe
  full-tensorial claim detected
  IBP started without approval
```

A schema-valid FAIL or NEEDS_PATCH is exactly the same stopping
point as a PASS. The pool must never ask another provider to
"find a different verdict" — that would convert a deterministic
schema-valid rejection into a hopeful retry, which violates the
trust stack.

## Hard Contracts

- **ScientificMetaReviewer remains a required reviewer role.**
  Loops 013 / 014 / 015 do not change.
- **`forbid_stub: true`** is the default. The pool refuses
  `adapter: stub` providers in production even if the profile
  allows stub in tests.
- **`require_real_provider: true`** is the default. When no
  provider is enabled + available, the pool emits
  `AGENT_ALL_PROVIDERS_UNAVAILABLE` and opens the review debt.
  It never silently substitutes a stub.
- **Secret redaction is on by default and cannot be disabled.**
  API keys set in env or pasted into prompts are redacted before
  any text is written to disk (stdout, stderr, prompt.md,
  invocation_summary, pool_result).

## Configuration

Edit `agents/runtime.local.yaml` (gitignored). The example file
`agents/runtime.local.example.yaml` contains a fully usable pool
template for the `ScientificMetaReviewer` role under the
`sigma_abc_hypothesis_pre_ibp_throughput` profile:

```yaml
profiles:
  sigma_abc_hypothesis_pre_ibp_throughput:
    reviewer_provider_pools:
      ScientificMetaReviewer:
        fallback_policy: runtime_failure_only
        require_real_provider: true
        forbid_stub: true
        providers:
          - name: anthropic_api
            adapter: anthropic_api
            api_key_env: ANTHROPIC_API_KEY
            model_env: ANTHROPIC_MODEL
            enabled_env: ANTHROPIC_API_KEY
          - name: openai_api
            ...
          - name: codex_cli_resolver
            adapter: command
            command: ["bash", "${REPO_ROOT}/scripts/codex_resolver.sh", "{agent_name}", "{prompt_path}", "{output_path}", "{stage_dir}"]
            enabled_env: LOOP_ENABLE_CODEX
```

Each provider's `enabled` field is one of:

- `enabled: true|false` (literal bool),
- `enabled_env: <NAME>` → looks up `os.environ[<NAME>]` and coerces.

`forbid_stub: true` rejects `adapter: stub` entries regardless of
`enabled`.

## Reading the Result

A successful invocation writes two sibling files:

```text
.loop/agent_invocations/ScientificMetaReviewer/invocation_summary.json
.loop/agent_invocations/ScientificMetaReviewer/pool_result.json
```

- `invocation_summary.json` is the existing summary fields,
  unchanged from Loop 014–017. The runner's existing callers
  continue to read this file.
- `pool_result.json` is the ADDITIVE new file. It includes:
  `reviewer_role`, `selected_provider`, `provider_attempts`,
  `adapter`, `actually_invoked`, `stub_used`, `runtime_status`,
  `schema_valid`, `verdict`, `retryable`, `fallback_reason`,
  `secret_redaction_applied`.

When the chain exhausts with retryable failures:

```json
{
  "runtime_status": "AGENT_ALL_PROVIDERS_UNAVAILABLE",
  "retryable": true,
  "review_debt_required": true,
  "fallback_reason": "AGENT_QUOTA_LIMIT"
}
```

The runner then writes `decision.action =
PROVISIONAL_FREEZE_WITH_REVIEW_DEBT` (unchanged from Loop 014–017).
The downstream `freeze_preconditions` semantics are **preserved
exactly** — including the requirement that `human_signoff.yaml`
exist for full freeze.

## Semantic-Verdict Behaviour

A schema-valid reviewer result stops the chain regardless of its
verdict. The pool is an **availability** layer, not a
**gatekeeping** layer.

- `verdict: PASS` or `verdict: PASS_WITH_CAVEAT` → chain stops,
  `freeze_evidence_valid: true` (subject to other freeze
  preconditions).
- `verdict: FAIL` or `verdict: NEEDS_PATCH` → chain stops,
  `freeze_evidence_valid: false`, review debt opens.
- `verdict: BLOCKED` → chain stops, freeze failed.

A reviewer that returns `verdict: FAIL` is authoritative. Do not
ask another provider for a "better" verdict.

## Boundary Status (preserved)

- `freeze_preconditions` unchanged.
- `completion_matrix.freeze_eligible` unchanged.
- `human_signoff.permission.freeze_checkpoint` unchanged.
- `boundary_audit.dc_caveat_preserved`, `overclaim_detected`,
  `ibp_started_without_approval`, `full_tensorial_claim_detected`
  fields unchanged.

## Quick Probe

```bash
python3 scripts/probe_reviewer_providers.py \
  --role ScientificMetaReviewer
```

Output (default) goes to
`archive/local_runs/<UTC-timestamp>_PROBE_REVIEWER_PROVIDERS_<ROLE>.md`.
Use `--write-root-report` to additionally emit a copy at the
repo root.

## Provider Pool in Autonomous Runner (Loop 022)

Loop 022 wires the Loop 021 provider pool into the actual
runner invocation path. **Probe is no longer the only consumer
of the pool**: the autonomous runner now selects the pool over
the legacy `runtime.command` path whenever a `reviewer_provider_pools.<role>`
block is configured for the active profile AND the profile's
`agents.require_real_invocation` is true.

```text
build_adapter()
  ├─ profile.reviewer_provider_pools.<ReviewerRole> present
  │    AND profile.agents.require_real_invocation == True
  │  → ProviderPoolAdapter (writes invocation_summary.json +
  │                           pool_result.json)
  │  Falls through on retryable runtime failures only.
  │
  ├─ profile.runtime.adapter == "command" | "codex_subagent"
  │    AND no pool configured
  │  → CommandAgentAdapter / CodexSubagentAdapter (legacy)
  │
  └─ profile.runtime.adapter == "stub"
     AND profile.agents.allow_stub_for_tests == True
    → DryRunStubAdapter (tests only)
```

### What this changes for users

- **Probe only checks provider availability.** Probe is still
  the right tool to confirm `openai_compatible_api` is
  `AVAILABLE` from the runner's shell.
- **Runner now also uses the provider pool.** A dry `build_adapter(profile)`
  call from inside `loop_engine.agent_runtime` returns
  `ProviderPoolAdapter` whenever the conditions above are met.
- **`runtime.command` remains the legacy fallback.** When no
  pool is configured, the runner uses the exact
  `runtime.command` list it used before. No silent
  substitution.
- **API keys must be exported in the same shell that launches
  the runner.** Subprocess env isolation in some harnesses
  (Claude Code, CI) means `export OPENAI_API_KEY=...` inside
  an interactive shell may not propagate. Use `agents/.env` or
  the same shell that calls `scripts/run_autonomous_loop.py`.
- **`semantic FAIL` is not retried.** A schema-valid
  `verdict: FAIL` (or `NEEDS_PATCH`) stops the chain — never
  fall through to another provider looking for a different
  answer.
- **Runtime failure may fallback to another provider.** The
  pool honours `fallback_policy: runtime_failure_only` exactly
  as before; `AGENT_QUOTA_LIMIT`, `AGENT_TIMEOUT`,
  `AGENT_NO_OUTPUT`, `AGENT_COMMAND_NOT_FOUND`,
  `AGENT_TRANSPORT_FAILURE`, `AGENT_RUNTIME_FAILURE` are the
  only statuses that fall through.

### What's NOT modified

- `freeze_preconditions` — unchanged.
- `completion_matrix` — unchanged.
- `human_signoff` — unchanged. `human_signoff.yaml` is still
  required for full freeze.
- `pre_run_gate` — unchanged.
- `sigma_abc/` physics — unchanged. 012C / 013 / IBP / total
  derivative untouched.

### Re-verify after wiring

```bash
# 1. probe — confirms the pool is configured & a provider is AVAILABLE
python3 scripts/probe_reviewer_providers.py \
  --role ScientificMetaReviewer

# 2. dry adapter selection — confirms the runner WOULD select the pool
python3 -c "
from loop_engine.agent_runtime import build_adapter
profile = {
  'agents': {'require_real_invocation': True},
  'runtime': {'adapter': 'command',
              'command': ['echo', 'legacy']},
  'reviewer_provider_pools': {
    'ScientificMetaReviewer': {
      'providers': [{'name': 'x', 'adapter': 'command',
                     'command': ['true']}],
    },
  },
}
a = build_adapter(profile, 'sigma_abc_hypothesis_pre_ibp_throughput')
print(type(a).__name__)
"
# expected: ProviderPoolAdapter
```

## Smoke Test

```bash
export ANTHROPIC_API_KEY=sk-ant-...  # do not commit
python3 scripts/run_reviewer_provider_smoke.py \
  --role ScientificMetaReviewer \
  --provider anthropic_api
```

Output (default) goes to
`archive/local_runs/<UTC-timestamp>_REVIEWER_PROVIDER_SMOKE_<ROLE>.md`.
The smoke does NOT touch sigma_abc stages, does NOT run 012C
promotion, does NOT start Stage 013.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
