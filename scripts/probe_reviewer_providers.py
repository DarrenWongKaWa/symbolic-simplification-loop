#!/usr/bin/env python3
"""Loop 021 — probe reviewer providers for a reviewer role.

Reports which providers are configured, enabled, available, and
which one the pool would select. Reports go to
``archive/local_runs/<UTC-timestamp>_PROBE_REVIEWER_PROVIDERS.md``,
NOT to the repo root.

Examples:

    python3 scripts/probe_reviewer_providers.py \
      --role ScientificMetaReviewer
    python3 scripts/probe_reviewer_providers.py \
      --role ScientificMetaReviewer --write-root-report

The probe does NOT invoke any provider. It only walks the
provider pool config, checks env vars, and prints a report.
Secrets are redacted before any output is written.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from loop_engine.config import REPO_ROOT, write_text
from loop_engine.reviewer_provider_pool import (
    _check_provider_availability,
    _is_provider_enabled,
)
from loop_engine.secret_redaction import redact_secrets


def _read_pool_cfg(role: str) -> dict | None:
    """Read the provider pool config for a role.

    Walks ``agents/runtime.local.example.yaml`` if
    ``agents/runtime.local.yaml`` is absent (the example file is
    committed and may be used as the de-facto config until the
    user creates their local override).
    """
    # Best-effort: surface `.env`-provided env vars BEFORE we read
    # provider availability, so probes see what the runner would
    # see. Without this call the probe would only see env vars
    # propagated by the calling shell, not those from the local
    # gitignored `.env`.
    from loop_engine.config import load_dotenv

    load_dotenv()
    import yaml

    for path in [
        REPO_ROOT / "agents" / "runtime.local.yaml",
        REPO_ROOT / "agents" / "runtime.local.example.yaml",
    ]:
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            continue
        profiles = data.get("profiles", {}) or {}
        for profile_name, profile_cfg in profiles.items():
            pool = (profile_cfg or {}).get("reviewer_provider_pools", {}) or {}
            if role in pool:
                return pool[role]
        # If we read the example file and the role isn't there, fall
        # through. Otherwise the example file is the only source.
        if path.name == "runtime.local.yaml":
            break
    return None


def _format_pool_report(role: str, pool_cfg: dict | None) -> str:
    if pool_cfg is None:
        return (
            f"# Reviewer Provider Probe\n\n"
            f"role: `{role}`\n"
            f"pool: **NOT CONFIGURED**\n\n"
            f"No `reviewer_provider_pools.<role>` entry found in\n"
            f"`agents/runtime.local.yaml` or\n"
            f"`agents/runtime.local.example.yaml`.\n"
        )
    lines: list[str] = []
    lines.append(f"# Reviewer Provider Probe\n\nrole: `{role}`\n")
    lines.append(
        f"fallback_policy: `{pool_cfg.get('fallback_policy', 'runtime_failure_only')}`\n"
        f"require_real_provider: `{pool_cfg.get('require_real_provider', True)}`\n"
        f"forbid_stub: `{pool_cfg.get('forbid_stub', True)}`\n"
    )
    providers = pool_cfg.get("providers", []) or []
    if not providers:
        lines.append("\nproviders: **EMPTY**\n")
        return "\n".join(lines) + "\n"
    for idx, p in enumerate(providers):
        name = p.get("name", "?")
        adapter = p.get("adapter", "?")
        enabled, why = _is_provider_enabled(p)
        availability, runtime = _check_provider_availability(p)
        lines.append(f"## {idx}. `{name}` (adapter: `{adapter}`)\n")
        lines.append(f"- enabled: `{enabled}` (reason: `{why}`)\n")
        lines.append(f"- availability_status: `{availability}`\n")
        lines.append(f"- runtime_status: `{runtime}`\n")
        # Redact api_key just in case.
        redacted = redact_secrets(repr(p))
        lines.append(f"- config: {redacted}\n")
        lines.append("\n")
    return "\n".join(lines) + "\n"


def _resolve_report_path(args: argparse.Namespace, role: str) -> Path:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H-%M-%S+00-00"
    )
    base_name = f"{ts}_PROBE_REVIEWER_PROVIDERS_{role}.md"
    if getattr(args, "write_root_report", False):
        return REPO_ROOT / base_name
    return (
        REPO_ROOT
        / "archive"
        / "local_runs"
        / base_name
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe reviewer providers for a reviewer role."
    )
    parser.add_argument(
        "--role",
        default="ScientificMetaReviewer",
        help="Reviewer role to probe (default: ScientificMetaReviewer).",
    )
    parser.add_argument(
        "--write-root-report",
        action="store_true",
        help=(
            "Additionally emit a copy at REPO_ROOT / <basename>. "
            "Off by default; reports go to archive/local_runs/."
        ),
    )
    args = parser.parse_args()

    pool_cfg = _read_pool_cfg(args.role)
    report_text = _format_pool_report(args.role, pool_cfg)
    target = _resolve_report_path(args, args.role)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_text(target, report_text)
    print(report_text)
    print(f"--- report written to: {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
