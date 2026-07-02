# API Keys

The reviewer provider pool reads API keys from environment
variables only. Real keys **must never** be written into the
repository or any file under `agents/`.

## Why Env Vars

- The configuration file `agents/runtime.local.yaml` is
  gitignored precisely so users can set personal per-machine
  overrides without leaking secrets.
- The example file `agents/runtime.local.example.yaml` is
  committed and uses **only** env-var names, never values.
- The redactor (`loop_engine/secret_redaction.py`) substitutes
  values with `<redacted:NAME>` markers before any text is
  written to disk (stdout, stderr, prompt.md,
  invocation_summary, pool_result).

## Supported Env Vars

| Env var | Adapter | Required |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | anthropic_api | yes (for the Anthropic provider) |
| `ANTHROPIC_MODEL` | anthropic_api | no (defaults to `claude-sonnet-4-5`) |
| `OPENAI_API_KEY` | openai_api | yes (for the OpenAI provider) |
| `OPENAI_MODEL` | openai_api | no (defaults to `gpt-5`) |
| `OPENAI_COMPATIBLE_API_KEY` | openai_compatible_api | yes (for an OpenAI-compatible endpoint) |
| `OPENAI_COMPATIBLE_BASE_URL` | openai_compatible_api | yes |
| `OPENAI_COMPATIBLE_MODEL` | openai_compatible_api | no (defaults to `gpt-5`) |
| `LOOP_ENABLE_CODEX` | command (codex_cli_resolver) | any non-empty value enables the provider |
| `LOOP_ENABLE_CLAUDE_CODE` | command (claude_code_cli) | any non-empty value enables the provider |
| `LOOP_CODEX_BIN` | command (codex_resolver.sh PATH-fallback) | absolute path to a `codex` binary |

## Setting Keys In Your Shell

```bash
# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...
export ANTHROPIC_MODEL=claude-sonnet-4-5

# OpenAI
export OPENAI_API_KEY=sk-proj-...
export OPENAI_MODEL=gpt-5

# OpenAI-Compatible (e.g. self-hosted)
export OPENAI_COMPATIBLE_API_KEY=...   # the "key" your endpoint accepts
export OPENAI_COMPATIBLE_BASE_URL=https://my-llm.example.com/v1/chat/completions
export OPENAI_COMPATIBLE_MODEL=my-model-name

# Codex CLI (PATH fallback for environments without codex in $PATH)
export LOOP_ENABLE_CODEX=1
export LOOP_CODEX_BIN=/Users/.../codex  # optional; resolver already searches

# Claude Code CLI
export LOOP_ENABLE_CLAUDE_CODE=1
```

## Verifying Redaction

The redactor detects keys by pattern plus env-var name. To
verify your key is redacted in every disk write, run the
probe script:

```bash
python3 scripts/probe_reviewer_providers.py \
  --role ScientificMetaReviewer
```

The output report at `archive/local_runs/<UTC>_PROBE_…md`
**never** contains the key, even if your prompt does.
The script's `failure_summary_redacted` field is a string
literal — it cannot leak your key through that channel
either.

## What Happens If a Key Is Missing

When `api_key_env` is set in the provider config but the env
var itself is unset, the pool emits:

```text
availability_status: AVAILABLE
runtime_status: AGENT_RUNTIME_FAILURE
failure_summary_redacted: "ANTHROPIC_API_KEY env var not set"
```

The chain treats this as a retryable failure (per the
`runtime_failure_only` policy) and falls through to the next
provider. The chain ultimately emits
`AGENT_ALL_PROVIDERS_UNAVAILABLE` if no provider has its key.

If the chain emits `AGENT_ALL_PROVIDERS_UNAVAILABLE`, the runner
writes `decision.action = PROVISIONAL_FREEZE_WITH_REVIEW_DEBT`
(unchanged from Loop 014–017). The review debt then opens
correctly and `freeze_preconditions` rejects freeze. The chain
does NOT silently substitute a stub.

## Security Notes

- **Never commit real keys** to any file under this repo.
- **Never paste real keys into prompt text.** If you do, the
  redactor strips them out, but pasting is still bad practice.
- **API keys in CI** must come from your CI vault; this repo
  assumes that and does not document any third-party key
  management tool.
- The redactor is best-effort and **does not** redact keys that
  are fragmented across multiple lines or hidden inside
  base64-encoded blobs. Treat your shell environment as the
  authoritative secret store.

## Runner Wiring (Loop 022)

Loop 022 wires the provider pool into the **autonomous runner's
reviewer invocation path**. Previously the pool was consulted
only by the probe (`scripts/probe_reviewer_providers.py`); now
the runner itself selects `ProviderPoolAdapter` whenever
`profile.reviewer_provider_pools.<ReviewerRole>` is configured
AND `profile.agents.require_real_invocation` is true.

This means:

- The probe (`scripts/probe_reviewer_providers.py`) is still
  the right tool for verifying a key is present and a provider
  is `AVAILABLE`.
- When a real provider (e.g. `openai_compatible_api` with
  `OPENAI_COMPATIBLE_API_KEY`) is enabled and the runner runs
  `ScientificMetaReviewer`, the pool picks the first enabled
  provider. On retryable runtime failure, it falls through to
  the next provider without involving the runner.
- When **all** providers fail retryably, the pool emits
  `AGENT_ALL_PROVIDERS_UNAVAILABLE` and the runner's existing
  `decision.action = PROVISIONAL_FREEZE_WITH_REVIEW_DEBT`
  semantics apply unchanged. `freeze_preconditions` still
  requires `human_signoff.yaml`. Stub is never a quiet fallback.

### Shell / Subprocess Isolation

Some development harnesses (Claude Code, many CI runners) do
NOT propagate interactive-shell exports into subprocess
environments. If `python3 scripts/probe_reviewer_providers.py
--role ScientificMetaReviewer` reports `AVAILABLE`, but
`scripts/run_autonomous_loop.py` reports the same provider as
`NOT_AVAILABLE` (env: LOOP_ENABLE_*), export the keys in the
**same** shell that launches the runner, or use a gitignored
local `.env` (loaded by `loop_engine.config.load_dotenv`).

```bash
# (preferred for CI / hermetic shells)
cat > /path/to/.env <<'EOF'
OPENAI_COMPATIBLE_API_KEY=sk-...
OPENAI_COMPATIBLE_BASE_URL=https://api.deepseek.com
OPENAI_COMPATIBLE_MODEL=deepseek-v4-pro
LOOP_ENABLE_OPENAI_COMPATIBLE=1
EOF

# Run the runner from the repo root so the loader finds .env.
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint --auto-patch
```

The loader never overwrites an existing env var (interactive
shell takes precedence) and never expands shell syntax.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
