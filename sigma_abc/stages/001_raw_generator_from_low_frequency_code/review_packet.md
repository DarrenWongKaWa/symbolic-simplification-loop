# Review Packet -- 001_raw_generator_from_low_frequency_code

## Scope

Review Stage 001 only. This stage generated a candidate raw wrapper and attempted projection regression.

## Key Evidence

- `validation/validation_summary.json`
- `validation/dc_series_projection_attempt.log`
- `raw/raw_sigma_abc_manifest.json`
- `raw/raw_sigma_abc.wl`

## Validation Summary

```json
{
  "stage_name": "001_raw_generator_from_low_frequency_code",
  "overall_gate": "FAIL",
  "identity_type": "ProjectionRegression",
  "checks": [
    {
      "name": "RawSigmaABCExists",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    },
    {
      "name": "FiniteFrequencyProjectionTo1D",
      "expected": "PASS",
      "actual": "PASS",
      "gate": "PASS"
    },
    {
      "name": "DCDirectSourceProjectionTo1D",
      "expected": "PASS",
      "actual": "PASS",
      "gate": "PASS"
    },
    {
      "name": "DCProjectionTo1D",
      "expected": "PASS",
      "actual": "TIMEOUT",
      "gate": "FAIL"
    },
    {
      "name": "NoSimplificationStarted",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    },
    {
      "name": "NoTensorialKernelFusionStarted",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    },
    {
      "name": "NoTensorialIBPStarted",
      "expected": true,
      "actual": true,
      "gate": "PASS"
    }
  ],
  "protected_regressions": [
    {
      "name": "finite_frequency_xxx_projection_to_low_frequency_1d",
      "gate": "PASS"
    },
    {
      "name": "dc_series_projection_to_sigma_abc_dc_1d",
      "gate": "TIMEOUT"
    }
  ],
  "caveats": [
    "The tensorial candidate is a direction-label lift from 1D sources, not a full tensorial correctness proof.",
    "DC series projection benchmark timed out; Stage 001 is not eligible for checkpoint freeze."
  ],
  "RawSigmaABCExists": true,
  "FiniteFrequencyProjectionTo1D": "PASS",
  "DCProjectionTo1D": "TIMEOUT",
  "NoSimplificationStarted": true,
  "MathematicaCommands": [
    {
      "command": "wolframscript -code src=\"/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/low_frequency/abc_w1_w2_1D.txt\"; dc=\"/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/low_frequency/Sigma_abc_dc_1D.txt\"; expr=ToExpression[Import[src,\"Text\"], InputForm]; target=ToExpression[Import[dc,\"Text\"], InputForm]; res=TimeConstrained[Quiet@FullSimplify[SeriesCoefficient[expr /. \\[Omega]2 -> -\\[Omega]1, {\\[Omega]1,0,2}] - target], 180, $TimedOut]; Print[If[res===$TimedOut,\"TIMEOUT\",ToString[res===0]]];",
      "exit_code": 0,
      "stdout": "TIMEOUT\nNull",
      "stderr": ""
    }
  ]
}
```

## Requested Review

1. Confirm that failed DC series benchmark blocks continuation.
2. Confirm that no tensorial simplification, kernel fusion, or IBP was started.
3. Confirm that claims are restricted to candidate generation and finite-frequency projection regression.
