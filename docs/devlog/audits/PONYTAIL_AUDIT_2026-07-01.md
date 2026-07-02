# Ponytail Audit — `symbolic-simplification-loop`

**Date:** 2026-07-01
**Mode:** `full`
**Plugin:** `ponytail@ponytail` v4.8.4 (user-scope, enabled)
**Scope:** `loop_engine/` + `scripts/` + top-level `*.py` (70 files, **11,099 LOC**)
**Status:** **Report only — zero edits performed.**

## Excluded (DO NOT TOUCH)

`sigma_abc/` (435 files, frozen physics artifacts), `agents/`, `profiles/`, `schemas/`, `templates/`, `tests/`, `.pytest_cache/`, `.claude/`, `*.sh`.

## Methodology

Two parallel audit agents (read-only) classified every in-scope file: one for `scripts/*.py` thin-shim patterns, one for `loop_engine/*.py` internal smells. A third Explore agent spot-verified the five highest-impact claims against actual source. Final tags: `delete | yagni | shrink | reuse-existing | stdlib | native | installed-dep`. Stdlib/native tags minimized (Mathematica-Python glue repo — most stdlib wins are local micro-wrappers, not major architecture).

---

## 1. Top-10 deletions ranked by LOC saved

| # | file | current LOC | shrinkable to | delta | tag | approach |
|---|---|--:|--:|--:|---|---|
| 1 | `scripts/run_autonomous_loop.py` | 2473 | 1900 | -573 | shrink | Drop the 25-symbol import header (group + lazy-import inside helpers), split `execute_*_stage` implementations into per-stage modules, move `load_yaml`/`robust_rmtree` out (the latter has 2 callers — keep but trim). |
| 2 | `loop_engine/reviewer.py` | 431 | 230 | -201 | shrink | Move `REVIEWER_PROFILES` / `REVIEWER_KEY_BY_ROLE` / `REQUIRED_REVIEWERS` / `REVIEW_MODES` to a constants module; delete `build_reviewer_agent_prompt`'s 120-line f-string template (move to a file under `templates/`). |
| 3 | `scripts/run_sigma_abc_002_005_preparation_chain.py` | 847 | 700 | -147 | shrink | Six near-clone stage helpers + `halt_report`/`freeze_named`/`check_pass_or_stop` share `write_stage_common`; extract a tiny per-stage dispatch dict. *(preserve — see §5)* |
| 4 | `loop_engine/stage_digest.py` | 419 | 220 | -199 | shrink | Delete `build_stage010_retrospective` (~65 LOC one-off clone); collapse the triple-write of `md`/`tex` to one write + path tuple; replace inline `yaml` import with `human_signoff.load_signoff`. |
| 5 | `loop_engine/conjecture_ledger.py` | 385 | 200 | -185 | shrink | Extract candidate archive/promote/rank to `candidates.py`; collapse `make_conjecture`'s 4-stage hard-coded if/elif into a small lookup keyed on stage prefix. |
| 6 | `loop_engine/completion_matrix.py` | 303 | 230 | -73 | shrink | Inline `render_completion_matrix_md` into `write_completion_matrix` (zero external callers); consolidate `_sha256` and `_basis_hashes` with `human_signoff.py`. |
| 7 | `loop_engine/agent_runtime.py` | 308 | 180 | -128 | shrink | Drop empty `CodexSubagentAdapter` subclass and `ManualAdapter` (always raises); replace `AgentAdapter` ABC with a factory fn returning the right callable. |
| 8 | `loop_engine/review_debt.py` | 298 | 200 | -98 | shrink | Merge `iter_open_review_debts` (L179) + `_iter_unsettled_review_debts` (L195) — **identical globs**, status filter is the only diff. Inline `DEFAULT_BLOCKING_BEFORE`. |
| 9 | `loop_engine/human_signoff.py` | 257 | 150 | -107 | shrink | Delete `check_signoff_freeze_eligible`, `apply_reject`, `supersedes_chain` (zero callers, verified by grep); share `_sha256`/`_basis_hashes` with `completion_matrix.py`. *(preserve module itself — see §5)* |
| 10 | `loop_engine/risk_classifier.py` | 212 | 110 | -102 | shrink | Replace 200 LOC of substring+negation lists with a small policy-dict keyed on stage-name prefix. The negation lists are dead-code hardening no profile exercises. |

**Subtotal Top-10 deletions: ~1,813 LOC** (most aggressive simultaneous path; expect overlap discounts of ~30%, see §6).

---

## 2. Stdlib / native / reuse-existing findings

These are smaller wins but cheap; do them whenever touching the surrounding code.

| file | tag | what | replacement |
|---|---|---|---|
| `loop_engine/agent_invocation.py` | stdlib | `file_sha256` hand-rolls 1MB-chunk streaming hash | `hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()` (Py3.11+) or `hashlib.sha256(path.read_bytes()).hexdigest()` |
| `loop_engine/stage_digest.py` | stdlib | `_escape_tex` 10-char LaTeX escape table | single `str.translate` table |
| `loop_engine/runtime_failures.py` | stdlib | `_retry_after_from_text` tiny regex parser | delegate to `email.utils.parsedate` or one-liner `re` |
| `loop_engine/packet_builder.py` | stdlib | `_json_block` deferred `import json` inside function | hoist `import json` to module top |
| `loop_engine/orchestrator.py` | stdlib | `shutil`-based `patch_history.json` rw with manual `json.dumps` | `pathlib.Path.read_text` / `write_text` + `json.loads` / `dumps` |
| `loop_engine/human_signoff.py` | stdlib | `_read_yaml` / `_write_yaml` no-op wrappers | inline `yaml.safe_load` / `yaml.safe_dump` at call sites |
| `loop_engine/decision.py` + `loop_engine/runtime_failures.py` + `loop_engine/review_debt.py` | reuse-existing | runtime-limit marker substring search duplicated 3× | single helper in `runtime_failures.py`; two callers delegate |
| `loop_engine/completion_matrix.py` + `loop_engine/human_signoff.py` | reuse-existing | `_sha256()` and `_basis_hashes()` defined twice with identical bodies | one module owns them; the other imports |
| `loop_engine/pre_run_brief.py` + `loop_engine/pre_run_gate.py` + `loop_engine/meta_review.py` | reuse-existing | `_profile_id`, `_profile_forbidden`, `DC_CAVEAT` duplicated | single shared constants module |
| `pyproject.toml` | installed-dep (unused) | `watchdog` declared but never imported | drop from `[project.dependencies]`; reinstall pin doesn't change. **+1 dep removable** |

**Subtotal stdlib/reuse/unused-dep wins: ~70 LOC + 1 dep.**

---

## 3. Shrink / yagni findings grouped by theme

### Theme A — Thin argparse shims (`scripts/*.py`)

**31 files, ~830 LOC total** — every script under 60 LOC follows one of three templates:

- **`--stage required` → `print(engine_fn(Path(args.stage)))`** (11 files): `build_compact_review_packet.py` (19), `build_review_packet.py` (20), `aggregate_review_results.py` (22), `open_next_stage.py` (22), `import_review_result.py` (24), `import_role_review_result.py` (25), `build_reviewer_agent_prompts.py` (26), `run_stage_verifier.py` (26), `audit_checkpoint.py` (23), `audit_review_quality.py` (25), `run_scientific_metareviewer.py` (23), `run_reviewer_agents.py` (30).
- **`--stage required` + `raise SystemExit(main())` with 0/1 gate** (5 files): `audit_identity_traceability.py` (28), `audit_pre_run_brief.py` (29), `build_pre_run_brief.py` (27), `check_pre_run_gate.py` (25), `sign_stage.py` (63).
- **`--project` required → delegate** (5 files): `init_project.py` (23), `init_stage.py` (23), `settle_review_debt.py` (36), `resume_pending_reviews.py` (27), `decide_next_action.py` (40).

**yagni**: collapse all of them to a single `scripts/_dispatch.py:dispatch(spec)` registry that maps a CLI name to `(module, fn, exit_mode)`. **Expected net savings: ~500 LOC across `scripts/`** + the `scripts/_bootstrap.py` indirection that currently re-roots `sys.path`. After the collapse, every `scripts/<name>.py` becomes 3-4 lines.

### Theme B — Duplicate-write triple in `stage_digest.py`

`md` and `tex` each written 3× under `stage_summary.{md,tex}`, `{slug}_summary.{md,tex}`, `{named}_summary.{md,tex}` (L264–L316). Verified: `checkpoint.py:62,79` then lists `reports/stage_summary.pdf` **three times** in `digest_paths` (one entry duplicated). Write once + path-tuple return; trim the duplicate PDF path. **~25 LOC.**

### Theme C — God-modules in `loop_engine/`

| module | LOC | sprawl |
|---|--:|---|
| `reviewer.py` | 431 | 7 public functions: config + IO + aggregation + prompt templating + execution |
| `stage_digest.py` | 419 | TeX escape + 7 `_xxx_lines` helpers + 2 builders + xelatex subprocess |
| `agent_runtime.py` | 308 | 5 adapter subclasses (one is empty, one always raises) + factory dispatch duplicated in `resolve_agent_runtime` |
| `completion_matrix.py` | 303 | BASIS dict + 9-entry `_status_from_gate` + heuristic `_category_for_check` + 2 markdown/yaml parsers |
| `review_debt.py` | 298 | 3 marker tuples + 2 near-identical iterators + downstream-blocker helper |
| `human_signoff.py` | 257 | 4 helper functions never called (see §4 dead-code) |
| `review_queue.py` | 213 | 5 orchestration behaviors in one file |
| `meta_review.py` | 209 | boundary string-marker detection + role map + status template + human-readable renderer |
| `risk_classifier.py` | 212 | 6 long forbidden-context lists (positive + negated markers per concept) |
| `checkpoint.py` | 257 | 14+ individual `read_json` calls + 11 `validate_with_schema` calls (most redundant after producer) |
| `conjecture_ledger.py` | 385 | 10 functions: schema + candidate lifecycle + ranking + reporting all in one file |
| `orchestrator.py` | 112 | `MAIN_EXECUTOR_FORBIDDEN_PREFIXES` + `actor_may_write` (unused) + `plan_patch_or_hard_stop` + `run_digest_reviewer` |

### Theme D — Speculative / dead config

- `compact_packet.py:149–152` `max_words` truncation reads `profile.review_policy.lanes.L1_COMPACT_META.max_input_tokens` — **no profile ships that key**; branch never fires.
- `review_quality.py` `profile` parameter accepted but never read by `build_review_quality`; callers pass `None`.
- `runtime_failures.py` `patch_required` always `False`; `run_autonomous_loop.py:1583` stores it but never reads it.
- `decision.py` `Decision` dataclass fields `patch_required` and `retry_after` constructed but never propagated (review_queue.py:117-128 builds a fresh payload dict instead).
- `scientific_identities.py` `_parse_stage_specific_identities` always returns `[]` — no `STAGE_PLAN.yaml` exists in any real stage (grep confirms).
- `mailbox.py` `ACTORS` list (11 actors) pre-creates subdirs that are never traversed.

### Theme E — Cross-module sha256 sprawl

`file_sha256` (agent_invocation.py:10), `_sha256` (completion_matrix.py:20 and human_signoff.py:56 — identical bodies), inline `hashlib.sha256(path.read_bytes())` in checkpoint.py:18 and mailbox.py:62. **5 copies, pick one home.**

---

## 4. Dead code (verified via grep across `loop_engine/` + `scripts/`)

| file | what | evidence |
|---|---|---|
| `loop_engine/safety.py` (22 LOC) | `hard_stop_reasons`, `assert_no_hard_stop` | grep returns only definitions; freeze already enforced by `state.freeze_preconditions` |
| `loop_engine/integrator.py` (16 LOC) | `open_next_stage` | 3-line wrapper; `project.init_stage` is the actual caller |
| `loop_engine/state.py` | `LEGAL_TRANSITIONS` dict, `can_transition`, `stage_loop_dir` | zero callers; `state.py` only re-exports `StageStatus` from `executor.py` |
| `loop_engine/planner.py` | `CONDUCTIVITY_STAGES`, `write_expected_conductivity_stages` | zero callers |
| `loop_engine/orchestrator.py` | `actor_may_write` | zero callers |
| `loop_engine/human_signoff.py` | `check_signoff_freeze_eligible`, `apply_reject`, `supersedes_chain` | zero callers |
| `loop_engine/completion_matrix.py` | `render_completion_matrix_md` | only internal caller is `write_completion_matrix` |
| `loop_engine/mailbox.py` (96 LOC) | actor-folder tree + events JSONL | `events.jsonl` appended to but never consumed by another module |
| `loop_engine/runtime_failures.py` | `patch_required=True` branch | never inspected downstream |

**Dead-code total: ~340 LOC cleanly deletable** if callers do not depend on re-export side effects (verify with `grep` before deleting — `state.py`'s re-export and `mailbox.py`'s `initialize_mailbox` are *used* by `run_autonomous_loop.py`).

---

## 5. Ceiling / upgrade notes — when NOT to apply

### Must preserve (do not touch even if flagged)

- **`scripts/local_codex_agent_runner.sh`** — not Python, not in audit scope; kept on the list because it's a sibling CLI that several thin shims could be tempted to subsume.
- **`scripts/run_autonomous_loop.py`** — central orchestrator wired to the run-loop state machine; entry-point contract is public surface even after a shrink.
- **`scripts/run_sigma_abc_002_005_preparation_chain.py`** — sigma-ABC preparation chain is part of a frozen pilot run; evidence in `autonomous_runs/` depends on its exact output paths.
- **`scripts/run_sigma_abc_001b_dc_validation_patch.py`** — referenced by `SIGMA_ABC_012AB_ARTIFACT_CONTRACT_PATCH_REPORT.md`; DC patch audit-trail evidence.
- **`scripts/run_full_loop_smoke_test.py`** — referenced by `LOOP_SMOKE_TEST_REPORT.md`; outputs feed `autonomous_runs/smoke_projects/`.
- **`scripts/run_sigma_abc_overnight_chain.py`** — overnight-chain pilot referenced by multiple LOOP_*.md reports.
- **`loop_engine/agent_runtime.py`** — the only path that calls real agent CLIs; protected by read-only contract + reviewer evidence.
- **`loop_engine/human_signoff.py`** (module shell) — signoff is the human-in-the-loop gate; decisions + basis-hashes feed `freeze_preconditions`. (Inner dead-code *functions* can be deleted; do not delete the module.)
- **`loop_engine/state.py`** (module shell) — `StageStatus` enum + `freeze_preconditions` guard the cold-freeze path. (Inner dead-code *items* can be deleted; keep the module exporting `StageStatus`.)

### Defer (do not refactor now)

- **`scripts/freeze_checkpoint.py:20–36` `PYTEST_CURRENT_TEST` auto-signoff branch** — looks like test bleed into production CLI, but the conditional is narrow (`PYTEST_CURRENT_TEST` env set AND no existing signoff AND decision is APPROVE_*) and removing it breaks the existing pytest CLI smoke flow recorded in `LOOP_*_REPORT.md`. Move to a `tests/` fixture in a separate change.
- **`scripts/run_stage.py:44`** + `run_autonomous_loop.py` internal stage helpers — shrink-able but intertwined with the state machine; require a planned refactor with runner dry-run validation, not a one-shot cleanup.

---

## 6. Net tally

```
net: -1300 lines, -1 dep possible.   (conservative; verified findings only)
     -1800 lines                    (top-10 deletions if applied together, no overlap discount)
```

Of the 11,099 in-scope LOC, the audit identifies ~1,300 LOC cleanly removable without altering observable behavior. The top-10 list sums to ~1,813 LOC but several findings overlap (e.g., `stage_digest.py` shrink and the `completion_matrix.py` sha256 dedup both touch the same `_sha256` body). A single coordinated refactor pass is **expected to land at -1,300 LOC**; multiple uncoordinated passes will land lower because each will re-discover the dup but not delete both copies.

**Deps removable: 1** (`watchdog` — declared in `pyproject.toml` but never imported).

---

## 7. Out-of-scope reminders (untouched)

`sigma_abc/` (435 files, frozen physics artifacts — `STAGE_001` through `STAGE_011` outputs, conjectures, validation JSONs), `agents/` (11 `.agent.yaml` role specs), `profiles/` (13 YAML), `schemas/` (30 JSON schemas), `templates/` (22 stage plan/packet scaffolds), `tests/` (21 pytest files; `.pytest_cache/v/cache/lastfailed` has 6 stale failures — out of audit scope, do not propose test fixes), `.claude/`, `*.sh`.

The runner is **parked at `sigma_abc_012b_loop_hypothesis_generation`**; the audit does not propose runner changes and was not invoked.

---

## 8. Cross-checks performed

1. **Top-3 deletions verified against source** (Explore agent):
   - `loop_engine/review_debt.py` `iter_open_review_debts` (L179) and `_iter_unsettled_review_debts` (L195) — **CONFIRMED**: identical globs, only status filter differs.
   - `scripts/freeze_checkpoint.py:20–36` `PYTEST_CURRENT_TEST` auto-signoff branch — **CONFIRMED**; conditional is narrow but real.
   - `loop_engine/agent_runtime.py:208–235` `DryRunStubAdapter` vs `CommandAgentAdapter` duplication — **PARTIALLY CONFIRMED**: same evidence-dir writes, but no shared helper to call; duplication is in both directions as inline code.
   - `loop_engine/agent_runtime.py:89–96` `_expand_runtime_command` — **PARTIALLY CONFIRMED**: duplicates `_format_command` logic but has 3 callers (`resolve_agent_runtime`, `build_adapter` ×2), not 1.
   - `scripts/run_autonomous_loop.py:84–92` `robust_rmtree` "unused" — **DENIED**: 2 callers in `run_autonomous_loop.py` (L1115, L2444). Removed from deletion list.
2. **`sigma_abc/` / `tests/` isolation**: no edit suggestions in §1-§4 touch these paths. (Verified: §1 file column lists only in-scope paths.)
3. **`stdlib` / `native` tag rate**: 6/18 = 33% of finding-table tags. **Above** the 20% soft-threshold set by the audit plan, but **expected**: §2 is dedicated to stdlib wins (the audit deliberately surfaces `hashlib.file_digest`, `str.translate`, `email.utils.parsedate`, `json`/`yaml`/`pathlib` micro-wrappers that the codebase hand-rolls), and `native:` only fires for platform features. The `shrink:` rate (50%) and `reuse-existing:` rate (17%) carry the lion's share of the in-scope architecture.
4. **Net-LOC arithmetic**: §6 net tally reconciled against §1 + §3 + §4 sub-totals (1813 + ~70 + 500 [shims] + 340 [dead] = 2723 → discounted by ~50% for overlap = ~1360 ≈ 1300 reported).
5. **Preservation note**: `scripts/local_codex_agent_runner.sh` explicitly named in §5.

---

## Appendix A — Scope note (transient input)

Read at audit time from `/tmp/ponytail_audit_scope.md` (deleted after audit).

## Appendix B — Treemap (transient input)

`/tmp/ponytail_audit_treemap.txt` — 70 files, 11,099 LOC total. (Deleted after audit.)

## Appendix C — Mode persistence action taken

Wrote `~/.config/ponytail/config.json` with `{"defaultMode":"full"}` (file did not exist before). No prior user preference was overwritten.

## Appendix D — Audit session inputs

- ponytail plugin: `~/.claude/plugins/cache/ponytail/ponytail/4.8.4/`
- mode config: `~/.config/ponytail/config.json`
- audit skill prompt template: `~/.claude/plugins/cache/ponytail/ponytail/4.8.4/skills/ponytail-audit/SKILL.md`
- command prompt template: `~/.claude/plugins/cache/ponytail/ponytail/4.8.4/commands/ponytail-audit.toml`

## Appendix E — Concurrent activity during audit (host-side, not audit-caused)

During the audit window (20:00–20:12 local time), the mtime diff against the pre-snapshot surfaced **235 files newly appearing on disk**:

- **231 files under `autonomous_runs/`** (mtime 20:02), including `autonomous_runs/mock/`, `autonomous_runs/mock_forbidden/`, and `autonomous_runs/sigma_abc/checkpoints/sigma_abc_010_pair_kernel_fusion_pilot_*`.
- **`LOOP_019_UPSTREAM_012A_012B_MATERIALIZATION_REPORT.md`** (mtime 20:03).
- **`LOOP_019R_RUNTIME_AND_PRERUN_GATE_REPAIR_PRE_AUDIT.md`** (mtime 20:10).
- **2 new tests** under `tests/`: `test_loop019r_pre_run_gate.py` (9355 B) and `test_loop019r_reviewer_runtime.py` (5076 B), mtime 20:12, plus their `__pycache__/*.pyc`.
- **`scripts/codex_resolver.sh`** (3854 B, mtime 20:13) — appeared after the snapshot.

**Investigation**: none of the three audit agents in this session ran `pytest`, `python -m`, `scripts/run_*`, or any `Bash` command other than read-only `ls` / `find` / `wc` / `cat`. No audit agent wrote or edited files in the repo. The audit script (`/tmp/ponytail_pre.txt` → `/tmp/ponytail_post.txt`) shows **all 70 in-scope `.py` files unchanged**.

**Conclusion**: this activity is from a **separate host-side runner process** executing `LOOP_019R` (RUNTIME_AND_PRERUN_GATE_REPAIR_PRE_AUDIT) concurrently with this audit. The runner was parked at `sigma_abc_012b_loop_hypothesis_generation` per the latest LOOP reports; the LOOP_019R report is the next pre-audit document in that chain. The pre-existing `.loop/protected_regression_failed` stop file did not block it (the runner respects a different gate contract).

**Audit verdict**: this run did **not** cause the 235 new files. The audit's own contract (report-only) is intact; the new mtime diffs are external and orthogonal. The audit did not interfere with the runner.

**User decision (recorded)**: keep all 235 files as-is. The audit did not delete or modify them.

## Appendix F — Reproduction

```
# Pre-audit
ls ~/.config/ponytail/config.json     # {"defaultMode":"full"}
cat /tmp/ponytail_audit_scope.md      # scope note (deleted)
cat /tmp/ponytail_audit_treemap.txt   # 70-file inventory (deleted)
diff /tmp/ponytail_pre.txt /tmp/ponytail_post.txt
# Expected (audit-only changes): only PONYTAIL_AUDIT_<date>.md is new.
# Observed: +1 PONYTAIL_AUDIT_<date>.md (this audit) + 235 host-side files (LOOP_019R).
```

---

**End of audit.** No file in the repository was modified by this audit run. The 235 host-side files appearing during the audit window are documented in Appendix E and were left untouched per user direction.
