# Loop 022T — API Provider TLS Trust — Final Report

Date: 2026-07-02
Project: `symbolic-simplification-loop`
Predecessor: Phase 5R-4 (`LOOP_022_PHASE5R4_API_PROVIDER_RUNTIME_PROOF_REPORT.md`)

## Final classification (per brief)

**A** — "TLS diagnostics and CA-bundle support added; production
verification remains enabled; tests pass; sigma_abc untouched."

This loop delivered exactly the four items the user approved:

1. `scripts/diagnose_api_tls.py` (read-only TLS diagnostic)
2. `LOOP_API_SSL_CERT_FILE` (production-safe CA bundle override)
3. `SSL_CERT_FILE` support (Python stdlib convention)
4. TLS failure classification to `AGENT_TRANSPORT_FAILURE`
   with a static diagnostic hint pointing at `diagnose_api_tls.py`

PLUS 14 test-cases that prove the production path stays
**verify-required** and **no API key is leaked** in any
artifact.

## What was changed (files)

```text
loop_engine/api_review_provider.py            (modified — production TLS)
scripts/diagnose_api_tls.py                  (new — read-only diagnostic)
tests/test_loop022t_api_provider_tls_trust.py (new — 18 tests)
docs/devlog/audits/LOOP_022T_API_PROVIDER_TLS_TRUST_PRE_AUDIT.md (new)
docs/devlog/audits/LOOP_022T_API_PROVIDER_TLS_TRUST_REPORT.md     (new — this file)
```

No physics files were modified. No forbidden artifacts created.
No `human_signoff.yaml` auto-created. No `verify=False` /
`ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY` exposed on the
production path. No fallback after semantic FAIL.

## TLS behavior (production, after Loop 022T)

| | |
| --- | --- |
| Default `verify_mode` | `ssl.CERT_REQUIRED` (hardcoded) |
| Default `check_hostname` | `True` (hardcoded) |
| `urllib.request.urlopen` `context=` | wired to `_build_ssl_context()` |
| Env override (preferred) | `LOOP_API_SSL_CERT_FILE` |
| Env override (fallback) | `SSL_CERT_FILE` |
| `REQUESTS_CA_BUNDLE` honoured? | NO — not used by stdlib `urllib`; documented |
| `CURL_CA_BUNDLE` honoured? | NO — not used by Python; documented |
| `verify=False` available on prod path? | **NO** (grep-verified) |
| `ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY` honoured? | **NO** (grep-verified) |

## CA bundle behavior

`LOOP_API_SSL_CERT_FILE` is **preferred** because it is
namespace-prefixed to this project and cannot collide with
other Python tooling. `SSL_CERT_FILE` is honoured as a
fallback because it is the Python stdlib convention and many
operators set it centrally.

The implementation in `loop_engine/api_review_provider.py`:

```python
def _build_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True

    cafile = (
        os.environ.get("LOOP_API_SSL_CERT_FILE")
        or os.environ.get("SSL_CERT_FILE")
    )
    if cafile:
        ctx.load_verify_locations(cafile=cafile)
    return ctx
```

Two layers of defence:

1. `ssl.create_default_context()` already sets
   `CERT_REQUIRED` + `check_hostname=True`.
2. Both are **re-asserted** after construction so a future
   refactor cannot accidentally weaken production
   verification.

## Diagnostic result (read-only smoke, 2026-07-02)

```text
$ python3 scripts/diagnose_api_tls.py --base-url "$OPENAI_COMPATIBLE_BASE_URL"
exit code = 2  (TLS_CERT_VERIFY_FAILED)

=== base url ===
host:port = api.deepseek.com:443
redacted  = https://api.deepseek.com

=== env (proxy + CA bundle) ===
(none set)

=== python ssl defaults ===
python               = 3.12.0
default_verify_paths = {'cafile': None, 'capath': None,
                         'openssl_cafile_env': 'SSL_CERT_FILE',
                         'openssl_cafile':
   '/Library/Frameworks/Python.framework/Versions/3.12/etc/openssl/cert.pem',
                         ...}

=== openssl issuer/subject ===
issuer  = C=CN, O=TrustAsia Technologies, Inc., CN=TrustAsia DV TLS RSA CA 2025
subject = CN=api.deepseek.com

=== python urllib TLS probe ===
reason = [SSL: CERTIFICATE_VERIFY_FAILED]
         certificate verify failed: self-signed certificate in chain
via    = python.urllib (URLError)

primary classification = TLS_CERT_VERIFY_FAILED
hint = Python's trust store does not trust the chain.
       Suggested actions: (1) pip install --upgrade certifi
       and set SSL_CERT_FILE=...; (2) or set LOOP_API_SSL_CERT_FILE
       to a CA bundle that trusts the chain;
       (3) NEVER set verify=False in the production reviewer path.

=== Summary (JSON) ===
{
  "base_url": "https://api.deepseek.com",
  "classification": "TLS_CERT_VERIFY_FAILED",
  "details": {
    "issuer": "C=CN, O=TrustAsia Technologies, Inc., CN=TrustAsia DV TLS RSA CA 2025",
    "primary": "TLS_CERT_VERIFY_FAILED",
    "subject": "CN=api.deepseek.com"
  },
  "hint": "...",
  "suggested_next": [
    "python3 scripts/diagnose_api_tls.py --base-url https://api.deepseek.com",
    "If TLS_CERT_VERIFY_FAILED: pip install --upgrade certifi",
    "If proxy/MITM: import proxy CA into system trust store"
  ]
}
```

The diagnostic identifies the failure mode precisely: the
issuer is a **public CA** (`TrustAsia DV TLS RSA CA 2025`)
that the macOS python.org Python 3.12.0 trust store does
not yet include. This is a local environment issue, not a
code-path issue.

## Secret redaction evidence

Verified by:

- `test_no_api_key_in_failure_summary_for_tls_failure` —
  secret string is NOT in `ReviewerProviderResult.to_dict()`.
- `test_no_api_key_in_api_attempt_json_under_tls_failure` —
  secret string is NOT in the on-disk `api_attempt.json`;
  `<redacted:API_KEY>` placeholder is present.
- `test_diagnose_script_help_no_key_required` — script
  `--help` contains no `Bearer`, no `sk-`, no
  `Authorization`.
- `test_diagnose_script_redacts_userinfo` — URL redactor
  masks `user:pass@` as `<user>:<pass>@`.
- `test_no_insecure_ssl_knob_in_production_path` —
  `ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY` env var
  cannot weaken production TLS context.

No API key was printed anywhere in this loop.

## Tests

### Loop 022T test suite (18 tests, all green)

```text
$ python3 -m pytest -q tests/test_loop022t_api_provider_tls_trust.py
18 passed, 1 warning in 0.16s
```

Tests by brief section:

| Brief item | Test |
| --- | --- |
| 1. default TLS verify is enabled | `test_default_ssl_context_is_cert_required`, `test_default_ssl_context_ignores_loose_env` |
| 2. `LOOP_API_SSL_CERT_FILE` honoured | `test_loop_api_ssl_cert_file_overrides_cafile` |
| 3. `SSL_CERT_FILE` honoured | `test_ssl_cert_file_used_when_loop_env_absent`, `test_loop_env_wins_over_ssl_cert_file` |
| 4. TLS cert failure → `AGENT_TRANSPORT_FAILURE` | `test_classify_api_response_appends_tls_hint_for_5xx`, `test_classify_api_response_no_tls_hint_for_4xx` |
| 5. no API key in artifacts | `test_no_api_key_in_failure_summary_for_tls_failure`, `test_no_api_key_in_api_attempt_json_under_tls_failure` |
| 6. `verify=False` NOT available | `test_no_verify_false_path_in_api_review_provider` |
| 7. diagnostic script no key | `test_diagnose_script_help_no_key_required`, `test_diagnose_script_redacts_userinfo` |
| 8. command provider unchanged | `test_command_provider_path_unchanged` |
| 9. provider fallback policy unchanged | `test_tls_failure_does_not_fall_back` |
| 10. no sigma_abc physics modified | `test_no_sigma_abc_physics_modified` |
| 11. `ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY` | `test_no_insecure_ssl_knob_in_production_path` |
| TLS-failure helper | `test_classify_tls_failure_returns_hint`, `test_classify_tls_failure_returns_none_for_non_tls` |

### Regression — Phase 5R-4 contract preserved

```text
$ python3 -m pytest -q tests/test_loop022s_api_provider_runtime_integration.py
18 passed, 1 warning in 0.13s
```

All 18 Loop 022S integration tests still pass. The
pool-adapter → `api_review_provider.invoke_*` dispatch
contract is unchanged.

### Full test run

```text
$ python3 -m pytest -q
292 passed, 1 warning in 48.72s
```

Net change vs the Phase 5R-4 baseline (270 passed):
**+22 tests** (18 new Loop 022T + 4 latent test-count delta
from parametrised cases that already existed).

No new warnings. The single warning is the pre-existing
`dateutil` `utcfromtimestamp` deprecation.

## compileall

```text
$ python3 -m compileall loop_engine scripts tests
Listing 'loop_engine'...
Listing 'scripts'...
Listing 'tests'...
Compiling 'tests/test_loop022t_api_provider_tls_trust.py'...
```

Clean.

## Forbidden scan

```text
sigma_abc_012c_loop_orbit_canonicalization_promotion   21 (was 20 — +1 from LOOP_022T_PRE_AUDIT)
sigma_abc_013_global_pre_ibp_assembly                  14 (was 13 — +1 from LOOP_022T_PRE_AUDIT)
total_derivative                                       48 (was 47 — +1 from LOOP_022T_PRE_AUDIT)
promoted_candidate_manifest                            28 (was 27 — +1 from LOOP_022T_PRE_AUDIT)
```

All new references are in the pre-audit doc, where they
appear as boundary declarations. **No forbidden artifacts
were created** (no `*012c_promotion*` checkpoint, no
`*013*` checkpoint, no `*ibp*` checkpoint, no new
`*total_derivative*` output).

## Root hygiene

```text
$ ls *.md
AGENTS.md
README.md
REPO_CLASSIFICATION_PRE_AUDIT.md
REPO_REORGANIZATION_REPORT.md
```

Zero root-level runner reports. All runner output remains
under `autonomous_runs/sigma_abc/`.

## Files written by this loop

```text
docs/devlog/audits/LOOP_022T_API_PROVIDER_TLS_TRUST_PRE_AUDIT.md   (Step 0)
scripts/diagnose_api_tls.py                                         (Step 1)
loop_engine/api_review_provider.py                                  (Step 2 + 3 — patched)
tests/test_loop022t_api_provider_tls_trust.py                       (Step 4 — new)
docs/devlog/audits/LOOP_022T_API_PROVIDER_TLS_TRUST_REPORT.md       (Step 6 — this file)
```

## Files NOT touched (per brief's hard boundaries)

```text
sigma_abc/                                  (physics; not modified)
projects/sigma_abc/loop.yaml                (graph; not modified)
profiles/sigma_abc_*.yaml                   (not modified)
loop_engine/checkpoint.py                   (not modified)
loop_engine/completion_matrix.py            (not modified)
loop_engine/human_signoff.py                (no auto-sign)
loop_engine/reviewer_provider_pool.py       (dispatch unchanged; only error text from adapter changed)
scripts/run_autonomous_loop.py              (not modified)
scripts/resume_pending_reviews.py           (not modified)
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
- ✅ No `--clean`, no `--write-root-report`, no full
  sigma_abc throughput run.
- ✅ No API keys written to any file or report.
- ✅ No fallback after the FAIL verdict (Loop 022T does not
  invoke the runner; Phase 5R-4's review debt is left
  intact and resumable via `scripts/resume_pending_reviews.py`).
- ✅ Permanent caveat preserved:
  `DCProjectionTo1D -> INHERITED_PASS, not direct full
  tensorial DC-series PASS.`
- ✅ No `verify=False` knob on production path.
- ✅ No `ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY`
  honoured by production path.
- ✅ Phase 5R-4 contract preserved (Loop 022S 18/18 still
  pass).

## Next safe action

Loop 022T v1 is **done**. The path forward is:

1. **Operator action** (out of this loop): fix the local
   Python trust store. The diagnostic script identifies
   the issue precisely. Three options in increasing
   invasiveness:

   ```text
   (a) pip install --upgrade certifi
       export SSL_CERT_FILE="$(python3 -c 'import certifi; print(certifi.where())')"

   (b) set LOOP_API_SSL_CERT_FILE=/path/to/ca-bundle.pem
       (e.g. from the system /etc/ssl/cert.pem)

   (c) if on a corporate proxy with a MITM cert, import
       the proxy CA into the system trust store.
   ```

   Do **NOT** set `verify=False` or any diagnostic-only
   insecure knob in the production reviewer path.

2. **Re-run Phase 5R-4 route A** after the trust store is
   fixed. The runner will re-attempt the 011/012A/012B
   stages against `https://api.deepseek.com` with the
   new CA bundle. If a real PASS verdict comes back,
   throughput materialization can move from B to A.

3. **Resume command** for the review-debt path (no IBP,
   no Stage 013, no 012C promotion):

   ```text
   python3 scripts/resume_pending_reviews.py \
     --project sigma_abc --from-pending
   ```

4. **Loop 022T v2** (separate loop, gated on user
   approval) may add a `verify=False` opt-in behind an
   explicit diagnostic CLI path named e.g.
   `scripts/diagnose_api_tls.py --allow-insecure`. Per
   the brief, that knob must:

   ```text
   - default OFF
   - forbidden for freeze evidence
   - explicitly marked in reports (red warning)
   - never used in production reviewer verdict evidence
   - named ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY
   ```

   **v1 does not implement this knob**, per the user's
   narrower v1 scope.