from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .config import relative_to_repo, write_json


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_protected_files(paths: list[Path]) -> dict[str, str | None]:
    snapshot: dict[str, str | None] = {}
    for path in paths:
        snapshot[str(path)] = file_sha256(path) if path.exists() else None
    return snapshot


def verify_read_only_contract(before: dict[str, str | None]) -> dict[str, Any]:
    changed: list[str] = []
    for raw_path, old_hash in before.items():
        path = Path(raw_path)
        new_hash = file_sha256(path) if path.exists() else None
        if new_hash != old_hash:
            changed.append(relative_to_repo(path))
    return {
        "ReviewerModifiedProtectedFiles": bool(changed),
        "ModifiedProtectedFiles": changed,
        "Decision": "HARD_STOP" if changed else "PASS",
    }


def write_invocation_summary(evidence_dir: Path, summary: dict[str, Any]) -> Path:
    target = evidence_dir / "invocation_summary.json"
    write_json(target, summary)
    return target
