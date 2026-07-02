(* Thermal rho kernels extracted for the raw-generation candidate.
   These helpers encode the polygamma convention seen in low_frequency/abc_w1_w2_1D.txt.
   They are not a new simplification identity. *)

ClearAll[zPlus, zMinus, rhoPlus, rhoMinus, rhoSymmetric];
zPlus[e_, w_: 0] := (Pi + \[Beta] (\[CapitalGamma] + I (-\[Mu] - w + e)))/(2 Pi);
zMinus[e_, w_: 0] := (Pi + \[Beta] (\[CapitalGamma] - I (-\[Mu] + w + e)))/(2 Pi);
rhoPlus[e_, w_: 0] := (I PolyGamma[0, zPlus[e, w]])/Pi;
rhoMinus[e_, w_: 0] := (I PolyGamma[0, zMinus[e, w]])/Pi;
rhoSymmetric[e_] := 1/2 + (I/2) (-PolyGamma[0, zMinus[e, 0]] + PolyGamma[0, zPlus[e, 0]])/Pi;
