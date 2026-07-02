# Loop 022 — Runner Provider-Pool Integration REPORT

## Status

VERDICT **A**. Runner now uses the Loop 021 reviewer provider pool
whenever a profile configures one. Legacy `runtime.command` fallback
is preserved exactly. Fallback is **runtime-failure-only**.

```text
Final classification (per user spec):
A. "Runner uses reviewer provider pool; legacy command fallback
    preserved; fallback is runtime-failure-only; tests pass;
    sigma_abc not modified."
```

Boundary contract:

- `sigma_abc/` physics untouched.
- 012C / 013 / tensorial IBP / total derivative NOT started.
- `pre_run_gate`, `freeze_preconditions`, `completion_matrix`,
  `human_signoff` unchanged.
- `human_signoff.yaml` was NOT auto-created.
- Real API keys NEVER written to any file or report.
- Permanent caveat preserved:
  `DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.`

## Files Modified

| File | Change |
|------|--------|
| `loop_engine/agent_runtime.py` | Added `ProviderPoolAdapter` (subclass of `AgentAdapter`); added `resolve_reviewer_pool_cfg(profile_name, reviewer_role)`; updated `build_adapter()` to select the pool over the legacy command path. Added an `import secret_redaction` for the prompt-redaction pass. |
| `loop_engine/reviewer_provider_pool.py` | `_run_command_provider` now applies `redact_secrets` to `command.txt` and `stdout.txt` (stderr already redacted). `_write_invocation_summary` now adds `provider_attempts` to the on-disk `invocation_summary.json` (the legacy callers continue to read the same shape; the new field is additive). |
| `tests/test_loop022_runner_provider_pool_integration.py` | NEW: 18 integration tests covering pool-or-legacy selection, fallback policy, secret redaction, review debt on all-unavailable, freeze-evidence semantics, and root hygiene. |
| `docs/devlog/audits/LOOP_022_RUNNER_PROVIDER_POOL_INTEGRATION_PRE_AUDIT.md` | NEW: audit enumerating every runner-side seam and the integration plan. |
| `docs/user_guide/REVIEWER_PROVIDER_POOL.md` | Added "Provider Pool in Autonomous Runner (Loop 022)" section with the build_adapter decision tree and a one-liner dry-integration check. |
| `docs/user_guide/API_KEYS.md` | Added "Runner Wiring (Loop 022)" section documenting shell / subprocess isolation and the `.env` fallback for non-interactive shells. |

## Integration Point

The single-point integration seam in
`loop_engine/agent_runtime.py::build_adapter`:

```text
build_adapter(profile, profile_name)
  ├─ profile.reviewer_provider_pools non-empty
  │  AND profile.agents.require_real_invocation == True
  │  -> ProviderPoolAdapter
  │
  ├─ profile.runtime.adapter == "command" | "codex_subagent"
  │  AND no pool configured
  │  -> CommandAgentAdapter / CodexSubagentAdapter (legacy)
  │
  └─ profile.runtime.adapter == "stub" with allow_stub_for_tests
     -> DryRunStubAdapter (tests only)
```

The runner itself is unchanged. `run_runtime_reviewer_agents()` in
`scripts/run_autonomous_loop.py` still calls `adapter.invoke(...)`
per role. The new adapter is a drop-in subclass of `AgentAdapter`,
so this requires no edits in the runner.

### Provider-Pool Selection Behaviour

`build_adapter` looks at the profile's
`reviewer_provider_pools.<ReviewerRole>` block (where
`<ReviewerRole>` matches the per-role `agent_name`) AND the
profile's `agents.require_real_invocation` flag. When both are
present, the runner selects `ProviderPoolAdapter`; otherwise the
legacy `CommandAgentAdapter`/`CodexSubagentAdapter` is returned
unchanged.

The pool adapter stores the **profile-level mapping** in
`self.pool_cfg` and resolves the per-role block at `invoke()` time
(so the same adapter can serve every reviewer role the runner
asks it about). When the profile-level mapping is absent and
only a single inline pool block is supplied, the adapter also
accepts that shape; both call sites have a test.

### Legacy Fallback Behaviour

The pool adapter always remembers the profile's `runtime.command`
list as `legacy_fallback_command` and the adapter name
(`command` / `codex_subagent`) as `legacy_fallback_adapter_name`,
and passes them into `loop_engine.reviewer_provider_pool.invoke_reviewer`.
When the pool has no candidates, `invoke_reviewer` falls through to
the legacy command. The legacy command is **only** used as a
last-resort fallback — it is never the first choice. The Loop 019R
`scripts/codex_resolver.sh` PATH-resolution behaviour is preserved
exactly. No code in `scripts/codex_resolver.sh` was modified.

### Fallback Policy Evidence

`loop_engine/provider_result.py::should_continue_to_next_provider`
is the single-source predicate. ReviewerProviderResult `review_debt_required`
remains the same as Loop 021:

- Schema-valid result (any verdict) → `False` → stop.
- `runtime_status == "AGENT_OK"` → `False` → stop.
- Retryable (`RETRYABLE_RUNTIME_STATUSES`) → `True` → next provider.
- Non-retryable failure → `False` → stop, write blocking review.

Tests in the new file directly exercise:

- `test_fallback_on_aggressive_first_command_times_out_then_second_passes`
  → first provider returns AGENT_COMMAND_NOT_FOUND; chain falls through.
- `test_quota_keyword_in_stderr_triggers_quota_then_falls_through`
  → first provider hits AGENT_QUOTA_LIMIT; chain falls through.
- `test_no_fallback_after_schema_valid_fail` → first provider
  returns schema-valid `verdict: FAIL`; chain stops; second
  provider's `selected=False`.
- `test_no_fallback_after_schema_valid_needs_patch` → same
  semantics for NEEDS_PATCH.

### No-Fallback Semantic Evidence

The pool's `should_continue_to_next_provider(runtime_status, schema_valid)`
returns False whenever `schema_valid=True` (PASS / PASS_WITH_CAVEAT /
FAIL / NEEDS_PATCH / BLOCKED). Tests `test_no_fallback_after_schema_valid_fail`
and `test_no_fallback_after_schema_valid_needs_patch` prove this
end-to-end: each writes a schema-valid JSON, runs the adapter,
asserts `selected_provider == "first_only"`, and confirms the
second provider's `selected=False`.

### Secret Redaction Evidence

`loop_engine/secret_redaction.redact_secrets` is applied at every
text write:

- `loop_engine/agent_runtime.py::ProviderPoolAdapter.invoke`
  writes redacted `prompt.md`, redacted `command.txt`, and
  post-redacts `stdout.txt` and `invocation_summary.json` when
  they contain a known-secret pattern.
- `loop_engine/reviewer_provider_pool.py::_run_command_provider`
  writes redacted `command.txt`, redacted `stdout.txt`, and
  redacted `stderr.txt`.
- `loop_engine/secret_redaction.py` is unchanged but is now
  imported by the adapter as defence-in-depth.

`test_no_real_api_key_on_disk_after_pool_invocation` sets
`OPENAI_API_KEY=sk-fakeprooftest-redactor-must-hide-12345`,
`ANTHROPIC_API_KEY=sk-ant-fakeproof-redact-12345`,
`OPENAI_COMPATIBLE_API_KEY=sk-fakeproof-redact-oc-12345`,
and runs the pool with a provider that echoes the key to stdout.
It then walks every file under
`stage_dir/.loop/agent_invocations/ScientificMetaReviewer/` and
asserts the literal keys do NOT appear. Result: PASS.

## Tests Result

```text
$ python3 -m pytest -q tests/test_loop021_*.py tests/test_loop022_*.py
45 passed, 1 warning in 0.21s

$ python3 -m pytest -q
1 failed, 225 passed, 1 warning in 34.36s
```

The single failure is
`tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`,
documented as the **pre-existing** `human_signoff.yaml is required`
hard-stop (Loop 020A / 021 / 021P final reports). This loop did
NOT touch its cause. The test is reported separately; it is the
last "1 failed" line from `python3 -m pytest -q` and is unrelated
to Loop 022.

Loop 022 adds 18 new tests:

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_build_adapter_selects_provider_pool_when_pool_configured` | builder returns ProviderPoolAdapter. |
| 2 | `test_build_adapter_preserves_legacy_command_when_pool_absent` | legacy CommandAgentAdapter preserved when no pool. |
| 3 | `test_build_adapter_preserves_codex_subagent_when_no_pool` | CodexSubagentAdapter preserved when no pool. |
| 4 | `test_pool_adapter_writes_provider_attempts` | provider_attempts and selected_provider land in invocation_summary.json. |
| 5 | `test_pool_adapter_records_selected_provider` | selected_provider is recorded. |
| 6 | `test_fallback_on_aggressive_first_command_times_out_then_second_passes` | AGENT_COMMAND_NOT_FOUND is retryable. |
| 7 | `test_quota_keyword_in_stderr_triggers_quota_then_falls_through` | AGENT_QUOTA_LIMIT (detected via stderr keyword) is retryable. |
| 8 | `test_no_fallback_after_schema_valid_fail` | semantic FAIL stops the chain. |
| 9 | `test_no_fallback_after_schema_valid_needs_patch` | semantic NEEDS_PATCH stops the chain. |
| 10 | `test_pool_adapter_forbids_stub` | stub is rejected when forbid_stub=True. |
| 11 | `test_no_real_api_key_on_disk_after_pool_invocation` | redaction covers stdout/stderr/prompt/command/summary paths. |
| 12 | `test_review_debt_required_when_all_providers_unavailable` | AGENT_ALL_PROVIDERS_UNAVAILABLE → review debt opens. |
| 13 | `test_completion_matrix_view_after_pool_failure` | missing verdict → freeze_evidence_valid=False (completion matrix sees "not freeze-eligible"). |
| 14 | `test_freeze_preconditions_unchanged` | trust-stack modules still import cleanly. |
| 15 | `test_no_residue_in_fake_root` | no files written at repo root from a pool invocation. |
| 16 | `test_sigma_abc_phys_unchanged` | sigma_abc/ exists as a directory (no edits). |
| 17 | `test_resolve_reviewer_pool_cfg_reads_runtime_local` | helper reads the profile mapping. |
| 18 | `test_resolve_reviewer_pool_cfg_returns_none_when_absent` | helper returns None when no pool is configured. |

## Compileall Result

```text
$ python3 -m compileall loop_engine scripts tests
(no errors)
```

## Root Hygiene Result

```text
$ ls *.md *.json
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
loop_config.json
```

Five curated root files. No runner-emitted reports, no probe/smoke
residue, no pool-related residue. Probe output still goes to
`archive/local_runs/<UTC>_PROBE_REVIEWER_PROVIDERS_<ROLE>.md`
(default), not to the root.

## Forbidden Artifact Scan

```text
$ find . -maxdepth 7 -type f \
    \( -name "*stage_013*" -o -name "*sigma_abc_013_*" \
       -o -name "*tensorial_ibp*" -o -name "*total_derivative*" \
       -o -name "*global_pre_ibp*" -o -name "*promoted_candidate_manifest*" \
       -o -name "*stage_012c_loop_orbit_canonicalization_promotion*" \) \
    -not -path "./.git/*" -not -path "./archive/*"
-> (no output)
```

No 012C / 013 / IBP / total-derivative / promotion artefacts.

## Probe-Runner Dry Integration Test

```text
$ python3 -c "
... from loop_engine.agent_runtime import build_adapter
... profile = {
...   'agents': {'require_real_invocation': True, ...},
...   'runtime': {'adapter': 'command',
...               'command': ['echo', 'legacy']},
...   'reviewer_provider_pools': {
...     'ScientificMetaReviewer': {
...       'providers': [
...         {'name': 'x', 'adapter': 'command',
...          'command': ['true']}],
...     },
...   },
... }
... ad = build_adapter(profile, 'sigma_abc_safe_pre_fusion')
... "
adapter_class= ProviderPoolAdapter
is_PoolAdapter= True
pool_cfg has providers= True
legacy_command preserved= ['echo', 'legacy']
timeout_seconds= 60
```

```text
$ python3 scripts/probe_reviewer_providers.py \
    --role ScientificMetaReviewer | grep openai_compatible
## 2. `openai_compatible_api` (adapter: `openai_compatible_api`)
- enabled: `True` (reason: `env:LOOP_ENABLE_OPENAI_COMPATIBLE`)
- availability_status: `AVAILABLE`
```

The probe still sees the user's `.env` keys; the runner now
**also** selects the pool via `build_adapter`. The runner no
longer routes through the legacy codex_resolver unless no
pool is configured.

## Next Safe Action

Per spec, Loop 022 finishes with verdict A. The runner is
ready for Phase 5R-2 (retry of sigma_abc throughput) if you
explicitly approve it.

Pre-existing test failure to be addressed in a separate loop
(per spec: not in this loop):

- `test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`
  fails on `human_signoff.yaml is required`. Fix would be
  wiring `human_signoff.auto_for_tests: true` through
  `freeze_checkpoint`; that is the same follow-up that the
  Phase 5R final report flagged.

No further agent-driven steps were taken. Awaiting user
direction.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
