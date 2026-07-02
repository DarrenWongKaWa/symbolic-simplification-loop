# Classification Manifest

Single-page mapping from "what" to "where", produced by the
Loop 020 repo-hygiene pass.

| Top-level entry                  | Class                           | Destination                                      |
| ---                              | ---                             | ---                                              |
| `loop_engine/`                   | A. PUBLIC_CORE                  | (unchanged)                                      |
| `scripts/`                       | A. PUBLIC_CORE                  | (unchanged)                                      |
| `schemas/`                       | A. PUBLIC_CORE                  | (unchanged)                                      |
| `templates/`                     | A. PUBLIC_CORE                  | (unchanged)                                      |
| `skill/`                         | A. PUBLIC_CORE                  | (unchanged)                                      |
| `tests/`                         | A. PUBLIC_CORE                  | (unchanged)                                      |
| `agents/runtime.local.example.yaml` | A. PUBLIC_CORE              | (unchanged)                                      |
| `agents/runtime.local.yaml`      | G. LOCAL_PRIVATE                | gitignored; not in this pass                      |
| `policies/`                      | A. PUBLIC_CORE                  | (unchanged; `sigma_abc_*` items future-move)      |
| `examples/`                      | B. PUBLIC_EXAMPLE               | (unchanged)                                      |
| `smoke_projects/`                | B. PUBLIC_EXAMPLE               | (unchanged)                                      |
| `sigma_abc/`                     | C. CASE_STUDY_SIGMA_ABC         | (root; future move to `case_studies/sigma_abc/`)|
| `profiles/`                      | C. CASE_STUDY_SIGMA_ABC         | (root; future move to `case_studies/sigma_abc/profiles/`) |
| `benchmarks/`                    | C. CASE_STUDY_SIGMA_ABC         | (root; future move to `case_studies/sigma_abc/benchmarks/`) |
| `identities/`                    | C. CASE_STUDY_SIGMA_ABC         | (root; future move to `case_studies/sigma_abc/identities/`) |
| `projects/sigma_abc/`            | C. CASE_STUDY_SIGMA_ABC         | (root; future move to `case_studies/sigma_abc/project/`) |
| `autonomous_runs/`               | F. GENERATED_ARTIFACT           | (root; gitignored)                               |
| `reports/`                       | F. GENERATED_ARTIFACT           | (root; gitignored)                               |
| `LOOP_003..010_*_REPORT.md`     | D. DEVLOG_LOOP_ENGINE           | `docs/devlog/loop_engine/`                        |
| `LOOP_011..012_*_REPORT.md`     | D. DEVLOG_LOOP_ENGINE           | `docs/devlog/loop_engine/`                        |
| `LOOP_013_*_REPORT.md`          | D. DEVLOG_LOOP_ENGINE           | `docs/devlog/loop_engine/`                        |
| `LOOP_014_*` through `LOOP_018_*` | D. DEVLOG_LOOP_ENGINE         | `docs/devlog/loop_engine/`                        |
| `LOOP_019_*`, `LOOP_019R_*`     | D. DEVLOG_LOOP_ENGINE           | `docs/devlog/loop_engine/`                        |
| `LOOP_SMOKE_TEST_REPORT.md`     | D. DEVLOG_LOOP_ENGINE           | `docs/devlog/loop_engine/`                        |
| `LOOP_REVIEW_AUTOMATION_REPORT.md` | D. DEVLOG_LOOP_ENGINE       | `docs/devlog/loop_engine/`                        |
| `PLAN.md`                        | D. DEVLOG_LOOP_ENGINE           | `docs/devlog/audits/`                             |
| `REPO_AUDIT.md`                  | D. DEVLOG_LOOP_ENGINE           | `docs/devlog/audits/`                             |
| `PROFILE_RUNNER_AUDIT.md`        | D. DEVLOG_LOOP_ENGINE           | `docs/devlog/audits/`                             |
| `PROFILE_RUNNER_DRY_RUN.md`      | D. DEVLOG_LOOP_ENGINE           | `docs/devlog/audits/`                             |
| `SCIENTIFIC_REVIEWER_AUDIT.md`  | D. DEVLOG_LOOP_ENGINE           | `docs/devlog/audits/`                             |
| `PONYTAIL_AUDIT_2026-07-01.md`   | D. DEVLOG_LOOP_ENGINE           | `docs/devlog/audits/`                             |
| `SIGMA_ABC_*_REPORT.md`         | E. DEVLOG_SIGMA_ABC             | `docs/devlog/sigma_abc/`                          |
| `STAGE_012C_PROMOTION_PRE_AUDIT.md` | D. DEVLOG_LOOP_ENGINE       | `docs/devlog/sigma_abc/` (gate-engineering report for 012C prep) |
| `AUTONOMOUS_LOOP_RUN_REPORT.md` | F. GENERATED_ARTIFACT           | `archive/local_runs/`                            |
| `SCHEMA_VALIDATION_RESULT.json`  | F. GENERATED_ARTIFACT           | `archive/local_runs/`                            |
| `REPO_CLASSIFICATION_PRE_AUDIT.md` | D. DEVLOG_LOOP_ENGINE       | (kept at root as the audit-of-record for this pass) |
| `.gitignore`                     | A. PUBLIC_CORE                  | (updated, keeps updated patterns)                |
| `.DS_Store`                      | H. DELETE_OR_IGNORE             | (deleted from working tree)                       |
| `.pytest_cache/`                 | H. DELETE_OR_IGNORE             | (deleted from working tree, gitignored)           |
| `__pycache__/` (recursive)       | H. DELETE_OR_IGNORE             | (deleted from working tree, gitignored)           |
| `__MACOSX/`                      | H. DELETE_OR_IGNORE             | (gitignored)                                     |
| `.claude/`                        | G. LOCAL_PRIVATE                | (gitignored)                                     |

## Trust Stack Invariants Preserved

- `loop_engine/` — no module removed; no behaviour changed.
- `schemas/` — no schema changed.
- `profiles/` — no profile's `forbidden_actions` list mutated in
  this pass. (Loop 019R's `sigma_abc_loop_candidate_preparation.yaml`
  explicit `forbidden_actions` block is preserved exactly.)
- `tests/` — no test edited. Tests that hard-code paths like
  `tests/test_sigma_abc_*` and reference `sigma_abc/*` paths keep
  their original root-level targets; sigma_abc/ stays at root.
- `scripts/codex_resolver.sh`, `agents/runtime.local.yaml`,
  `loop_engine/pre_run_brief.py` — all Loop 019R plumbing fixes
  preserved exactly.

## Boundary Constraints Honored

- Did not modify `sigma_abc/` physics.
- Did not run any autonomous_loop.
- Did not start 012C / 013 / IBP / total derivative.
- Did not claim full tensorial sigma_abc correctness.
- Did not weaken pre_run_gate / freeze_preconditions / human_signoff.
- Did not replace real reviewer with stub.
- Did not bypass L2_FULL_PANEL review.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
