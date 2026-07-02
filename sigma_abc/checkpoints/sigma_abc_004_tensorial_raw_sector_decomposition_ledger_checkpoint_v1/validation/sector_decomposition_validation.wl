rawFile = "/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-simplification-loop/sigma_abc/checkpoints/sigma_abc_001_raw_generator_checkpoint_v1/raw/raw_sigma_abc_finite_frequency.wl";
stageDir = "/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-simplification-loop/sigma_abc/stages/004_tensorial_raw_sector_decomposition_ledger";
expr = Get[rawFile]["Expression"];
expanded = Expand[expr];
terms = If[Head[expanded] === Plus, List @@ expanded, {expanded}];
bandIndices[t_] := Sort @ DeleteDuplicates @ Flatten @ Cases[
  HoldComplete[t],
  HoldPattern[(h1[_] | h2[_, _] | h3[_, _, _])[i_Integer, j_Integer]] :> {i, j},
  Infinity
];
classify[t_] := Module[{k = Length[bandIndices[t]]},
  Which[k <= 1, "center/contact sector", k == 2, "pair/two-band sector", k >= 3, "loop/three-band sector", True, "unclassified"]
];
labels = classify /@ terms;
bands = bandIndices /@ terms;
centerTerms = Pick[terms, labels, "center/contact sector"];
pairTerms = Pick[terms, labels, "pair/two-band sector"];
loopTerms = Pick[terms, labels, "loop/three-band sector"];
unclassifiedTerms = Pick[terms, labels, "unclassified"];
sectorSum = Total[Join[centerTerms, pairTerms, loopTerms, unclassifiedTerms]];
rawMinus = expanded - sectorSum;
reconstructionZero = rawMinus === 0;
decomp = <|
  "SourceRawFile" -> rawFile,
  "Method" -> "Additive term partition by number of distinct band indices in h1/h2/h3 factors; no simplification, fusion, or IBP.",
  "CenterSector" -> Total[centerTerms],
  "PairSector" -> Total[pairTerms],
  "LoopSector" -> Total[loopTerms],
  "UnclassifiedSector" -> Total[unclassifiedTerms],
  "RawExpandedExpression" -> expanded,
  "SectorSum" -> sectorSum,
  "RawMinusSectorSum" -> rawMinus,
  "RawMinusSectorSumQ" -> reconstructionZero
|>;
Put[decomp, FileNameJoin[{stageDir, "output", "sector_decomposition.wl"}]];
rows = MapThread[
  {#1, #2, Length[#3], StringRiffle[ToString /@ #3, ";"], ToString[InputForm[Hash[#4, "SHA256"]]]} &,
  {Range[Length[terms]], labels, bands, terms}
];
Export[FileNameJoin[{stageDir, "output", "sector_ledger.csv"}],
  Prepend[rows, {"row", "sector", "band_count", "bands", "term_hash"}]
];
counts = <|
  "center/contact sector" -> Length[centerTerms],
  "pair/two-band sector" -> Length[pairTerms],
  "loop/three-band sector" -> Length[loopTerms],
  "unclassified" -> Length[unclassifiedTerms],
  "total_rows" -> Length[terms]
|>;
Export[FileNameJoin[{stageDir, "output", "sector_counts.json"}], counts, "JSON"];
validation = <|
  "SectorDecompositionExists" -> True,
  "RawMinusSectorSum" -> If[reconstructionZero, 0, "NONZERO"],
  "SectorCountsRecorded" -> True,
  "NoKernelFusionStarted" -> True,
  "NoIBPStarted" -> True,
  "Counts" -> counts
|>;
Export[FileNameJoin[{stageDir, "validation", "sector_decomposition_validation_result.json"}], validation, "JSON"];
Print[validation];
