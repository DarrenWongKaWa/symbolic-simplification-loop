# sigma_xxx Projection Benchmark

## Purpose

Register the known projected `sigma_xxx` final checkpoint as the future projection benchmark for the tensorial `sigma_abc` project.

## Known Final Basis

- `K_c`
- `K_R`
- `K_ReL`
- `K_ImL`

## Known Benchmark Path

```text
118 raw rows -> 208 coefficient rows -> 7 kernels -> 4 kernels + partial_k F_pair_total
10 residuals -> 6 cokernel -> 0 cokernel
DeltaKR -> 0
Anan Eq.(6) regression -> inherited PASS
Modify4-to-Modify5 Rice-Mele consistency -> PASS
```

## Future Hard Benchmark

```text
ProjectToXXX[sigma_mu_alpha_beta] - sigma_xxx_final_reference == 0
```

The final kernel-level projection benchmark is deferred until the reference files and tensorial raw ledger are both available in compatible machine-readable form.

Stage 001b caveat preserved: DCProjectionTo1D is INHERITED_PASS from finite-frequency xxx projection plus the archived 1D DC notebook pipeline, not a direct full tensorial DC-series PASS.
