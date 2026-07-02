# RAW_SIGMA_ABC_CONTRACT

## Purpose

Define the required structure for the future file:

```text
raw/raw_sigma_abc.wl
```

This contract is ready before the raw expression exists.

## Required Top-Level Form

The file must evaluate to one Wolfram Language `Association`.

Required keys:

```wl
<|
  "ObjectName" -> "sigma_abc_raw",
  "Status" -> "GENERATED",
  "Scope" -> "...",
  "IndexConventions" -> <|...|>,
  "ThermalConvention" -> <|...|>,
  "Expression" -> expr,
  "SectorDecomposition" -> <|...|>,
  "SummationStructure" -> <|...|>,
  "AllowedOperations" -> {...},
  "ForbiddenClaims" -> {...},
  "ProjectionBenchmarks" -> <|...|>,
  "Provenance" -> <|...|>,
  "Validation" -> <|...|>
|>
```

## Required Semantic Content

### Tensor indices

The expression must retain tensor indices explicitly:

```text
mu, alpha, beta
```

or an equivalent documented convention. The projected `xxx` component must be
obtained only by an explicit projection map.

### Band indices

The expression must retain band-index provenance. At minimum, it must identify
single-band, two-band, and three-band structures before any simplification.

### Finite-Gamma convention

The file must specify the finite broadening convention for `Gamma` and all
denominator structures.

### Thermal convention

The file must specify the thermal block convention and any `PG` or polygamma
normalization used by the generator.

### Sector decomposition

The raw expression must either include or allow exact extraction of:

```text
center sector
pair sector
loop sector
residual or unclassified sector, if present
```

### Projection benchmark

The raw expression must include enough metadata to test:

```text
ProjectToXXX[sigma_abc_tensor_formula] - sigma_xxx_final_reference == 0
```

## Required Validation Before Import

Before the raw expression can be imported into a simplification stage, the
following gates must pass:

```text
RawSigmaABCExists -> True
RawTopLevelAssociationQ -> True
ExpressionMissingQ -> False
TensorIndexConventionDeclaredQ -> True
ProjectionBenchmarkRegisteredQ -> True
SourceProvenanceDeclaredQ -> True
```

The current branch intentionally satisfies only contract-readiness gates, not
raw-availability gates.

