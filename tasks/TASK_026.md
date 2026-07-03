# Task ID

TASK_026

# Title

Artifact-Based Agent Dispatcher

# Problem

The symbolic-simplification-loop workflow has separated roles, but the human still manually copies prompts, task specs, executor summaries, diffs, command outputs, and reviewer results between CodexPlanner, ClaudeCodeExecutor, and CodexReviewer sessions.

This manual glue layer is slow and error-prone. The repo needs a native `agent_bus` that coordinates role handoff through inbox/outbox artifacts and round-state files while preserving human approval boundaries.

# Goal

Add a first-version artifact-driven dispatcher for manual providers.

The dispatcher must:

- Create and maintain the required `agent_bus/` directory layout.
- Read `next_action_report.json`.
- Create `planner_prompt.md`.
- Wait for `TASK_XXX.md` from planner outbox.
- Create `executor_prompt.md`.
- Wait for `executor_report.md` from executor outbox.
- Collect git diff and acceptance command results.
- Create `reviewer_prompt.md`.
- Wait for `patch_review_result.json`.
- Write `agent_round_summary.json` and `agent_round_summary.md`.
- Support manual providers only.
- Never auto-freeze checkpoints.
- Never cross human approval boundaries.

# Non-goals

- Do not implement automatic Codex invocation.
- Do not implement automatic Claude Code CLI invocation.
- Do not implement background daemons or remote queues.
- Do not modify scientific formulas, validation outputs, checkpoints, or signoff ledgers.
- Do not auto-stage, auto-commit, auto-approve, auto-freeze, or auto-reject.
- Do not replace TASK_023/TASK_024 diagnosis behavior.
- Do not replace human scientist approval.

# Allowed edits

- Add `scripts/run_agent_dispatcher.py`.
- Add an importable helper module such as `loop_engine/agent_bus.py`.
- Add schemas if useful, such as:
  - `schemas/agent_round_summary.schema.json`
  - `schemas/agent_bus_state.schema.json`
- Add tests such as `tests/test_agent_dispatcher.py`.
- Add smoke fixtures under `tests/fixtures/agent_bus/` or generate fixtures with `tmp_path`.
- Add `.gitkeep` files only if needed to preserve empty bus directories.
- Add minimal docs comments inside the new dispatcher/helper code.

# Forbidden edits

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
- Do not auto-freeze checkpoint manifests.
- Do not modify unrelated untracked devlog audit files.

# Implementation steps

1. Add `agent_bus` layout creation.

The dispatcher must create this structure under a configurable bus root, defaulting to `agent_bus/`:

- `planner/inbox`
- `planner/processing`
- `planner/outbox`
- `planner/failed`
- `executor/inbox`
- `executor/processing`
- `executor/outbox`
- `executor/failed`
- `reviewer/inbox`
- `reviewer/processing`
- `reviewer/outbox`
- `reviewer/failed`
- `human/inbox`
- `human/approved`
- `human/rejected`
- `round_state/`

2. Define a deterministic round state.

Add a state file under `agent_bus/round_state/`, for example `current_round.json`, containing:

- `round_id`
- `created_at`
- `updated_at`
- `phase`
- `next_action_report`
- `planner_prompt`
- `task_spec`
- `executor_prompt`
- `executor_report`
- `reviewer_prompt`
- `patch_review_result`
- `agent_round_summary`
- `human_boundary_status`
- `events`

Use deterministic phase names such as:

- `INIT`
- `PLANNER_PROMPT_READY`
- `WAITING_FOR_TASK_SPEC`
- `EXECUTOR_PROMPT_READY`
- `WAITING_FOR_EXECUTOR_REPORT`
- `REVIEWER_PROMPT_READY`
- `WAITING_FOR_REVIEW_RESULT`
- `ROUND_SUMMARY_READY`
- `FAILED`

3. Add `scripts/run_agent_dispatcher.py`.

Required CLI behavior:

- `--bus-root PATH`, default `agent_bus`
- `--next-action-report PATH`
- `--round-id ID`, optional
- `--acceptance-command CMD`, repeatable
- `--advance`, advances exactly one phase
- `--status`, prints current phase and expected next artifact
- `--summary-only`, rebuilds summaries from existing artifacts
- `--no-command-run`, records acceptance commands as not run
- `--fail-reason TEXT`, moves current pending item to failed state

The script must be safe to run repeatedly. Re-running should not duplicate prompts or overwrite accepted outbox artifacts unless the user passes an explicit force flag.

4. Planner prompt generation.

When starting from `next_action_report.json`, write:

- `agent_bus/planner/inbox/planner_prompt.md`

The planner prompt must include:

- Diagnosis summary from `next_action_report.json`
- Required task-spec structure
- Explicit instruction that planner must not edit code
- Explicit instruction to write `TASK_XXX.md` to `agent_bus/planner/outbox/`
- Human boundary reminders

5. Planner outbox handling.

The dispatcher must wait for exactly one matching task spec, such as:

- `agent_bus/planner/outbox/TASK_026.md`

If multiple `TASK_*.md` files exist, fail deterministically with an ambiguity message unless `--task PATH` or equivalent is provided.

When accepted, copy or reference the task into state without modifying the planner outbox artifact.

6. Executor prompt generation.

Create:

- `agent_bus/executor/inbox/executor_prompt.md`

The executor prompt must include:

- The task spec content/path
- Allowed edits and forbidden edits from the task spec
- Instruction to implement only the bounded task
- Instruction to write `executor_report.md` to `agent_bus/executor/outbox/`
- Instruction not to auto-freeze checkpoints or cross human approval boundaries

7. Executor report handling.

The dispatcher must wait for:

- `agent_bus/executor/outbox/executor_report.md`

It must not trust success claims blindly. It must collect:

- `git status --short`
- `git diff --stat`
- `git diff`
- configured acceptance command outputs and exit codes, unless `--no-command-run` is passed

Store command evidence under `agent_bus/round_state/`, for example:

- `acceptance_results.json`
- `git_status.txt`
- `git_diff_stat.txt`
- `git_diff.patch`

8. Reviewer prompt generation.

Create:

- `agent_bus/reviewer/inbox/reviewer_prompt.md`

The reviewer prompt must include:

- Task spec
- Executor report
- Git status/diff evidence
- Acceptance command outputs
- Explicit instruction that reviewer must not edit files
- Required reviewer output path:
  - `agent_bus/reviewer/outbox/patch_review_result.json`

9. Reviewer result handling.

The dispatcher must wait for:

- `agent_bus/reviewer/outbox/patch_review_result.json`

Validate it against an existing or new schema. The result should include at least:

- `verdict`
- `blocking_issues`
- `nonblocking_caveats`
- `required_followups`
- `reviewed_files`
- `acceptance_evidence_assessment`
- `human_boundary_assessment`

10. Round summary generation.

Write:

- `agent_bus/round_state/agent_round_summary.json`
- `agent_bus/round_state/agent_round_summary.md`

The summary must include:

- round id
- final phase
- diagnosis input path
- task spec path
- executor report path
- reviewer result path
- git evidence paths
- acceptance command result paths
- verdict
- next recommended human action
- forbidden automatic actions
- statement that no checkpoint freeze or human signoff mutation was performed

11. Human approval boundary.

If `next_action_report.json`, task spec, executor report, or reviewer result indicates any of:

- `HUMAN_SIGNOFF_REQUIRED`
- `BOUNDARY_APPROVAL_REQUIRED`
- freeze approval
- IBP approval
- total derivative approval
- tensorial claim approval
- human scientist approval

then the dispatcher must route a summary to:

- `agent_bus/human/inbox/`

and must stop before any action that would imply approval.

12. Add tests.

Cover at least:

- Directory layout creation.
- Starting from `next_action_report.json` creates `planner_prompt.md`.
- Missing planner task leaves state in `WAITING_FOR_TASK_SPEC`.
- Planner task creates `executor_prompt.md`.
- Missing executor report leaves state in `WAITING_FOR_EXECUTOR_REPORT`.
- Executor report triggers git/acceptance evidence collection.
- Reviewer prompt includes task, executor report, diff, and command evidence.
- Missing reviewer result leaves state in `WAITING_FOR_REVIEW_RESULT`.
- Reviewer result creates JSON and markdown round summaries.
- Multiple planner task specs fail deterministically.
- Human-boundary classification routes summary to `human/inbox`.
- Dispatcher does not modify scientific artifacts, checkpoints, validation artifacts, or human signoff ledgers.

# Acceptance commands

```bash
python -m pytest tests/test_agent_dispatcher.py

python scripts/run_agent_dispatcher.py \
  --bus-root /tmp/loop_agent_bus_smoke \
  --next-action-report /tmp/loop_diag_smoke/next_action_report.json \
  --advance \
  --no-command-run

python scripts/run_agent_dispatcher.py \
  --bus-root /tmp/loop_agent_bus_smoke \
  --status
```

# Expected output files

- `scripts/run_agent_dispatcher.py`
- `loop_engine/agent_bus.py`
- Optional `schemas/agent_round_summary.schema.json`
- Optional `schemas/agent_bus_state.schema.json`
- `tests/test_agent_dispatcher.py`
- Runtime bus artifacts:
  - `agent_bus/planner/inbox/planner_prompt.md`
  - `agent_bus/executor/inbox/executor_prompt.md`
  - `agent_bus/reviewer/inbox/reviewer_prompt.md`
  - `agent_bus/round_state/current_round.json`
  - `agent_bus/round_state/acceptance_results.json`
  - `agent_bus/round_state/git_status.txt`
  - `agent_bus/round_state/git_diff_stat.txt`
  - `agent_bus/round_state/git_diff.patch`
  - `agent_bus/round_state/agent_round_summary.json`
  - `agent_bus/round_state/agent_round_summary.md`
  - optional human-boundary summary under `agent_bus/human/inbox/`

# Risks

- A dispatcher can look like automation authority. Mitigate by making version one artifact-driven and manual-provider-only.
- Re-running the dispatcher can overwrite hand-authored artifacts. Mitigate with idempotent state checks and no overwrite by default.
- Multiple outbox files can create ambiguity. Mitigate by failing deterministically.
- Acceptance commands can be expensive or mutate state. Mitigate with explicit command list, recorded outputs, and `--no-command-run`.
- Human approval boundaries can be crossed accidentally if summaries are treated as approvals. Mitigate by routing boundary cases to `human/inbox` and explicitly forbidding approval, signoff, and freeze mutation.
- Git diffs may contain large outputs. Mitigate by writing full diff to a file and summarizing paths in markdown.

# Definition of done

TASK_026 is done when:

- `scripts/run_agent_dispatcher.py` creates the required `agent_bus/` layout.
- `next_action_report.json` can start a dispatcher round without manual prompt copying.
- Planner, executor, and reviewer handoffs are represented by inbox/outbox artifacts.
- Dispatcher waits for manual-provider outputs instead of invoking Codex or Claude automatically.
- Git diff and acceptance command evidence are collected after executor report arrival.
- `agent_round_summary.json` and `agent_round_summary.md` are written.
- Human approval boundary cases are routed to `agent_bus/human/inbox/` and stop safely.
- Tests cover layout, phase transitions, ambiguity handling, evidence collection, summary generation, and read-only safety.
- No scientific artifacts, frozen checkpoints, completed-stage validation artifacts, validated sigma outputs, or human signoff ledgers are modified.
