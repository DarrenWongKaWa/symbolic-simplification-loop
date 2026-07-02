<|
  "ObjectName" -> "sigma_abc_raw",
  "Status" -> "TEMPLATE_ONLY",
  "Scope" -> "full tensorial nonlinear conductivity sigma_{mu alpha beta}",
  "RawSigmaABCExists" -> False,
  "RawGenerationNeeded" -> True,
  "IndexConventions" -> <|
    "TensorIndices" -> {"mu", "alpha", "beta"},
    "ProjectedBenchmarkComponent" -> {"x", "x", "x"},
    "BandIndices" -> {"a", "b", "c"}
  |>,
  "ThermalConvention" -> <|
    "Status" -> Missing["NotDeclaredYet"],
    "ExpectedFields" -> {"PGConvention", "BetaConvention", "GammaConvention"}
  |>,
  "Expression" -> Missing["NotGeneratedYet"],
  "SectorDecomposition" -> <|
    "Center" -> Missing["NotGeneratedYet"],
    "Pair" -> Missing["NotGeneratedYet"],
    "Loop" -> Missing["NotGeneratedYet"],
    "Residual" -> Missing["NotGeneratedYet"]
  |>,
  "SummationStructure" -> Missing["NotGeneratedYet"],
  "ProjectionBenchmarks" -> <|
    "SigmaXXX" -> "ProjectToXXX[sigma_abc_tensor_formula] - sigma_xxx_final_reference == 0"
  |>,
  "AllowedOperations" -> {
    "raw generation",
    "raw transcription",
    "source provenance audit",
    "projection benchmark registration"
  },
  "ForbiddenClaims" -> {
    "raw_sigma_abc.wl exists",
    "sigma_abc simplification has started",
    "full tensorial formula is correct"
  },
  "Provenance" -> <|
    "Source" -> Missing["NotSelectedYet"],
    "GeneratedBy" -> Missing["NotGeneratedYet"],
    "GeneratedAt" -> Missing["NotGeneratedYet"]
  |>,
  "Validation" -> <|
    "RawTopLevelAssociationQ" -> True,
    "ExpressionMissingQ" -> True,
    "ContractOnlyQ" -> True
  |>
|>

