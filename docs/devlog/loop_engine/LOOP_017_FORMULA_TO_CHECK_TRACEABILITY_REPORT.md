# Loop 017 — Formula-to-Check Traceability

## Status

PASS.

The formula-to-check traceability layer audits each rendered
scientific identity against the `validation_summary.json` checks
actually present in the stage, classifies each binding as
`LINKED / REGISTERED / INFORMATIONAL_ONLY / MISSING_CHECK`, and feeds
the result into `freeze_preconditions` so that an unlinked *blocking*
identity hard-blocks checkpoint freeze.

```text
python3 scripts/audit_identity_traceability.py \
  --stage autonomous_runs/sigma_abc/stages/sigma_abc_010_pair_kernel_fusion_pilot \
  --project sigma_abc
-> exit 0; .loop/identity_traceability.json materialized
   identity_traceability_gate = PASS
   blocking_failures         = []
```

`sigma_abc` physics NOT modified. No 012C promotion, Stage 013
global pre-IBP assembly, tensorial IBP, or total-derivative reduction
started. Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## What Loop 017 Is

An auditor that consumes the rendered scientific identities (Loop 016
output) plus the stage's `.loop/validation_summary.json` and assigns
each identity one of:

```text
LINKED            # at least one requested check name was found
REGISTERED        # has requested checks but none were found AND not blocking
INFORMATIONAL_ONLY  # role == "caveat"
MISSING_CHECK     # blocking AND none of its requested checks were found
```

The auditor emits:

```text
identity_traceability_gate = PASS  iff  no blocking identity is MISSING_CHECK
blocking_failures          = [...]  blocking identities that are MISSING_CHECK
```

The freeze layer (`loop_engine/state.freeze_preconditions`) reads
`.loop/identity_traceability.json` and refuses to freeze if
`identity_traceability_gate != "PASS"` or `blocking_failures`
non-empty. This means a stage that forgets to emit any check an
identity requires **cannot** reach checkpoint.

## Artifacts

```text
schemas/identity_traceability.schema.json
loop_engine/identity_traceability.py
scripts/audit_identity_traceability.py
tests/test_loop014_017_pre_run_identity_traceability.py
```

Runtime artifacts on stage 010:

```text
.loop/identity_traceability.json
reports/identity_traceability.md
```

## Observed Behavior on Stage 010

```text
identity_traceability_gate = PASS
blocking_failures         = []
items:
  - Reconstruction               trace_status=REGISTERED        blocking=False  linked=[]
  - XXX projection regression    trace_status=LINKED           blocking=True   linked=[sigma_xxx_projection]
  - Pair / orbit fusion          trace_status=LINKED           blocking=False  linked=[PairFusionDifference]
  - DC inherited caveat          trace_status=INFORMATIONAL_ONLY blocking=False linked=[]
  - Forbidden-family containment trace_status=LINKED           blocking=True   linked=[NoIBPStarted, NoTotalDerivativeIntroduced, NoFullTensorialClaim]
```

After Phase 1's identity-library expansion (the
`Forbidden-family containment.check` list grew to also include
`NoTensorialIBPStarted`, `NoFullTensorialKernelFusionStarted`,
`NoFullTensorialClaim`, `NoCandidatePromoted`), the auditor now
links `Forbidden-family containment` against any of those names
*or* the canonical `NoIBPStarted` / `NoTotalDerivativeIntroduced`
that the previous safe-prefusion path already emitted via
`validation_summary.json::checks`.

## Identity-Traceability Renderer Output (md excerpt)

```text
# Identity Traceability

IdentityTraceabilityGate -> PASS

| Identity | Status | Linked checks | Blocking |
|---|---|---|---|
| Reconstruction | REGISTERED | none | False |
| XXX projection regression | LINKED | sigma_xxx_projection | True |
| Pair / orbit fusion | LINKED | PairFusionDifference | False |
| DC inherited caveat | INFORMATIONAL_ONLY | none | False |
| Forbidden-family containment | LINKED | NoIBPStarted, NoTotalDerivativeIntroduced, NoFullTensorialClaim | True |
```

## Freeze-Blocking Test Coverage

`test_identity_traceability_blocks_freeze_and_checkpoint_manifest_includes_it`
proves the wiring into `freeze_preconditions`:

```text
1) Build a stage with valid completion matrix + human signoff
2) Traceability audit PASSes -> freeze_preconditions returns []
3) Mutate identity_traceability.identity_traceability_gate = "FAIL"
4) Re-run freeze_preconditions -> returns ["identity_traceability ..."]; freeze blocked
```

It also proves the manifest integration: `build_checkpoint_manifest`
includes `identity_traceability: ".loop/identity_traceability.json"`
when present.

## Schema Validation

```text
loop_engine.schemas.validate_with_schema(
    identity_traceability_payload, "identity_traceability"
)
-> OK
```

## Traceability Status Semantics

| Status              | Meaning                                                                 |
|---------------------|-------------------------------------------------------------------------|
| `LINKED`            | At least one requested check name appears in the stage's validation.   |
| `REGISTERED`        | Has requested checks but none matched AND not blocking — soft note.    |
| `INFORMATIONAL_ONLY`| `role == caveat`. Always passes through, never blocks.                  |
| `MISSING_CHECK`     | `blocking=true` AND none of the requested checks were found.           |

A blocking identity that lands in `MISSING_CHECK` adds its label to
`blocking_failures` and fails the gate, blocking freeze. This is what
just saved stage 006 from freezing with an un-asserted
"no IBP" claim.

## Remaining Non-goals

Loop 017 must not:

```text
- Invent a check that does not appear in validation_summary.
- Hide an unlinked blocking identity.
- Treat DC inherited caveat as blocking.
- Touch sigma_abc physics.
```

## Next

All four per-loop gates are PASS. Proceed to Phase 6 (final
integration audit).