# Loop 021 — Phase 5R Provider Readiness Audit

## Status

NO_PROVIDER_POOL_CONFIGURED_RETRY_HALTED.

```text
Final classification (per user spec):
C. "Retry not attempted; reason: no available reviewer
   provider / clean scheduler active / missing approval."

In this audit, the load-bearing reason is "no available reviewer
provider pool": the runner's `agents/runtime.local.yaml` declares
legacy `runtime:` blocks but no `reviewer_provider_pools` section.
```

`sigma_abc` physics NOT modified. No 012C / 013 / IBP / total
derivative started. No full tensorial sigma_abc correctness
claim.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Probe Behaviour (Fresh Evidence)

```text
$ python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
# Reviewer Provider Probe

role: `ScientificMetaReviewer`
pool: **NOT CONFIGURED**

No `reviewer_provider_pools.<role>` entry found in
`agents/runtime.local.yaml` or
`agents/runtime.local.example.yaml`.
```

The probe walks `agents/runtime.local.yaml` first
(gitignored; user-owned) then
`agents/runtime.local.example.yaml` (committed template).

- `agents/runtime.local.yaml` exists and declares
  `profiles.<…>.runtime` per profile but no
  `reviewer_provider_pools.<role>` block for any role. The
  legacy `runtime:` block remains in place and is the active
  configuration.
- `agents/runtime.local.example.yaml` DOES contain a
  `reviewer_provider_pools.ScientificMetaReviewer` block under
  `profiles.sigma_abc_hypothesis_pre_ibp_throughput` —
  **but** the probe only walks the committed example file when
  the local file is absent. Because the local file IS present
  (even if it has no `reviewer_provider_pools` key), the probe
  does not fall through to the example. That is the correct
  behaviour: users with a hand-curated `runtime.local.yaml`
  must intentionally add a `reviewer_provider_pools` block.

## Env Vars Currently Set On This Machine

```text
ANTHROPIC_API_KEY=<unset>
ANTHROPIC_MODEL=claude-sonnet-4-5
OPENAI_API_KEY=<unset>
OPENAI_MODEL=<unset>
OPENAI_COMPATIBLE_API_KEY=<unset>
OPENAI_COMPATIBLE_BASE_URL=<unset>
OPENAI_COMPATIBLE_MODEL=<unset>
LOOP_ENABLE_CODEX=<unset>          # Codex CLI path-fallback is available via
                                  # scripts/codex_resolver.sh regardless
LOOP_CODEX_BIN=<unset>             # resolver searches known absolute paths
LOOP_ENABLE_CLAUDE_CODE=<unset>
```

A single model name (`ANTHROPIC_MODEL=claude-sonnet-4-5`) is
set, but no API key is set. The pool's
`invocation_anthropic_api` skeleton requires `ANTHROPIC_API_KEY`
and would return `AGENT_RUNTIME_FAILURE` with the hint
"ANTHROPIC_API_KEY env var not set".

Codex is reachable via `scripts/codex_resolver.sh` PATH-fallback,
but `LOOP_ENABLE_CODEX` is unset, so the pool would mark the
Codex provider as `DISABLED_BY_ENV`. The loop 019R finding
("Codex CLI returns `AGENT_QUOTA_LIMIT` on this machine")
remains the load-bearing reason to **not** rely on Codex for
Phase 5R.

## Stub Check

```text
Forbid stub default: True
Any `adapter: stub` entries in `agents/runtime.local.yaml`: none
result.stub_used for any pool path: False (default behaviour)
```

No silent stub substitution. Production reviewers remain
real.

## Secret Redaction Check

`loop_engine.secret_redaction.redact_secrets` was run over the
probe output before being written to disk. The probe markdown
contains no `ANTHROPIC_API_KEY` value because no key is set;
the failure_summary contains only the literal "env var not set"
hint.

## Root Cleanliness

```text
$ ls *.md *.json
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
loop_config.json
```

Five root-level files, no runner-emitted reports. Loop 020A
hygiene held.

## Why This Audit Halts

Three preconditions from the user's prompt are not all
satisfied:

1. **Quota probe is not clear, but more importantly no provider
   pool is configured.** Without a `reviewer_provider_pools`
   block, the runner falls back to the legacy
   `runtime.adapter: command` single-provider path. That path
   points at `bash scripts/codex_resolver.sh`, which calls
   `codex`, which itself returns `AGENT_QUOTA_LIMIT`.
2. **No API key is currently set on this machine.** Even if a
   `reviewer_provider_pools` block were added to
   `runtime.local.yaml` now, the Anthropic / OpenAI providers
   would each emit `AGENT_RUNTIME_FAILURE` ("API_KEY env var
   not set"). The Codex CLI path remains the only one that
   actually invokes a real provider, and Codex is quota-limited.
3. **Defer to the human partner.** Setting real API keys is a
   user decision, not a code-side action. The probe is the
   audit's recommended "scope for the human" action; nothing
   beyond writing a report and stopping is appropriate in this
   session.

The right next action depends on what the user wants:

- (a) Set `ANTHROPIC_API_KEY` (and optionally
  `ANTHROPIC_MODEL`) so the Anthropic provider can serve
  `ScientificMetaReviewer`. Then re-run probe. If you have
  Anthropic access, this is the smallest manual step to unlock
  Phase 5R.

- (b) Set `OPENAI_API_KEY` (and optionally
  `OPENAI_MODEL=gpt-5.5`) so the OpenAI provider can serve.

- (c) Wait for Codex CLI quota to clear (RetryAfter was
  `9:14 PM` in Loop 019R), then re-run throughput against
  Codex only.

- (d) Add an OpenAI-compatible local endpoint
  (`OPENAI_COMPATIBLE_BASE_URL`) and set
  `OPENAI_COMPATIBLE_API_KEY` + `OPENAI_COMPATIBLE_MODEL`.

Until one of (a) / (b) / (c) / (d) is in place, Phase 5R cannot
be safely retried. Loop 019R Phase 5 had the same dependency,
and `LOOP_021_QUOTA_STILL_ACTIVE_REPORT.md` recorded that
quota is still active.

## Files Examined

```text
agents/runtime.local.yaml
agents/runtime.local.example.yaml
scripts/probe_reviewer_providers.py
loop_engine/reviewer_provider_pool.py
loop_engine/api_review_provider.py
autonomous_runs/sigma_abc/AUTONOMOUS_LOOP_RUN_REPORT.md
docs/devlog/audits/LOOP_021_REVIEWER_PROVIDER_POOL_REPORT.md
docs/devlog/audits/LOOP_019R_QUOTA_STILL_ACTIVE_REPORT.md
```

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
