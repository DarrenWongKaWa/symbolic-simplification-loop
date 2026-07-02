# Loop 019R — Codex Quota Still Active Report

## Status

QUOTA_STILL_ACTIVE_RETRY_HALTED.

```text
Final classification (per user spec):
C. "Retry not attempted; reason: Codex CLI usage limit still active
   on this account; clean-source audit also completed and shows no
   background scheduler was responsible for the earlier clean-style
   wipe; 012C promotion not started."
```

`sigma_abc` physics NOT modified. No 012C promotion. No Stage 013.
No tensorial IBP. No total-derivative reduction. No claim of full
tensorial sigma_abc correctness.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Step 0 — Clean-Source Audit Result

The user's prior prompt traced the `2026-07-01T12:38:06` wipe
back to a `--clean`-style invocation. The audit confirms:

```text
$ CronList
No scheduled jobs.
```

- No active cron / `400bcc3e` / `/loop` scheduler.
- No wrapper scripts reference `--clean` or
  `sigma_abc_loop_candidate_preparation --clean`.
- Only entry point for `--clean` is
  `scripts/run_autonomous_loop.py:2419,2444` (the CLI).
- The runner is invoked directly by user (this session) and by the
  pytest test
  `tests/test_sigma_abc_loop_candidate_preparation.py::test_loop_candidate_preparation_blocks_when_stage012_inputs_are_absent`.
- That pytest test invokes the runner without `--clean`. It only
  wipes its own stage directory
  (`sigma_abc_012c_real_loop_candidate_preparation`).

The 011/012A/012B provisional checkpoints disappeared because the
runner advanced past those provisional siblings and re-froze 010
(deep chain still ends at 010, since the reviewer verdict was
`AGENT_QUOTA_LIMIT` and never produced a deep-chain successor). The
mid-run snapshots were reachable in mid-run but did not survive the
next runner invocation that consumed them.

No background scheduler was responsible.

Audit report written: not separately needed at this stage — the
audit findings fit naturally inside this report (see "Clean-Source
Audit" section above).

## Step 1 — Quota Probe Result

A minimal Codex CLI invocation was attempted directly, bypassing
`scripts/codex_resolver.sh`, with a benign "Reply with the single
word: PONG" prompt and read-only sandbox. Result:

```text
exit=1 elapsed=114.0s
stderr-tail:
  ERROR: Reconnecting... 5/5
  warning: Falling back from WebSockets to HTTPS transport. request timed out
  ERROR: You've hit your usage limit. Upgrade to Pro
         (https://chatgpt.com/explore/pro), visit
         https://codex/settings/usage to purchase more credits or
         try again at 9:14 PM.
```

The Codex CLI itself returned `exit 1` after `~114 s` with
`AGENT_QUOTA_LIMIT` (`You've hit your usage limit ... try again at
9:14 PM`). This matches the per-stage reason observed during the
Phase 5 throughput run (`AGENT_QUOTA_LIMIT / RetryAfter -> 9:14
PM`) — the limit has **not** cleared.

`scripts/codex_resolver.sh --probe` alone is misleading:
`--probe` only validates PATH resolution, not quota. The
contract with this loop's gate requires an **actual Codex
invocation** to confirm quota. The probe above is the real check.

Stub invocation was NOT used. `ProductionStubForbidden=True` was
preserved on every production profile. The real Codex CLI was
called directly via its absolute path.

## Why The Retry Is Halted

Two preconditions from the user's prompt are not satisfied:

1. **Quota probe is NOT clear.** Codex CLI itself returns
   `AGENT_QUOTA_LIMIT`. Re-running throughput now would
   re-create `PROVISIONAL_FREEZE_WITH_REVIEW_DEBT` for all three
   stages — same outcome as Phase 5; no deep chain advance.

2. **Deep chain state unknown without retry.** Even after Codex
   quota clears, runner behavior on `--from-current-checkpoint`
   with `auto-patch` and `max-stages 3` consumed the provisional
   011/012A/012B snapshots without promoting them to deep-chain
   successors, so the deep chain is currently at 010 regardless.

The right next action is to wait for Codex quota to clear (the
RetryAfter hint is `9:14 PM` local; the wall clock at this report
is 2026-07-01T12:47 UTC, several hours before quota reset). Only
then should the throughput rerun be attempted, **with a clean
target state** captured by `LOOP_019R_PRE_RETRY_SNAPSHOT.md`.

## Step 2 — Pre-Retry Snapshot (Already Captured)

```text
recorded_at_utc: 2026-07-01T12:45:54.945507Z
deepest_physical_checkpoint: null
checkpoints: []    # all 011/012A/012B provisional snapshots are gone
stages_present:
  - stages/sigma_abc_010_pair_kernel_fusion_pilot
  - stages/sigma_abc_012c_real_loop_candidate_preparation
AUTONOMOUS_LOOP_RUN_REPORT.md sha256:
  0e84b2164943c8c5a0868f6d44b8b65d5d6367aa8d42a5b79de40f3b9d6f75d1
```

Full snapshot dump: see `LOOP_019R_PRE_RETRY_SNAPSHOT.md` in the
repo root.

## What Did NOT Happen

- We did NOT touch `sigma_abc/` physics.
- We did NOT start 012C promotion.
- We did NOT start Stage 013.
- We did NOT start tensorial IBP.
- We did NOT introduce total-derivative reduction.
- We did NOT claim full tensorial sigma_abc correctness.
- We did NOT modify any Loop 014–017 trust-stack code, profile, or schema.
- We did NOT rerun the throughput profile while quota was active.
- We did NOT replace real reviewer with a stub.

## Permanent Caveat Preserved

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Final Classification (Verbatim Per User Spec)

```text
C. "Retry not attempted; reason: quota still active / clean scheduler active /
    missing approval."
```

In this Loop's actual evidence, the load-bearing cause was quota:
`clean scheduler active` was checked and disproved; `missing approval`
is the implicit gate that this report honours by halting the retry.
The user's instruction was unambiguous: "Do not rerun throughput
while quota is still active."

## Next Safe Action

When the Codex quota resets (after `RetryAfter -> 9:14 PM`):

1. Re-run quota probe (`scripts/codex_resolver.sh --probe` plus a
   minimal Codex invocation, same recipe as above). Confirm exit 0.
2. Re-run throughput:

   ```text
   python3 scripts/run_autonomous_loop.py \
     --project sigma_abc \
     --profile sigma_abc_hypothesis_pre_ibp_throughput \
     --from-current-checkpoint \
     --auto-patch \
     --write-digests \
     --max-stages 3
   ```
3. If review verdict now produces real results (not
   `AGENT_QUOTA_LIMIT`), `scripts/resume_pending_reviews.py` and
   `scripts/settle_review_debt.py` can settle the debt and the
   deep chain can advance to 012B.
4. Apply an explicit human signoff (`scripts/sign_stage.py`) per
   the suggested blocks already captured in
   `LOOP_019R_MATERIALIZATION_RUN_REPORT.md`.
5. Then — and only then — write
   `LOOP_019R_QUOTA_RETRY_MATERIALIZATION_REPORT.md` with verdict A.

Do NOT proceed to Loop 020 (012C promotion with L2_FULL_PANEL)
under any circumstance until verdict A has been recorded.
