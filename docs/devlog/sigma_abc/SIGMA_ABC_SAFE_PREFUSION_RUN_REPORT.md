# Sigma ABC Safe Pre-Fusion Run Report

## Scope

This run uses the repo-native autonomous runner with
`profile=sigma_abc_safe_pre_fusion`.  It advances only the safe pre-fusion
architecture/pair-basis/regression-decision stages authorized by the profile.

It does not run tensorial IBP, full tensorial kernel fusion, global coupled
tensorial solve, paper supplement writing, or any full tensorial correctness
claim.

## Stages Attempted

| Stage | Status | Validation | Review | Decision | Frozen | Patch attempts |
| --- | --- | --- | --- | --- | --- | --- |
| `sigma_abc_006_tensorial_sector_architecture_review` | FROZEN | PASS | PASS | FREEZE | yes | 0 |
| `sigma_abc_007_pair_sector_basis_closure_pilot` | FROZEN | PASS | PASS | FREEZE | yes | 0 |
| `sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision` | FROZEN | PASS | PASS | FREEZE | yes | 0 |

## Summary

- stages_attempted: 3
- stages_frozen: 3
- stages_patched: 0
- stages_failed: 0
- frozen_checkpoints: ["sigma_abc_006_tensorial_sector_architecture_review", "sigma_abc_007_pair_sector_basis_closure_pilot", "sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision"]
- reviewer_mode: `codex_subagent`
- protected_benchmark: `sigma_xxx_projection`
- hard_stop_policy: `sigma_abc_hard_stops`
- recommended_next_profile: `sigma_abc_pair_basis_refinement`
- human_approval_required_before_continuing: `False`

## Known Sector Ledger

```json
{
  "center_contact_sector": 93,
  "loop_three_band_sector": 288,
  "pair_two_band_sector": 912,
  "total_rows": 1293,
  "unclassified": 0
}
```

## Known Gates Preserved

```json
{
  "DCProjectionStillInheritedPASS": true,
  "RawMinusSectorSum": 0,
  "RawProjectionStillPASS": true,
  "SectorLedgerXXXCollapse": "PASS"
}
```

## Known Caveats

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Frozen Checkpoints Protected

```json
[
  "sigma_abc_001_raw_generator_checkpoint_v1",
  "sigma_abc_002_raw_import_and_convention_audit_checkpoint_v1",
  "sigma_abc_003_xxx_projection_benchmark_hardening_checkpoint_v1",
  "sigma_abc_004_tensorial_raw_sector_decomposition_ledger_checkpoint_v1",
  "sigma_abc_005_sector_ledger_xxx_collapse_regression_checkpoint_v1"
]
```

## Forbidden Actions Not Run

- tensorial IBP
- full tensorial kernel fusion
- global coupled tensorial solve
- paper supplement writing
- full tensorial correctness claim

## Recommended Next Step

If continuation is desired, use the recommended profile explicitly:

```bash
python3 scripts/run_autonomous_loop.py --project sigma_abc --profile sigma_abc_pair_basis_refinement --from-current-checkpoint
```

Do not continue automatically from this report.
