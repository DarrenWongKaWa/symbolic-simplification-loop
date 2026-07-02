# Loop 003 Autonomous Project Runner Report

Branch: `loop_003_autonomous_project_runner`

## Goal

This branch adds a repo-native autonomous loop runner so routine symbolic-loop
stages can be selected, executed, reviewed, decided, and frozen from local
project metadata rather than from long external prompts.

This is an orchestration-layer branch only.  It does not change `sigma_abc`
physics, does not continue `sigma_abc` stages, and does not start tensorial
kernel fusion or tensorial IBP reduction.

## Implemented Artifacts

| Artifact | Purpose |
| --- | --- |
| `projects/sigma_abc/loop.yaml` | Safe pre-fusion stage graph for the future tensorial `sigma_abc` project |
| `profiles/sigma_abc_safe_pre_fusion.yaml` | Allowed autonomy, reviewer mode, patch limits, and stop-after-stage boundary |
| `policies/sigma_abc_hard_stops.yaml` | Hard-stop tags and caveats that must be preserved |
| `benchmarks/sigma_xxx_projection.yaml` | Protected `sigma_xxx` projection benchmark metadata and caveats |
| `scripts/run_autonomous_loop.py` | Repo-native autonomous loop runner |
| `profiles/test_safe_loop.yaml` | Test/smoke profile for autonomous runner validation |
| `projects/mock*/loop.yaml` | Mock projects used to validate positive and negative gates |

## Runner Behavior

`scripts/run_autonomous_loop.py` performs the local loop lifecycle:

1. load `projects/<project>/loop.yaml`;
2. load `profiles/<profile>.yaml`;
3. load hard-stop and benchmark policies;
4. read already frozen checkpoints from `autonomous_runs/<project>/checkpoints/`;
5. choose pending stages up to the profile limit;
6. initialize each stage;
7. execute the stage-local mock plan;
8. write validation and metrics;
9. build the review packet;
10. run Codex-local structured reviewers;
11. aggregate `.loop/review_result.json`;
12. combine validation and review in the decision engine;
13. freeze only when the decision allows it;
14. write `AUTONOMOUS_LOOP_RUN_REPORT.md`.

## Smoke Command

```bash
python scripts/run_autonomous_loop.py --project mock --profile test_safe_loop --clean
```

The command runs two mock stages from `projects/mock/loop.yaml`:

```text
mock_000_identity
mock_001_identity
```

Both stages validate, pass structured local review, receive `FREEZE`, and create
checkpoint manifests.

## Safety Gates

The following negative gates are covered by tests and live smoke runs:

| Gate | Expected result |
| --- | --- |
| validation failure | `DO_NOT_FREEZE`; no checkpoint manifest |
| missing reviewer output | `PATCH`; no checkpoint manifest |
| hard-stop forbidden stage tag | `HARD_STOP`; no checkpoint manifest |

## Verification Commands

Fresh verification commands used for this branch:

```bash
python3 -m pytest -q
python3 -m py_compile scripts/run_autonomous_loop.py
python3 scripts/run_full_loop_smoke_test.py --clean
python3 scripts/run_autonomous_loop.py --project mock --profile test_safe_loop --clean
python3 scripts/run_autonomous_loop.py --project mock_validation_fail --profile test_safe_loop --clean
python3 scripts/run_autonomous_loop.py --project mock_missing_reviewer --profile test_safe_loop --clean
python3 scripts/run_autonomous_loop.py --project mock_forbidden --profile test_safe_loop --clean
```

Observed gates:

```text
pytest: 29 passed, 1 warning
autonomous mock schema gate: PASS
mock stages frozen: 2
validation failure blocks freeze: PASS
missing reviewer blocks freeze: PASS
hard stop policy blocks forbidden stage: PASS
```

## Claim Boundary

Allowed:

```text
The repo now contains an autonomous runner that can execute a local stage graph
through validation, structured local review, decision, and checkpoint freezing.
```

Allowed:

```text
A mock project can run two stages from loop.yaml without an external long
prompt, and protected failure modes block freezing.
```

Not allowed:

```text
This branch started sigma_abc simplification.
```

Not allowed:

```text
This branch performed tensorial kernel fusion or tensorial IBP reduction.
```

Not allowed:

```text
This branch proves full tensorial sigma_abc correctness.
```

