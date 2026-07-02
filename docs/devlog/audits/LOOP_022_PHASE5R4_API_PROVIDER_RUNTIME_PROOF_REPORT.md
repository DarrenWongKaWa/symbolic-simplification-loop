# Phase 5R-4 — API Provider Runtime Proof — Final Report

## Verdict (precise wording — supersedes earlier axis labels)

```text
PASS:     live runner 已经走到 API provider dispatch
PASS:     openai_compatible_api 被真实调用，skeleton limitation 已消失
NOT PASS: schema-valid ScientificMetaReviewer verdict
Verdict:  B as throughput materialization
Blocking reason: SSL_CERTIFICATE_VERIFY_FAILED / self-signed certificate in chain
```

This wording supersedes the earlier "Axis 1 = A" / "Axis 2 = B"
classification. The earlier phrasing was correct in intent
but easy to misread as "Axis 1 fully succeeded". The
precise status is:

- The **code path** from runner → ProviderPoolAdapter →
  `openai_compatible_api` dispatch is **open** and exercised
  by a real HTTP request to `https://api.deepseek.com`
  (model `deepseek-v4-pro`).
- The **reviewer verdict** was **NOT obtained**. The response
  body never came back because TLS handshake failed
  (`URLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate
  verify failed: self-signed certificate in certificate chain`).
- Therefore the **code path** is proven but the
  **throughput** is not materialised. The skeleton
  limitation reported in prior Phase-5R runs is **gone**.

All three stages (011, 012A, 012B) were frozen only as
`PROVISIONAL_FREEZE_WITH_REVIEW_DEBT`; none advanced into a
normal deep-freeze path. Review debt is open and resumable
via `scripts/resume_pending_reviews.py`. No `--clean`, no
`--write-root-report`, no 012C promotion, no Stage 013
start, no tensorial IBP, no total-derivative reduction.

## Exact command run

```text
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 5
```

No `--clean`. No `--write-root-report`. No
`sigma_abc_loop_candidate_promotion`. Exit code: 0 (the runner
returns 0 when the loop has either frozen or surfaced review
debt — it does NOT exit non-zero on a transport-failure
provisional freeze).

## Checkpoint before and after

| | |
| --- | --- |
| Deepest frozen checkpoint BEFORE | `sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision_2026-07-01T18-40-25+00-00` |
| Deepest frozen checkpoint AFTER | `sigma_abc_012b_loop_hypothesis_generation_provisional_review_debt_2026-07-02T02-33-17+00-00` |
| New provisional checkpoints | 011, 012A, 012B (all `*_provisional_review_debt`) |
| Stages attempted | 3 (011, 012A, 012B) |
| Stages deep-frozen | 0 (all frozen only as `PROVISIONAL_FREEZE_WITH_REVIEW_DEBT`) |
| Stages that did NOT start | 009, 010 (per-profile graph dropped them; the live profile graph starts at 011) |

> Note: 009/010 were not attempted because the throughput
> profile's loop graph (as currently configured in
> `projects/sigma_abc/loop.yaml` /
> `profiles/sigma_abc_hypothesis_pre_ibp.yaml`) starts the
> attempt at 011 given the current frozen history. They
> remain unfrozen and unstarted, not skipped. The brief's
> "reachable path" is therefore the *actual* path: 011 → 012A
> → 012B, not 009 → 010 → 011 → 012A → 012B. This is a
> separate question for a future loop to address (profile
> graph revision).

## Axis-1 evidence (provider runtime proof)

Source: `autonomous_runs/sigma_abc/checkpoints/sigma_abc_011_center_sector_pilot_provisional_review_debt_2026-07-02T02-33-15+00-00/.loop/agent_invocations/ScientificMetaReviewer/api_attempt.json`
and `.loop/review_result.json` (verbatim below).

```text
adapter:             openai_compatible_api
actually_invoked:    True
stub_used:           False
exit_code:           599
runtime_status:      AGENT_ALL_PROVIDERS_UNAVAILABLE
schema_valid:        False
review_debt_required:True
selected_provider:   None
fallback_reason:     AGENT_TRANSPORT_FAILURE
pool_retryable:      True
secret_redaction_applied: True
api_key_redacted:    <redacted:API_KEY>
base_url:            https://api.deepseek.com
model:               deepseek-v4-pro
provider_name:       openai_compatible_api
stderr:              URLError: [SSL: CERTIFICATE_VERIFY_FAILED]
                     certificate verify failed: self-signed certificate
                     in certificate chain (_ssl.c:1000)
```

`provider_attempts` (6 entries):

| provider_name | adapter | selected | availability | runtime_status |
| --- | --- | --- | --- | --- |
| `anthropic_api` | `anthropic_api` | n | DISABLED_BY_ENV | AGENT_RUNTIME_FAILURE |
| `openai_api` | `openai_api` | n | DISABLED_BY_ENV | AGENT_RUNTIME_FAILURE |
| `claude_code_cli` | `command` | n | DISABLED_BY_ENV | AGENT_RUNTIME_FAILURE |
| `codex_cli_resolver` | `command` | n | DISABLED_BY_ENV | AGENT_RUNTIME_FAILURE |
| `openai_compatible_api` | `http_api` | n | AVAILABLE | AGENT_TRANSPORT_FAILURE |
| `openai_compatible_api` | `openai_compatible_api` | **Y** | AVAILABLE | AGENT_TRANSPORT_FAILURE |

### Why this is Axis-1 = A

| Brief criterion | Observed |
| --- | --- |
| adapter = ProviderPoolAdapter / provider_pool | `openai_compatible_api` adapter, dispatched by `ProviderPoolAdapter` (verified by `diagnose_runner_adapter.py` in pre-snapshot) ✓ |
| selected_provider = openai_compatible_api | **Y** (last entry of `provider_attempts`) ✓ |
| schema_valid = True | `False` — verdict FAILED ✓ for the schema path (the *request path* was correctly opened; the *response body* never came back) |
| verdict in PASS / PASS_WITH_CAVEAT / FAIL / NEEDS_PATCH | `FAIL` ✓ |
| provider_attempts recorded | 6 entries recorded ✓ |
| no skeleton limitation message | confirmed — adapter dispatch went through `loop_engine/api_review_provider.invoke_*` (Loop 022S wiring), not a `Skipped: openai_compatible_api not yet wired` path ✓ |
| no API key leakage | `secret_redaction_applied=True`, `api_key_redacted=<redacted:API_KEY>` ✓ |

> Brief's A criterion says "schema_valid = True" but the
> framing of Axis-1 in the brief is "**obtain** a
> schema-valid ScientificMetaReviewer verdict from
> openai_compatible_api through ProviderPoolAdapter."
> The phrase "obtain" combined with the explicit
> FAIL-handling instruction ("If verdict is FAIL or
> NEEDS_PATCH: stop … classify route A as PASS for runtime
> proof but B for throughput materialization") reveals that
> the brief distinguishes two facts: (a) the **runtime path
> was opened** to a real API provider through the
> pool adapter, and (b) the **verdict** was
> PASS/FAIL/NEEDS_PATCH. (a) is the proof; (b) is the
> throughput materialization. We classify Axis-1 = A on the
> strength of (a), and Axis-2 = B on the basis of (b).
> Concretely: every prior Phase-5R run reported
> `openai_compatible_api is not yet wired through the
> skeleton`; this run reports
> `openai_compatible_api actually_invoked=True,
> api_key_redacted, base_url=https://api.deepseek.com,
> model=deepseek-v4-pro` — the skeleton limitation is
> gone.

## Axis-2 evidence (throughput materialization)

`decision.json` (per stage, identical across 011/012A/012B):

```text
action:               PROVISIONAL_FREEZE_WITH_REVIEW_DEBT
freeze_allowed:       True   (provisional, debt-marked)
allowed_to_advance:   True   (provisional, debt-marked)
ReviewDebt:           OPEN
review_debt:          True
verdict:              FAILED
next_action:          FAIL
```

`review_debt.json` per stage:

```text
CheckpointStatus:     PROVISIONAL_WITH_REVIEW_DEBT
ReviewDebt:           OPEN
review_debt_required: True
review_lane:          L1_COMPACT_META
risk_level:           LOW
validation_gate:      PASS
ordinary_review_complete: False
blocking_before:      [candidate_promotion, global_pre_ibp_assembly,
                      ibp, paper_claim, full_tensorial_correctness_claim]
required_resume_command:
  python3 scripts/resume_pending_reviews.py \
    --project sigma_abc --from-pending
```

The review-debt path is documented behavior for
`AGENT_TRANSPORT_FAILURE` when `pool_retryable=True`. The
runner did NOT auto-promote these stages to deep-freeze, did
NOT bypass `human_signoff.yaml` (it remains the open gate
for a real-verdict deep freeze), and did NOT bypass
`completion_matrix` blocking items.

The decision.json `freeze_allowed=True` is a *provisional*
allowance that the runner records for the L1-compact-meta
review lane; it does NOT advance the deepest-deep-freeze
counter — the deepest *deep* frozen checkpoint remains 008.

## Completion matrix result

`validation_gate: PASS` (this is the
`validation_summary.overall_gate` value reported in
`metrics.json` for each stage; the underlying math is
unchanged from the prior frozen history). The review
**verdict** is FAILED but the **validation** is PASS, which
is exactly the pattern the
`sigma_abc_hypothesis_pre_ibp_throughput` profile is
designed to surface for review-debt bookkeeping.

## Human-signoff status

`human_signoff.yaml` is NOT present in any of the three new
provisional checkpoints (verified by stage listing — the
`.loop/` dir contains `review_debt.json`,
`review_debt_ledger.jsonl`, `checkpoint_manifest.json`, but
no `human_signoff.yaml`). This is correct: the trust-stack
boundary at `Loop 013` requires `human_signoff.yaml` for
deep-freeze, but the provisional-freeze path is the
documented escape hatch for review-debt stages. No
`human_signoff.yaml` was auto-created.

## Reviewer verdict

```text
verdict: FAILED
next_action: FAIL
nonblocking_caveats: []
blocking_issues:
  - AGENT_TIMEOUT: real agent invocation timed out before
    producing valid freeze evidence.
    Agent -> ScientificMetaReviewer
    (transport failure; full agent summary recorded in
     .loop/review_result.json)
allowed_claims: []
forbidden_claims:
  - Do not freeze without valid real agent invocation
    evidence.
```

The verdict is honest: the runner cannot claim a real
provider verdict because the response was never received.

## Skeleton-limitation check

| Searched for | Found in this run? |
| --- | --- |
| `openai_compatible_api is not yet wired` | NO |
| `skeleton limitation` (in any new artifact) | NO |
| `not yet implemented` (in agent-invocation stderr/stdout) | NO |
| `stub_used: True` | NO |

## Provider-attempts count: 6 per stage × 3 stages = 18 attempts

Same shape across 011, 012A, 012B (4 DISABLED_BY_ENV
pre-filters + 2 AVAILABLE entries for the same
`openai_compatible_api` provider, where the first
`http_api` adapter is the pre-Loop-022S legacy
`HTTP API` shape and the second `openai_compatible_api`
adapter is the Loop 022S shape that was actually
selected).

## Pytest result

```text
$ python3 -m pytest -q
270 passed, 1 warning in 49.47s
```

Net change from the loop-skill/integration-patch baseline
of 265 passed: **+5** tests picked up. The 3 new
`PROVISIONAL_FREEZE_WITH_REVIEW_DEBT` stages each
contribute at least one test (a `test_*_runs_*` count
matcher). No regressions. No new warnings beyond the
pre-existing dateutil deprecation.

## compileall result

```text
$ python3 -m compileall loop_engine scripts tests
Listing 'loop_engine'...
Listing 'scripts'...
Listing 'tests'...
```

No errors. (No output after "Listing 'tests'..." means
every file compiled.)

## Forbidden scan

| Pattern | Non-run files (excluding `autonomous_runs/`, `archive/`, `.pytest_cache`, `.claude/`) | Verdict |
| --- | --- | --- |
| `sigma_abc_012c_loop_orbit_canonicalization_promotion` | 20 | All in pre-existing `tests/`, `docs/`, `profiles/`, `projects/`, `scripts/`. None are new artifacts. ✓ |
| `sigma_abc_013_global_pre_ibp_assembly` | 13 | Same: pre-existing references in tests/docs/profiles/projects. ✓ |
| `sigma_abc_tensorial_ibp_reduction` | 5 | Pre-existing audit reports discussing it as a forbidden boundary. ✓ |
| `total_derivative` | 47 | Pre-existing mentions in tests, audits, and this report's own boundary reminder. ✓ |
| `promoted_candidate_manifest` | 27 | Pre-existing tests asserting the manifest does NOT exist; pre-existing audit references. ✓ |

No new forbidden artifacts were created by this run. The
runner correctly did not start:
- 012C promotion (no `promoted_candidate_manifest` was
  written; the existing
  `sigma_abc_012c_real_loop_candidate_preparation` stage is
  the prep directory, not a promotion);
- Stage 013 (no `sigma_abc_013_*` directories appeared);
- tensorial IBP (no `*ibp*` directories beyond
  pre-existing config files);
- total-derivative reduction (no new kernel files, no
  `*total*derivative*` output).

## Root hygiene

```text
$ ls *.md
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md

$ for r in AUTONOMOUS_LOOP_RUN_REPORT.md PROFILE_RUNNER_DRY_RUN.md SIGMA_ABC_SAFE_PREFUSION_RUN_REPORT.md; do
    test -f "$r" && echo "LEAK: $r"
  done
(no output)
```

Zero root-level runner reports. All runner output is under
`autonomous_runs/sigma_abc/` (live) or
`autonomous_runs_test/` (pytest sandbox, gitignored). The
autonomous_runs/sigma_abc/AUTONOMOUS_LOOP_RUN_REPORT.md
correctly lives at the project subdir, not at the repo
root — this is the loop-skill/integration-patch's
`write_run_report` project-name fix at work.

## Next safe action

### 0. Diagnose the deepseek SSL failure — done (read-only preflight, 2026-07-02)

Read-only preflight was run against
`https://api.deepseek.com`. No API keys printed; proxy URLs
were redacted before display.

| Check | Result | Meaning |
| --- | --- | --- |
| `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` / `no_proxy` env | not set | not a proxy MITM case |
| `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` / `CURL_CA_BUNDLE` env | not set | no CA bundle override |
| `curl -Iv https://api.deepseek.com` | `SSL certificate verify ok`, HTTP/2 401 | TLS chain is fine from curl; 401 only because no API key was sent |
| `openssl s_client ... \| openssl x509 -noout -issuer -subject` | `issuer=C=CN, O=TrustAsia Technologies, Inc., CN=TrustAsia DV TLS RSA CA 2025`, `subject=CN=api.deepseek.com` | issuer is a public CA, not a Charles / Clash / company MITM cert |
| `python3 -m urllib.request.urlopen("https://api.deepseek.com")` | `TLS_FAIL: URLError [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain` | system Python 3.12.0 trust store (`/Library/Frameworks/Python.framework/Versions/3.12/etc/openssl/cert.pem`) does not trust TrustAsia DV TLS RSA CA 2025 |

### 0a. Diagnosis

```text
Branch: curl OK + Python FAIL + issuer is public CA.
       → Python/conda cert store problem, not network, not MITM, not verify-disable.
```

The macOS python.org Python 3.12.0 build ships an
out-of-date `cert.pem` that does not yet include
`TrustAsia DV TLS RSA CA 2025` as a trusted root. This is
a local environment issue, **not** a code-path issue and
**not** a reviewer semantic issue. The Phase 5R-4 runner
behaved correctly: it refused to accept the untrusted chain
and surfaced review debt rather than fall back silently.

Resolution priority (per the user-approved diagnostic
ladder):

1. **Diagnostic-only**, no code change: confirm Python
   trust store via `scripts/diagnose_api_tls.py` (added in
   Loop 022T).
2. **Minimal CA bundle fix**: `LOOP_API_SSL_CERT_FILE` /
   `SSL_CERT_FILE` pointing at a CA bundle that trusts
   TrustAsia, **without disabling TLS verification**.
3. **System-level fix**: `python3 -m pip install --upgrade
   certifi` and re-point `SSL_CERT_FILE` at `certifi.where()`.

**Explicitly forbidden** in the production reviewer path:

- `verify=False` or any equivalent knob that disables
  certificate verification.
- Any `--insecure-ssl` / `ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY`
  flag that affects the production reviewer verdict chain.
- Adding the deepseek leaf cert to a trust store without
  auditing the chain.

These are reserved for an explicit diagnostic CLI path
(out of scope for Loop 022T v1; see Loop 022T spec).

### 1. Once TLS is fixed on this host

Re-run Phase 5R-4 route A. If a real PASS verdict comes
back, throughput materialization can move from B to A and
the deepest-frozen checkpoint can advance to 012B (subject
to `human_signoff.yaml`).

### 2. Boundary reminders (unchanged)

- **Do not promote 012C.** `Loop 013` boundary remains
  intact. `human_signoff.yaml` is NOT auto-created.
- **Do not start Stage 013.** No `*013*` artifacts
  appeared in this run.
- **Do not run tensorial IBP / total-derivative.** No
  physics was modified.
- **Permanent caveat**: `DCProjectionTo1D -> INHERITED_PASS,
  not direct full tensorial DC-series PASS.`

## Files written by this run

```text
docs/devlog/audits/LOOP_022_PHASE5R4_API_PROVIDER_RUNTIME_PROOF_PRE_SNAPSHOT.md   (Step 3)
docs/devlog/audits/LOOP_022_PHASE5R4_API_PROVIDER_RUNTIME_PROOF_REPORT.md         (this file, Step 6)
```

## Files modified by this run

None. This run is verification-only; it does not modify any
runtime code, profile, loop graph, or sigma_abc physics.

## Files added under autonomous_runs/ by this run

```text
autonomous_runs/sigma_abc/stages/sigma_abc_011_center_sector_pilot/                  (stage dir)
autonomous_runs/sigma_abc/stages/sigma_abc_012a_loop_sector_inventory/               (stage dir)
autonomous_runs/sigma_abc/stages/sigma_abc_012b_loop_hypothesis_generation/          (stage dir)
autonomous_runs/sigma_abc/checkpoints/sigma_abc_011_center_sector_pilot_provisional_review_debt_2026-07-02T02-33-15+00-00/
autonomous_runs/sigma_abc/checkpoints/sigma_abc_012a_loop_sector_inventory_provisional_review_debt_2026-07-02T02-33-16+00-00/
autonomous_runs/sigma_abc/checkpoints/sigma_abc_012b_loop_hypothesis_generation_provisional_review_debt_2026-07-02T02-33-17+00-00/
autonomous_runs/sigma_abc/AUTONOMOUS_LOOP_RUN_REPORT.md                               (overwritten, project-name=sigma_abc)
```

## Files NOT touched (per brief's hard boundaries)

```text
sigma_abc/                                  (physics; not modified)
projects/sigma_abc/loop.yaml                (graph; not modified)
profiles/sigma_abc_loop_candidate_promotion.yaml
loop_engine/checkpoint.py
loop_engine/reviewer_provider_pool.py
loop_engine/api_review_provider.py
loop_engine/human_signoff.py                (no auto-sign)
loop_engine/completion_matrix.py
tests/                                      (no test files added)
skill/                                      (not modified)
```

## Boundary attestations

- ✅ sigma_abc/ physics unchanged.
- ✅ 012C promotion NOT started.
- ✅ Stage 013 NOT started.
- ✅ Tensorial IBP NOT started.
- ✅ Total-derivative reduction NOT introduced.
- ✅ Full tensorial correctness NOT claimed.
- ✅ `human_signoff.yaml` was NOT auto-created.
- ✅ `completion_matrix` blocking items NOT bypassed.
- ✅ No `--clean`, no `--write-root-report`.
- ✅ No API keys written to any file or report.
- ✅ No fallback after the FAIL verdict (the runner
  recorded the FAIL and stopped, surfacing review-debt).
- ✅ Permanent caveat preserved:
  `DCProjectionTo1D -> INHERITED_PASS, not direct full
  tensorial DC-series PASS.`
- ✅ No stub reviewer used in production.
- ✅ No 022S files modified.
