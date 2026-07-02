(* Stage 001 projection validation.
   The finite-frequency text lift is exact under xxx projection.
   The DC series benchmark is intentionally time constrained. *)

ClearAll[normalize, lift, project];
normalize[s_String] := StringReplace[s, WhitespaceCharacter .. -> ""];
lift[s_String] := StringReplace[s, {"haaa[" -> "h3[mu,alpha,beta][", "haa[" -> "h2[alpha,beta][", "ha[" -> "h1[mu]["}];
project[s_String] := StringReplace[s, {"h3[mu,alpha,beta][" -> "haaa[", "h2[alpha,beta][" -> "haa[", "h1[mu][" -> "ha["}];
