This repo packages a benchmark-driven Loop Engineering workflow for symbolic simplification in theoretical physics. It is based on the completed projected sigma_xxx simplification case and is intended to drive future projects such as full tensorial sigma_abc derivation. The framework enforces staged planning, symbolic validation, structured reviewer packets, structured verdicts, and frozen checkpoints.

## Codex Skill Entry Point

When working from Codex, invoke the installed skill first:

```text
Use $symbolic-simplification-loop.
```

The installed skill at `~/.codex/skills/symbolic-simplification-loop/` is the
compact agent-facing protocol. This repository is the detailed implementation,
schemas, tests, and case-study source of truth.

## What This Is

`symbolic-simplification-loop` is a lightweight workflow package. It does not simplify physics expressions by itself. Instead, it gives Codex, a human scientist, and an independent reviewer role a shared protocol for moving a symbolic derivation through staged plans, exact validation, reviewer-agent audit, and frozen checkpoints.

The core loop is:

```text
PLAN -> EXECUTE -> VERIFY -> PACKET -> REVIEW -> DECIDE -> CHECKPOINT
```

For checkpoint freeze, Loop 013 adds a human signoff node:

```text
STAGE_PLAN
-> validation_summary
-> review_result / boundary_audit
-> completion_matrix
-> human scientist signoff
-> freeze_preconditions
-> checkpoint manifest
```

The invariant is evidence before claims:

```text
old expression - new expression = 0
old expression - new expression - dF = 0
projection benchmark - reference benchmark = 0
```

## Why sigma_xxx Is The Reference Case

The reference benchmark is the completed projected one-dimensional multiband `sigma^xxx` pipeline:

```text
118 raw rows -> 208 coefficient rows -> 7 fused kernels -> 4 surviving kernels + dF_pair_total
10 residuals -> 6 cokernel -> 0 cokernel
DeltaKR -> 0
Anan Eq.(6) regression -> inherited PASS
Modify4-to-Modify5 Rice-Mele consistency -> PASS
```

The final projected basis is:

```text
K_c
K_R
K_ReL
K_ImL
```

Future full tensorial `sigma_{mu alpha beta}` work must project to the known `sigma^xxx` final checkpoint before it can claim full correctness.

## Start A New Project

```bash
python scripts/init_project.py --name sigma_abc
python scripts/init_stage.py --project sigma_abc --stage 000_raw_import
```

The generated project uses:

```text
raw/
stages/
checkpoints/
review_packets/
review_results/
reports/
validation/
supplements/
```

Each stage contains a plan, report, claim boundary, snapshots, scripts, output, validation, reports, and `.loop/` metadata.

## Run One Stage

This package does not execute Mathematica or physics code automatically. The stage runner validates the lifecycle files and records status.

```bash
python scripts/run_stage.py --stage sigma_abc/stages/000_raw_import
```

`scripts/run_stage.py` is intentionally a lifecycle-state helper only: it only
advances stage state and does not execute full physical verification, reviewer
agents, autonomous decisions, or checkpoint freezing. Use
`scripts/run_autonomous_loop.py` for the full repo-native
plan/execute/validate/review/decision/checkpoint cycle.

After stage scripts produce outputs, build a structured reviewer packet:

```bash
python scripts/build_review_packet.py --stage sigma_abc/stages/000_raw_import
```

V1 defaults conceptually to a Codex subagent reviewer: the reviewer reads the packet and selected validation artifacts, does not edit files, and returns structured `review_result.json`. Manual ChatGPT and API review remain optional modes. Save the structured JSON result, then import it:

```bash
python scripts/import_review_result.py --stage sigma_abc/stages/000_raw_import --file review.json
python scripts/decide_next_action.py --stage sigma_abc/stages/000_raw_import
```

To prepare a Codex subagent reviewer prompt:

```bash
python scripts/build_reviewer_agent_prompt.py --stage sigma_abc/stages/000_raw_import
```

Routine branch review can be split into three read-only Codex subagents:

```bash
python scripts/build_reviewer_agent_prompts.py --stage sigma_abc/stages/000_raw_import
```

This produces role-specific prompts for:

```text
AlgebraReviewer   checks Old - New - dF, row counts, and validation gates.
PhysicsReviewer   checks basis, symmetry, conventions, and claim boundary.
SoftwareReviewer  checks repo hygiene, stale files, table provenance, and reproducibility.
```

The canonical machine-readable reviewer output directory is
`.loop/reviewer_results/`. The older `.loop/reviews/` name may appear in legacy
manual instructions, but new autonomous stages should write reviewer JSON files
to `.loop/reviewer_results/`.

Save role-specific review JSON files under `.loop/reviewer_results/`, then aggregate them:

```bash
python scripts/import_role_review_result.py --stage sigma_abc/stages/000_raw_import --file algebra_review.json --role AlgebraReviewer
python scripts/import_role_review_result.py --stage sigma_abc/stages/000_raw_import --file physics_review.json --role PhysicsReviewer
python scripts/import_role_review_result.py --stage sigma_abc/stages/000_raw_import --file software_review.json --role SoftwareReviewer
python scripts/aggregate_review_results.py --stage sigma_abc/stages/000_raw_import
```

The reviewer is not the verifier. Even a `PASS` review cannot freeze a stage if `validation_summary.overall_gate != "PASS"`.

## Completion Matrix And Human Signoff

Every freeze-eligible stage should produce:

```text
reports/completion_matrix.json
reports/completion_matrix.md
.loop/human_signoff.yaml
.loop/human_signoff_history/
.loop/human_signoff_ledger.jsonl
```

The completion matrix summarizes what the stage planned, what evidence exists,
which protected regressions are only registered, which outputs are missing, and
whether boundary checks such as no unapproved IBP or no full tensorial overclaim
remain safe. `completion_matrix.freeze_eligible` is display-only; the
authoritative freeze gate is still `loop_engine.state.freeze_preconditions`.

Human signoff has four decisions:

```text
APPROVE_FREEZE
APPROVE_FREEZE_WITH_CAVEAT
DO_NOT_FREEZE_PATCH
REJECT_AND_STOP
```

Human signoff cannot override failed validation, failed review, stale evidence,
or unsafe boundary audit. It can only choose a permitted transition: approve
freeze when all gates pass, approve freeze with explicitly accepted caveats,
continue a boundary-safe patch loop, or reject and stop.

Chat-friendly signing example:

```bash
python scripts/sign_stage.py --stage sigma_abc/stages/012c <<'EOF'
SIGNOFF stage=sigma_abc_012c_real_loop_candidate_preparation
decision=DO_NOT_FREEZE_PATCH
reason=Stage012A/012B artifacts are missing; boundary audit is safe; caveats preserved.
signed_by=wangjiahua
EOF
```

Legacy `.loop/human_signoff.json` files can be upgraded with:

```bash
python scripts/migrate_human_signoff.py --stage sigma_abc/stages/012c
```

## Review Policy

Use Codex subagent review for routine branch review. Use web GPT for major checkpoints, paper claims, final scientific audits, and next research branch planning.

Do not confuse this symbolic reviewer-agent audit with Codex app `/review`. The app review pane is useful for code diffs and inline feedback; this loop's reviewer agents audit symbolic exactness gates, row provenance, convention maps, protected regressions, and claim boundaries.

Freeze a checkpoint only after validation and review gates pass:

```bash
python scripts/freeze_checkpoint.py --stage sigma_abc/stages/000_raw_import
```

## Use sigma_xxx As sigma_abc Benchmark

The template in `examples/sigma_abc_template/` states the core protected regression:

```text
ProjectToXXX[sigma_abc_tensor_formula] - sigma_xxx_final_reference == 0
```

If symbolic comparison is impossible, a numerical projection regression may be accepted only with an explicit caveat.

## Local Verification

Run:

```bash
pytest
```

## Repository Layout

After the Loop 020 repo-hygiene pass, the public layout is:

- Reusable loop framework: `loop_engine/`, `scripts/`, `schemas/`,
  `templates/`, `skill/`, `tests/`, `agents/runtime.local.example.yaml`.
- Public examples: `examples/`, `smoke_projects/`.
- Case study: `sigma_abc/`, `profiles/`, `benchmarks/`, `identities/`,
  `projects/sigma_abc/` (migration target:
  `case_studies/sigma_abc/`).
- Devlogs: `docs/devlog/loop_engine/`, `docs/devlog/sigma_abc/`,
  `docs/devlog/audits/`.
- Generated artifacts: `archive/local_runs/`,
  `autonomous_runs/`, `reports/` (gitignored).

See [`docs/REPO_LAYOUT.md`](docs/REPO_LAYOUT.md) for the full map
and [`docs/CLASSIFICATION_MANIFEST.md`](docs/CLASSIFICATION_MANIFEST.md)
for a per-file destination table.

## Quickstart for New Users

Read [`docs/user_guide/QUICKSTART.md`](docs/user_guide/QUICKSTART.md)
before running anything. The trust-stack invariants (no reviewer
opinion decides completion status, no IBP without explicit human
approval, the permanent `DCProjectionTo1D` caveat) are documented
there.

## Reviewer Provider Pool (Loop 021)

The reviewer roles in the trust stack (e.g.
`ScientificMetaReviewer`) are satisfied by a configurable
**provider pool** defined in
`agents/runtime.local.yaml` (gitignored) or
`agents/runtime.local.example.yaml` (committed template). The
pool falls through to the next provider on retryable runtime
failures only; schema-valid reviewer results stop the chain.

- [`docs/user_guide/REVIEWER_PROVIDER_POOL.md`](docs/user_guide/REVIEWER_PROVIDER_POOL.md) —
  pool contract, hard contracts, configuration, semantic-verdict behaviour.
- [`docs/user_guide/API_KEYS.md`](docs/user_guide/API_KEYS.md) —
  supported env vars (Anthropic, OpenAI, OpenAI-compatible,
  Codex, Claude Code), shell setup, redaction behaviour.

Probe and smoke scripts:

```text
python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
python3 scripts/run_reviewer_provider_smoke.py --role ScientificMetaReviewer --provider anthropic_api
```

Reports default to `archive/local_runs/<UTC-timestamp>_*.md`. Use
`--write-root-report` to also emit at the repo root.

```
```
