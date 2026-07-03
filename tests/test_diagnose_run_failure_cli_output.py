"""Tests for the stable CLI output contract of ``scripts/diagnose_run_failure.py``.

TASK_025_BACKFILL (post-review patch) — verifies the ``--output-mode``
contract, the ``--print-json`` / ``--print-markdown`` automation flags,
the ``--quiet`` flag, the ``--outdir`` alias, argument validation,
exit codes, and schema validity of the generated JSON report.

Post-review contract assertions:

* ``--print-json`` makes stdout *purely* parseable JSON: no path line,
  no prefix, no suffix. ``json.loads(proc.stdout)`` must succeed and
  ``proc.stdout | python -m json.tool`` must round-trip.
* ``--print-markdown`` makes stdout *purely* the markdown payload: no
  path line, no prefix. The two payloads are emitted in deterministic
  JSON-then-markdown order.
* Explicit user-provided path arguments that do not exist (e.g.
  ``--run-root``, ``--stage``, ``--command-status-json``) cause a
  nonzero exit. ``--command-status-json`` that exists but is malformed
  JSON also causes a nonzero exit.
* Internal missing artifacts inside a valid ``--run-root`` or
  ``--stage`` still exit 0 and produce an actionable
  ``MISSING_REQUIRED_FILE`` diagnosis.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from loop_engine.config import write_json, write_text
from loop_engine.schemas import validate_with_schema


REPO_ROOT = Path(__file__).resolve().parents[1]
DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."
SCRIPT = REPO_ROOT / "scripts" / "diagnose_run_failure.py"


# ---------------------------------------------------------------------------
# Builders (kept local to keep the file self-contained)
# ---------------------------------------------------------------------------


def _validation(*, overall_gate: str = "PASS") -> dict:
    return {
        "stage_name": "stage_t25_cli",
        "overall_gate": overall_gate,
        "checks": [
            {"name": "NoIBPStarted", "expected": True, "actual": True, "gate": "PASS"},
        ],
        "boundary_audit": {
            "overclaim_detected": False,
            "full_tensorial_claim_detected": False,
            "ibp_started_without_approval": False,
            "dc_caveat_preserved": True,
        },
    }


def _review(*, verdict: str = "PASS") -> dict:
    return {
        "verdict": verdict,
        "stage_name": "stage_t25_cli",
        "mathematical_status": {
            "exact_reconstruction": True,
            "simplification_real": True,
            "regression_preserved": True,
            "overclaim_detected": False,
        },
        "blocking_issues": [],
        "nonblocking_caveats": [DC_CAVEAT],
        "allowed_claims": ["PASS"],
        "forbidden_claims": ["Do not claim full tensorial sigma_abc correctness."],
        "next_action": "FREEZE",
        "patch_instructions": [],
    }


def _stage_skeleton(tmp_path: Path, *, name: str = "stage_t25_cli") -> Path:
    stage = tmp_path / "stages" / name
    (stage / ".loop").mkdir(parents=True, exist_ok=True)
    (stage / "reports").mkdir(parents=True, exist_ok=True)
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n")
    write_text(stage / "CLAIM_BOUNDARY.md", f"# Claim Boundary\n\n{DC_CAVEAT}\n")
    return stage


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the diagnose CLI with a fresh PYTHONPATH (repo root) and capture output."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
    )


def _pipe_through_json_tool(stdout: str) -> dict:
    """Pipe ``stdout`` through ``python -m json.tool`` and parse the output.

    This mirrors the reviewer's second acceptance criterion: stdout must
    be consumable by ``python -m json.tool`` as a single JSON document.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "json.tool"],
        cwd=REPO_ROOT,
        check=False,
        input=stdout,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
    )
    assert proc.returncode == 0, (
        f"python -m json.tool failed (rc={proc.returncode}): {proc.stderr!r} "
        f"for input: {stdout!r}"
    )
    return json.loads(proc.stdout)


# ---------------------------------------------------------------------------
# --output-mode json: stdout mentions JSON only
# ---------------------------------------------------------------------------


def test_output_mode_json_mentions_only_json_path(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli("--stage", str(stage), "--output-mode", "json", "--output-dir", str(out))
    assert proc.returncode == 0, proc.stderr
    # Only JSON is mentioned on stdout.
    assert "next_action_report.json" in proc.stdout
    assert "next_action_report.md" not in proc.stdout
    # Only the JSON artifact is written.
    assert (out / "next_action_report.json").exists()
    assert not (out / "next_action_report.md").exists()
    # JSON validates against the schema.
    payload = json.loads((out / "next_action_report.json").read_text())
    validate_with_schema(payload, "next_action_report")


# ---------------------------------------------------------------------------
# --output-mode markdown: stdout mentions markdown only
# ---------------------------------------------------------------------------


def test_output_mode_markdown_mentions_only_markdown_path(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli("--stage", str(stage), "--output-mode", "markdown", "--output-dir", str(out))
    assert proc.returncode == 0, proc.stderr
    # Only markdown is mentioned on stdout.
    assert "next_action_report.md" in proc.stdout
    assert "next_action_report.json" not in proc.stdout
    # Only the markdown artifact is written.
    assert (out / "next_action_report.md").exists()
    assert not (out / "next_action_report.json").exists()


# ---------------------------------------------------------------------------
# --output-mode both: deterministic JSON-then-markdown order
# ---------------------------------------------------------------------------


def test_output_mode_both_prints_both_paths_in_json_then_markdown_order(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli("--stage", str(stage), "--output-mode", "both", "--output-dir", str(out))
    assert proc.returncode == 0, proc.stderr
    # Both artifact files written.
    assert (out / "next_action_report.json").exists()
    assert (out / "next_action_report.md").exists()
    # JSON path comes first, then markdown path (deterministic order).
    json_idx = proc.stdout.index("next_action_report.json")
    md_idx = proc.stdout.index("next_action_report.md")
    assert json_idx < md_idx
    # Order on stdout: both lines present, JSON first.
    lines = [line for line in proc.stdout.splitlines() if "next_action_report" in line]
    assert lines == [
        f"next_action_report.json: {out / 'next_action_report.json'}",
        f"next_action_report.md: {out / 'next_action_report.md'}",
    ]


def test_output_mode_both_is_default(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli("--stage", str(stage), "--output-dir", str(out))
    assert proc.returncode == 0, proc.stderr
    assert (out / "next_action_report.json").exists()
    assert (out / "next_action_report.md").exists()
    json_idx = proc.stdout.index("next_action_report.json")
    md_idx = proc.stdout.index("next_action_report.md")
    assert json_idx < md_idx


# ---------------------------------------------------------------------------
# --print-json: stdout is purely parseable JSON
# ---------------------------------------------------------------------------


def test_print_json_emits_pure_parseable_json_to_stdout(tmp_path):
    """stdout is purely parseable JSON: no path line, no prefix, no suffix.

    The reviewer's acceptance criterion: ``json.loads(proc.stdout)`` must
    succeed directly without any substring extraction.
    """
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "json",
        "--output-dir", str(out),
        "--print-json",
    )
    assert proc.returncode == 0, proc.stderr
    # Stdout must be pure JSON: no path line, no human prefix/suffix.
    assert "next_action_report.json:" not in proc.stdout
    assert "next_action_report.md:" not in proc.stdout
    # Direct json.loads of the entire stdout must succeed.
    parsed = json.loads(proc.stdout)
    assert parsed["classification"]["code"] == "VALIDATION_GATE_FAILED"
    # The JSON on disk still validates.
    on_disk = json.loads((out / "next_action_report.json").read_text())
    assert on_disk["classification"]["code"] == "VALIDATION_GATE_FAILED"


def test_print_json_pipes_to_python_m_json_tool(tmp_path):
    """stdout pipes through ``python -m json.tool`` (reviewer's second criterion)."""
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "json",
        "--output-dir", str(out),
        "--print-json",
    )
    assert proc.returncode == 0, proc.stderr
    parsed = _pipe_through_json_tool(proc.stdout)
    assert parsed["classification"]["code"] in {
        "HUMAN_SIGNOFF_REQUIRED",
        "FREEZE_PRECONDITION_FAILED",
        "UNKNOWN_FAILURE",
    }


def test_print_json_does_not_emit_path_line_before_payload(tmp_path):
    """Failure-mode check: if the path line ever reappears before the JSON,
    this test will fail. Guards the blocking-issue-1 regression.
    """
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "json",
        "--output-dir", str(out),
        "--print-json",
    )
    assert proc.returncode == 0, proc.stderr
    # Stdout must start with "{" (the JSON payload), not "next_action_report.json:".
    assert proc.stdout.lstrip().startswith("{"), proc.stdout[:80]
    # And it must not contain the path-line prefix anywhere.
    assert "next_action_report" not in proc.stdout


def test_quiet_and_print_json_emits_pure_json(tmp_path):
    """``--quiet --print-json`` still emits pure JSON, because ``--print-json``
    is an explicit print request and wins over ``--quiet``.
    """
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "json",
        "--output-dir", str(out),
        "--quiet",
        "--print-json",
    )
    assert proc.returncode == 0, proc.stderr
    # No path line; stdout is pure JSON.
    assert "next_action_report.json:" not in proc.stdout
    assert "next_action_report.md:" not in proc.stdout
    parsed = json.loads(proc.stdout)
    assert parsed["classification"]["code"] == "VALIDATION_GATE_FAILED"


# ---------------------------------------------------------------------------
# --print-markdown
# ---------------------------------------------------------------------------


def test_print_markdown_emits_pure_markdown_to_stdout(tmp_path):
    """In ``markdown`` mode + ``--print-markdown``, stdout is purely the
    markdown payload (no path line, no JSON path).
    """
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "markdown",
        "--output-dir", str(out),
        "--print-markdown",
    )
    assert proc.returncode == 0, proc.stderr
    # No path lines, no JSON path. Stdout starts with the markdown heading.
    assert "next_action_report.json" not in proc.stdout
    assert "next_action_report.md:" not in proc.stdout
    assert proc.stdout.lstrip().startswith("# Next Action Report"), proc.stdout[:80]
    # Markdown content present.
    assert "VALIDATION_GATE_FAILED" in proc.stdout
    # Markdown artifact exists on disk.
    assert (out / "next_action_report.md").exists()


def test_print_markdown_in_both_mode_suppresses_path_lines(tmp_path):
    """In ``both`` mode + ``--print-markdown`` (no ``--print-json``), stdout
    is purely the markdown payload; path lines are suppressed.
    """
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "both",
        "--output-dir", str(out),
        "--print-markdown",
    )
    assert proc.returncode == 0, proc.stderr
    # Path lines are suppressed; stdout is the markdown payload.
    assert "next_action_report.json:" not in proc.stdout
    assert "next_action_report.md:" not in proc.stdout
    assert proc.stdout.lstrip().startswith("# Next Action Report"), proc.stdout[:80]


def test_print_json_and_print_markdown_in_both_mode_emit_both_payloads(tmp_path):
    """In ``both`` mode + both print flags, stdout is JSON then markdown
    (deterministic order), with no path lines.
    """
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "both",
        "--output-dir", str(out),
        "--print-json",
        "--print-markdown",
    )
    assert proc.returncode == 0, proc.stderr
    # No path lines.
    assert "next_action_report.json:" not in proc.stdout
    assert "next_action_report.md:" not in proc.stdout
    # The JSON payload on stdout must match the on-disk file exactly
    # (up to a trailing newline), and the markdown payload must be
    # the rest of stdout. This avoids the trap of finding the first "}"
    # inside the JSON's nested objects.
    on_disk_json = (out / "next_action_report.json").read_text()
    expected_json = on_disk_json if on_disk_json.endswith("\n") else on_disk_json + "\n"
    assert proc.stdout.startswith(expected_json), (
        f"stdout should start with the JSON payload; got: {proc.stdout[:200]!r}"
    )
    md_part = proc.stdout[len(expected_json):]
    assert md_part.lstrip().startswith("# Next Action Report"), md_part[:80]
    # Sanity: the JSON end of the expected prefix must occur before the
    # markdown heading in the original stdout.
    json_end_in_stdout = expected_json.rstrip().rfind("}")
    md_start = proc.stdout.index("# Next Action Report")
    assert json_end_in_stdout < md_start


# ---------------------------------------------------------------------------
# --quiet
# ---------------------------------------------------------------------------


def test_quiet_suppresses_path_lines(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "both",
        "--output-dir", str(out),
        "--quiet",
    )
    assert proc.returncode == 0, proc.stderr
    # No path lines on stdout.
    assert "next_action_report.json:" not in proc.stdout
    assert "next_action_report.md:" not in proc.stdout
    # Both files still written.
    assert (out / "next_action_report.json").exists()
    assert (out / "next_action_report.md").exists()


def test_quiet_does_not_suppress_print_json(tmp_path):
    """``--print-json`` is an explicit print request and is preserved by ``--quiet``.

    (The path line is also suppressed by ``--print-json`` itself, so this
    test focuses on the JSON-payload assertion.)
    """
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "json",
        "--output-dir", str(out),
        "--quiet",
        "--print-json",
    )
    assert proc.returncode == 0, proc.stderr
    # No path lines, but JSON payload is on stdout.
    assert "next_action_report.json:" not in proc.stdout
    parsed = json.loads(proc.stdout)
    assert parsed["classification"]["code"] == "VALIDATION_GATE_FAILED"


# ---------------------------------------------------------------------------
# --outdir alias
# ---------------------------------------------------------------------------


def test_outdir_alias_writes_to_specified_directory(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "alias_out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "both",
        "--outdir", str(out),
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "next_action_report.json").exists()
    assert (out / "next_action_report.md").exists()
    # stdout reports the same paths.
    assert str(out / "next_action_report.json") in proc.stdout
    assert str(out / "next_action_report.md") in proc.stdout


def test_output_dir_and_outdir_combined_rejected(tmp_path):
    stage = _stage_skeleton(tmp_path)
    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-dir", str(out_a),
        "--outdir", str(out_b),
    )
    assert proc.returncode != 0
    # argparse writes its error to stderr.
    assert "outdir" in proc.stderr.lower() or "output-dir" in proc.stderr.lower() or "not allowed" in proc.stderr.lower()


# ---------------------------------------------------------------------------
# Invalid argument combinations
# ---------------------------------------------------------------------------


def test_output_mode_invalid_value_rejected(tmp_path):
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(tmp_path / "stage"),
        "--output-mode", "xml",
        "--output-dir", str(out),
    )
    assert proc.returncode != 0
    assert "invalid choice" in proc.stderr.lower() or "xml" in proc.stderr.lower()


def test_json_only_and_output_mode_combined_rejected(tmp_path):
    stage = _stage_skeleton(tmp_path)
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--json-only",
        "--output-mode", "markdown",
        "--output-dir", str(out),
    )
    assert proc.returncode != 0
    assert "contradictory" in proc.stderr.lower()


def test_json_only_and_markdown_only_combined_rejected(tmp_path):
    stage = _stage_skeleton(tmp_path)
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--json-only",
        "--markdown-only",
        "--output-dir", str(out),
    )
    assert proc.returncode != 0
    assert "contradictory" in proc.stderr.lower()


def test_print_markdown_incompatible_with_json_mode(tmp_path):
    stage = _stage_skeleton(tmp_path)
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "json",
        "--output-dir", str(out),
        "--print-markdown",
    )
    assert proc.returncode != 0
    assert "print-markdown" in proc.stderr.lower()


def test_print_json_incompatible_with_markdown_mode(tmp_path):
    stage = _stage_skeleton(tmp_path)
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "markdown",
        "--output-dir", str(out),
        "--print-json",
    )
    assert proc.returncode != 0
    assert "print-json" in proc.stderr.lower()


# ---------------------------------------------------------------------------
# Missing required arguments / unreadable explicit inputs
# ---------------------------------------------------------------------------


def test_missing_output_dir_rejected(tmp_path):
    stage = _stage_skeleton(tmp_path)
    proc = _run_cli("--stage", str(stage))
    assert proc.returncode != 0
    assert "output-dir" in proc.stderr.lower() or "outdir" in proc.stderr.lower()


def test_unreadable_run_root_path_rejected(tmp_path):
    """A non-existent ``--run-root`` is an *unreadable explicit input*.

    The reviewer-required behavior is to exit nonzero (exit code 2) with
    a clear stderr error, not to emit a ``MISSING_REQUIRED_FILE``
    diagnosis and exit 0.
    """
    out = tmp_path / "out"
    proc = _run_cli(
        "--run-root", str(tmp_path / "does_not_exist"),
        "--output-dir", str(out),
    )
    assert proc.returncode != 0, proc.stderr
    assert "run-root" in proc.stderr.lower()
    assert "does not exist" in proc.stderr.lower() or "not exist" in proc.stderr.lower()


def test_unreadable_stage_path_rejected(tmp_path):
    """A non-existent ``--stage`` is also an unreadable explicit input."""
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(tmp_path / "does_not_exist_stage"),
        "--output-dir", str(out),
    )
    assert proc.returncode != 0, proc.stderr
    assert "stage" in proc.stderr.lower()
    assert "does not exist" in proc.stderr.lower() or "not exist" in proc.stderr.lower()


def test_unreadable_command_status_json_path_rejected(tmp_path):
    """A non-existent ``--command-status-json`` is an unreadable explicit input."""
    out = tmp_path / "out"
    stage = _stage_skeleton(tmp_path)
    proc = _run_cli(
        "--stage", str(stage),
        "--command-status-json", str(tmp_path / "no_such_status.json"),
        "--output-dir", str(out),
    )
    assert proc.returncode != 0, proc.stderr
    assert "command-status-json" in proc.stderr.lower()


def test_malformed_command_status_json_exits_nonzero(tmp_path):
    """A malformed ``--command-status-json`` exits nonzero (reviewer requirement)."""
    out = tmp_path / "out"
    stage = _stage_skeleton(tmp_path)
    bad = tmp_path / "bad_status.json"
    bad.write_text("{ this is : not, valid JSON", encoding="utf-8")
    proc = _run_cli(
        "--stage", str(stage),
        "--command-status-json", str(bad),
        "--output-dir", str(out),
    )
    assert proc.returncode != 0, proc.stderr
    assert "command-status-json" in proc.stderr.lower()
    assert "json" in proc.stderr.lower()


def test_run_root_exists_with_missing_internal_artifacts_exits_zero(tmp_path):
    """When ``--run-root`` exists but stage artifacts are missing, the
    diagnosis still exits 0 and reports an actionable ``MISSING_REQUIRED_FILE``
    diagnosis. The exit-code contract covers *top-level* explicit input
    paths, not internal artifacts.
    """
    run_root = tmp_path / "run_root"
    (run_root / "stages").mkdir(parents=True, exist_ok=True)
    # No stage directories; no AUTONOMOUS_LOOP_RUN_REPORT.md; no checkpoints.
    out = tmp_path / "out"
    proc = _run_cli(
        "--run-root", str(run_root),
        "--output-dir", str(out),
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads((out / "next_action_report.json").read_text())
    assert payload["classification"]["code"] == "MISSING_REQUIRED_FILE"


def test_run_root_with_stage_missing_required_basis_files_exits_zero(tmp_path):
    """``--run-root`` + a stage dir under ``stages/`` that exists but lacks
    its basis files still exits 0 and reports ``MISSING_REQUIRED_FILE``.
    """
    run_root = tmp_path / "run_root"
    (run_root / "stages" / "stage_incomplete").mkdir(parents=True, exist_ok=True)
    out = tmp_path / "out"
    proc = _run_cli(
        "--run-root", str(run_root),
        "--output-dir", str(out),
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads((out / "next_action_report.json").read_text())
    assert payload["classification"]["code"] == "MISSING_REQUIRED_FILE"


def test_stage_exists_with_missing_internal_artifacts_exits_zero(tmp_path):
    """An explicit ``--stage`` that exists but has missing basis files
    still exits 0 with ``MISSING_REQUIRED_FILE``. Only the *top-level*
    path argument is treated as an input contract error.
    """
    stage = tmp_path / "stage_partial"
    stage.mkdir(parents=True, exist_ok=True)
    # Note: no .loop/, no STAGE_PLAN.md, no CLAIM_BOUNDARY.md.
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-dir", str(out),
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads((out / "next_action_report.json").read_text())
    assert payload["classification"]["code"] == "MISSING_REQUIRED_FILE"


# ---------------------------------------------------------------------------
# Schema validation of generated JSON
# ---------------------------------------------------------------------------


def test_json_output_validates_against_schema_in_every_mode(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    for mode in ("json", "both"):
        out = tmp_path / f"out_{mode}"
        proc = _run_cli(
            "--stage", str(stage),
            "--output-mode", mode,
            "--output-dir", str(out),
        )
        assert proc.returncode == 0, proc.stderr
        payload = json.loads((out / "next_action_report.json").read_text())
        validate_with_schema(payload, "next_action_report")
    # json-only mode also produces schema-valid JSON.
    out = tmp_path / "out_json_only"
    proc = _run_cli(
        "--stage", str(stage),
        "--json-only",
        "--output-dir", str(out),
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads((out / "next_action_report.json").read_text())
    validate_with_schema(payload, "next_action_report")


# ---------------------------------------------------------------------------
# Backward compatibility: legacy --json-only and --markdown-only still work
# ---------------------------------------------------------------------------


def test_legacy_json_only_still_supported(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli("--stage", str(stage), "--json-only", "--output-dir", str(out))
    assert proc.returncode == 0, proc.stderr
    assert (out / "next_action_report.json").exists()
    assert not (out / "next_action_report.md").exists()
    assert "next_action_report.json" in proc.stdout
    assert "next_action_report.md" not in proc.stdout


def test_legacy_markdown_only_still_supported(tmp_path):
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="FAIL"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli("--stage", str(stage), "--markdown-only", "--output-dir", str(out))
    assert proc.returncode == 0, proc.stderr
    assert (out / "next_action_report.md").exists()
    assert not (out / "next_action_report.json").exists()
    assert "next_action_report.md" in proc.stdout
    assert "next_action_report.json" not in proc.stdout


# ---------------------------------------------------------------------------
# --print-json output is valid JSON
# ---------------------------------------------------------------------------


def test_print_json_output_is_pure_json_no_path_line(tmp_path):
    """``--print-json`` output is pure JSON that round-trips through ``json.loads``.

    The reviewer's blocking-issue-1 acceptance criterion: the path line
    is suppressed and ``json.loads(proc.stdout)`` succeeds.
    """
    stage = _stage_skeleton(tmp_path)
    write_json(stage / ".loop" / "validation_summary.json", _validation(overall_gate="PASS"))
    write_json(stage / ".loop" / "review_result.json", _review(verdict="PASS"))
    out = tmp_path / "out"
    proc = _run_cli(
        "--stage", str(stage),
        "--output-mode", "json",
        "--output-dir", str(out),
        "--print-json",
    )
    assert proc.returncode == 0, proc.stderr
    # No path line; stdout is pure JSON.
    assert "next_action_report.json:" not in proc.stdout
    assert "next_action_report.md:" not in proc.stdout
    parsed = json.loads(proc.stdout)
    validate_with_schema(parsed, "next_action_report")


# ---------------------------------------------------------------------------
# Smoke against the in-repo polynomial smoke project
# ---------------------------------------------------------------------------


def test_smoke_project_runs_with_output_mode_both(tmp_path):
    stage = REPO_ROOT / "smoke_projects" / "mock_polynomial_loop" / "stages" / "000_polynomial_identity"
    if not stage.exists():
        pytest.skip("smoke project missing in this environment")
    out = tmp_path / "smoke_out"
    proc = _run_cli("--stage", str(stage), "--output-mode", "both", "--output-dir", str(out))
    assert proc.returncode == 0, proc.stderr
    assert (out / "next_action_report.json").exists()
    assert (out / "next_action_report.md").exists()
    payload = json.loads((out / "next_action_report.json").read_text())
    validate_with_schema(payload, "next_action_report")
    # Deterministic order.
    json_idx = proc.stdout.index("next_action_report.json")
    md_idx = proc.stdout.index("next_action_report.md")
    assert json_idx < md_idx
