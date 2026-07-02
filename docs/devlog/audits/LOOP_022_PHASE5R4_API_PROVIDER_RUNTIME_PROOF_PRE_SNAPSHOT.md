# Phase 5R-4 — API Provider Runtime Proof — Pre-Snapshot

Captured 2026-07-02 prior to executing Phase 5R-4 route A
throughput retry.

## Current deepest frozen checkpoint

```text
sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision_2026-07-01T18-40-25+00-00
```

(Phase 5R-4 reachable path is therefore 009 → 010 → 011 → 012A → 012B;
the 010 pair-kernel-fusion-pilot checkpoint from the prior phase is
present in checkpoint history but the stages tree currently
ends at 008 — the live tree regressed during the
loop-skill/repo-integration-patch's own pytest, per that patch's
report §"Pre-state vs post-state".)

## autonomous_runs/sigma_abc/checkpoints/

```text
sigma_abc_006_tensorial_sector_architecture_review_2026-07-01T18-40-23+00-00/
sigma_abc_007_pair_sector_basis_closure_pilot_2026-07-01T18-40-24+00-00/
sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision_2026-07-01T18-40-25+00-00/
```

## autonomous_runs/sigma_abc/stages/

```text
sigma_abc_006_tensorial_sector_architecture_review/
sigma_abc_007_pair_sector_basis_closure_pilot/
sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision/
sigma_abc_012c_real_loop_candidate_preparation/
```

(012c stage dir present as a normal follow-on per the prior
patch's work; no promotion has been executed, no
candidate-manifest created.)

## Provider readiness result

```text
$ python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
role: ScientificMetaReviewer
fallback_policy: runtime_failure_only
require_real_provider: True
forbid_stub: True

  anthropic_api          (adapter: anthropic_api)          DISABLED_BY_ENV  (missing_env:LOOP_ENABLE_ANTHROPIC)
  openai_api             (adapter: openai_api)             DISABLED_BY_ENV  (missing_env:LOOP_ENABLE_OPENAI)
  openai_compatible_api  (adapter: openai_compatible_api)  AVAILABLE        (env:LOOP_ENABLE_OPENAI_COMPATIBLE)
  claude_code_cli        (adapter: command)                DISABLED_BY_ENV  (missing_env:LOOP_ENABLE_CLAUDE_CODE)
  codex_cli_resolver     (adapter: command)                DISABLED_BY_ENV  (missing_env:LOOP_ENABLE_CODEX)
```

openai_compatible_api is the single AVAILABLE provider.

## Runner adapter diagnostic result

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

`AdapterSelected=ProviderPoolAdapter` — `LegacyFallbackCommand` is
present as a documented fallback (allowed by `fallback_policy:
runtime_failure_only`), but is NOT the active selection.

## Loop 022S test result

```text
$ python3 -m pytest -q tests/test_loop022s_api_provider_runtime_integration.py
18 passed, 1 warning in 0.64s
```

18/18 PASS — the wiring of `openai_compatible_api` /
`openai_api` / `anthropic_api` into
`loop_engine/reviewer_provider_pool.py::run_pool` is verified
by an existing test suite. This snapshot does NOT modify any
Loop 022S file.

## Repo root contents (top-level only)

```text
.claude/                (claude project memory)
.env                    (private; not touched)
.gitignore
.pytest_cache/
AGENTS.md
LICENSE
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
agents/                 (runtime.local.yaml lives here)
archive/                (local_runs/; one-off outputs)
autonomous_runs/        (per-invocation runner output; live)
autonomous_runs_test/   (pytest sandbox, gitignored)
benchmarks/
case_studies/
docs/
examples/
identities/
loop_config.json
loop_engine/
policies/
profiles/
projects/
pyproject.toml
reports/
schemas/
scripts/
sigma_abc/
skill/
smoke_projects/
templates/
tests/
```

No root-level runner reports leaked. (The
`archive/local_runs/` tree has 012C-related audit files; those
are pre-existing and not produced by Phase 5R-4.)

## Redacted runtime config shape (env-var names only, no values)

```text
agents/runtime.local.yaml — provider declarations
  anthropic_api:
    api_key_env: ANTHROPIC_API_KEY
    model_env:   ANTHROPIC_MODEL
    enabled_env: LOOP_ENABLE_ANTHROPIC
    adapter:     anthropic_api

  openai_api:
    api_key_env: OPENAI_API_KEY
    model_env:   OPENAI_MODEL
    enabled_env: LOOP_ENABLE_OPENAI
    adapter:     openai_api

  openai_compatible_api:
    api_key_env:   OPENAI_COMPATIBLE_API_KEY
    base_url_env:  OPENAI_COMPATIBLE_BASE_URL
    model_env:     OPENAI_COMPATIBLE_MODEL
    enabled_env:   LOOP_ENABLE_OPENAI_COMPATIBLE
    adapter:       openai_compatible_api

  claude_code_cli:
    enabled_env: LOOP_ENABLE_CLAUDE_CODE
    adapter:     command

  codex_cli_resolver:
    enabled_env: LOOP_ENABLE_CODEX
    adapter:     command
```

No API key values are recorded in this snapshot. The single
provider that has its enable flag set
(`LOOP_ENABLE_OPENAI_COMPATIBLE`) is `openai_compatible_api`.

## Pre-snapshot conclusions

- Preflight: GREEN (3/3 checks pass).
- Single AVAILABLE provider is `openai_compatible_api`.
- Loop 022S wiring intact (18/18 tests pass).
- Adapter selection: `ProviderPoolAdapter` confirmed.
- Clean-source guard: GREEN (no active background runners).
- Deepest frozen checkpoint: 008.
- Reachable path for Phase 5R-4 route A: 009 → 010 → 011 → 012A → 012B.

Proceeding to Step 4 (route A throughput retry).
