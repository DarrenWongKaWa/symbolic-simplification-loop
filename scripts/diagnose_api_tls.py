#!/usr/bin/env python3
"""Loop 022T — diagnose TLS trust for the API review provider base URL.

This script is a **read-only diagnostic** for the same TLS path
the `loop_engine.api_review_provider` adapters use. It does
NOT send any chat / completion request and does NOT require
an API key.

Usage:

    python3 scripts/diagnose_api_tls.py --base-url "$OPENAI_COMPATIBLE_BASE_URL"
    python3 scripts/diagnose_api_tls.py --base-url https://api.deepseek.com

Output is a short textual report (one section per check) and
an exit code:

    0  TLS_OK                          host reachable, chain valid
    2  TLS_CERT_VERIFY_FAILED          chain rejected by Python
    3  TLS_PROXY_OR_SELF_SIGNED_CHAIN_SUSPECTED  issuer looks like a MITM
    4  TLS_NETWORK_FAILURE             DNS / TCP / timeout
    5  USAGE_ERROR                     bad invocation
    6  BAD_BASE_URL                    URL not parseable / wrong scheme

No secret value is ever printed. Proxy URLs that contain
``user:pass@`` are redacted in display output.

This script NEVER touches ``sigma_abc/``, never starts the
autonomous loop, never writes any disk artifact other than
the textual report on stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


# ---- helpers ---------------------------------------------------------


_USER_PASS_RE = re.compile(r"(://)([^/@:]+):([^/@]+)(@)")


def _redact_url(url: str) -> str:
    """Redact user:pass@ in any URL. Keeps host + path intact."""
    if not url:
        return url
    return _USER_PASS_RE.sub(r"\1<user>:<pass>@\4", url)


def _safe_host_for_display(parsed: urllib.parse.ParseResult) -> str:
    """host:port only. Never include userinfo or query string."""
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return f"{host}:{port}"


def _print_section(title: str) -> None:
    print()
    print(f"=== {title} ===")


# ---- probes ----------------------------------------------------------


def _probe_env() -> dict[str, Any]:
    """Read proxy + CA bundle env vars without printing sensitive values.

    Returns a dict that may be JSON-serialised for machine
    consumption.
    """
    keys = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
        "LOOP_API_SSL_CERT_FILE",
    )
    found: dict[str, str] = {}
    for k in keys:
        if k in os.environ:
            v = os.environ[k]
            found[k] = _redact_url(v) if "://" in v else v
    return found


def _probe_python_ssl_defaults() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "default_verify_paths": ssl.get_default_verify_paths()._asdict()
        if hasattr(ssl.get_default_verify_paths(), "_asdict")
        else str(ssl.get_default_verify_paths()),
    }


def _issuer_subject_from_openssl(host: str, port: int) -> tuple[str | None, str | None]:
    """Return (issuer, subject) as strings by shelling out to
    ``openssl s_client`` (no chat call; just the handshake +
    certificate). Returns (None, None) if openssl is missing
    or fails.
    """
    try:
        completed = subprocess.run(
            [
                "openssl",
                "s_client",
                "-connect",
                f"{host}:{port}",
                "-servername",
                host,
                "-showcerts",
            ],
            input="",
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, None
    blob = completed.stdout
    if not blob:
        return None, None
    # Walk every cert block and grab the last issuer/subject;
    # the chain's leaf subject is what matters for the host.
    issuers = re.findall(r"^issuer= ?(.*)$", blob, flags=re.MULTILINE)
    subjects = re.findall(r"^subject= ?(.*)$", blob, flags=re.MULTILINE)
    return (issuers[0] if issuers else None), (subjects[0] if subjects else None)


def _looks_like_mitm(issuer: str | None) -> bool:
    """Heuristic: flag issuer strings that contain names commonly
    associated with local proxies / MITM tools. Conservative —
    false positives are fine for a diagnostic.
    """
    if not issuer:
        return False
    lowered = issuer.lower()
    markers = (
        "charles",
        "clash",
        "surge",
        "mitmproxy",
        "fiddler",
        "burp",
        "squid",
        "company",
        "corporate",
        "internal ca",
        "self-signed",
        "localhost",
        "127.0.0.1",
    )
    return any(m in lowered for m in markers)


def _probe_https(host: str, port: int) -> tuple[str, dict[str, Any]]:
    """Run an HTTPS GET against ``https://host:port/`` and classify.

    Returns ``(classification, details)``. Never raises.
    Never sends an API-key-bearing header.
    """
    details: dict[str, Any] = {
        "url": _redact_url(f"https://{host}:{port}/"),
    }
    url = f"https://{host}:{port}/"
    req = urllib.request.Request(url, method="GET")
    # No Authorization header; we only want to exercise TLS.
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            details["status"] = resp.status
            details["peer"] = _redact_url(str(resp.geturl()))
            details["via"] = "python.urllib"
            return "TLS_OK", details
    except urllib.error.HTTPError as exc:
        # HTTPError is reachable; the TLS handshake succeeded.
        details["status"] = exc.code
        details["reason"] = str(exc.reason)
        details["via"] = "python.urllib (HTTPError after TLS)"
        return "TLS_OK", details
    except urllib.error.URLError as exc:
        reason = str(exc.reason)
        details["reason"] = reason
        details["via"] = "python.urllib (URLError)"
        if "CERTIFICATE_VERIFY_FAILED" in reason or "certificate verify" in reason.lower():
            return "TLS_CERT_VERIFY_FAILED", details
        if "self-signed" in reason.lower():
            return "TLS_CERT_VERIFY_FAILED", details
        return "TLS_NETWORK_FAILURE", details
    except (TimeoutError, socket.timeout):
        details["reason"] = "timeout"
        return "TLS_NETWORK_FAILURE", details
    except OSError as exc:
        details["reason"] = str(exc)
        return "TLS_NETWORK_FAILURE", details


# ---- classification & reporting -------------------------------------


_CLASSIFICATION_HINTS: dict[str, str] = {
    "TLS_OK": "TLS chain is valid from this Python interpreter.",
    "TLS_CERT_VERIFY_FAILED": (
        "Python's trust store does not trust the chain. The issuer may be "
        "a public CA not yet bundled in this Python build, or a self-signed "
        "cert. Suggested actions: (1) pip install --upgrade certifi and set "
        "SSL_CERT_FILE=$(python3 -c 'import certifi;print(certifi.where())'); "
        "(2) or set LOOP_API_SSL_CERT_FILE to a CA bundle that trusts the "
        "chain; (3) NEVER set verify=False in the production reviewer path."
    ),
    "TLS_PROXY_OR_SELF_SIGNED_CHAIN_SUSPECTED": (
        "Issuer name matches a known MITM proxy / company-CA pattern. "
        "If you intentionally use a corporate proxy, configure the proxy's "
        "CA via LOOP_API_SSL_CERT_FILE / SSL_CERT_FILE rather than disabling "
        "TLS verification."
    ),
    "TLS_NETWORK_FAILURE": (
        "Network-level failure (DNS / TCP / timeout). Re-check connectivity, "
        "proxy settings, or whether the host is reachable."
    ),
}


def _classify(issuer: str | None, primary: str) -> str:
    if primary == "TLS_OK":
        return "TLS_OK"
    if primary == "TLS_CERT_VERIFY_FAILED" and _looks_like_mitm(issuer):
        return "TLS_PROXY_OR_SELF_SIGNED_CHAIN_SUSPECTED"
    return primary


def _suggest(base_url: str) -> list[str]:
    """Actionable next-step hints. No key / no path printing."""
    return [
        f"python3 scripts/diagnose_api_tls.py --base-url {base_url}",
        # Operational hints without leaking values.
        "If TLS_CERT_VERIFY_FAILED: pip install --upgrade certifi",
        "If proxy/MITM: import proxy CA into system trust store",
    ]


def _emit_report(*, base_url: str, classification: str, details: dict[str, Any]) -> None:
    summary = {
        "base_url": _redact_url(base_url),
        "classification": classification,
        "hint": _CLASSIFICATION_HINTS.get(classification, ""),
        "details": details,
        "suggested_next": _suggest(base_url),
    }
    print()
    print("=== Summary ===")
    print(json.dumps(summary, indent=2, sort_keys=True))


# ---- main ------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL whose TLS trust we want to probe (e.g. https://api.deepseek.com)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the final summary as JSON on the last line only.",
    )
    args = parser.parse_args(argv)

    raw = args.base_url.strip()
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme != "https" or not parsed.hostname:
        _print_section("base url")
        print(f"bad base url (need https://host[:port]): {_redact_url(raw)}")
        return 6

    host = parsed.hostname
    port = parsed.port or 443

    _print_section("base url")
    print(f"host:port = {_safe_host_for_display(parsed)}")
    print(f"redacted  = {_redact_url(raw)}")

    env = _probe_env()
    _print_section("env (proxy + CA bundle)")
    if env:
        for k, v in env.items():
            print(f"{k}={v}")
    else:
        print("(none set)")

    py = _probe_python_ssl_defaults()
    _print_section("python ssl defaults")
    print(f"python               = {py['python']}")
    print(f"default_verify_paths = {py['default_verify_paths']}")

    _print_section("openssl issuer/subject")
    issuer, subject = _issuer_subject_from_openssl(host, port)
    if issuer is None and subject is None:
        print("(openssl s_client unavailable or failed)")
    else:
        print(f"issuer  = {issuer}")
        print(f"subject = {subject}")

    _print_section("python urllib TLS probe")
    primary, details = _probe_https(host, port)
    classification = _classify(issuer, primary)
    for k, v in sorted(details.items()):
        print(f"{k} = {v}")
    print(f"primary classification = {primary}")
    if classification != primary:
        print(f"refined classification = {classification}")
    print(f"hint                   = {_CLASSIFICATION_HINTS.get(classification, '')}")

    _emit_report(
        base_url=raw,
        classification=classification,
        details={
            "primary": primary,
            "issuer": issuer,
            "subject": subject,
            "probe": details,
        },
    )

    code_map = {
        "TLS_OK": 0,
        "TLS_CERT_VERIFY_FAILED": 2,
        "TLS_PROXY_OR_SELF_SIGNED_CHAIN_SUSPECTED": 3,
        "TLS_NETWORK_FAILURE": 4,
    }
    return code_map.get(classification, 1)


if __name__ == "__main__":
    raise SystemExit(main())