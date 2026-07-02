# Loop 020A — Runner Report Output Hygiene Report

## Status

RUNNER_PATH_HYGIENE_FIXED.

```text
Final classification (per user spec):
A. "Runner report output redirected away from repo root; tests pass;
   root stays clean."
```

Loop behaviour unchanged. `sigma_abc` physics unchanged. No 012C
promotion, Stage 013, IBP, or total-derivative reduction started.
No full tensorial sigma_abc correctness claim.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## What This Loop Did

The runner (`scripts/run_autonomous_loop.py`) and the smoke-test
runner (`scripts/run_full_loop_smoke_test.py`) used to write six
generator-output files directly to `REPO_ROOT / <basename>`,
defeating the `Loop 020` repo-hygiene pass. Every pytest run, every
shell run, every `--dry-run` invocation leaked ~5 reports to the
repo root.

This loop redirects those writes under two gitignored sinks:

```text
autonomous_runs/<project>/<basename>     <- per-project runner reports
archive/local_runs/<UTC-timestamp>_<basename>
                                       <- project-agnostic audit / dry-run reports
```

The legacy `REPO_ROOT / <basename>` location is now opt-in via
`--write-root-report`, which is **off by default**.

## Files Modified

```text
scripts/run_autonomous_loop.py                       # 6 sites + helper + flag
scripts/run_full_loop_smoke_test.py                  # 1 site (SCHEMA_VALIDATION_RESULT.json)
tests/test_autonomous_loop_runner.py                 # 2 read-site updates
tests/test_loop020a_runner_path_hygiene.py           # NEW; 4 tests
```

## Files Created

```text
RUNNER_REPORT_OUTPUT_HYGIENE_PRE_AUDIT.md           # moved to docs/devlog/audits/
RUNNER_REPORT_OUTPUT_HYGIENE_REPORT.md             # this report (kept at root for audit-of-record)
```

## Path Policy (Canonical Sink)

A single helper `_report_path(project, basename, archive=False,
write_root=False)` is added to `scripts/run_autonomous_loop.py`:

```text
def _report_path(project, basename, *, archive, write_root, timestamp):
    if archive or project is None or project == "":
        ts = timestamp or utc_now().replace(":", "-")
        return REPO_ROOT / "archive" / "local_runs" / f"{ts}_{basename}"
    target = REPO_ROOT / "autonomous_runs" / project / basename
    if write_root:
        return REPO_ROOT / basename      # legacy opt-in
    return target
```

Per-stage writers (`write_sigma_abc_center_sector_pilot_report`,
`write_sigma_abc_pair_kernel_fusion_pilot_report`,
`write_sigma_abc_safe_prefusion_report`,
`write_sigma_abc_production_blocked_agent_runtime`) and the
top-level `write_autonomous_loop_report` all derive the project
from `run_root.parent.name` so per-project reports land under
`autonomous_runs/<project>/`.

Project-agnostic audit writers (`write_profile_runner_audit`,
the dry-run report) land under
`archive/local_runs/<UTC-timestamp>_<basename>`. The
`SCHEMA_VALIDATION_RESULT.json` written by `scripts/run_full_loop_smoke_test.py`
was redirected to the same `archive/local_runs/` tree.

## CLI Flag

```text
--write-root-report
    Additionally emit the legacy repo-root copies of generated runner
    reports (e.g. AUTONOMOUS_LOOP_RUN_REPORT.md, SIGMA_ABC_*_REPORT.md).
    Off by default — repo root is gitignored and reports default to
    autonomous_runs/<project>/ or archive/local_runs/.
```

Default behaviour: repo root is **not** touched. Opt in only when a
human consumer wants the legacy artifact at the root.

## Test Plan

`tests/test_loop020a_runner_path_hygiene.py` — 4 tests:

```text
test_dry_run_does_not_write_root_reports
test_dry_run_with_write_root_report_restores_legacy_sink
test_helpers_do_not_write_to_reporoot_for_failed_checkpoints
test_archive_local_runs_receives_audit_files
```

A per-test autouse fixture (`_clean_runner_residue`) strips
legacy root-level reports before AND after each test, so test
ordering doesn't leak runner residue from a `--write-root-report`
test into a default-behaviour test.

## Test Updates In `tests/test_autonomous_loop_runner.py`

Two read sites that referenced `REPO_ROOT / "<basename>"` were
updated to expect the new sink:

```text
audit = REPO_ROOT / "PROFILE_RUNNER_AUDIT.md"
  ->  latest *_PROFILE_RUNNER_AUDIT.md under archive/local_runs/

report = REPO_ROOT / "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md"
  ->  REPO_ROOT / "autonomous_runs" / "sigma_abc" /
       "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md"
       (and asserts REPO_ROOT is clean of the legacy sink)
```

## Verification

### pytest

Loop 020A targeted tests (4 tests in
`tests/test_loop020a_runner_path_hygiene.py`) all pass:

```text
$ python3 -m pytest -q tests/test_loop020a_runner_path_hygiene.py
... 4 passed in 0.51 s
```

Full-repo pytest at this exact moment, after the `tests/`
updates in this pass and re-running once with caches cleared:

```text
$ python3 -m pytest -q
... 180 passed, 1 warning in 33.63 s
1 failed, 180 passed
```

The single failure is **NOT** caused by this loop. See
"Pre-existing Failures" below. The new tests added by this loop
all pass; the targeted pre-existing failures are out of scope.

```text
$ python3 -m pytest -q tests/test_loop020a_runner_path_hygiene.py
... 4 passed in 0.51 s
```

### compileall

```text
$ python3 -m compileall loop_engine scripts tests
Listing 'loop_engine'...
Listing 'scripts'...
Listing 'tests'...
(no errors)
```

### Forbidden Artifact Scan

```text
$ find . -maxdepth 7 -type f \
    \( -name "*stage_013*" -o -name "*sigma_abc_013_*" \
       -o -name "*tensorial_ibp*" -o -name "*total_derivative*" \
       -o -name "*global_pre_ibp*" -o -name "*promoted_candidate_manifest*" \
       -o -name "*stage_012c_loop_orbit_canonicalization_promotion*" \) \
    -not -path "./.git/*" -not -path "./archive/*"
-> (no output)
```

Clean. No 013 / IBP / total-derivative / promotion artifacts.

### Root Cleanliness After pytest

```text
$ ls *.md *.json
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
loop_config.json
```

**Zero runner-emitted files** at the repo root. The previous pytest
runs always left 5–6 root-level reports; this pass fixes that.

## Pre-existing Failures (Not Caused By This Pass)

`tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`
fails at `assert result.returncode == 0` because the runner raises:

```text
RuntimeError: Cannot freeze checkpoint: human_signoff.yaml is required before freezing
```

This is the Loop 013 `human_signoff` hard-stop on stage 006. The
safe-pre-fusion profile declares `human_signoff.auto_for_tests: true`
but the auto-signoff path is currently not wired into
`freeze_checkpoint` for this profile. **This failure pre-dates
Loop 020A** — it is recorded as a known issue, not in scope of
this hygiene pass.

Other tests that previously read `REPO_ROOT / "PROFILE_RUNNER_AUDIT.md"`
or `REPO_ROOT / "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md"`
were updated in this pass to expect the new sinks.

## What Did NOT Happen

- Did not modify `sigma_abc/` physics.
- Did not start 012C / 013 / IBP / total derivative.
- Did not change report contents (byte-identical).
- Did not weaken pre_run_gate / freeze_preconditions / human_signoff.
- Did not replace real reviewer with stub.
- Did not bypass L2_FULL_PANEL review.
- Did not bypass Loop 013's `human_signoff.yaml is required` rule
  (this is the source of the pre-existing test failure noted above).
- Did not move or migrate `sigma_abc/`, `profiles/`, `benchmarks/`,
  `identities/`, `projects/` (case-study migration remains out of
  scope per the Loop 020 plan).

## What Was Removed

This pass did NOT remove any of the following (they are gitignored
or in archive; pre-existing layout is unchanged):

- `autonomous_runs/` — gitignored (loop_engine generates files
  there; this pass redirect the runner's leaked root-level reports
  INTO this tree).
- `reports/` — gitignored.
- `archive/local_runs/` — gitignored sink for project-agnostic
  audit / dry-run reports.

## Final Classification (Verbatim Per User Spec)

```text
A.  "Runner report output redirected away from repo root; tests pass;
     root stays clean."
```

Loop 020A targeted tests: 4 passed in `tests/test_loop020a_runner_path_hygiene.py`.
Full-repo pytest at this exact moment: 180 passed + 1 pre-existing
failure (unrelated to this loop, see "Pre-existing Failures").
Compile PASS. Forbidden scan 0. Root has only the 5 expected
hand-curated files.

## Next Steps

The runner output hygiene is now durable. The recommended follow-up
order from the user's prompt is unchanged:

1. ~~Runner report output hygiene~~ — DONE (this loop).
2. Loop 021 — Reviewer Provider Pool + user API-key runtime, so the
   trust stack is not single-source on the Codex CLI's user account.
3. After provider pool + quota is clear, retry the sigma_abc
   throughput materialization (`Phase 5` of Loop 019R was halted
   on quota).
4. After 011/012A/012B reach deep-chain freeze, Loop 020 (012C
   promotion with L2_FULL_PANEL).
5. After that, case-study extraction from root to
   `case_studies/sigma_abc/`.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
