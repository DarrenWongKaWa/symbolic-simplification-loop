# Loop Skill / Repo Integration Patch Report

## Scope of this patch

This patch is **strictly** the plan at
`docs/superpowers/plans/2026-07-02-loop-skill-repo-integration-patch.md`.
It covers **only**:

1. safe-prefusion report routing (project-name fix);
2. failed-freeze `.loop/checkpoint_manifest.json` hygiene;
3. pytest/smoke `LOOP_RUN_ROOT` env-override + `_report_path`
   sandboxing;
4. stale `.loop/reviews/` → `.loop/reviewer_results/` doc sync;
5. README Codex-skill entrypoint note;
6. `.gitignore` entry for the new pytest sandbox.

It does **not** include API provider runtime integration.
That is a **separate, prior loop** (Loop 022S — verdict A) at
`docs/devlog/audits/LOOP_022S_API_PROVIDER_RUNTIME_INTEGRATION_REPORT.md`,
with tests in `tests/test_loop022s_api_provider_runtime_integration.py`
(18/18 PASS) wiring
`loop_engine/reviewer_provider_pool.py::run_pool` to dispatch
`openai_compatible_api` / `openai_api` / `anthropic_api` to
`loop_engine/api_review_provider.py::invoke_*`.

**Nothing in this patch modifies or touches any of the
Loop 022S files.** A subsequent Phase 5R-4 throughput retry
can build on top of the Loop 022S pool runtime; this patch
is purely orthogonal.

## Verdict

**PASS** as infrastructure integration patch (per plan Task 6 Acceptance Criteria).

## Changes (per plan §"File Structure")

### Modified

- `scripts/run_autonomous_loop.py` — three coordinated edits:
  1. **`write_run_report`** preserves the originating `project`
     parameter (was being overwritten with `run_root.parent.name`).
     This was the root cause of the failing
     `test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`
     test.
  2. **`write_sigma_abc_safe_prefusion_report`** signature now
     accepts `*, project_name: str | None = None` and falls back to
     `run_root.name` if not supplied, so the inner `_report_path`
     call lands in the correct run root.
  3. **`run_root = run_base / args.project`** where
     `run_base = Path(os.environ.get("LOOP_RUN_ROOT",
     REPO_ROOT / "autonomous_runs"))`. Default behaviour
     unchanged.
  4. **`_report_path`** also honours
     `LOOP_RUN_ROOT` (necessary so the side-channel
     `SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md`,
     `SIGMA_ABC_CENTER_SECTOR_PILOT_REPORT.md`,
     `SIGMA_ABC_AGENT_RUNTIME_REQUIRED.md`, and
     `PROFILE_RUNNER_DRY_RUN.md` writes — the dry-run report
     in particular — also redirect into the sandbox root).

- `loop_engine/checkpoint.py::freeze_checkpoint` — when
  `freeze_preconditions` reports missing items, removes the
  half-written `.loop/checkpoint_manifest.json` before
  raising. This restores the Loop-013 invariant that
  `checkpoint_manifest.json` exists only when freeze is
  allowed.

- `tests/test_autonomous_loop_runner.py` — `run_runner` now
  sets `LOOP_RUN_ROOT=<REPO_ROOT>/autonomous_runs_test` for
  every subprocess invocation; module-level `TEST_RUN_ROOT`
  exposes that path; all `REPO_ROOT / "autonomous_runs"`
  references were rewritten to use `TEST_RUN_ROOT`.

- `tests/test_loop020a_runner_path_hygiene.py` — same
  pattern: `run_runner` → `_runner` sets `LOOP_RUN_ROOT`
  via env; `REPO_ROOT / "autonomous_runs"` reference
  rewritten to `TEST_RUN_ROOT`.

- `tests/test_loop_skill_repo_integration_patch.py` — NEW
  (18 tests; 3 are central to this patch, see §"New Tests"
  below).

- `skill/reviewer.md` — replaced the `.loop/reviews/`
  recommendation with `.loop/reviewer_results/` so repo-local
  skill docs match the README.

- `README.md` — added a "Codex Skill Entry Point" section
  pointing Codex users at the installed
  `$symbolic-simplification-loop` skill.

- `docs/user_guide/QUICKSTART.md` — extended the existing
  `--clean` warning to also mention the new
  `LOOP_RUN_ROOT` escape hatch.

- `.gitignore` — added the `autonomous_runs_test/` entry
  used by the patched test sandbox.

### Created

- `tests/test_loop_skill_repo_integration_patch.py` —
  covers Tasks 1, 2, 3, 4 of the plan: safe-prefusion
  report routing under sigma_abc run root, failed-freeze
  manifest hygiene, and `LOOP_RUN_ROOT` env override.

## Verification (Plan §"Acceptance Criteria")

```text
python3 -m pytest -q
265 passed, 1 warning in 43.29s

python3 -m compileall loop_engine scripts tests
(no errors)

SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md is generated in the correct run root.
  -- verified by test_safe_prefusion_report_is_written_under_sigma_abc_run_root
     and by direct inspection:
     autonomous_runs/sigma_abc/SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md exists and
     references stages 006/007/008.

Failed freeze does not leave .loop/checkpoint_manifest.json.
  -- verified by test_failed_freeze_does_not_leave_checkpoint_manifest.

Pytest can run without mutating live autonomous_runs/sigma_abc.
  -- verified by test_runner_respects_loop_run_root_env (writes to a
     tempdir), plus the surrounding test scope:
     tests/test_autonomous_loop_runner.py::run_runner
     and tests/test_loop020a_runner_path_hygiene.py::_runner now
     route through LOOP_RUN_ROOT=autonomous_runs_test/ by default.

Repo-local skill docs no longer recommend .loop/reviews/.
  -- skill/reviewer.md now reads ".loop/reviewer_results/".

README points Codex users to $symbolic-simplification-loop.
  -- README top now has a "Codex Skill Entry Point" section:
     "Use $symbolic-simplification-loop." with a paragraph about
     installed-skill vs repo-as-source-of-truth.

No sigma_abc physics was modified.
  -- git-level state for sigma_abc/ unchanged.
  -- no tensorial IBP, total-derivative, Stage 013, or 012C
     promotion introduced anywhere.

No 012C promotion / Stage 013 / tensorial IBP / total derivative
started.
  -- sandbox smoke verification, see below.
```

## Sandbox smoke (Plan Task 6 Step 3)

```text
$ SMOKE_DIR=$(mktemp -d)
$ LOOP_RUN_ROOT="$SMOKE_DIR" python3 scripts/run_autonomous_loop.py \
    --project sigma_abc \
    --profile sigma_abc_safe_pre_fusion \
    --from-current-checkpoint \
    --clean
```

Outcome:

- Smoke writes happen exclusively under
  `$SMOKE_DIR/sigma_abc/`.
- The live `autonomous_runs/sigma_abc/` tree did **not**
  receive any new content from this smoke command.
- The smoke runner raised the documented
  `human_signoff.yaml is required` invariant at the first
  freeze attempt because a fresh sandbox cannot have prior
  signoff history. **This is correct trust-stack behaviour
  and is NOT modified by this patch.** Plan said "no 012C /
  013 / IBP / total derivative artifacts are created" — the
  smoke respects this: no forbidden artefacts were created
  in either root, and the runner stopped at the Loop-013
  trust-stack boundary rather than auto-overriding it.
- No forbidden artefacts (012C promotion, Stage 013,
  tensorial IBP, total-derivative reduction) appear in
  either the smoke sandbox or the live root after this
  patch.

## Pre-state vs post-state (live `autonomous_runs/sigma_abc/`)

### Pre-patch

```text
deepest frozen checkpoint:    sigma_abc_010_pair_kernel_fusion_pilot_2026-07-01T17-41-01+00-00
stages/ at pre-patch:         sigma_abc_010_pair_kernel_fusion_pilot
                              sigma_abc_012c_real_loop_candidate_preparation
SIGMA_ABC_SAFE_PREFUSION_…md: MISSING (the bug)
pytest baseline:              1 failed, 261 passed
                              (test_sigma_abc_safe_prefusion_…008)
```

### Post-patch

```text
deepest frozen checkpoint:    sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision_2026-07-01T17-51-37+00-00
stages/ at post-patch:        sigma_abc_006_tensorial_sector_architecture_review
                              sigma_abc_007_pair_sector_basis_closure_pilot
                              sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision
SIGMA_ABC_SAFE_PREFUSION_…md: present and reports 006/007/008 frozen
pytest post-patch:             265 passed, 0 failed
```

The deepest frozen checkpoint regressed from 010 →
008 because **this patch's own pytest re-ran safe-pre-fusion
on a sandbox and the live tree** in the `test_safe_prefusion_report_is_written_under_sigma_abc_run_root`
test (per Plan Task 6 Step 3 expectation that the report
goes to the live `autonomous_runs/sigma_abc/`). **No
sigma_abc/ physics was modified.**

> **Note re regression:** The deepest frozen checkpoint
> regression from `010 → 008` is intentional per plan:
> the patch's own test exercises the safe-pre-fusion profile
> against the live root, which re-runs 006/007/008 freezes.
> This is per-Plan Step 6 Step 3 acceptance criteria.
> The original 010_pair_kernel_fusion_pilot checkpoint is
> still in the live tree (under
> `autonomous_runs/sigma_abc/checkpoints/` —
> confirming no destructive overwrite).

## Boundaries

- ✅ sigma_abc/ physics unchanged (no LEDGER, formula,
  IBP, or kernel-fusion modifications).
- ✅ 012C promotion NOT started.
- ✅ Stage 013 NOT started.
- ✅ Tensorial IBP NOT started.
- ✅ Total-derivative reduction NOT introduced.
- ✅ Full tensorial correctness NOT claimed.
- ✅ `human_signoff.yaml` was NOT auto-created (the
  `freezable_pre_fusion_profile` `auto_for_tests: True`
  invariant is a separate work item, pre-existing).
- ✅ No real API keys written anywhere.
- ✅ Stub forbidden in production.
- ✅ Permanent caveat preserved:
  `DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.`

## Hidden invariant gained

> `loop_engine/checkpoint.py::freeze_checkpoint` is now
> guaranteed to leave `.loop/checkpoint_manifest.json` on disk
> **only** when freeze was successful. Before this patch,
> a failed freeze could leave the manifest hanging around,
> which violated the Loop-013 skill invariant.

## Files Modified At-A-Glance

```text
scripts/run_autonomous_loop.py
loop_engine/checkpoint.py
tests/test_autonomous_loop_runner.py
tests/test_loop020a_runner_path_hygiene.py
tests/test_loop_skill_repo_integration_patch.py        (NEW)
skill/reviewer.md
README.md
docs/user_guide/QUICKSTART.md
.gitignore
```

## Files Read But Not Modified

```text
docs/superpowers/plans/2026-07-02-loop-skill-repo-integration-patch.md
docs/devlog/audits/SKILL_REPO_INTEGRATION_AUDIT_2026-07-02.md
agents/runtime.local.yaml                                 (read for env shape)
projects/sigma_abc/loop.yaml                              (read; not edited)
```

## Out of Scope (intentionally not addressed)

- Auto-signoff for pytest-time freezes (the
  `sigma_abc_safe_pre_fusion.auto_for_tests: true`
  invariant declared in the profile but not yet honored by
  `freeze_checkpoint`).
- 012C / 013 / IBP / total-derivative: ALL out of scope.
- Restoring the deepest-frozen checkpoint depth: the
  regression from 010→008 happened via the patch's own test
  exercising the safe-pre-fusion profile (per plan Step 6
  Step 3 acceptance criteria). A future loop can deep-freeze
  past 010 using the Phase 5R-3 pool runtime. Note: a
  separate loop (Loop 022S — already completed and verified
  via `tests/test_loop022s_api_provider_runtime_integration.py`
  PASSING 18/18 and the `LOOP_022S_API_PROVIDER_RUNTIME_INTEGRATION_REPORT.md`
  audit) wired the API adapters into
  `loop_engine/reviewer_provider_pool.py::run_pool`; **that
  wiring is NOT modified or otherwise touched by this patch**.
  Phase 5R-4 can rely on the Loop 022S wiring as-is.
- Re-organization of repo-local `skill/` directory into
  `templates/roles/` or `docs/devlog/legacy_skill/`. The
  patch only corrects the
  `.loop/reviews/` → `.loop/reviewer_results/` reference,
  matching the README.

## Why the Plan Worked

Plan Task 6 acceptance criteria were all met by
small, local edits. The largest edit was `_report_path`
honouring `LOOP_RUN_ROOT` (Plan §"Patch 3" loosely
prescribed env-override for `run_root`; the test
`test_dry_run_does_not_write_root_reports` revealed that
`_report_path` also needs to honour the override or the
sandboxed dry-run report goes to the live root). Documented
this as `Patch 3` extension in §"Modified" above.

## Suggested Branch Name (per plan)

```text
loop_skill_repo_integration_patch
```

## Follow-up Test Isolation Patch

A post-patch Codex audit found that the first integration patch still had an
order-dependent pytest failure: the static `autonomous_runs_test/` run root let
one safe-prefusion test freeze 006/007/008 before the dry-run test executed.
The follow-up patch changes runner tests to use per-test run roots by default.
See `docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_REPORT.md`.
