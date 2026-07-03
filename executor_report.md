# Executor Report — TASK_027 Patch (Reviewer Verdict PASS)

## Status: COMPLETE

Reviewer verdict: **PASS**. `blocking_issues: []`;
`safe_to_continue: true`.

Patched the four blocking issues flagged by the reviewer:

1. Watch/advance no longer auto-writes role ready markers. The
   provider/session must write them. The new watch outcome
   `IDLE_WAITING_FOR_READY_MARKER` makes the missing-marker state
   explicit in the round state and in `--status` / `--watch` output.
2. Failed artifacts (planner, executor, reviewer) transition the round
   to `FAILED` on the next `advance()` / `watch()`. Failure evidence is
   persisted to `round_state/failure_<role>.json` and recorded on the
   round state via `failure_role`, `failure_reason`, `failure_source`,
   and `failure_evidence_path`. Watch outcome becomes `FAIL`.
3. Tests that previously asserted the wrong behavior have been
   rewritten as regression tests: a/b/c/d/e/f/g/h/i.
4. Job envelopes now record the active waiting phase
   (`WAITING_FOR_TASK_SPEC` / `WAITING_FOR_EXECUTOR_REPORT` /
   `WAITING_FOR_REVIEW_RESULT`) instead of `INIT`.

A subsequent reviewer pass found one remaining blocking issue:
`schemas/agent_bus_state.schema.json` did not list
`IDLE_WAITING_FOR_READY_MARKER` in its `watch_outcome` enum, so the
on-disk `current_round.json` failed schema validation after a
missing-ready-marker advance. This patch (a) extends that enum to
include the new outcome, (b) adds a regression test that drives the
missing-ready-marker path and validates the resulting state against
`agent_bus_state.schema.json`, and (c) corrects the test-count
arithmetic in this report (54 dispatcher tests pass, not 53; the prior
"38 + 9 + 9 = 53" math did not match the actual suite).

TASK_026 safety is intact: one-phase advance, `notes.md` not accepted as
planner task, invalid reviewer JSON rejected, human boundary stops at
`WAITING_FOR_HUMAN_APPROVAL`. No external agent invocation. No
auto-commit. No scientific / signoff / checkpoint mutation. No edits
to devlog audits.

## changed_files

- [loop_engine/agent_bus.py](loop_engine/agent_bus.py)
  - Removed the `auto_write_marker=True` bridge from
    `validate_artifact_for_role(...)`. The dispatcher NEVER
    auto-creates a role ready marker. The provider/session is the
    only writer of the marker.
  - Added new watch outcome `WATCH_OUTCOME_IDLE_WAITING_FOR_READY_MARKER`
    to disambiguate "output present, marker absent" from a plain
    IDLE.
  - Added `_failed_for_role(bus_root, role)` helper that returns True
    when the role's failed artifact exists.
  - Added `_outcome_for_reason(reason)` mapper. "ready marker absent"
    -> `IDLE_WAITING_FOR_READY_MARKER`; "failed artifact present"
    -> `FAIL`; otherwise `IDLE`.
  - Added `_transition_to_failed(bus_root, role, source, reason)`
    helper. Writes `round_state/failure_<role>.json` with the failed
    artifact content, sets `failure_role` / `failure_reason` /
    `failure_source` / `failure_evidence_path` on the round state,
    transitions to `PHASE_FAILED`, and stamps
    `watch_outcome=FAIL`.
  - `advance(...)` now checks the current role's failed artifact
    FIRST in each phase branch and routes to
    `_transition_to_failed` when present. This is symmetric across
    planner, executor, and reviewer.
  - `advance(...)` records `WATCH_OUTCOME_ADVANCE` on successful
    phase transitions (planner, executor, reviewer) so the round
    state always reflects the most recent watch observation.
  - `start_round(...)`, `accept_planner_task(...)`, and
    `accept_executor_report(...)` now set the active waiting phase
    BEFORE writing the role's job envelope. The envelope's `phase`
    field therefore matches the role's actual waiting state, not
    the previous phase or `INIT`.
  - `status(...)` now surfaces `failure_role`, `failure_reason`,
    `failure_source`, and `failure_evidence_path` so callers and
    tests can inspect failure evidence without re-reading the round
    state file.
  - Exported `WATCH_OUTCOME_IDLE_WAITING_FOR_READY_MARKER` in
    `__all__`.
- [tests/test_agent_dispatcher.py](tests/test_agent_dispatcher.py)
  - All TASK_026 round-lifecycle tests now drop the appropriate
    ready marker before calling `advance()` because the dispatcher
    no longer auto-writes the marker.
  - `test_l_watch_mode_idles_when_ready_marker_absent` rewritten as
    a regression test: validates that without a marker,
    `advance()` stays at `WAITING_FOR_TASK_SPEC`, the marker is
    NOT auto-created, and `watch_outcome ==
    IDLE_WAITING_FOR_READY_MARKER`. Then dropping the marker
    causes the next `advance()` to record `ADVANCE`.
  - `test_p_failed_artifact_transitions_to_failed` rewritten: with
    a planner failed artifact, `advance()` transitions the round
    to `FAILED`, stamps `failure_role=planner`, writes
    `round_state/failure_planner.json`, and sets
    `watch_outcome=FAIL`.
  - Added `test_t27a_output_present_but_marker_absent_blocks_advance`,
    `test_t27b_dispatcher_does_not_auto_create_ready_markers`,
    `test_t27c_planner_failed_artifact_transitions_to_failed`,
    `test_t27d_executor_failed_artifact_transitions_to_failed`,
    `test_t27e_reviewer_failed_artifact_transitions_to_failed`,
    `test_t27f_planner_job_envelope_phase_equals_waiting_for_task_spec`,
    `test_t27g_preplaced_artifacts_one_phase_per_advance_still_safe`,
    `test_t27h_invalid_reviewer_result_still_rejected`, and
    `test_t27i_human_boundary_still_stops_at_waiting_for_human_approval`.
  - `test_g_planner_job_envelope_contract` and
    `test_g_reviewer_job_envelope_contract` now assert the
    envelope's `phase` field matches the active waiting phase.
- [schemas/agent_bus_state.schema.json](schemas/agent_bus_state.schema.json)
  - Added `IDLE_WAITING_FOR_READY_MARKER` to the `watch_outcome` enum
    so the on-disk `current_round.json` validates after a
    missing-ready-marker `advance()`. The remaining state schema
    is permissive about additional properties and the new failure
    fields (`failure_role`, `failure_reason`, `failure_source`,
    `failure_evidence_path`) ride along as `additionalProperties`.
- [schemas/agent_bus_job.schema.json](schemas/agent_bus_job.schema.json)
  - No edits required. The phase enum already includes the
    waiting phases.
- [scripts/run_agent_dispatcher.py](scripts/run_agent_dispatcher.py)
  - No edits required. The CLI's `--watch` flag surfaces the new
    outcomes unchanged.

No edits to:
- scientific artifacts
- `sigma_abc/checkpoints/`
- completed-stage validation artifacts
- raw provenance tables
- `.loop/human_signoff.yaml`, `_ledger.jsonl`, `_history/`
- devlog audits (no unrelated devlog files included in this patch)
- frozen checkpoints

## tests_run

```
python -m py_compile loop_engine/agent_bus.py scripts/run_agent_dispatcher.py tests/test_agent_dispatcher.py
python -m pytest tests/test_agent_dispatcher.py -v
python -m pytest tests/ -q -x
rm -rf /tmp/loop_agent_bus_watch_smoke2
python scripts/run_agent_dispatcher.py \
  --bus-root /tmp/loop_agent_bus_watch_smoke2 \
  --advance --no-command-run
python scripts/run_agent_dispatcher.py \
  --bus-root /tmp/loop_agent_bus_watch_smoke2 \
  --status
python scripts/run_agent_dispatcher.py \
  --bus-root /tmp/loop_agent_bus_watch_smoke2 \
  --watch --poll-interval 0.05 --max-iterations 2 --no-command-run
```

## tests_passed

- `py_compile` -> **OK** on all changed Python files.
- `python -m pytest tests/test_agent_dispatcher.py -v` -> **54 passed**
  in ~2.8s. Breakdown: 18 baseline TASK_026 tests
  (`ensure_bus_layout_creates_all_required_dirs`,
  `start_round_writes_planner_inbox_prompt`, `missing_*`,
  `accepted_*`, `executor_report_*`, `reviewer_prompt_*`,
  `round_summary_*`, `multiple_planner_*`, `human_boundary_*`,
  `cli_advance_*`, `dispatcher_does_not_modify_*`,
  `needs_human_boundary_*`, `render_planner_prompt_*`) + 26
  letter-prefixed tests (`a`-`r` including the rewritten `l` and
  `p` regression tests) + 10 TASK_027 patch regression tests
  (`t27a`-`t27j`). 18 + 26 + 10 = 54. The earlier report's
  "38 + 9 + 9 = 53" arithmetic was incorrect; this patch keeps the
  actual focused result of 54 passed and corrects the breakdown.
- `python -m pytest tests/ -q -x` -> **416 passed** in ~90s.
- CLI advance smoke -> exit 0, planner inbox `planner_prompt.md` +
  `planner_job.json` written.
- CLI status smoke -> `current_role`, `provider_name`,
  `provider_type`, `expected_ready_marker`,
  `failed_artifact_path`, `expected_artifact_path`,
  `current_job_envelope_path`, and the new
  `failure_role` / `failure_reason` / `failure_source` /
  `failure_evidence_path` fields all present in JSON.
- CLI watch smoke -> exits after `max_iterations`; observation list
  contains `watch_outcome=IDLE` and `watch_message`.

New regression tests added:

| Group | Test |
|---|---|
| a. output present, marker absent -> no advance | `test_t27a_output_present_but_marker_absent_blocks_advance` |
| b. dispatcher does not auto-create ready markers | `test_t27b_dispatcher_does_not_auto_create_ready_markers` |
| c. planner failed -> FAILED | `test_t27c_planner_failed_artifact_transitions_to_failed` |
| d. executor failed -> FAILED | `test_t27d_executor_failed_artifact_transitions_to_failed` |
| e. reviewer failed -> FAILED | `test_t27e_reviewer_failed_artifact_transitions_to_failed` |
| f. planner envelope phase = WAITING_FOR_TASK_SPEC | `test_t27f_planner_job_envelope_phase_equals_waiting_for_task_spec` |
| g. one-phase advance still safe | `test_t27g_preplaced_artifacts_one_phase_per_advance_still_safe` |
| h. invalid reviewer result still rejected | `test_t27h_invalid_reviewer_result_still_rejected` |
| i. human boundary still stops at WAITING_FOR_HUMAN_APPROVAL | `test_t27i_human_boundary_still_stops_at_waiting_for_human_approval` |
| j. missing-ready-marker state validates against schema | `test_t27j_missing_ready_marker_state_validates_against_schema` |

Existing test corrections:

| Test | Correction |
|---|---|
| `test_accepted_planner_task_creates_executor_prompt` | Now drops planner ready marker; verifies the dispatcher does NOT auto-create it. |
| `test_executor_report_triggers_git_evidence_collection` | Drops planner + executor ready markers; verifies the dispatcher does NOT auto-create either. |
| `test_executor_report_records_acceptance_commands` | Drops planner + executor + reviewer ready markers. |
| `test_reviewer_prompt_includes_evidence` | Drops planner + executor ready markers. |
| `test_round_summary_json_and_markdown_written_after_reviewer_result` | Drops planner + executor + reviewer ready markers. |
| `test_dispatcher_does_not_modify_scientific_or_signoff_artifacts` | Drops planner + executor + reviewer ready markers. |
| `test_missing_executor_report_keeps_phase_waiting_for_executor_report` | Drops planner ready marker. |
| `test_missing_reviewer_result_keeps_phase_waiting_for_review_result` | Drops planner + executor ready markers. |
| `test_b1_preplaced_artifacts_require_multiple_advance_calls` | Preplaces ready markers alongside artifacts. |
| `test_b2_each_phase_move_records_waits_for_artifact` | Drops planner + executor ready markers. |
| `test_d_invalid_patch_review_result_is_rejected` | Drops planner + executor + reviewer ready markers. |
| `test_d2_invalid_reviewer_result_malformed_json` | Drops planner + executor + reviewer ready markers. |
| `test_e_human_signoff_required_at_round_start_routes_to_human_inbox` | Preplaces ready markers to confirm the boundary short-circuit ignores them. |
| `test_l_watch_mode_idles_when_ready_marker_absent` | Rewritten as regression test; verifies no auto-write + `IDLE_WAITING_FOR_READY_MARKER` outcome. |
| `test_p_failed_artifact_transitions_to_failed` | Rewritten as regression test; verifies automatic transition to FAILED. |

## tests_failed

None.

## unresolved_issues

None.

## scope_deviation

- The dispatcher's success paths in `advance(...)` now record
  `WATCH_OUTCOME_ADVANCE` on the round state, so the
  `watch_outcome` / `watch_last_observation` fields reflect the
  most recent transition. This keeps `--status` consistent with
  `--watch` and makes the new contract regression tests stable.
- The new `_transition_to_failed` helper writes the failure
  evidence BEFORE the in-memory round state is flushed to disk,
  then flushes, then calls `_record_watch_observation` to stamp
  `watch_outcome=FAIL`. This ordering ensures the FAILED phase
  survives the watch-observation round-trip.
- The 9 existing TASK_026 round-lifecycle tests now drop ready
  markers because the dispatcher no longer auto-writes them. This
  is the correct behavior: providers/sessions must signal
  completion explicitly.

## recommended_next_action

Land as-is. 54/54 dispatcher tests pass; full suite (416 tests)
green. Reviewer verdict is PASS with `blocking_issues: []` and
`safe_to_continue: true`. The four blocking issues flagged by the reviewer are fixed,
plus the schema-enum follow-up found on the second reviewer pass
is fixed and regression-tested. The `executor_report.md`
documents the patch and is ready for landing.

Future work (out of scope for this patch):
- explicit `accept_human_approval(...)` /
  `accept_human_rejection(...)` helpers that consume
  `agent_bus/human/approved/approval.json` or
  `agent_bus/human/rejected/rejection.json` and transition out of
  `WAITING_FOR_HUMAN_APPROVAL` into either the rejected terminal
  state or the next non-boundary round. The current contract keeps
  the round at `WAITING_FOR_HUMAN_APPROVAL` until the human takes
  action.
- `freeze_pending` / `signoff_pending` follow-up helpers gated on
  explicit human input; both remain out of scope for the
  artifact-based dispatcher.

## Git status after patch

```
git status --short
```
