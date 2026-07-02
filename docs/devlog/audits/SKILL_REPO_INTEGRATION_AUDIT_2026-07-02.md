# Skill / Repo Integration Audit

## Scope

This audit checks how the installed Codex skill
`~/.codex/skills/symbolic-simplification-loop` should integrate with the
updated `symbolic-simplification-loop` repository.

The audit uses the skill's own invariants:

- exact validation before claims;
- review and review-debt gates before freeze;
- no checkpoint overwrite;
- caveat preservation;
- no unapproved tensorial IBP, total-derivative promotion, Stage 013, or 012C
  promotion.

## Verification Run

```text
python3 -m compileall loop_engine scripts tests
PASS
```

```text
python3 -m pytest -q
1 failed, 243 passed, 1 warning
```

Failing test:

```text
tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008
```

The failure is reproducible in isolation.

## Findings

### 1. Skill and repo overlap but are not yet source-of-truth aligned

The installed skill is concise and suitable as an agent-facing workflow entry.
The repo now contains a richer engine with completion matrices, human signoff,
identity traceability, provider pools, pre-run gates, and repo hygiene reports.

Recommendation:

- Treat the installed skill as the compact agent entry point.
- Treat repo docs as detailed references.
- Add links from the skill to repo docs once the repo is installed or invoked
  from this project.
- Keep the skill small; do not copy all Loop 013--022 details into SKILL.md.

### 2. Repo has an older `skill/` directory that conflicts with the installed skill

The repo-local `skill/` directory still says reviewer JSON should be saved under
`.loop/reviews/`, while the README says the canonical directory is
`.loop/reviewer_results/`.

Recommendation:

- Migrate or rename repo-local `skill/` to `templates/roles/` or
  `docs/devlog/legacy_skill/`.
- If the repo-local skill remains public, update it to match
  `.loop/reviewer_results/`.
- Use `~/.codex/skills/symbolic-simplification-loop` as the actual Codex skill.

### 3. Safe-prefusion report generation has a project-name bug

`scripts/run_autonomous_loop.py` overwrites the `project` parameter with
`run_root.parent.name`.

For `run_root = autonomous_runs/sigma_abc`, this makes:

```text
project -> autonomous_runs
```

Therefore:

```python
if project == "sigma_abc" and profile_name == "sigma_abc_safe_pre_fusion":
```

does not trigger, and `SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md` is not written.

This breaks the test that expects the profile-specific report.

Recommended patch:

- keep the function parameter as `project_name`;
- use `run_root.name` if deriving the project name from path;
- call `write_sigma_abc_safe_prefusion_report(...)` based on the original
  project/profile, not `run_root.parent.name`.

### 4. Freeze manifest is written before freeze preconditions finish

`loop_engine/checkpoint.py::freeze_checkpoint` calls
`build_checkpoint_manifest(stage)` before `freeze_preconditions(...)`.

`build_checkpoint_manifest` writes `.loop/checkpoint_manifest.json` even if
`freeze_preconditions` later fails, for example when
`.loop/human_signoff.yaml` is missing.

This can leave a stage with:

```text
.loop/checkpoint_manifest.json exists
human_signoff.yaml missing
freeze raised RuntimeError
```

That violates the skill rule that `checkpoint_manifest.json` should exist only
when freeze is allowed.

Recommended patch:

- split manifest construction from manifest writing;
- run freeze preconditions before writing `.loop/checkpoint_manifest.json`;
- or delete the manifest on freeze-precondition failure.

### 5. Tests and manual runs mutate the same `autonomous_runs/sigma_abc` root

The failing test uses:

```text
--project sigma_abc --profile sigma_abc_safe_pre_fusion --from-current-checkpoint --clean
```

This deletes/rebuilds the same run root used for live scientific state. During
this audit the active run root was changed by test commands.

Recommendation:

- tests should use a temporary run root, unique project name, or environment
  override;
- live case-study runs should not share mutable state with pytest;
- the skill should warn users that `--clean` is destructive and should not be
  used on a live run root unless starting over intentionally.

### 6. Dry-run identity guard is too strict for multi-stage previews

The dry-run report for `sigma_abc_safe_pre_fusion` compares:

```text
ExpectedStage -> stop_after_stage
ActualStage -> first next stage
```

This marks multi-stage dry-runs as `ReportIdentityCheck -> FAIL` even when the
allowed stage list is correct.

Recommended patch:

- for dry-run, compare `ExpectedStage` against the last selected stage, or
  introduce:

```text
ActualFirstStage
ActualLastStage
SelectedStageCount
```

and check that the last selected stage equals the stop-after stage.

## Skill Integration Plan

### Near-term

1. Patch safe-prefusion report generation.
2. Patch checkpoint manifest write ordering.
3. Isolate pytest run roots from live `autonomous_runs/sigma_abc`.
4. Update repo-local `skill/` references to `.loop/reviewer_results/`.
5. Add a README line telling users to invoke the installed skill:

   ```text
   Use $symbolic-simplification-loop before running staged symbolic workflows.
   ```

### Skill update after repo patches

After the repo stabilizes, update the installed skill references to mention:

- completion matrix;
- human signoff;
- identity traceability;
- provider pool runtime check;
- `--clean` destructive warning;
- repo-local docs paths.

Keep the installed skill compact; push details into references.

## Current State Caveat

Because the audit ran pytest and isolated runner checks, the current
`autonomous_runs/sigma_abc` tree should not be treated as the authoritative
scientific checkpoint state without restoration from a known checkpoint or a
fresh intended runner invocation.

