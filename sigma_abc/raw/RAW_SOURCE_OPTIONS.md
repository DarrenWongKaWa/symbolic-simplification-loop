# RAW_SOURCE_OPTIONS

The future `raw/raw_sigma_abc.wl` must come from an explicit source. This file
lists acceptable source paths; none has been selected yet.

## Option A: Transcription From Existing Formula

Transcribe a trusted existing tensorial formula into the required association
format.

Required gates:

- Source formula citation or local source path.
- Tensor-index convention audit.
- Denominator and finite-`Gamma` convention audit.
- Independent transcription review.
- Projection-to-`xxx` benchmark prepared before simplification.

## Option B: Generator From General Kubo/Keldysh Formula

Build a generator from a general Kubo/Keldysh expression and export the raw
tensorial expression.

Required gates:

- Generator derivation note.
- Generator source code archived.
- Output association validates against `RAW_SIGMA_ABC_CONTRACT.md`.
- Projection-to-`xxx` benchmark prepared before simplification.

## Option C: Extension Of Existing sigma_xxx Generation Scripts

Extend the existing projected `sigma_xxx` generation machinery to retain
general tensor indices.

Required gates:

- Clear map from projected `xxx` generator to tensorial generator.
- No reuse of projected-only simplifications as tensorial identities.
- Exact `xxx` projection regression against the known final checkpoint.

## Current Selection

```text
SelectedRawSource -> Missing["NotSelectedYet"]
RawGenerationNeeded -> True
```

