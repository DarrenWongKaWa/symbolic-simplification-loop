# Runner Permission Policy Hardening Report

## Verdict

PASS as executor-permission policy hardening.

## Problem

The Claude/Codex execution loop could spend excessive wall time when a broad
plan let the executor attempt commands outside the manually supplied
`--allowedTools` list. The denied command was operationally useful signal, but
it was not represented as a structured loop-engine outcome.

## What Changed

- Added `loop_engine/executor_permission_policy.py`.
- Added `scripts/build_claude_allowed_tools.py`.
- Added `tests/test_runner_permission_policy.py`.
- Updated the Claude/Codex loop protocol with a required
  `Claude Allowed-Tools Gate`.

## New Policy

Before a Claude execution patch, Codex should run:

```bash
python3 scripts/build_claude_allowed_tools.py --plan <plan_path>
```

The resulting `claude_allowed_tools_arg` is the source of truth for
Claude's `--allowedTools` argument.

Only commands declared in fenced `Run` bash blocks become `Bash(...)` tools.
Undeclared commands remain denied and are classified as:

```text
EXECUTOR_UNAUTHORIZED_COMMAND
```

Executor timeout is classified separately as:

```text
EXECUTOR_TIMEOUT
```

## Validation

Targeted test:

```bash
python3 -m pytest -q tests/test_runner_permission_policy.py -vv
4 passed
```

Full-suite verification is recorded in the final Codex response for this
patch.

Full-suite test:

```bash
python3 -m pytest -q
274 passed, 1 warning
```

Bytecode check:

```bash
python3 -m compileall loop_engine scripts tests
No errors
```

## Boundaries

- `sigma_abc` physics unchanged.
- 012C promotion not started.
- Stage 013 not started.
- Tensorial IBP not started.
- Total-derivative reduction not introduced.
- Full tensorial correctness not claimed.
- `DCProjectionTo1D -> INHERITED_PASS` caveat preserved.

## Next Use

For future Claude handoffs, generate allowed tools from the plan rather than
hand-writing them. If Claude asks for an undeclared command, write a smaller
follow-up plan that declares the command and rerun the allowed-tools generator.
