(* Candidate raw sigma_abc generator from low_frequency 1D sources.
   This script performs a direction-label lift:
     ha[i,j]   -> h1[mu][i,j]
     haa[i,j]  -> h2[alpha,beta][i,j]
     haaa[i,j] -> h3[mu,alpha,beta][i,j]
   It is a projection-preserving raw-generation candidate only. *)

ClearAll[lift1DToTensorialCandidate, projectXXXCandidate];
lift1DToTensorialCandidate[text_String] := StringReplace[text, {
  "haaa[" -> "h3[mu,alpha,beta][",
  "haa[" -> "h2[alpha,beta][",
  "ha[" -> "h1[mu]["
}];
projectXXXCandidate[text_String] := StringReplace[text, {
  "h3[mu,alpha,beta][" -> "haaa[",
  "h2[alpha,beta][" -> "haa[",
  "h1[mu][" -> "ha["
}];
