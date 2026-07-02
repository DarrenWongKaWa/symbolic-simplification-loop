# Loop 014–017 Final Integration Report

## Status

PASS — verified.

Loops 014, 015, 016, 017 are individually and jointly PASS. Runtime
artifacts are materialized, schema-validated, and embedded into the
stage summary digest. The two pre-existing pytest failures are
resolved. `sigma_abc` physics is unmodified. No 012C promotion, Stage
013 global pre-IBP assembly, tensorial IBP, or total-derivative
reduction was started. Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Per-Loop Status

| Loop | Source artifacts | Runtime artifact on stage 010 | Schema OK | Gate | Report |
| --- | --- | --- | --- | --- | --- |
| 014 B-lite pre-run brief | PRESENT | `.loop/pre_run_brief.json` + `reports/agent_self_understanding.md` | OK | `WARN`, `hard_stop=False` | `LOOP_014_AGENT_PRE_RUN_BRIEF_LITE_REPORT.md` |
| 015 B-hardgate pre-run brief | PRESENT | `.loop/pre_run_gate_result.json` | OK | `WARN`, `execution_allowed=True`, `reviewer_consulted=False` | `LOOP_015_AGENT_PRE_RUN_BRIEF_HARDGATE_REPORT.md` |
| 016 Scientific identity rendering | PRESENT | `.loop/scientific_identities.json` + `reports/stage_..._scientific_identities.md/.tex` | OK | library size = 5 identities | `LOOP_016_SCIENTIFIC_IDENTITY_RENDERING_REPORT.md` |
| 017 Formula-to-check traceability | PRESENT | `.loop/identity_traceability.json` + `reports/identity_traceability.md` | OK | `PASS`, `blocking_failures=[]` | `LOOP_017_FORMULA_TO_CHECK_TRACEABILITY_REPORT.md` |

## Verification Commands and Outputs

### pytest

```text
$ python3 -m pytest -q
... 159 passed, 1 warning in 33.64 s
```

Exit code: 0. Failure count: 0.

### compileall

```text
$ python3 -m compileall loop_engine scripts tests
Listing 'loop_engine'...
Listing 'scripts'...
Listing 'tests'...
(no errors)
```

### CLI Refresh on Stage 010

```text
$ python3 scripts/build_pre_run_brief.py \
    --stage autonomous_runs/sigma_abc/stages/sigma_abc_010_pair_kernel_fusion_pilot \
    --profile profiles/sigma_abc_pair_kernel_fusion_pilot.yaml
-> .loop/pre_run_brief.json (exit 0)

$ python3 scripts/audit_pre_run_brief.py --stage ... --profile ...
-> .loop/pre_run_brief_audit.json (exit 0, hard_stop=False)

$ python3 scripts/check_pre_run_gate.py --stage ... --profile ...
-> .loop/pre_run_gate_result.json (exit 0, execution_allowed=True)

$ python3 scripts/audit_identity_traceability.py --stage ... --project sigma_abc
-> .loop/identity_traceability.json (exit 0, gate=PASS)
```

### Stage 010 Artifact Summary (live dump)

```text
014 brief: profile_match={deps, expected_outputs, forbidden_actions, in_approved_stage_ids}=True,
          boundary_acked=True, DC caveat in list=True
014 audit: gate=WARN, hard_stop=False, blocking_reasons=[]
015 gate:  gate=WARN, execution_allowed=True, reviewer_consulted=False
016 idents: count=5, Forbidden-family containment.check_count=6,
           role=boundary, blocking=True,
           includes_NoTensorialIBPStarted=True
017 trace:  gate=PASS, blocking_failures=[],
           Forbidden-family containment status=LINKED,
           linked=[NoIBPStarted, NoTotalDerivativeIntroduced, NoFullTensorialClaim]
SCHEMA VALIDATION: all 4 artifacts OK
```

### Rendered Reports

```text
reports/agent_self_understanding.md                                          size=570
reports/stage_sigma_abc_010_pair_kernel_fusion_pilot_scientific_identities.md size=1194
reports/stage_sigma_abc_010_pair_kernel_fusion_pilot_scientific_identities.tex size=1281
reports/identity_traceability.md                                             size=481
```

### Stage Summary Digest Integration (sections 12–14)

```text
## 12. Pre-run brief
## 13. Scientific identities
- Identity -> XXX projection regression (protected_regression)
- Identity -> Forbidden-family containment (boundary)
## 14. Identity traceability
- XXX projection regression -> LINKED
- Forbidden-family containment -> LINKED
```

### Forbidden-Artifact Scan

```text
find . -maxdepth 4 -type f \
  \( -name "sigma_abc_012c_loop_orbit_canonicalization_promotion*" \
     -o -name "*promoted_candidate_manifest*" \
     -o -name "*tensorial_ibp*" \
     -o -name "*total_derivative*" \)
-> (no output)
```

No 012C candidate promotion, no tensorial IBP, no total-derivative
reduction artifacts produced.

## Files Changed Across Phases 0–6

```text
LOOP_014_017_STATUS_AUDIT.md                       # Phase 0 audit
LOOP_013_HOTFIX_FOLLOWUP_TEST_FIX_REPORT.md        # Phase 1 hotfix follow-up
LOOP_014_AGENT_PRE_RUN_BRIEF_LITE_REPORT.md        # Phase 2
LOOP_015_AGENT_PRE_RUN_BRIEF_HARDGATE_REPORT.md    # Phase 3
LOOP_016_SCIENTIFIC_IDENTITY_RENDERING_REPORT.md   # Phase 4
LOOP_017_FORMULA_TO_CHECK_TRACEABILITY_REPORT.md   # Phase 5
LOOP_014_017_FINAL_INTEGRATION_REPORT.md           # Phase 6 (this file)

identities/sigma_abc.default_identities.yaml      # Phase 1 expanded FF check list
tests/test_sigma_abc_loop_candidate_preparation.py # Phase 1 BLOCKED-contract update
```

Engine, schema, templates, runner scripts, profiles, freeze_preconditions,
human_signoff, completion_matrix, and `sigma_abc/` physics were NOT modified.

## Two Pre-existing Failures Resolved (Phase 1)

| Failure | Root cause | Fix | Test |
| --- | --- | --- | --- |
| `test_loop_candidate_preparation_blocks_when_stage012_inputs_are_absent` | Pre-run gate hardened (Loop 015) means runner now BLOCKED early; legacy test expected FAIL + downstream keys emitted | Updated test to expect BLOCKED + `PreRunGate` check + 012C keys ABSENT + candidate outputs ABSENT | PASS |
| `test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008` | `Forbidden-family containment` identity bound to `NoIBPStarted` / `NoTotalDerivativeIntroduced` only; safe-prefusion emits `NoTensorialIBPStarted` / `NoFullTensorialKernelFusionStarted` instead, so MISSING_CHECK + blocking → freeze gate fails | Expanded identity library `Forbidden-family containment.check` to include those names | PASS |

Full evidence: [`LOOP_013_HOTFIX_FOLLOWUP_TEST_FIX_REPORT.md`](./LOOP_013_HOTFIX_FOLLOWUP_TEST_FIX_REPORT.md).

## Non-goals Preserved

This work did not:

```text
- Modify sigma_abc physics.
- Start 012C promotion.
- Start Stage 013 global pre-IBP assembly.
- Start tensorial IBP.
- Introduce total-derivative reduction.
- Claim full tensorial sigma_abc correctness.
- Replace deterministic completion with reviewer opinion.
- Weaken freeze_preconditions.
- Weaken human signoff.
```

## Recommended Next Command

Only after this final integration report PASS, the next step is to
**return to the sigma_abc mainline** for the 012C-prep dry-run only
(no promotion):

```text
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_loop_candidate_preparation \
  --dry-run \
  --from-current-checkpoint
```

Expected:

```text
PreRunBriefGate            -> PASS or correctly BLOCKED
PreRunGateResult           -> execution_allowed=False (BLOCKED by forbidden intent)
ScientificIdentitiesLoaded -> True
IdentityTraceabilityGate   -> PASS (no 012C-specific keys emitted)
NoCandidatePromoted        -> True
NoIBPStarted               -> True
NoTotalDerivativeIntroduced-> True
```

Do NOT promote any 012C candidate automatically. 012C promotion
requires explicit human approval and L2 full-panel review.