# Task ID

TASK_027

# Title

Provider Contracts, Job Envelopes, and Safe Watch Mode for Agent Dispatcher

# Problem

TASK_026 introduces an artifact-based dispatcher with role prompts and one-phase advancement, but fixed role identity is not enough for reliable handoff. Each role needs an explicit machine-readable contract that declares what it may read, what it must write, how completion is signaled, what failure artifact to emit, what paths are forbidden, and which state transitions are allowed.

The human also still has to manually run `scripts/run_agent_dispatcher.py --advance` after every artifact appears. The dispatcher needs a safe watch mode that wakes up, checks expected artifacts, validates them, and advances one phase at a time without invoking real external agents or crossing human approval boundaries.

# Goal

Extend the TASK_026 artifact-based agent dispatcher with:

- Machine-readable job envelopes for planner, executor, and reviewer jobs.
- Explicit role input/output path declarations.
- Ready markers or equivalent atomic completion signals.
- Failed-artifact paths.
- Forbidden-path declarations.
- Provider contract support for manual providers and optional mock providers in tests.
- A safe watch mode that repeatedly performs one-phase advancement while respecting waiting states and human boundaries.
- Improved status output showing the current role, expected artifact, ready marker, provider type, and human-boundary state.

# Non-goals

- Do not implement real Claude Code CLI invocation.
- Do not implement real Codex CLI invocation.
- Do not implement background execution of real providers.
- Do not auto-commit.
- Do not auto-stage.
- Do not auto-freeze checkpoints.
- Do not auto-create or mutate human signoff.
- Do not replace TASK_026 artifact handoff semantics.
- Do not change scientific validation, review, completion matrix, signoff, freeze, or checkpoint semantics.

# Allowed edits

- `loop_engine/agent_bus.py`
- `scripts/run_agent_dispatcher.py`
- `schemas/agent_bus_job.schema.json`
- `schemas/agent_bus_state.schema.json`, only if needed to add job-envelope fields
- `schemas/agent_round_summary.schema.json`, only if needed for backward-compatible references to job envelopes or watch outcomes
- `tests/test_agent_dispatcher.py`
- A new focused test file such as `tests/test_agent_dispatcher_watch_mode.py`
- Smoke fixtures under `tests/fixtures/agent_bus/` or generated `tmp_path` fixtures
- Minimal documentation comments in dispatcher/helper code

# Forbidden edits

- Do not implement real Claude Code CLI provider.
- Do not implement real Codex CLI provider.
- Do not auto-commit.
- Do not auto-stage.
- Do not auto-freeze checkpoints.
- Do not edit scientific artifacts.
- Do not edit frozen checkpoints.
- Do not edit files under `sigma_abc/checkpoints/`.
- Do not edit completed-stage validation artifacts.
- Do not edit raw provenance tables.
- Do not edit validated `sigma_abc` outputs.
- Do not edit `.loop/human_signoff.yaml`.
- Do not edit `.loop/human_signoff_ledger.jsonl`.
- Do not edit `.loop/human_signoff_history/`.
- Do not auto-create human signoff files.
- Do not modify unrelated untracked devlog audit files.

# Implementation steps

1. Add a job-envelope schema.

Create `schemas/agent_bus_job.schema.json` requiring at least:

- `round_id`
- `role`
- `phase`
- `working_directory`
- `input_files`
- `output_files`
- `ready_marker`
- `failed_artifact`
- `forbidden_paths`
- `expected_schema`
- `provider_name`
- `allowed_next_states`

Allowed `role` values should include `planner`, `executor`, and `reviewer`.

`expected_schema` may be `null` for markdown artifacts such as `TASK_XXX.md` and `executor_report.md`, but should be populated for structured artifacts such as `patch_review_result.json` when a schema exists.

2. Generate job envelopes for each role.

When the dispatcher creates a prompt for a role, it must also write a job envelope next to that prompt, for example:

- `agent_bus/planner/inbox/planner_job.json`
- `agent_bus/executor/inbox/executor_job.json`
- `agent_bus/reviewer/inbox/reviewer_job.json`

Each job envelope must declare exact paths for:

- role input files
- required output artifact
- ready marker
- failed artifact
- forbidden paths

Suggested ready markers:

- `agent_bus/planner/outbox/TASK_READY`
- `agent_bus/executor/outbox/EXECUTOR_READY`
- `agent_bus/reviewer/outbox/REVIEW_READY`

Suggested failed artifacts:

- `agent_bus/planner/failed/planner_failed.md`
- `agent_bus/executor/failed/executor_failed.md`
- `agent_bus/reviewer/failed/reviewer_failed.md`

3. Add provider contract support.

Add a provider abstraction or configuration field that supports:

- `manual`
- `mock`, only for tests if useful

For TASK_027, `manual` must be the default and must not invoke any external command.

The dispatcher may validate that a provider exists and can declare its expected input/output paths, but it must not launch Claude Code, Codex CLI, or other real agents.

4. Update generated prompts.

Every generated role prompt must contain explicit sections:

- `What To Read`
- `What To Write`
- `Output Path`
- `Ready Marker`
- `Failed Artifact`
- `Forbidden Paths`
- `When To Stop`

Planner prompt must instruct the planner to write `TASK_XXX.md` to planner outbox and then create the planner ready marker.

Executor prompt must instruct the executor to write `executor_report.md` to executor outbox and then create the executor ready marker.

Reviewer prompt must instruct the reviewer to write `patch_review_result.json` to reviewer outbox and then create the reviewer ready marker.

5. Validate expected artifacts before advancement.

Before advancing from a waiting phase, the dispatcher must verify:

- the expected output artifact exists
- the ready marker exists
- the failed artifact does not exist, unless transitioning to `FAILED`
- the output artifact is non-empty
- the output artifact validates against `expected_schema` if one is declared
- no forbidden paths were modified by the dispatcher itself

If the ready marker is missing, remain in the current waiting phase and report the missing marker in status output.

If the failed artifact exists, transition to `FAILED` and record the failure evidence.

6. Add safe watch mode.

Extend `scripts/run_agent_dispatcher.py` with:

- `--watch`
- `--poll-interval N`

Watch mode must:

- call the same one-phase advancement code used by `--advance`
- perform at most one state transition per poll cycle
- respect `WAITING_*` phases
- idle when expected artifacts or ready markers are absent
- stop or idle at `WAITING_FOR_HUMAN_APPROVAL`
- never auto-freeze checkpoints
- never auto-create signoff
- never invoke real providers
- validate expected artifacts before advancing
- exit cleanly on `ROUND_SUMMARY_READY` or `FAILED`, unless an explicit future option says otherwise

7. Add a human-boundary waiting phase.

If human approval is required, the state machine should use an explicit phase such as:

- `WAITING_FOR_HUMAN_APPROVAL`

This phase must include:

- human boundary reason
- expected human input path, such as `agent_bus/human/approved/approval.json` or `agent_bus/human/rejected/rejection.json`
- statement that no approval is inferred from summaries or reviewer output

TASK_027 does not need to implement approval ingestion beyond safe detection and idling, unless TASK_026 already has a compatible manual human-boundary artifact.

8. Improve status output.

`scripts/run_agent_dispatcher.py --status` must show:

- current phase
- current role
- expected next artifact
- expected ready marker
- failed artifact path
- provider type
- human boundary state, if applicable
- whether watch mode would advance, idle, fail, or stop

Status must be read-only.

9. Update round state.

Extend `current_round.json` to record:

- current job envelope path
- provider name
- ready marker path
- expected artifact path
- failed artifact path
- watch mode observations or last idle reason
- allowed next states

Keep the update backward-compatible with TASK_026 fields.

10. Add tests.

Cover at least:

- Generated planner, executor, and reviewer job envelopes contain correct input/output paths.
- Job envelopes include ready marker, failed artifact, forbidden paths, provider name, and allowed next states.
- Prompts include read/write/output/ready-marker/forbidden-path/stop sections.
- Manual provider does not invoke external agents.
- Optional mock provider test does not require real external agents.
- Watch mode advances only one phase at a time.
- Watch mode idles safely when expected artifacts are absent.
- Watch mode idles when expected ready marker is absent.
- Invalid expected artifact prevents advancement.
- Missing expected artifact prevents advancement.
- Failed artifact transitions to `FAILED`.
- Watch mode stops or idles at `WAITING_FOR_HUMAN_APPROVAL`.
- Status output includes phase, role, expected artifact, ready marker, provider type, and human boundary state.
- Dispatcher does not modify scientific artifacts, frozen checkpoints, completed validation artifacts, validated sigma outputs, or human signoff ledgers.

# Acceptance commands

```bash
python -m pytest tests/test_agent_dispatcher.py
python -m pytest tests/test_agent_dispatcher_watch_mode.py

python scripts/run_agent_dispatcher.py \
  --bus-root /tmp/loop_agent_bus_watch_smoke \
  --next-action-report /tmp/loop_diag_smoke/next_action_report.json \
  --advance \
  --no-command-run

python scripts/run_agent_dispatcher.py \
  --bus-root /tmp/loop_agent_bus_watch_smoke \
  --status

python scripts/run_agent_dispatcher.py \
  --bus-root /tmp/loop_agent_bus_watch_smoke \
  --watch \
  --poll-interval 1 \
  --no-command-run
```

# Expected output files

- Updated `loop_engine/agent_bus.py`
- Updated `scripts/run_agent_dispatcher.py`
- `schemas/agent_bus_job.schema.json`
- Optional updated `schemas/agent_bus_state.schema.json`
- Optional updated `schemas/agent_round_summary.schema.json`
- Updated `tests/test_agent_dispatcher.py`
- Optional `tests/test_agent_dispatcher_watch_mode.py`
- Runtime bus artifacts:
  - `agent_bus/planner/inbox/planner_job.json`
  - `agent_bus/executor/inbox/executor_job.json`
  - `agent_bus/reviewer/inbox/reviewer_job.json`
  - `agent_bus/planner/outbox/TASK_READY`
  - `agent_bus/executor/outbox/EXECUTOR_READY`
  - `agent_bus/reviewer/outbox/REVIEW_READY`
  - `agent_bus/planner/failed/planner_failed.md`
  - `agent_bus/executor/failed/executor_failed.md`
  - `agent_bus/reviewer/failed/reviewer_failed.md`
  - updated `agent_bus/round_state/current_round.json`
  - updated `agent_bus/round_state/agent_round_summary.json`
  - updated `agent_bus/round_state/agent_round_summary.md`

# Risks

- Watch mode can accidentally look like autonomous execution. Mitigate by supporting manual and test mock providers only, with no external-agent invocation.
- Ready markers can be created before artifacts are fully written. Mitigate by requiring both non-empty output artifacts and ready markers, and by recommending marker creation only after output write completion.
- Repeated watch cycles can overwrite prompts or state. Mitigate with idempotent phase handling and no overwrite of accepted outbox artifacts by default.
- Human-boundary cases can be mistaken for approval. Mitigate with an explicit `WAITING_FOR_HUMAN_APPROVAL` phase and no inferred approval from summaries, reviews, or ready markers.
- Provider contracts can drift from prompts. Mitigate by generating prompts from the same job-envelope data structure used for validation.
- Tests may accidentally require real providers. Mitigate with manual-provider assertions and optional mock-only tests.

# Definition of done

TASK_027 is done when:

- Planner, executor, and reviewer prompts each have a matching machine-readable job envelope.
- Job envelopes declare input files, output files, ready marker, failed artifact, forbidden paths, expected schema, provider name, and allowed next states.
- Generated prompts explicitly declare what to read, what to write, where to write it, what ready marker to create, what not to edit, and when to stop.
- Manual provider is the default and never invokes external agents.
- Optional mock provider, if implemented, is limited to tests.
- `--watch --poll-interval N` safely performs repeated one-phase advancement.
- Watch mode idles when expected artifacts or ready markers are absent.
- Watch mode validates expected artifacts before advancement.
- Watch mode stops or idles at `WAITING_FOR_HUMAN_APPROVAL`.
- Status output reports phase, role, expected artifact, ready marker, provider type, and human-boundary state.
- Tests cover job envelopes, prompt sections, watch behavior, missing/invalid ready markers, human-boundary stopping, and no external-agent invocation.
- No scientific artifacts, frozen checkpoints, completed-stage validation artifacts, validated sigma outputs, or human signoff ledgers are modified.
