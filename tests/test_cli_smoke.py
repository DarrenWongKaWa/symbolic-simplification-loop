from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True)


def test_cli_smoke_init_packet_decide_freeze(tmp_path: Path):
    run([sys.executable, str(REPO_ROOT / "scripts" / "init_project.py"), "--name", "demo"], tmp_path)
    project = tmp_path / "demo"
    run([sys.executable, str(REPO_ROOT / "scripts" / "init_stage.py"), "--project", str(project), "--stage", "000_raw_import"], tmp_path)
    stage = project / "stages" / "000_raw_import"

    (stage / ".loop" / "validation_summary.json").write_text(
        json.dumps(
            {
                "stage_name": "000_raw_import",
                "overall_gate": "PASS",
                "identity_type": "OldMinusNewZero",
                "checks": [{"name": "exact", "expected": "0", "actual": "0", "gate": "PASS"}],
            }
        ),
        encoding="utf-8",
    )
    review_file = tmp_path / "review.json"
    review_file.write_text(
        json.dumps(
            {
                "verdict": "PASS",
                "stage_name": "000_raw_import",
                "mathematical_status": {
                    "exact_reconstruction": True,
                    "simplification_real": True,
                    "regression_preserved": True,
                    "overclaim_detected": False,
                },
                "blocking_issues": [],
                "nonblocking_caveats": [],
                "allowed_claims": ["allowed"],
                "forbidden_claims": ["forbidden"],
                "next_action": "FREEZE",
                "suggested_next_stage": None,
                "patch_instructions": [],
            }
        ),
        encoding="utf-8",
    )

    run([sys.executable, str(REPO_ROOT / "scripts" / "build_review_packet.py"), "--stage", str(stage)], tmp_path)
    assert (stage / "review_packet.md").exists()
    run([sys.executable, str(REPO_ROOT / "scripts" / "build_reviewer_agent_prompt.py"), "--stage", str(stage)], tmp_path)
    assert (stage / "reviewer_agent_prompt.md").exists()
    run([sys.executable, str(REPO_ROOT / "scripts" / "build_reviewer_agent_prompts.py"), "--stage", str(stage)], tmp_path)
    assert (stage / "reviewer_agent_prompt.AlgebraReviewer.md").exists()
    assert (stage / "reviewer_agent_prompt.PhysicsReviewer.md").exists()
    assert (stage / "reviewer_agent_prompt.SoftwareReviewer.md").exists()
    reviews_dir = stage / ".loop" / "reviews"
    reviews_dir.mkdir(parents=True)
    for role in ["AlgebraReviewer", "PhysicsReviewer", "SoftwareReviewer"]:
        (reviews_dir / f"review_result.{role}.json").write_text(
            json.dumps(
                {
                    "verdict": "PASS",
                    "stage_name": "000_raw_import",
                    "reviewer_role": role,
                    "review_scope": "routine_branch",
                    "mathematical_status": {
                        "exact_reconstruction": True,
                        "simplification_real": True,
                        "regression_preserved": True,
                        "overclaim_detected": False,
                    },
                    "blocking_issues": [],
                    "nonblocking_caveats": [],
                    "allowed_claims": ["allowed"],
                    "forbidden_claims": ["forbidden"],
                    "next_action": "FREEZE",
                    "suggested_next_stage": None,
                    "patch_instructions": [],
                }
            ),
            encoding="utf-8",
        )
    run([sys.executable, str(REPO_ROOT / "scripts" / "aggregate_review_results.py"), "--stage", str(stage)], tmp_path)
    run([sys.executable, str(REPO_ROOT / "scripts" / "import_review_result.py"), "--stage", str(stage), "--file", str(review_file)], tmp_path)
    run([sys.executable, str(REPO_ROOT / "scripts" / "decide_next_action.py"), "--stage", str(stage)], tmp_path)
    decision = json.loads((stage / ".loop" / "decision.json").read_text(encoding="utf-8"))
    assert decision["action"] == "FREEZE"
    run([sys.executable, str(REPO_ROOT / "scripts" / "freeze_checkpoint.py"), "--stage", str(stage)], tmp_path)
    assert list((project / "checkpoints").iterdir())


def test_full_loop_smoke_runner_cli_loads():
    result = run([sys.executable, str(REPO_ROOT / "scripts" / "run_full_loop_smoke_test.py"), "--help"], REPO_ROOT)
    assert "--clean" in result.stdout
