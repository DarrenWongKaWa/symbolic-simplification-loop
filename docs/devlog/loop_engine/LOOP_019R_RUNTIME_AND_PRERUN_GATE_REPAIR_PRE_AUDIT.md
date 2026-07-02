# Loop 019R — Runtime + Pre-run Gate Repair Pre-Audit

## Status

TWO_BLOCKERS_IDENTIFIED; REPAIR_DESIGN_PENDING_USER_APPROVAL.

Both Loop 019 blockers now have their root causes pinned to
specific code paths. No physical `sigma_abc` artifact change
required to fix either. Both repairs are additive (TDD-first),
respect the existing trust stack invariants, and can be
unit-tested without running the autonomous runner.

This pre-audit does **not** start any runner, does **not** modify
any sigma_abc physics, does **not** start Stage 013 / IBP /
total-derivative reduction, and does **not** promote 012C.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Current Deepest Physical Checkpoint

```text
autonomous_runs/sigma_abc/checkpoints/sigma_abc_010_pair_kernel_fusion_pilot_2026-07-01T12-02-18+00-00/
```

The 011 / 012B provisional checkpoints observed in Loop 019's
report were wiped by an interim runner invocation in
`autonomous_runs/sigma_abc/AUTONOMOUS_LOOP_RUN_REPORT.md`
(timestamp 2026-07-01T12:02:34). The runner used `--clean`-like
behaviour (or a stage-by-stage cleanup), so the live-on-disk
artefacts from the throughput run no longer exist.

`sigma_abc` mainline is therefore still physically parked at
stage 010.

## Blockers Identified (Verbatim Evidence)

### Blocker A — ScientificMetaReviewer `AGENT_NO_OUTPUT` / `exit_code=127`

`scripts/local_codex_agent_runner.sh` lines 17–20:

```bash
if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found" >&2
  exit 127
fi
```

`agents/runtime.local.yaml` currently routes reviewer invocations
through `bash scripts/local_codex_agent_runner.sh ...` for the
throughput profile. On this machine:

```text
$ command -v codex
(returns 1, no path)
$ which codex
codex not found
```

But a real `codex` binary DOES exist on disk:

```text
/Users/wangjiahua/.vscode/extensions/openai.chatgpt-26.623.81905-darwin-arm64/bin/macos-aarch64/codex
/Users/wangjiahua/.codex/plugins/.plugin-appserver/codex
/Applications/Codex.app/Contents/Resources/codex
```

These are not in any PATH-listed directory in `echo "$PATH"`,
so `command -v codex` fails immediately. The runner script
self-aborts at line 17 with `exit 127` before even constructing
the prompt. The runner reports this back as
`runtime_status=AGENT_NO_OUTPUT, exit_code=127, schema_valid=False`,
which the throughput profile's `l1_on_no_output` then maps to
`PROVISIONAL_FREEZE_WITH_REVIEW_DEBT`.

**This is not a codex-tool failure; it is a PATH-resolution
failure inside a CodeX bash wrapper.**

Production stubs are forbidden by the throughput profile
(`forbid_stub_in_production: True`), so we must NOT replace the
real runner with a stub. The fix is to make the wrapper's
`codex` resolution actually find a real binary.

### Blocker B — 012A pre-run gate hard-stop on a NEGATIVE-context mention

`loop_engine/pre_run_brief.py` lines 153–162:

```python
combined = " ".join([
    str(task.get("goal_restated", "")),
    " ".join(str(action) for action in task.get("allowed_actions", [])),
]).lower()
forbidden_hits = [pattern for pattern in EXPLICIT_FORBIDDEN_PATTERNS
                  if pattern in combined]
hard_stop = bool(forbidden_hits)
```

`EXPLICIT_FORBIDDEN_PATTERNS` contains the substring
`"candidate promotion"`. The 012A / 012C-prep STAGE_PLAN.md goal
line reads:

```text
"Prepare real sigma_abc loop-orbit candidate artifacts for a
 future 012C promotion retry; no candidate promotion."
```

`_goal_from_plan` captures this whole line as `goal_restated`.
The substring matcher then trips on `"candidate promotion"` and
sets `hard_stop=True`, even though the goal's semantic intent
is NEGATIVE ("no candidate promotion").

The matcher's substring rule is too coarse to distinguish:

- Positive intent (`"I will promote the candidate"`) → must hard-stop
- Boundary acknowledgement (`"... preparation only; no candidate promotion"`) → must NOT hard-stop
- Frozen-banner caveat (`"candidate promotion forbidden"`) → must NOT hard-stop

Loop 015's design explicitly required the agent to declare its
forbidden-action list in the brief (and to acknowledge the
forbidden boundary), but the matcher penalises the very act of
declaring the boundary.

## Forbidden Artifact Scan (before any repair)

```text
$ find . -maxdepth 6 -type f \
    \( -name "*stage_013*" -o -name "*sigma_abc_013_*" \
       -o -name "*tensorial_ibp*" -o -name "*total_derivative*" \
       -o -name "*global_pre_ibp*" -o -name "*promoted_candidate_manifest*" \
       -o -name "*stage_012c_loop_orbit_canonicalization_promotion*" \)
-> (no output)
```

Clean baseline. No forbidden artifacts.

## Proposed Repair Path (Pending User Approval)

Two minimal, additive, test-first repairs. Engine code changes
only. Profile, completion_matrix, freeze_preconditions, and
sigma_abc/ are untouched.

### Repair A — codex CLI resolution

Keep `ProductionStubForbidden: True` and `RealAgentInvocationRequired:
True` on the throughput profile. Replace the `bash scripts/local_codex_agent_runner.sh`
wrapper invocation with a more robust resolver that:

1. Looks up `codex` candidates from `PATH` first (`command -v codex`).
2. If absent, falls back to a known list of absolute paths
   (`/Users/wangjiahua/.vscode/extensions/openai.chatgpt-*/bin/macos-aarch64/codex`,
   `/Users/wangjiahua/.codex/plugins/.plugin-appserver/codex`,
   `/Applications/Codex.app/Contents/Resources/codex`).
3. Re-execs itself with `PATH` set so the resolved binary becomes
   the `codex` in `PATH`.
4. If still not found, exits with a SPECIFIC actionable error
   (`exit 127`) that lists the searched paths instead of just
   "codex CLI not found".

`agents/runtime.local.yaml` will be adjusted to call the new
wrapper script. ProductionStubForbidden stays True.

Add a smoke test under `tests/test_loop019r_reviewer_runtime.py`:

```text
test_codex_resolver_finds_real_binary_under_vscode_extension
test_codex_resolver_returns_actionable_error_when_nothing_matches
test_runtime_local_yaml_references_resolver_script
test_resolver_does_not_fall_back_to_stub
```

### Repair B — pre-run brief positive-vs-boundary matcher

Refactor `loop_engine.pre_run_brief.audit_pre_run_brief` to
distinguish a NEGATIVE forbidden-boundary mention from a
POSITIVE execution intent:

1. Pull `goal_restated` and `allowed_actions` into a list of
   sentences (split on `.`, `;`, `,`, `:`).
2. For each forbidden pattern, scan ONLY sentences that are
   positive imperatives (start with a present-tense verb like
   "promote", "start", "perform", "introduce", "begin", "I will",
   "the executor will") OR that contain obviously-positive
   verbs ("promote a candidate", "promote this candidate",
   "promote the candidate", "promote candidate").
3. A NEGATIVE sentence ("no candidate promotion",
   "candidate promotion forbidden", "do not promote",
   "without promoting", "without candidate promotion",
   "without promotion") is acknowledged, NOT executed intent.

Specifically:

```text
"no candidate promotion"         -> NOT a hard-stop
"candidate promotion forbidden"  -> NOT a hard-stop
"do not promote the candidate"  -> NOT a hard-stop
"I will promote the candidate"  -> HARD-STOP
"promote the candidate now"     -> HARD-STOP
"the agent will promote this candidate" -> HARD-STOP
"the next stage promotes the candidate" -> HARD-STOP
```

The existing `EXPLICIT_FORBIDDEN_PATTERNS` substring list is
left in place but is now only consulted AFTER the
positive-vs-boundary classification above. A negative mention
in the goal sentence is logged as `forbidden_boundary_acknowledged`,
not as `hard_stop`. The hard-stop list also still catches real
positive intent on simple patterns like `"start ibp"` and
`"introduce total derivative"`.

Add new tests under `tests/test_loop019r_pre_run_gate.py`:

```text
test_audit_passes_when_goal_says_no_candidate_promotion
test_audit_passes_when_goal_says_candidate_promotion_forbidden
test_audit_hard_stops_when_goal_says_i_will_promote_candidate
test_audit_hard_stops_when_allowed_actions_include_promote_candidate
test_audit_hard_stops_when_goal_says_perform_ibp
test_audit_hard_stops_when_goal_says_introduce_total_derivative
test_audit_warns_when_expected_outputs_empty
test_audit_does_not_call_reviewer
test_profile_match_in_approved_stage_ids_does_not_override_hard_stop
test_dc_caveat_missing_still_warns
```

These tests must be RED before any source change, GREEN after.

## Why This Path Is Safe

- It does not modify `loop_engine/state.freeze_preconditions`,
  `loop_engine/completion_matrix.py`, `loop_engine/human_signoff.py`,
  or `loop_engine/checkpoint.py` — the freeze contract stays intact.
- It does not modify `sigma_abc/` physics at all.
- It does not weaken any profile, schema, policy, or hard-stop policy.
- It does not start 012C / 013 / IBP / total-derivative.
- The current `PROVISIONAL_FREEZE_WITH_REVIEW_DEBT` chain is already
  filtered out by `review_debt.block_before_l2_promotion`, etc., so
  even if upstream freezes are PROVISIONAL, downstream promotion
  remains blocked.
- All fixes are additive: existing tests must still pass, and
  review-related negative-context audit paths must remain
  WARN-level (not PASS), so the original safety boundary is not
  weakened — only the false positive is removed.

## Files To Touch

```text
scripts/local_codex_agent_runner.sh            (or a new sibling resolver script)
agents/runtime.local.yaml
loop_engine/pre_run_brief.py
tests/test_loop019r_pre_run_gate.py            (new)
tests/test_loop019r_reviewer_runtime.py        (new)
```

## Files Explicitly NOT To Touch

```text
sigma_abc/
loop_engine/state.py
loop_engine/checkpoint.py
loop_engine/completion_matrix.py
loop_engine/human_signoff.py
loop_engine/identity_traceability.py
loop_engine/scientific_identities.py
loop_engine/pre_run_gate.py
profiles/*
schemas/*
```

## Part 3 — Dry Verification

After implementing the fixes, the verification does NOT re-run
the throughput runner. Instead it runs pytest on the two new
test modules and verifies that pre-existing 159 tests still pass.
This keeps the change unit-testable and reverses-into-revert-able.

If any 012A or 012B stage directory needs to be regenerated,
that is a separate, user-approved runner invocation after this
audit closes.

## Part 4 — Resume Review Debt

The 011 / 012B provisional checkpoints that Loop 019 created
have been wiped. `scripts/resume_pending_reviews.py` and
`scripts/settle_review_debt.py` would re-create them on a fresh
throughput run, but that re-creation is gated on the runtime
and pre-run-gate fixes above succeeding.

`scripts/resume_pending_reviews.py` cannot settle review debt
that does not yet exist on disk. If invoked before re-running
the throughput profile, the script will report `no_pending_reviews`
or equivalent, which is honest behavior.

## Part 5 — Rerun Upstream Materialization

ONLY after Parts 1 and 2 are green (pytest passes including the
two new test modules) AND the user has approved this audit's
recommended command, may we re-run:

```text
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 3
```

This re-run is expected to:

```text
- attempt 011, 012A, 012B in order
- 012A pre_run_gate -> PASS or WARN, hard_stop=False
- ScientificMetaReviewer command -> exit_code=0 (or real failure)
- no PRE_RUN_GATE_FAILED on 012A
- no 012C promotion
- no Stage 013
- no IBP
- no total derivative
```

If the re-run is not approved in this session, this audit stops
at Parts 1–3 (no live runner invocation).

## Recommended Next Step

User approval to:

1. Add the two new test modules under `tests/test_loop019r_*.py`
   (Phase 4 step 1 of `systematic-debugging`: RED).
2. Implement the two minimal source fixes (Phase 4 step 2: GREEN).
3. Verify no regression in the existing 159 pytest cases
   (Phase 4 step 3: VERIFY).
4. STOP. Do not invoke the throughput runner. Report `LOOP_019R_*_REPORT.md`
   with verdict `B` (repair complete upstream-side; no fresh
   materialization run in this session).

If the user instead wants a fresh materialization, that runs as
a separate, explicit `Loop 019R-M` invocation with a
`LOOP_019R_MATERIALIZATION_RUN_REPORT.md`.

## Files Examined

```text
LOOP_019_UPSTREAM_012A_012B_MATERIALIZATION_REPORT.md
LOOP_019_UPSTREAM_012A_012B_MATERIALIZATION_PRE_AUDIT.md
autonomous_runs/sigma_abc/AUTONOMOUS_LOOP_RUN_REPORT.md
scripts/local_codex_agent_runner.sh
scripts/run_autonomous_loop.py (lines 84-92, 2419-2447)
agents/runtime.local.yaml
agents/runtime.local.example.yaml
loop_engine/pre_run_brief.py
loop_engine/agent_invocation.py
autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/STAGE_PLAN.md
```

## Non-goals

This audit does not:

```text
- Modify sigma_abc physics.
- Start 012C promotion.
- Start Stage 013.
- Start tensorial IBP.
- Introduce total-derivative reduction.
- Claim full tensorial sigma_abc correctness.
- Replace real reviewer invocation with a stub.
- Weaken pre_run_gate / freeze_preconditions / human_signoff.
- Convert missing physical artifacts into success.
```

## Permanent Caveat Preserved

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```