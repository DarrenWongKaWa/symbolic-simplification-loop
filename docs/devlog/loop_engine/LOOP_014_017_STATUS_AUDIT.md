# Loop 014–017 Status Audit

## Status

PRE_MATERIALIZED / NEVER_FINALIZED.

Loops 014–017 的代码、模板、schema、identity library 都已落到仓库，
测试在 `tests/test_loop014_017_pre_run_identity_traceability.py` 中 7 个
case **全部 PASS**，但**没有任何 `LOOP_014_*` / `LOOP_015_*` / `LOOP_016_*` /
`LOOP_017_*` 报告文件**，也没有 `LOOP_014_017_FINAL_INTEGRATION_REPORT.md`，
因此不能宣称 014–017 总体 PASS。

`sigma_abc` physics 未修改；012C promotion、Stage 013、tensorial IBP、
total-derivative reduction 均未启动。永久 caveat 保留：

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Per-Loop Status

| Loop | Source artifacts | Tests | Runtime artifacts | Report | Status |
| --- | --- | --- | --- | --- | --- |
| 014 B-lite pre-run brief | PRESENT (schema + engine + script + audit + 2 templates) | PASS (1/1 in new file) | none at repo root (`autonomous_runs/sigma_abc/stages/...` empty for 014 outputs) | MISSING | CODE_PRESENT / NO_RUNTIME / NO_REPORT |
| 015 B-hardgate pre-run brief | PRESENT (engine + script + schema) | PASS (in 014–017 file) | none | MISSING | CODE_PRESENT / NO_RUNTIME / NO_REPORT |
| 016 Scientific identity rendering | PRESENT (engine + 2 schemas + 2 templates + default identity YAML) | PASS (1/1 in new file) | none | MISSING | CODE_PRESENT / NO_RUNTIME / NO_REPORT |
| 017 Formula-to-check traceability | PRESENT (engine + schema + audit script) | PASS (1/1 in new file, includes freeze-blocking test) | none persisted | MISSING | CODE_PRESENT / NO_RUNTIME / NO_REPORT |

FirstIncompleteLoop → 014 (by Phase 2 of PLAN.md order).

ForbiddenArtifactsGenerated → False at audit time. The `autonomous_runs/`
tree contains only `sigma_abc_006_tensorial_sector_architecture_review` left
over from prior runs, no 012C promote manifest, no IBP artifacts, no full
tensorial correctness claim.

## Verification Performed

```text
find LOOP_014..017*
-> (no output)

python3 -m pytest -q tests/test_loop014_017_pre_run_identity_traceability.py
-> 7 passed, 1 warning in ~1.3 s

python3 -m compileall loop_engine scripts tests
-> PASS

python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_safe_pre_fusion \
  --from-current-checkpoint --clean
-> raises RuntimeError at freeze_checkpoint:
   "Cannot freeze checkpoint: identity_traceability gate must be PASS:
    Forbidden-family containment; human_signoff.yaml is required before freezing"
```

## Required Artifacts Inventory (from PLAN 0.2)

```text
schemas/pre_run_brief.schema.json                    -> OK
loop_engine/pre_run_brief.py                         -> OK
scripts/build_pre_run_brief.py                       -> OK
scripts/audit_pre_run_brief.py                       -> OK
templates/PRE_RUN_BRIEF.template.md                  -> OK
templates/AGENT_SELF_UNDERSTANDING.template.md       -> OK
loop_engine/pre_run_gate.py                          -> OK
scripts/check_pre_run_gate.py                        -> OK
schemas/pre_run_gate_result.schema.json              -> OK
loop_engine/scientific_identities.py                 -> OK
schemas/scientific_identity.schema.json              -> OK
schemas/scientific_identity_library.schema.json     -> OK
identities/sigma_abc.default_identities.yaml         -> OK
templates/SCIENTIFIC_IDENTITIES_STAGE_SECTION.template.md  -> OK
templates/SCIENTIFIC_IDENTITIES_STAGE_SECTION.template.tex -> OK
loop_engine/identity_traceability.py                 -> OK
schemas/identity_traceability.schema.json            -> OK
scripts/audit_identity_traceability.py               -> OK
```

All 18 file checks PRESENT.

## Two Pre-existing pytest Failures (BLOCKING final PASS)

Both failures are described in PLAN 1.2. New observations tighten the
diagnosis:

### Failure 1 — `test_loop_candidate_preparation_blocks_when_stage012_inputs_are_absent`

```text
tests/test_sigma_abc_loop_candidate_preparation.py
  line 118: assert validation["overall_gate"] == "FAIL"
  AssertionError: assert 'BLOCKED' == 'FAIL'
```

The test setup wipes stage012a/012b and runs the loop; implementation now
reports `overall_gate = BLOCKED`. Semantically the implementation is
correct: missing upstream artifacts → BLOCKED (dependency failure), not
FAIL (mathematical failure). Per PLAN 1.2 rule:

```text
FAIL = mathematical/validation failure.
BLOCKED = dependency/readiness/precondition failure.
```

Required test correction: replace the literal `"FAIL"` with `"BLOCKED"`
and add (or relax to) the recommended assertions called out in PLAN 1.3.

### Failure 2 — `test_sigma_abc_safe_prefusion_runs_only_stages_006_to_008`

```text
tests/test_autonomous_loop_runner.py
  subprocess CalledProcessError, exit status 1
```

Direct invocation traceback:

```text
RuntimeError: Cannot freeze checkpoint: identity_traceability gate must be PASS:
Forbidden-family containment; human_signoff.yaml is required before freezing
```

This is **not** a stage-policy failure. Stages 006/007/008 ran. The freeze
hard-stopped because:

1. `Forbidden-family containment` identity (declared `blocking: true`,
   bound to checks `NoIBPStarted` and `NoTotalDerivativeIntroduced` in
   `identities/sigma_abc.default_identities.yaml`) is being judged as
   MISSING_CHECK by the new traceability auditor (017) on a stage
   that does not emit those validation fields.
2. No `human_signoff.yaml` exists for the cleaned stage.

Diagnosis: 017's freeze-precondition was newly wired and pulls identities
through a stricter gate than the previous run path. The `Forbidden-family
containment` identity marks itself `blocking: true` and references
`NoIBPStarted` / `NoTotalDerivativeIntroduced` checks that safe-prefusion
profiles do not currently emit (safe-prefusion is supposed to **prove**
no IBP, not assert it as a check). Two coherent fixes are possible —
decision required from user, see below.

## compileall

```text
python3 -m compileall loop_engine scripts tests
-> PASS (no errors)
```

## Recommended Next Action (decision required)

Three coherent paths forward. They differ on which side of the gate is
considered the source of truth. Recommended ordering listed.

### Option A — Treat 017 traceability gate as authoritative, broaden safe-prefusion checks (RECOMMENDED)

1. Update `identities/sigma_abc.default_identities.yaml` so `Forbidden-
   family containment` is either:
   - marked `blocking: false` and `role: boundary` with a CHECK line that
     always evaluates PRESENT on safe-prefusion runs, OR
   - bound to whatever check `sigma_abc_safe_pre_fusion` actually emits
     today.
2. Update `test_loop_candidate_preparation_blocks_when_stage012_inputs_are_absent`
   to expect `BLOCKED` instead of `FAIL` per PLAN 1.2.
3. Re-run pytest; expect 159 passed, 0 failed.
4. Persist runtime artifacts under `autonomous_runs/sigma_abc/stages/...`
   for 014 (pre-run brief), 015 (pre-run gate), 016 (scientific identities),
   017 (identity traceability) on a clean sigma_abc stage that already has
   human_signoff.
5. Write the four per-loop reports and a final integration report.

### Option B — Relax 017 to REGISTERED/BLOCKED so safe-prefusion can freeze

1. Change `loop_engine/identity_traceability.py` so blocking identities
   without linked checks on safe-prefusion profiles are `REGISTERED` (not
   `MISSING_CHECK`).
2. Fix the same test assertion in Failure 1.
3. Less defensible than A: it weakens the new gate instead of clarifying
   the identity library.

### Option C — Stop at audit, do not advance to sigma_abc runner

1. Leave tests failing, keep the audit as a status report.
2. Do not write per-loop reports until the failure root causes are
   resolved.
3. Use this only if you want a human decision before any gate code
   change.

Whatever option is chosen, the audit itself must not claim 014–017 PASS:
this report is material evidence that code exists, tests pass, but no
runtime artifacts or reports are persisted.

## Files Written by This Audit

```text
LOOP_014_017_STATUS_AUDIT.md   # this file
```

No code, schema, or runtime artifact was modified by this audit.
