# Loop 013 Completion-Matrix Status Hotfix

## Status

PASS.

Hotfix applied to `_status_from_gate()` mapping in `loop_engine/completion_matrix.py` and the corresponding `items.status` enum in `schemas/completion_matrix.schema.json`. Freeze remains hard-locked behind `human_signoff.yaml` and explicit human approval. No sigma_abc physics was modified. Stage 012C promotion, Stage 013 global pre-IBP assembly, tensorial IBP, and total-derivative reduction were not started.

## Files Changed

```text
loop_engine/completion_matrix.py        # _status_from_gate uses literal mapping table
schemas/completion_matrix.schema.json    # items.status enum adds DONE_WITH_CAVEAT
tests/test_loop013_human_signoff_completion_matrix.py  # +6 hotfix tests
LOOP_013_COMPLETION_MATRIX_STATUS_HOTFIX_REPORT.md     # this report
```

`loop_engine/state.py::freeze_preconditions`, `loop_engine/decision.py`, profile YAML files, and sigma_abc physics directories are NOT modified.

## Mapping Table (before / after)

| Gate string              | Before hotfix     | After hotfix        | Blocking |
| ---                      | ---               | ---                 | ---      |
| `PASS`                   | `DONE`            | `DONE`              | no       |
| `PASS_WITH_CAVEAT`       | `MISSING` (fallback) | `DONE_WITH_CAVEAT` | no       |
| `REGISTERED`             | `REGISTERED`      | `REGISTERED`        | no       |
| `REGISTERED_NOT_RUN`     | `MISSING` (fallback) | `REGISTERED`      | no       |
| `INHERITED_PASS`         | `MISSING` (fallback) | `REGISTERED`      | no       |
| `INHERITED`              | `MISSING` (fallback) | `REGISTERED`      | no       |
| `FAIL`                   | `FAILED`          | `FAILED`            | yes      |
| `MISSING`                | `MISSING`         | `MISSING`           | yes      |
| `BLOCKED`                | `BLOCKED`         | `BLOCKED`           | yes      |
| Unknown (any future value) | `MISSING`       | `MISSING` (safe fallback) | yes |

`REGISTERED` and `DONE_WITH_CAVEAT` are non-blocking by design. The unknown-gate fallback is `MISSING` (blocking), preventing silently OK'ing future gate values.

## New Schema Entry

`schemas/completion_matrix.schema.json::items.items.properties.status.enum` was extended from

```json
["DONE", "REGISTERED", "MISSING", "FAILED", "BLOCKED"]
```

to

```json
["DONE", "DONE_WITH_CAVEAT", "REGISTERED", "MISSING", "FAILED", "BLOCKED"]
```

`overall_completion` enum is intentionally NOT extended (still `COMPLETE / INCOMPLETE / BLOCKED / FAILED`). Caveats are surfaced at item level and at the `recommended_human_action` layer, not at the aggregate level — keeping the aggregate stable for downstream consumers.

## Blocking Logic Verification (unchanged code, new semantics automatic)

### Call site A — `validation.checks` items (lines 156-169)

```python
"blocking": status in {"MISSING", "FAILED", "BLOCKED"} and status != "REGISTERED",
```

- `DONE_WITH_CAVEAT` NOT in the left set → `blocking = False` ✓
- `REGISTERED` NOT in the left set → `blocking = False` ✓
- `FAILED`, `MISSING`, `BLOCKED` → `blocking = True` ✓

### Call site B — `protected_regressions` items (lines 171-184)

```python
"blocking": status in {"FAILED", "MISSING", "BLOCKED"},
```

- `REGISTERED` (now reachable from `REGISTERED_NOT_RUN`, `INHERITED_PASS`, `INHERITED`, plain `REGISTERED`) → `blocking = False` ✓
- All `FAILED`, `MISSING`, `BLOCKED` → `blocking = True` ✓

No code edits required at the call sites.

## Test Additions

Six new tests added to `tests/test_loop013_human_signoff_completion_matrix.py`:

1. `test_status_from_gate_literal_mapping` — Unit-style test on `_status_from_gate` covering all 9 mapped values + lowercase normalization + safe fallback for unknown gates.
2. `test_completion_matrix_schema_accepts_done_with_caveat_status` — Schema accepts an item with `status: DONE_WITH_CAVEAT`.
3. `test_protected_regression_registered_not_run_is_non_blocking` — `sigma_xxx_projection` with `gate: REGISTERED_NOT_RUN` becomes `status=REGISTERED`, `blocking=False`.
4. `test_dcprojection_to_1d_inherited_pass_is_non_blocking` — `DCProjectionTo1D` with `gate: INHERITED_PASS` becomes `status=REGISTERED`, `blocking=False`.
5. `test_registered_gates_do_not_count_as_blocking_incomplete` — Four protected regressions with `REGISTERED` / `INHERITED_PASS` / `REGISTERED_NOT_RUN` / `INHERITED` produce zero blocking-incomplete items and overall `COMPLETE`.
6. `test_012c_like_stage_with_registered_protected_regressions_still_incomplete` — 012C-like stage with `ready=False` (Stage012A/012B dependency items FAILED) AND injected registered protected regressions: overall `FAILED`, recommended action `DO_NOT_FREEZE_PATCH`, blocking items restricted to dependency/readiness failures (no registered items in the blocking list), boundary audit remains safe.

## Recommended-Action Policy — UNCHANGED

`_build_recommended_action` is not modified. `APPROVE_FREEZE_WITH_CAVEAT` continues to be triggered when validation gate is `PASS` AND review verdict is in `{PASS, PASS_WITH_CAVEAT}` AND caveats list is non-empty. The new `DONE_WITH_CAVEAT` is an item-level state and does not feed this path — review verdict remains the source of truth for caveat-driven recommendations.

## Freeze Is Still Hard-Locked

`loop_engine/state.py::freeze_preconditions` is unchanged. Freeze still requires:

- `validation_summary.overall_gate == "PASS"`
- `review.verdict ∈ {PASS, PASS_WITH_CAVEAT}`
- `CLAIM_BOUNDARY.md` exists
- `reports/completion_matrix.json` exists AND fresh AND boundary audit safe AND no blocking incomplete items
- `.loop/human_signoff.yaml` exists AND fresh AND `decision ∈ {APPROVE_FREEZE, APPROVE_FREEZE_WITH_CAVEAT}` AND `permission.freeze_checkpoint=true` AND three `human_scientific_judgment` flags true AND (`decision == APPROVE_FREEZE_WITH_CAVEAT` ⇒ `accepted_caveats` non-empty)

`DONE_WITH_CAVEAT` does not loosen any precondition.

## Fix 2 / Fix 3 — Skipped Per User Instruction

**Fix 2 (012C live signoff)**: skipped. The active stage changed during the planning cycle (`sigma_abc_012c_real_loop_candidate_preparation` ↔ `sigma_abc_006_tensorial_sector_architecture_review`). Per user clarification ("修复代码 + 跳过 012c 现场签字"), this hotfix does not write a live `human_signoff.yaml` for either stage. Signoff for the active stage is deferred to a future Loop.

**Fix 3 (recommended-action policy)**: no change. `_build_recommended_action` retains `APPROVE_FREEZE_WITH_CAVEAT` as the recommended action when validation/review pass and caveats exist. `freeze_preconditions` still requires explicit `human_signoff` with `accepted_caveats` for `APPROVE_FREEZE_WITH_CAVEAT`. No loosening.

## Verification

```text
python3 -m pytest -q tests/test_loop013_human_signoff_completion_matrix.py
-> 16 passed, 1 warning
```

Targeted Loop 013 file passes 16 tests (10 pre-existing + 6 hotfix). The full file now reads 16 not 10.

```text
python3 -m pytest -q
-> 157 passed, 2 failed, 1 warning
```

```text
python3 -m compileall loop_engine scripts tests
-> PASS (EXIT=0)
```

The two failures in the full suite are pre-existing and unrelated to this hotfix:

- `tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`
- `tests/test_sigma_abc_loop_candidate_preparation.py::test_loop_candidate_preparation_blocks_when_stage012_inputs_are_absent`

Verified by temporarily reverting this hotfix and observing both tests still fail with identical messages (`overall_gate = BLOCKED` vs expected `FAIL`, and `run_autonomous_loop.py` exit status 1). Root cause is upstream of `_status_from_gate` (production pipeline producing `BLOCKED` gates in `validation_summary.json` instead of `FAIL`), not a mapping issue.

## Sigma_abc Boundary Check

```text
sigma_abc/stages/sigma_abc_012c_loop_orbit_canonicalization_promotion -> not generated
sigma_abc/stages/sigma_abc_013_global_pre_ibp_assembly                 -> not generated
sigma_abc/stages/sigma_abc_tensorial_ibp_reduction                     -> not generated
autonomous_runs/sigma_abc/stages/sigma_abc_012c_loop_orbit_canonicalization_promotion -> not generated
autonomous_runs/sigma_abc/stages/sigma_abc_013_global_pre_ibp_assembly                 -> not generated
```

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

No sigma_abc physics files were touched. No new stage directories were created. No IBP, no total-derivative, no tensorial promotion artifact was generated.

## Future Work

- Fix the pre-existing 2 test failures (root cause: `_build_recommended_action` semantics vs. `validation_summary.json::overall_gate = BLOCKED` in `sigma_abc_safe_pre_fusion` profile). Out of scope for this hotfix.
- Consider extending `recommended_human_action` enum with `INVESTIGATE_BOUNDARY` if Loop 014 wants finer-grained boundary failure handling.
- Re-evaluate live signoff policy when the active sigma_abc stage stabilizes (was `012c_real_loop_candidate_preparation`, briefly `006_tensorial_sector_architecture_review`, currently `012c_real_loop_candidate_preparation` again).