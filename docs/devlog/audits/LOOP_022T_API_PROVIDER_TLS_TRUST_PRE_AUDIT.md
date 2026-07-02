# Loop 022T — API Provider TLS Trust — Pre-Audit

Date: 2026-07-02
Project: `symbolic-simplification-loop`
Predecessor: Phase 5R-4 (`LOOP_022_PHASE5R4_API_PROVIDER_RUNTIME_PROOF_REPORT.md`)

## 0. Why this loop exists

Phase 5R-4 proved the live runner → ProviderPoolAdapter →
`openai_compatible_api` dispatch path is **open** and a real
HTTP request reached `https://api.deepseek.com`. However the
reviewer verdict was NOT obtained because Python's TLS
handshake failed at the deepseek endpoint:

```text
URLError: [SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: self-signed certificate in certificate chain
```

A read-only preflight (recorded in the Phase 5R-4 report)
confirmed the failure is a **local Python trust store**
issue, NOT a network / MITM / code-path issue:

| Check | Result |
| --- | --- |
| `HTTP_PROXY` / `HTTPS_PROXY` env | not set |
| `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` env | not set |
| `curl -Iv https://api.deepseek.com` | `SSL certificate verify ok`, HTTP/2 401 |
| `openssl issuer` | `TrustAsia DV TLS RSA CA 2025` (public CA) |
| `python3 urllib.request.urlopen` | `TLS_FAIL: CERTIFICATE_VERIFY_FAILED` |

The macOS python.org Python 3.12.0 ships an out-of-date
`cert.pem` that does not yet trust `TrustAsia DV TLS RSA
CA 2025`. curl uses `/etc/ssl/cert.pem` which is current.

## 1. Scope of Loop 022T (narrow, per user approval)

```text
diagnose_api_tls.py
LOOP_API_SSL_CERT_FILE
SSL_CERT_FILE support
TLS failure classification
tests proving verify remains enabled
```

**NOT** in scope for v1 (explicitly out):

- `verify=False` / any insecure-SSL knob in the production
  reviewer path
- `ALLOW_INSECURE_SSL_FOR_LOCAL_DIAGNOSTIC_ONLY`
- touching sigma_abc physics
- 012C promotion / Stage 013 / tensorial IBP / total-derivative
- auto-creating `human_signoff.yaml`
- bypassing `completion_matrix`
- writing API keys to any file or report
- fallback after semantic FAIL / NEEDS_PATCH

## 2. Audit: `loop_engine/api_review_provider.py`

### 2.1 File role

Provides the three non-command adapters the Phase-5R-4 pool
dispatches:

- `invoke_anthropic_api` (URL constant: `https://api.anthropic.com/v1/messages`)
- `invoke_openai_api` (URL constant: `https://api.openai.com/v1/chat/completions`)
- `invoke_openai_compatible_api` (URL: `OPENAI_COMPATIBLE_BASE_URL` env var)

All three call `_call_api(...)` to do the HTTP POST.

### 2.2 How urllib / ssl context is created (the gap)

`_call_api` (`api_review_provider.py:102-129`) is the only
HTTP transport entry point:

```python
req = urllib.request.Request(url, data=body, headers=headers, method="POST")
try:
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        ...
except urllib.error.URLError as exc:
    return (599, "", f"URLError: {exc.reason}")
```

It uses `urllib.request.urlopen` with **no SSL context**.

Concretely:

- Python's default behavior for `urlopen` is to use the
  default SSL context (`ssl.create_default_context()`),
  which loads the certs from `ssl.get_default_verify_paths()`
  (= `/Library/Frameworks/Python.framework/Versions/3.12/etc/openssl/cert.pem`
  on this host).
- The default context **does** honor `SSL_CERT_FILE` for the
  cert store location, but only when set via `ssl.SSLContext.load_verify_locations`
  — `urllib.request.urlopen` without an explicit `context=`
  argument does NOT read `SSL_CERT_FILE` as a per-call override
  on the default context in some Python versions; this is
  implementation-dependent.
- There is no `cafile=`, no `capath=`, no explicit
  `ssl.SSLContext`.

### 2.3 How `OPENAI_COMPATIBLE_BASE_URL` is used

- Constant: `OPENAI_COMPATIBLE_DEFAULT_BASE_URL` in
  `api_review_provider.py:237` (only used when env is empty;
  not relevant to current config which sets the env var).
- Resolved in `reviewer_provider_pool.py::_resolve_base_url`
  via `base_url_env: OPENAI_COMPATIBLE_BASE_URL`.
- Passed into `invoke_openai_compatible_api(..., base_url=...)`
  and then to `_call_api(url=base_url, ...)`.

No transformation, no validation, no scheme check. Good —
we don't need to touch the URL resolution.

### 2.4 Whether `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` / `CURL_CA_BUNDLE` are honored today

| Env var | Honored by `urlopen` w/o context? | Honored after Step 2? |
| --- | --- | --- |
| `SSL_CERT_FILE` | No (no context argument) | **YES** — `ssl.SSLContext.load_verify_locations(cafile=os.environ["LOOP_API_SSL_CERT_FILE"] or os.environ["SSL_CERT_FILE"])` |
| `REQUESTS_CA_BUNDLE` | n/a (we don't use `requests`) | NO — documented as not used |
| `CURL_CA_BUNDLE` | n/a (we don't use `curl`) | NO — documented as not used |
| `LOOP_API_SSL_CERT_FILE` | No (custom) | **YES** — preferred override |

### 2.5 Where stderr / error text is written

- `_call_api` returns `(status_code, payload, stderr_text)`
  where `stderr_text` is the exception reason (e.g.
  `"URLError: [SSL: CERTIFICATE_VERIFY_FAILED] ..."`).
- `_record_invocation` writes `api_attempt.json` with the
  redacted `api_key`, `base_url`, `model`, and `summary_extra`
  (status, stderr).
- `_classify_api_response` writes the same text into
  `failure_summary_redacted=redact_secrets(f"status={status_code}; stderr={stderr_text[:200]}")`.
  Redaction runs (`secret_redaction.redact_secrets`) before
  disk write ✓.

The TLS failure text DOES contain information that helps the
operator diagnose the issue (e.g.
`self-signed certificate in certificate chain`). After Step 3
it will also include a hint pointing at `diagnose_api_tls.py`.

### 2.6 Whether secrets are redacted

Yes — `secret_redaction.redact_secrets` is called on every
disk write in this module. The TLS error text itself does
not contain secrets (no API key, no Authorization header).
After Step 3 we will additionally check that any new fields
added to the error context are redacted.

### 2.7 Current Phase 5R-4 SSL evidence

Verbatim from
`autonomous_runs/sigma_abc/checkpoints/sigma_abc_011_center_sector_pilot_provisional_review_debt_*/.loop/agent_invocations/ScientificMetaReviewer/api_attempt.json`:

```text
api_key_redacted: <redacted:API_KEY>
base_url:         https://api.deepseek.com
model:            deepseek-v4-pro
provider_name:    openai_compatible_api
summary_extra:
  status:  599
  stderr:  URLError: [SSL: CERTIFICATE_VERIFY_FAILED]
           certificate verify failed: self-signed certificate in chain
```

`review_debt_required=True`,
`secret_redaction_applied=True`,
`selected_provider=None`,
`runtime_status=AGENT_TRANSPORT_FAILURE`,
`pool_retryable=True`.

## 3. Audit: `loop_engine/reviewer_provider_pool.py`

Pool-level behavior is **unchanged** by Loop 022T. The only
thing that changes is what `_run_api_provider` receives from
`api_review_provider.py::_call_api`:

- before: `URLError: CERTIFICATE_VERIFY_FAILED ...`
  → `runtime_status=AGENT_TRANSPORT_FAILURE`
- after (Step 3): same `runtime_status`, same
  `runtime_status=AGENT_TRANSPORT_FAILURE`, **plus** a
  redacted hint appended to `failure_summary_redacted` like
  `"diagnose: python3 scripts/diagnose_api_tls.py --base-url https://api.deepseek.com"`.

No change to:
- `_detect_quota_or_timeout` precedence (quota keywords
  still win)
- `_run_api_provider` dispatch logic
- `run_pool` candidate ordering
- `forbid_stub`, `require_real_provider`, `secret_redaction_applied`

## 4. Audit: `tests/test_loop022s_api_provider_runtime_integration.py`

Read (not modified by Loop 022T). Confirms the adapter
dispatch contract Loop 022T must preserve:

- `pool_cfg` contains `openai_compatible_api` adapter
- `_run_api_provider` calls `invoke_openai_compatible_api`
- missing key → `runtime_status=AGENT_RUNTIME_FAILURE` (not
  `AGENT_TRANSPORT_FAILURE`)
- pool result retains `secret_redaction_applied=True`

These are exactly the contract Loop 022T tests must
preserve.

## 5. Insertion points for Loop 022T

| Step | File | Insertion point |
| --- | --- | --- |
| Step 1 (diagnostic script) | `scripts/diagnose_api_tls.py` | new file |
| Step 2 (CA bundle support) | `loop_engine/api_review_provider.py` | new `_build_ssl_context()` helper called by `_call_api` |
| Step 3 (TLS failure classification) | `loop_engine/api_review_provider.py` | new `_diagnostic_hint_for_stderr(stderr_text)` helper called by `_classify_api_response` for `AGENT_TRANSPORT_FAILURE` cases |
| Step 4 (tests) | `tests/test_loop022t_api_provider_tls_trust.py` | new file |
| Step 6 (report) | `docs/devlog/audits/LOOP_022T_API_PROVIDER_TLS_TRUST_REPORT.md` | new file |

## 6. Risk analysis

| Risk | Mitigation |
| --- | --- |
| Accidentally weaken TLS in production | `verify_mode` is hardcoded `ssl.CERT_REQUIRED` in `_build_ssl_context`; monkeypatch test asserts it. |
| Accidentally leak API key in TLS error context | All new error text is static, parameter-free, no substitution of secrets. |
| Accidentally regress Phase 5R-4 (which already proved the dispatch path) | Loop 022S tests stay at 18/18. Step 4 tests do NOT call the network. |
| Touching physics | `sigma_abc/` not in insertion points; forbidden scan in Step 5. |
| Auto-creating `human_signoff.yaml` | `loop_engine/human_signoff.py` not in insertion points. |

## 7. Next safe action

Proceed to Step 1: write `scripts/diagnose_api_tls.py`.