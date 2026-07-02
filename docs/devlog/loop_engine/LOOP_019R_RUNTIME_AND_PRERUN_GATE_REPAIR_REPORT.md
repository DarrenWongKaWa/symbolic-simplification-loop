# Loop 019R — Runtime + Pre-run Gate Repair Report

## Status

REPAIR_COMPLETE — BOTH_BLOCKERS_FIXED.

```text
Final classification (per user spec):
A. "Runtime and pre-run gate repaired; 011/012A/012B materialized or
   ready to materialize; 012C promotion not started."
```

`sigma_abc` physics NOT modified. No 012C promotion. No Stage 013.
No tensorial IBP. No total-derivative reduction. No claim of full
tensorial sigma_abc correctness.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## What Was Fixed (Two Loops A + B)

### Blocker A — `ScientificMetaReviewer` exit 127 (now resolves)

Root cause (verified by reading `scripts/local_codex_agent_runner.sh`
lines 17–20 and probing the runtime):

```text
$ command -v codex
(returns 1, no path)
$ ls /Users/wangjiahua/.vscode/extensions/openai.chatgpt-*/bin/macos-aarch64/codex
/Users/wangjiahua/.vscode/extensions/.../codex   <- real binary, exists
$ ls /Users/wangjiahua/.codex/plugins/.plugin-appserver/codex
/Users/wangjiahua/.codex/plugins/.plugin-appserver/codex   <- real binary, exists
$ ls /Applications/Codex.app/Contents/Resources/codex
/Applications/Codex.app/Contents/Resources/codex  <- real binary, exists
$ echo "$PATH" | tr ':' '\n' | grep -i codex
(nothing)
```

`local_codex_agent_runner.sh` line 17 self-aborts with `exit 127`
when `command -v codex` fails. The Codex CLI exists on disk but is
not on `PATH`, so every reviewer's invocation immediately aborted.

**Fix**:

1. New resolver script `scripts/codex_resolver.sh`:
   - Step 1: probe `command -v codex`.
   - Step 2: fall back to explicit override `LOOP_CODEX_BIN`.
   - Step 3: search `~/.codex/plugins/.plugin-appserver/codex`,
     `/Applications/Codex.app/Contents/Resources/codex`,
     `~/.vscode/extensions/**/codex` (only if executable).
   - Re-execs the canonical `local_codex_agent_runner.sh` with a
     PATH that surfaces the resolved binary as `codex`.
   - If nothing resolves, prints an actionable diagnostic listing
     searched paths and exits 127. Never silently falls back to a
     stub. `LOOP_CODEX_STUB` is never exported.

   Probe-only verification on this machine:

   ```text
   $ bash scripts/codex_resolver.sh --probe
   codex resolved at: /Users/wangjiahua/.codex/plugins/.plugin-appserver/codex
   EXIT=0
   ```

2. `agents/runtime.local.yaml`: every production profile
   (`sigma_abc_hypothesis_pre_ibp`,
   `sigma_abc_hypothesis_pre_ibp_throughput`,
   `sigma_abc_loop_candidate_promotion`,
   `test_hypothesis_search_loop_real_agent`) now invokes
   `bash ${REPO_ROOT}/scripts/codex_resolver.sh` instead of the raw
   `local_codex_agent_runner.sh`. ProductionStubForbidden stays True
   everywhere. No behavior change to reviewer protocol — only PATH
   resolution.

### Blocker B — Pre-run gate false positive on negative-context mentions

Root cause (verified by reading `loop_engine/pre_run_brief.py` lines
153–162 of the prior revision plus `loop_engine/pre_run_gate.py`
lines 61–62):

`audit_pre_run_brief` concatenates `goal_restated` and
`allowed_actions`, then substring-matches against
`EXPLICIT_FORBIDDEN_PATTERNS` (which contained `"candidate
promotion"`). The STAGE_PLAN for stage 012A and 012C-readiness reads:

```text
"Prepare real sigma_abc loop-orbit candidate artifacts for a
 future 012C promotion retry; no candidate promotion."
```

`_goal_from_plan` only returned the **first non-blank non-heading
line** of the plan, which frequently was not the goal text. The
substring matcher then tripped on `"candidate promotion"` regardless
of whether the sentence was actually advertising execution intent.

**Fix** (in `loop_engine/pre_run_brief.py`, with tests
in `tests/test_loop019r_pre_run_gate.py`):

1. `_goal_from_plan` rewritten to actually find a `## Goal` section
   header and collect its body lines until the next heading. Falls
   back to legacy `Goal:` directive and to first-non-blank line.
   This is a long-standing latent bug that Loop 015 missed.
2. `_split_into_sentences` splits free-form text on `. ; : \n`.
3. `_classify_sentence` per sentence: NEGATIVE-precedence (the Loop
   015 design); only an explicit first-person / agent / executor /
   `now` anchor can override negation.
4. `_POSITIVE_SENTENCE_MARKERS` extended with bare-imperative
   patterns so genuine positive intent (`"Promote the loop
   candidate now."`, `"Introduce total derivative reduction."`,
   `"Start IBP now."`) is detected even without `I will…`.
5. `_NEGATIVE_SENTENCE_MARKERS` extended with the verbal negations
   needed to classify sentences like
   `"do not introduce total derivative"` as boundary
   acknowledgement rather than positive intent.
6. **Profile-driven boundary enforcement** introduced: when a
   profile's *explicit* `forbidden_actions` list (the field is
   `forbidden_actions: [...]`, NOT the implicit
   `_profile_forbidden`-derived defaults) covers a token, ANY brief
   mention of that token is hard-stopped regardless of wording. This
   is the Loop 015 contract restored: profiles with explicit forbid
   declarations keep their boundary authority. Profiles without
   (e.g. throughput) get the substring classifier's verdict instead.
7. `profiles/sigma_abc_loop_candidate_preparation.yaml` got an
   explicit `forbidden_actions:` block listing `candidate promotion`,
   `global assembly`, `IBP`, `total derivative reduction`,
   `full tensorial sigma_abc correctness claim`. This is what
   restores the Loop 018 / 019 / 015 behavior where 012C preparation
   is blocked at `pre_run_gate` and the runner emits
   `overall_gate = BLOCKED`.
8. `audit_pre_run_brief` result schema gains two new fields
   `positive_intent_forbidden_hits` and
   `forbidden_boundary_acknowledged` (both lists). Existing fields
   (`gate`, `hard_stop`, `warnings`, `blocking_reasons`) unchanged.

## What Was NOT Modified

```text
sigma_abc/                                   <- physics, untouched
loop_engine/state.py                         <- freeze_preconditions, untouched
loop_engine/completion_matrix.py             <- completion matrix, untouched
loop_engine/human_signoff.py                 <- human signoff, untouched
loop_engine/checkpoint.py                     <- freeze_checkpoint, untouched
loop_engine/identity_traceability.py         <- identity traceability, untouched
loop_engine/scientific_identities.py         <- scientific identities, untouched
profiles/sigma_abc_hypothesis_pre_ibp*.yaml  <- throughput profile unchanged (only adds forbidden_actions to 012C-prep)
schemas/*                                    <- schemas, untouched
local_codex_agent_runner.sh                  <- canonical runner unchanged (resolver delegates to it)
```

## Verification (Fresh, End-to-End)

### pytest (deterministic)

```text
$ python3 -m pytest -q
... 177 passed, 1 warning in 33.83 s
```

Exit code 0. Failure count 0.

The 18 new tests added by Loop 019R all pass:

```text
tests/test_loop019r_pre_run_gate.py
  test_audit_passes_when_goal_says_no_candidate_promotion
  test_audit_passes_when_goal_says_candidate_promotion_forbidden
  test_audit_passes_when_goal_says_do_not_promote_candidate
  test_audit_hard_stops_when_goal_says_i_will_promote_candidate
  test_audit_hard_stops_when_allowed_actions_include_promote_candidate
  test_audit_hard_stops_when_goal_says_start_ibp
  test_audit_hard_stops_when_goal_says_introduce_total_derivative
  test_audit_hard_stops_when_profile_forbids_candidate_promotion
  test_audit_passes_when_profile_neutral_and_goal_mentions_promotion
  test_audit_warns_when_expected_outputs_empty
  test_audit_hard_stops_unchanged_for_truly_missing_brief
  test_audit_does_not_call_reviewer
  test_boundary_acknowledgement_recorded_as_warning_not_block
tests/test_loop019r_reviewer_runtime.py
  test_resolver_script_exists_and_is_executable
  test_resolver_emits_actionable_error_when_no_codex_found
  test_resolver_runs_real_codex_when_present
  test_runtime_local_yaml_references_resolver_script
  test_production_stub_remains_forbidden_in_runtime_local
```

### compileall

```text
$ python3 -m compileall loop_engine scripts tests
Listing 'loop_engine'...
Listing 'scripts'...
Listing 'tests'...
(no errors)
```

### Resolver Probe

```text
$ bash scripts/codex_resolver.sh --probe
codex resolved at: /Users/wangjiahua/.codex/plugins/.plugin-appserver/codex
EXIT=0
```

### Forbidden Artifact Scan

```text
$ find . -maxdepth 6 -type f \
    \( -name "*stage_013*" -o -name "*sigma_abc_013_*" \
       -o -name "*tensorial_ibp*" -o -name "*total_derivative*" \
       -o -name "*global_pre_ibp*" -o -name "*promoted_candidate_manifest*" \
       -o -name "*stage_012c_loop_orbit_canonicalization_promotion*" \)
-> (no output)
```

Clean. No 013 / IBP / total-derivative / promotion artifacts.

### Current Deepest Physical Checkpoint

```text
autonomous_runs/sigma_abc/checkpoints/sigma_abc_010_pair_kernel_fusion_pilot_2026-07-01T12-26-09+00-00/
```

The deepest physical frozen checkpoint is still stage 010. The
provisional 011 / 012B snapshots that Loop 019 created were wiped by
an interim `--clean` invocation. **No upstream materialization
occurred during Loop 019R; only the trust-stack plumbing was
repaired.** Re-materialization is a user-approved separate step.

### 012C Hardstop Regression Test Re-PASS

The Phase 1 regression
`tests/test_sigma_abc_loop_candidate_preparation.py::test_loop_candidate_preparation_blocks_when_stage012_inputs_are_absent`
that previously emitted `'FAIL'` instead of `'BLOCKED'`:

```text
PASSED
```

This validates the Loop 018 contract end-to-end: even with the new
positive-vs-boundary classifier, the sigma_abc_loop_candidate_preparation
profile's explicit `forbidden_actions` correctly force the brief
audit into `hard_stop=True` → `pre_run_gate.execution_allowed=False`
→ runner emits `overall_gate = BLOCKED`.

## What Happens Next (Not In Scope Of Loop 019R)

Loop 019R is a **plumbing-only** repair. It does NOT re-run the
throughput profile. The user-approved Part 5 of the pre-audit
remains pending and is gated on:

1. Whether the user wants `LOOP_019R_MATERIALIZATION_RUN_REPORT.md`
   (verdict A → 011/012A/012B materialize via
   `scripts/run_autonomous_loop.py --profile sigma_abc_hypothesis_pre_ibp_throughput --max-stages 3 --from-current-checkpoint --auto-patch --write-digests`).
2. Whether the user wants `LOOP_020_012C_PROMOTION_L2_FULL_PANEL`
   (verdict requires explicit human approval per
   `sigma_abc_loop_candidate_promotion.yaml:human_approval.scope`).

Both next steps are explicitly outside the Loop 019R boundary.
Loop 019R stops at "trust-stack plumbing verified, no live runner
invocation by this loop".

## Files Changed By Loop 019R

```text
scripts/codex_resolver.sh                            (NEW; PATH-fallback resolver wrapper)
agents/runtime.local.yaml                            (replace local_codex_agent_runner.sh invocations)
loop_engine/pre_run_brief.py                         (positive/negative classifier, profile-driven enforcement, goal parser fix)
profiles/sigma_abc_loop_candidate_preparation.yaml   (explicit forbidden_actions declaration)
tests/test_loop019r_pre_run_gate.py                  (NEW; 13 cases)
tests/test_loop019r_reviewer_runtime.py              (NEW; 5 cases)
LOOP_019R_RUNTIME_AND_PRERUN_GATE_REPAIR_PRE_AUDIT.md  (this audit's pre-audit)
LOOP_019R_RUNTIME_AND_PRERUN_GATE_REPAIR_REPORT.md       (this report)
```

`scripts/local_codex_agent_runner.sh`, `schemas/`, `sigma_abc/`,
state / freeze / completion-matrix / human-signoff / checkpointer /
identity-traceability / scientific-identities modules are NOT
modified.

## Final Classification (Verbatim Per User Spec)

```text
A.  "Runtime and pre-run gate repaired; 011/012A/012B materialized or
     ready to materialize; 012C promotion not started."
```

## Boundaries Honored (Verified)

- Did not modify `sigma_abc` physics.
- Did not start 012C promotion.
- Did not start Stage 013.
- Did not start tensorial IBP.
- Did not introduce total-derivative reduction.
- Did not claim full tensorial sigma_abc correctness.
- Did not weaken pre_run_gate (it still hard-stops on
  forbidden-actions tokens, profile-driven or sentence-positive).
- Did not weaken freeze_preconditions.
- Did not weaken human_signoff.
- Did not replace real reviewer with stub.
- Did not bypass review.
- Did not convert missing physical artifacts into success
  (`completion_matrix.freeze_eligible` stays False on provisional
  freezes; pre-run-gate FAIL still BLOCKED in the runner).
- Permanent DCProjectionTo1D caveat remains in every `_profile_caveats`
  auto-append and every frozen `validation_summary.caveats` entry.

## Next Safe Action

If the user later wants Loop 020 (012C promotion with L2_FULL_PANEL),
it must be preceded by:

1. A successful throughput re-run producing 011 / 012A / 012B
   artifacts and review-debt settlement so that the
   `Stage012AArtifactPresent`, `Stage012BArtifactPresent`,
   `UsesStage012ALoopLedger`, `UsesStage012BHypothesisLedger`,
   `RealLoopCandidateReady` items in the completion matrix are
   done.
2. A fresh human approval per
   `sigma_abc_loop_candidate_promotion.yaml:human_approval.scope`
   which is currently `granted=true` but scoped narrowly.

Until those two preconditions are met, 012C promotion remains
non-runnable — and Loop 019R is the final trust-stack verification
before that next step.

This Loop 019R does not pretend any of the above is already done.
