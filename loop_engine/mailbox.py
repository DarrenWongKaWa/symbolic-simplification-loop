from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .config import utc_now, write_json


ACTORS = [
    "main_executor",
    "verifier_agent",
    "algebra_reviewer",
    "physics_reviewer",
    "software_reviewer",
    "review_aggregator",
    "scientific_metareviewer",
    "stage_digest_builder",
    "digest_reviewer",
    "decision_engine",
    "patch_planner",
]


def mailbox_root(stage: Path) -> Path:
    return stage / ".loop" / "mailbox"


def attempt_name(attempt: int) -> str:
    return f"attempt_{attempt:03d}"


def initialize_mailbox(stage: Path, stage_id: str, attempt: int = 1) -> Path:
    root = mailbox_root(stage)
    attempt_root = root / attempt_name(attempt)
    for actor in ACTORS:
        (attempt_root / actor).mkdir(parents=True, exist_ok=True)
    state = {
        "stage_id": stage_id,
        "current_attempt": attempt,
        "status": "INITIALIZED",
        "attempts": [attempt],
        "AgentRuntimeStatus": "STUB_FOR_TESTS_OR_LOCAL_STRUCTURED",
    }
    write_json(root / "state.json", state)
    (root / "events.jsonl").parent.mkdir(parents=True, exist_ok=True)
    if not (root / "events.jsonl").exists():
        (root / "events.jsonl").write_text("", encoding="utf-8")
    return root


def mailbox_state(stage: Path) -> dict[str, Any]:
    with (mailbox_root(stage) / "state.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _hash_path(stage: Path, rel_path: str) -> str | None:
    path = stage / rel_path
    if not path.exists() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_event(
    stage: Path,
    stage_id: str,
    attempt: int,
    actor: str,
    event_type: str,
    input_paths: list[str],
    output_paths: list[str],
    summary: str,
) -> dict[str, Any]:
    hashes = {
        rel: digest
        for rel in [*input_paths, *output_paths]
        if (digest := _hash_path(stage, rel)) is not None
    }
    event = {
        "timestamp": utc_now(),
        "stage_id": stage_id,
        "attempt": attempt,
        "actor": actor,
        "event_type": event_type,
        "input_paths": input_paths,
        "output_paths": output_paths,
        "hashes": hashes,
        "summary": summary,
    }
    events_path = mailbox_root(stage) / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event
