# Verifier Role

The verifier checks symbolic exactness and protected regressions.

## Required Gates

- Exact reconstruction gate
- Basis closure gate
- Kernel fusion gate
- IBP equivalence gate
- Regression preservation gate
- Projection benchmark gate
- Claim boundary gate

## Identity Types

```text
OldMinusNewZero:
  OldExpression - NewExpression == 0

IBPEquivalence:
  OldExpression - NewExpression - D[F,k] == 0

ProjectionRegression:
  TensorFormula[xxx] - SigmaXXXReference == 0

NumericalRegression:
  MaxAbsDifference < tolerance
```

For `sigma_abc`, the protected benchmark is:

```text
ProjectToXXX[tensor_formula] - sigma_xxx_final_reference == 0
```

