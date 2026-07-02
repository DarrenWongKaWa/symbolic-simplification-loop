# Repo Review Findings Fix Report

## Verdict

PASS as repo-review findings fix.

## Fixed Findings

### 1. Provider-pool schema validation

Problem:

```text
Command providers treated output-file existence as schema_valid.
```

Fix:

- `_run_command_provider` now validates `request.output_path` through the
  configured schema name.
- Invalid reviewer JSON no longer becomes freeze evidence.
- Existing output must be refreshed by the provider attempt before it can be
  accepted as schema-valid evidence.

Regression tests:

```text
test_command_provider_rejects_invalid_preexisting_output
test_provider_command_template_preserves_literal_braces
```

### 2. Provider command placeholder expansion

Problem:

```text
_build_command_for_provider used str.format(...) on every token.
Literal JSON/Python braces in command strings could raise KeyError.
```

Fix:

```text
Only known placeholders are replaced:
{agent_name}, {prompt_path}, {output_path}, {stage_dir}
```

### 3. Duplicate YAML keys

Problem:

```text
agents/runtime.local.yaml duplicated sigma_abc_hypothesis_pre_ibp_throughput.
```

Fix:

- Merged the duplicated profile block.
- Added duplicate-key YAML regression coverage for runtime config files.

### 4. Claude allowed-tools generator strict mode

Problem:

```text
scripts/build_claude_allowed_tools.py always returned PASS, even when no Bash
tools were extracted from an execution plan.
```

Fix:

- Added `--require-bash`.
- The CLI now returns `overall_gate -> FAIL` when no Bash tools are generated
  and strict execution mode is requested.

### 5. Git repository boundary

Problem:

```text
symbolic-simplification-loop was not a git repository.
```

Fix:

```text
git init
```

No commit was created.

## Verification

Targeted red/green tests:

```bash
python3 -m pytest -q \
  tests/test_loop022_runner_provider_pool_integration.py::test_provider_command_template_preserves_literal_braces \
  tests/test_loop022_runner_provider_pool_integration.py::test_command_provider_rejects_invalid_preexisting_output \
  tests/test_yaml_config_hygiene.py \
  tests/test_runner_permission_policy.py::test_build_claude_allowed_tools_require_bash_fails_without_run_commands \
  -vv
```

Result:

```text
4 passed
```

Full suite:

```bash
python3 -m pytest -q
296 passed, 1 warning
```

Compile check:

```bash
python3 -m compileall loop_engine scripts tests
PASS
```

Runtime check:

```bash
python3 scripts/check_agent_runtime.py --profile sigma_abc_hypothesis_pre_ibp
AgentRuntimeStatus -> AVAILABLE
ProductionRunAllowed -> True
StubUsed -> False
```

Invalid pre-existing output reproduction:

```text
schema_valid -> false
freeze_evidence_valid -> false
selected_provider -> null
runtime_status -> AGENT_SCHEMA_FAIL
```

## Boundaries

- `sigma_abc` physics unchanged.
- 012C promotion not started.
- Stage 013 not started.
- Tensorial IBP not started.
- Total-derivative reduction not introduced.
- Full tensorial correctness not claimed.
- `DCProjectionTo1D -> INHERITED_PASS` caveat preserved.

## Next Safe Action

Commit this infrastructure checkpoint, then run a dry-run for:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_loop_candidate_preparation \
  --dry-run \
  --from-current-checkpoint
```
