from __future__ import annotations

"""Artifact-based agent dispatcher (TASK_026 + TASK_027).

Manual-provider-only artifact bus that coordinates handoffs between a
planner, an executor, and a reviewer (think: CodexPlanner -> ClaudeCodeExecutor
-> CodexReviewer) without ever invoking those roles automatically.

Public API surface (all I/O is synchronous and pure-of-side-effects
except where explicitly creating layout/evidence/summary files):

- ``ensure_bus_layout(bus_root) -> dict[str, Path]``
- ``start_round(bus_root, *, next_action_report, round_id=None, ...)``
- ``render_planner_prompt(next_action_report, round_state) -> str``
- ``accept_planner_task(bus_root, *, task_path=None) -> Path``
- ``render_executor_prompt(task_text, round_state) -> str``
- ``accept_executor_report(bus_root, *, executor_report_path=None) -> Path``
- ``collect_git_evidence(repo_root, round_state_dir) -> dict[str, Path]``
- ``collect_acceptance_evidence(round_state_dir, *, commands, no_command_run) -> dict``
- ``render_reviewer_prompt(...) -> str``
- ``accept_reviewer_result(bus_root, *, result_path=None) -> Path``
- ``render_round_summary(...) -> (dict, str)``
- ``needs_human_boundary(...) -> bool``
- ``advance(bus_root, *, repo_root=None, acceptance_commands=None,
            no_command_run=False, force=False, next_action_report=None)``
- ``status(bus_root) -> dict``
- ``summarize_only(bus_root, *, repo_root=None) -> dict``
- ``fail_pending(bus_root, reason: str) -> dict``

Round phases (string enum, see ``schemas/agent_bus_state.schema.json``):

    INIT -> PLANNER_PROMPT_READY -> WAITING_FOR_TASK_SPEC ->
    EXECUTOR_PROMPT_READY -> WAITING_FOR_EXECUTOR_REPORT ->
    REVIEWER_PROMPT_READY -> WAITING_FOR_REVIEW_RESULT ->
    ROUND_SUMMARY_READY (or FAILED)

A round that begins from a human-boundary-classified ``next_action_report``
is short-circuited to ``WAITING_FOR_HUMAN_APPROVAL`` before any planner
prompt is written.

Human-boundary-aware: when the diagnosis or task spec or reviewer result
carries an approval-required signal, the dispatcher routes a summary to
``human/inbox/`` and stops before further automatic action. The dispatcher
itself NEVER freezes checkpoints, mutates signoff ledgers, or invokes the
Codex/Claude CLI.
"""

import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from .config import read_json, read_text, utc_now, write_json, write_text
from .schemas import validate_with_schema


# ---------------------------------------------------------------------------
# Layout + constants
# ---------------------------------------------------------------------------


LAYOUT: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("planner",   ("inbox", "processing", "outbox", "failed")),
    ("executor",  ("inbox", "processing", "outbox", "failed")),
    ("reviewer",  ("inbox", "processing", "outbox", "failed")),
    ("human",     ("inbox", "approved", "rejected")),
    ("round_state", ()),
)


PHASE_INIT                       = "INIT"
PHASE_PLANNER_PROMPT_READY       = "PLANNER_PROMPT_READY"
PHASE_WAITING_FOR_TASK_SPEC      = "WAITING_FOR_TASK_SPEC"
PHASE_EXECUTOR_PROMPT_READY      = "EXECUTOR_PROMPT_READY"
PHASE_WAITING_FOR_EXECUTOR_REPORT = "WAITING_FOR_EXECUTOR_REPORT"
PHASE_REVIEWER_PROMPT_READY      = "REVIEWER_PROMPT_READY"
PHASE_WAITING_FOR_REVIEW_RESULT  = "WAITING_FOR_REVIEW_RESULT"
PHASE_ROUND_SUMMARY_READY        = "ROUND_SUMMARY_READY"
PHASE_WAITING_FOR_HUMAN_APPROVAL = "WAITING_FOR_HUMAN_APPROVAL"
PHASE_FAILED                     = "FAILED"


PHASE_ORDER: tuple[str, ...] = (
    PHASE_INIT,
    PHASE_PLANNER_PROMPT_READY,
    PHASE_WAITING_FOR_TASK_SPEC,
    PHASE_EXECUTOR_PROMPT_READY,
    PHASE_WAITING_FOR_EXECUTOR_REPORT,
    PHASE_REVIEWER_PROMPT_READY,
    PHASE_WAITING_FOR_REVIEW_RESULT,
    PHASE_ROUND_SUMMARY_READY,
    PHASE_WAITING_FOR_HUMAN_APPROVAL,
    PHASE_FAILED,
)


HUMAN_BOUNDARY_NONE         = "NONE"
HUMAN_BOUNDARY_PENDING      = "PENDING_HUMAN"
HUMAN_BOUNDARY_APPROVED     = "APPROVED"
HUMAN_BOUNDARY_REJECTED     = "REJECTED"


# Substrings that, when present in task text, indicate a human approval
# boundary. Kept lowercase; comparison is case-insensitive.
HUMAN_BOUNDARY_TOKENS: tuple[str, ...] = (
    "freeze",
    "ibp",
    "total derivative",
    "tensorial",
    "boundary approval",
    "human scientist",
    "human signoff",
    "human approval",
)


STDOUT_TRUNCATE = 64 * 1024
STDERR_TRUNCATE = 16 * 1024
GIT_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Provider + role contract constants (TASK_027)
# ---------------------------------------------------------------------------


PROVIDER_TYPE_MANUAL = "manual"
PROVIDER_TYPE_MOCK = "mock"


# Default provider assignments per role. The dispatcher is manual-only
# and never invokes Claude/Codex CLIs; the mock provider is reserved
# for tests and is a no-op stub.
PROVIDER_FOR_ROLE: dict[str, tuple[str, str]] = {
    "planner":  ("CodexPlanner",       PROVIDER_TYPE_MANUAL),
    "executor": ("ClaudeCodeExecutor", PROVIDER_TYPE_MANUAL),
    "reviewer": ("CodexReviewer",      PROVIDER_TYPE_MANUAL),
    "human":    ("HumanReviewer",      PROVIDER_TYPE_MANUAL),
}


# Per-role artifact contract. Each tuple:
#   (output_filename, ready_marker_filename, failed_filename, expected_schema_or_None)
ROLE_CONTRACT: dict[str, dict[str, Any]] = {
    "planner": {
        "output_filename": "TASK_*.md",
        "output_exact": None,
        "ready_marker": "TASK_READY",
        "failed_artifact": "planner_failed.md",
        "expected_schema": None,
        "allowed_next_states": (PHASE_WAITING_FOR_EXECUTOR_REPORT, PHASE_FAILED),
    },
    "executor": {
        "output_filename": "executor_report.md",
        "output_exact": "executor_report.md",
        "ready_marker": "EXECUTOR_READY",
        "failed_artifact": "executor_failed.md",
        "expected_schema": None,
        "allowed_next_states": (PHASE_WAITING_FOR_REVIEW_RESULT, PHASE_FAILED),
    },
    "reviewer": {
        "output_filename": "patch_review_result.json",
        "output_exact": "patch_review_result.json",
        "ready_marker": "REVIEW_READY",
        "failed_artifact": "reviewer_failed.md",
        "expected_schema": "patch_review_result",
        "allowed_next_states": (PHASE_ROUND_SUMMARY_READY, PHASE_FAILED),
    },
}


# Paths that no provider may write to. Surfaced in job envelopes and
# prompts; enforced via filesystem roles in the dispatcher.
FORBIDDEN_PROVIDER_PATHS: tuple[str, ...] = (
    "sigma_abc/",
    ".loop/human_signoff.yaml",
    ".loop/human_signoff_ledger.jsonl",
    ".loop/human_signoff_history/",
    "docs/devlog/audits/",
    "agent_bus/round_state/git_status.txt",
    "agent_bus/round_state/git_diff_stat.txt",
    "agent_bus/round_state/git_diff.patch",
    "agent_bus/round_state/acceptance_results.json",
    "agent_bus/round_state/agent_round_summary.json",
    "agent_bus/round_state/agent_round_summary.md",
)


WATCH_OUTCOME_ADVANCE = "ADVANCE"
WATCH_OUTCOME_IDLE = "IDLE"
WATCH_OUTCOME_IDLE_WAITING_FOR_READY_MARKER = "IDLE_WAITING_FOR_READY_MARKER"
WATCH_OUTCOME_FAIL = "FAIL"
WATCH_OUTCOME_STOP_HUMAN_BOUNDARY = "STOP_HUMAN_BOUNDARY"
WATCH_OUTCOME_STOP_TERMINAL = "STOP_TERMINAL"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def bus_paths(bus_root: Path) -> dict[str, Path]:
    """Return resolved bus paths for role:dir pairs."""
    bus_root = Path(bus_root)
    out: dict[str, Path] = {"bus_root": bus_root}
    for role, subdirs in LAYOUT:
        out[role] = bus_root / role
        for sub in subdirs:
            out[f"{role}_{sub}"] = bus_root / role / sub
    out["round_state_dir"] = bus_root / "round_state"
    out["round_state_file"] = bus_root / "round_state" / "current_round.json"
    out["acceptance_results"] = bus_root / "round_state" / "acceptance_results.json"
    out["git_status"] = bus_root / "round_state" / "git_status.txt"
    out["git_diff_stat"] = bus_root / "round_state" / "git_diff_stat.txt"
    out["git_diff"] = bus_root / "round_state" / "git_diff.patch"
    out["agent_round_summary_json"] = bus_root / "round_state" / "agent_round_summary.json"
    out["agent_round_summary_md"] = bus_root / "round_state" / "agent_round_summary.md"
    out["planner_inbox_prompt"] = bus_root / "planner" / "inbox" / "planner_prompt.md"
    out["planner_job_envelope"] = bus_root / "planner" / "inbox" / "planner_job.json"
    out["planner_ready_marker"] = bus_root / "planner" / "outbox" / "TASK_READY"
    out["planner_failed_artifact"] = bus_root / "planner" / "failed" / "planner_failed.md"
    out["executor_inbox_prompt"] = bus_root / "executor" / "inbox" / "executor_prompt.md"
    out["executor_job_envelope"] = bus_root / "executor" / "inbox" / "executor_job.json"
    out["executor_ready_marker"] = bus_root / "executor" / "outbox" / "EXECUTOR_READY"
    out["executor_failed_artifact"] = bus_root / "executor" / "failed" / "executor_failed.md"
    out["reviewer_inbox_prompt"] = bus_root / "reviewer" / "inbox" / "reviewer_prompt.md"
    out["reviewer_job_envelope"] = bus_root / "reviewer" / "inbox" / "reviewer_job.json"
    out["reviewer_ready_marker"] = bus_root / "reviewer" / "outbox" / "REVIEW_READY"
    out["reviewer_failed_artifact"] = bus_root / "reviewer" / "failed" / "reviewer_failed.md"
    out["human_approval_artifact"] = bus_root / "human" / "approved" / "approval.json"
    out["human_rejection_artifact"] = bus_root / "human" / "rejected" / "rejection.json"
    return out


def ensure_bus_layout(bus_root: Path) -> dict[str, Path]:
    """Create the bus layout. Idempotent."""
    bus_root = Path(bus_root)
    paths = bus_paths(bus_root)
    for role, subdirs in LAYOUT:
        for sub in subdirs:
            (bus_root / role / sub).mkdir(parents=True, exist_ok=True)
    paths["round_state_dir"].mkdir(parents=True, exist_ok=True)
    return paths


# ---------------------------------------------------------------------------
# Provider + role -> job envelope
# ---------------------------------------------------------------------------


def _provider_for(role: str, override: tuple[str, str] | None = None) -> tuple[str, str]:
    """Return ``(provider_name, provider_type)`` for ``role``.

    The default provider is manual and never invokes any external agent.
    Tests may pass a tuple ``("mock_name", PROVIDER_TYPE_MOCK)`` to
    exercise alternate paths; the dispatcher still does not invoke a
    real CLI for either type.
    """
    if override is not None:
        return override
    return PROVIDER_FOR_ROLE.get(role, ("UnknownProvider", PROVIDER_TYPE_MANUAL))


def role_for_phase(phase: str) -> str | None:
    """Return the role that owns the in-flight work for a given phase."""
    if phase in {PHASE_PLANNER_PROMPT_READY, PHASE_WAITING_FOR_TASK_SPEC}:
        return "planner"
    if phase in {PHASE_EXECUTOR_PROMPT_READY, PHASE_WAITING_FOR_EXECUTOR_REPORT}:
        return "executor"
    if phase in {PHASE_REVIEWER_PROMPT_READY, PHASE_WAITING_FOR_REVIEW_RESULT}:
        return "reviewer"
    if phase == PHASE_WAITING_FOR_HUMAN_APPROVAL:
        return "human"
    return None


def _input_files_for_role(role: str, bus_root: Path, round_state: dict[str, Any]) -> list[str]:
    """Return the absolute paths the provider may read for the given role."""
    paths = bus_paths(bus_root)
    if role == "planner":
        nar = round_state.get("next_action_report")
        return [str(nar)] if nar else []
    if role == "executor":
        out = [str(paths["planner_inbox_prompt"])]
        ts = round_state.get("task_spec")
        if ts:
            out.append(str(ts))
        out.append(str(paths["executor_inbox_prompt"]))
        return out
    if role == "reviewer":
        out: list[str] = [str(paths["reviewer_inbox_prompt"])]
        ts = round_state.get("task_spec")
        if ts:
            out.append(str(ts))
        er = round_state.get("executor_report")
        if er:
            out.append(str(er))
        out.extend([
            str(paths["git_status"]),
            str(paths["git_diff_stat"]),
            str(paths["git_diff"]),
            str(paths["acceptance_results"]),
        ])
        return out
    return []


def _output_files_for_role(role: str, bus_root: Path) -> list[str]:
    """Return the absolute paths the provider must write for the given role."""
    paths = bus_paths(bus_root)
    if role == "planner":
        return [str(paths["planner_outbox"] / "TASK_*.md")]
    if role == "executor":
        return [str(paths["executor_outbox"] / ROLE_CONTRACT["executor"]["output_exact"])]
    if role == "reviewer":
        return [str(paths["reviewer_outbox"] / ROLE_CONTRACT["reviewer"]["output_exact"])]
    return []


def _ready_marker_path_for_role(role: str, bus_root: Path) -> Path:
    paths = bus_paths(bus_root)
    return paths[f"{role}_ready_marker"]


def _failed_artifact_path_for_role(role: str, bus_root: Path) -> Path:
    paths = bus_paths(bus_root)
    return paths[f"{role}_failed_artifact"]


def render_job_envelope(
    role: str,
    bus_root: Path,
    round_state: dict[str, Any],
    *,
    provider_override: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Build the machine-readable job envelope for ``role``.

    The envelope mirrors what the matching prompt must declare. The
    dispatcher writes a JSON copy next to the prompt at
    ``<role>/inbox/<role>_job.json``.
    """
    if role not in ROLE_CONTRACT:
        raise ValueError(f"unknown role for job envelope: {role}")
    paths = bus_paths(bus_root)
    provider_name, provider_type = _provider_for(role, provider_override)
    phase = round_state.get("phase", PHASE_INIT)
    envelope = {
        "round_id": round_state.get("round_id"),
        "role": role,
        "phase": phase,
        "working_directory": str(bus_root),
        "input_files": _input_files_for_role(role, bus_root, round_state),
        "output_files": _output_files_for_role(role, bus_root),
        "ready_marker": str(_ready_marker_path_for_role(role, bus_root)),
        "failed_artifact": str(_failed_artifact_path_for_role(role, bus_root)),
        "forbidden_paths": list(FORBIDDEN_PROVIDER_PATHS),
        "expected_schema": ROLE_CONTRACT[role]["expected_schema"],
        "provider_name": provider_name,
        "provider_type": provider_type,
        "allowed_next_states": list(ROLE_CONTRACT[role]["allowed_next_states"]),
        "job_envelope_path": str(paths[f"{role}_job_envelope"]),
        "generated_at": utc_now(),
    }
    validate_with_schema(envelope, "agent_bus_job")
    return envelope


def write_job_envelope(
    role: str,
    bus_root: Path,
    round_state: dict[str, Any],
    *,
    provider_override: tuple[str, str] | None = None,
) -> Path:
    """Render and persist the job envelope for ``role``; return its path."""
    paths = ensure_bus_layout(bus_root)
    envelope = render_job_envelope(role, bus_root, round_state, provider_override=provider_override)
    write_json(paths[f"{role}_job_envelope"], envelope)
    return paths[f"{role}_job_envelope"]


# ---------------------------------------------------------------------------
# Ready-marker / failed-artifact validation
# ---------------------------------------------------------------------------


def _expected_output_path(role: str, bus_root: Path) -> Path:
    """Return the expected output artifact path for ``role`` (concrete path)."""
    paths = bus_paths(bus_root)
    exact = ROLE_CONTRACT[role].get("output_exact")
    if exact:
        return paths[f"{role}_outbox"] / exact
    # Planner uses a glob (TASK_*.md). Caller resolves via accept_planner_task.
    return paths[f"{role}_outbox"] / "TASK_*.md"


def validate_artifact_for_role(
    role: str,
    bus_root: Path,
    *,
    artifact_path: Path | None = None,
) -> tuple[bool, str]:
    """Validate expected artifact + ready marker + failed-artifact absence.

    Returns ``(ok, reason)``. ``ok=False`` means ``advance()`` must NOT
    transition the phase. The returned reason is suitable for status
    output.

    The dispatcher NEVER auto-creates a role's ready marker. The marker
    must be written by the provider/session after the output artifact is
    complete. If the marker is absent, validation fails with
    ``"ready marker absent"`` regardless of whether the output file
    itself is present and well-formed.

    Failed-artifact presence is checked first; if it exists, validation
    fails with ``"failed artifact present"`` and the caller is expected
    to transition the round to ``FAILED``.
    """
    if role not in ROLE_CONTRACT:
        return False, f"unknown role: {role}"
    paths = bus_paths(bus_root)

    # Failed-artifact presence short-circuits to FAILED.
    failed_path = paths[f"{role}_failed_artifact"]
    if failed_path.exists():
        return False, f"failed artifact present at {failed_path}"

    # Output artifact must exist and be non-empty.
    if artifact_path is None:
        artifact_path = _expected_output_path(role, bus_root)
    artifact_path = Path(artifact_path)
    if "*" in str(artifact_path):
        # Glob mode (planner): the caller must resolve the exact task spec.
        return False, f"artifact path contains wildcard: {artifact_path}"
    if not artifact_path.exists():
        return False, f"output artifact missing: {artifact_path}"
    try:
        if artifact_path.stat().st_size <= 0:
            return False, f"output artifact empty: {artifact_path}"
    except OSError as exc:
        return False, f"output artifact stat failed: {exc}"

    # Schema validation when expected.
    expected_schema = ROLE_CONTRACT[role]["expected_schema"]
    if expected_schema:
        try:
            payload = read_json(artifact_path)
            validate_with_schema(payload, expected_schema)
        except (json.JSONDecodeError, OSError) as exc:
            return False, f"output artifact not parseable JSON: {exc}"
        except Exception as exc:  # jsonschema.ValidationError
            return False, f"output artifact failed schema {expected_schema}: {exc}"

    # Ready marker: required. The dispatcher does NOT auto-create it.
    # The provider/session must drop the marker once its output is
    # complete and validated.
    ready_path = paths[f"{role}_ready_marker"]
    if not ready_path.exists():
        return False, f"ready marker absent: {ready_path}"
    return True, "ok"





def new_round_id(prefix: str = "AGENT") -> str:
    stamp = utc_now().replace(":", "").replace("-", "").replace("+", "_")
    short = uuid.uuid4().hex[:8]
    return f"{prefix}_{stamp}_{short}"


def _empty_round_state(round_id: str) -> dict[str, Any]:
    now = utc_now()
    return {
        "round_id": round_id,
        "created_at": now,
        "updated_at": now,
        "phase": PHASE_INIT,
        "next_action_report": None,
        "planner_prompt": None,
        "task_spec": None,
        "executor_prompt": None,
        "executor_report": None,
        "reviewer_prompt": None,
        "patch_review_result": None,
        "agent_round_summary": None,
        "human_boundary_status": HUMAN_BOUNDARY_NONE,
        "human_boundary_required": False,
        "acceptance_commands": [],
        "events": [],
    }


def read_round_state(bus_root: Path) -> dict[str, Any]:
    """Read round state from disk; default to a fresh INIT state if missing."""
    paths = bus_paths(Path(bus_root))
    path = paths["round_state_file"]
    if not path.exists():
        return _empty_round_state("UNINITIALIZED")
    try:
        return read_json(path)
    except (json.JSONDecodeError, OSError):
        return _empty_round_state("UNINITIALIZED")


def write_round_state(bus_root: Path, state: dict[str, Any]) -> None:
    paths = bus_paths(Path(bus_root))
    paths["round_state_dir"].mkdir(parents=True, exist_ok=True)
    state["updated_at"] = utc_now()
    write_json(paths["round_state_file"], state)


def _append_event(state: dict[str, Any], message: str) -> None:
    state.setdefault("events", []).append({
        "at": utc_now(),
        "phase": state.get("phase", PHASE_INIT),
        "message": message,
    })


def _validate_state(state: dict[str, Any]) -> None:
    validate_with_schema(state, "agent_bus_state")


# ---------------------------------------------------------------------------
# Phase progression
# ---------------------------------------------------------------------------


def _set_phase(state: dict[str, Any], phase: str) -> None:
    if phase not in PHASE_ORDER:
        raise ValueError(f"unknown phase: {phase}")
    state["phase"] = phase
    _append_event(state, f"phase -> {phase}")


# ---------------------------------------------------------------------------
# Round state role metadata (TASK_027)
# ---------------------------------------------------------------------------


def _attach_role_metadata(
    state: dict[str, Any],
    role: str,
    paths: dict[str, Path],
) -> None:
    """Stamp the round state with the current role's contract metadata.

    Persists ``current_role``, ``provider_name``/``provider_type``,
    ``current_job_envelope_path``, ``ready_marker_path``,
    ``expected_artifact_path``, and ``failed_artifact_path``. Does NOT
    write the job envelope to disk; the caller is expected to do that
    via :func:`write_job_envelope` for prompts generated alongside
    these fields.
    """
    state["current_role"] = role
    provider_name, provider_type = _provider_for(role)
    state["provider_name"] = provider_name
    state["provider_type"] = provider_type
    if role == "planner":
        state["current_job_envelope_path"] = str(paths["planner_job_envelope"])
        state["ready_marker_path"] = str(paths["planner_ready_marker"])
        state["expected_artifact_path"] = str(paths["planner_outbox"] / "TASK_*.md")
        state["failed_artifact_path"] = str(paths["planner_failed_artifact"])
    elif role == "executor":
        state["current_job_envelope_path"] = str(paths["executor_job_envelope"])
        state["ready_marker_path"] = str(paths["executor_ready_marker"])
        state["expected_artifact_path"] = str(paths["executor_outbox"] / "executor_report.md")
        state["failed_artifact_path"] = str(paths["executor_failed_artifact"])
    elif role == "reviewer":
        state["current_job_envelope_path"] = str(paths["reviewer_job_envelope"])
        state["ready_marker_path"] = str(paths["reviewer_ready_marker"])
        state["expected_artifact_path"] = str(paths["reviewer_outbox"] / "patch_review_result.json")
        state["failed_artifact_path"] = str(paths["reviewer_failed_artifact"])
    elif role == "human":
        state["current_job_envelope_path"] = None
        state["ready_marker_path"] = str(paths["human_approval_artifact"])
        state["expected_artifact_path"] = str(paths["human_approval_artifact"])
        state["failed_artifact_path"] = str(paths["human_rejection_artifact"])


# ---------------------------------------------------------------------------
# Round lifecycle
# ---------------------------------------------------------------------------


def start_round(
    bus_root: Path,
    *,
    next_action_report: Path | str | None,
    round_id: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Initialize a fresh round.

    If the supplied ``next_action_report`` classifies the run as
    HUMAN_SIGNOFF_REQUIRED or BOUNDARY_APPROVAL_REQUIRED, the round is
    short-circuited to ``WAITING_FOR_HUMAN_APPROVAL`` and a boundary
    summary is dropped into ``human/inbox/``. No planner/executor/reviewer
    prompts are written.

    Otherwise the planner inbox prompt is generated and the round
    transitions to ``WAITING_FOR_TASK_SPEC`` (note: NOT
    ``PLANNER_PROMPT_READY`` — the prompt is immediately available so the
    waiting state begins now).

    Idempotent: if ``current_round.json`` exists and ``force=False``, the
    existing state is returned unchanged.
    """
    bus_root = Path(bus_root)
    paths = ensure_bus_layout(bus_root)
    rid = round_id or new_round_id()
    state = read_round_state(bus_root)
    if paths["round_state_file"].exists() and not force and state.get("round_id") not in (None, "UNINITIALIZED"):
        return state

    state = _empty_round_state(rid)
    if next_action_report is not None:
        nar_path = Path(next_action_report)
        if not nar_path.exists():
            raise FileNotFoundError(f"next_action_report not found: {nar_path}")
        state["next_action_report"] = str(nar_path)
        report = read_json(nar_path)
        code = (report.get("classification") or {}).get("code")
        if code in {"HUMAN_SIGNOFF_REQUIRED", "BOUNDARY_APPROVAL_REQUIRED"}:
            _route_human_boundary(bus_root, state, report, paths, reason=f"next_action_report classification={code}")
            write_round_state(bus_root, state)
            _validate_state(state)
            return state
        render = render_planner_prompt(report, state)
        write_text(paths["planner_inbox_prompt"], render)
        state["planner_prompt"] = str(paths["planner_inbox_prompt"])
        _append_event(state, f"wrote planner prompt to {paths['planner_inbox_prompt']}")
        _attach_role_metadata(state, "planner", paths)
        # Set the active waiting phase BEFORE writing the job envelope so
        # the envelope's phase field matches the role's actual waiting
        # state (not INIT). The render_job_envelope helper reads the
        # current phase from round_state.
        _set_phase(state, PHASE_WAITING_FOR_TASK_SPEC)
        write_job_envelope("planner", Path(paths["bus_root"]), state)
        _append_event(state, f"wrote planner job envelope to {paths['planner_job_envelope']}")
    else:
        _set_phase(state, PHASE_INIT)
    write_round_state(bus_root, state)
    _validate_state(state)
    return state


def _route_human_boundary(
    bus_root: Path,
    state: dict[str, Any],
    report: dict[str, Any] | None,
    paths: dict[str, Path],
    *,
    reason: str,
) -> None:
    """Drop a boundary summary into human/inbox and set
    WAITING_FOR_HUMAN_APPROVAL. Never auto-mutates signoff/checkpoint
    artifacts.
    """
    _ = bus_root
    state["human_boundary_required"] = True
    state["human_boundary_status"] = HUMAN_BOUNDARY_PENDING
    code = (report or {}).get("classification", {}).get("code", "UNKNOWN")
    description = (report or {}).get("classification", {}).get("description", "")
    summary_lines = [
        f"# Human Boundary Required -- Round {state.get('round_id', 'UNKNOWN')}",
        "",
        f"- Reason: {reason}",
        f"- Classification code: `{code}`",
        f"- Description: {description}",
        f"- Next action report: `{state.get('next_action_report')}`",
        "",
        "The dispatcher will not write planner, executor, or reviewer",
        "prompts until a human approves this boundary.",
        "",
        "## Forbidden automatic actions",
        "",
        "- auto-freeze checkpoints",
        "- auto-mutate .loop/human_signoff.yaml",
        "- auto-mutate .loop/human_signoff_ledger.jsonl",
        "- auto-mutate .loop/human_signoff_history/",
        "- auto-edit scientific artifacts",
        "- auto-edit sigma_abc/checkpoints/",
        "- invoke Claude Code CLI on this agent's behalf",
        "- invoke Codex CLI on this agent's behalf",
        "",
    ]
    summary_md = "\n".join(summary_lines)
    boundary_path = paths["human_inbox"] / f"boundary_{state.get('round_id', 'UNKNOWN')}.md"
    write_text(boundary_path, summary_md)
    state.setdefault("extra", {})["boundary_summary_path"] = str(boundary_path)
    _append_event(state, f"routed boundary summary to {boundary_path}")
    _set_phase(state, PHASE_WAITING_FOR_HUMAN_APPROVAL)


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


def render_planner_prompt(
    next_action_report: dict[str, Any],
    round_state: dict[str, Any],
    *,
    job_envelope: dict[str, Any] | None = None,
) -> str:
    """Build the planner prompt text."""
    cls = (next_action_report.get("classification") or {})
    code = cls.get("code", "UNKNOWN_FAILURE")
    desc = cls.get("description", "")
    subject = next_action_report.get("subject", {}) or {}
    all_cls = next_action_report.get("all_classifications", []) or []
    next_action = next_action_report.get("next_action", {}) or {}
    forbidden = next_action_report.get("forbidden_actions", []) or []

    rid = round_state.get("round_id", "UNINITIALIZED")
    nar_ref = round_state.get("next_action_report") or "next_action_report.json"

    all_lines: list[str] = []
    for entry in all_cls:
        all_lines.append(f"- {entry.get('code', '')}: {entry.get('description', '')}")
    all_block = "\n".join(all_lines) if all_lines else "- (none)"

    forbidden_block = "\n".join(f"- {action}" for action in forbidden) if forbidden else "- (none)"

    # Build the contract sections (TASK_027).
    je = job_envelope or {
        "input_files": [str(nar_ref)] if nar_ref else [],
        "output_files": ["agent_bus/planner/outbox/TASK_*.md"],
        "ready_marker": "agent_bus/planner/outbox/TASK_READY",
        "failed_artifact": "agent_bus/planner/failed/planner_failed.md",
        "forbidden_paths": list(FORBIDDEN_PROVIDER_PATHS),
        "provider_name": PROVIDER_FOR_ROLE["planner"][0],
        "provider_type": PROVIDER_FOR_ROLE["planner"][1],
        "allowed_next_states": list(ROLE_CONTRACT["planner"]["allowed_next_states"]),
    }
    read_block = "\n".join(f"- `{p}`" for p in je["input_files"]) or "- (none)"
    write_block = "\n".join(f"- `{p}`" for p in je["output_files"]) or "- (none)"
    forbidden_block_t27 = "\n".join(f"- `{p}`" for p in je["forbidden_paths"]) or "- (none)"
    next_states_block = ", ".join(f"`{s}`" for s in je["allowed_next_states"]) or "(none)"

    return f"""# Planner Prompt (Round {rid})

## ROLE

- Role: `planner` (CodexPlanner, manual provider)
- Round: `{rid}`
- Provider: `{je['provider_name']}` (type: `{je['provider_type']}`)

## ROUND_ID

`{rid}`

## READ

{read_block}

## WRITE ONLY

{write_block}

Write exactly ONE `TASK_XXX.md` to `agent_bus/planner/outbox/`. Filename
MUST match `TASK_<round_id>.md` when a round_id is set, else any
`TASK_*.md`. After the file is written and you have verified it is
non-empty, create the planner ready marker:

## READY MARKER

- `{je['ready_marker']}`

Create this marker ONLY after the `TASK_*.md` is fully written and
non-empty. Empty file + marker = invalid.

## FAILED ARTIFACT

- `{je['failed_artifact']}`

If you cannot produce a valid task spec, write a short failure note to
this path (do NOT touch any other file).

## DO NOT EDIT

{forbidden_block_t27}

- You MUST NOT edit code, scientific artifacts, frozen checkpoints,
  validation artifacts, signoff ledgers, or any file outside
  `agent_bus/`.
- You MUST NOT auto-stage, auto-commit, auto-approve, auto-freeze, or
  auto-reject.
- Treat any classification mentioning `HUMAN_SIGNOFF_REQUIRED`,
  `BOUNDARY_APPROVAL_REQUIRED`, or `FREEZE_PRECONDITION_FAILED` as a
  hard human-approval requirement; the executor MUST be told to stop and
  request human approval.

## STOP CONDITION

Stop after writing the `TASK_*.md` and the ready marker (or the failed
artifact). Do not start any other task. Do not touch the executor,
reviewer, human, or round_state inboxes.

## Allowed next states

{next_states_block}

## Diagnosis (driven by next_action_report.json)

- Source report: `{nar_ref}`
- Subject kind: `{subject.get('kind', 'unknown')}`
- Run root: `{subject.get('run_root') or 'n/a'}`
- Project: `{subject.get('project') or 'n/a'}`
- Stage: `{subject.get('stage_id') or 'n/a'}`

## Primary classification

- Code: **{code}**
- Description: {desc}

## All classifications

{all_block}

## Required next action

- Recommended: `{next_action.get('recommended', 'ASK_HUMAN_REVIEWER')}`
- Rationale: {next_action.get('rationale', '')}
- Human required: `{next_action.get('human_required', False)}`
- Boundary approval required: `{next_action.get('boundary_approval_required', False)}`
- Patch-or-reject recommended: `{next_action.get('patch_or_reject_recommended', False)}`

## Forbidden automatic actions (from NAR)

{forbidden_block}

## Required task-spec structure

When you write `TASK_XXX.md`, include exactly the following top-level
keys (matches the executor-friendly format this bus already speaks):

- `# Task ID` (e.g. `TASK_026`)
- `# Title`
- `# Problem`
- `# Goal`
- `# Non-goals`
- `# Allowed edits`
- `# Forbidden edits`
- `# Implementation steps`
- `# Acceptance commands`
- `# Expected output files`
- `# Risks`
- `# Definition of done`
"""


def render_executor_prompt(
    task_text: str,
    round_state: dict[str, Any],
    *,
    task_path: Path | str | None = None,
    job_envelope: dict[str, Any] | None = None,
) -> str:
    rid = round_state.get("round_id", "UNINITIALIZED")
    ref = str(task_path) if task_path is not None else "(see task text below)"
    je = job_envelope or {
        "input_files": [str(task_path)] if task_path else [],
        "output_files": ["agent_bus/executor/outbox/executor_report.md"],
        "ready_marker": "agent_bus/executor/outbox/EXECUTOR_READY",
        "failed_artifact": "agent_bus/executor/failed/executor_failed.md",
        "forbidden_paths": list(FORBIDDEN_PROVIDER_PATHS),
        "provider_name": PROVIDER_FOR_ROLE["executor"][0],
        "provider_type": PROVIDER_FOR_ROLE["executor"][1],
        "allowed_next_states": list(ROLE_CONTRACT["executor"]["allowed_next_states"]),
    }
    read_block = "\n".join(f"- `{p}`" for p in je["input_files"]) or "- (none)"
    write_block = "\n".join(f"- `{p}`" for p in je["output_files"]) or "- (none)"
    forbidden_block = "\n".join(f"- `{p}`" for p in je["forbidden_paths"]) or "- (none)"
    next_states_block = ", ".join(f"`{s}`" for s in je["allowed_next_states"]) or "(none)"

    return f"""# Executor Prompt (Round {rid})

## ROLE

- Role: `executor` (ClaudeCodeExecutor, manual provider)
- Round: `{rid}`
- Provider: `{je['provider_name']}` (type: `{je['provider_type']}`)

## ROUND_ID

`{rid}`

## READ

{read_block}

## WRITE ONLY

{write_block}

Write `executor_report.md` to `agent_bus/executor/outbox/` only. After
the file is written and you have verified it is non-empty and contains
all required sections, create the executor ready marker:

## READY MARKER

- `{je['ready_marker']}`

Create this marker ONLY after the `executor_report.md` is fully written
and non-empty. Empty file + marker = invalid.

## FAILED ARTIFACT

- `{je['failed_artifact']}`

If you cannot complete the task, write a short failure note to this
path (do NOT touch any other file).

## DO NOT EDIT

{forbidden_block}

- Implement only the bounded task. Do NOT expand scope.
- Do NOT auto-freeze, auto-stage, auto-commit, auto-approve, or
  auto-reject.
- Do NOT start another task; do not write to other round's bus.

## STOP CONDITION

Stop after writing `executor_report.md` and the ready marker (or the
failed artifact). Do not start TASK_NNN+1, do not commit, do not
push. The dispatcher will collect git diff + acceptance command output
and pass it forward to the reviewer.

## Allowed next states

{next_states_block}

## Source task spec

- Path: `{ref}`

```markdown
{task_text}
```

## Instructions

1. Implement only the bounded task above. Do NOT expand scope.
2. Do NOT edit frozen checkpoints, completed-stage validation artifacts,
   scientific outputs, or human signoff ledgers.
3. Do NOT auto-freeze, auto-stage, auto-commit, auto-approve, or
   auto-reject.
4. Run the acceptance commands from the task spec.
5. Write your full report to:
   `agent_bus/executor/outbox/executor_report.md`

The report MUST use these section names so the dispatcher can find them:

- `## Status`
- `## changed_files`
- `## commands_run`
- `## tests_passed`
- `## tests_failed`
- `## unresolved_issues`
- `## scope_deviation`
- `## recommended_next_action`

If you do not auto-freeze checkpoints, do not modify human signoff
files, and respect all forbidden-edit lists, say so plainly in the
report. The dispatcher will collect git diff + acceptance command
output and pass it forward to the reviewer.
"""


def render_reviewer_prompt(
    task_text: str,
    executor_report_text: str,
    evidence_paths: dict[str, Any],
    *,
    task_path: Path | str | None = None,
    executor_report_path: Path | str | None = None,
    job_envelope: dict[str, Any] | None = None,
) -> str:
    rel = lambda p: str(p) if p is not None else "(none)"  # noqa: E731
    je = job_envelope or {
        "input_files": [
            rel(task_path), rel(executor_report_path),
            rel(evidence_paths.get("git_status")),
            rel(evidence_paths.get("git_diff_stat")),
            rel(evidence_paths.get("git_diff")),
            rel(evidence_paths.get("acceptance_results")),
        ],
        "output_files": ["agent_bus/reviewer/outbox/patch_review_result.json"],
        "ready_marker": "agent_bus/reviewer/outbox/REVIEW_READY",
        "failed_artifact": "agent_bus/reviewer/failed/reviewer_failed.md",
        "forbidden_paths": list(FORBIDDEN_PROVIDER_PATHS),
        "provider_name": PROVIDER_FOR_ROLE["reviewer"][0],
        "provider_type": PROVIDER_FOR_ROLE["reviewer"][1],
        "allowed_next_states": list(ROLE_CONTRACT["reviewer"]["allowed_next_states"]),
    }
    read_block = "\n".join(f"- `{p}`" for p in je["input_files"] if p) or "- (none)"
    write_block = "\n".join(f"- `{p}`" for p in je["output_files"]) or "- (none)"
    forbidden_block = "\n".join(f"- `{p}`" for p in je["forbidden_paths"]) or "- (none)"
    next_states_block = ", ".join(f"`{s}`" for s in je["allowed_next_states"]) or "(none)"

    return f"""# Reviewer Prompt

## ROLE

- Role: `reviewer` (CodexReviewer, manual provider)
- Provider: `{je['provider_name']}` (type: `{je['provider_type']}`)

## ROUND_ID

`{evidence_paths.get('round_id', 'UNINITIALIZED')}`

## READ

{read_block}

## WRITE ONLY

{write_block}

Write `patch_review_result.json` to `agent_bus/reviewer/outbox/`. After
the file is written, validated, and you have verified it is non-empty
and parses against the required schema, create the reviewer ready
marker:

## READY MARKER

- `{je['ready_marker']}`

Create this marker ONLY after the JSON is fully written, parseable, and
schema-valid. Empty / invalid JSON + marker = invalid.

## FAILED ARTIFACT

- `{je['failed_artifact']}`

If you cannot produce a valid result, write a short failure note to
this path (do NOT touch any other file).

## DO NOT EDIT

{forbidden_block}

- You MUST NOT edit any file outside `agent_bus/reviewer/outbox/`. The
  reviewer is read-only on the rest of the repository.

## STOP CONDITION

Stop after writing `patch_review_result.json` and the ready marker (or
the failed artifact). Do not start another task. Do not commit.

## Allowed next states

{next_states_block}

## Task spec

- Path: `{rel(task_path)}`

```markdown
{task_text}
```

## Executor report

- Path: `{rel(executor_report_path)}`

```markdown
{executor_report_text}
```

## Collected evidence paths

- Git status: `{rel(evidence_paths.get('git_status'))}`
- Git diff stat: `{rel(evidence_paths.get('git_diff_stat'))}`
- Git diff patch: `{rel(evidence_paths.get('git_diff'))}`
- Acceptance results: `{rel(evidence_paths.get('acceptance_results'))}`

## Required output

Write your verdict to:
`agent_bus/reviewer/outbox/patch_review_result.json`

Required JSON shape:

- `verdict` -- e.g. `PASS`, `PASS_WITH_CAVEAT`, `FAIL`
- `blocking_issues` -- array of strings; FAIL-worthy defects
- `caveats` -- array of strings; minor concerns
- `recommended_next_action` -- non-empty string
- `safe_to_continue` -- boolean
- `nonblocking_caveats` -- array of strings; minor concerns
- `required_followups` -- array of strings; concrete next tasks
- `reviewed_files` -- array of strings; relative or absolute paths
- `acceptance_evidence_assessment` -- string; PASS / WARN / FAIL with reasons
- `human_boundary_assessment` -- string; mention anything that
  requires a human scientist (freeze, IBP, tensorial claim, candidate
  promotion, overclaim, etc.). Empty string if none.
"""


# ---------------------------------------------------------------------------
# Boundary detection
# ---------------------------------------------------------------------------


def needs_human_boundary(
    next_action_report: dict[str, Any] | None,
    task_text: str | None,
    executor_text: str | None,
    reviewer_result: dict[str, Any] | None,
) -> bool:
    """Return True if any signal indicates a human-approval boundary."""
    if next_action_report:
        code = (next_action_report.get("classification") or {}).get("code")
        if code in {"HUMAN_SIGNOFF_REQUIRED", "BOUNDARY_APPROVAL_REQUIRED"}:
            return True
        boundary = next_action_report.get("next_action", {}).get("boundary_approval_required")
        if boundary:
            return True
    combined = " ".join(filter(None, (task_text, executor_text)) or [])
    if combined:
        lower = combined.lower()
        for token in HUMAN_BOUNDARY_TOKENS:
            if token in lower:
                return True
    if reviewer_result:
        assess = (reviewer_result.get("human_boundary_assessment") or "").strip()
        if assess:
            return True
    return False


# ---------------------------------------------------------------------------
# Outbox acceptance
# ---------------------------------------------------------------------------


def _list_outbox(bus_root: Path, role: str) -> list[Path]:
    paths = bus_paths(Path(bus_root))
    out_dir = paths[f"{role}_outbox"]
    if not out_dir.exists():
        return []
    return sorted(p for p in out_dir.iterdir() if p.is_file())


def accept_planner_task(bus_root: Path, *, task_path: Path | None = None) -> Path:
    """Locate/accept the planner outbox task spec.

    Only files matching ``TASK_*.md`` (or ``TASK_<round_id>.md`` when a
    round_id is set) are accepted. Other markdown files (e.g. ``notes.md``)
    are ignored.

    Raises:
        FileNotFoundError: no TASK_*.md present
        AmbiguousPlannerTasks: multiple TASK_*.md present
    """
    bus_root = Path(bus_root)
    paths = ensure_bus_layout(bus_root)
    if task_path is not None:
        tp = Path(task_path)
        if not tp.exists():
            raise FileNotFoundError(f"task spec not found: {tp}")
        name = tp.name
        if not (name.startswith("TASK_") and name.endswith(".md") and name != "TASK_*.md"):
            raise InvalidPlannerTask(
                f"task_path must match TASK_*.md pattern, got: {name}"
            )
        return tp

    files = _list_outbox(bus_root, "planner")
    candidates = [
        p for p in files
        if p.name.startswith("TASK_") and p.name.endswith(".md") and p.name != "TASK_*.md"
    ]
    # Prefer TASK_<round_id>.md when round_id is known.
    state = read_round_state(bus_root)
    rid = state.get("round_id")
    if rid:
        exact = [p for p in candidates if p.name == f"TASK_{rid}.md"]
        if exact:
            candidates = exact
    if not candidates:
        raise FileNotFoundError("no TASK_*.md in planner/outbox")
    if len(candidates) > 1:
        raise AmbiguousPlannerTasks([str(p) for p in candidates])

    chosen = candidates[0]
    state["task_spec"] = str(chosen)
    _append_event(state, f"accepted planner task {chosen}")
    # Set the active waiting phase BEFORE rendering the job envelope so
    # the envelope's phase field matches the role's actual waiting
    # state (not the previous phase).
    _set_phase(state, PHASE_WAITING_FOR_EXECUTOR_REPORT)
    _attach_role_metadata(state, "executor", paths)
    envelope = render_job_envelope("executor", bus_root, state)
    render = render_executor_prompt(
        read_text(chosen),
        state,
        task_path=chosen,
        job_envelope=envelope,
    )
    write_text(paths["executor_inbox_prompt"], render)
    write_json(paths["executor_job_envelope"], envelope)
    state["executor_prompt"] = str(paths["executor_inbox_prompt"])
    state["current_job_envelope_path"] = str(paths["executor_job_envelope"])
    _append_event(state, f"wrote executor prompt to {paths['executor_inbox_prompt']}")
    _append_event(state, f"wrote executor job envelope to {paths['executor_job_envelope']}")
    write_round_state(bus_root, state)
    return chosen


class InvalidPlannerTask(ValueError):
    """Raised when a non-TASK_*.md path is provided to accept_planner_task."""


class AmbiguousPlannerTasks(FileNotFoundError):
    """Raised when the planner outbox contains multiple TASK_*.md files."""


def accept_executor_report(bus_root: Path, *, executor_report_path: Path | None = None) -> Path:
    bus_root = Path(bus_root)
    paths = ensure_bus_layout(bus_root)
    if executor_report_path is not None:
        rp = Path(executor_report_path)
        if not rp.exists():
            raise FileNotFoundError(f"executor_report not found: {rp}")
    else:
        files = [p for p in _list_outbox(bus_root, "executor") if p.name == "executor_report.md"]
        if not files:
            raise FileNotFoundError("no executor_report.md in executor/outbox")
        rp = files[0]

    state = read_round_state(bus_root)
    state["executor_report"] = str(rp)
    _append_event(state, f"accepted executor report {rp}")
    # Set the active waiting phase BEFORE rendering the job envelope so
    # the envelope's phase field matches the role's actual waiting
    # state (not the previous phase).
    _set_phase(state, PHASE_WAITING_FOR_REVIEW_RESULT)
    _attach_role_metadata(state, "reviewer", paths)
    task_text = ""
    if state.get("task_spec"):
        task_text = read_text(Path(state["task_spec"]))
    evidence: dict[str, Any] = {
        "git_status": str(paths["git_status"]),
        "git_diff_stat": str(paths["git_diff_stat"]),
        "git_diff": str(paths["git_diff"]),
        "acceptance_results": str(paths["acceptance_results"]),
        "round_id": state.get("round_id"),
    }
    envelope = render_job_envelope("reviewer", bus_root, state)
    render = render_reviewer_prompt(
        task_text,
        read_text(rp),
        evidence,
        task_path=state.get("task_spec"),
        executor_report_path=rp,
        job_envelope=envelope,
    )
    write_text(paths["reviewer_inbox_prompt"], render)
    write_json(paths["reviewer_job_envelope"], envelope)
    state["reviewer_prompt"] = str(paths["reviewer_inbox_prompt"])
    state["current_job_envelope_path"] = str(paths["reviewer_job_envelope"])
    _append_event(state, f"wrote reviewer prompt to {paths['reviewer_inbox_prompt']}")
    _append_event(state, f"wrote reviewer job envelope to {paths['reviewer_job_envelope']}")
    write_round_state(bus_root, state)
    return rp


def accept_reviewer_result(bus_root: Path, *, result_path: Path | None = None) -> Path:
    """Accept the reviewer result, validating against the
    ``patch_review_result`` schema.

    On any validation or JSON-parse error:
      - record ``state.reviewer_error``
      - leave the phase as ``WAITING_FOR_REVIEW_RESULT``
      - write an error artifact to ``round_state/reviewer_error.json``
      - re-raise ``InvalidReviewerResult`` so callers can see the cause.

    Never reaches ``ROUND_SUMMARY_READY`` until a valid reviewer result
    is accepted.
    """
    bus_root = Path(bus_root)
    paths = ensure_bus_layout(bus_root)
    if result_path is not None:
        rp = Path(result_path)
    else:
        files = [p for p in _list_outbox(bus_root, "reviewer") if p.name == "patch_review_result.json"]
        if not files:
            raise FileNotFoundError("no patch_review_result.json in reviewer/outbox")
        rp = files[0]
    if not rp.exists():
        raise FileNotFoundError(f"reviewer result not found: {rp}")

    state = read_round_state(bus_root)
    paths["round_state_dir"].mkdir(parents=True, exist_ok=True)
    error_path = paths["round_state_dir"] / "reviewer_error.json"

    try:
        payload = read_json(rp)
        validate_with_schema(payload, "patch_review_result")
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        record = {
            "evaluated_at": utc_now(),
            "result_path": str(rp),
            "error": f"invalid JSON: {exc}",
        }
        write_json(error_path, record)
        state["reviewer_error"] = str(error_path)
        _append_event(state, f"reviewer result invalid JSON: {exc}")
        write_round_state(bus_root, state)
        raise InvalidReviewerResult(f"invalid reviewer JSON: {exc}") from exc
    except Exception as exc:
        # jsonschema.ValidationError is some subclass of Exception; match broadly.
        record = {
            "evaluated_at": utc_now(),
            "result_path": str(rp),
            "error": f"schema validation failed: {exc}",
        }
        write_json(error_path, record)
        state["reviewer_error"] = str(error_path)
        _append_event(state, f"reviewer result schema invalid: {exc}")
        # Stay in WAITING_FOR_REVIEW_RESULT; do NOT raise plain ValueError
        # which callers may handle. Instead, surface a typed error.
        write_round_state(bus_root, state)
        raise InvalidReviewerResult(f"reviewer result failed patch_review_result schema: {exc}") from exc

    state["patch_review_result"] = str(rp)
    state.pop("reviewer_error", None)
    _append_event(state, f"accepted reviewer result {rp}")

    task_text = read_text(Path(state["task_spec"])) if state.get("task_spec") else None
    executor_text = read_text(Path(state["executor_report"])) if state.get("executor_report") else None
    nar_payload: dict[str, Any] | None = None
    if state.get("next_action_report"):
        try:
            nar_payload = read_json(Path(state["next_action_report"]))
        except (json.JSONDecodeError, OSError):
            nar_payload = None

    boundary_required = needs_human_boundary(nar_payload, task_text, executor_text, payload)
    evidence_paths = {
        "git_status": paths["git_status"],
        "git_diff_stat": paths["git_diff_stat"],
        "git_diff": paths["git_diff"],
        "acceptance_results": paths["acceptance_results"],
    }

    summary_obj, summary_md = render_round_summary(
        state=state,
        evidence_paths=evidence_paths,
        reviewer_result=payload,
        boundary_required=boundary_required,
    )
    write_json(paths["agent_round_summary_json"], summary_obj)
    write_text(paths["agent_round_summary_md"], summary_md)
    state["agent_round_summary"] = str(paths["agent_round_summary_json"])
    _append_event(state, "wrote agent_round_summary.{json,md}")

    if boundary_required:
        state["human_boundary_required"] = True
        state["human_boundary_status"] = HUMAN_BOUNDARY_PENDING
        boundary_path = paths["human_inbox"] / f"boundary_{state['round_id']}.md"
        write_text(boundary_path, summary_md)
        state.setdefault("extra", {})["boundary_summary_path"] = str(boundary_path)
        _append_event(state, f"routed boundary summary to {boundary_path}")
        _set_phase(state, PHASE_ROUND_SUMMARY_READY)
    else:
        _set_phase(state, PHASE_ROUND_SUMMARY_READY)
    # Clear role-specific metadata now that the round is terminal.
    state["current_role"] = None
    state["current_job_envelope_path"] = None
    state["ready_marker_path"] = None
    state["expected_artifact_path"] = None
    state["failed_artifact_path"] = None

    write_round_state(bus_root, state)
    return rp


class InvalidReviewerResult(ValueError):
    """Raised when the reviewer result fails JSON parse or schema validation."""


# ---------------------------------------------------------------------------
# Git + acceptance evidence
# ---------------------------------------------------------------------------


def _run_git(cmd: list[str], cwd: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "error": None,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"git error: {exc}",
            "error": str(exc),
        }


def collect_git_evidence(repo_root: Path, round_state_dir: Path) -> dict[str, Path]:
    """Run `git status`, `git diff --stat`, `git diff` and write evidence files.

    Safe to call when git is unavailable: writes empty files instead of
    raising.
    """
    repo_root = Path(repo_root)
    round_state_dir = Path(round_state_dir)
    round_state_dir.mkdir(parents=True, exist_ok=True)
    status_path = round_state_dir / "git_status.txt"
    stat_path = round_state_dir / "git_diff_stat.txt"
    diff_path = round_state_dir / "git_diff.patch"

    status_run = _run_git(["git", "status", "--short"], repo_root)
    stat_run = _run_git(["git", "diff", "--stat"], repo_root)
    diff_run = _run_git(["git", "diff"], repo_root)

    status_text = status_run["stdout"] if status_run["returncode"] == 0 else (
        f"git status unavailable: {status_run['stderr'] or status_run['error']}"
    )
    stat_text = stat_run["stdout"] if stat_run["returncode"] == 0 else (
        f"git diff --stat unavailable: {stat_run['stderr'] or stat_run['error']}"
    )
    diff_text = diff_run["stdout"] if diff_run["returncode"] == 0 else (
        f"git diff unavailable: {diff_run['stderr'] or diff_run['error']}"
    )

    status_path.write_text(status_text, encoding="utf-8")
    stat_path.write_text(stat_text, encoding="utf-8")
    diff_path.write_text(diff_text, encoding="utf-8")

    return {
        "git_status": status_path,
        "git_diff_stat": stat_path,
        "git_diff": diff_path,
    }


def collect_acceptance_evidence(
    round_state_dir: Path,
    *,
    commands: list[str],
    no_command_run: bool,
) -> dict[str, Any]:
    """Run each acceptance command and record results.

    With ``no_command_run=True``, no commands are executed but each one is
    recorded as ``run=False``.
    """
    round_state_dir = Path(round_state_dir)
    round_state_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for cmd in commands:
        cmd = cmd.strip()
        if not cmd:
            continue
        if no_command_run:
            results.append({
                "command": cmd,
                "run": False,
                "returncode": None,
                "stdout": "",
                "stderr": "",
                "elapsed_seconds": None,
            })
            continue
        # Shell out via subprocess shell split.
        try:
            proc = subprocess.run(
                cmd,
                shell=True,  # noqa: S602 — explicit user-provided command list
                capture_output=True,
                text=True,
                timeout=600,
            )
            results.append({
                "command": cmd,
                "run": True,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[:STDOUT_TRUNCATE],
                "stderr": (proc.stderr or "")[:STDERR_TRUNCATE],
                "elapsed_seconds": None,
            })
        except subprocess.TimeoutExpired:
            results.append({
                "command": cmd,
                "run": True,
                "returncode": -1,
                "stdout": "",
                "stderr": f"timeout after 600s",
                "elapsed_seconds": None,
            })
        except FileNotFoundError as exc:
            results.append({
                "command": cmd,
                "run": True,
                "returncode": -1,
                "stdout": "",
                "stderr": f"shell error: {exc}",
                "elapsed_seconds": None,
            })

    payload = {
        "generated_at": utc_now(),
        "no_command_run": no_command_run,
        "results": results,
    }
    write_json(round_state_dir / "acceptance_results.json", payload)
    return payload


# ---------------------------------------------------------------------------
# Round summary
# ---------------------------------------------------------------------------


def render_round_summary(
    state: dict[str, Any],
    evidence_paths: dict[str, Any],
    reviewer_result: dict[str, Any] | None = None,
    *,
    boundary_required: bool = False,
) -> tuple[dict[str, Any], str]:
    summary = {
        "round_id": state.get("round_id"),
        "phase": state.get("phase"),
        "diagnosis_input_path": state.get("next_action_report"),
        "task_spec_path": state.get("task_spec"),
        "executor_report_path": state.get("executor_report"),
        "reviewer_result_path": state.get("patch_review_result"),
        "git_evidence_paths": {
            "status": str(evidence_paths.get("git_status", "")) or None,
            "diff_stat": str(evidence_paths.get("git_diff_stat", "")) or None,
            "diff": str(evidence_paths.get("git_diff", "")) or None,
        },
        "acceptance_results_path": str(evidence_paths.get("acceptance_results", "")) or None,
        "verdict": (reviewer_result or {}).get("verdict") if reviewer_result else None,
        "next_recommended_human_action": (
            (reviewer_result or {}).get("required_followups")
            or ["ASK_HUMAN_REVIEWER"]
            if reviewer_result else None
        ),
        "forbidden_automatic_actions": [
            "auto-freeze checkpoints",
            "auto-mutate .loop/human_signoff.yaml",
            "auto-mutate .loop/human_signoff_ledger.jsonl",
            "auto-mutate .loop/human_signoff_history/",
            "auto-edit scientific artifacts",
            "auto-edit sigma_abc/checkpoints/",
            "auto-edit completed-stage validation",
            "invoke Claude Code CLI on this agent's behalf",
            "invoke Codex CLI on this agent's behalf",
        ],
        "human_boundary_required": boundary_required,
        "boundary_summary_path": None,
        "no_checkpoint_freeze_or_signoff_mutation": True,
        "generated_at": utc_now(),
    }
    if boundary_required:
        verdict_text = (reviewer_result or {}).get("verdict") or "BOUNDARY_PENDING"
        summary["verdict"] = verdict_text
        summary["next_recommended_human_action"] = (
            (reviewer_result or {}).get("required_followups")
            or ["REQUEST_HUMAN_APPROVAL"]
        )
    validate_with_schema(summary, "agent_round_summary")

    md_lines: list[str] = []
    md_lines.append(f"# Agent Round Summary -- Round {summary['round_id']}")
    md_lines.append("")
    md_lines.append(f"- Final phase: `{summary['phase']}`")
    md_lines.append(f"- Diagnosis input: `{summary['diagnosis_input_path']}`")
    md_lines.append(f"- Task spec: `{summary['task_spec_path']}`")
    md_lines.append(f"- Executor report: `{summary['executor_report_path']}`")
    md_lines.append(f"- Reviewer result: `{summary['reviewer_result_path']}`")
    md_lines.append(f"- Verdict: `{summary['verdict']}`")
    md_lines.append(f"- Human boundary required: `{summary['human_boundary_required']}`")
    md_lines.append("")
    md_lines.append("## Evidence paths")
    md_lines.append("")
    md_lines.append(f"- git status: `{summary['git_evidence_paths']['status']}`")
    md_lines.append(f"- git diff stat: `{summary['git_evidence_paths']['diff_stat']}`")
    md_lines.append(f"- git diff patch: `{summary['git_evidence_paths']['diff']}`")
    md_lines.append(f"- acceptance results: `{summary['acceptance_results_path']}`")
    md_lines.append("")
    md_lines.append("## Forbidden automatic actions")
    md_lines.append("")
    for action in summary["forbidden_automatic_actions"]:
        md_lines.append(f"- {action}")
    md_lines.append("")
    md_lines.append("## No-mutation attestation")
    md_lines.append("")
    md_lines.append(
        "This dispatcher is manual-provider-only. It did NOT freeze any "
        "checkpoint, did NOT mutate `.loop/human_signoff.yaml`, "
        "`.loop/human_signoff_ledger.jsonl`, or `.loop/human_signoff_history/`, "
        "and did NOT edit scientific artifacts or `sigma_abc/` outputs."
    )
    md_lines.append("")

    md = "\n".join(md_lines) + "\n"
    return summary, md


# ---------------------------------------------------------------------------
# Top-level advance / status / summarize / fail
# ---------------------------------------------------------------------------


def _expected_next_artifact(state: dict[str, Any]) -> str:
    phase = state.get("phase", PHASE_INIT)
    return {
        PHASE_INIT: "Run --advance with --next-action-report to start a round.",
        PHASE_PLANNER_PROMPT_READY: (
            "Wait for `agent_bus/planner/outbox/TASK_*.md` from the planner."
        ),
        PHASE_WAITING_FOR_TASK_SPEC: (
            "Wait for `agent_bus/planner/outbox/TASK_*.md` from the planner."
        ),
        PHASE_EXECUTOR_PROMPT_READY: (
            "Wait for `agent_bus/executor/outbox/executor_report.md` from the executor."
        ),
        PHASE_WAITING_FOR_EXECUTOR_REPORT: (
            "Wait for `agent_bus/executor/outbox/executor_report.md` from the executor."
        ),
        PHASE_REVIEWER_PROMPT_READY: (
            "Wait for `agent_bus/reviewer/outbox/patch_review_result.json` from the reviewer."
        ),
        PHASE_WAITING_FOR_REVIEW_RESULT: (
            "Wait for `agent_bus/reviewer/outbox/patch_review_result.json` from the reviewer."
        ),
        PHASE_ROUND_SUMMARY_READY: (
            "Round summary has been written. Re-run with --summary-only to refresh."
        ),
        PHASE_WAITING_FOR_HUMAN_APPROVAL: (
            "Wait for a human to drop an approval/rejection artifact into "
            "`agent_bus/human/approved/` or `agent_bus/human/rejected/`."
        ),
        PHASE_FAILED: "Round failed. Run --fail-reason to record details.",
    }.get(phase, "Unknown phase")


def status(bus_root: Path) -> dict[str, Any]:
    bus_root = Path(bus_root)
    ensure_bus_layout(bus_root)
    state = read_round_state(bus_root)
    role = state.get("current_role") or role_for_phase(state.get("phase", PHASE_INIT))
    out: dict[str, Any] = {
        "bus_root": str(bus_root),
        "round_id": state.get("round_id"),
        "phase": state.get("phase"),
        "current_role": role,
        "expected_next_artifact": _expected_next_artifact(state),
        "expected_ready_marker": state.get("ready_marker_path"),
        "failed_artifact_path": state.get("failed_artifact_path"),
        "expected_artifact_path": state.get("expected_artifact_path"),
        "provider_name": state.get("provider_name"),
        "provider_type": state.get("provider_type"),
        "current_job_envelope_path": state.get("current_job_envelope_path"),
        "human_boundary_required": state.get("human_boundary_required", False),
        "human_boundary_status": state.get("human_boundary_status", HUMAN_BOUNDARY_NONE),
        "watch_outcome": state.get("watch_outcome"),
        "watch_last_observation": state.get("watch_last_observation"),
        "failure_role": state.get("failure_role"),
        "failure_reason": state.get("failure_reason"),
        "failure_source": state.get("failure_source"),
        "failure_evidence_path": state.get("failure_evidence_path"),
        "paths": {
            k: str(v)
            for k, v in bus_paths(bus_root).items()
            if isinstance(v, Path) and not k.endswith("_dir")
        },
    }
    return out


def _repo_root_or_cwd(repo_root: Path | None) -> Path:
    if repo_root is None:
        repo_root = Path.cwd()
    return Path(repo_root)


def advance(
    bus_root: Path,
    *,
    repo_root: Path | None = None,
    acceptance_commands: list[str] | None = None,
    no_command_run: bool = False,
    force: bool = False,
    next_action_report: Path | None = None,
) -> dict[str, Any]:
    """Advance exactly ONE phase based on the current state.

    Phase-machine contract:

    - INIT (no NAR) -> unchanged; provide --next-action-report.
    - INIT (with --next-action-report) -> WAITING_FOR_TASK_SPEC or
      WAITING_FOR_HUMAN_APPROVAL (handled inside ``start_round``).
    - WAITING_FOR_TASK_SPEC -> if exactly one matching TASK_*.md exists
      in planner/outbox AND the planner ready marker is present, generate
      executor prompt and transition to WAITING_FOR_EXECUTOR_REPORT.
      Otherwise stay put. Missing ready marker -> IDLE (no advance).
    - WAITING_FOR_EXECUTOR_REPORT -> if executor_report.md exists in
      executor/outbox AND the executor ready marker is present, generate
      reviewer prompt and transition to WAITING_FOR_REVIEW_RESULT.
      Otherwise stay put. Missing ready marker -> IDLE (no advance).
    - WAITING_FOR_REVIEW_RESULT -> if a valid patch_review_result.json
      exists in reviewer/outbox AND the reviewer ready marker is present,
      generate round summary and transition to ROUND_SUMMARY_READY.
      Otherwise stay put.
    - WAITING_FOR_HUMAN_APPROVAL / ROUND_SUMMARY_READY / FAILED -> no
      automatic advance (require explicit human input or --fail-reason).

    Preplaced planner/executor/reviewer outbox artifacts are NEVER
    consumed across multiple phases in a single advance() call. Each
    accept-step only consumes the artifact for its own phase, and the
    method returns once that single step's transition has been written.
    """
    bus_root = Path(bus_root)
    paths = ensure_bus_layout(bus_root)
    repo_root = _repo_root_or_cwd(repo_root)

    # Step 0: optionally start a fresh round. This transitions INIT to
    # WAITING_FOR_TASK_SPEC (or WAITING_FOR_HUMAN_APPROVAL). We count
    # this as one phase move and DO NOT also advance further in the
    # same call.
    if next_action_report is not None:
        state = start_round(bus_root, next_action_report=next_action_report, force=force)
        return status(bus_root)

    phase = read_round_state(bus_root).get("phase", PHASE_INIT)
    rs_dir = paths["round_state_dir"]

    # Step 1: WAITING_FOR_TASK_SPEC -> accept planner task -> WAITING_FOR_EXECUTOR_REPORT.
    if phase == PHASE_WAITING_FOR_TASK_SPEC:
        # If the planner dropped a failed artifact, transition to FAILED.
        if _failed_for_role(bus_root, "planner"):
            return _transition_to_failed(
                bus_root, role="planner", source="advance",
                reason="planner failed artifact present",
            )
        # Validate the planner outbox + ready marker before consuming.
        ok, reason = _validate_role_artifact(bus_root, "planner")
        if not ok:
            outcome = _outcome_for_reason(reason)
            _record_watch_observation(bus_root, outcome, f"planner: {reason}")
            return status(bus_root)
        try:
            accept_planner_task(bus_root)
        except FileNotFoundError:
            _record_watch_observation(bus_root, WATCH_OUTCOME_IDLE, "planner: no TASK_*.md")
            return status(bus_root)
        except AmbiguousPlannerTasks:
            _record_watch_observation(bus_root, WATCH_OUTCOME_FAIL, "planner: ambiguous TASK_*.md")
            return status(bus_root)
        except InvalidPlannerTask as exc:
            _record_watch_observation(bus_root, WATCH_OUTCOME_FAIL, f"planner: {exc}")
            return status(bus_root)
        _record_watch_observation(
            bus_root, WATCH_OUTCOME_ADVANCE,
            f"planner: {PHASE_WAITING_FOR_TASK_SPEC} -> {PHASE_WAITING_FOR_EXECUTOR_REPORT}",
        )
        return status(bus_root)

    # Step 2: WAITING_FOR_EXECUTOR_REPORT -> accept executor report -> WAITING_FOR_REVIEW_RESULT.
    if phase == PHASE_WAITING_FOR_EXECUTOR_REPORT:
        if _failed_for_role(bus_root, "executor"):
            return _transition_to_failed(
                bus_root, role="executor", source="advance",
                reason="executor failed artifact present",
            )
        ok, reason = _validate_role_artifact(bus_root, "executor")
        if not ok:
            outcome = _outcome_for_reason(reason)
            _record_watch_observation(bus_root, outcome, f"executor: {reason}")
            return status(bus_root)
        try:
            accept_executor_report(bus_root)
        except FileNotFoundError:
            _record_watch_observation(bus_root, WATCH_OUTCOME_IDLE, "executor: no executor_report.md")
            return status(bus_root)
        _record_watch_observation(
            bus_root, WATCH_OUTCOME_ADVANCE,
            f"executor: {PHASE_WAITING_FOR_EXECUTOR_REPORT} -> {PHASE_WAITING_FOR_REVIEW_RESULT}",
        )
        return status(bus_root)

    # Step 3: WAITING_FOR_REVIEW_RESULT -> collect evidence + accept reviewer
    # result -> ROUND_SUMMARY_READY.
    if phase == PHASE_WAITING_FOR_REVIEW_RESULT:
        if _failed_for_role(bus_root, "reviewer"):
            return _transition_to_failed(
                bus_root, role="reviewer", source="advance",
                reason="reviewer failed artifact present",
            )
        ok, reason = _validate_role_artifact(bus_root, "reviewer")
        if not ok:
            outcome = _outcome_for_reason(reason)
            _record_watch_observation(bus_root, outcome, f"reviewer: {reason}")
            return status(bus_root)
        collect_git_evidence(repo_root, rs_dir)
        cmds = list(acceptance_commands or [])
        # Persist the configured commands on the round state so callers
        # can recall them on subsequent advances. Always collect evidence
        # so the round summary has fresh artifacts even if reviewer
        # validation fails.
        collect_acceptance_evidence(rs_dir, commands=cmds, no_command_run=no_command_run)
        state = read_round_state(bus_root)
        if cmds:
            state["acceptance_commands"] = cmds
            write_round_state(bus_root, state)
        try:
            accept_reviewer_result(bus_root)
        except InvalidReviewerResult:
            _record_watch_observation(
                bus_root, WATCH_OUTCOME_FAIL, "reviewer: schema-invalid patch_review_result"
            )
            # The helper already wrote reviewer_error.json and kept the
            # state at WAITING_FOR_REVIEW_RESULT. Don't advance.
            return status(bus_root)
        except FileNotFoundError:
            _record_watch_observation(bus_root, WATCH_OUTCOME_IDLE, "reviewer: no patch_review_result.json")
            return status(bus_root)
        _record_watch_observation(
            bus_root, WATCH_OUTCOME_ADVANCE,
            f"reviewer: {PHASE_WAITING_FOR_REVIEW_RESULT} -> {PHASE_ROUND_SUMMARY_READY}",
        )
        return status(bus_root)

    # Phases that should not auto-advance: WAITING_FOR_HUMAN_APPROVAL,
    # ROUND_SUMMARY_READY, FAILED, INIT. Just report current status.
    if phase == PHASE_WAITING_FOR_HUMAN_APPROVAL:
        _record_watch_observation(
            bus_root,
            WATCH_OUTCOME_STOP_HUMAN_BOUNDARY,
            "waiting for human approval/rejection",
        )
    return status(bus_root)


def _failed_for_role(bus_root: Path, role: str) -> bool:
    """Return True if the role's failed artifact exists on disk."""
    paths = bus_paths(bus_root)
    return paths[f"{role}_failed_artifact"].exists()


def _outcome_for_reason(reason: str) -> str:
    """Map a validation reason to a watch outcome.

    "ready marker absent" -> IDLE_WAITING_FOR_READY_MARKER (caller did
    the work; marker is the only thing missing).
    "failed artifact present" -> FAIL (caller is expected to transition
    to FAILED).
    Anything else -> IDLE.
    """
    if reason.startswith("ready marker absent"):
        return WATCH_OUTCOME_IDLE_WAITING_FOR_READY_MARKER
    if reason.startswith("failed artifact present"):
        return WATCH_OUTCOME_FAIL
    return WATCH_OUTCOME_IDLE


def _transition_to_failed(
    bus_root: Path,
    *,
    role: str,
    source: str,
    reason: str,
) -> dict[str, Any]:
    """Transition the round to FAILED with failure evidence.

    Records ``failure_role``, ``failure_reason``, ``failure_source``,
    and ``failure_evidence_path`` on the round state, writes a short
    failure summary to ``round_state/failure_<role>.json``, and stamps
    ``watch_outcome=FAIL`` + ``watch_last_observation`` on the state.
    Does NOT mutate signoff ledgers, frozen checkpoints, or scientific
    artifacts. Returns the current status.
    """
    bus_root = Path(bus_root)
    paths = ensure_bus_layout(bus_root)
    state = read_round_state(bus_root)
    failed_path = paths[f"{role}_failed_artifact"]

    evidence: dict[str, Any] = {
        "at": utc_now(),
        "round_id": state.get("round_id"),
        "phase": state.get("phase"),
        "role": role,
        "source": source,
        "reason": reason,
        "failed_artifact_path": str(failed_path),
    }
    if failed_path.exists():
        try:
            evidence["failed_artifact_content"] = failed_path.read_text(encoding="utf-8")
        except OSError:
            evidence["failed_artifact_content"] = None

    evidence_path = paths["round_state_dir"] / f"failure_{role}.json"
    write_json(evidence_path, evidence)

    state["failure_role"] = role
    state["failure_reason"] = reason
    state["failure_source"] = source
    state["failure_evidence_path"] = str(evidence_path)
    _set_phase(state, PHASE_FAILED)
    # Persist the in-memory state (with the new FAILED phase) BEFORE
    # recording the watch outcome, because _record_watch_observation
    # reads back from disk and would otherwise clobber the phase.
    write_round_state(bus_root, state)
    _record_watch_observation(
        bus_root, WATCH_OUTCOME_FAIL,
        f"{role}: {reason} (evidence={evidence_path.name})",
    )
    return status(bus_root)


def _validate_role_artifact(bus_root: Path, role: str) -> tuple[bool, str]:
    """Wrap :func:`validate_artifact_for_role` with planner glob resolution.

    Returns ``(ok, reason)`` exactly as the underlying validator. The
    caller chooses the watch outcome based on the reason string: reasons
    starting with ``"ready marker absent"`` map to
    ``IDLE_WAITING_FOR_READY_MARKER``; reasons starting with
    ``"failed artifact present"`` map to ``FAIL`` (and the round is
    transitioned to ``FAILED`` by the caller); all other failures map
    to ``IDLE``.
    """
    paths = bus_paths(bus_root)
    if role == "planner":
        # Resolve the glob to the actual chosen task spec so the
        # validate-against-schema check can find the file.
        try:
            chosen = accept_planner_task_choose_only(bus_root)
        except FileNotFoundError as exc:
            return False, str(exc)
        except AmbiguousPlannerTasks as exc:
            return False, f"ambiguous planner tasks: {exc}"
        except InvalidPlannerTask as exc:
            return False, str(exc)
        return validate_artifact_for_role(role, bus_root, artifact_path=chosen)
    return validate_artifact_for_role(role, bus_root, artifact_path=_expected_output_path(role, bus_root))


def accept_planner_task_choose_only(bus_root: Path) -> Path:
    """Return the chosen planner outbox task spec without consuming it.

    Mirrors the resolution logic of :func:`accept_planner_task` but does
    not move phases or write the executor prompt. Used by the watch
    loop to validate the artifact before deciding whether to advance.
    """
    files = _list_outbox(bus_root, "planner")
    candidates = [
        p for p in files
        if p.name.startswith("TASK_") and p.name.endswith(".md") and p.name != "TASK_*.md"
    ]
    state = read_round_state(bus_root)
    rid = state.get("round_id")
    if rid:
        exact = [p for p in candidates if p.name == f"TASK_{rid}.md"]
        if exact:
            candidates = exact
    if not candidates:
        raise FileNotFoundError("no TASK_*.md in planner/outbox")
    if len(candidates) > 1:
        raise AmbiguousPlannerTasks([str(p) for p in candidates])
    return candidates[0]


def _record_watch_observation(bus_root: Path, outcome: str, message: str) -> None:
    """Record a watch-mode observation on the round state."""
    state = read_round_state(bus_root)
    state["watch_outcome"] = outcome
    state["watch_last_observation"] = message
    _append_event(state, f"watch[{outcome}]: {message}")
    write_round_state(bus_root, state)


def summarize_only(bus_root: Path, *, repo_root: Path | None = None) -> dict[str, Any]:
    """Re-derive round summary from existing artifacts."""
    bus_root = Path(bus_root)
    paths = ensure_bus_layout(bus_root)
    repo_root = _repo_root_or_cwd(repo_root)
    rs_dir = paths["round_state_dir"]
    state = read_round_state(bus_root)

    # Re-collect git evidence to refresh timestamps.
    collect_git_evidence(repo_root, rs_dir)

    reviewer_payload: dict[str, Any] | None = None
    rp = state.get("patch_review_result")
    if rp:
        try:
            reviewer_payload = read_json(Path(rp))
        except (json.JSONDecodeError, OSError):
            reviewer_payload = None

    task_text = read_text(Path(state["task_spec"])) if state.get("task_spec") else None
    executor_text = read_text(Path(state["executor_report"])) if state.get("executor_report") else None
    nar_payload: dict[str, Any] | None = None
    if state.get("next_action_report"):
        try:
            nar_payload = read_json(Path(state["next_action_report"]))
        except (json.JSONDecodeError, OSError):
            nar_payload = None
    boundary_required = needs_human_boundary(nar_payload, task_text, executor_text, reviewer_payload)

    evidence_paths = {
        "git_status": paths["git_status"],
        "git_diff_stat": paths["git_diff_stat"],
        "git_diff": paths["git_diff"],
        "acceptance_results": paths["acceptance_results"],
    }
    summary_obj, summary_md = render_round_summary(
        state=state,
        evidence_paths=evidence_paths,
        reviewer_result=reviewer_payload,
        boundary_required=boundary_required,
    )
    write_json(paths["agent_round_summary_json"], summary_obj)
    write_text(paths["agent_round_summary_md"], summary_md)

    if boundary_required:
        boundary_path = paths["human_inbox"] / f"boundary_{state['round_id']}.md"
        write_text(boundary_path, summary_md)
        state["human_boundary_required"] = True
        state["human_boundary_status"] = HUMAN_BOUNDARY_PENDING
        state.setdefault("extra", {})["boundary_summary_path"] = str(boundary_path)

    write_round_state(bus_root, state)
    return status(bus_root)


# ---------------------------------------------------------------------------
# Watch mode (TASK_027)
# ---------------------------------------------------------------------------


def watch_one(
    bus_root: Path,
    *,
    repo_root: Path | None = None,
    acceptance_commands: list[str] | None = None,
    no_command_run: bool = False,
    next_action_report: Path | None = None,
    sleep_fn: Any = None,
) -> dict[str, Any]:
    """Perform a single safe-watch poll.

    Reuses the same one-phase advancement logic as :func:`advance`. The
    returned dict is :func:`status` extended with ``watch_outcome`` and
    ``watch_message`` keys.

    Watch contracts:

    - Calls ``advance()`` at most once.
    - At ``WAITING_FOR_HUMAN_APPROVAL`` -> ``STOP_HUMAN_BOUNDARY``
      (no further advance).
    - At ``ROUND_SUMMARY_READY`` / ``FAILED`` -> ``STOP_TERMINAL``.
    - Otherwise records ``ADVANCE`` / ``IDLE`` / ``FAIL`` on the round
      state via :func:`_record_watch_observation`.
    - Never invokes external agents; the manual provider is the only
      provider type used.
    - Never auto-freezes checkpoints or mutates signoff artifacts.
    """
    bus_root = Path(bus_root)
    state = read_round_state(bus_root)
    phase = state.get("phase", PHASE_INIT)
    if phase == PHASE_WAITING_FOR_HUMAN_APPROVAL:
        _record_watch_observation(
            bus_root, WATCH_OUTCOME_STOP_HUMAN_BOUNDARY, "human boundary in effect"
        )
        out = status(bus_root)
        out["watch_outcome"] = WATCH_OUTCOME_STOP_HUMAN_BOUNDARY
        out["watch_message"] = "STOP_HUMAN_BOUNDARY: awaiting human approval/rejection"
        return out
    if phase in {PHASE_ROUND_SUMMARY_READY, PHASE_FAILED}:
        _record_watch_observation(
            bus_root, WATCH_OUTCOME_STOP_TERMINAL, f"terminal phase {phase}"
        )
        out = status(bus_root)
        out["watch_outcome"] = WATCH_OUTCOME_STOP_TERMINAL
        out["watch_message"] = f"STOP_TERMINAL: phase={phase}"
        return out

    out = advance(
        bus_root,
        repo_root=repo_root,
        acceptance_commands=acceptance_commands,
        no_command_run=no_command_run,
        next_action_report=next_action_report,
    )
    if state.get("watch_outcome") is None:
        # advance() leaves the state alone when there's nothing to do.
        # Surface a sensible default for callers / status output.
        new_phase = out.get("phase", phase)
        if new_phase == phase:
            _record_watch_observation(bus_root, WATCH_OUTCOME_IDLE, "no transition")
        else:
            _record_watch_observation(bus_root, WATCH_OUTCOME_ADVANCE, f"{phase} -> {new_phase}")
    out = status(bus_root)
    out["watch_outcome"] = read_round_state(bus_root).get("watch_outcome")
    out["watch_message"] = read_round_state(bus_root).get("watch_last_observation")
    return out


def watch(
    bus_root: Path,
    *,
    poll_interval: float = 1.0,
    max_iterations: int | None = None,
    repo_root: Path | None = None,
    acceptance_commands: list[str] | None = None,
    no_command_run: bool = False,
    sleep_fn: Any = None,
) -> list[dict[str, Any]]:
    """Run the safe watch loop.

    Parameters mirror the CLI:

    - ``poll_interval``: seconds between polls. Floor at 0.05s.
    - ``max_iterations``: optional cap on the number of polls.
    - ``sleep_fn``: optional sleep callable. Defaults to
      :func:`time.sleep`; tests can pass a no-op.
    """
    import time as _time
    if sleep_fn is None:
        sleep_fn = _time.sleep
    interval = max(0.05, float(poll_interval))
    bus_root = Path(bus_root)
    observations: list[dict[str, Any]] = []
    iters = 0
    while True:
        if max_iterations is not None and iters >= max_iterations:
            break
        iters += 1
        out = watch_one(
            bus_root,
            repo_root=repo_root,
            acceptance_commands=acceptance_commands,
            no_command_run=no_command_run,
        )
        observations.append(out)
        if out.get("watch_outcome") in {
            WATCH_OUTCOME_STOP_HUMAN_BOUNDARY,
            WATCH_OUTCOME_STOP_TERMINAL,
            WATCH_OUTCOME_FAIL,
        }:
            break
        sleep_fn(interval)
    return observations


# ---------------------------------------------------------------------------
# fail_pending
# ---------------------------------------------------------------------------


def fail_pending(bus_root: Path, reason: str) -> dict[str, Any]:
    bus_root = Path(bus_root)
    paths = ensure_bus_layout(bus_root)
    state = read_round_state(bus_root)
    phase = state.get("phase", PHASE_INIT)
    role = "planner" if phase in {PHASE_PLANNER_PROMPT_READY, PHASE_WAITING_FOR_TASK_SPEC} else (
        "executor" if phase in {PHASE_EXECUTOR_PROMPT_READY, PHASE_WAITING_FOR_EXECUTOR_REPORT} else (
            "reviewer" if phase in {PHASE_REVIEWER_PROMPT_READY, PHASE_WAITING_FOR_REVIEW_RESULT}
            else None
        )
    )
    if role:
        inbox = paths[f"{role}_inbox"]
        failed = paths[f"{role}_failed"]
        if inbox.exists():
            for f in inbox.iterdir():
                target = failed / f.name
                if target.exists():
                    target = failed / f"{f.stem}.{utc_now().replace(':', '')}{f.suffix}"
                shutil.copy2(f, target)
                f.unlink()
    state["human_boundary_required"] = False
    state["human_boundary_status"] = HUMAN_BOUNDARY_REJECTED
    _set_phase(state, PHASE_FAILED)
    state["fail_reason"] = reason
    _append_event(state, f"failed: {reason}")
    write_round_state(bus_root, state)
    return status(bus_root)


__all__ = [
    "LAYOUT",
    "PHASE_INIT",
    "PHASE_PLANNER_PROMPT_READY",
    "PHASE_WAITING_FOR_TASK_SPEC",
    "PHASE_EXECUTOR_PROMPT_READY",
    "PHASE_WAITING_FOR_EXECUTOR_REPORT",
    "PHASE_REVIEWER_PROMPT_READY",
    "PHASE_WAITING_FOR_REVIEW_RESULT",
    "PHASE_ROUND_SUMMARY_READY",
    "PHASE_WAITING_FOR_HUMAN_APPROVAL",
    "PHASE_FAILED",
    "PHASE_ORDER",
    "HUMAN_BOUNDARY_NONE",
    "HUMAN_BOUNDARY_PENDING",
    "HUMAN_BOUNDARY_APPROVED",
    "HUMAN_BOUNDARY_REJECTED",
    "PROVIDER_TYPE_MANUAL",
    "PROVIDER_TYPE_MOCK",
    "PROVIDER_FOR_ROLE",
    "ROLE_CONTRACT",
    "FORBIDDEN_PROVIDER_PATHS",
    "WATCH_OUTCOME_ADVANCE",
    "WATCH_OUTCOME_IDLE",
    "WATCH_OUTCOME_IDLE_WAITING_FOR_READY_MARKER",
    "WATCH_OUTCOME_FAIL",
    "WATCH_OUTCOME_STOP_HUMAN_BOUNDARY",
    "WATCH_OUTCOME_STOP_TERMINAL",
    "AmbiguousPlannerTasks",
    "InvalidPlannerTask",
    "InvalidReviewerResult",
    "bus_paths",
    "ensure_bus_layout",
    "new_round_id",
    "read_round_state",
    "write_round_state",
    "start_round",
    "render_planner_prompt",
    "render_executor_prompt",
    "render_reviewer_prompt",
    "render_job_envelope",
    "write_job_envelope",
    "validate_artifact_for_role",
    "role_for_phase",
    "accept_planner_task",
    "accept_executor_report",
    "accept_reviewer_result",
    "collect_git_evidence",
    "collect_acceptance_evidence",
    "needs_human_boundary",
    "render_round_summary",
    "advance",
    "watch_one",
    "watch",
    "status",
    "summarize_only",
    "fail_pending",
]
