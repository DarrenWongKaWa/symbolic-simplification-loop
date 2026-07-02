# Loop Skill / Repo Integration Follow-Up Test Isolation Report

## Verdict

PASS as test-isolation follow-up for `loop_skill_repo_integration_patch`.

## Executor Status

Claude Code was invoked to execute:

```text
docs/superpowers/plans/2026-07-02-loop-skill-repo-integration-followup-test-isolation.md
```

The Claude process was manually interrupted after it requested Bash commands
outside the allowed tool list. Therefore this report is a Codex-side
verification report, not a clean Claude completion report.

## Issue

The previous patch routed pytest runner subprocesses to a shared
`autonomous_runs_test/` root. This fixed live-root pollution but allowed test
order pollution. If
`test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008` ran before
`test_sigma_abc_dry_run_reports_profile_driven_next_stage`, the second test saw
all safe-prefusion stages already completed and reported:

```text
NextStage -> none
Next allowed stage: none
```

The test expected a fresh run root where stage 006 was still next.

## Fix Verified

Runner tests now use per-test run roots by default. Tests that intentionally
need persistent state pass the same `run_root` explicitly.

Key changes verified by Codex inspection:

```text
tests/test_autonomous_loop_runner.py
  run_runner(..., run_root: Path | None = None)
  default run root is tempfile.mkdtemp(...)
  tests that inspect output pass tmp_path-derived run_root

tests/test_loop020a_runner_path_hygiene.py
  runner helper accepts run_root
  tests pass tmp_path-derived run_root
```

## Verification

Codex independently ran:

```text
python3 -m pytest -q \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008 \
  tests/test_autonomous_loop_runner.py::test_sigma_abc_dry_run_reports_profile_driven_next_stage \
  -vv
```

Result:

```text
2 passed, 1 warning
```

Codex independently ran:

```text
python3 -m pytest -q
```

Result:

```text
266 passed, 1 warning in 47.36s
```

Codex independently ran:

```text
python3 -m compileall loop_engine scripts tests
```

Result:

```text
No errors
```

## Boundaries

- sigma_abc physics unchanged.
- 012C promotion not started.
- Stage 013 not started.
- Tensorial IBP not started.
- Total-derivative reduction not introduced.
- Full tensorial correctness not claimed.
- DCProjectionTo1D inherited-pass caveat preserved.

## Status

The follow-up test-isolation blocker is cleared. The broader loop can now move
to report/claim consistency hardening or the next explicitly approved
infrastructure hygiene stage.
