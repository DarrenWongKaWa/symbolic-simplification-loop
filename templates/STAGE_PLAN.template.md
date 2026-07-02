# Stage Plan

## Stage

`<stage_name>`

## Goal

What this stage is supposed to prove or transform.

## Input Snapshots

- `input_snapshots/<file>`

## Expected Outputs

- `output/<file>`
- `validation/validation_summary.json`

## Allowed Transformations

- `<operation>`

## Forbidden Transformations

- `<operation>`

## Validation Identity

```text
OldExpression - NewExpression == 0
```

or

```text
OldExpression - NewExpression - D[F,k] == 0
```

## Protected Regressions

- `<regression>`

## Claim Boundary

Allowed:

- `<claim>`

Forbidden:

- `<claim>`

## Next-Stage Trigger

What condition opens the next stage.

