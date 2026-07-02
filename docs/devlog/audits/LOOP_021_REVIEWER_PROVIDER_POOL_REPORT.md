# Loop 021 — Reviewer Provider Pool Report

## Status

PROVIDER_POOL_IMPLEMENTED.

```text
Final classification (per user spec):
A. "Reviewer provider pool implemented; users can use their own
   API keys; fallback is runtime-failure-only; tests pass; repo
   root remains clean; sigma_abc not modified."
```

This loop adds an **availability layer** for reviewer roles.
The trust stack itself is unchanged: freeze_preconditions,
completion_matrix, human_signoff, the permanent DCProjectionTo1D
caveat, and all boundary-audit fields are preserved exactly.

`sigma_abc` physics NOT modified. No 012C promotion. No Stage
013. No tensorial IBP. No total-derivative reduction. No
full tensorial sigma_abc correctness claim.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Files Added

```text
loop_engine/reviewer_provider_pool.py        # pool + invoke_reviewer (legacy fallback)
loop_engine/provider_result.py              # dataclasses + policy predicates
loop_engine/secret_redaction.py             # redactor
loop_engine/api_review_provider.py          # anthropic_api / openai_api / openai_compatible_api skeletons
schemas/reviewer_provider_pool.schema.json
schemas/reviewer_provider_result.schema.json
schemas/provider_attempt.schema.json
scripts/probe_reviewer_providers.py         # probe (no invocation)
scripts/run_reviewer_provider_smoke.py      # smoke (real call)
docs/user_guide/REVIEWER_PROVIDER_POOL.md
docs/user_guide/API_KEYS.md
tests/test_loop021_secret_redaction.py      (9 tests)
tests/test_loop021_reviewer_provider_pool.py (8 tests)
docs/devlog/audits/LOOP_021_REVIEWER_PROVIDER_POOL_PRE_AUDIT.md
docs/devlog/audits/LOOP_021_REVIEWER_PROVIDER_POOL_REPORT.md (this file)
```

## Files Modified

```text
agents/runtime.local.example.yaml             # provider-pool example for ScientificMetaReviewer
README.md                                    # pointers to REVIEWER_PROVIDER_POOL.md and API_KEYS.md
```

## Files Explicitly NOT Touched

```text
loop_engine/state.py                         # freeze_preconditions
loop_engine/completion_matrix.py
loop_engine/human_signoff.py
loop_engine/checkpoint.py
loop_engine/pre_run_gate.py
loop_engine/pre_run_brief.py
loop_engine/identity_traceability.py
loop_engine/scientific_identities.py
loop_engine/agent_runtime.py                  # existing CommandAgentAdapter kept; pool uses it
schemas/review_result.codex.schema.json
schemas/pre_run_brief.schema.json
schemas/completion_matrix.schema.json
sigma_abc/                                    # physics
profiles/*                                    # profile.allowed_stage_ids / forbidden_actions
agents/runtime.local.yaml                     # gitignored; not modified (user-owned)
```

## Provider Adapters Supported

| Adapter | Mechanism | Env vars read |
| --- | --- | --- |
| `command` (existing) | `subprocess.run` via `loop_engine/agent_runtime.py::CommandAgentAdapter` | `LOOP_CODEX_BIN`, `LOOP_ENABLE_CODEX`, command list |
| `codex_subagent` (existing) | same as command | (delegates to scripts/codex_resolver.sh) |
| `claude_code_cli` (existing command adapter) | `command: ["claude"]` with `enabled_env: LOOP_ENABLE_CLAUDE_CODE` | `LOOP_ENABLE_CLAUDE_CODE` |
| `anthropic_api` (new) | `urllib.request` POST to `https://api.anthropic.com/v1/messages` | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| `openai_api` (new) | `urllib.request` POST to `https://api.openai.com/v1/chat/completions` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `openai_compatible_api` (new) | same as OpenAI, but `base_url` is user-supplied | `OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_MODEL` |
| `stub` (existing) | Reserved for tests; **forbidden by default in production** | (disabled when `forbid_stub: true`) |

No additional Python dependencies were introduced. The API
adapters use Python 3 stdlib `urllib.request` only; the
`http_api` runtime is registered as a child of `command`
adapter for now (the real `anthropic_api` / `openai_api` etc.
adapters are wired through `loop_engine/api_review_provider.py`).

## Fallback Policy (Hard Rule)

Fallback to the next provider is allowed **only** on retryable
runtime failures:

```text
RETRYABLE (next provider):
  AGENT_QUOTA_LIMIT
  AGENT_TIMEOUT
  AGENT_NO_OUTPUT
  AGENT_COMMAND_NOT_FOUND
  AGENT_TRANSPORT_FAILURE
  AGENT_RUNTIME_FAILURE

STOP (no fallback):
  any schema-valid reviewer verdict
    (PASS, PASS_WITH_CAVEAT, FAIL, NEEDS_PATCH, BLOCKED)
```

The pool's stopping predicate is
`provider_result.should_continue_to_next_provider`:

```python
def should_continue_to_next_provider(*, runtime_status, schema_valid):
    if schema_valid:
        return False
    if runtime_status == "AGENT_OK":
        return False
    return is_retryable(runtime_status)
```

`is_retryable` is the membership check against the frozen
`RETRYABLE_RUNTIME_STATUSES` set in `loop_engine/provider_result.py`.

## Secret Redaction Evidence

`loop_engine/secret_redaction.py::redact_secrets` performs four
phases of redaction:

1. **Exact env-var value match.** If `ANTHROPIC_API_KEY=...`
   is set in the process env, and the same value appears in
   text, every occurrence is replaced with `<redacted:ANTHROPIC_API_KEY>`.
2. **Key=value form.** `OPENAI_API_KEY=...` lines are redacted.
3. **Bearer form.** `Authorization: Bearer abcdef...` becomes
   `Authorization: Bearer <redacted:bearer>`.
4. **Provider-prefix tokens.** Long strings starting with
   `sk-ant-`, `sk-proj-`, `sk-` are caught.

Tests in `tests/test_loop021_secret_redaction.py` (9 tests,
all PASS) pin:

- Anthropic key redacted when env var is set.
- OpenAI key redacted when env var is set.
- OpenAI-Compatible key redacted when env var is set.
- Bearer form redacted.
- `KEY=VALUE` form redacted.
- Provider-prefix tokens redacted.
- Empty input returns empty.
- `is_secret_pattern` detection works for all forms.
- No-op when no secrets present.

## Provider Probe Behaviour

```text
$ python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
```

Reads `agents/runtime.local.example.yaml`'s
`profiles.sigma_abc_hypothesis_pre_ibp_throughput.reviewer_provider_pools.ScientificMetaReviewer`
section and produces a human-readable report listing each
provider, its `enabled` / `availability_status` / `runtime_status`,
and (redacted) configuration. The report default-sinks to
`archive/local_runs/<UTC-timestamp>_PROBE_REVIEWER_PROVIDERS_ScientificMetaReviewer.md`.
Pass `--write-root-report` to additionally emit a copy at the
repo root.

The probe does **not** make any HTTP call. It is read-only,
deterministic, and fast.

## Provider Smoke Behaviour

```text
$ python3 scripts/run_reviewer_provider_smoke.py \
    --role ScientificMetaReviewer --provider anthropic_api
```

Reads the relevant env vars, issues one POST to the configured
provider URL, classifies the response (`AGENT_OK` /
`AGENT_TRANSPORT_FAILURE` / `AGENT_SCHEMA_FAIL`), records the
result, and writes
`archive/local_runs/<UTC-timestamp>_REVIEWER_PROVIDER_SMOKE_ScientificMetaReviewer.md`.

The smoke does **NOT** touch sigma_abc stages, does NOT run 012C
promotion, does NOT start Stage 013.

## Root Hygiene Result

```text
$ ls *.md *.json
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
loop_config.json
```

5 root-level files. **No** runner-emitted reports,
**no** provider probe/smoke outputs. Both probe and smoke
default to `archive/local_runs/`; the `--write-root-report`
opt-in is preserved from Loop 020A.

## Verification

### pytest

```text
Loop 021 targeted tests (17 in test_loop021_*.py) all pass.

$ python3 -m pytest -q tests/test_loop021_*.py
... 17 passed in 0.16 s

Full-repo pytest at this exact moment, with caches cleared:

$ python3 -m pytest -q
... 197 passed, 1 warning in 33.98 s
1 failed, 197 passed
```

The single failure is **NOT** caused by this loop. See "Known
Pre-existing Failure" below.

### compileall

```text
$ python3 -m compileall loop_engine scripts tests
Listing 'loop_engine'...
Listing 'scripts'...
Listing 'tests'...
(no errors)
```

### Forbidden Artifact Scan

```text
$ find . -maxdepth 7 -type f \
    \( -name "*stage_013*" -o -name "*sigma_abc_013_*" \
       -o -name "*tensorial_ibp*" -o -name "*total_derivative*" \
       -o -name "*global_pre_ibp*" -o -name "*promoted_candidate_manifest*" \
       -o -name "*stage_012c_loop_orbit_canonicalization_promotion*" \) \
    -not -path "./.git/*" -not -path "./archive/*"
-> (no output)
```

Clean. No 013 / IBP / total-derivative / promotion artifacts.

### Root Cleanliness After pytest

```text
$ ls *.md *.json
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
loop_config.json
```

Stable after this loop. Probe and smoke outputs live under
`archive/local_runs/` (gitignored).

## Boundary Constraints Honored

- Did not modify `loop_engine/state.py` (freeze_preconditions).
- Did not modify `loop_engine/completion_matrix.py`.
- Did not modify `loop_engine/human_signoff.py`.
- Did not modify `loop_engine/checkpoint.py`.
- Did not modify `loop_engine/pre_run_gate.py`.
- Did not modify `loop_engine/pre_run_brief.py`.
- Did not allow human signoff to replace a missing reviewer verdict.
- Did not replace real reviewer with stub in production
  (`forbid_stub: true` is the default in every example pool).
- Did not start 012C / 013 / IBP / total derivative.
- Did not touch `sigma_abc/`.
- Did not introduce new third-party Python dependencies.

## Known Pre-existing Failure (Not Caused By Loop 021)

`tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`
fails on `assert result.returncode == 0` because the runner
raises:

```text
RuntimeError: Cannot freeze checkpoint: human_signoff.yaml is required before freezing
```

This is the Loop 013 `human_signoff` hard-stop on stage 006.
The safe-pre-fusion profile declares `human_signoff.auto_for_tests:
true` but the auto-signoff path is currently not wired into
`freeze_checkpoint` for this profile. **This failure pre-dates
Loop 020A and Loop 021** — it is recorded as a known issue, not
in scope of this loop or the previous hygiene pass.

## Fallback Policy: No-Fallback on Semantic Failure

The pool must NEVER ask another provider for a different verdict
when one provider has produced a schema-valid result. This is
encoded in `provider_result.should_continue_to_next_provider`:

```text
schema_valid=True  -> return False  (chain stops)
runtime_status=AGENT_OK  -> return False  (chain stops)
runtime_status in RETRYABLE_RUNTIME_STATUSES -> return True  (chain continues)
runtime_status not in RETRYABLE_RUNTIME_STATUSES -> return False  (chain stops)
```

A `verdict: FAIL` from one provider is authoritative. The pool
treats FAIL / NEEDS_PATCH exactly the same way as PASS:
chain stops, the verdict lands in `invocation_summary.json`,
`completion_matrix.freeze_eligible` becomes False, and
`freeze_preconditions` rejects freeze. No second provider can
"veto" the FAIL by returning a PASS.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

This caveat is preserved in every frozen
`validation_summary.caveats` entry that already exists (e.g. on
the `010_pair_kernel_fusion_pilot` frozen checkpoint), in the
identity library (`identities/sigma_abc.default_identities.yaml`'s
`DC inherited caveat` identity), and in
`docs/user_guide/QUICKSTART.md`. Loop 021 does not create or
modify any of those.

## Next Safe Action

With Loop 021 plumbing ready, the trusted external reviewer
pool is now provider-agnostic. The previously blocking
dependency on a single Codex CLI user account is replaced by a
configurable pool of one or more API / CLI providers.

The recommended order from the user remains:

1. ~~Runner report output hygiene~~ — done (Loop 020A).
2. ~~Reviewer provider pool + API-key runtime~~ — done (this
   loop).
3. After Codex CLI quota resets, retry the sigma_abc
   throughput materialization (`Phase 5` of Loop 019R). The
   pool already accepts `codex_cli_resolver` as one of its
   providers; it does not have to be the first provider.
4. After 011/012A/012B reach deep-chain freeze, **only then**
   proceed to Loop 020 (012C promotion with L2_FULL_PANEL).
5. After that, case-study extraction from root to
   `case_studies/sigma_abc/` (deferred per Loop 020 plan).

Until Loop 020 is reached, the runner / pipeline is parked.

## Final Classification

```text
A.  "Reviewer provider pool implemented; users can use their own
     API keys; fallback is runtime-failure-only; tests pass; repo
     root remains clean; sigma_abc not modified."
```

Loop 021 targeted tests: 17 passed (17/17). Full-repo pytest:
197 passed + 1 pre-existing failure (safe_pre_fusion
human_signoff, unrelated). Compile PASS. Forbidden scan 0.
Root has only the 5 expected hand-curated files.
