# Validation Ledger

| Stage | Verification type | Identity checked | Expected | Actual | Gate | Evidence | Claim boundary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `sigma_abc_006_tensorial_sector_architecture_review` | inventory_only | `Inventory/provenance checkpoint; this is not an exact-zero identity.` | `no forbidden fusion/IBP/promotion` | `PASS` | PASS | `.loop/validation_summary.json`, `reports/completion_matrix.json` | DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.; Safe pre-fusion metadata stage; no tensorial IBP or full tensorial kernel fusion was run. |
| `sigma_abc_007_pair_sector_basis_closure_pilot` | inventory_only | `Inventory/provenance checkpoint; this is not an exact-zero identity.` | `no forbidden fusion/IBP/promotion` | `PASS` | PASS | `.loop/validation_summary.json`, `reports/completion_matrix.json` | DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.; Safe pre-fusion metadata stage; no tensorial IBP or full tensorial kernel fusion was run. |
| `sigma_abc_008_pair_sector_xxx_regression_and_next_basis_decision` | projection_regression | `ProjectToXXX[sigma_mu_alpha_beta] - sigma_xxx_final_reference = 0` | `PASS` | `PASS` | PASS | `.loop/validation_summary.json` | DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.; Safe pre-fusion metadata stage; no tensorial IBP or full tensorial kernel fusion was run. |

## Notes

- `inventory_only` and `preparation_gate` stages are not exact-zero identities.
- `inherited_pass` is allowed only with documented provenance and preserved caveats.
- This ledger is human-facing and does not replace `validation_summary.json`.
