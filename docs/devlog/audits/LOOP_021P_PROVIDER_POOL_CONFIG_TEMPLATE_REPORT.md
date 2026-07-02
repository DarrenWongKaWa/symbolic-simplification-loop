# Loop 021P — Provider Pool Config Template Report

## Status

PROVIDER_POOL_TEMPLATE_SEEDED_LOCALLY.

```text
Final classification (per user spec):
A. "Provider pool config template seeded;
   ScientificMetaReviewer pool configured locally without secrets;
   probe lists providers; no sigma_abc stages run."
```

This loop is **configuration-only**. No sigma_abc stages ran. No
012C / 013 / IBP / total derivative started. No full tensorial
sigma_abc correctness claim.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## What This Loop Did

1. **Pre-audit** (Step 1): Identified that the example file
   already contained a `reviewer_provider_pools.ScientificMetaReviewer`
   block under
   `profiles.sigma_abc_hypothesis_pre_ibp_throughput`, and that
   the local `runtime.local.yaml` was missing that block.
2. **Skipped** Step 2: The example file already had the pool;
   no edit needed there.
3. **Step 3**: ADDED the same
   `reviewer_provider_pools.ScientificMetaReviewer` block to
   `agents/runtime.local.yaml` under
   `profiles.sigma_abc_hypothesis_pre_ibp_throughput`, **alongside**
   the existing legacy `runtime:` block (Loop 012 contract).
4. **Step 4**: Re-ran `scripts/probe_reviewer_providers.py` —
   pool is now CONFIGURED. All five providers listed and marked
   `DISABLED_BY_ENV` (because their `enabled_env` variables are
   unset on this machine).
5. **Step 5**: Wrote
   `docs/devlog/audits/LOOP_021P_USER_PROVIDER_SETUP.md` with
   explicit per-provider shell `export` commands + a "do not
   paste keys into repo" reminder.
6. **Step 6**: Verified.

## Files Modified

```text
agents/runtime.local.yaml            # ADDED reviewer_provider_pools block
                                    # alongside existing legacy runtime:
                                    # block (preserves Loop 012 contract)
```

## Files Created

```text
docs/devlog/audits/LOOP_021P_PROVIDER_POOL_CONFIG_TEMPLATE_PRE_AUDIT.md
docs/devlog/audits/LOOP_021P_USER_PROVIDER_SETUP.md
docs/devlog/audits/LOOP_021P_PROVIDER_POOL_CONFIG_TEMPLATE_REPORT.md
```

## Files Explicitly NOT Modified

```text
agents/runtime.local.example.yaml   # already contained pool block; no edit needed
sigma_abc/                          # physics
loop_engine/                         # trust stack
profiles/                            # profile forbidden_actions
schemas/                             # unchanged
docs/user_guide/REVIEWER_PROVIDER_POOL.md
docs/user_guide/API_KEYS.md
docs/devlog/audits/LOOP_021_PHASE5R_PROVIDER_READINESS_AUDIT.md
```

## Probe Behaviour (Fresh Evidence)

```text
$ unset ANTHROPIC_API_KEY OPENAI_API_KEY OPENAI_COMPATIBLE_API_KEY \
        OPENAI_COMPATIBLE_BASE_URL OPENAI_COMPATIBLE_MODEL \
        LOOP_ENABLE_CLAUDE_CODE LOOP_ENABLE_CODEX

$ python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
# Reviewer Provider Probe

role: `ScientificMetaReviewer`
fallback_policy: `runtime_failure_only`
require_real_provider: `True`
forbid_stub: `True`

## 0. `anthropic_api` (adapter: `anthropic_api`)
   - enabled: `False` (reason: `missing_env:ANTHROPIC_API_KEY`)
   - availability_status: `DISABLED_BY_ENV`
   - runtime_status: `NOT_INVOKED`

## 1. `openai_api` (adapter: `openai_api`)
   - enabled: `False` (reason: `missing_env:OPENAI_API_KEY`)

## 2. `openai_compatible_api` (adapter: `openai_compatible_api`)
   - enabled: `False` (reason: `missing_env:OPENAI_COMPATIBLE_API_KEY`)

## 3. `claude_code_cli` (adapter: `command`)
   - enabled: `False` (reason: `missing_env:LOOP_ENABLE_CLAUDE_CODE`)

## 4. `codex_cli_resolver` (adapter: `command`)
   - enabled: `False` (reason: `missing_env:LOOP_ENABLE_CODEX`)

(EXIT=0)
```

Five providers configured; all disabled-by-env because their
gating env var is unset. Pool is recognised. `stub_used=false`
is the default; no fallback stub is substituted.

## Secret Check

```text
$ grep -E "(sk-ant|sk-proj|Bearer)" agents/runtime.local.yaml | head
(no output)
```

No real key strings present. Only env var **names**. The
redactor (`loop_engine/secret_redaction.py`) remains in force
for any future probe / smoke / runner output.

## Existing Test Compatibility

`tests/test_loop012_engineering_hygiene.py::test_runtime_local_config_uses_repo_root_placeholder`
expects every profile in `runtime.local.yaml` to declare a
`runtime:` block with `command:` containing `${REPO_ROOT}`.
This loop preserves the legacy `runtime:` block on every profile
(including the new pool block on
`sigma_abc_hypothesis_pre_ibp_throughput`) so the test passes
without modification.

`tests/test_loop021_*.py` (17 tests, including the secret
redaction contract and the reviewer provider pool contract)
remain GREEN.

## Verification

### pytest

```text
$ python3 -m pytest -q tests/test_loop021_*.py
... 17 passed, 1 warning in 0.15 s
```

Loop 021 targeted tests all pass.

```text
$ python3 -m pytest -q
... 197 passed, 1 warning in 35.32 s
1 failed, 197 passed
```

The single failure is the **pre-existing** safe-pre-fusion
human_signoff hard-stop recorded in Loop 020A and Loop 021
final reports. It is **NOT** caused by this loop.

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

### Root Cleanliness

```text
$ ls *.md *.json
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
loop_config.json
```

Five hand-curated root files. **No** runner-emitted reports,
**no** probe/smoke residue, **no** pool-related files at root.

## Boundary Constraints Honored

- Did not modify `sigma_abc/` physics.
- Did not run sigma_abc stages.
- Did not run 012C promotion.
- Did not start Stage 013.
- Did not run tensorial IBP.
- Did not introduce total-derivative reduction.
- Did not claim full tensorial sigma_abc correctness.
- Did not weaken freeze_preconditions / completion_matrix /
  human_signoff.
- Did not use stub reviewer in production.
- Did not write real API keys to any file.
- Did not fall back after semantic FAIL or NEEDS_PATCH.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Final Classification

```text
A.  "Provider pool config template seeded;
     ScientificMetaReviewer pool configured locally without secrets;
     probe lists providers; no sigma_abc stages run."
```

## Next Safe Action

When you have shell access to set an API key env var, the
trust-stack plumbing will pick up the change after a probe
re-run. Suggested sequence:

```bash
# 1. Read the user setup document one more time.
less docs/devlog/audits/LOOP_021P_USER_PROVIDER_SETUP.md

# 2. Choose ONE provider and set its env vars in your shell
#    (do not paste any value into this chat).
export ANTHROPIC_API_KEY="..."   # for Anthropic
export ANTHROPIC_MODEL="claude-sonnet-4-5"

# 3. Verify with probe.
python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer

# 4. Reply with "Anthropic is available" (or whichever you chose).

# 5. Loop 021P does NOT need to run again. The next iteration is
#    Phase 5R, gated on a real provider being available.
```

Then the Phase 5R procedure (Step 2 clean-source guard →
Step 3 snapshot → Step 4 throughput → Step 5 review-debt
handling → Step 6 suggested signoff → Step 7 final report)
becomes runnable. Phase 5R continues to require explicit user
approval before invoking the runner.
