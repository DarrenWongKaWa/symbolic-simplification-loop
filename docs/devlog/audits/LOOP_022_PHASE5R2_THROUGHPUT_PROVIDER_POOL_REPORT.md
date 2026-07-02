# Loop 022 Phase 5R-2 — Throughput Retry (Provider Pool Wired)

## Status

```text
Final classification (per user spec):
B. "Upstream materialization still not fully frozen;
   reason: runner invoked 011 via LEGACY codex_resolver.sh path
   (adapter='command'); reviewer's verdict PASS_WITH_CAVEAT came
   from Codex CLI, not the DeepSeek provider pool; pool config
   in runtime.local.yaml was never consulted by build_adapter
   (only profile YAML is read); freeze rejected for human_signoff
   + completion_matrix blocking items; 012A / 012B NOT reached;
   deepest physical checkpoint after run remains 008;
   012C promotion NOT started."
```

This is **partial progress**: the runner now loads Loop 022's
`ProviderPoolAdapter` machinery (verified by `tests/test_loop022_*`
PASSING), and the probe confirms `openai_compatible_api` is
AVAILABLE through DeepSeek. However, the in-memory `profile`
dict that `build_adapter` reads is the `profiles/sigma_abc_*.yaml`
content, and the user's `reviewer_provider_pools` block lives in
`agents/runtime.local.yaml`. As a result:

- The runner reads only `runtime.command` from the profile YAML.
- The pool config in `runtime.local.yaml` is **invisible** to the
  runner's `build_adapter` path.

This is the discoverable gap this run surfaced. It is fixable in
a small follow-up (have `build_adapter` consult
`resolve_reviewer_pool_cfg(profile_name)` after
`runtime_config_for_profile` so the pool config in
`runtime.local.yaml` is actually used). **That follow-up was not
in this loop's spec.** It is documented under "Next Safe Action".

`sigma_abc/` physics was NOT modified. No 012C / 013 / IBP / total
derivative was started. `human_signoff.yaml` was NOT auto-created.
Permanent caveat preserved:
`DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.`

## Step 1 — Provider Readiness (fresh evidence)

```text
$ python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer
... report written to archive/local_runs/2026-07-01T16-47-13+00-00_PROBE_REVIEWER_PROVIDERS_ScientificMetaReviewer.md

## 2. `openai_compatible_api` (adapter: `openai_compatible_api`)
- enabled: `True` (reason: `env:LOOP_ENABLE_OPENAI_COMPATIBLE`)
- availability_status: AVAILABLE
- runtime_status: AVAILABLE
- config: {redacted — only api_key_env/base_url_env/model_env names}
```

Single enabled + available provider: **`openai_compatible_api`**
(pointing at DeepSeek).

Stub forbidden in production (Loop 021 contract). Secrets redacted
in the on-disk report. Loop 019R `codex_resolver.sh` not invoked
by the probe.

## Step 2 — Clean-Source Guard

```text
$ tmux ls
no server running on /private/tmp/tmux-501/default

$ ps aux | grep -E "(run_autonomous_loop|sigma_abc|symbolic-simplification|cleanup)" | grep -v grep
(no matches; only system daemons)

$ crontab -l
crontab: no crontab for wangjiahua

$ ls ~/Library/LaunchAgents | grep -i "loop\|runner\|sigma"
(none)

grep "^\s*\"--clean\"\|add_argument(\"--clean\"" scripts/ -- native CLI parsers only.
```

No background watch, no scheduler, no `--clean` invocation.

## Step 3 — Pre-Retry Snapshot

[Full snapshot file at docs/devlog/audits/LOOP_022_PHASE5R2_PRE_RETRY_SNAPSHOT.md](LOOP_022_PHASE5R2_PRE_RETRY_SNAPSHOT.md).

```text
deepest frozen checkpoint at run start:  sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision_2026-07-01T16-42-00+00-00
stages/ at run start:                     006 / 007 / 008
                                          (no 011 / 012A / 012B present)
loop.yaml current_checkpoint:              sigma_abc_005_sector_ledger_xxx_collapse_regression_checkpoint_v1
provider selected by probe:                openai_compatible_api
providers enabled:                         (LOOP_ENABLE_OPENAI_COMPATIBLE)
providers available:                       only openai_compatible_api
rejected runtime config shape:             redacted, names only
root contents:                             5 curated files (AGENTS.md, README.md,
                                            REPO_CLASSIFICATION_PRE_AUDIT.md,
                                            REPO_REORGANIZATION_REPORT.md,
                                            loop_config.json)
```

## Step 4 — Throughput Runner Command (verbatim per spec)

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 3
```

(No `--clean`. No `--write-root-report`. No
`sigma_abc_loop_candidate_promotion` profile.)

## What Happened

The runner advanced past the resume point (005) and **attempted
one stage**:

```text
attempted: sigma_abc_011_center_sector_pilot
frozen:    (no frozen checkpoint — freeze rejected below)
012A / 012B NOT attempted (runner crashed at freeze_checkpoint)
```

### Stage 011 — produced a real verdict (but via legacy Codex path)

The runner invoked **`ScientificMetaReviewer` via the LEGACY
`codex_resolver.sh` adapter, NOT the provider pool**. Evidence:

```text
.loop/agent_invocations/ScientificMetaReviewer/invocation_summary.json:
{
  "adapter": "command",                     ← LEGACY path
  "exit_code": 0,
  "schema_valid": true,
  "runtime_status": "AGENT_OK",
  "actually_invoked": true,
  "stub_used": false,
  "freeze_evidence_valid": true
}

.loop/agent_invocations/ScientificMetaReviewer/pool_result.json:
(does not exist)                              ← pool never ran for this role
```

`command.txt` confirms the legacy invocation:
```text
bash /Users/.../scripts/codex_resolver.sh ScientificMetaReviewer \
     /Users/.../reviewer_agent_prompt.ScientificMetaReviewer.md \
     /Users/.../scientific_metareviewer.json \
     /Users/.../sigma_abc_011_center_sector_pilot
```

**Root cause of the disconnect**: `loop_engine.agent_runtime.build_adapter`
reads `profile` (the YAML on disk under `profiles/`), and the
profile YAML for `sigma_abc_hypothesis_pre_ibp_throughput` does
NOT carry a `reviewer_provider_pools` block. The pool config is
correctly present under that profile name in
`agents/runtime.local.yaml`, but `build_adapter` does not consult
`runtime.local.yaml` for the pool (it only reads `runtime.local.yaml`
for legacy `runtime.command` via `runtime_config_for_profile`).
This is the discoverable gap this Phase 5R-2 run surfaced.

The Codex CLI (real agent, not stub) produced a reviewer verdict:

```text
.verdict:                 PASS_WITH_CAVEAT
.mathematical_status:    exact_reconstruction=true, regression_preserved=true,
                         overclaim_detected=false, simplification_real=true
.blocking_issues:         []
.next_action:             FREEZE
.reviewer_role:           GeneralReviewer     (Codex downgraded role due to
                                                local schema's reviewer_role
                                                enum that does not yet admit
                                                ScientificMetaReviewer literal)
```

### Decision and Freeze

```text
.loop/decision.json:
{
  "action": "FREEZE_WITH_CAVEAT",
  "reason": "review passed with caveats",
  "freeze_allowed": true,
  ...
}

.loop/review_result.json:
{
  "verdict": "PASS_WITH_CAVEAT",
  ...
  "nonblocking_caveats": [
    "Local schema review_result.codex.schema.json does not permit
     reviewer_role=ScientificMetaReviewer; encoded as GeneralReviewer.",
    "Validated identity is stage-local RowProvenanceHashConservation
     only: 93 center/contact rows conserved into 3 pattern families
     with CenterProvenanceDifference=0.",
    "CenterFusionDifference is explicitly NOT_CLAIMED.",
    "XXXCenterProjectionRegression is INHERITED_OR_DEFERRED, and
     Stage010PairFusionRegression is reported as WARN rather than
     a fresh direct pass.",
    "Permanent caveat preserved: DCProjectionTo1D -> INHERITED_PASS, ..."
  ]
}
```

The decision was `freeze_allowed=true`, but **the freeze itself
was rejected** by `freeze_checkpoint`:

```text
RuntimeError: Cannot freeze checkpoint: completion_matrix has
  blocking incomplete items: XXXCenterProjectionRegression,
  Stage010PairFusionRegression; human_signoff.yaml is required
  before freezing
```

This is the pre-existing Loop 013 trust-stack contract:
`human_signoff.yaml` is required for full freeze, and the runner
**did not auto-create** one (per spec). No `human_signoff.yaml`
was written anywhere during this run.

### `XXXCenterProjectionRegression` & `Stage010PairFusionRegression`

These are blocking items in `completion_matrix` that the runner
rightly refuses to freeze past. Both are tracking the boundary of
**what was actually validated** at this stage:

- `XXXCenterProjectionRegression` — directly checking the
  `sigma_abc_011` center-sector against the registered `sigma_xxx`
  benchmark. Per the stage profile, this is `INHERITED_OR_DEFERRED`,
  not a fresh pass.
- `Stage010PairFusionRegression` — re-running the Stage 010 pair
  fusion regression check. The current profile is `WARN`, not a
  fresh direct `PASS`.

These are honest, accurate blockings per the protective contract.
They were intentionally NOT silently overridden.

### 012A / 012B

After the freeze-rejection, the runner raised out of
`run_stage` and the script terminated (uncaught RuntimeError).
Stages 012A (`sigma_abc_loop_sector_inventory`) and 012B
(`sigma_abc_loop_hypothesis_generation`) were **NOT attempted**.

### Checkpoints after run

```text
$ ls autonomous_runs/sigma_abc/checkpoints/
sigma_abc_006_tensorial_sector_architecture_review_2026-07-01T16-41-57+00-00
sigma_abc_007_pair_sector_basis_closure_pilot_2026-07-01T16-41-59+00-00
sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision_2026-07-01T16-42-00+00-00
```

**Deepest physical checkpoint after run: `sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision_2026-07-01T16-42-00+00-00`**
(unchanged from pre-retry).

### Review debt

`AGENT_TIMEOUT` / `AGENT_QUOTA_LIMIT` did NOT occur. `ScientificMetaReviewer`
returned `AGENT_OK` via Codex CLI. No `AGENT_ALL_PROVIDERS_UNAVAILABLE`
either — because the runner consulted Codex (which the user has
authenticated), not the pool.

`loop_engine.review_debt.iter_open_review_debts`:
- 011's `decision.action = FREEZE_WITH_CAVEAT` does NOT mark debt,
  because the runner returned `freeze_allowed=true` from `decide_next_action`.
  The freeze-rejection by `freeze_checkpoint` is a separate
  enforcement layer (Loop 013).
- No new debt entries opened for 011.

### Human signoff

`human_signoff.yaml` was NOT created. The pre-existing signoffs
(stages 006/007/008) are unchanged.

## Step 5 — Review / Freeze Status

| Stage | Reviewer verdict | Decision | Frozen as checkpoint? | Reason |
|-------|------------------|----------|----------------------|--------|
| 011 | PASS_WITH_CAVEAT (via Codex CLI) | FREEZE_WITH_CAVEAT | **No** | freeze_checkpoint rejected: completion_matrix items + human_signoff.yaml missing |

The intended 012A / 012B were never attempted because `run_stage`
raised out at the freeze-rejection.

## Step 6 — Verification

### pytest

```text
$ python3 -m pytest -q
2 failed, 224 passed, 1 warning in 33.54s
```

Failures:

1. `tests/test_autonomous_loop_runner.py::test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`
   — pre-existing `human_signoff.yaml is required` failure (Loop 020A / 021 / 021P documented).
2. `tests/test_autonomous_loop_runner.py::test_sigma_abc_dry_run_reports_profile_driven_next_stage`
   — test-order dependence; passes in isolation (`pytest tests/...::test_sigma_abc_dry_run...`)
   but fails when the runner executes write residue from an earlier
   test pollutes `archive/local_runs/`. Pre-existing infra issue
   unrelated to Loop 022 / Phase 5R-2.

The remaining 224 tests pass.

### compileall

```text
$ python3 -m compileall loop_engine scripts tests
(no errors)
```

### Forbidden artifact scan

```text
$ find . -maxdepth 7 -type f \
    \( -name "*stage_013*" -o -name "*sigma_abc_013_*" \
       -o -name "*tensorial_ibp*" -o -name "*total_derivative*" \
       -o -name "*global_pre_ibp*" -o -name "*promoted_candidate_manifest*" \
       -o -name "*stage_012c_loop_orbit_canonicalization_promotion*" \) \
    -not -path "./.git/*" -not -path "./archive/*"
(no output)
```

No 012C / 013 / IBP / total derivative / promotion artefacts.

### Root hygiene

```text
$ ls *.md *.json
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
loop_config.json
```

Five curated files. No runner residue at the repo root (auto-pulled
to `archive/local_runs/` on subsequent invocations).

## Boundary Constraints Honored

- Did not modify `sigma_abc/`.
- Did not start 012C / 013 / IBP / total derivative.
- Did not modify freeze_preconditions / completion_matrix / human_signoff.
- Did NOT auto-create `human_signoff.yaml`.
- Did not bypass the Loop 013 `human_signoff.yaml is required` invariant.
- Did not fallback after semantic FAIL or NEEDS_PATCH (Codex returned PASS_WITH_CAVEAT; not retried).
- Did not run the provider pool on the runner side (pool config was correctly present in `runtime.local.yaml`, but `build_adapter` reads the profile YAML only — surfaced as a follow-up).
- Did not paste any real API key value at any point. The secret redactor remains in force for any disk write.

## Permanent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Final Classification

```text
B.  "Upstream materialization still not fully frozen;
     reason: runner invoked 011 via LEGACY codex_resolver.sh path
     (adapter='command'); reviewer's verdict PASS_WITH_CAVEAT came
     from Codex CLI, not the DeepSeek provider pool; pool config
     in runtime.local.yaml was never consulted by build_adapter
     (only profile YAML is read); freeze rejected for human_signoff
     + completion_matrix blocking items; 012A / 012B NOT reached;
     deepest physical checkpoint after run remains 008;
     012C promotion NOT started."
```

## Next Safe Action

Three things, in priority order, would unblock Phase 5R-2 to
verdict A:

1. **Profile / runtime-pool merge at the runner seam.** Have
   `loop_engine.agent_runtime.build_adapter` call
   `resolve_reviewer_pool_cfg(profile_name)` after
   `runtime_config_for_profile(...)`, and merge that pool block
   into a profile-level `reviewer_provider_pools` if it exists
   in `agents/runtime.local.yaml`. Effect: the same
   `ProviderPoolAdapter` that the Loop 022 tests pin would
   activate in production. After this change, Codex would not
   be the first choice — `openai_compatible_api` (DeepSeek)
   would. A retry of this exact same command would then advance
   past 011 to 012A → 012B with provider-pool-backed verdicts.

2. **Auto-signoff for pytest-style runs.** The
   `sigma_abc_safe_pre_fusion` profile already declares
   `human_signoff.auto_for_tests: true`, but the
   `freeze_checkpoint` runner does not honour
   `auto_for_tests`. A small wiring loop would freeze Stage 011
   in the pytest context, but a real human signoff would still
   be required for any production freeze of 011.

3. **Completion-matrix blocking-item resolution for 011.**
   `XXXCenterProjectionRegression` and `Stage010PairFusionRegression`
   are flagged as WARN/INHERITED_OR_DEFERRED. Stage 011 is not
   a fresh direct PASS for either. Resolving these to PASS would
   require either: (a) producing a registered
   `sigma_xxx_projection` kernel that explicitly extends to the
   center sector, or (b) marking `completion_matrix` items that
   explicitly inherit from the upstream Stage 008 deferred
   register. Either path is **separate** and outside Phase 5R-2.

Until those three are addressed, Phase 5R-2 cannot reach verdict A.
The trust-stack invariants are preserved.

No further agent-driven steps were taken. Awaiting user direction
on whether to:

- `approved: integrate profile / runtime-pool merge at runner`
  to make the pool config in `runtime.local.yaml` actually
  take effect in the runner (recommended), or
- `approved: stop here, parked`,
- or some other direction.
