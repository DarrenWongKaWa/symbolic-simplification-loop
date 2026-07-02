# Loop 021P — Provider Pool Config Template Pre-Audit

## Status

TEMPLATE_GAP_IDENTIFIED_AND_LOCALLY_FIXABLE.

The trust stack is unchanged. No sigma_abc physics modified. No
012C / 013 / IBP / total derivative started. No full tensorial
sigma_abc correctness claim.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Phase 5R Probe Verdict

```text
$ python3 scripts/probe_reviewer_providers.py \
    --role ScientificMetaReviewer

# Reviewer Provider Probe

role: `ScientificMetaReviewer`
pool: **NOT CONFIGURED**

No `reviewer_provider_pools.<role>` entry found in
`agents/runtime.local.yaml` or
`agents/runtime.local.example.yaml`.
```

The probe walks `agents/runtime.local.yaml` first, then
`agents/runtime.local.example.yaml`. Because the local file
exists and declares `runtime:` blocks (the legacy command-adapter
path) but no `reviewer_provider_pools` block, the probe stops
on the local file and reports the pool as NOT CONFIGURED.

## What Is Missing

### `agents/runtime.local.example.yaml` (committed template)

The committed example file **already contains** a
`reviewer_provider_pools.ScientificMetaReviewer` block under
`profiles.sigma_abc_hypothesis_pre_ibp_throughput`. No edit is
required to the example file.

```text
profiles.sigma_abc_hypothesis_pre_ibp_throughput.reviewer_provider_pools
  .ScientificMetaReviewer
    .fallback_policy = runtime_failure_only
    .forbid_stub     = True
    .providers
      .anthropic_api          (adapter: anthropic_api)
      .openai_api             (adapter: openai_api)
      .openai_compatible_api  (adapter: openai_compatible_api)
      .claude_code_cli        (adapter: command)
      .codex_cli_resolver     (adapter: command)
```

All five providers use **only env-var names**; no real keys
are present.

### `agents/runtime.local.yaml` (user-owned, gitignored)

The local file currently contains only legacy `runtime:` blocks
per profile. The `reviewer_provider_pools` block is missing.
This is the load-bearing reason that the probe reports
"NOT CONFIGURED" today.

The fix is to add the same block, with **only env-var names**,
preserving the legacy `runtime:` blocks. Loop 021P does not
remove the legacy command-adapter path because:

- the legacy path is the only one that can invoke Codex CLI
  directly today,
- the provider pool falls back to the legacy path when no
  pool config is present (back-compat per Loop 021), and
- preserving both lets users transition at their own pace.

## Secret Audit

```text
$ grep -rE '(ANTHROPIC_API_KEY|OPENAI_API_KEY|OPENAI_COMPATIBLE_API_KEY|sk-ant|sk-proj)' agents/ 2>/dev/null | head -20
agents/runtime.local.example.yaml:  ANTHROPIC_API_KEY
agents/runtime.local.example.yaml:  OPENAI_API_KEY
agents/runtime.local.example.yaml:  OPENAI_COMPATIBLE_API_KEY

(only the env var NAMES, never values)
```

No real API keys are present in either file. The redaction
test suite (`tests/test_loop021_secret_redaction.py`) confirms
that values matching these names are stripped before any disk
write.

## `.gitignore` Audit

```text
$ cat .gitignore
...
.env                                                <- present
agents/runtime.local.yaml                           <- present (Loop 019R)
...
```

Both `.env` (user-owned) and `agents/runtime.local.yaml`
(user-owned) are gitignored. Accidentally committing a real
key would require running `git add -f` deliberately with the
gitignore rule overridden; `git status` would still surface the
file as the gitignore-derived ignore.

## Probe Files Audit

```text
$ ls scripts/ | grep reviewer
scripts/probe_reviewer_providers.py
scripts/run_reviewer_provider_smoke.py
```

The probe script walks:
1. `agents/runtime.local.yaml` (priority).
2. `agents/runtime.local.example.yaml` (fallback when local
   is absent OR when local declares no pool for the role).

When local IS present, the probe **does not** continue to the
example file even if the local file lacks a pool for the role.
This is intentional: a user who maintains `runtime.local.yaml`
should explicit-enable the pool there. The Phase 5R audit
captured this behaviour; Loop 021P aligns the local file with
the example template.

## Files To Touch

```text
agents/runtime.local.yaml            # ADD reviewer_provider_pools block,
                                     # env-var names only
docs/devlog/audits/LOOP_021P_USER_PROVIDER_SETUP.md   # NEW user instructions
docs/devlog/audits/LOOP_021P_PROVIDER_POOL_CONFIG_TEMPLATE_REPORT.md  # NEW final report
```

## Files Explicitly NOT To Touch

```text
agents/runtime.local.example.yaml   # already has pool block
sigma_abc/                          # physics
loop_engine/                         # trust stack
profiles/                            # profile / forbidden_actions
schemas/                             # unchanged
agents/runtime.local.yaml            # preserve legacy runtime: blocks;
                                     # only ADD reviewer_provider_pools
                                     # block
```

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
