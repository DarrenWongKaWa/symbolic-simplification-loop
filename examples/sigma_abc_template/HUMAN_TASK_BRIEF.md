# Human Task Brief: sigma_abc

## Project Name

`sigma_abc`

## Scientific Target

Derive and simplify the full tensorial nonlinear conductivity `sigma_{mu alpha beta}`.

## Raw Input Expression Location

`raw/tensorial_expression/`

## Desired Physical Basis

- Tensorial center sector.
- Tensorial pair geometric sector.
- Tensorial loop interference sector.
- Any additional tensorial structures must be retained until validated.

## Known Benchmark

Projection to `xxx` must reduce to the completed projected `sigma_xxx` final checkpoint:

```text
ProjectToXXX[tensor_formula] - sigma_xxx_final_reference == 0
```

## Allowed Operations

- Exact algebraic rewriting with validation.
- IBP only with exported primitive.
- Tensor index symmetrization only after convention audit.
- Numerical fallback only with explicit tolerance and caveat.

## Forbidden Operations

- Do not claim full tensorial correctness until `xxx` projection regression passes.
- Do not discard center or loop sectors without validation.
- Do not transfer `sigma_xxx` parity cancellations to general tensor components.

## Claim Boundary

Allowed:

- Stage-local tensorial claims with exact validation.

Forbidden:

- Full tensorial formula correctness before projection benchmark.
- Full equality to external compact kernels without convention matching.

## Stopping Criteria

- Protected `xxx` projection regression fails.
- Tensor index convention audit unresolved.
- Validation gate fails.
- Reviewer verdict requires patch or fail.
- `STOP` file exists.

