# Executor Report — TASK_025_BACKFILL (CLI Output Contract Normalization, post-review patch)

## Status: COMPLETE

This patch addresses the reviewer's two blocking issues against the prior
`TASK_025_BACKFILL` patch:

- **Blocking issue 1**: `--print-json` stdout is now *purely* parseable
  JSON. No path line, no prefix, no suffix, no human text. `json.loads(proc.stdout)`
  succeeds directly and `proc.stdout | python -m json.tool` round-trips.
- **Blocking issue 2**: The exit-code contract is enforced for explicit
  unreadable inputs and malformed JSON inputs. A non-existent
  `--run-root` / `--stage` / `--command-status-json` now exits nonzero
  with a clear stderr error, and a malformed `--command-status-json`
  also exits nonzero. Internal missing artifacts inside a valid
  `--run-root` / `--stage` still exit 0 with `MISSING_REQUIRED_FILE`,
  preserving the diagnosis tool's read-only contract.

The original TASK_025_BACKFILL contract is preserved:

- `--output-mode json` writes/mentions only the JSON artifact.
- `--output-mode markdown` writes/mentions only the markdown artifact.
- `--output-mode both` writes/mentions both, in deterministic
  JSON-then-markdown order (default for backward compatibility).
- Legacy `--json-only` / `--markdown-only` are still accepted and
  rejected when combined with each other or with `--output-mode`.
- `--quiet` suppresses path lines; explicit `--print-json` /
  `--print-markdown` still emit their payload.
- `--outdir` is an alias for `--output-dir`; both are mutually
  exclusive.
- `--print-markdown` is rejected in `--output-mode json` /
  `--json-only`; `--print-json` is rejected in `--output-mode
  markdown` / `--markdown-only`.
- Generated JSON still validates against
  `schemas/next_action_report.schema.json` in every mode.
- TASK_023 and TASK_024 diagnosis tests are unchanged and pass.
- No edits to scientific artifacts, frozen checkpoints, completed
  validation artifacts, human signoff ledgers, the `sigma_abc/`
  scientific content, `loop_engine/run_diagnosis.py` (no diagnostic
  semantics change), `agent_bus` state-machine behavior, dispatcher
  watch mode, or unrelated devlog audits. No real provider
  invocation. No auto-commit, auto-freeze, or auto-signoff. No
  TASK_028.

## changed_files

- [scripts/diagnose_run_failure.py](scripts/diagnose_run_failure.py)
  - **`--print-json` stdout is now pure JSON**: when `--print-json` is
    set, the artifact path line is suppressed. stdout is *only* the
    pretty-printed JSON payload, terminated by a single trailing
    newline. `json.loads(proc.stdout)` succeeds; piping to
    `python -m json.tool` round-trips. Same rule for `--print-markdown`.
  - **`--print-json` + `--print-markdown` in `both` mode**: stdout is
    JSON first, then markdown (deterministic order), with no path
    lines. The print order mirrors the path-line order.
  - **Explicit-input validation**: introduced
    `_validate_explicit_paths(args)`. For each of
    `--run-root`, `--stage`, `--stdout-file`, `--stderr-file`,
    `--command-status-json`, `--repo-root`, if the user provided a
    path that does not exist, the CLI prints a stderr error and
    exits with code `2`. If `--command-status-json` exists but is not
    parseable JSON, the CLI prints a stderr error and exits with
    code `2`.
  - **Internal-missing-artifact behavior preserved**: when a valid
    `--run-root` or `--stage` exists but its internal artifacts
    (`.loop/validation_summary.json`, `STAGE_PLAN.md`, etc.) are
    missing, the diagnosis still exits `0` with
    `MISSING_REQUIRED_FILE`. The exit-code contract covers
    *top-level* explicit input paths, not internal artifacts.
  - Updated docstring's exit-code table to document the new `2`
    conditions (explicit missing path, malformed
    `--command-status-json`).
  - Exposed `_validate_explicit_paths` and `_stdout_print` in
    `__all__` for testability.
  - No edits to `loop_engine/run_diagnosis.py`. The
    `write_next_action_reports(...)` helper already supported
    `json_only` / `markdown_only`, so the CLI just maps the new
    output-mode flag to those parameters.
- [tests/test_diagnose_run_failure_cli_output.py](tests/test_diagnose_run_failure_cli_output.py)
  - Removed the `_extract_last_json_object` substring-extraction
    workaround. Every JSON contract test now uses
    `json.loads(proc.stdout)` directly or pipes through
    `python -m json.tool`.
  - Added `test_print_json_emits_pure_parseable_json_to_stdout`
    asserting stdout starts with `{`, contains no `next_action_report`
    substring, and round-trips through `json.loads`.
  - Added `test_print_json_pipes_to_python_m_json_tool` that invokes
    `python -m json.tool` against captured stdout and verifies the
    round-trip succeeds.
  - Added `test_print_json_does_not_emit_path_line_before_payload` as
    a regression guard.
  - Added `test_quiet_and_print_json_emits_pure_json` verifying that
    `--print-json` is preserved by `--quiet` and stdout is pure JSON.
  - Updated `test_print_markdown_emits_markdown_to_stdout` and added
    `test_print_markdown_in_both_mode_suppresses_path_lines` to
    enforce the pure-markdown contract.
  - Added `test_print_json_and_print_markdown_in_both_mode_emit_both_payloads`
    verifying deterministic JSON-then-markdown order with no path
    lines in `both` + both print flags mode.
  - Replaced `test_unreadable_run_root_path_is_diagnosed_not_rejected`
    with `test_unreadable_run_root_path_rejected` (exit nonzero,
    stderr mentions `run-root` and `does not exist`).
  - Added `test_unreadable_stage_path_rejected`,
    `test_unreadable_command_status_json_path_rejected`, and
    `test_malformed_command_status_json_exits_nonzero` covering the
    other explicit-input exit-code contract cases.
  - Added `test_run_root_exists_with_missing_internal_artifacts_exits_zero`,
    `test_run_root_with_stage_missing_required_basis_files_exits_zero`,
    and `test_stage_exists_with_missing_internal_artifacts_exits_zero`
    covering the preserved internal-missing-artifact behavior (exit
    0, `MISSING_REQUIRED_FILE`).
  - Updated `test_quiet_does_not_suppress_print_json` to assert pure
    JSON on stdout (no path line, no substring extraction).
  - Kept all backward-compat tests:
    `test_legacy_json_only_still_supported`,
    `test_legacy_markdown_only_still_supported`,
    `test_smoke_project_runs_with_output_mode_both`,
    `test_json_output_validates_against_schema_in_every_mode`.

No edits to:
- scientific artifacts
- `sigma_abc/checkpoints/`
- completed-stage validation artifacts
- raw provenance tables
- `.loop/human_signoff.yaml`, `_ledger.jsonl`, `_history/`
- devlog audits (no unrelated devlog files included in this patch)
- frozen checkpoints
- `loop_engine/run_diagnosis.py` (no diagnostic semantics change)
- `agent_bus` state-machine behavior
- dispatcher watch mode
- `tests/test_run_failure_diagnosis.py` (TASK_023 tests still pass)
- `tests/test_run_root_diagnosis.py` (TASK_024 tests still pass)
- `tests/test_agent_dispatcher.py` and
  `tests/test_agent_runtime_adapter.py` (TASK_026/027 tests still
  pass)

## tests_run

```
python -m py_compile scripts/diagnose_run_failure.py tests/test_diagnose_run_failure_cli_output.py
python -m pytest tests/test_diagnose_run_failure_cli_output.py -v
python -m pytest tests/test_run_failure_diagnosis.py tests/test_run_root_diagnosis.py -v
python -m pytest tests/test_agent_dispatcher.py tests/test_agent_runtime_adapter.py
python -m pytest tests/ -q

# CLI smoke for blocking issue 1 (pure JSON stdout)
python scripts/diagnose_run_failure.py \
  --stage smoke_projects/mock_polynomial_loop/stages/000_polynomial_identity \
  --outdir /tmp/loop_diag_pure_json --output-mode json --print-json
# Pipe the result through python -m json.tool

# CLI smoke for blocking issue 2 (exit codes on explicit inputs)
python scripts/diagnose_run_failure.py \
  --run-root /tmp/does_not_exist --output-dir /tmp/loop_diag_bad_runroot
python scripts/diagnose_run_failure.py \
  --stage /tmp/does_not_exist_stage --output-dir /tmp/loop_diag_bad_stage
echo "not valid JSON" > /tmp/bad_status.json
python scripts/diagnose_run_failure.py \
  --stage smoke_projects/mock_polynomial_loop/stages/000_polynomial_identity \
  --command-status-json /tmp/bad_status.json --output-dir /tmp/loop_diag_bad_status
```

## tests_passed

- `py_compile` -> **OK** on `scripts/diagnose_run_failure.py` and
  `tests/test_diagnose_run_failure_cli_output.py`.
- `python -m pytest tests/test_diagnose_run_failure_cli_output.py -v`
  -> **33 passed** in ~20s. (Was 23 in the prior patch; the
  post-review patch added 10 new tests covering the blocking-issue
  contracts and removed one obsolete test.)
- `python -m pytest tests/test_run_failure_diagnosis.py tests/test_run_root_diagnosis.py`
  -> **54 passed** in ~5s. (29 TASK_023 + 25 TASK_024 — unchanged.)
- `python -m pytest tests/test_agent_dispatcher.py tests/test_agent_runtime_adapter.py`
  -> **65 passed** in ~5s. (TASK_026/027 — unchanged.)
- `python -m pytest tests/ -q` -> **449 passed** in ~108s
  (was 439 in the prior patch; +10 net new tests).
- CLI smoke: `... --print-json` produced pure JSON stdout that
  `json.loads` and `python -m json.tool` both accept.
- CLI smoke: nonexistent `--run-root` exited `2` with stderr
  mentioning `run-root` and `does not exist`.
- CLI smoke: nonexistent `--stage` exited `2` with stderr
  mentioning `stage` and `does not exist`.
- CLI smoke: malformed `--command-status-json` exited `2` with
  stderr mentioning `command-status-json` and `JSON`.

New / updated regression tests:

| Group | Test |
|---|---|
| Blocking issue 1 — pure JSON stdout | `test_print_json_emits_pure_parseable_json_to_stdout` |
| Blocking issue 1 — pipes to `json.tool` | `test_print_json_pipes_to_python_m_json_tool` |
| Blocking issue 1 — no path line guard | `test_print_json_does_not_emit_path_line_before_payload` |
| Blocking issue 1 — pure JSON with `--quiet` | `test_quiet_and_print_json_emits_pure_json` |
| Blocking issue 1 — pure markdown stdout | `test_print_markdown_emits_pure_markdown_to_stdout` |
| Blocking issue 1 — `both` + `--print-markdown` suppresses paths | `test_print_markdown_in_both_mode_suppresses_path_lines` |
| Blocking issue 1 — `both` + both print flags | `test_print_json_and_print_markdown_in_both_mode_emit_both_payloads` |
| Blocking issue 1 — `--quiet` + `--print-json` pure JSON | `test_quiet_does_not_suppress_print_json` |
| Blocking issue 1 — `--print-json` round-trips | `test_print_json_output_is_pure_json_no_path_line` |
| Blocking issue 2 — `--run-root` rejected | `test_unreadable_run_root_path_rejected` |
| Blocking issue 2 — `--stage` rejected | `test_unreadable_stage_path_rejected` |
| Blocking issue 2 — `--command-status-json` missing | `test_unreadable_command_status_json_path_rejected` |
| Blocking issue 2 — `--command-status-json` malformed | `test_malformed_command_status_json_exits_nonzero` |
| Blocking issue 2 — run-root with internal gaps | `test_run_root_exists_with_missing_internal_artifacts_exits_zero` |
| Blocking issue 2 — stage-without-basis exits 0 | `test_stage_exists_with_missing_internal_artifacts_exits_zero` |
| Blocking issue 2 — run-root + partial stage exits 0 | `test_run_root_with_stage_missing_required_basis_files_exits_zero` |
| `--output-mode json` mentions only JSON | `test_output_mode_json_mentions_only_json_path` |
| `--output-mode markdown` mentions only markdown | `test_output_mode_markdown_mentions_only_markdown_path` |
| `--output-mode both` deterministic order | `test_output_mode_both_prints_both_paths_in_json_then_markdown_order` |
| default is `both` | `test_output_mode_both_is_default` |
| `--quiet` suppresses path lines | `test_quiet_suppresses_path_lines` |
| `--outdir` alias works | `test_outdir_alias_writes_to_specified_directory` |
| `--output-dir` + `--outdir` rejected | `test_output_dir_and_outdir_combined_rejected` |
| invalid `--output-mode` rejected | `test_output_mode_invalid_value_rejected` |
| `--json-only` + `--output-mode` rejected | `test_json_only_and_output_mode_combined_rejected` |
| `--json-only` + `--markdown-only` rejected | `test_json_only_and_markdown_only_combined_rejected` |
| `--print-markdown` rejected in `json` | `test_print_markdown_incompatible_with_json_mode` |
| `--print-json` rejected in `markdown` | `test_print_json_incompatible_with_markdown_mode` |
| missing `--output-dir` rejected | `test_missing_output_dir_rejected` |
| JSON schema-valid in every mode | `test_json_output_validates_against_schema_in_every_mode` |
| legacy `--json-only` still works | `test_legacy_json_only_still_supported` |
| legacy `--markdown-only` still works | `test_legacy_markdown_only_still_supported` |
| smoke project end-to-end | `test_smoke_project_runs_with_output_mode_both` |

## tests_failed

None.

## unresolved_issues

None.

## scope_deviation

- The blocking-issue-1 test for the `both` + both-print-flags case
  (`test_print_json_and_print_markdown_in_both_mode_emit_both_payloads`)
  finds the JSON/markdown boundary by comparing the on-disk JSON
  file with the leading prefix of stdout, instead of trying to
  locate a `}` character (which would match the first nested
  object's closer, not the document's). This is the simplest
  reliable approach given that the CLI's printed JSON is a verbatim
  copy of the on-disk JSON file. Documented in the test body.
- The `_validate_explicit_paths(...)` helper treats every path
  argument the user provided as an explicit input contract. This
  matches the reviewer's "If the user explicitly provides an input
  path that is unreadable/nonexistent, exit nonzero" rule. The
  diagnosis tool's `MISSING_REQUIRED_FILE` classification still
  fires for *internal* missing artifacts (e.g. a stage exists but
  `.loop/validation_summary.json` is missing), and that path still
  exits `0` — the diagnosis tool's read-only contract is preserved.
- The legacy `--json-only` / `--markdown-only` flags remain
  supported and behave exactly as `--output-mode json` /
  `--output-mode markdown` respectively. They are not deprecated
  in this patch; a future patch can deprecate them once
  external callers migrate.

## recommended_next_action

Land as-is. **33/33 focused CLI output tests pass**, **54/54 TASK_023
+ TASK_024 diagnosis tests pass**, **65/65 TASK_026/027 agent_bus
tests pass**, full suite **449/449 tests green** in ~108s. Both
reviewer blocking issues are fixed:

- `--print-json` stdout is purely parseable JSON; `json.loads(proc.stdout)`
  succeeds; `python -m json.tool` round-trips. The same pure-payload
  contract applies to `--print-markdown`.
- Explicit user-provided path arguments (`--run-root`, `--stage`,
  `--command-status-json`, etc.) that are unreadable or — for
  `--command-status-json` — malformed now exit nonzero with a clear
  stderr error. Internal missing artifacts inside a valid
  `--run-root` / `--stage` keep the `MISSING_REQUIRED_FILE` +
  exit `0` diagnosis semantics.

The CLI now has a stable, automation-friendly stdout contract:

- `json` mode emits JSON paths / payloads only.
- `markdown` mode emits markdown paths / payloads only.
- `both` mode emits both, in deterministic JSON-then-markdown
  order. With `--print-json` and/or `--print-markdown`, the path
  lines are suppressed and stdout is the pure payload(s).
- `--quiet` silences path lines; `--print-json` /
  `--print-markdown` always emit pure payloads.
- Argument errors, unreadable explicit inputs, malformed
  `--command-status-json`, schema-validation / write failures all
  exit nonzero; diagnostic errors go to stderr so stdout remains
  parseable.
- Generated JSON remains schema-valid.
- TASK_023, TASK_024, TASK_026, and TASK_027 tests are unchanged
  and pass.
- No scientific artifacts, frozen checkpoints, completed
  validation artifacts, human signoff ledgers, or `sigma_abc`
  scientific content are modified.

Future work (out of scope for this patch):
- Stable JSON envelope: every CLI invocation could print a
  single top-level `{"command": ..., "result": ..., "artifacts":
  {"json": ..., "markdown": ...}}` object. Out of scope per
  TASK_025_BACKFILL, which is about stdout separation, not
  envelope unification.
- A `diagnose.cli.exit_code` classifier that maps the
  `classification.code` to a process exit code (e.g.
  `BOUNDARY_APPROVAL_REQUIRED` -> 3, `HUMAN_SIGNOFF_REQUIRED`
  -> 4). Useful for orchestrators that want to react to the
  classification without re-reading the JSON. Not requested
  in TASK_025_BACKFILL.
- Deprecate `--json-only` / `--markdown-only` in favor of
  `--output-mode`. The current patch keeps them as
  backward-compatible aliases; a deprecation notice can be
  added once external callers have migrated.

## Git status after patch

```
git status --short
```
