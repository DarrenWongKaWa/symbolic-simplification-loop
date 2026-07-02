# Loop Report Consistency Hardening B2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans.

**Goal:** Finish report-consistency hardening by archiving evidence for the current follow-up patch, documenting the report audit gate, and writing the final hardening report.

**Architecture:** Documentation and evidence only. No code changes except running the existing audit script.

**Tech Stack:** Markdown, JSON, existing `scripts/audit_loop_report_consistency.py`.

---

## Hard Boundaries

Do not modify `sigma_abc` physics. Do not start 012C, Stage 013, tensorial IBP, or total-derivative reduction. Preserve `DCProjectionTo1D -> INHERITED_PASS`.

---

## Files

Create:

```text
docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_EVIDENCE.json
docs/devlog/loop_engine/LOOP_REPORT_CONSISTENCY_HARDENING_REPORT.md
```

Modify:

```text
docs/superpowers/plans/2026-07-02-claude-execution-codex-review-loop-protocol.md
```

---

### Task 1: Create Evidence JSON

Create `docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_EVIDENCE.json`:

```json
{
  "pytest": {
    "status": "PASS",
    "summary": "269 passed, 1 warning"
  },
  "compileall": {
    "status": "PASS",
    "summary": "No errors"
  },
  "two_test_reproducer": {
    "status": "PASS",
    "summary": "2 passed, 1 warning"
  },
  "report_consistency_tests": {
    "status": "PASS",
    "summary": "3 passed"
  }
}
```

### Task 2: Document Report Consistency Gate

Append to `docs/superpowers/plans/2026-07-02-claude-execution-codex-review-loop-protocol.md` under Standard Benchmark Gates:

```markdown
### Report Consistency Gate

When a Claude execution report claims PASS, create or locate a JSON evidence
file and run:

```bash
python3 scripts/audit_loop_report_consistency.py \
  --report <report.md> \
  --evidence <evidence.json>
```

A strict PASS report must not coexist with failed evidence. If evidence failed
but the report honestly says `PASS_WITH_FOLLOWUP_REQUIRED`, the audit may return
`PASS_WITH_CAVEAT`.
```

### Task 3: Run Report Audit

Run:

```bash
python3 scripts/audit_loop_report_consistency.py \
  --report docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_REPORT.md \
  --evidence docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_EVIDENCE.json
```

Expected:

```text
"overall_gate": "PASS"
```

### Task 4: Write Final Report

Create `docs/devlog/loop_engine/LOOP_REPORT_CONSISTENCY_HARDENING_REPORT.md`:

```markdown
# Loop Report Consistency Hardening Report

## Verdict

PASS as report-consistency benchmark hardening.

## What Changed

- Added `scripts/audit_loop_report_consistency.py`.
- Added `tests/test_loop_report_consistency.py`.
- Added evidence JSON for the current follow-up patch.
- Documented the report consistency gate in the Claude/Codex loop protocol.

## Verification

```text
python3 -m pytest -q
269 passed, 1 warning
```

```text
python3 -m compileall loop_engine scripts tests
No errors
```

```text
python3 -m pytest -q tests/test_loop_report_consistency.py -vv
3 passed
```

```text
python3 scripts/audit_loop_report_consistency.py --report docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_REPORT.md --evidence docs/devlog/loop_engine/LOOP_SKILL_REPO_INTEGRATION_FOLLOWUP_TEST_ISOLATION_EVIDENCE.json
overall_gate -> PASS
```

## Boundaries

- sigma_abc physics unchanged.
- 012C promotion not started.
- Stage 013 not started.
- Tensorial IBP not started.
- Total-derivative reduction not introduced.
- Full tensorial correctness not claimed.
- DCProjectionTo1D inherited-pass caveat preserved.
```

### Task 5: Stop

Do not run full pytest in Claude. Codex already ran it and will rerun if needed.
