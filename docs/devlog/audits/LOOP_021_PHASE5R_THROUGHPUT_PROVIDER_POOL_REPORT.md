# Loop 021 Phase 5R — Throughput Run Report

## Status

PROVISIONAL_FREEZE_ON_011_VIA_LEGACY_CODEX_PATH.

```text
Final classification (per user spec):
B. "Upstream materialization still not fully frozen; reason:
   runner ran sigma_abc_011_center_sector_pilot; validation
   reached PASS via legacy codex resolver path (NOT provider
   pool); ScientificMetaReviewer invocation timed out at 900s
   (AGENT_TIMEOUT); freeze rejected for human_signoff.yaml
   absence; 012A / 012B were not reached; deepest physical
   checkpoint remains sigma_abc_010_pair_kernel_fusion_pilot;
   012C promotion not started."
```

Loop 021 plumbing (probe + smoke + secret-redaction + provider
pool) is **verified live** (207 passed + 1 pre-existing). The
pool itself **is NOT** wired into the production runner
(`scripts/run_autonomous_loop.py`). The runner still uses
the legacy `runtime.command` path. That path invokes
`bash scripts/codex_resolver.sh` for ScientificMetaReviewer,
which **timed out at 900s**, exactly matching the Loop 019R
finding.

`sigma_abc` physics NOT modified. No 012C / 013 / IBP / total
derivative started. No full tensorial sigma_abc correctness
claim.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Provider Readiness (Fresh Evidence)

```text
$ python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
# Reviewer Provider Probe

role: `ScientificMetaReviewer`

## 2. `openai_compatible_api` (adapter: `openai_compatible_api`)
   - enabled: `True` (reason: env:LOOP_ENABLE_OPENAI_COMPATIBLE)
   - availability_status: AVAILABLE
   - runtime_status: AVAILABLE
   - config: {...} (redacted)
```

The user's `.env` lives at the repo root (mode 600,
gitignored). `loop_engine.config.load_dotenv` is now wired
into the probe (`scripts/probe_reviewer_providers.py::_read_pool_cfg`
calls `load_dotenv()` before reading the runtime config).
The loader does not overwrite env vars already set by an
interactive shell; secrets stay on disk in the gitignored
`.env`.

## Step 2 — Clean-Source Guard

```text
$ CronList
No scheduled jobs.
```

No `--clean` background watcher. No `--clean` shell hook.

## Step 3 — Pre-Retry Snapshot

```text
deepest physical checkpoint at run start:
  sigma_abc_010_pair_kernel_fusion_pilot_2026-07-01T15-22-20+00-00

stage dirs at run start:
  stages/sigma_abc_010_pair_kernel_fusion_pilot/
  stages/sigma_abc_012c_real_loop_candidate_preparation/

config file content hashes (values redacted, not printed):
  .env                              sha256 96b2db30413265055d22fd6612e8f2274f64f977dbdf3c974f887dc28c0b48c1
  agents/runtime.local.yaml         sha256 ca506363829c09cda44a2622e76d6dee8e44973556d88dac382b9be1ef70049b
  agents/runtime.local.example.yaml sha256 2ae6cb52727e53f76bcd25184dc3bcdd0e37b42f43b9e884fffed85c99d055bf
```

## Step 4 — Throughput Runner Command

```text
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 3
```

(No `--clean`. No `--write-root-report`.)

## What Happened

The runner ran stage `sigma_abc_011_center_sector_pilot`. The
stage executed through `freeze_checkpoint()` and was rejected
by the runtime precondition:

```text
RuntimeError: Cannot freeze checkpoint: human_signoff.yaml is required before freezing
```

This is the **pre-existing** `human_signoff.yaml is required`
hard-stop from the Loop 013 trust-stack. It is documented in
Loop 020A and Loop 021 final reports as a known failure mode
of `test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`
and any runner that attempts stage 011 without a signoff.

Before the freeze failed, the stage produced most of the
usual artifacts:

```text
.loop/agent_invocations/ScientificMetaReviewer   (legacy codex-resolver adapter)
.loop/agent_invocations/algebrareviewer
.loop/agent_invocations/physicsreviewer
.loop/agent_invocations/softwarereviewer
.loop/agent_invocations/scientific_metareviewer
.loop/agent_invocations/digest_reviewer
.loop/agent_invocations/main_executor
.loop/agent_invocations/verifier_agent
```

Decision file `decision.json` for 011:

```text
{
  "CheckpointStatus": "PROVISIONAL_WITH_REVIEW_DEBT",
  "ReviewDebt": "OPEN",
  "action": "PROVISIONAL_FREEZE_WITH_REVIEW_DEBT",
  "reason": "AGENT_TIMEOUT: real agent invocation timed out
            before producing valid freeze evidence. Agent ->
            ScientificMetaReviewer.
            exit_code=None, runtime_status=AGENT_TIMEOUT,
            timeout_expired=True, schema_valid=True,
            actually_invoked=True, stub_used=False"
}
```

`validation_summary.overall_gate: PASS`,
`NoIBPStarted: True`, `NoTotalDerivativeIntroduced: True`.

The ScientificMetaReviewer invocation **timed out at 900s**
because the **legacy codex_resolver path** is still active:

```text
.loop/agent_invocations/ScientificMetaReviewer/stderr.txt
  (codex CLI v0.142.5 hung on the "Try again at 9:14 PM" quota
   recovery prompt)
```

The provider pool plumbing was **not used** because the
runner reads only `runtime.command` and never reads
`reviewer_provider_pools.<role>`. That deeper integration
is outside Phase 5R's scope (it belongs to a follow-up
runner-integration loop that wires
`loop_engine.reviewer_provider_pool.run_pool` /
`invoke_reviewer` into `scripts/run_autonomous_loop.py`).

A provisional sibling checkpoint was created at:

```text
autonomous_runs/sigma_abc/checkpoints/sigma_abc_011_center_sector_pilot_provisional_review_debt_2026-07-01T16-09-33+00-00
```

The runner did **not** reach `sigma_abc_012a_loop_sector_inventory`
or `sigma_abc_012b_loop_hypothesis_generation`. After the
runtime error, the runner re-froze the 010 chain as a
no-op side-effect, leaving the deep chain at stage 010:

```text
autonomous_runs/sigma_abc/checkpoints/sigma_abc_010_pair_kernel_fusion_pilot_2026-07-01T16-13-32+00-00/
```

So the **deepest physical checkpoint after the run** is
still `sigma_abc_010_pair_kernel_fusion_pilot`. Stage 012B
deep-freeze **did not happen**.

## Step 5 — Review-Debt Handling

```text
$ ls autonomous_runs/sigma_abc/checkpoints/*provisional*/.loop/decision.json
autonomous_runs/sigma_abc/checkpoints/
  sigma_abc_011_center_sector_pilot_provisional_review_debt_2026-07-01T16-09-33+00-00/
  .loop/decision.json
```

The review debt for 011 is `OPEN`. **Per the Phase 5R spec,
the runner never reached the deferred-resume step** because
the runner stopped after stage 011. The
`scripts/resume_pending_reviews.py` and
`scripts/settle_review_debt.py` scripts have not been invoked
because the precondition (all gates passing for 011) is **not**
met: `human_signoff.yaml` is absent.

The trust-stack invariant from Loop 013 explicitly says
"human signoff cannot override failed validation, failed
review, stale evidence, or unsafe boundary audit". The
signoff cannot be bypassed.

## Step 6 — Suggested Signoff Block (NOT applied)

Per the spec:

> "Do not auto-sign."

This report does **NOT** call `scripts/sign_stage.py`. The
following block is the recommended signoff payload IF the user
explicitly approves the debt settlement:

```text
SIGNOFF stage=sigma_abc_011_center_sector_pilot
decision=DO_NOT_FREEZE_PATCH
reason=ScientificMetaReviewer invocation timed out at 900s
     (legacy codex resolver path); provider pool not yet wired
     into runner. Validation PASS, boundary audit safe, but
     review debt still open pending reviewer verdict.
     DCProjectionTo1D -> INHERITED_PASS caveat preserved.
signed_by=wangjiahua
```

```text
SIGNOFF stage=sigma_abc_012a_loop_sector_inventory
decision=DO_NOT_FREEZE_PATCH
reason=Stage was not reached during Phase 5R runner invocation
     (freeze_checkpoint hard-stop on stage 011).
signed_by=wangjiahua
```

```text
SIGNOFF stage=sigma_abc_012b_loop_hypothesis_generation
decision=DO_NOT_FREEZE_PATCH
reason=Stage was not reached during Phase 5R runner invocation.
signed_by=wangjiahua
```

The `human_signoff.yaml` file on disk has NOT been created.
The runner remains in trust-stack-respecting state.

## Step 7 — Verification

### pytest

```text
$ python3 -m pytest -q
... 207 passed, 1 warning in 34.00 s
1 failed, 207 passed
```

The single failure is the **pre-existing** safe-pre-fusion
human_signoff hard-stop. It is **NOT** caused by this loop;
documented in Loop 020A, Loop 021, Loop 021P final reports.

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

### Root Hygiene

```text
$ ls *.md *.json
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
loop_config.json
```

Five curated root files. **No** runner-emitted reports,
**no** probe/smoke residue, **no** pool-related residue.

The runner-emitted `AUTONOMOUS_LOOP_RUN_REPORT.md` (one file
written during this run) was gitignored; if it persists at
the root between sessions it is captured by `archive/local_runs/`
on subsequent invocations. Probe-and-smoke outputs go
directly under `archive/local_runs/`.

## Boundary Constraints Honored

- Did not modify `sigma_abc/`.
- Did not start 012C / 013 / IBP / total derivative.
- Did not modify freeze_preconditions / completion_matrix /
  human_signoff.
- Did NOT auto-sign — `human_signoff.yaml` was NOT created.
- Did not bypass the Loop 013 `human_signoff.yaml is required`
  invariant.
- Did not fallback after semantic FAIL or NEEDS_PATCH.
- Did not run the provider pool on behalf of the runner —
  the pool was wired into the probe only (Step 1).
- Did not print any real API key value at any point. The
  secret redactor remains in force for any disk write.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Final Classification

```text
B.  "Upstream materialization still not fully frozen; reason:
     runner ran sigma_abc_011_center_sector_pilot; validation
     reached PASS via legacy codex resolver path (NOT provider
     pool); ScientificMetaReviewer invocation timed out at 900s
     (AGENT_TIMEOUT); freeze rejected for human_signoff.yaml
     absence; 012A / 012B were not reached; deepest physical
     checkpoint remains sigma_abc_010_pair_kernel_fusion_pilot;
     012C promotion not started."
```

## Next Safe Action

Two follow-ups would unlock Phase 5R to verdict A:

1. **Runner-integration loop (not in this batch)**: wire
   `reviewer_provider_pools.<role>` into
   `scripts/run_autonomous_loop.py` so the runner uses the
   Loop 021 provider pool instead of the legacy
   `runtime.command` path. With that, the
   `ScientificMetaReviewer` timeout would not happen
   because the pool would fall through from Codex's `AGENT_TIMEOUT`
   to the next provider.

2. **Human signoff contract for automated pytest-style runs**: the
   `sigma_abc_safe_pre_fusion` profile declares
   `human_signoff.auto_for_tests: true`, but
   `freeze_checkpoint` in the runner does not honour
   `auto_for_tests`. Wiring that path (so that pytest-time
   freezes get a signoff automatically while production freezes
   still require a real human) is a separate small change.

Until those two are addressed, **Phase 5R cannot reach verdict A**.
Trust-stack invariants are preserved.
