# Loop 016 — Scientific Identity Rendering

## Status

PASS.

The scientific-identity rendering layer produces machine-readable
identity library, schema-validates, renders both Markdown and LaTeX
forms, embeds the section into the stage summary digest, and explicitly
does NOT alter validation status.

```text
python3 scripts/audit_identity_traceability.py \
  --stage autonomous_runs/sigma_abc/stages/sigma_abc_010_pair_kernel_fusion_pilot \
  --project sigma_abc
-> exit 0; .loop/scientific_identities.json + .md + .tex materialized
```

`sigma_abc` physics NOT modified. No 012C promotion, Stage 013
global pre-IBP assembly, tensorial IBP, or total-derivative reduction
started. Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## What Loop 016 Is

A renderer that:

- Loads a project's *default* identity library (e.g.
  `identities/sigma_abc.default_identities.yaml`).
- Loads any stage-specific identity overrides (none in this project
  yet; template file present for future use).
- Validates the library against
  `schemas/scientific_identity_library.schema.json`.
- Renders a per-stage Markdown section and a per-stage LaTeX
  section, embedding the identity LaTeX expressions directly.
- Embeds the section into the stage summary digest.
- Surfaces the DC inherited caveat as `INFORMATIONAL_ONLY`.
- Surfaces the Forbidden-family containment as `boundary` /
  `blocking`.

The renderer must NOT alter the stage's validation status — only
visualize the existing identities and link metadata. The
`rendered.validation_status_changed` flag is enforced to be `False`.

## Artifacts

```text
schemas/scientific_identity.schema.json
schemas/scientific_identity_library.schema.json
loop_engine/scientific_identities.py
identities/sigma_abc.default_identities.yaml
templates/SCIENTIFIC_IDENTITIES_STAGE_SECTION.template.md
templates/SCIENTIFIC_IDENTITIES_STAGE_SECTION.template.tex
scripts/audit_identity_traceability.py   # also writes scientific_identities payload
tests/test_loop014_017_pre_run_identity_traceability.py
```

Runtime artifacts on stage 010:

```text
.loop/scientific_identities.json
reports/stage_sigma_abc_010_pair_kernel_fusion_pilot_scientific_identities.md
reports/stage_sigma_abc_010_pair_kernel_fusion_pilot_scientific_identities.tex
```

## Default Identity Library

`identities/sigma_abc.default_identities.yaml` declares five identities:

```text
Reconstruction              role=reconstruction     blocking=False  check=mock_identity
XXX projection regression   role=protected_regression  blocking=True   check=[XXXProjectionRegression, ProtectedSigmaXXXBenchmark, sigma_xxx_projection]
Pair / orbit fusion         role=fusion             blocking=False  check=PairFusionDifference
DC inherited caveat         role=caveat             blocking=False  check=DCProjectionTo1D
Forbidden-family containment role=boundary           blocking=True   check=[NoIBPStarted, NoTotalDerivativeIntroduced, NoTensorialIBPStarted, NoFullTensorialKernelFusionStarted, NoFullTensorialClaim, NoCandidatePromoted]
```

After Phase 1's identity-library expansion, the `Forbidden-family
containment.check` list grew to include the canonical safe-prefusion
check names (`NoTensorialIBPStarted`,
`NoFullTensorialKernelFusionStarted`, `NoFullTensorialClaim`,
`NoCandidatePromoted`) so that LINKED binding succeeds on every
profile that emits any of these names.

## Rendered Markdown (excerpt, stage 010)

```text
# Scientific Identities

- **Reconstruction** (reconstruction): check `mock_identity`
  \[
  \Delta_{\mathrm{recon}} = \mathcal{K}_{\mathrm{old}} - \mathcal{K}_{\mathrm{new}} = 0.
  \]
- **XXX projection regression** (protected_regression): check `XXXProjectionRegression, ProtectedSigmaXXXBenchmark, sigma_xxx_projection`
  \[
  \mathrm{Proj}_{xxx} \left[ \sigma^{abc}_{\mathrm{tensorial}} \right] - \sigma^{xxx}_{\mathrm{protected}} = 0.
  \]
- **Pair / orbit fusion** (fusion): check `PairFusionDifference`
- **DC inherited caveat** (caveat): check `DCProjectionTo1D`
- **Forbidden-family containment** (boundary): check `NoIBPStarted, NoTotalDerivativeIntroduced, NoTensorialIBPStarted, NoFullTensorialKernelFusionStarted, NoFullTensorialClaim, NoCandidatePromoted`
```

## Rendered LaTeX (excerpt, stage 010)

```latex
\section*{Scientific Identities}

\paragraph{Reconstruction}
\[
\Delta_{\mathrm{recon}} = \mathcal{K}_{\mathrm{old}} - \mathcal{K}_{\mathrm{new}} = 0.
\]
\emph{Linked check:} \texttt{mock\_identity}

\paragraph{XXX projection regression}
\[
\mathrm{Proj}_{xxx} \left[ \sigma^{abc}_{\mathrm{tensorial}} \right] - \sigma^{xxx}_{\mathrm{protected}} = 0.
\]
```

## Stage Digest Integration

`reports/stage_summary.md` section 13 contains:

```text
## 13. Scientific identities
- Identity -> XXX projection regression (protected_regression)
- Identity -> Forbidden-family containment (boundary)
```

This was produced by `loop_engine.stage_digest.build_stage_digest`,
which now reads `.loop/scientific_identities.json` and surfaces the
identity labels + roles.

## Schema Validation

```text
loop_engine.schemas.validate_with_schema(
    scientific_identities_payload, "scientific_identity_library"
)
-> OK
```

## Validation Status Preserved

The renderer enforces a contract: rendering must not change
`validation_summary.overall_gate` or `review_result.verdict`. The
test `test_scientific_identity_library_rendering_and_digest` asserts
`rendered["validation_status_changed"] is False`.

## Remaining Non-goals

Loop 016 must not:

```text
- Rewrite any identity expression.
- Drop the DC caveat identity.
- Change validation_summary.overall_gate.
- Change review_result.verdict.
- Touch sigma_abc physics.
```

## Next

Proceed to Loop 017 (formula-to-check traceability), which audits each
identity against the validation_summary checks actually present in the
stage.