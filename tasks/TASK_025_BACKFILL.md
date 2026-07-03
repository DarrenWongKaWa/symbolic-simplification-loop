# Task ID

TASK_025_BACKFILL

# Title

Normalize CLI Output Contract for diagnose_run_failure.py

# Problem

`diagnose_run_failure.py` currently prints both `next_action_report.json` and `next_action_report.md` paths even when invoked in JSON-only or markdown-only modes. This is acceptable for humans but unsafe for automation, dispatcher providers, Langflow integration, and scripts that parse stdout.

# Goal

Stabilize the CLI output contract for `scripts/diagnose_run_failure.py` without changing diagnosis classification semantics.

The CLI must support:

- `--output-mode json`
- `--output-mode markdown`
- `--output-mode both`
- optional automation flags:
  - `--quiet`
  - `--print-json`
  - `--print-markdown`
  - `--outdir` as alias for existing output directory behavior if useful

# Non-goals

- Do not implement real Claude Code or Codex CLI providers.
- Do not change dispatcher watch mode.
- Do not change run-root diagnosis semantics beyond output formatting.
- Do not change classification precedence unless required by existing tests.
- Do not auto-commit.
- Do not auto-freeze checkpoints.

# Allowed edits

- `scripts/diagnose_run_failure.py`
- `loop_engine/run_diagnosis.py`, only if needed for cleaner output-mode plumbing
- `tests/test_run_failure_diagnosis.py`
- `tests/test_run_root_diagnosis.py`, only if existing run-root tests need CLI expectation updates
- New focused test file such as `tests/test_diagnose_run_failure_cli_output.py`
- Minimal docs/comments near CLI argument parsing

# Forbidden edits

- Do not edit scientific artifacts.
- Do not edit frozen checkpoints.
- Do not edit files under `sigma_abc/checkpoints/`.
- Do not edit completed validation artifacts.
- Do not edit raw provenance tables.
- Do not edit human signoff ledgers.
- Do not edit `.loop/human_signoff.yaml`.
- Do not edit validated `sigma_abc` scientific outputs.
- Do not modify `agent_bus` state-machine behavior unless strictly necessary.
- Do not implement real provider invocation.
- Do not auto-stage, auto-commit, or auto-freeze.

# Implementation steps

1. Define CLI output modes.

Add `--output-mode {json,markdown,both}`.

Preserve backward compatibility by mapping existing `--json-only` to `--output-mode json` and existing `--markdown-only` to `--output-mode markdown`, if those flags already exist.

Default should be `both` unless existing behavior requires another default.

2. Normalize stdout behavior.

In `json` mode:

- stdout must mention only JSON output path or print direct JSON if `--print-json` is used.
- stdout must not mention markdown paths.
- stdout must not include markdown summaries.

In `markdown` mode:

- stdout must mention only markdown output path or print direct markdown if `--print-markdown` is used.
- stdout must not mention JSON output paths unless explicitly requested by an added flag.

In `both` mode:

- stdout may report both artifacts.
- order must be deterministic:
  1. JSON path
  2. Markdown path

3. Add automation flags.

Implement:

- `--quiet`: suppress nonessential stdout after successful generation.
- `--print-json`: emit report JSON to stdout.
- `--print-markdown`: emit markdown report to stdout.
- `--outdir`: optional alias for `--output-dir`, if current CLI uses `--output-dir`.

If `--quiet` is combined with `--print-json` or `--print-markdown`, explicit print flags should win or the CLI should reject the combination deterministically. Choose one behavior and test it.

4. Preserve file generation semantics.

`--output-mode json` should generate `next_action_report.json`.

`--output-mode markdown` should generate `next_action_report.md`.

`--output-mode both` should generate both.

Do not generate the unrequested artifact unless needed for compatibility; if compatibility requires generation, do not mention it on stdout in the opposite mode.

5. Stabilize exit codes.

Exit code rules:

- `0` for successful diagnosis and requested report generation.
- Nonzero for invalid arguments.
- Nonzero for unreadable inputs.
- Nonzero for malformed `next_action_report` output or schema validation failure.
- Nonzero for filesystem write failures.

6. Preserve schema validation.

Generated `next_action_report.json` must validate against `schemas/next_action_report.schema.json` in all modes that generate JSON.

7. Add tests.

Cover at least:

- `--output-mode json` stdout does not mention markdown artifacts.
- `--output-mode markdown` stdout does not mention JSON artifacts unless explicitly requested.
- `--output-mode both` prints both artifact paths in deterministic JSON-then-markdown order.
- `--print-json` emits parseable JSON to stdout.
- `--print-markdown` emits markdown to stdout without JSON path noise.
- `--quiet` suppresses nonessential stdout.
- invalid `--output-mode` exits nonzero.
- unreadable input exits nonzero.
- generated JSON validates against `next_action_report.schema.json`.
- existing TASK_023 diagnosis tests still pass.
- existing TASK_024 run-root diagnosis tests still pass.

# Acceptance commands

```bash
python -m pytest tests/test_run_failure_diagnosis.py
python -m pytest tests/test_run_root_diagnosis.py
python -m pytest tests/test_diagnose_run_failure_cli_output.py

python scripts/diagnose_run_failure.py \
  --stage smoke_projects/mock_polynomial_loop/stages/000_polynomial_identity \
  --outdir /tmp/loop_diag_cli_json \
  --output-mode json

python scripts/diagnose_run_failure.py \
  --stage smoke_projects/mock_polynomial_loop/stages/000_polynomial_identity \
  --outdir /tmp/loop_diag_cli_markdown \
  --output-mode markdown

python scripts/diagnose_run_failure.py \
  --stage smoke_projects/mock_polynomial_loop/stages/000_polynomial_identity \
  --outdir /tmp/loop_diag_cli_both \
  --output-mode both

python scripts/diagnose_run_failure.py \
  --stage smoke_projects/mock_polynomial_loop/stages/000_polynomial_identity \
  --outdir /tmp/loop_diag_cli_print_json \
  --output-mode json \
  --print-json \
  | python -m json.tool >/tmp/loop_diag_cli_print_json/parsed.json
```

# Expected output files

- Updated `scripts/diagnose_run_failure.py`
- Optional updated `loop_engine/run_diagnosis.py`
- New or updated CLI-focused pytest file
- Runtime outputs:
  - `next_action_report.json`
  - `next_action_report.md`, only when requested by output mode or compatibility path

# Risks

- Existing callers may rely on old mixed stdout. Mitigate by keeping `both` as default and documenting deterministic order.
- `--json-only` and `--markdown-only` may conflict with `--output-mode`. Mitigate by rejecting contradictory arguments with a nonzero exit.
- `--quiet` combined with print flags can be ambiguous. Mitigate with explicit tested precedence or argument rejection.
- Automation may parse stdout while errors go to stdout. Mitigate by sending diagnostics and argument errors to stderr.
- Changing file generation could break hidden assumptions. Mitigate by testing generated files and preserving backward compatibility where practical.

# Definition of done

TASK_025_BACKFILL is done when:

- `diagnose_run_failure.py` has a stable documented output-mode contract.
- `--output-mode json` does not print markdown paths or markdown summaries.
- `--output-mode markdown` does not print JSON paths unless explicitly requested.
- `--output-mode both` prints JSON then markdown deterministically.
- `--print-json` emits parseable JSON to stdout.
- `--quiet` suppresses nonessential stdout.
- Exit codes are stable and tested.
- Generated JSON remains schema-valid.
- TASK_023 and TASK_024 diagnosis tests still pass.
- No scientific artifacts, frozen checkpoints, completed validation artifacts, human signoff ledgers, or `sigma_abc` scientific content are modified.
