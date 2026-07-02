# Loop 005 Real Agent Invocation And Named Digests Report

## Branch

`loop_005_real_agent_invocation_and_named_digests`

## Scope

This branch upgrades loop infrastructure only. It does not modify `sigma_abc`
physics, does not start Stage 011, does not rewrite frozen scientific outputs,
and does not claim full tensorial `sigma_{\mu\alpha\beta}` correctness.

## Role Architecture

Agents make judgments, plans, reviews, and patches:

- `MainExecutor`
- `VerifierAgent`
- `AlgebraReviewer`
- `PhysicsReviewer`
- `SoftwareReviewer`
- `ScientificMetaReviewer`
- `PatchPlanner`
- `DigestReviewer`

Deterministic services perform aggregation and policy actions:

- Verifier service
- ReviewAggregator service
- StageDigestBuilder service
- DecisionEngine service
- Checkpoint freezer
- Mailbox event logger

## Mailbox Protocol

Every autonomous stage now creates:

```text
.loop/mailbox/state.json
.loop/mailbox/events.jsonl
.loop/mailbox/attempt_001/<actor>/
```

Mailbox events include timestamp, stage id, attempt number, actor, event type,
input paths, output paths, hashes, and a short summary.

## Patch Loop Protocol

Normal review or meta-review failure can route to `PATCH`. Patch handling is
structured:

```text
DecisionEngine -> PATCH
PatchPlanner -> PATCH_PLAN.md + .loop/patch_planner_result.json
MainExecutor retry -> validation/review/meta-review/digest/decision rerun
```

Repeated identical patch reasons or exhausted patch attempts hard-stop the
stage.

## Verifier Service And VerifierAgent

The deterministic verifier service writes:

```text
.loop/verifier_service_result.json
```

The VerifierAgent audit writes:

```text
.loop/verifier_agent_result.json
.loop/blackboard/verifier_agent_result.json
```

VerifierAgent cannot override failed validation. Production freeze requires
validation to pass independently.

## Named Digest Behavior

Loop 005 keeps generic files for backward compatibility but makes named files
canonical for manifests:

```text
reports/<stage_id>_summary.md
reports/<stage_id>_summary.tex
reports/<stage_id>_summary.pdf
reports/<stage_id>_human_review.md
.loop/<stage_id>_meta_review.json
```

Generic aliases may also exist:

```text
reports/stage_summary.md
reports/stage_summary.tex
reports/stage_summary.pdf
reports/human_readable_review.md
.loop/meta_review_result.json
```

## Production Agent Invocation Policy

Production `sigma_abc` profiles now require:

```yaml
agents:
  require_real_invocation: true
  forbid_stub_in_production: true
  require_invocation_evidence: true
  require_read_only_contract: true
  require_mailbox_events: true

orchestration:
  use_mailbox: true
  require_patch_planner_for_patch: true
  max_patch_attempts_per_stage: 2
```

Test profiles may use structured local/stub agent outputs only when explicitly
declared with:

```yaml
agents:
  allow_stub_for_tests: true
```

## Adapter Limitation

The current Python runner records mailbox events and structured local agent
outputs. It does not yet call an external Codex subagent runtime from Python.
Therefore future production `sigma_abc` runs must treat missing real invocation
evidence as:

```text
AgentRuntimeStatus -> UNAVAILABLE
ProductionRunAllowed -> False
```

until a real runtime adapter is added. The mock loop remains allowed because
`profiles/test_safe_loop.yaml` explicitly permits stubs for tests.

## Retrospective Stage 010 Audit

Created:

```text
reports/stage_010_pair_kernel_fusion_pilot_orchestration_audit.md
```

It records:

```text
Stage010ProductionAgentInvocationStatus -> NOT_PROVEN
```

This is acceptable retrospectively, but future production profile runs must
provide mailbox events and invocation evidence.

## Commands Run

```bash
python3 -m pytest tests/test_mailbox_orchestration.py -q
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
python3 scripts/run_autonomous_loop.py --project mock --profile test_safe_loop --clean
```

## Current Status

```text
mailbox state created -> True
mailbox events record agent order -> True
patch planner route works -> True
same patch reason hard-stops -> True
verifier agent cannot override validation fail -> True
digest reviewer blocks digest overclaim -> True
MainExecutor forbidden output policy exists -> True
production profile requires real invocation -> True
named digest paths work -> True
real Codex runtime adapter from Python -> NOT_IMPLEMENTED
future sigma_abc production without real invocation evidence -> NOT_ALLOWED
```

## Claim Boundary

Allowed:

- Claim Loop 005 adds mailbox-based structured orchestration.
- Claim named stage digests and named meta-review outputs are generated.
- Claim production `sigma_abc` profiles now require real invocation evidence.
- Claim mock/test profiles can still run with explicit stub permission.

Forbidden:

- Do not claim new `sigma_abc` physics simplification.
- Do not claim Stage 011 was started.
- Do not claim full tensorial `sigma_{\mu\alpha\beta}` correctness.
- Do not claim retrospective Stage 010 had real independent invocation evidence.

## Persistent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
