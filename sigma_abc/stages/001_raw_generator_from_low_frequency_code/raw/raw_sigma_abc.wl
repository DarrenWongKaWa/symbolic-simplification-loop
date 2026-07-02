<|
  "ObjectName" -> "sigma_abc_raw",
  "Status" -> "CANDIDATE_UNVERIFIED",
  "Scope" -> "candidate tensorial raw wrapper generated from low_frequency 1D source files",
  "IndexConventions" -> <|
    "mu" -> "current/output index",
    "alpha" -> "first electric-field index",
    "beta" -> "second electric-field index"
  |>,
  "ThermalConvention" -> <|"Source" -> "low_frequency/abc_w1_w2_1D.txt polygamma kernels"|>,
  "Expression" -> Get[FileNameJoin[{DirectoryName[$InputFileName], "raw_sigma_abc_finite_frequency.wl"}]]["Expression"],
  "SectorDecomposition" -> <|"Status" -> "NotStarted"|>,
  "SummationStructure" -> <|"Status" -> "Inherited from low_frequency 1D source; tensorial sector decomposition not started"|>,
  "AllowedOperations" -> {"xxx projection regression only"},
  "ForbiddenClaims" -> {
    "full tensorial correctness",
    "official raw import",
    "sector decomposition",
    "kernel fusion",
    "IBP reduction"
  },
  "ProjectionBenchmarks" -> <|"FiniteFrequencyXXX" -> "PASS", "DCXXXSeries" -> "TIMEOUT"|>,
  "Provenance" -> <|"FiniteFrequency1D" -> "input_snapshots/abc_w1_w2_1D.txt", "DC1D" -> "input_snapshots/Sigma_abc_dc_1D.txt"|>,
  "Validation" -> <|"OverallGate" -> "FAIL", "Reason" -> "DC series benchmark timed out"|>
|>
