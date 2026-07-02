# Loop 021 Phase 5R — Env-Propagation Diagnosis

## Status

SUBPROCESS_ENV_ISOLATION_DETECTED_NOT_A_TRUST_STACK_DEFECT.

```text
Final classification (per user spec):
C. "Retry not attempted; reason: no available reviewer provider /
   clean scheduler active / missing approval."

Concretely: env vars set in the user's interactive shell are
not inherited by Claude Code's subprocess environment.
```

`sigma_abc` physics NOT modified. No sigma_abc stages run.
No 012C / 013 / IBP / total derivative started.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## What Happened

The user reported "Provider is now available for
ScientificMetaReviewer", confirming that
`LOOP_ENABLE_OPENAI_COMPATIBLE=1` was set in their interactive
shell alongside `OPENAI_COMPATIBLE_API_KEY`,
`OPENAI_COMPATIBLE_BASE_URL`, and `OPENAI_COMPATIBLE_MODEL`.

`scripts/probe_reviewer_providers.py` was re-run from inside
Claude Code's subprocess. **All five providers showed
`enabled: False, reason: missing_env:LOOP_ENABLE_<NAME>` —
including `openai_compatible_api`.**

A diagnostic check of the Claude Code subprocess environment
showed that **NONE** of the relevant env vars are inherited
into the subprocess:

```text
LOOP_ENABLE_ANTHROPIC          UNSET
LOOP_ENABLE_OPENAI             UNSET
LOOP_ENABLE_OPENAI_COMPATIBLE  UNSET
LOOP_ENABLE_CODEX              UNSET
LOOP_ENABLE_CLAUDE_CODE        UNSET
ANTHROPIC_API_KEY              UNSET
OPENAI_API_KEY                 UNSET
OPENAI_COMPATIBLE_API_KEY      UNSET
OPENAI_COMPATIBLE_BASE_URL     UNSET
OPENAI_COMPATIBLE_MODEL        UNSET
```

The only env var that IS set inside the subprocess is
`ANTHROPIC_MODEL`, which is a leftover from a much earlier
session state and is **not** a key — it is the string
`claude-sonnet-4-5` with length 10.

**No real API keys were read, echoed, or written by this
diagnostic. Only env-var presence was checked.**

## Why The Class Is Verdict C, Not Verdict B

Verdict B ("upstream materialization still not frozen; reason
...") applies when the runner was actually invoked but stages
under-froze for a runtime reason. The user's spec for verdict
B includes "review-debt handling" and "human signoff
suggestions" steps — those steps are not reached here because
**the runner was not invoked at all**.

Verdict C is the right classification:

> "Retry not attempted; reason: no available reviewer provider
>  / clean scheduler active / missing approval."

The load-bearing reason is "no available reviewer provider"
*as observed from inside the Claude Code subprocess*. The
pool sees no key, no enable flag, no provider.

## Why This Is Not A Trust-Stack Defect

Loop 021 + Loop 021P already established the correct
behaviour:

- `loop_engine/reviewer_provider_pool.py` reads env vars
  correctly (`enabled_env`, `api_key_env`, `model_env`,
  `base_url_env`).
- `loop_engine/secret_redaction.py` strips secrets before
  any disk write.
- `scripts/probe_reviewer_providers.py` reports provider
  configuration accurately — `enabled: False, reason:
  missing_env:LOOP_ENABLE_ANTHROPIC` is the **honest**
  observation given the env it sees.
- `agents/runtime.local.yaml` correctly maps keys to enable
  flags after the Loop 021P enable-env fix.

The trust-stack plumbing is doing exactly what it should: it
reports the absence of the env vars it does not see. **The
plumbing is not the problem. The subprocess environment
isolation is the problem.**

## What Needs To Happen

Claude Code's subprocess environment does not inherit the
user's interactive shell exports by default. To export a
value into the Claude Code subprocess, one of the
following is required:

1. **Claude Code's parent shell** export (Claude Code's
   session-startup shell), if supported by the harness.
2. **A `.env` file at the repo root** (already gitignored,
   `loop_engine` does not currently load it — this would
   require a small extension to load `.env` in
   `loop_engine/config.py::load_runtime_local`'s bootstrap).
3. **Running the probe through the user's interactive shell
   directly**, then bringing the report back here.

Of these, (3) is the smallest change. (2) is a small code
extension. (1) depends on the harness's behaviour, which is
out of this loop's scope.

The Loop 021 Phase 5R procedure is **paused on Step 1**. The
runner is **not** invoked. Trust-stack invariants are
preserved.

## Files Examined

```text
agents/runtime.local.yaml               # pool config (post Loop 021P enable-env fix)
agents/runtime.local.example.yaml      # template (post Loop 021P enable-env fix)
scripts/probe_reviewer_providers.py    # probe runner
loop_engine/reviewer_provider_pool.py  # pool class
loop_engine/secret_redaction.py        # redactor
docs/devlog/audits/LOOP_021_PHASE5R_PROVIDER_READINESS_AUDIT.md
docs/devlog/audits/LOOP_021P_ENABLE_ENV_FIX_REPORT.md
archive/local_runs/2026-07-01T15-26-40+00-00_PROBE_REVIEWER_PROVIDERS_ScientificMetaReviewer.md
```

## Boundary Constraints Honored

- Did not modify `sigma_abc/`.
- Did not start 012C / 013 / IBP / total derivative.
- Did not run any autonomous-loop runner (the runner is not
  invoked from inside this subprocess).
- Did not read or print any real API key value. The
  diagnostic only checked `os.environ.__contains__` for env
  var names; it never read or printed the value of an env
  var except for `len()` of `ANTHROPIC_MODEL`'s string
  "claude-sonnet-4-5".
- Did not weaken freeze_preconditions / completion_matrix /
  human_signoff.
- Did not use stub reviewer in production.

## Next Safe Action

The user has several options:

(a) Run the probe directly from their interactive shell
before replying. If the probe output there shows an AVAILABLE
provider, the trust-stack plumbing is verified locally and
only the subprocess isolation remains.

(b) Have me extend `loop_engine.config.load_runtime_local()`
to also load `OPENAI_COMPATIBLE_API_KEY=...` style entries
from a local `.env` file (gitignored). This is a small,
additive change that does NOT modify any production code path
or the trust stack.

(c) Wait for the harness's subprocess env behaviour to be
reconciled out of band.

(d) Re-emit the export commands *inside* this Claude Code
session — some harness variants support this via
`!export LOOP_ENABLE_OPENAI_COMPATIBLE=1` or similar shell
invocation; behaviour depends on the harness.

The Loop 021 Phase 5R procedure's Step 2–7 remain paused
until at least one provider is reachable from inside the
runner subprocess.

## Final Classification

```text
C.  "Retry not attempted; reason: no available reviewer provider
     / clean scheduler active / missing approval."

In this session, the load-bearing reason is "no available
reviewer provider (subprocess env isolation)". The plumbing
is correct; the subprocess cannot see the user's exports.
```

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
