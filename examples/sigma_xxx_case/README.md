# sigma_xxx Reference Case

This is the benchmark metadata for the completed projected one-dimensional multiband `sigma^xxx` simplification. It is not a full tensorial `sigma_{mu alpha beta}` derivation.

## Final Projected Basis

- `K_c`: single-band center velocity-power kernel.
- `K_R`: two-band pair shift-vector kernel.
- `K_ReL`: three-band loop real-interference kernel.
- `K_ImL`: three-band loop imaginary-interference kernel.

## Benchmark Progression

```text
118 raw rows -> 208 coefficient rows -> 7 kernels -> 4 kernels + dF_pair_total
10 residuals -> 6 cokernel -> 0 cokernel
DeltaKR -> 0
Anan Eq.(6) regression -> inherited PASS
Modify4-to-Modify5 Rice-Mele consistency -> PASS
```

## Claim Boundary

Allowed:

- Projected 1D `sigma^xxx` pair velocity sectors are IBP-exact at the final checkpoint.
- The projected pair sector reduces modulo BZ total derivatives to the pair shift-vector kernel.
- The final projected basis has center, pair-shift, loop-Re, and loop-Im kernel families.

Forbidden:

- Full tensorial `sigma_{mu alpha beta}` correctness.
- Full equality to Anan Eq.(5).
- General center or loop vanishing.

