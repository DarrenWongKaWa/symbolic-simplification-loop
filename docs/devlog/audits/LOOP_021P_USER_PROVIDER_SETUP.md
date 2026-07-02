# Loop 021P — User Provider Setup

This document tells the user which shell environment variables to
set so that `scripts/probe_reviewer_providers.py` and
`scripts/run_reviewer_provider_smoke.py` can reach a real
reviewer provider.

The runtime contract (Loop 021) is unchanged. Each provider
name in `agents/runtime.local.yaml`'s
`reviewer_provider_pools.ScientificMetaReviewer.providers`
list is configured to read its credentials from shell env vars
**only**. No values are written into the repository.

## Hard Rules

- **Do not paste a real API key into:**
  - `agents/runtime.local.yaml`
  - `agents/runtime.local.example.yaml`
  - any prompt sent to Claude Code / ChatGPT / Codex
  - any chat window UI
  - any `*.md` report under `archive/local_runs/`
  - any file checked in to git
- **API keys must live in:**
  - shell environment variables (`export ...`), or
  - your CI vault's secret manager, or
  - an un-versioned local `.env` file (kept on `.gitignore`).

## Probe Without Keys

```bash
$ unset ANTHROPIC_API_KEY OPENAI_API_KEY OPENAI_COMPATIBLE_API_KEY \
        OPENAI_COMPATIBLE_BASE_URL OPENAI_COMPATIBLE_MODEL \
        LOOP_ENABLE_CLAUDE_CODE LOOP_ENABLE_CODEX

$ python3 scripts/probe_reviewer_providers.py \
    --role ScientificMetaReviewer
```

Expected (5 providers listed, all `DISABLED_BY_ENV`):
```text
role: `ScientificMetaReviewer`
fallback_policy: `runtime_failure_only`
require_real_provider: `True`
forbid_stub: `True`
0. `anthropic_api` (adapter: `anthropic_api`)
   - enabled: False (reason: missing_env:ANTHROPIC_API_KEY)
   - availability_status: DISABLED_BY_ENV
   - runtime_status: NOT_INVOKED
1. `openai_api` (adapter: `openai_api`)
   - enabled: False (reason: missing_env:OPENAI_API_KEY)
2. `openai_compatible_api` (adapter: `openai_compatible_api`)
   - enabled: False (reason: missing_env:OPENAI_COMPATIBLE_API_KEY)
3. `claude_code_cli` (adapter: `command`)
   - enabled: False (reason: missing_env:LOOP_ENABLE_CLAUDE_CODE)
4. `codex_cli_resolver` (adapter: `command`)
   - enabled: False (reason: missing_env:LOOP_ENABLE_CODEX)
```

When at least one provider shows
`availability_status: AVAILABLE`, you can re-run throughput
under the Loop 021 Phase 5R procedure.

## Anthropic Setup

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export ANTHROPIC_MODEL="claude-sonnet-4-5"   # optional; default: claude-sonnet-4-5

python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
python3 scripts/run_reviewer_provider_smoke.py \
  --role ScientificMetaReviewer \
  --provider anthropic_api
```

The `anthropic_api` provider becomes the first enabled +
available provider. Re-running the probe should show its line
with `enabled: True` and `availability_status: AVAILABLE`.

## OpenAI Setup

```bash
export OPENAI_API_KEY="sk-proj-..."
export OPENAI_MODEL="gpt-5.5"           # optional; default: gpt-5

python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
```

## OpenAI-Compatible Setup (Self-Hosted or Local)

```bash
export OPENAI_COMPATIBLE_BASE_URL="https://my-llm.example.com/v1/chat/completions"
export OPENAI_COMPATIBLE_API_KEY="...the key your endpoint expects..."
export OPENAI_COMPATIBLE_MODEL="my-model-name"   # optional

python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
```

Use this option when you want to point at a local LLM (LM Studio,
llama.cpp server, vLLM, Ollama, etc.) without depending on a
cloud provider.

## Codex CLI Setup

```bash
export LOOP_ENABLE_CODEX=1
# Optional: if `codex` is not on PATH
# export LOOP_CODEX_BIN=/Users/.../codex

bash scripts/codex_resolver.sh --probe
```

The probe runs the resolver's PATH-fallback and reports either
the resolved `codex` path or an actionable diagnostic.

## Claude Code CLI Setup

```bash
export LOOP_ENABLE_CLAUDE_CODE=1
command -v claude
```

The `claude_code_cli` adapter uses `claude` (no args) as the
default command. Override by editing
`agents/runtime.local.yaml`'s `claude_code_cli` entry:

```yaml
- name: claude_code_cli
  adapter: command
  command: ["claude"]
  enabled_env: LOOP_ENABLE_CLAUDE_CODE
```

If your `claude` CLI uses different flags, replace the
`command` list (the redactor preserves the resolved command
text in the probe report but redacts env values).

## Anti-Paste Note

> The redactor `loop_engine/secret_redaction.py` strips
> `ANTHROPIC_API_KEY=…` lines and `sk-ant-…` / `sk-proj-…` /
> `Bearer …` tokens from every file the runner writes.
> This is **best-effort** defence in depth — the primary
> defence is that you never paste a key into a tracked file in
> the first place.

## Next Step After Probe Lists An AVAILABLE Provider

Reply with whichever shell vars you set:

- "Anthropic is available"
- "OpenAI is available"
- "OpenAI-Compatible at <base_url> is available"
- "Codex CLI is available"
- "Claude Code CLI is available"

Then I will re-run the Phase 5R procedure with provider-pool
mode enabled. No key values will be echoed back to me, written
to disk, or stored in any prompt.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
