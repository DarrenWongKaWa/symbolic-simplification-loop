from __future__ import annotations

from pathlib import Path

from loop_engine.config import REPO_ROOT, read_json, write_json, write_text
from loop_engine.packet_builder import build_review_packet
from loop_engine.reviewer import aggregate_review_results, build_reviewer_agent_prompt, build_reviewer_agent_prompts


def test_review_packet_includes_validation_metrics_and_claim_boundary(tmp_path: Path):
    stage = tmp_path / "project" / "stages" / "000_raw_import"
    (stage / ".loop").mkdir(parents=True)
    (stage / "output").mkdir()
    write_text(stage / "STAGE_PLAN.md", "# Stage Plan\n\nProtected regression: sigma_xxx\n")
    write_text(stage / "EXECUTION_REPORT.md", "# Execution Report\n\nFiles created.\n")
    write_text(stage / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\nForbidden: overclaim.\n")
    write_json(stage / ".loop" / "metrics.json", {"before": {"rows": 118}, "after": {"kernels": 4}})
    write_json(stage / ".loop" / "validation_summary.json", {"stage_name": "000_raw_import", "overall_gate": "PASS", "checks": []})
    packet = build_review_packet(stage)
    text = packet.read_text(encoding="utf-8")
    assert "sigma_xxx" in text
    assert '"rows": 118' in text
    assert "Forbidden: overclaim" in text
    assert "Structured Reviewer Packet" in text
    assert "codex_subagent" in text
    assert "AlgebraReviewer" in text
    assert "web-GPT audit" in text
    assert "Codex app `/review`" in text
    assert "Do not replace verifier scripts" in text


def test_reviewer_agent_prompt_is_read_only_and_not_verifier(tmp_path: Path):
    stage = tmp_path / "project" / "stages" / "000_raw_import"
    stage.mkdir(parents=True)
    write_text(stage / "review_packet.md", "# Structured Reviewer Packet\n")
    prompt = build_reviewer_agent_prompt(stage)
    text = prompt.read_text(encoding="utf-8")
    assert "Do not edit code" in text
    assert "Do not replace verifier scripts" in text
    assert "validation_summary.overall_gate" in text
    assert '"verdict": "PASS | PASS_WITH_CAVEAT | NEEDS_PATCH | FAILED"' in text


def test_full_panel_read_only_reviewer_prompts(tmp_path: Path):
    stage = tmp_path / "project" / "stages" / "000_raw_import"
    stage.mkdir(parents=True)
    write_text(stage / "review_packet.md", "# Structured Reviewer Packet\n")
    prompts = build_reviewer_agent_prompts(stage)
    names = {path.name for path in prompts}
    assert names == {
        "reviewer_agent_prompt.AlgebraReviewer.md",
        "reviewer_agent_prompt.PhysicsReviewer.md",
        "reviewer_agent_prompt.ScientificMetaReviewer.md",
        "reviewer_agent_prompt.SoftwareReviewer.md",
    }
    texts = {path.name: path.read_text(encoding="utf-8") for path in prompts}
    assert "Old - New - dF" in texts["reviewer_agent_prompt.AlgebraReviewer.md"]
    assert "basis" in texts["reviewer_agent_prompt.PhysicsReviewer.md"]
    assert "scientific claim boundary" in texts["reviewer_agent_prompt.ScientificMetaReviewer.md"]
    assert "stale" in texts["reviewer_agent_prompt.SoftwareReviewer.md"]
    assert all('sandbox_mode = "read-only"' in text for text in texts.values())


def test_aggregate_role_review_results(tmp_path: Path):
    stage = tmp_path / "project" / "stages" / "000_raw_import"
    reviews = stage / ".loop" / "reviews"
    reviews.mkdir(parents=True)

    def write_review(role: str, verdict: str, caveats: list[str] | None = None):
        write_json(
            reviews / f"review_result.{role}.json",
            {
                "verdict": verdict,
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
                "nonblocking_caveats": caveats or [],
                "allowed_claims": [f"{role} allowed"],
                "forbidden_claims": [f"{role} forbidden"],
                "next_action": "FREEZE",
                "suggested_next_stage": None,
                "patch_instructions": [],
            },
        )

    write_review("AlgebraReviewer", "PASS")
    write_review("PhysicsReviewer", "PASS_WITH_CAVEAT", ["physics caveat"])
    write_review("SoftwareReviewer", "PASS")

    target = aggregate_review_results(stage)
    aggregate = read_json(target)
    assert aggregate["verdict"] == "PASS_WITH_CAVEAT"
    assert aggregate["reviewer_role"] == "IntegratorReview"
    assert aggregate["nonblocking_caveats"] == ["physics caveat"]
    assert len(aggregate["source_review_files"]) == 3


def test_sigma_xxx_benchmark_metadata_loads():
    manifest = read_json(REPO_ROOT / "examples" / "sigma_xxx_case" / "final_checkpoint_manifest.json")
    benchmark = read_json(REPO_ROOT / "examples" / "sigma_xxx_case" / "benchmark_sigma_xxx_projection.json")
    assert manifest["final_basis"] == ["K_c", "K_R", "K_ReL", "K_ImL"]
    assert manifest["progression"]["surviving_kernels"] == 4
    assert "ProjectToXXX" in benchmark["identity"]
