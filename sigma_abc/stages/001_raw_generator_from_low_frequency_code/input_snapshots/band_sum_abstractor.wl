(* ::Package:: *)

(*  band_sum_abstractor.wl

    Purpose:
      Convert one explicitly expanded 3-band sector, usually the sector with
      epsilon[1], into an abstract N-band expression.

    Basic idea:
      - Terms containing only index 1 become the generic n-sector.
      - Terms containing indices {1,2} or {1,3} become Sum[..., {m,1,N}]
        with condition m != n.
      - Terms containing {1,2,3} become Sum[..., {m,1,N},{l,1,N}]
        with conditions m != n, l != n, l != m.

    Usage:
      1. Put your explicit expression in expr3 = (...);
      2. Evaluate:
             abs = AbstractThreeBandSector[expr3]
             TeXForm[abs]

    Important:
      This code assumes the expression you paste is one sector centered on
      band 1, like the example with PolyGamma[..., epsilon[1]].
*)

ClearAll[
  explicitBandIndices,
  relabelBandIndices,
  constrainedSum,
  additivePieces,
  abstractPiece,
  inactiveSumVariables,
  splitFreeFactors,
  pullFreeFactorsFromSums,
  combineInactiveSums,
  compactSumBody,
  compactBandStep,
  CompactBandExpression,
  CollectGammaNumerator,
  GammaOrderPieces,
  GammaOrderForm,
  energyAtomQ,
  directEnergyDifferenceRules,
  linearEnergyDifferenceReduce,
  EnergyDifferenceReduce,
  matrixFactorQ,
  splitMatrixFactors,
  CollectByMatrixProducts,
  CompactEnergyDifferenceNotation,
  CompactGammaOrderEnergyNotation,
  RebuildGammaOrderExpression,
  CompactOutput,
  matrixElementHeads,
  matrixBandIndices,
  rawMatrixMonomialPieces,
  AbstractCenteredCoefficient,
  SpecializeCenteredCoefficient,
  AbstractThreeBandSector
];

matrixElementHeads = {ha, haa, hab, hac, hbc, habc};

matrixBandIndices[expr_] := Sort @ DeleteDuplicates @ Flatten @ Cases[
  HoldComplete[expr],
  HoldPattern[h_[i_Integer, j_Integer] /; MemberQ[matrixElementHeads, h]] :>
    {i, j},
  Infinity
];

rawMatrixMonomialPieces[expr_] := Module[{expanded, terms, split, groups},
  expanded = Expand[expr];
  terms = If[Head[expanded] === Plus, List @@ expanded, {expanded}];
  split = splitMatrixFactors /@ terms;
  groups = GatherBy[split, Last];
  Map[
    Factor[Together[Total[#[[All, 1]]]]] #[[1, 2]] &,
    groups
  ]
];

explicitBandIndices[expr_] := Sort @ DeleteDuplicates @ Cases[
   HoldComplete[expr],
   HoldPattern[h_[i_Integer, j_Integer] /; MemberQ[matrixElementHeads, h]] :>
     Cases[{i, j}, k_Integer /; 1 <= k <= 3 :> k],
   Infinity
] ~Join~ Cases[
   HoldComplete[expr],
   HoldPattern[\[Epsilon][i_Integer]] /; 1 <= i <= 3 :> i,
   Infinity
] // Flatten // Sort // DeleteDuplicates;

relabelBandIndices[expr_, rules_] := expr /. {
   HoldPattern[h_[i_, j_] /; MemberQ[matrixElementHeads, h]] :>
     h[i /. rules, j /. rules],
   HoldPattern[\[Epsilon][i_]] :> \[Epsilon][i /. rules]
};

constrainedSum[body_, {}] := body;

constrainedSum[body_, {m}] :=
  Inactive[Sum][
    Boole[m != n] body,
    {m, 1, NBands}
  ];

constrainedSum[body_, {m, l}] :=
  Inactive[Sum][
    Boole[m != n && l != n && l != m] body,
    {m, 1, NBands}, {l, 1, NBands}
  ];

(* Split additive structure, including prefactor*(a+b+c).
   This is intentionally gentler than Expand: denominators and powers stay intact. *)
additivePieces[expr_Plus] := Flatten[additivePieces /@ (List @@ expr)];
additivePieces[expr_Times] := Module[
  {factors = List @@ expr, plusPos, before, terms},
  plusPos = FirstPosition[factors, _Plus, Missing["NotFound"], {1}, Heads -> False];
  If[MissingQ[plusPos],
    {expr},
    before = Delete[factors, plusPos];
    terms = List @@ Extract[factors, plusPos];
    Flatten[additivePieces[Times @@ Append[before, #]] & /@ terms]
  ]
];
additivePieces[expr_] := {expr};

abstractPiece[piece_] := Module[
  {inds, body},
  inds = explicitBandIndices[piece];

  Which[
    inds === {} || inds === {1},
      relabelBandIndices[piece, {1 -> n}],

    inds === {1, 2},
      body = relabelBandIndices[piece, {1 -> n, 2 -> m}];
      constrainedSum[body, {m}],

    inds === {1, 3},
      body = relabelBandIndices[piece, {1 -> n, 3 -> m}];
      constrainedSum[body, {m}],

    inds === {1, 2, 3},
      body = relabelBandIndices[piece, {1 -> n, 2 -> m, 3 -> l}];
      constrainedSum[body, {m, l}],

    True,
      Message[AbstractThreeBandSector::badinds, inds, HoldForm[piece]];
      piece
  ]
];

AbstractThreeBandSector::badinds =
  "Could not classify explicit band indices `1` in piece `2`.";

inactiveSumVariables[iters_] := Cases[
  HoldComplete[iters],
  {v_Symbol, __} :> v,
  Infinity
];

splitFreeFactors[body_Times, vars_] := Module[
  {factors, free, dependent},
  factors = List @@ body;
  free = Select[factors, FreeQ[#, Alternatives @@ vars] &];
  dependent = Select[factors, ! FreeQ[#, Alternatives @@ vars] &];
  {Times @@ free, Times @@ dependent}
];

splitFreeFactors[body_, vars_] :=
  If[FreeQ[body, Alternatives @@ vars], {body, 1}, {1, body}];

pullFreeFactorsFromSums[expr_] := FixedPoint[
  ReplaceAll[
    #,
    HoldPattern[Inactive[Sum][body_, iters__List]] :>
      Module[{vars, split},
        vars = inactiveSumVariables[{iters}];
        split = splitFreeFactors[body, vars];
        If[split[[1]] === 1,
          Inactive[Sum][split[[2]], iters],
          split[[1]] Inactive[Sum][split[[2]], iters]
        ]
      ]
  ] &,
  expr
];

combineInactiveSums[expr_] := FixedPoint[
  ReplaceAll[
    #,
    p_Plus :> Module[{terms, sumData, otherTerms, groups, merged},
      terms = List @@ p;
      sumData = Cases[
        terms,
        HoldPattern[Inactive[Sum][body_, iters__List]] :> {{iters}, body}
      ];
      otherTerms = DeleteCases[
        terms,
        HoldPattern[Inactive[Sum][_, __List]]
      ];
      groups = GatherBy[sumData, First];
      merged = Map[
        Inactive[Sum][compactSumBody[Total[#[[All, 2]]]], Sequence @@ #[[1, 1]]] &,
        groups
      ];
      Total[Join[otherTerms, merged]]
    ]
  ] &,
  expr
];

compactSumBody[body_] := Factor[Together[body]];

compactBandStep[expr_] := Module[
  {combined, factored, pulled},
  combined = combineInactiveSums[expr];
  factored = combined //. HoldPattern[Inactive[Sum][body_, iters__List]] :>
    Inactive[Sum][compactSumBody[body], iters];
  pulled = pullFreeFactorsFromSums[factored];
  compactSumBody[pulled]
];

CompactBandExpression[expr_] := Nest[compactBandStep, expr, 4];

(* Collect the numerator of a rational expression by powers of gamma.
   This is useful for long conductivity pieces whose denominator also contains
   gamma, so plain Collect[expr, gamma] is usually not the desired operation. *)
CollectGammaNumerator[expr_, gamma_: \[CapitalGamma]] := Module[
  {num, den},
  {num, den} = NumeratorDenominator[Together[expr]];
  Collect[Expand[num], gamma, Factor]/den
];

(* Return an association from gamma power -> numerator coefficient.
   Example keys are 0, 1, 2, 3. The common denominator is not included here. *)
GammaOrderPieces[expr_, gamma_: \[CapitalGamma]] := Module[
  {num, den, poly, maxPower},
  {num, den} = NumeratorDenominator[Together[expr]];
  poly = Collect[Expand[num], gamma, Factor];
  maxPower = Exponent[poly, gamma];
  Association@Table[
    k -> Factor[Coefficient[poly, gamma, k]],
    {k, 0, maxPower}
  ]
];

(* Return an association with common denominator plus the numerator pieces.
   This is convenient when you want to inspect O(gamma^0), O(gamma^1), etc. *)
GammaOrderForm[expr_, gamma_: \[CapitalGamma]] := Module[
  {num, den, poly, maxPower},
  {num, den} = NumeratorDenominator[Together[expr]];
  poly = Collect[Expand[num], gamma, Factor];
  maxPower = Exponent[poly, gamma];
  <|
    "Denominator" -> den,
    "NumeratorByOrder" -> Association@Table[
      k -> Factor[Coefficient[poly, gamma, k]],
      {k, 0, maxPower}
    ],
    "Expression" -> Collect[poly, gamma, Factor]/den
  |>
];

(* Energy-difference and matrix-product utilities.

   Convention:
     dE[a,b] means \[Epsilon][a] - \[Epsilon][b].

   The single-index object \[Epsilon][a] is left untouched unless it appears in
   an explicit difference or in a linear coefficient whose total epsilon
   coefficient is zero.
*)

energyAtomQ[x_] := MatchQ[x, HoldPattern[\[Epsilon][_Symbol | _Integer]]];

directEnergyDifferenceRules[head_: dE] := {
  HoldPattern[\[Epsilon][a_] - \[Epsilon][b_]] :> head[a, b],
  HoldPattern[-\[Epsilon][a_] + \[Epsilon][b_]] :> head[b, a]
};

linearEnergyDifferenceReduce[expr_, base_: n, head_: dE] := Module[
  {vars, coeffs, totalCoeff},
  vars = DeleteDuplicates @ Cases[
    expr,
    HoldPattern[\[Epsilon][i : (_Symbol | _Integer)]] :> i,
    Infinity
  ];
  If[Length[vars] < 2 || ! MemberQ[vars, base], Return[expr]];

  coeffs = Association@Table[
    v -> Coefficient[expr, \[Epsilon][v]],
    {v, vars}
  ];
  totalCoeff = Total[Values[coeffs]];

  If[TrueQ[Simplify[totalCoeff == 0]],
    Factor @ Total[
      DeleteCases[
        Table[
          If[v === base, 0, coeffs[v] head[v, base]],
          {v, vars}
        ],
        0
      ]
    ],
    expr
  ]
];

EnergyDifferenceReduce[expr_, base_: n, head_: dE] := Module[
  {reduced},
  reduced = expr //. directEnergyDifferenceRules[head];
  reduced //. p_Plus :> linearEnergyDifferenceReduce[p, base, head]
];

matrixFactorQ[x_] := Which[
  MemberQ[matrixElementHeads, Head[x]] && Length[List @@ x] == 2,
    True,
  Head[x] === Power &&
    IntegerQ[x[[2]]] && Positive[x[[2]]] &&
    MemberQ[matrixElementHeads, Head[x[[1]]]] &&
    Length[List @@ x[[1]]] == 2,
    True,
  True,
    False
];

splitMatrixFactors[term_Times] := Module[
  {factors, matrixFactors, coefficientFactors},
  factors = List @@ term;
  matrixFactors = Select[factors, matrixFactorQ];
  coefficientFactors = Select[factors, ! matrixFactorQ[#] &];
  {Times @@ coefficientFactors, Times @@ matrixFactors}
];

splitMatrixFactors[term_] :=
  If[matrixFactorQ[term], {1, term}, {term, 1}];

CollectByMatrixProducts[expr_, base_: n, head_: dE] := Module[
  {expanded, terms, split, groups},
  expanded = Expand[expr];
  terms = If[Head[expanded] === Plus, List @@ expanded, {expanded}];
  split = splitMatrixFactors /@ terms;
  groups = GatherBy[split, Last];
  Total[
    Map[
      EnergyDifferenceReduce[Factor[Together[Total[#[[All, 1]]]]], base, head] #[[1, 2]] &,
      groups
    ]
  ]
];

CompactEnergyDifferenceNotation[expr_, base_: n, head_: dE] := Module[
  {collected},
  collected = expr //. HoldPattern[Inactive[Sum][body_, iters__List]] :>
    Inactive[Sum][CollectByMatrixProducts[body, base, head], iters];
  EnergyDifferenceReduce[CollectByMatrixProducts[collected, base, head], base, head]
];

RebuildGammaOrderExpression[gammaForm_Association, gamma_: \[CapitalGamma]] :=
  Total[
    KeyValueMap[
      gamma^#1 #2 &,
      gammaForm["NumeratorByOrder"]
    ]
  ]/gammaForm["Denominator"];

CompactGammaOrderEnergyNotation[expr_, base_: n, gamma_: \[CapitalGamma], head_: dE] := Module[
  {form, compactPieces},
  form = GammaOrderForm[expr, gamma];
  compactPieces = Association @ KeyValueMap[
    #1 -> CompactEnergyDifferenceNotation[#2, base, head] &,
    form["NumeratorByOrder"]
  ];
  <|
    "Denominator" -> form["Denominator"],
    "NumeratorByOrder" -> compactPieces,
    "Expression" -> Total[KeyValueMap[gamma^#1 #2 &, compactPieces]]/form["Denominator"]
  |>
];

Options[AbstractThreeBandSector] = {CompactOutput -> False};

AbstractThreeBandSector[expr_, OptionsPattern[]] := Module[
  {pieces, abstracted},
  pieces = additivePieces[expr];
  abstracted = DeleteDuplicates[abstractPiece /@ pieces];
  If[TrueQ[OptionValue[CompactOutput]],
    CompactBandExpression[Inactive[Sum][Total[abstracted], {n, 1, NBands}]],
    Inactive[Sum][Total[abstracted], {n, 1, NBands}]
  ]
];

(* Center-aware abstraction for a complete three-band coefficient.

   The coefficient is first separated by the number of external bands used.
   The one-external-band sector is represented by one reference external band.
   The two-external-band sector carries 1/2 because the constrained (m,l) sum
   is ordered and therefore contains both permutations for NBands == 3.
*)
AbstractCenteredCoefficient[expr_, center_Integer] := Module[
  {external, pieces, zero, oneReference, one, two, rules0, rules1, rules2},
  external = DeleteCases[{1, 2, 3}, center];
  (* Combine scalar coefficients of identical matrix monomials before
     classifying band sectors. Temporary spectator energies cancel here. *)
  pieces = rawMatrixMonomialPieces[expr];
  zero = Total @ Select[
    pieces,
    SubsetQ[{center}, matrixBandIndices[#]] &
  ];
  oneReference = external[[1]];
  one = Total @ Select[
    pieces,
    With[{inds = matrixBandIndices[#]},
      MemberQ[inds, oneReference] &&
      SubsetQ[{center, oneReference}, inds]
    ] &
  ];
  two = Total @ Select[
    pieces,
    Length[Intersection[matrixBandIndices[#], external]] == 2 &
  ];
  rules0 = {center -> n};
  rules1 = {center -> n, oneReference -> m};
  rules2 = {center -> n, external[[1]] -> m, external[[2]] -> l};
  <|
    "CenterOnly" -> relabelBandIndices[zero, rules0],
    "OneExternalKernel" -> relabelBandIndices[one, rules1],
    "TwoExternalKernel" -> relabelBandIndices[two, rules2],
    "Expression" ->
      relabelBandIndices[zero, rules0] +
      Inactive[Sum][
        Boole[m != n] relabelBandIndices[one, rules1],
        {m, 1, NBands}
      ] +
      (1/2) Inactive[Sum][
        Boole[m != n && l != n && l != m] relabelBandIndices[two, rules2],
        {m, 1, NBands}, {l, 1, NBands}
      ]
  |>
];

SpecializeCenteredCoefficient[abstract_Association, center_Integer] := Module[
  {external, rules},
  external = DeleteCases[{1, 2, 3}, center];
  rules = {n -> center};
  (abstract["CenterOnly"] /. rules) +
  Total[
    Table[
      If[
        m0 == center,
        0,
        abstract["OneExternalKernel"] /. {n -> center, m -> m0}
      ],
      {m0, 1, 3}
    ]
  ] +
  (1/2) Total[
    Flatten @ Table[
      If[
        m0 == center || l0 == center || l0 == m0,
        0,
        abstract["TwoExternalKernel"] /. {n -> center, m -> m0, l -> l0}
      ],
      {m0, 1, 3}, {l0, 1, 3}
    ]
  ]
];

(* Optional: remove Boole[...] wrappers if you prefer Subscripted-condition notation
   only in the final paper. Keeping Boole makes the expression algebraic and exact. *)

(* Gamma-order utilities:

   collected = CollectGammaNumerator[expr]
     returns one rational expression whose numerator is collected by powers of
     \[CapitalGamma].

   pieces = GammaOrderPieces[expr]
     returns <|0 -> O(\[CapitalGamma]^0) numerator coefficient,
               1 -> O(\[CapitalGamma]^1) numerator coefficient, ...|>.

   form = GammaOrderForm[expr]
     returns <|"Denominator" -> commonDenominator,
               "NumeratorByOrder" -> pieces,
               "Expression" -> collectedExpression|>.

   compactForm = CompactGammaOrderEnergyNotation[expr]
     first splits the numerator by powers of \[CapitalGamma], then compacts
     each order by matrix products and energy differences. This is usually the
     best workflow for final paper notation.

   By default dE[a,b] means \[Epsilon][a] - \[Epsilon][b]. To use another
   notation, pass it as the fourth argument, for example:
     CompactGammaOrderEnergyNotation[expr, n, \[CapitalGamma], \[CapitalDelta]]
*)
