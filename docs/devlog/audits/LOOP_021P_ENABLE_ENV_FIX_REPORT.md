# Loop 021P — Enable-Env Fix Report

## Status

ENABLE_ENV_SEPARATED_FROM_API_KEY.

```text
Final classification (per user spec):
A. "Provider pool config template seeded; ScientificMetaReviewer
   pool configured locally without secrets; probe lists providers;
   no sigma_abc stages run."
```

This loop is a small follow-up to Loop 021P. It corrects a
real design defect: API-key providers (Anthropic, OpenAI,
OpenAI-Compatible) used `enabled_env: <*_API_KEY>`,
interpreting the key value itself as a boolean enable flag.
That meant a non-empty key would never enable the provider
because the value is a secret, not a "1 / true / yes".

The fix splits the two concerns:

```text
api_key_env: <name>        # reads the secret value
enabled_env: LOOP_ENABLE_<NAME>   # reads an explicit boolean flag
```

`sigma_abc` physics NOT modified. No sigma_abc stages run.
No 012C / 013 / IBP / total derivative started. No real API key
read or written anywhere. No full tensorial sigma_abc
correctness claim.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Files Modified

```text
agents/runtime.local.yaml           # enabled_env paths corrected (3 providers)
agents/runtime.local.example.yaml  # same correction; template for future users
```

## Files Explicitly NOT Modified

```text
loop_engine/                         # trust stack unchanged
loop_engine/reviewer_provider_pool.py
loop_engine/provider_result.py
loop_engine/secret_redaction.py
loop_engine/api_review_provider.py
sigma_abc/                            # physics
profiles/                             # forbidden_actions unchanged
schemas/                              # unchanged
agents/runtime.local.yaml legacy runtime: blocks (preserved)
docs/                                 # docs updated by user-facing note only
```

## What Changed (Verbatim Diff)

```diff
- enabled_env: ANTHROPIC_API_KEY       (was the API key itself)
+ enabled_env: LOOP_ENABLE_ANTHROPIC   (boolean enable flag)

- enabled_env: OPENAI_API_KEY          (was the API key itself)
+ enabled_env: LOOP_ENABLE_OPENAI      (boolean enable flag)

- enabled_env: OPENAI_COMPATIBLE_API_KEY (was the API key itself)
+ enabled_env: LOOP_ENABLE_OPENAI_COMPATIBLE (boolean enable flag)
```

`api_key_env` / `base_url_env` / `model_env` paths are unchanged
— they keep reading the actual secret / base URL / model name.
The redactor (`loop_engine/secret_redaction.py`) is unaffected
(it strips values, not env-var names).

For the command-adapter providers (`claude_code_cli`,
`codex_cli_resolver`), the existing `enabled_env` was already
correct (`LOOP_ENABLE_CLAUDE_CODE`, `LOOP_ENABLE_CODEX`); no
change there.

## Live Verification (Fresh Evidence)

```text
$ grep -E "enabled_env" agents/runtime.local.yaml | head
            enabled_env: LOOP_ENABLE_ANTHROPIC
            enabled_env: LOOP_ENABLE_OPENAI
            enabled_env: LOOP_ENABLE_OPENAI_COMPATIBLE
            enabled_env: LOOP_ENABLE_CLAUDE_CODE
            enabled_env: LOOP_ENABLE_CODEX

$ grep -E "enabled_env" agents/runtime.local.example.yaml | head
            enabled_env: LOOP_ENABLE_ANTHROPIC
            enabled_env: LOOP_ENABLE_OPENAI
            enabled_env: LOOP_ENABLE_OPENAI_COMPATIBLE
            enabled_env: LOOP_ENABLE_CLAUDE_CODE
            enabled_env: LOOP_ENABLE_CODEX

$ grep -E "(sk-ant|sk-proj|Bearer )" agents/runtime.local.yaml \
              agents/runtime.local.example.yaml
(no output)

$ python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
```

When the user exports `LOOP_ENABLE_ANTHROPIC=1` (or any of
`LOOP_ENABLE_OPENAI`, `LOOP_ENABLE_OPENAI_COMPATIBLE`,
`LOOP_ENABLE_CLAUDE_CODE`, `LOOP_ENABLE_CODEX`) before invoking
the probe, the matching provider becomes `enabled: True`,
`availability_status: AVAILABLE` (assuming the corresponding API
key is also set).

**Crucially, the fix did not read, touch, log, or write any
real API key.** The keys stay in the user's shell environment
where they belong.

## Verification

### pytest

```text
$ python3 -m pytest -q tests/test_loop021_*.py
... 17 passed, 1 warning in 0.20 s
```

Loop 021 targeted tests all pass.

```text
$ python3 -m pytest -q
... 197 passed, 1 warning in 36.13 s
1 failed, 197 passed
```

The single failure is the **pre-existing** safe-pre-fusion
human_signoff hard-stop (Loop 020A, Loop 021, Loop 021P all
recorded it). It is **NOT** caused by this loop.

### compileall

```text
$ python3 -m compileall loop_engine scripts tests
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

Five hand-curated root files. No probe / runner residue.

## Boundary Constraints Honored

- Did not modify `sigma_abc/`.
- Did not run sigma_abc stages.
- Did not run 012C / 013 / IBP / total derivative.
- Did not read or print any real API key.
- Did not write any API key to any file.
- Did not weaken freeze_preconditions / completion_matrix /
  human_signoff.
- Did not use stub reviewer in production.
- Did not fall back after semantic FAIL or NEEDS_PATCH.

## Next Safe Action

The user-side step that follows this fix:

```bash
# 1. Read the user setup document.
less docs/devlog/audits/LOOP_021P_USER_PROVIDER_SETUP.md

# 2. Set ONE provider's boolean flag (in shell, not in any file).
export LOOP_ENABLE_OPENAI_COMPATIBLE=1     # for OpenAI-Compatible
# OR export LOOP_ENABLE_ANTHROPIC=1      # for Anthropic
# OR export LOOP_ENABLE_OPENAI=1         # for OpenAI
# OR export LOOP_ENABLE_CODEX=1          # for Codex CLI
# OR export LOOP_ENABLE_CLAUDE_CODE=1    # for Claude Code CLI

# 3. Verify with probe.
python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer

# 4. Reply with the provider that became AVAILABLE.
```

When the probe reports at least one provider as
`enabled: True, availability_status: AVAILABLE`, the user can
reply with "Provider is now available for
ScientificMetaReviewer" (without echoing key values) to
trigger Phase 5R.

## Final Classification

```text
A.  "Provider pool config template seeded; ScientificMetaReviewer
     pool configured locally without secrets; probe lists
     providers; no sigma_abc stages run."
```

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
