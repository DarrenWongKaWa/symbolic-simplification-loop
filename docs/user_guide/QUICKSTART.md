# Quickstart

This guide is intentionally short. It tells you what is reusable,
what is case-study, and the two invariants you must not violate.

## What is this repository

`symbolic-simplification-loop` is a **trust-stack framework** for
running a multi-stage autonomous loop with hard-bound safety
properties. It is NOT a content repo; the only runnable contract
is the loop engine + schemas + audit chain.

A research case study (`sigma_abc`) lives in this repo as the
**stress test** for the framework.

## Reusable loop framework (PUBLIC_CORE)

Importable Python:

```python
from loop_engine.pre_run_brief import build_pre_run_brief, audit_pre_run_brief
from loop_engine.pre_run_gate import check_pre_run_gate
from loop_engine.completion_matrix import write_completion_matrix
from loop_engine.human_signoff import build_signoff_from_decision, write_signoff
from loop_engine.identity_traceability import write_identity_traceability
```

CLI entry points (under `scripts/`):

| Script | Purpose |
| --- | --- |
| `scripts/run_autonomous_loop.py` | Main autonomous runner. |
| `scripts/build_pre_run_brief.py --stage --profile` | Build the pre-run brief for a stage. |
| `scripts/audit_pre_run_brief.py --stage --profile` | Audit a brief without consulting reviewers. |
| `scripts/check_pre_run_gate.py --stage --profile` | Run the gate decision. |
| `scripts/audit_identity_traceability.py --stage --project` | Render identities + traceability. |
| `scripts/sign_stage.py --stage` | Apply a chat-style human signoff. |
| `scripts/codex_resolver.sh --probe` | Verify the reviewer command resolves. |
| `scripts/local_codex_agent_runner.sh` | Canonical Codex subprocess wrapper. |

Run the test suite:

```text
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
```

The framework's invariants:

- **pre-run gate** is **always** deterministic (no reviewer call).
- **completion matrix** is **always** deterministic (no reviewer
  opinion decides completion status).
- **human signoff** cannot override failed validation, failed
  review, stale evidence, or unsafe boundary audit.
- **review verdict ∈ {PASS, PASS_WITH_CAVEAT}** plus
  `human_signoff.permission.freeze_checkpoint=true` plus
  healthy `completion_matrix` plus
  `identity_traceability_gate=PASS` plus `overall_gate=PASS`
  is what enables `freeze_checkpoint`.

## Case study (CASE_STUDY_SIGMA_ABC)

`sigma_abc/`, `profiles/sigma_abc_*.yaml`, `identities/sigma_abc.*`,
`benchmarks/`, `projects/sigma_abc/` together form the case study.
See `case_studies/sigma_abc/README.md` for the future-migration map
(the case-study files are still at the repo root in this pass).

To run the case study (advice only — the trust stack is unchanged):

```text
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 3
```

`--clean` will wipe the entire run root. Do not pass it during
a multi-stage retry unless you are starting over. For pytest or
smoke work, set `LOOP_RUN_ROOT` to an isolated directory (e.g.
`$(mktemp -d)`) so the runner writes into a sandbox instead of
the live `autonomous_runs/sigma_abc/` case-study run root.

## Examples (PUBLIC_EXAMPLE)

```text
examples/             <- finished example projects (kept at root)
smoke_projects/       <- smoke-test input fixtures (kept at root)
```

## Reporting and devlogs

Per-loop engineering reports (DEVLOG_LOOP_ENGINE) live in:

```text
docs/devlog/loop_engine/
docs/devlog/audits/
```

Per-stage sigma_abc reports (DEVLOG_SIGMA_ABC) live in:

```text
docs/devlog/sigma_abc/
```

Generated artifacts and one-off run outputs go to:

```text
archive/local_runs/        <- one-off outputs (gitignored)
autonomous_runs/           <- per-invocation runner output (gitignored)
reports/                   <- per-invocation stage digests (gitignored)
```

## Hard constraints (do not violate)

- The 012C **promotion** profile is `sigma_abc_loop_candidate_promotion`
  and its `human_approval.scope` field is the authority for whether
  promotion can run. Do not promote loop candidates outside it.
- Stage 013 (`sigma_abc_013_global_pre_ibp_assembly`) is a
  separate human-approval boundary. Do not auto-start it.
- Tensorial IBP and total-derivative reduction remain forbidden
  in every production profile.
- The permanent caveat
  `DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial
  DC-series PASS.` is preserved on every frozen
  `validation_summary.caveats` and every identity library.
