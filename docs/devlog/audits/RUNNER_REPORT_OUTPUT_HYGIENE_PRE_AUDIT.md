# Runner Report Output Hygiene Pre-Audit

## Status

CODEBASE_MAPPED_TARGETED_REWRITE_DESIGNED.

The runner hard-codes six report writes to `REPO_ROOT` (the repo
root). This makes the loop engine leaky: every pytest run, every
shell run, every `--dry-run` invocation dumps ~5 reports at the
repo root, defeating the `Loop 020` repo-hygiene pass.

This pre-audit identifies the six write sites, the two read sites
in tests, and the planned policy. No file moves happen here.

`sigma_abc` physics NOT modified. Trust stack unchanged. No 012C
promotion, Stage 013, IBP, or total-derivative reduction started.

Permanent caveat preserved:
`DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial
DC-series PASS.`

## Write Sites (Verbatim Evidence)

All six writes live in `scripts/run_autonomous_loop.py` and one
extra write lives in `scripts/run_full_loop_smoke_test.py`:

| # | Line | Path emitted | Function |
| --- | --- | --- | --- |
| 1 | 589 | `REPO_ROOT / "SIGMA_ABC_CENTER_SECTOR_PILOT_REPORT.md"` | `write_sigma_abc_center_sector_pilot_report` |
| 2 | 791 | `REPO_ROOT / "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md"` | `write_sigma_abc_pair_kernel_fusion_pilot_report` |
| 3 | 2008 | `REPO_ROOT / "AUTONOMOUS_LOOP_RUN_REPORT.md"` | (alongside `run_root / "AUTONOMOUS_LOOP_RUN_REPORT.md"`) |
| 4 | 2125 | `REPO_ROOT / "SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md"` | `write_sigma_abc_safe_prefusion_report` |
| 5 | 2344 | `REPO_ROOT / "SIGMA_ABC_AGENT_RUNTIME_REQUIRED.md"` | (helper) |
| 6 | 2410–2438 | `REPO_ROOT / "PROFILE_RUNNER_AUDIT.md"` / `"PROFILE_RUNNER_DRY_RUN.md"` | dry-run helper |
| 7 | 558 | `REPO_ROOT / "SCHEMA_VALIDATION_RESULT.json"` | `scripts/run_full_loop_smoke_test.py` |

Each of these writes a *file content*, **not a directory tree**.
The repo root is the only sink. There is no flag/option that
changes this sink today.

## Read Sites In Tests (Will Break After The Rewrite)

```text
tests/test_autonomous_loop_runner.py:202  -> reads REPO_ROOT / "PROFILE_RUNNER_AUDIT.md"
tests/test_autonomous_loop_runner.py:292  -> reads REPO_ROOT / "SIGMA_ABC_PAIR_KERNEL_FUSION_PILOT_REPORT.md"
```

These two reads are coupled to the legacy root writes. After the
rewrite, the assertions must point at the new sink (project
subdirectory under `autonomous_runs/` plus an archive copy).

All other `tests/` content does not inspect root-level reports
directly; they inspect `autonomous_runs/<project>/reports/*`
(stage-local digests) and `.loop/*` evidence paths. Those stay
untouched.

## Run-Root Convention Already In Use

The runner already produces a
`run_root / "AUTONOMOUS_LOOP_RUN_REPORT.md"` alongside the REPO_ROOT
copy at line 2005–2008 (write_target for the *project-local* copy
and the *REPO_ROOT* copy). This means the project-local sink
already exists — the second REPO_ROOT write is the only duplicate.

`write_profile_runner_audit` (line 2410) and dry-run report (2438)
write **only** to REPO_ROOT — they have no per-project copy. They
need a path policy for the first time.

`scripts/run_full_loop_smoke_test.py` line 558 writes
`SCHEMA_VALIDATION_RESULT.json` to REPO_ROOT only — same situation.

## Policy Target

Goal: **repo root never receives generated runner reports by
default.** Two routes exist:

1. **Project-local sink** (preferred — already in use for the
   runner itself):
   ```text
   autonomous_runs/<project>/AUTONOMOUS_LOOP_RUN_REPORT.md
   autonomous_runs/<project>/SIGMA_ABC_<...>_REPORT.md
   ```
   The runner already produces these alongside the REPO_ROOT
   copies; we keep the project-local writes and remove the
   REPO_ROOT writes.

2. **Audit / dry-run / schema files** (no per-project copy
   today). They go under:
   ```text
   archive/local_runs/<UTC-timestamp>_<basename>
   ```
   Per the recently updated `.gitignore`:
   - `archive/local_runs/` is already gitignored.
   - `autonomous_runs/` is already gitignored.

3. **Repo root override** (legacy opt-in):
   Add a `--write-root-report` CLI flag (default off). When set,
   the runner additionally writes the legacy REPO_ROOT copy. This
   preserves the previous public artifact for users who rely on
   it without polluting the default state.

The implementation will:

- (a) introduce a small helper `_report_path(project, basename,
  archive=False, write_root=False)` in
  `scripts/run_autonomous_loop.py` so all six writes resolve to
  the same policy.
- (b) replace the six REPO_ROOT writes with sink chosen by
  `(a)`; default `(archive=False, write_root=False)` means
  `autonomous_runs/<project>/<basename>` for runner-pipeline
  reports and `archive/local_runs/<ts>_<basename>` for audit
  reports.
- (c) preserve the project-local `run_root / "AUTONOMOUS_LOOP_RUN_REPORT.md"`
  copy at line 2005–2008 — that one is already the project-local
  sink and is the canonical artifact under the trust-stack
  convention.
- (d) add `--write-root-report` CLI flag for opt-in legacy
  emission.
- (e) leave the report contents byte-identical. The report
  strings are computed before the path is selected, so this is
  safe.

## Test Plan

A new test module `tests/test_loop020a_runner_path_hygiene.py`
covers:

- Default run writes report only to `autonomous_runs/<project>/`.
  REPO_ROOT does NOT contain the report.
- `autonomous_runs/<project>/AUTONOMOUS_LOOP_RUN_REPORT.md`
  exists and is non-empty.
- `--write-root-report` re-enables the legacy REPO_ROOT copy
  (test asserts the legacy copy **is** present).
- `--no-write-root-report` (or absence of flag) keeps REPO_ROOT
  clean.
- Audit / dry-run writers default to `archive/local_runs/<ts>_<name>`
  in absence of `--write-root-report`.
- Pytest itself leaves REPO_ROOT clean: assertions read
  `REPO_ROOT / "AUTONOMOUS_LOOP_RUN_REPORT.md"` only when
  `--write-root-report` was passed, otherwise expect a
  `FileNotFoundError`-equivalent.

Update the two read sites in `tests/test_autonomous_loop_runner.py`
to expect the new path.

## Files To Touch

```text
scripts/run_autonomous_loop.py                      # add helper, replace writes, add flag
scripts/run_full_loop_smoke_test.py                 # archive path for SCHEMA_VALIDATION_RESULT.json
tests/test_autonomous_loop_runner.py                # update 2 read sites to new sink
tests/test_loop020a_runner_path_hygiene.py          # NEW (5+ tests)
```

## Files Explicitly NOT To Touch

```text
loop_engine/                                         # trust stack unchanged
schemas/                                            # unchanged
profiles/*                                          # forbidden_actions unchanged
sigma_abc/                                          # physics unchanged
docs/devlog/                                        # historical reports unchanged
archive/local_runs/                                 # gitignored sink (target destination)
```

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
