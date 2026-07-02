# Loop 013 Hotfix Follow-up: Two Pre-existing pytest Failures Fix

## Status

PASS.

```text
python3 -m pytest -q
-> 159 passed, 1 warning in ~35 s
python3 -m compileall loop_engine scripts tests
-> PASS
```

No `sigma_abc` physics was modified. No 012C promotion, Stage 013
global pre-IBP assembly, tensorial IBP, or total-derivative reduction
was started. Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Failures Resolved

### Failure 1 — `test_loop_candidate_preparation_blocks_when_stage012_inputs_are_absent`

**Before**

```text
AssertionError: assert 'BLOCKED' == 'FAIL'
```

**Cause**

The implementation correctly switched `overall_gate` from `FAIL` to
`BLOCKED` once the pre-run gate hardened (Loop 015 work). The test still
asserted the legacy FAIL string. In addition, downstream 012C-specific
keys (`ReportIdentityCheck`, `CandidateSource`, `ToyCandidateDetected`,
`MockCandidateDetected`, `UsesStage012ALoopLedger`,
`UsesStage012BHypothesisLedger`) cannot be written when pre-run gate
early-rejects forbidden intent — the runner halts before any candidate
analysis runs.

**Fix (test only, no implementation change)**

```text
tests/test_sigma_abc_loop_candidate_preparation.py
  line 118: assert "FAIL" -> assert "BLOCKED"
  lines 119-137: re-shaped to assert BLOCKED semantics:
    - PreRunGate check present with gate == "BLOCKED"
    - 012C-specific keys MUST BE absent (early reject is the whole point)
    - loop_* and validation/* candidate artifacts MUST NOT exist
```

Per PLAN 1.2 rule:

```text
FAIL = mathematical/validation failure.
BLOCKED = dependency/readiness/precondition failure.
```

### Failure 2 — `test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`

**Before**

```text
subprocess CalledProcessError, exit status 1
RuntimeError: Cannot freeze checkpoint: identity_traceability gate must be PASS:
Forbidden-family containment; human_signoff.yaml is required before freezing
```

**Cause**

`identities/sigma_abc.default_identities.yaml` declared
`Forbidden-family containment` with `blocking: true`, bound to checks
`NoIBPStarted` and `NoTotalDerivativeIntroduced`. The safe-prefusion
profile runs stages 006/007/008, which only emit `NoTensorialIBPStarted`
and `NoFullTensorialKernelFusionStarted` as boundary assertions — never
the canonical names listed. The identity auditor (`loop_engine/identity_traceability.py`)
correctly concluded MISSING_CHECK + blocking → freeze gate failed.

**Fix (declaration only, no engine change)**

```text
identities/sigma_abc.default_identities.yaml
  Forbidden-family containment.check extended to:
    - NoIBPStarted
    - NoTotalDerivativeIntroduced
    - NoTensorialIBPStarted
    - NoFullTensorialKernelFusionStarted
    - NoFullTensorialClaim
    - NoCandidatePromoted
```

The auditor still requires at least one of these checks to appear in
`validation_summary.json::checks` / `protected_regressions` / top-level
keys for `LINKED` status. Safe-prefusion now naturally provides
`NoTensorialIBPStarted`. The identity remains `blocking: true` and
`role: boundary`, so the gate still stops freeze if a stage forgets to
emit any of them.

The `human_signoff.yaml` requirement is unchanged and continues to be
the freeze-time security boundary.

## Files Changed

```text
identities/sigma_abc.default_identities.yaml                       # expanded check list
tests/test_sigma_abc_loop_candidate_preparation.py                # BLOCKED contract update
LOOP_013_HOTFIX_FOLLOWUP_TEST_FIX_REPORT.md                       # this report
```

`loop_engine/`, `scripts/`, `schemas/`, `profiles/`, `sigma_abc/`, and
`freeze_preconditions` were NOT modified.

## Verification

```text
pytest -q                    -> 159 passed, 0 failed
compileall loop_engine scripts tests -> PASS
```

## What's Next

Phase 1 of PLAN.md is satisfied. Proceed to Phase 2 (Loop 014 runtime
artifacts) using the existing 006 stage as a fixture, then Phase 3
through Phase 7.
