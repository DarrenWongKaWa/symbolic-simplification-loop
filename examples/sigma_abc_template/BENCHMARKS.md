# sigma_abc Benchmarks

## Protected Projection Gate

```text
ProjectToXXX[sigma_abc_tensor_formula] - sigma_xxx_final_reference == 0
```

This is the first required global benchmark.

## Accepted Symbolic Gate

```text
FullSimplify[ProjectToXXX[tensor_formula] - sigma_xxx_reference] == 0
```

## Numerical Fallback

If symbolic comparison is impossible:

```text
MaxAbsDifference < tolerance
```

The tolerance, sampling domain, random seeds, and caveat must be recorded.

## Reference sigma_xxx Basis

- center velocity-power
- pair shift-vector
- loop Re/Im three-band interference

