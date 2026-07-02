# PLAN.md — Initial Repo Checkpoint and 012C-Prep Dry-Run

## Branch

```text
repo_initial_checkpoint_then_012c_prep_dry_run
```

## Purpose

Create a clean repository checkpoint after the loop-skill integration fixes, then run only the safe 012C-preparation dry-run.

This task is engineering and readiness validation only. It must not start a new physics simplification stage.

## Hard Boundaries

Do not modify `sigma_abc` physics.
Do not start 012C promotion.
Do not start Stage 013.
Do not start tensorial IBP.
Do not introduce total-derivative reduction.
Do not claim full tensorial `sigma_{mu alpha beta}` correctness.
Do not add `agents/runtime.local.yaml` to git; it is local runtime configuration.
Do not commit generated run roots, caches, private runtime evidence, or `.claude/` state.

## Context

The previous repo audit fixes are implemented:

1. Provider-pool command outputs are schema-validated before use as freeze evidence.
2. Provider command templates no longer use raw `.format`; only known placeholders are replaced.
3. Local runtime duplicate profile key was removed from `agents/runtime.local.yaml`.
4. `scripts/build_claude_allowed_tools.py` supports `--require-bash`.
5. The repository has been initialized with git, but the first clean checkpoint is not yet committed.

Known verification before this task:

```text
pytest -> 296 passed, 1 warning
compileall -> PASS
check_agent_runtime sigma_abc_hypothesis_pre_ibp -> AVAILABLE, StubUsed False
```

## Tasks

### 1. Audit repo state before checkpoint

Run:

```bash
git status --short
git status --ignored --short | head -80
```

Confirm ignored/generated/private paths are not staged:

```text
agents/runtime.local.yaml
autonomous_runs/
autonomous_runs_test/
.claude/
__pycache__/
.pytest_cache/
```

If `.gitignore` misses any generated or private path, patch `.gitignore` before committing.

### 2. Re-run core verification

Run:

```bash
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
python3 scripts/check_agent_runtime.py --profile sigma_abc_hypothesis_pre_ibp
```

Required:

```text
pytest PASS
compileall PASS
AgentRuntimeStatus -> AVAILABLE
ProductionRunAllowed -> True
StubUsed -> False
```

### 3. Re-run targeted regression tests for the fixed audit findings

Run:

```bash
python3 -m pytest -q \
  tests/test_loop022_runner_provider_pool_integration.py::test_command_provider_rejects_invalid_preexisting_output \
  tests/test_loop022_runner_provider_pool_integration.py::test_provider_command_template_preserves_literal_braces \
  tests/test_yaml_config_hygiene.py \
  tests/test_runner_permission_policy.py -vv
```

Required:

```text
all targeted regressions PASS
```

### 4. Check Claude allowed-tools builder hard-fail behavior

Run:

```bash
python3 scripts/build_claude_allowed_tools.py \
  --plan docs/superpowers/plans/2026-07-02-runner-output-isolation-smoke-matrix.md \
  --require-bash
```

Required:

```text
Builder succeeds only when Bash is present in the allowed-tools list.
```

### 5. Create the initial git checkpoint

Review staged files manually, then create the initial checkpoint commit.

Suggested commands:

```bash
git add .
git status --short
git commit -m "Initial symbolic simplification loop checkpoint"
```

Before committing, verify that this command does not stage ignored/private runtime files:

```bash
git diff --cached --name-only | grep -E '(^agents/runtime.local.yaml$|^autonomous_runs/|^autonomous_runs_test/|^\\.claude/)' && exit 1 || true
```

If the grep finds any forbidden path, unstage it and patch `.gitignore`.

### 6. Run 012C-prep dry-run only

After the initial checkpoint exists, run only the preparation dry-run:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_loop_candidate_preparation \
  --dry-run \
  --from-current-checkpoint
```

Expected:

```text
NoCandidatePromoted -> True
NoIBPStarted -> True
NoTotalDerivativeIntroduced -> True
Stage013Started -> False
DCProjectionTo1D caveat preserved as INHERITED_PASS
```

If the dry-run reports missing Stage 012A/012B artifacts, do not patch physics and do not promote candidates. Record the artifact-contract failure as the next engineering task.

### 7. Write final report

Create:

```text
docs/devlog/loop_engine/INITIAL_CHECKPOINT_AND_012C_PREP_DRY_RUN_REPORT.md
```

The report must include:

```text
files changed
git checkpoint commit hash
pytest result
compileall result
runtime check result
targeted regression result
allowed-tools builder result
012C-prep dry-run result
whether Stage 012A/012B artifacts were resolved
confirmation no sigma_abc physics changed
confirmation no 012C promotion / 013 / IBP / total-derivative artifacts generated
recommended next command
```

## Acceptance Criteria

This task is complete only if:

```text
pytest PASS
compileall PASS
runtime check PASS
targeted regressions PASS
initial git checkpoint exists
012C-prep dry-run executed only as dry-run
no sigma_abc physics modified
no 012C promotion
no Stage 013
no tensorial IBP
no total-derivative reduction
final report exists
```

## Expected Next Step

If 012C-prep dry-run resolves the Stage 012A/012B artifact contract:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_loop_candidate_preparation \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 1
```

If artifact resolution fails, open a focused patch:

```text
sigma_abc_012ab_artifact_contract_patch
```

Do not start 012C promotion until the preparation gate reports readiness.
