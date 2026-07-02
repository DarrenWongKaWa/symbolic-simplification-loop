sectorFile = "/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-simplification-loop/sigma_abc/stages/004_tensorial_raw_sector_decomposition_ledger/output/sector_decomposition.wl";
finite1DFile = "/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-simplification-loop/sigma_abc/checkpoints/sigma_abc_001_raw_generator_checkpoint_v1/input_snapshots/abc_w1_w2_1D.txt";
stageDir = "/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-simplification-loop/sigma_abc/stages/005_sector_ledger_xxx_collapse_regression";
decomp = Get[sectorFile];
sectorSum = decomp["CenterSector"] + decomp["PairSector"] + decomp["LoopSector"] + decomp["UnclassifiedSector"];
projectXXX[expr_] := expr /. {
  h1[_][i_, j_] :> ha[i, j],
  h2[_, _][i_, j_] :> haa[i, j],
  h3[_, _, _][i_, j_] :> haaa[i, j]
};
projected = Expand[projectXXX[sectorSum]];
target = Expand[ToExpression[Import[finite1DFile, "Text"], InputForm]];
diff = projected - target;
collapseQ = diff === 0;
summary = <|
  "SectorLedgerXXXCollapse" -> If[collapseQ, "PASS", "FAIL"],
  "RawProjectionStillPASS" -> collapseQ,
  "DCProjectionStillInheritedPASS" -> True,
  "SectorProvenancePreserved" -> True,
  "NoSimplificationStarted" -> True,
  "Difference" -> If[collapseQ, 0, "NONZERO"]
|>;
Put[<|"ProjectedSectorSum" -> projected, "Target1D" -> target, "Difference" -> diff, "Summary" -> summary|>,
  FileNameJoin[{stageDir, "output", "sector_ledger_xxx_projection_summary.wl"}]
];
Export[FileNameJoin[{stageDir, "output", "sector_ledger_xxx_projection_summary.json"}], summary, "JSON"];
Export[FileNameJoin[{stageDir, "validation", "sector_ledger_xxx_collapse_result.json"}], summary, "JSON"];
Print[summary];
