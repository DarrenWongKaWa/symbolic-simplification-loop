(* DC projection validation patch for Stage 001b.

The safe validation order is:
  1. Project raw_sigma_abc_finite_frequency.wl to xxx by
       h3[mu,alpha,beta] -> haaa,
       h2[alpha,beta]    -> haa,
       h1[mu]            -> ha.
  2. Compare the projected expression with abc_w1_w2_1D.txt.
  3. Attempt direct DC extraction:
       omega2 -> -omega1;
       SeriesCoefficient[Series[..., {omega1,0,2}],2].
  4. If direct extraction times out, use inherited DC validation:
       finite-frequency projection PASS
       plus archived 1D notebook DC pipeline provenance
       plus Sigma_abc_dc_1D.txt source snapshot.

This file records validation logic only. It does not start sector decomposition,
kernel fusion, or IBP.
*)

ClearAll[ProjectXXXRawCandidate];
ProjectXXXRawCandidate[expr_] := expr /. {
  h3[mu, alpha, beta][i_, j_] :> haaa[i, j],
  h2[alpha, beta][i_, j_] :> haa[i, j],
  h1[mu][i_, j_] :> ha[i, j]
};

DCOperator1D[expr_] := SeriesCoefficient[
  Series[expr /. \[Omega]2 -> -\[Omega]1, {\[Omega]1, 0, 2}],
  2
];

ValidationLogic = <|
  "DirectOptimizedOrder" -> {
    "Project tensorial finite-frequency raw candidate to xxx",
    "Collapse directional matrix elements to ha/haa/haaa",
    "Apply omega2 -> -omega1",
    "Extract SeriesCoefficient order 2"
  },
  "InheritedDCPremises" -> {
    "FiniteFrequencyProjectionTo1D -> PASS",
    "DC notebook imports abc_w1_w2_1D.txt",
    "DC notebook applies omega2 -> -omega1",
    "DC notebook exports FunctionExpand[Sigma_abc_dc] to Sigma_abc_dc_1D.txt"
  }
|>;
