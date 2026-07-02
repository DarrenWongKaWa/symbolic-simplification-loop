# Loop 022 Phase 5R-2 — Pre-Retry Snapshot

## Status

```text
PROVIDER READY: openai_compatible_api AVAILABLE (DeepSeek via env:OPENAI_COMPATIBLE_API_KEY).
CLEAN-SOURCE GUARD: clear (no cron, no tmux, no launchd, no background runner).
PHASE 5R-2 READY TO RUN.
```

## 1. Provider Readiness (fresh evidence)

```text
$ python3 scripts/probe_reviewer_providers.py --role ScientificMetaReviewer | head -45
... report written to archive/local_runs/2026-07-01T16-47-13+00-00_PROBE_REVIEWER_PROVIDERS_ScientificMetaReviewer.md
# Reviewer Provider Probe

role: `ScientificMetaReviewer`
fallback_policy: `runtime_failure_only`
require_real_provider: `True`
forbid_stub: `True`

## 2. `openai_compatible_api` (adapter: `openai_compatible_api`)
- enabled: `True` (reason: `env:LOOP_ENABLE_OPENAI_COMPATIBLE`)
- availability_status: `AVAILABLE`
- runtime_status: `AVAILABLE`
- config: {redacted: shows only api_key_env / base_url_env / model_env names}
```

Single enabled + available provider: `openai_compatible_api`
(pointing at DeepSeek via `OPENAI_COMPATIBLE_BASE_URL`/`_KEY`/`_MODEL`).
Stub forbidden in production, secrets redacted in report.

## 2. Clean-Source Guard

```text
$ tmux ls
no server running on /private/tmp/tmux-501/default

$ ps aux | grep -E "(run_autonomous_loop|sigma_abc|symbolic-simplification)" | grep -v grep
(no matches)

$ crontab -l
crontab: no crontab for wangjiahua

$ ls ~/Library/LaunchAgents | grep -i "loop\|runner\|sigma"
(none)

grep -rn "\-\-clean" scripts/  ->  only `parser.add_argument("--clean", action="store_true")`
                                  in `scripts/run_autonomous_loop.py` and
                                  `scripts/run_full_loop_smoke_test.py`.
                                  Nothing invokes `--clean` automatically.
```

No active background clean-style scheduler. No watch daemon points
at this repo. No tmux session is running a runner. Cron is empty.

## 3. Pre-Retry State

### Deepest physical checkpoint (frozen)

```text
$ ls -t autonomous_runs/sigma_abc/checkpoints/ | head -3
sigma_abc_006_tensorial_sector_architecture_review_2026-07-01T16-41-57+00-00
sigma_abc_007_pair_sector_basis_closure_pilot_2026-07-01T16-41-59+00-00
sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision_2026-07-01T16-42-00+00-00
```

The deepest frozen stage for sigma_abc is **stage 008**
(pair-sector benchmark + next-basis decision). Stages 011/012A/012B
were never produced (Phase 5R hit `human_signoff.yaml is required`
before recording any 011 freeze). The current `loop.yaml`'s
`current_checkpoint` reads
`sigma_abc_005_sector_ledger_xxx_collapse_regression_checkpoint_v1`
(the canonical project-level checkpoint that the runner resumes
from; `--from-current-checkpoint` will resume from here).

### Stages dirs

```text
$ ls autonomous_runs/sigma_abc/stages/
sigma_abc_006_tensorial_sector_architecture_review
sigma_abc_007_pair_sector_basis_closure_pilot
sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision
```

No 011/012A/012B stage dir present yet.

### Repo root

```text
$ ls *.md *.json
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
loop_config.json
```

Five curated files. No runner residue.

### Runtime config shape (values redacted, names only)

```text
agents/runtime.local.yaml                  ->  profiles.sigma_abc_hypothesis_pre_ibp_throughput.runtime.<UNKNOWN TO LOOP>
                                              profiles.sigma_abc_hypothesis_pre_ibp_throughput.reviewer_provider_pools.ScientificMetaReviewer
                                              providers: [
                                                openai_compatible_api  (adapter: openai_compatible_api, enabled_env: LOOP_ENABLE_OPENAI_COMPATIBLE),
                                                ...codex_cli_resolver  (adapter: command, enabled_env: LOOP_ENABLE_CODEX, NOT ENABLED)...,
                                                ...claude_code_cli     (adapter: command, enabled_env: LOOP_ENABLE_CLAUDE_CODE, NOT ENABLED)...,
                                              ]

.env                                        ->  OPENAI_COMPATIBLE_BASE_URL=<redacted:url>
                                              OPENAI_COMPATIBLE_MODEL=<redacted:name>
                                              OPENAI_COMPATIBLE_API_KEY=<redacted:OPENAI_COMPATIBLE_API_KEY>
                                              LOOP_ENABLE_OPENAI_COMPATIBLE=1
```

Loader will read these via `loop_engine.config.load_dotenv()`,
which is now wired into `loop_engine.agent_runtime.load_runtime_local()`
(Loop 021P/Phase 5R fix).

### Forbidden artifacts (clean)

```text
$ find . -maxdepth 7 -type f \
    \( -name "*stage_013*" -o -name "*sigma_abc_013_*" \
       -o -name "*tensorial_ibp*" -o -name "*total_derivative*" \
       -o -name "*global_pre_ibp*" -o -name "*promoted_candidate_manifest*" \
       -o -name "*stage_012c_loop_orbit_canonicalization_promotion*" \) \
    -not -path "./.git/*" -not -path "./archive/*"
(no output)
```

## 4. Plan

The next command to execute (verbatim per spec):

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 3
```

This loop:

- Will attempt stages 011 / 012A / 012B in that order (the
  next three stages past the resume point).
- Will use `ProviderPoolAdapter` for all reviewer roles
  (Loop 022).
- Will NOT use `--clean`, `--write-root-report`, or any
  `sigma_abc_loop_candidate_promotion` profile.
- Will NOT auto-create `human_signoff.yaml`.
- Will NOT start 012C promotion, Stage 013, or tensorial IBP.
- Will NOT introduce total-derivative reduction.

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
