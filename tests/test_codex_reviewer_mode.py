from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from loop_engine.decision import decide_next_action
from loop_engine.reviewer import DEFAULT_REVIEW_MODE, aggregate_review_results, load_review_mode


REPO_ROOT = Path(__file__).resolve().parents[1]


def make_stage(tmp_path: Path, validation_gate: str = "PASS") -> Path:
    stage = tmp_path / "stage"
    (stage / ".loop").mkdir(parents=True)
    (stage / "validation").mkdir()
    (stage / ".loop" / "validation_summary.json").write_text(
        json.dumps(
            {
                "stage_name": stage.name,
                "overall_gate": validation_gate,
                "identity_type": "OldMinusNewZero",
                "checks": [{"name": "identity", "expected": 0, "actual": 0, "gate": validation_gate}],
            }
        ),
        encoding="utf-8",
    )
    (stage / ".loop" / "metrics.json").write_text(json.dumps({"stage_name": stage.name}), encoding="utf-8")
    (stage / "review_packet.md").write_text("# Review Packet\n\nAll gates look good.\n", encoding="utf-8")
    (stage / "CLAIM_BOUNDARY.md").write_text("# Claim Boundary\n\nNo overclaims.\n", encoding="utf-8")
    return stage


def write_role(stage: Path, role_file: str, verdict: str = "PASS") -> None:
    role_map = {
        "algebra_reviewer": "AlgebraReviewer",
        "physics_reviewer": "PhysicsReviewer",
        "software_reviewer": "SoftwareReviewer",
    }
    target = stage / ".loop" / "reviewer_results" / f"{role_file}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "verdict": verdict,
                "stage_name": stage.name,
                "reviewer_role": role_map[role_file],
                "review_scope": "routine_branch",
                "mathematical_status": {
                    "exact_reconstruction": True,
                    "simplification_real": False,
                    "regression_preserved": True,
                    "overclaim_detected": False,
                },
                "blocking_issues": ["needs patch"] if verdict == "NEEDS_PATCH" else [],
                "nonblocking_caveats": ["minor caveat"] if verdict == "PASS_WITH_CAVEAT" else [],
                "allowed_claims": ["allowed"],
                "forbidden_claims": ["forbidden"],
                "next_action": "PATCH" if verdict == "NEEDS_PATCH" else "FREEZE",
                "suggested_next_stage": None,
                "patch_instructions": ["patch"] if verdict == "NEEDS_PATCH" else [],
            }
        ),
        encoding="utf-8",
    )


def run(cmd: list[str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True)


def test_default_review_mode_is_codex_subagent(tmp_path: Path):
    stage = make_stage(tmp_path)
    assert DEFAULT_REVIEW_MODE == "codex_subagent"
    assert load_review_mode(stage) == "codex_subagent"


def test_run_reviewer_agents_creates_three_structured_results(tmp_path: Path):
    stage = make_stage(tmp_path)
    run([sys.executable, str(REPO_ROOT / "scripts" / "run_reviewer_agents.py"), "--stage", str(stage)])

    for name in ["algebra_reviewer", "physics_reviewer", "software_reviewer"]:
        assert (stage / ".loop" / "reviewer_results" / f"{name}.json").exists()

    run([sys.executable, str(REPO_ROOT / "scripts" / "aggregate_review_results.py"), "--stage", str(stage)])
    aggregate = json.loads((stage / ".loop" / "review_result.json").read_text(encoding="utf-8"))
    assert aggregate["verdict"] == "PASS"
    assert aggregate["next_action"] == "FREEZE"


def test_missing_reviewer_output_blocks_freeze(tmp_path: Path):
    stage = make_stage(tmp_path)
    write_role(stage, "algebra_reviewer")
    write_role(stage, "physics_reviewer")

    target = aggregate_review_results(stage)
    review = json.loads(target.read_text(encoding="utf-8"))
    assert review["verdict"] == "NEEDS_PATCH"
    assert review["next_action"] == "PATCH"

    decision = decide_next_action(json.loads((stage / ".loop" / "validation_summary.json").read_text()), review)
    assert not decision.freeze_allowed


def test_reviewer_disagreement_produces_caveat_or_patch(tmp_path: Path):
    stage = make_stage(tmp_path)
    write_role(stage, "algebra_reviewer", "PASS")
    write_role(stage, "physics_reviewer", "PASS_WITH_CAVEAT")
    write_role(stage, "software_reviewer", "PASS")

    review = json.loads(aggregate_review_results(stage).read_text(encoding="utf-8"))
    assert review["verdict"] == "PASS_WITH_CAVEAT"
    assert review["next_action"] == "FREEZE"

    stage2 = make_stage(tmp_path / "patch")
    write_role(stage2, "algebra_reviewer", "PASS")
    write_role(stage2, "physics_reviewer", "NEEDS_PATCH")
    write_role(stage2, "software_reviewer", "PASS")

    review2 = json.loads(aggregate_review_results(stage2).read_text(encoding="utf-8"))
    assert review2["verdict"] == "NEEDS_PATCH"
    assert review2["next_action"] == "PATCH"


def test_validation_fail_overrides_reviewer_pass(tmp_path: Path):
    stage = make_stage(tmp_path, validation_gate="FAIL")
    for role in ["algebra_reviewer", "physics_reviewer", "software_reviewer"]:
        write_role(stage, role, "PASS")

    review = json.loads(aggregate_review_results(stage).read_text(encoding="utf-8"))
    validation = json.loads((stage / ".loop" / "validation_summary.json").read_text(encoding="utf-8"))
    decision = decide_next_action(validation, review)
    assert decision.action == "DO_NOT_FREEZE"
    assert not decision.freeze_allowed

