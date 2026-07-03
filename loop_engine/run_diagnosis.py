from __future__ import annotations

"""Deterministic, read-only failure classifier for loop / autonomous runs.

Layered on top of existing artifacts (validation_summary, review_result,
completion_matrix, human_signoff, pre_run_gate, freeze_preconditions). This
module does NOT modify scientific outputs, frozen checkpoints, signoff
ledgers, or completion matrices. It only reads and emits a report.

Public API:

- ``diagnose_run(...)`` -> ``dict``  (machine-readable report)
- ``render_next_action_markdown(report: dict)`` -> ``str``
- ``write_next_action_reports(report, output_dir)`` -> ``(json_path, md_path)``
- ``inspect_run_root(run_root, project=None)`` -> ``dict``  (run-root discovery; pure, read-only)

Classification precedence (primary code):

1. ``SCHEMA_VALIDATION_FAILED``    - a known JSON artifact is malformed or fails its schema
2. ``MISSING_REQUIRED_FILE``       - required basis files are absent for the requested mode
3. ``BOUNDARY_APPROVAL_REQUIRED``  - boundary audit / decision evidence requires human approval
4. ``VALIDATION_GATE_FAILED``      - validation_summary.json present, overall_gate != PASS
5. ``REVIEW_GATE_FAILED``          - review_result.json present, verdict not PASS / PASS_WITH_CAVEAT
6. ``COMPLETION_MATRIX_UNHEALTHY`` - completion_matrix.json present and unhealthy
7. ``HUMAN_SIGNOFF_REQUIRED``      - freeze would otherwise be eligible but signoff missing/blocks
8. ``FREEZE_PRECONDITION_FAILED``  - freeze_preconditions returns reasons not already classified
9. ``COMMAND_FAILED``              - command metadata indicates nonzero exit, no specific artifact match
10. ``UNKNOWN_FAILURE``             - no rule matched

Secondary findings are stored in ``all_classifications`` so a primary
classification never hides co-occurring failures.
"""

import json
from pathlib import Path
from typing import Any

import yaml

from .config import read_json, read_text, utc_now, write_json, write_text
from .schemas import validate_with_schema


SCHEMA_VERSION = "1.0.0"
DIAGNOSIS_READONLY = True

# Classification code constants (used in all_classifications + classification.code).
CLASSIFICATION_CODES = {
    "COMMAND_FAILED",
    "MISSING_REQUIRED_FILE",
    "SCHEMA_VALIDATION_FAILED",
    "VALIDATION_GATE_FAILED",
    "REVIEW_GATE_FAILED",
    "COMPLETION_MATRIX_UNHEALTHY",
    "HUMAN_SIGNOFF_REQUIRED",
    "FREEZE_PRECONDITION_FAILED",
    "BOUNDARY_APPROVAL_REQUIRED",
    "UNKNOWN_FAILURE",
}

# Default basis files considered "required" for stage-mode diagnosis.
STAGE_BASIS = {
    "validation_summary": ".loop/validation_summary.json",
    "review_result": ".loop/review_result.json",
    "claim_boundary": "CLAIM_BOUNDARY.md",
    "stage_plan": "STAGE_PLAN.md",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _relative(path: Path) -> str:
    """Best-effort display path: relative-to-cwd when possible."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _evidence(label: str, path: Path, *, exists: bool | None = None, summary: str | None = None) -> dict[str, Any]:
    return {
        "label": label,
        "path": _relative(path),
        "exists": exists if exists is not None else path.exists(),
        "summary": summary or "",
    }


def _safe_read_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return read_json(path)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def _try_validate_with_schema(data: dict[str, Any] | None, schema_name: str) -> tuple[bool, str]:
    if data is None:
        return False, "data is None"
    try:
        validate_with_schema(data, schema_name)
        return True, ""
    except Exception as exc:  # jsonschema.ValidationError or FileNotFoundError
        return False, str(exc)


# ---------------------------------------------------------------------------
# Classification primitives
# ---------------------------------------------------------------------------


def _detect_command_failure(
    *,
    command_return_code: int | None,
    stdout_file: Path | None,
    stderr_file: Path | None,
    command_status_json: Path | None,
) -> dict[str, Any] | None:
    """Return a COMMAND_FAILED classification dict if command metadata signals a failure.

    The check is independent of any artifact on disk; higher-priority
    classifications (schema / missing / validation / review / completion)
    still take precedence even if this fires.
    """
    if command_return_code is None and stdout_file is None and stderr_file is None and command_status_json is None:
        return None

    # command_status_json overrides everything else when present.
    if command_status_json is not None:
        if not command_status_json.exists():
            return {
                "code": "COMMAND_FAILED",
                "description": f"command_status_json not found at {_relative(command_status_json)}",
                "evidence": [_evidence("command_status_json", command_status_json, exists=False)],
            }
        status = _safe_read_json(command_status_json)
        if status is None:
            return {
                "code": "COMMAND_FAILED",
                "description": f"command_status_json is malformed: {_relative(command_status_json)}",
                "evidence": [_evidence("command_status_json", command_status_json, exists=True, summary="malformed JSON")],
            }
        rc = status.get("return_code") or status.get("exit_code")
        if isinstance(rc, int) and rc != 0:
            return {
                "code": "COMMAND_FAILED",
                "description": f"command_status_json reports non-zero return_code={rc}",
                "evidence": [_evidence("command_status_json", command_status_json, exists=True, summary=str(status))],
            }
        return None

    # Explicit return code wins.
    if command_return_code is not None and command_return_code != 0:
        evidence: list[dict[str, Any]] = []
        if stdout_file is not None:
            evidence.append(_evidence("stdout", stdout_file))
        if stderr_file is not None:
            evidence.append(_evidence("stderr", stderr_file))
        return {
            "code": "COMMAND_FAILED",
            "description": f"command returned non-zero exit code: {command_return_code}",
            "evidence": evidence or [_evidence("command_return_code", Path("."), exists=False, summary=str(command_return_code))],
        }

    # Heuristic: nonzero exit suspected from stderr.
    if stderr_file is not None and stderr_file.exists():
        text = read_text(stderr_file)
        if text.strip():
            return {
                "code": "COMMAND_FAILED",
                "description": "stderr file is non-empty",
                "evidence": [_evidence("stderr", stderr_file, exists=True, summary=text[:240])],
            }
    return None


def _classify_missing_files(stage: Path | None) -> list[dict[str, Any]]:
    """Detect MISSING_REQUIRED_FILE entries for stage-mode diagnosis."""
    findings: list[dict[str, Any]] = []
    if stage is None:
        return findings
    for label, rel in STAGE_BASIS.items():
        path = stage / rel
        if not path.exists():
            findings.append({
                "code": "MISSING_REQUIRED_FILE",
                "description": f"required stage file missing: {rel}",
                "evidence": [_evidence(label, path, exists=False)],
            })
    return findings


def _classify_schema_failures(stage: Path | None) -> list[dict[str, Any]]:
    """Detect SCHEMA_VALIDATION_FAILED entries by validating every known JSON artifact."""
    findings: list[dict[str, Any]] = []
    if stage is None:
        return findings
    candidates = [
        ("validation_summary", stage / ".loop" / "validation_summary.json", "validation_summary"),
        ("review_result", stage / ".loop" / "review_result.json", "review_result"),
        ("completion_matrix", stage / "reports" / "completion_matrix.json", "completion_matrix"),
        ("pre_run_brief", stage / ".loop" / "pre_run_brief.json", "pre_run_brief"),
        ("pre_run_gate_result", stage / ".loop" / "pre_run_gate_result.json", "pre_run_gate_result"),
        ("command_status", stage / ".loop" / "command_status.json", None),
    ]
    for label, path, schema_name in candidates:
        if not path.exists():
            continue
        raw_text = read_text(path)
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            findings.append({
                "code": "SCHEMA_VALIDATION_FAILED",
                "description": f"{label} JSON is malformed: {exc}",
                "evidence": [_evidence(label, path, exists=True, summary="JSONDecodeError")],
            })
            continue
        if schema_name is None:
            continue
        ok, reason = _try_validate_with_schema(parsed, schema_name)
        if not ok:
            findings.append({
                "code": "SCHEMA_VALIDATION_FAILED",
                "description": f"{label} fails schema validation: {reason}",
                "evidence": [_evidence(label, path, exists=True, summary=reason[:240])],
            })
    return findings


def _classify_validation_gate(stage: Path | None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if stage is None:
        return findings
    path = stage / ".loop" / "validation_summary.json"
    if not path.exists():
        return findings
    data = _safe_read_json(path)
    if data is None:
        return findings  # schema check will surface this
    gate = data.get("overall_gate")
    if gate is None:
        return findings
    if gate != "PASS":
        findings.append({
            "code": "VALIDATION_GATE_FAILED",
            "description": f"validation_summary.overall_gate != PASS (got {gate!r})",
            "evidence": [_evidence("validation_summary", path, exists=True, summary=f"overall_gate={gate}")],
        })
    return findings


def _classify_review_gate(stage: Path | None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if stage is None:
        return findings
    path = stage / ".loop" / "review_result.json"
    if not path.exists():
        return findings
    data = _safe_read_json(path)
    if data is None:
        return findings
    verdict = data.get("verdict")
    if verdict is None:
        return findings
    if verdict not in {"PASS", "PASS_WITH_CAVEAT"}:
        findings.append({
            "code": "REVIEW_GATE_FAILED",
            "description": f"review_result.verdict is not freezable (got {verdict!r})",
            "evidence": [_evidence("review_result", path, exists=True, summary=f"verdict={verdict}")],
        })
    return findings


def _classify_completion_matrix(stage: Path | None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if stage is None:
        return findings
    path = stage / "reports" / "completion_matrix.json"
    if not path.exists():
        return findings
    data = _safe_read_json(path)
    if data is None:
        return findings
    overall = data.get("overall_completion")
    freeze_eligible = data.get("freeze_eligible")
    boundary = data.get("boundary_audit", {}) or {}
    recommended = data.get("recommended_human_action")

    unhealthy = False
    reasons: list[str] = []
    if overall != "COMPLETE":
        unhealthy = True
        reasons.append(f"overall_completion={overall!r}")
    if freeze_eligible is False:
        unhealthy = True
        reasons.append("freeze_eligible=false")
    if recommended in {"DO_NOT_FREEZE_PATCH", "REJECT_AND_STOP"}:
        unhealthy = True
        reasons.append(f"recommended_human_action={recommended!r}")
    if any(boundary.get(key) for key in [
        "overclaim_detected",
        "full_tensorial_claim_detected",
        "ibp_started_without_approval",
    ]):
        unhealthy = True
        reasons.append("boundary audit raised a hard-safety flag")
    if boundary.get("dc_caveat_preserved") is False:
        unhealthy = True
        reasons.append("dc_caveat_preserved is false")

    if unhealthy:
        findings.append({
            "code": "COMPLETION_MATRIX_UNHEALTHY",
            "description": "completion matrix not healthy: " + ", ".join(reasons),
            "evidence": [_evidence("completion_matrix", path, exists=True, summary=f"overall={overall}, freeze_eligible={freeze_eligible}, recommended={recommended}")],
        })
    return findings


def _boundary_approval_evidence_paths(stage: Path | None) -> list[Path]:
    if stage is None:
        return []
    return [
        stage / ".loop" / "validation_summary.json",
        stage / ".loop" / "review_result.json",
        stage / "reports" / "completion_matrix.json",
        stage / ".loop" / "pre_run_gate_result.json",
        stage / ".loop" / "pre_run_brief.json",
        stage / "STAGE_PLAN.md",
        stage / "CLAIM_BOUNDARY.md",
    ]


def _classify_boundary_approval(stage: Path | None) -> list[dict[str, Any]]:
    """Detect BOUNDARY_APPROVAL_REQUIRED from boundary audit + decision evidence.

    Triggers when at least one of:
    - validation/review boundary_audit reports a hard-safety flag (overclaim /
      full-tensorial / ibp_started_without_approval / dc_caveat_lost)
    - completion_matrix recommended_human_action == REJECT_AND_STOP
    - completion_matrix boundary_audit.overclaim / full_tensorial /
      ibp_started flags are true
    - pre_run_gate_result is FAIL with hard-stop / forbidden intent
    - pre_run_brief positive_intent_forbidden_hits non-empty
    - STAGE_PLAN.md or CLAIM_BOUNDARY.md text contains forbidden patterns
      without negation
    """
    findings: list[dict[str, Any]] = []
    if stage is None:
        return findings
    evidence: list[dict[str, Any]] = []
    triggers: list[str] = []

    for label, rel, schema in [
        ("validation_summary", ".loop/validation_summary.json", "validation_summary"),
        ("review_result", ".loop/review_result.json", "review_result"),
    ]:
        path = stage / rel
        if not path.exists():
            continue
        data = _safe_read_json(path) or {}
        boundary = data.get("boundary_audit", {}) or {}
        for key in ("overclaim_detected", "full_tensorial_claim_detected", "ibp_started_without_approval"):
            if boundary.get(key) is True:
                triggers.append(f"{label}.boundary_audit.{key}=true")
                evidence.append(_evidence(label, path, exists=True, summary=key))
        if boundary.get("dc_caveat_preserved") is False:
            triggers.append(f"{label}.boundary_audit.dc_caveat_preserved=false")
            evidence.append(_evidence(label, path, exists=True, summary="dc_caveat_preserved=false"))

    matrix_path = stage / "reports" / "completion_matrix.json"
    matrix_data = _safe_read_json(matrix_path) if matrix_path.exists() else None
    if matrix_data is not None:
        boundary = matrix_data.get("boundary_audit", {}) or {}
        for key in ("overclaim_detected", "full_tensorial_claim_detected", "ibp_started_without_approval"):
            if boundary.get(key) is True:
                triggers.append(f"completion_matrix.boundary_audit.{key}=true")
                evidence.append(_evidence("completion_matrix", matrix_path, exists=True, summary=key))
        if boundary.get("dc_caveat_preserved") is False:
            triggers.append("completion_matrix.boundary_audit.dc_caveat_preserved=false")
            evidence.append(_evidence("completion_matrix", matrix_path, exists=True, summary="dc_caveat_preserved=false"))
        if matrix_data.get("recommended_human_action") == "REJECT_AND_STOP":
            triggers.append("completion_matrix.recommended_human_action=REJECT_AND_STOP")
            evidence.append(_evidence("completion_matrix", matrix_path, exists=True, summary="REJECT_AND_STOP"))

    gate_path = stage / ".loop" / "pre_run_gate_result.json"
    gate_data = _safe_read_json(gate_path) if gate_path.exists() else None
    if gate_data is not None:
        if gate_data.get("gate") == "FAIL" and (gate_data.get("blocking_reasons") or []):
            triggers.append("pre_run_gate_result.gate=FAIL with blocking reasons")
            evidence.append(_evidence("pre_run_gate_result", gate_path, exists=True, summary=str(gate_data.get("blocking_reasons"))[:240]))

    brief_path = stage / ".loop" / "pre_run_brief.json"
    brief_data = _safe_read_json(brief_path) if brief_path.exists() else None
    if brief_data is not None:
        hits = brief_data.get("positive_intent_forbidden_hits") or []
        if hits:
            triggers.append("pre_run_brief.positive_intent_forbidden_hits non-empty")
            evidence.append(_evidence("pre_run_brief", brief_path, exists=True, summary=",".join(hits)))

    # Plan / claim boundary text scan (cheap, deterministic, no LLM).
    for label, rel in (("stage_plan", "STAGE_PLAN.md"), ("claim_boundary", "CLAIM_BOUNDARY.md")):
        text_path = stage / rel
        if not text_path.exists():
            continue
        body = read_text(text_path).lower()
        # Bare positive imperative markers indicate positive forbidden intent.
        bare = (
            "promote the candidate",
            "promote this candidate",
            "promote the loop candidate",
            "start ibp",
            "perform ibp",
            "introduce total derivative",
            "claim full tensorial",
            "reduce ibp",
        )
        for marker in bare:
            if marker in body:
                # Check if every containing sentence is acknowledged (negative).
                # Cheap check: if "do not", "without", "no " immediately precedes, skip.
                idx = body.find(marker)
                prefix = body[max(0, idx - 16):idx].strip()
                if prefix.endswith(("do not", "without", "no", "never", "must not", "should not", "will not", "shall not")):
                    continue
                triggers.append(f"{label} contains positive forbidden intent: {marker!r}")
                evidence.append(_evidence(label, text_path, exists=True, summary=marker))
                break

    if triggers:
        findings.append({
            "code": "BOUNDARY_APPROVAL_REQUIRED",
            "description": "boundary approval is required: " + "; ".join(sorted(set(triggers))),
            "evidence": evidence,
        })
    return findings


def _classify_human_signoff(stage: Path | None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if stage is None:
        return findings
    signoff_path = stage / ".loop" / "human_signoff.yaml"
    matrix_path = stage / "reports" / "completion_matrix.json"
    validation_path = stage / ".loop" / "validation_summary.json"
    review_path = stage / ".loop" / "review_result.json"

    # Need validation + review PASS-equivalent + completion matrix COMPLETE/freeze_eligible
    # to even consider the "freeze would be eligible but no signoff" branch.
    matrix = _safe_read_json(matrix_path) if matrix_path.exists() else None
    validation = _safe_read_json(validation_path) if validation_path.exists() else None
    review = _safe_read_json(review_path) if review_path.exists() else None
    if not (validation and review and matrix):
        return findings

    if validation.get("overall_gate") != "PASS":
        return findings
    if review.get("verdict") not in {"PASS", "PASS_WITH_CAVEAT"}:
        return findings
    if matrix.get("overall_completion") != "COMPLETE":
        return findings
    if matrix.get("freeze_eligible") is not True:
        return findings

    signoff = _safe_read_yaml(signoff_path)
    if signoff is None:
        findings.append({
            "code": "HUMAN_SIGNOFF_REQUIRED",
            "description": "freeze would otherwise be eligible but human_signoff.yaml is missing",
            "evidence": [_evidence("human_signoff", signoff_path, exists=False)],
        })
        return findings

    # Signoff exists but blocks freeze specifically.
    decision = signoff.get("decision")
    permission = signoff.get("permission", {}) or {}
    if decision not in {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT"} or not permission.get("freeze_checkpoint"):
        findings.append({
            "code": "HUMAN_SIGNOFF_REQUIRED",
            "description": (
                f"human_signoff.yaml present but blocks freeze: decision={decision!r}, "
                f"freeze_checkpoint={permission.get('freeze_checkpoint')}"
            ),
            "evidence": [_evidence("human_signoff", signoff_path, exists=True, summary=f"decision={decision}")],
        })
    return findings


def _classify_freeze_preconditions(stage: Path | None) -> list[dict[str, Any]]:
    """Call freeze_preconditions directly; return FREEZE_PRECONDITION_FAILED for any reasons not already a signoff/boundary finding."""
    findings: list[dict[str, Any]] = []
    if stage is None:
        return findings
    validation_path = stage / ".loop" / "validation_summary.json"
    review_path = stage / ".loop" / "review_result.json"
    validation = _safe_read_json(validation_path) if validation_path.exists() else None
    review = _safe_read_json(review_path) if review_path.exists() else None
    if validation is None or review is None:
        return findings

    # Import lazily to avoid circular dependency at module load.
    from .state import freeze_preconditions

    try:
        reasons = freeze_preconditions(stage, validation, review)
    except Exception as exc:  # pragma: no cover - safety net
        return [{
            "code": "FREEZE_PRECONDITION_FAILED",
            "description": f"freeze_preconditions raised {type(exc).__name__}: {exc}",
            "evidence": [],
        }]

    # Drop reasons that are signoff-specific or boundary-specific; those
    # should already be reported by their respective classifiers.
    signoff_keywords = ("human_signoff",)
    boundary_keywords = ("boundary_audit", "overclaim", "tensorial", "ibp_started", "dc_caveat_preserved")
    remaining = [
        reason for reason in reasons
        if not any(keyword in reason for keyword in signoff_keywords + boundary_keywords)
    ]
    if not remaining:
        return findings
    findings.append({
        "code": "FREEZE_PRECONDITION_FAILED",
        "description": "freeze_preconditions returned blocking reasons: " + "; ".join(remaining),
        "evidence": [_evidence("freeze_preconditions", stage, exists=True, summary=f"{len(reasons)} reason(s)")],
    })
    return findings


def _classify_missing_decision_checkpoint(stage: Path | None) -> list[dict[str, Any]]:
    """Emit MISSING_REQUIRED_FILE when a stage that otherwise looks freezable
    (PASS validation, PASS/PASS_WITH_CAVEAT review, COMPLETE matrix,
    freeze_eligible True, valid APPROVE_FREEZE signoff) is missing the
    downstream ``.loop/decision.json`` and/or ``.loop/checkpoint_manifest.json``.

    Without these two artifacts the run has nothing to inspect; reporting
    ``UNKNOWN_FAILURE`` for this case hides actionable remediation. The
    evidence list always contains one entry per missing file.
    """
    findings: list[dict[str, Any]] = []
    if stage is None:
        return findings

    validation_path = stage / ".loop" / "validation_summary.json"
    review_path = stage / ".loop" / "review_result.json"
    matrix_path = stage / "reports" / "completion_matrix.json"
    signoff_path = stage / ".loop" / "human_signoff.yaml"

    validation = _safe_read_json(validation_path) if validation_path.exists() else None
    review = _safe_read_json(review_path) if review_path.exists() else None
    matrix = _safe_read_json(matrix_path) if matrix_path.exists() else None
    signoff = _safe_read_yaml(signoff_path) if signoff_path.exists() else None

    # Only fire when every gate the stage SHOULD have cleared has, in fact,
    # cleared. This is "happy-gates but missing artifacts" — the case the
    # reviewer flagged.
    if not (validation and review and matrix and signoff):
        return findings
    if validation.get("overall_gate") != "PASS":
        return findings
    if review.get("verdict") not in {"PASS", "PASS_WITH_CAVEAT"}:
        return findings
    if matrix.get("overall_completion") != "COMPLETE":
        return findings
    if matrix.get("freeze_eligible") is not True:
        return findings
    if signoff.get("decision") not in {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT"}:
        return findings

    # Only fire when the matrix is genuinely fresh against current on-disk
    # basis files. If the matrix is stale, FREEZE_PRECONDITION_FAILED already
    # classifies the run correctly and we should defer to it.
    try:
        from .completion_matrix import validate_completion_matrix_freshness
        fresh, _ = validate_completion_matrix_freshness(stage, matrix)
    except Exception:  # pragma: no cover - safety net
        fresh = False
    if not fresh:
        return findings

    decision_path = stage / ".loop" / "decision.json"
    checkpoint_path = stage / ".loop" / "checkpoint_manifest.json"
    missing: list[Path] = []
    if not decision_path.exists():
        missing.append(decision_path)
    if not checkpoint_path.exists():
        missing.append(checkpoint_path)
    if not missing:
        return findings

    evidence = [
        _evidence(
            "decision" if p.name == "decision.json" else "checkpoint_manifest",
            p,
            exists=False,
        )
        for p in missing
    ]
    rels = [_relative(p) for p in missing]
    findings.append({
        "code": "MISSING_REQUIRED_FILE",
        "description": (
            "stage passed all gates and is signed off, but required post-signoff "
            "artifacts are missing: " + ", ".join(rels)
        ),
        "evidence": evidence,
    })
    return findings


# ---------------------------------------------------------------------------
# Run-root discovery (TASK_024)
# ---------------------------------------------------------------------------


# Required run-root artifacts (run-root-only diagnosis refuses without these).
REQUIRED_RUN_ROOT_PATHS = (
    "stages",
)

# Optional but useful run-root evidence.
OPTIONAL_RUN_ROOT_PATHS = (
    "AUTONOMOUS_LOOP_RUN_REPORT.md",
    "checkpoints",
)


def _read_loop_yaml_stages(project_root: Path) -> list[str] | None:
    """Return ``stages[].id`` order from a project's ``loop.yaml`` if present."""
    if not project_root:
        return None
    loop_yaml = project_root / "loop.yaml"
    if not loop_yaml.exists():
        return None
    try:
        raw = yaml.safe_load(loop_yaml.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    stages = raw.get("stages") or []
    ids: list[str] = []
    for entry in stages:
        if isinstance(entry, dict) and entry.get("id"):
            ids.append(str(entry["id"]))
        elif isinstance(entry, str):
            ids.append(entry)
    return ids or None


def _resolve_stage_order_source(run_root: Path, project: str | None, repo_root: Path | None) -> tuple[list[str], str]:
    """Return (ordered stage ids that exist under run_root, source-label).

    Precedence:

    1. Explicit ``--project`` and ``projects/<project>/loop.yaml``
    2. ``run_root.name`` mapped to ``projects/<run_root.name>/loop.yaml``
    3. Sorted stage directory names
    """
    discovered = sorted(p.name for p in (run_root / "stages").iterdir() if p.is_dir()) if (run_root / "stages").is_dir() else []
    candidates: list[tuple[list[str], str]] = []

    if repo_root is not None and project:
        proj_root = repo_root / "projects" / project
        ids = _read_loop_yaml_stages(proj_root)
        if ids:
            candidates.append((ids, f"projects/{project}/loop.yaml"))

    if repo_root is not None:
        ids = _read_loop_yaml_stages(repo_root / "projects" / run_root.name)
        if ids:
            candidates.append((ids, f"projects/{run_root.name}/loop.yaml"))

    candidates.append((discovered, "lexicographic(stage dirs)"))

    order, source = candidates[0]
    # Keep only ids that are actually stage directories; preserve requested order.
    filtered = [s for s in order if (run_root / "stages" / s).is_dir()]
    if not filtered:
        filtered = discovered
        source = "lexicographic(stage dirs)"
    return filtered, source


def _stage_gate_status(stage: Path) -> dict[str, Any]:
    """Return a small summary of gate artifacts at a stage directory.

    Reads on-demand; never raises. Missing files -> MISSING markers.
    """
    validation_path = stage / ".loop" / "validation_summary.json"
    review_path = stage / ".loop" / "review_result.json"
    decision_path = stage / ".loop" / "decision.json"
    matrix_path = stage / "reports" / "completion_matrix.json"
    signoff_path = stage / ".loop" / "human_signoff.yaml"
    checkpoint_path = stage / ".loop" / "checkpoint_manifest.json"

    validation = _safe_read_json(validation_path) if validation_path.exists() else None
    review = _safe_read_json(review_path) if review_path.exists() else None
    decision = _safe_read_json(decision_path) if decision_path.exists() else None
    matrix = _safe_read_json(matrix_path) if matrix_path.exists() else None
    signoff = _safe_read_yaml(signoff_path) if signoff_path.exists() else None
    checkpoint = _safe_read_json(checkpoint_path) if checkpoint_path.exists() else None

    return {
        "stage_id": stage.name,
        "validation_gate": validation.get("overall_gate") if validation else "MISSING",
        "review_verdict": review.get("verdict") if review else "MISSING",
        "decision": decision.get("decision") if decision else "MISSING",
        "completion": matrix.get("overall_completion") if matrix else "MISSING",
        "freeze_eligible": matrix.get("freeze_eligible") if matrix else None,
        "checkpoint_present": checkpoint is not None,
        "signoff_decision": (signoff or {}).get("decision") if signoff else "MISSING",
    }


def _stage_has_failure_marker(status: dict[str, Any]) -> str | None:
    """Return a short marker for the first failing/blocked gate, or None.

    Priority: validation -> review -> completion -> decision.
    """
    vg = status.get("validation_gate")
    if vg not in (None, "MISSING", "PASS"):
        return f"validation_gate={vg}"
    rv = status.get("review_verdict")
    if rv not in (None, "MISSING", "PASS", "PASS_WITH_CAVEAT"):
        return f"review_verdict={rv}"
    cm = status.get("completion")
    fe = status.get("freeze_eligible")
    if cm not in (None, "MISSING", "COMPLETE") or fe is False:
        return f"completion={cm} freeze_eligible={fe}"
    dec = status.get("decision")
    if dec not in (None, "MISSING"):
        # decision.json present is informational only; skip unless an explicit block.
        return None
    return None


def _select_target_stage(
    *,
    run_root: Path,
    project: str | None,
    repo_root: Path | None,
) -> tuple[Path | None, str, list[str], str]:
    """Select the diagnosis target stage under ``run_root``.

    Returns ``(stage_path | None, selection_reason, ordered_ids, order_source)``.
    Reading only — never mutates any file. ``stage_path`` is None when nothing
    usable exists (no ``stages/`` dir or zero stage dirs).
    """
    stages_dir = run_root / "stages"
    if not stages_dir.is_dir():
        return None, "stages/ directory missing", [], "lexicographic(stage dirs)"

    ordered_ids, order_source = _resolve_stage_order_source(run_root, project, repo_root)
    if not ordered_ids:
        return None, "no stage directories discovered", [], order_source

    statuses: dict[str, dict[str, Any]] = {}
    for sid in ordered_ids:
        sp = stages_dir / sid
        if sp.is_dir():
            statuses[sid] = _stage_gate_status(sp)

    # 1. First stage with a failure/block marker.
    for sid in ordered_ids:
        if sid not in statuses:
            continue
        marker = _stage_has_failure_marker(statuses[sid])
        if marker:
            return stages_dir / sid, f"first failure/block marker: {marker}", ordered_ids, order_source

    # 2. First stage missing required gate artifacts after it appears to have started.
    required_gate_labels = ("validation_gate", "review_verdict", "completion")
    for sid in ordered_ids:
        status = statuses.get(sid)
        if status is None:
            continue
        missing_labels = [k for k in required_gate_labels if status.get(k) == "MISSING"]
        # Treat as "appears to have started" if any gate is present OR checkpoint exists.
        appears_started = any(
            status.get(k) not in (None, "MISSING") for k in required_gate_labels
        ) or status.get("checkpoint_present") is True or status.get("decision") != "MISSING"
        if missing_labels and appears_started:
            return stages_dir / sid, f"missing gate artifacts: {','.join(missing_labels)}", ordered_ids, order_source

    # 3. First stage without a checkpoint manifest when prior ordered stages are frozen.
    def _is_frozen(sid: str) -> bool:
        st = statuses.get(sid)
        if st is None:
            return False
        return (
            st.get("checkpoint_present") is True
            and st.get("validation_gate") == "PASS"
            and st.get("review_verdict") in {"PASS", "PASS_WITH_CAVEAT"}
            and st.get("completion") == "COMPLETE"
            and st.get("freeze_eligible") is True
            and st.get("signoff_decision") in {"APPROVE_FREEZE", "APPROVE_FREEZE_WITH_CAVEAT"}
        )

    for idx, sid in enumerate(ordered_ids):
        if sid not in statuses:
            continue
        prior = ordered_ids[:idx]
        if prior and all(_is_frozen(p) for p in prior if p in statuses):
            if not statuses[sid].get("checkpoint_present"):
                return stages_dir / sid, "prior stages frozen; selected stage missing checkpoint manifest", ordered_ids, order_source

    # 4. All discovered stages appear frozen -> select last, will become UNKNOWN_FAILURE.
    if all(_is_frozen(sid) for sid in ordered_ids if sid in statuses):
        last = ordered_ids[-1]
        if last in statuses:
            return stages_dir / last, "all stages appear frozen; no known failure", ordered_ids, order_source

    # Fallback to first ordered stage so the diagnosis can still proceed.
    first = next((sid for sid in ordered_ids if sid in statuses), None)
    if first is None:
        return None, "no stage directories discovered", ordered_ids, order_source
    return stages_dir / first, "no failure marker; selected first ordered stage", ordered_ids, order_source


def inspect_run_root(run_root: Path, project: str | None = None, *, repo_root: Path | None = None) -> dict[str, Any]:
    """Discover autonomous-loop run artifacts under ``run_root``.

    Pure and read-only: returns a dict with run-root metadata, discovered
    stage statuses, the selected target stage (path, reason), and evidence
    entries suitable for inclusion in a ``next_action_report.json``.
    """
    run_root = Path(run_root)
    repo_root = Path(repo_root) if repo_root is not None else None

    # Required minimum: run_root exists, stages/ exists, at least one stage dir.
    run_root_exists = run_root.exists() and run_root.is_dir()
    stages_dir = run_root / "stages"
    stages_dir_exists = stages_dir.exists() and stages_dir.is_dir()
    discovered: list[str] = []
    if stages_dir_exists:
        discovered = sorted(p.name for p in stages_dir.iterdir() if p.is_dir())

    run_report_exists = (run_root / "AUTONOMOUS_LOOP_RUN_REPORT.md").exists()
    checkpoints_dir_exists = (run_root / "checkpoints").exists()

    target_stage, selection_reason, ordered_ids, order_source = _select_target_stage(
        run_root=run_root,
        project=project,
        repo_root=repo_root,
    )

    statuses = {(run_root / "stages" / sid).name: _stage_gate_status(run_root / "stages" / sid)
                for sid in ordered_ids if (run_root / "stages" / sid).is_dir()}

    # Frozen checkpoint count (best-effort: count frozen entries under checkpoints/).
    frozen_checkpoint_count = 0
    checkpoints_dir = run_root / "checkpoints"
    if checkpoints_dir.exists() and checkpoints_dir.is_dir():
        frozen_checkpoint_count = sum(1 for p in checkpoints_dir.iterdir() if p.is_dir())

    evidence: list[dict[str, Any]] = []
    evidence.append(_evidence("run_root", run_root, exists=run_root_exists))
    evidence.append(_evidence("stages_dir", stages_dir, exists=stages_dir_exists))
    evidence.append(_evidence("autonomous_loop_run_report", run_root / "AUTONOMOUS_LOOP_RUN_REPORT.md", exists=run_report_exists))
    evidence.append(_evidence("checkpoints_dir", run_root / "checkpoints", exists=checkpoints_dir_exists))
    evidence.append({
        "label": "discovered_stage_count",
        "path": _relative(stages_dir),
        "exists": True,
        "summary": str(len(discovered)),
    })
    evidence.append({
        "label": "stage_order_source",
        "path": _relative(run_root),
        "exists": True,
        "summary": order_source,
    })
    if target_stage is not None:
        evidence.append({
            "label": "selected_stage",
            "path": _relative(target_stage),
            "exists": True,
            "summary": selection_reason,
        })

    return {
        "run_root": run_root,
        "run_root_exists": run_root_exists,
        "stages_dir_exists": stages_dir_exists,
        "discovered_stage_ids": discovered,
        "ordered_stage_ids": ordered_ids,
        "stage_order_source": order_source,
        "project": project,
        "run_report_exists": run_report_exists,
        "checkpoints_dir_exists": checkpoints_dir_exists,
        "frozen_checkpoint_count": frozen_checkpoint_count,
        "selected_stage": target_stage,
        "selection_reason": selection_reason,
        "stage_statuses": statuses,
        "evidence": evidence,
        "required_minimum_satisfied": run_root_exists and stages_dir_exists and bool(discovered),
        "repo_root": repo_root,
    }


# ---------------------------------------------------------------------------
# Recommended action derivation
# ---------------------------------------------------------------------------


def _derive_next_action(primary_code: str, gate_status: dict[str, Any]) -> dict[str, Any]:
    """Map primary code + gate summary to a recommended next-action string.

    Uses evidence already collected; does NOT call external services or
    auto-modify anything. Returns a frozen-friendly dict.
    """
    rationale_map = {
        "COMMAND_FAILED": "Inspect command return code / stderr / command_status.json and re-run after fixing the underlying command.",
        "MISSING_REQUIRED_FILE": "Produce the missing stage basis files (STAGE_PLAN.md, CLAIM_BOUNDARY.md, .loop/validation_summary.json, .loop/review_result.json) and re-run diagnosis.",
        "SCHEMA_VALIDATION_FAILED": "Repair the malformed or schema-invalid JSON before re-running diagnosis.",
        "VALIDATION_GATE_FAILED": "Address validation_summary.overall_gate != PASS: see .loop/validation_summary.json::checks and re-run validation.",
        "REVIEW_GATE_FAILED": "Address review_result.verdict: implement patch_instructions and re-submit for review.",
        "COMPLETION_MATRIX_UNHEALTHY": "Inspect reports/completion_matrix.json — resolve blocking items and boundary audit findings before freeze.",
        "HUMAN_SIGNOFF_REQUIRED": "Obtain a human signoff via scripts/sign_stage.py (decision must permit freeze).",
        "FREEZE_PRECONDITION_FAILED": "Resolve freeze_preconditions blocking reasons before invoking scripts/freeze_checkpoint.py.",
        "BOUNDARY_APPROVAL_REQUIRED": "Halt and request explicit human approval for the boundary action (IBP, total derivative, kernel fusion, tensorial claim, candidate promotion, overclaim).",
        "UNKNOWN_FAILURE": "No deterministic rule matched. Inspect .loop/* artifacts and consider asking a human reviewer.",
    }
    recommended = {
        "COMMAND_FAILED": "INSPECT_AND_RETRY",
        "MISSING_REQUIRED_FILE": "PRODUCE_BASIS_FILES",
        "SCHEMA_VALIDATION_FAILED": "REPAIR_JSON",
        "VALIDATION_GATE_FAILED": "PATCH_AND_REVALIDATE",
        "REVIEW_GATE_FAILED": "IMPLEMENT_PATCH_INSTRUCTIONS",
        "COMPLETION_MATRIX_UNHEALTHY": "RESOLVE_BLOCKING_AND_BOUNDARY",
        "HUMAN_SIGNOFF_REQUIRED": "OBTAIN_HUMAN_SIGNOFF",
        "FREEZE_PRECONDITION_FAILED": "RESOLVE_FREEZE_BLOCKERS",
        "BOUNDARY_APPROVAL_REQUIRED": "REQUEST_BOUNDARY_APPROVAL",
        "UNKNOWN_FAILURE": "ASK_HUMAN_REVIEWER",
    }.get(primary_code, "ASK_HUMAN_REVIEWER")

    return {
        "recommended": recommended,
        "rationale": rationale_map.get(primary_code, ""),
        "human_required": primary_code in {
            "HUMAN_SIGNOFF_REQUIRED",
            "BOUNDARY_APPROVAL_REQUIRED",
            "REVIEW_GATE_FAILED",
            "COMPLETION_MATRIX_UNHEALTHY",
            "FREEZE_PRECONDITION_FAILED",
        },
        "boundary_approval_required": primary_code == "BOUNDARY_APPROVAL_REQUIRED",
        "patch_or_reject_recommended": primary_code in {
            "REVIEW_GATE_FAILED",
            "COMPLETION_MATRIX_UNHEALTHY",
            "BOUNDARY_APPROVAL_REQUIRED",
        },
    }


def _forbidden_actions(primary_code: str, gate_status: dict[str, Any]) -> list[str]:
    """List actions the tool must NOT take based on its own contract."""
    forbidden: list[str] = []
    if DIAGNOSIS_READONLY:
        forbidden.extend([
            "modify scientific outputs",
            "modify frozen checkpoint manifests",
            "modify .loop/human_signoff.yaml",
            "modify .loop/human_signoff_ledger.jsonl",
            "modify .loop/human_signoff_history/",
            "auto-freeze checkpoints",
            "auto-patch failed stages",
            "call external LLM reviewer",
        ])
    if primary_code == "BOUNDARY_APPROVAL_REQUIRED":
        forbidden.extend([
            "promote candidate",
            "start IBP without approval",
            "introduce total derivative",
            "claim full tensorial sigma_abc correctness",
        ])
    return forbidden


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def diagnose_run(
    *,
    run_root: Path | None = None,
    stage: Path | None = None,
    project: str | None = None,
    command_return_code: int | None = None,
    stdout_file: Path | None = None,
    stderr_file: Path | None = None,
    command_status_json: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Inspect existing artifacts and return a deterministic next-action report.

    No side effects; safe to call from any context. Writes must go through
    ``write_next_action_reports``.

    When called with ``run_root`` (and no explicit ``stage``), inspects run
    root discovery selects a target stage deterministically and reuses the
    stage-level diagnosis path. ``repo_root`` is auto-detected when None.
    """
    findings: list[dict[str, Any]] = []

    # Run-root discovery whenever --run-root is provided, even alongside an
    # explicit --stage. When stage is explicit, classification is still driven
    # by it (target_stage stays explicit), but run-root metadata + evidence
    # flow through to the report for context.
    run_root_meta: dict[str, Any] | None = None
    auto_resolved_stage: Path | None = None
    auto_resolution_reason: str | None = None

    if run_root is not None:
        if repo_root is None:
            # Lazy auto-detect: walk up from this file looking for the repo root.
            here = Path(__file__).resolve().parent
            for ancestor in [here, *here.parents]:
                if (ancestor / "loop_engine").is_dir() and (ancestor / "schemas").is_dir():
                    repo_root = ancestor
                    break
        run_root_meta = inspect_run_root(Path(run_root), project=project, repo_root=repo_root)
        if not run_root_meta["required_minimum_satisfied"]:
            # Emit MISSING_REQUIRED_FILE for run-root-level gaps.
            run_root_path = Path(run_root)
            missing = []
            if not run_root_meta["run_root_exists"]:
                missing.append("run_root")
            if not run_root_meta["stages_dir_exists"]:
                missing.append(f"{_relative(run_root_path)}/stages")
            if run_root_meta["run_root_exists"] and run_root_meta["stages_dir_exists"] and not run_root_meta["discovered_stage_ids"]:
                missing.append("at least one stage directory under stages/")
            findings.append({
                "code": "MISSING_REQUIRED_FILE",
                "description": "run-root diagnosis missing required artifacts: " + ", ".join(missing),
                "evidence": run_root_meta["evidence"],
            })
        elif stage is None:
            # Only auto-pick a stage when the caller didn't pass --stage.
            auto_resolved_stage = run_root_meta["selected_stage"]
            auto_resolution_reason = run_root_meta["selection_reason"]

    # Schema / Missing / Command checks run first so malformed or absent
    # basis files surface as the primary cause.
    target_stage = stage if stage is not None else auto_resolved_stage
    findings.extend(_classify_schema_failures(target_stage))
    findings.extend(_classify_missing_files(target_stage))
    findings.extend(_classify_boundary_approval(target_stage))
    findings.extend(_classify_validation_gate(target_stage))
    findings.extend(_classify_review_gate(target_stage))
    findings.extend(_classify_completion_matrix(target_stage))
    findings.extend(_classify_human_signoff(target_stage))
    findings.extend(_classify_freeze_preconditions(target_stage))
    findings.extend(_classify_missing_decision_checkpoint(target_stage))

    cmd_failure = _detect_command_failure(
        command_return_code=command_return_code,
        stdout_file=stdout_file,
        stderr_file=stderr_file,
        command_status_json=command_status_json,
    )
    if cmd_failure is not None:
        findings.append(cmd_failure)

    # Deduplicate while preserving order; primary code is the first matched.
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for f in findings:
        code = f["code"]
        if code in seen:
            continue
        seen.add(code)
        unique.append(f)

    if not unique:
        primary_code = "UNKNOWN_FAILURE"
    else:
        # Primary is the highest-precedence finding.
        precedence = [
            "SCHEMA_VALIDATION_FAILED",
            "MISSING_REQUIRED_FILE",
            "BOUNDARY_APPROVAL_REQUIRED",
            "VALIDATION_GATE_FAILED",
            "REVIEW_GATE_FAILED",
            "COMPLETION_MATRIX_UNHEALTHY",
            "HUMAN_SIGNOFF_REQUIRED",
            "FREEZE_PRECONDITION_FAILED",
            "COMMAND_FAILED",
            "UNKNOWN_FAILURE",
        ]
        primary_code = "UNKNOWN_FAILURE"
        for code in precedence:
            if code in seen:
                primary_code = code
                break

    # Build evidence list from all findings.
    evidence: list[dict[str, Any]] = []
    for finding in unique:
        evidence.extend(finding.get("evidence", []))
    if run_root_meta is not None and run_root_meta.get("evidence") is not None:
        # Include run-root discovery evidence even when a target stage was
        # also selected; this gives the consumer visible run-level health.
        evidence.extend(run_root_meta["evidence"])

    # Subject.
    subject_kind = "unknown"
    if stage is not None:
        subject_kind = "stage"
    elif target_stage is not None:
        subject_kind = "stage"  # auto-resolved from run root -> still a stage subject
    elif run_root is not None:
        subject_kind = "run"
    elif command_return_code is not None or command_status_json is not None or stdout_file is not None or stderr_file is not None:
        subject_kind = "command"
    subject: dict[str, Any] = {"kind": subject_kind}
    if target_stage is not None:
        subject["stage_id"] = target_stage.name
    if project:
        subject["project"] = project
    if run_root is not None:
        subject["run_root"] = _relative(run_root)
    if run_root_meta is not None and stage is None:
        # Auto-resolution path: selected_stage/selection_reason/order_source
        # describe the run-root's choice and become authoritative.
        subject["selected_stage"] = _relative(run_root_meta["selected_stage"]) if run_root_meta["selected_stage"] else None
        subject["stage_selection_reason"] = run_root_meta["selection_reason"]
        subject["stage_order_source"] = run_root_meta["stage_order_source"]
    if run_root_meta is not None:
        subject["run_required_minimum_satisfied"] = run_root_meta["required_minimum_satisfied"]
        subject["discovered_stage_count"] = len(run_root_meta["discovered_stage_ids"])
        subject["frozen_checkpoint_count"] = run_root_meta["frozen_checkpoint_count"]
    if stage is not None:
        # Mark explicit-stage mode so consumers can distinguish from auto-resolved.
        subject["explicit_stage"] = True

    # Gate status summary.
    validation_path = target_stage / ".loop" / "validation_summary.json" if target_stage is not None else None
    review_path = target_stage / ".loop" / "review_result.json" if target_stage is not None else None
    matrix_path = target_stage / "reports" / "completion_matrix.json" if target_stage is not None else None
    pre_run_gate_path = target_stage / ".loop" / "pre_run_gate_result.json" if target_stage is not None else None

    validation_data = _safe_read_json(validation_path) if validation_path and validation_path.exists() else None
    review_data = _safe_read_json(review_path) if review_path and review_path.exists() else None
    matrix_data = _safe_read_json(matrix_path) if matrix_path and matrix_path.exists() else None
    pre_run_gate_data = _safe_read_json(pre_run_gate_path) if pre_run_gate_path and pre_run_gate_path.exists() else None

    gate_status: dict[str, Any] = {
        "pre_run_gate": pre_run_gate_data.get("gate") if pre_run_gate_data else "MISSING",
        "validation_gate": (validation_data.get("overall_gate") if validation_data else "MISSING"),
        "review_verdict": review_data.get("verdict") if review_data else "MISSING",
        "completion": matrix_data.get("overall_completion") if matrix_data else "MISSING",
        "freeze_eligible": matrix_data.get("freeze_eligible") if matrix_data else None,
        "command_return_code": command_return_code,
    }

    primary_description = next(
        (f["description"] for f in unique if f["code"] == primary_code),
        "No specific failure matched; treat as unknown.",
    )

    next_action = _derive_next_action(primary_code, gate_status)
    forbidden_actions = _forbidden_actions(primary_code, gate_status)

    diagnostic_warnings: list[str] = []
    if primary_code == "MISSING_REQUIRED_FILE" and (stage is not None or run_root_meta is not None):
        if run_root_meta is not None:
            diagnostic_warnings.append(
                "run-root diagnosis was attempted without complete run-level artifacts; some checks were skipped."
            )
        else:
            diagnostic_warnings.append(
                "stage-mode diagnosis was attempted without complete basis files; some checks were skipped."
            )
    if run_root_meta is not None and run_root_meta.get("selection_reason"):
        diagnostic_warnings.append(
            f"run-root target stage selected by: {run_root_meta['selection_reason']}"
        )
    if primary_code == "UNKNOWN_FAILURE":
        diagnostic_warnings.append(
            "no rule matched; this may indicate a partial run, a new failure mode, or insufficient context."
        )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "classification": {"code": primary_code, "description": primary_description},
        "all_classifications": [{"code": f["code"], "description": f["description"]} for f in unique],
        "subject": subject,
        "evidence": evidence,
        "gate_status": gate_status,
        "next_action": next_action,
        "forbidden_actions": forbidden_actions,
        "diagnostic_warnings": diagnostic_warnings,
        "tool_metadata": {
            "diagnostic_readonly": DIAGNOSIS_READONLY,
            "modified_artifacts": [],
            "generated_at": utc_now(),
        },
    }
    return report


def render_next_action_markdown(report: dict[str, Any]) -> str:
    """Render the report as a deterministic human-readable Markdown document."""
    classification = report.get("classification", {}) or {}
    subject = report.get("subject", {}) or {}
    gate_status = report.get("gate_status", {}) or {}
    next_action = report.get("next_action", {}) or {}
    forbidden_actions = list(report.get("forbidden_actions", []) or [])
    diagnostic_warnings = list(report.get("diagnostic_warnings", []) or [])
    tool_metadata = report.get("tool_metadata", {}) or {}

    lines: list[str] = []
    lines.append("# Next Action Report")
    lines.append("")
    lines.append(f"- Schema version: `{report.get('schema_version', '')}`")
    lines.append(f"- Subject kind: `{subject.get('kind', 'unknown')}`")
    if subject.get("stage_id"):
        lines.append(f"- Stage: `{subject['stage_id']}`")
    if subject.get("project"):
        lines.append(f"- Project: `{subject['project']}`")
    if subject.get("run_root"):
        lines.append(f"- Run root: `{subject['run_root']}`")
    if subject.get("selected_stage") is not None:
        lines.append(f"- Selected stage: `{subject['selected_stage']}`")
    if subject.get("stage_selection_reason"):
        lines.append(f"- Selection reason: {subject['stage_selection_reason']}")
    if subject.get("stage_order_source"):
        lines.append(f"- Stage order source: `{subject['stage_order_source']}`")
    if subject.get("discovered_stage_count") is not None:
        lines.append(f"- Discovered stage count: `{subject['discovered_stage_count']}`")
    if subject.get("frozen_checkpoint_count") is not None:
        lines.append(f"- Frozen checkpoint count: `{subject['frozen_checkpoint_count']}`")
    lines.append("")

    lines.append("## Primary classification")
    lines.append("")
    lines.append(f"- Code: **{classification.get('code', 'UNKNOWN_FAILURE')}**")
    lines.append(f"- Description: {classification.get('description', '')}")
    lines.append("")

    lines.append("## All classifications (secondary findings)")
    lines.append("")
    all_classifications = report.get("all_classifications", []) or []
    if all_classifications:
        lines.append("| Code | Description |")
        lines.append("|---|---|")
        for entry in all_classifications:
            lines.append(f"| {entry.get('code', '')} | {entry.get('description', '')} |")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Gate status")
    lines.append("")
    lines.append(f"- Pre-run gate: `{gate_status.get('pre_run_gate', 'MISSING')}`")
    lines.append(f"- Validation gate: `{gate_status.get('validation_gate', 'MISSING')}`")
    lines.append(f"- Review verdict: `{gate_status.get('review_verdict', 'MISSING')}`")
    lines.append(f"- Completion: `{gate_status.get('completion', 'MISSING')}`")
    freeze_eligible = gate_status.get("freeze_eligible")
    lines.append(f"- Freeze eligible: `{freeze_eligible}`")
    rc = gate_status.get("command_return_code")
    lines.append(f"- Command return code: `{rc}`")
    lines.append("")

    lines.append("## Evidence")
    lines.append("")
    evidence = report.get("evidence", []) or []
    if evidence:
        lines.append("| Label | Path | Exists | Summary |")
        lines.append("|---|---|---|---|")
        for entry in evidence:
            lines.append(
                f"| {entry.get('label', '')} | `{entry.get('path', '')}` | "
                f"{entry.get('exists', False)} | {entry.get('summary', '')} |"
            )
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Recommended next action")
    lines.append("")
    lines.append(f"- Recommended: **{next_action.get('recommended', 'ASK_HUMAN_REVIEWER')}**")
    lines.append(f"- Rationale: {next_action.get('rationale', '')}")
    lines.append(f"- Human required: `{next_action.get('human_required', False)}`")
    lines.append(f"- Boundary approval required: `{next_action.get('boundary_approval_required', False)}`")
    lines.append(f"- Patch-or-reject recommended: `{next_action.get('patch_or_reject_recommended', False)}`")
    lines.append("")

    if forbidden_actions:
        lines.append("## Forbidden actions (diagnostic contract)")
        lines.append("")
        for action in forbidden_actions:
            lines.append(f"- {action}")
        lines.append("")

    if diagnostic_warnings:
        lines.append("## Diagnostic warnings")
        lines.append("")
        for warning in diagnostic_warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.append("## Read-only guarantee")
    lines.append("")
    lines.append(
        "This report was produced by `loop_engine.run_diagnosis.diagnose_run(...)` and is "
        "guaranteed to be read-only. The diagnostic tool did NOT modify scientific artifacts, "
        "frozen checkpoint manifests, signoff ledgers, signoff history, completion matrices, "
        "review results, or validation summaries."
    )
    lines.append("")
    lines.append(f"- Diagnostic read-only: `{tool_metadata.get('diagnostic_readonly', True)}`")
    lines.append(f"- Modified artifacts: `{tool_metadata.get('modified_artifacts', [])}`")
    lines.append(f"- Generated at: `{tool_metadata.get('generated_at', '')}`")
    lines.append("")
    return "\n".join(lines)


def write_next_action_reports(
    report: dict[str, Any],
    output_dir: Path,
    *,
    json_only: bool = False,
    markdown_only: bool = False,
) -> tuple[Path, Path]:
    """Write the JSON and Markdown report to ``output_dir``.

    Always validates the JSON against the ``next_action_report`` schema
    before writing, so a caller cannot persist a malformed report.
    Returns ``(json_path, md_path)``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "next_action_report.json"
    md_path = output_dir / "next_action_report.md"

    if not markdown_only:
        # Validate the report shape before writing so callers can't persist garbage.
        validate_with_schema(report, "next_action_report")
        write_json(json_path, report)
    if not json_only:
        write_text(md_path, render_next_action_markdown(report))
    return json_path, md_path


__all__ = [
    "diagnose_run",
    "render_next_action_markdown",
    "write_next_action_reports",
    "inspect_run_root",
    "CLASSIFICATION_CODES",
    "SCHEMA_VERSION",
    "DIAGNOSIS_READONLY",
    "STAGE_BASIS",
]