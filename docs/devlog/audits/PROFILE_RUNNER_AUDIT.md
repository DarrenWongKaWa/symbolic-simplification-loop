# Profile Runner Audit

ProfileRunnerStatus -> COMPLETE

## Current Checkpoint

```text
sigma_abc_012b_loop_hypothesis_generation
```

## Next Allowed Stage

```text
sigma_abc_012c_loop_orbit_canonicalization_promotion
```

## Allowed Stage List

- `sigma_abc_012c_loop_orbit_canonicalization_promotion`

## Stop-After Stage

```text
sigma_abc_012c_loop_orbit_canonicalization_promotion
```

## Protected Benchmarks

- `sigma_xxx_projection`

## Permanent Caveats

- DCProjectionTo1D is INHERITED_PASS, not direct full tensorial DC-series PASS.
- Stage001DCCaveatPreserved
- DCProjectionTo1D -> INHERITED_PASS

## Forbidden Actions

- full tensorial sigma_abc correctness
- direct full tensorial DC-series PASS
- full equality to projected sigma_xxx final formula before projection validation

## Hard-Stop Conditions

- forbidden tag: kernel_fusion
- forbidden tag: ibp_reduction
- forbidden tag: tensorial_simplification

## Reviewer Mode

```text
codex_subagent
```

## Patch Limits

```json
{}
```
