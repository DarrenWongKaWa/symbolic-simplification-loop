#!/usr/bin/env python3
"""TASK_041 report-schema checker.

Read-only CLI that validates the expected shape of a
``reports/TASK_XXX_<NAME>/`` directory for a single construction-loop
task. It is the second bounded checker-phase task and follows the
narrow scripts exception documented in ``docs/safety.md`` and the
master repair framework.

The checker must NOT:

* modify, stage, commit, sign off, freeze, or push anything;
* depend on non-stdlib packages;
* do network I/O;
* recurse into unrelated parts of the repo beyond the single
  report directory it is asked to check.

Required artifacts that must be present for ``exit 0``:

    PLAN.md
    executor_report.md
    review_result.json
    landing_report.md

Optional artifacts (recognized, not required):

    audit_evidence.md
    final_summary.md
    build.log

Optional subdirectories (inspected only when present; never required
for ordinary tasks):

    human_review/    -- engineering audit files
    supplement/      -- theoretical derivation files

Exit codes:

* ``0`` -- required files present and no structural issue detected.
* ``1`` -- required files missing or structural issue detected.
* ``2`` -- target path is missing or not a directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_FILES: tuple[str, ...] = (
    "PLAN.md",
    "executor_report.md",
    "review_result.json",
    "landing_report.md",
)

OPTIONAL_FILES: tuple[str, ...] = (
    "audit_evidence.md",
    "final_summary.md",
    "build.log",
)

HUMAN_REVIEW_FILES: tuple[str, ...] = (
    "engineering_audit.tex",
    "engineering_audit.pdf",
    "build.log",
)

SUPPLEMENT_FILES: tuple[str, ...] = (
    "theoretical_derivation_supplement.tex",
    "theoretical_derivation_supplement.pdf",
    "build.log",
    "symbol_dictionary.tex",
    "validation_ledger_table.tex",
    "kernel_appendix.tex",
    "stage_to_derivation_map.md",
    "input_snapshot_manifest.wl",
)


def check_report(report_dir: Path) -> tuple[int, list[str]]:
    """Validate ``report_dir``. Return ``(rc, lines)``.

    ``lines`` is the reviewer-readable summary that the caller prints
    to stdout. ``rc`` is the suggested exit code for this report.
    """

    lines: list[str] = []
    missing_required: list[str] = []
    present_required: list[str] = []
    present_optional: list[str] = []
    missing_optional: list[str] = []
    optional_subdir_findings: list[str] = []
    review_result_problems: list[str] = []

    if not report_dir.exists():
        return 2, [f"report directory not found: {report_dir}"]
    if not report_dir.is_dir():
        return 2, [f"not a directory: {report_dir}"]

    for name in REQUIRED_FILES:
        if (report_dir / name).is_file():
            present_required.append(name)
        else:
            missing_required.append(name)

    for name in OPTIONAL_FILES:
        if (report_dir / name).is_file():
            present_optional.append(name)
        else:
            missing_optional.append(name)

    # Optional human_review/ -- inspect only if it exists.
    hr = report_dir / "human_review"
    if hr.exists():
        if not hr.is_dir():
            optional_subdir_findings.append(
                f"human_review exists but is not a directory: {hr}"
            )
        else:
            present_hr = [n for n in HUMAN_REVIEW_FILES if (hr / n).is_file()]
            if present_hr:
                optional_subdir_findings.append(
                    f"human_review/ contains: {', '.join(sorted(present_hr))}"
                )

    # Optional supplement/ -- inspect only if it exists.
    sp = report_dir / "supplement"
    if sp.exists():
        if not sp.is_dir():
            optional_subdir_findings.append(
                f"supplement exists but is not a directory: {sp}"
            )
        else:
            present_sp = [n for n in SUPPLEMENT_FILES if (sp / n).is_file()]
            if present_sp:
                optional_subdir_findings.append(
                    f"supplement/ contains: {', '.join(sorted(present_sp))}"
                )

    # review_result.json must parse as JSON and carry a verdict field.
    rr = report_dir / "review_result.json"
    if rr.is_file():
        try:
            payload = json.loads(rr.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            review_result_problems.append(
                f"review_result.json is not valid JSON: {exc.msg}"
            )
        else:
            verdict = payload.get("verdict") if isinstance(payload, dict) else None
            if verdict not in {"PASS", "PASS_WITH_CAVEAT", "FAIL"}:
                review_result_problems.append(
                    "review_result.json missing or invalid verdict "
                    "(expected PASS|PASS_WITH_CAVEAT|FAIL)"
                )

    # Render the reviewer-readable summary.
    lines.append(f"check_task_report_schema: {report_dir}")
    lines.append(f"  required present : {len(present_required)}/{len(REQUIRED_FILES)}")
    if present_required:
        for name in present_required:
            lines.append(f"    [OK]   {name}")
    if missing_required:
        for name in missing_required:
            lines.append(f"    [MISS] {name}")

    lines.append(
        f"  optional present : {len(present_optional)}/{len(OPTIONAL_FILES)}"
    )
    for name in OPTIONAL_FILES:
        marker = "[OK]" if name in present_optional else "[--]"
        lines.append(f"    {marker} {name}")

    if optional_subdir_findings:
        lines.append("  optional subdirs :")
        for finding in optional_subdir_findings:
            lines.append(f"    - {finding}")

    if review_result_problems:
        lines.append("  review_result.json problems:")
        for problem in review_result_problems:
            lines.append(f"    - {problem}")

    if missing_required or review_result_problems:
        lines.append("RESULT: FAIL")
        return 1, lines

    lines.append("RESULT: PASS")
    return 0, lines


def main(argv: list[str] | None = None) -> int:
    # Intercept --self-test before argparse so it does not require
    # the positional report_dir argument.
    if argv is None:
        argv = sys.argv[1:]
    if "--self-test" in argv:
        argv = [a for a in argv if a != "--self-test"]
        return run_self_test()

    parser = argparse.ArgumentParser(
        prog="check_task_report_schema.py",
        description=(
            "Read-only check: validate the expected shape of a "
            "single reports/TASK_XXX_<NAME>/ directory."
        ),
    )
    parser.add_argument(
        "report_dir",
        help="Path to the reports/TASK_XXX_<NAME>/ directory to check.",
    )
    args = parser.parse_args(argv)

    rc, lines = check_report(Path(args.report_dir))
    sys.stdout.write("\n".join(lines) + "\n")
    return rc


def run_self_test() -> int:
    """Internal behavior smoke test. Uses a temp directory; safe and
    read-only with respect to the worktree."""

    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="check_task_report_schema_selftest_"))
    try:
        # Case 1: a fully populated report directory -> 0.
        d_ok = tmp / "TASK_OK"
        d_ok.mkdir()
        for n in REQUIRED_FILES:
            (d_ok / n).write_text(
                "OK\n" if n.endswith(".md") else "{\"verdict\": \"PASS\"}\n",
                encoding="utf-8",
            )
        (d_ok / "audit_evidence.md").write_text("audit\n", encoding="utf-8")
        rc, lines = check_report(d_ok)
        assert rc == 0, (rc, lines)
        joined = "\n".join(lines)
        assert "RESULT: PASS" in joined, joined

        # Case 2: missing required -> 1.
        d_missing = tmp / "TASK_MISS"
        d_missing.mkdir()
        (d_missing / "PLAN.md").write_text("p\n", encoding="utf-8")
        rc, lines = check_report(d_missing)
        assert rc == 1, (rc, lines)
        joined = "\n".join(lines)
        assert "[MISS] executor_report.md" in joined, joined
        assert "[MISS] review_result.json" in joined, joined
        assert "[MISS] landing_report.md" in joined, joined
        assert "RESULT: FAIL" in joined, joined

        # Case 3: human_review/ present with audit pdf -> 0, reported.
        d_hr = tmp / "TASK_HR"
        d_hr.mkdir()
        for n in REQUIRED_FILES:
            (d_hr / n).write_text(
                "OK\n" if n.endswith(".md") else "{\"verdict\": \"PASS\"}\n",
                encoding="utf-8",
            )
        (d_hr / "human_review").mkdir()
        (d_hr / "human_review" / "engineering_audit.pdf").write_text(
            "%PDF\n", encoding="utf-8"
        )
        rc, lines = check_report(d_hr)
        assert rc == 0, (rc, lines)
        joined = "\n".join(lines)
        assert "human_review/" in joined, joined
        assert "engineering_audit.pdf" in joined, joined

        # Case 4: review_result.json invalid verdict -> 1.
        d_bad = tmp / "TASK_BAD"
        d_bad.mkdir()
        for n in REQUIRED_FILES:
            (d_bad / n).write_text(
                "OK\n" if n.endswith(".md") else "{\"verdict\": \"MAYBE\"}\n",
                encoding="utf-8",
            )
        rc, lines = check_report(d_bad)
        assert rc == 1, (rc, lines)
        joined = "\n".join(lines)
        assert "invalid verdict" in joined, joined

        # Case 5: non-existent path -> 2.
        rc, lines = check_report(tmp / "DOES_NOT_EXIST")
        assert rc == 2, (rc, lines)

        sys.stdout.write(
            "self-test: OK (full=0, missing=1, hr=0, bad-verdict=1, missing-dir=2)\n"
        )
        return 0
    except AssertionError as exc:  # pragma: no cover
        sys.stderr.write(f"self-test FAILED: {exc!r}\n")
        return 1
    finally:
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())