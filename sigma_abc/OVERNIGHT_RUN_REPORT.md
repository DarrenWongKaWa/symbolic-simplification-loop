# OVERNIGHT_RUN_REPORT.md

## Stages Attempted

1. `001_raw_generator_from_low_frequency_code` -- attempted, failed hard gate.

## Stages Passed

None.

## Stages Failed

- `001_raw_generator_from_low_frequency_code` because `DCProjectionTo1D -> TIMEOUT`.

## Commands Run

```json
[
  {
    "command": "wolframscript -code src=\"/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/low_frequency/abc_w1_w2_1D.txt\"; dc=\"/Users/wangjiahua/Desktop/25-26/Dissipation & Nonlinear Transport/newsimplification/low_frequency/Sigma_abc_dc_1D.txt\"; expr=ToExpression[Import[src,\"Text\"], InputForm]; target=ToExpression[Import[dc,\"Text\"], InputForm]; res=TimeConstrained[Quiet@FullSimplify[SeriesCoefficient[expr /. \\[Omega]2 -> -\\[Omega]1, {\\[Omega]1,0,2}] - target], 180, $TimedOut]; Print[If[res===$TimedOut,\"TIMEOUT\",ToString[res===0]]];",
    "exit_code": 0,
    "stdout": "TIMEOUT\nNull",
    "stderr": ""
  }
]
```

## Files Generated

```text
.loop/decision.json
.loop/metrics.json
.loop/review_result.json
.loop/reviews/review_result.AlgebraReviewer.json
.loop/reviews/review_result.PhysicsReviewer.json
.loop/reviews/review_result.SoftwareReviewer.json
.loop/stage_plan.json
.loop/validation_summary.json
CLAIM_BOUNDARY.md
EXECUTION_REPORT.md
STAGE_PLAN.md
decision.json
input_snapshots/DC limit - Gamma Expansion -1D.nb
input_snapshots/Sigma_abc_dc_1D.txt
input_snapshots/abc_w1_w2_1D.txt
input_snapshots/band_sum_abstractor.wl
raw/raw_sigma_abc.wl
raw/raw_sigma_abc_dc.wl
raw/raw_sigma_abc_finite_frequency.wl
raw/raw_sigma_abc_manifest.json
review_packet.md
review_result.AlgebraReviewer.json
review_result.PhysicsReviewer.json
review_result.SoftwareReviewer.json
review_result.json
reviewer_agent_prompt.AlgebraReviewer.md
reviewer_agent_prompt.PhysicsReviewer.md
reviewer_agent_prompt.SoftwareReviewer.md
scripts/generate_raw_sigma_abc.wl
scripts/thermal_rho_kernels.wl
validation/dc_series_projection_attempt.log
validation/project_xxx_projection_validation.wl
validation/validation_summary.json
```

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

## Reviewer Verdict

`FAILED`

## Decision Output

```json
{
  "action": "DO_NOT_FREEZE",
  "reason": "validation failed or missing PASS gate",
  "freeze_allowed": false,
  "caveats": [],
  "suggested_next_stage": null
}
```

## Frozen Checkpoints

None. The stage was not frozen because `overall_gate != PASS`.

## Known Caveats

- Candidate tensorial wrapper is projection-preserving only.
- DC direct-source wrapper exists, but the required finite-frequency-to-DC series benchmark timed out.

## Recommended Next Stage

`rerun_stage_001_with_successful_dc_projection_benchmark`.
Do not start Stage 002 until Stage 001 passes.
