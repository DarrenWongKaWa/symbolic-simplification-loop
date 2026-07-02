from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from loop_engine.scientist_review.stage_dossier import classify_verification


REPO_ROOT = Path(__file__).resolve().parents[1]
DC_CAVEAT = "DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS."


def _run_builder(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "build_scientist_review_packet.py"),
            "--project",
            "sigma_abc",
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_build_scientist_review_packet_generates_core_files(tmp_path: Path):
    output = tmp_path / "scientist_review" / "sigma_abc"
    result = _run_builder(output)

    assert result.returncode == 0, result.stderr
    for name in [
        "DASHBOARD.md",
        "VALIDATION_LEDGER.md",
        "SCRIPT_MAP.md",
        "CLAIM_BOUNDARY.md",
        "SIGNOFF_PACKET.md",
        "SCIENTIST_REVIEW_PACKET.md",
        "SCIENTIST_REVIEW_PACKET.tex",
    ]:
        assert (output / name).exists(), name
    assert (output / "STAGE_DOSSIERS").is_dir()
    assert list((output / "STAGE_DOSSIERS").glob("*.md"))


def test_build_scientist_review_packet_does_not_create_human_signoff(tmp_path: Path):
    output = tmp_path / "scientist_review" / "sigma_abc"
    result = _run_builder(output)

    assert result.returncode == 0, result.stderr
    assert not list(output.rglob("human_signoff.yaml"))
    assert "This packet does not create or replace human_signoff.yaml" in (
        output / "SIGNOFF_PACKET.md"
    ).read_text(encoding="utf-8")


def test_build_scientist_review_packet_preserves_dc_caveat_and_live_divergence(tmp_path: Path):
    output = tmp_path / "scientist_review" / "sigma_abc"
    result = _run_builder(output)

    assert result.returncode == 0, result.stderr
    dashboard = (output / "DASHBOARD.md").read_text(encoding="utf-8")
    signoff_packet = (output / "SIGNOFF_PACKET.md").read_text(encoding="utf-8")
    claim_boundary = (output / "CLAIM_BOUNDARY.md").read_text(encoding="utf-8")
    packet = (output / "SCIENTIST_REVIEW_PACKET.md").read_text(encoding="utf-8")
    assert DC_CAVEAT in dashboard
    assert DC_CAVEAT in signoff_packet
    assert DC_CAVEAT in claim_boundary
    assert DC_CAVEAT in packet
    assert "live-root vs devlog divergence" in dashboard
    assert "live-root vs devlog divergence" in signoff_packet
    assert "011/012A/012B/012C-prep" in dashboard
    assert "011/012A/012B/012C-prep" in signoff_packet


def test_build_scientist_review_packet_classifies_inventory_without_old_new(tmp_path: Path):
    output = tmp_path / "scientist_review" / "sigma_abc"
    result = _run_builder(output)

    assert result.returncode == 0, result.stderr
    ledger = (output / "VALIDATION_LEDGER.md").read_text(encoding="utf-8")
    dossiers = "\n".join(p.read_text(encoding="utf-8") for p in (output / "STAGE_DOSSIERS").glob("*.md"))
    assert "inventory_only" in ledger or "preparation_gate" in ledger
    assert "not an exact-zero identity" in dossiers
    assert "Old - New = 0" not in dossiers


def test_build_scientist_review_packet_redacts_runtime_local_yaml(tmp_path: Path):
    output = tmp_path / "scientist_review" / "sigma_abc"
    result = _run_builder(output)

    assert result.returncode == 0, result.stderr
    packet = (output / "SCIENTIST_REVIEW_PACKET.md").read_text(encoding="utf-8")
    assert "runtime.local.yaml" in packet
    assert "REDACTED" in packet
    assert "OPENAI_API_KEY=" not in packet


def test_build_scientist_review_packet_does_not_create_forbidden_artifacts(tmp_path: Path):
    output = tmp_path / "scientist_review" / "sigma_abc"
    result = _run_builder(output)

    assert result.returncode == 0, result.stderr
    forbidden_patterns = [
        "*sigma_abc_012c_loop_orbit_canonicalization_promotion*",
        "*sigma_abc_013_global_pre_ibp_assembly*",
        "*tensorial*ibp*",
        "*total*derivative*",
    ]
    found: list[Path] = []
    for pattern in forbidden_patterns:
        found.extend(output.rglob(pattern))
    assert found == []


def test_non_exact_verification_types_are_not_mislabeled_old_new_zero(tmp_path: Path):
    inherited_stage = tmp_path / "sigma_abc_001b_dc_projection_validation_patch"
    inventory_stage = tmp_path / "sigma_abc_012a_loop_sector_inventory"
    prep_stage = tmp_path / "sigma_abc_012c_real_loop_candidate_preparation"

    inherited = classify_verification(
        inherited_stage,
        {
            "overall_gate": "PASS",
            "checks": [
                {
                    "name": "DCProjectionTo1D",
                    "actual": "INHERITED_PASS",
                    "expected": "INHERITED_PASS",
                    "gate": "PASS",
                }
            ],
            "caveats": [DC_CAVEAT],
        },
    )
    inventory = classify_verification(
        inventory_stage,
        {
            "overall_gate": "PASS",
            "checks": [],
            "caveats": [DC_CAVEAT],
        },
    )
    preparation = classify_verification(
        prep_stage,
        {
            "overall_gate": "PASS",
            "checks": [
                {"name": "Stage012AArtifactPresent", "actual": True, "gate": "PASS"},
                {"name": "NoCandidatePromoted", "actual": True, "gate": "PASS"},
            ],
            "caveats": [DC_CAVEAT],
        },
    )

    assert inherited["type"] == "inherited_pass"
    assert inventory["type"] == "inventory_only"
    assert preparation["type"] == "preparation_gate"
    for verification in [inherited, inventory, preparation]:
        assert verification["identity_plaintext"] != "Old - New = 0"
        assert "Old - New = 0" not in verification["identity_plaintext"]
