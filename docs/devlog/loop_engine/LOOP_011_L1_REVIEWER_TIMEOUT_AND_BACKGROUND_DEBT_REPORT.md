# Loop 011 L1 Reviewer Timeout And Background Debt Report

## Verdict

```text
PASS: Loop 011 L1 reviewer timeout and background review-debt mode
```

This branch fixes the throughput bottleneck where a low-risk
`L1_COMPACT_META` real Codex reviewer can hang, timeout, or produce no valid
output after deterministic validation has already passed.

It does not modify `sigma_abc` physics, does not start 012C promotion, does not
start Stage 013, does not start tensorial IBP, does not introduce
total-derivative reduction, and does not claim full tensorial
`sigma_{\mu\alpha\beta}` correctness.

## Code Changes

- `loop_engine/agent_runtime.py`
  - Adds structured runtime status:
    - `AGENT_TIMEOUT`
    - `AGENT_QUOTA_LIMIT`
    - `AGENT_NO_OUTPUT`
    - `AGENT_SCHEMA_FAIL`
    - `AGENT_OK`
  - Writes `review_debt_required` into invocation summaries.
  - Keeps real invocation evidence; no stub fallback is introduced.

- `loop_engine/runtime_failures.py`
  - Classifies quota, timeout, no-output, and schema-fail reviewer outcomes.
  - Preserves compatibility with the older `AGENT_RUNTIME_QUOTA_EXHAUSTED`
    marker while adding `AGENT_QUOTA_LIMIT`.

- `loop_engine/decision.py`
  - Treats `AGENT_TIMEOUT`, `AGENT_NO_OUTPUT`, and quota markers as
    validated-pending-review conditions rather than patchable code failures.

- `loop_engine/review_debt.py`
  - Allows L1 timeout/quota/no-output to create review debt when validation is
    `PASS` and all safety predicates hold.
  - Writes:
    - `CheckpointStatus -> PROVISIONAL_WITH_REVIEW_DEBT`
    - `OrdinaryReviewComplete -> False`
    - `ExecutorRerunRequired -> False`
    - `VerifierRerunRequired -> False`
  - Keeps high-risk stages blocked by open or blocking review debt.
  - Updates settled debt to `CheckpointStatus -> FROZEN_WITH_CAVEAT`.

- `scripts/run_autonomous_loop.py`
  - Applies lane-specific timeout policy:
    - L1: `l1_timeout_seconds`
    - L2: `l2_timeout_seconds`
  - Converts L1 real-agent timeout/no-output into review debt when the
    throughput profile allows it.
  - Fixes multi-stage run-report identity so `ActualStage` is the last
    attempted stage, not the first.

- `profiles/sigma_abc_hypothesis_pre_ibp_throughput.yaml`
  - Adds explicit L1/L2 timeout and debt policy:
    - L1 timeout/quota/no-output -> `PROVISIONAL_FREEZE_WITH_REVIEW_DEBT`
    - L2 timeout -> `VALIDATED_PENDING_REVIEW`

- `profiles/sigma_abc_hypothesis_pre_ibp.yaml`
  - Adds explicit strict L1/L2 timeout policy without review-debt advancement.

## Tests Added

```text
tests/test_loop011_l1_reviewer_timeout_debt.py
```

Coverage:

- `test_command_agent_adapter_timeout_returns_agent_timeout_status`
- `test_command_agent_adapter_no_output_returns_agent_no_output_status`
- `test_l1_timeout_creates_review_debt_not_hard_stop`
- `test_l1_no_output_creates_review_debt`
- `test_l1_review_debt_allows_012b_exploration_and_blocks_012c`
- `test_l2_timeout_does_not_allow_advance`
- `test_settle_l1_review_debt_without_executor_rerun`
- `test_failed_debt_review_blocks_promotion`
- `test_multistage_run_report_identity_uses_last_attempted_stage`

## Verification

```text
python3 -m pytest -q
128 passed, 1 warning
```

```text
python3 -m compileall loop_engine scripts tests
PASS
```

## Applied Sigma ABC Throughput Run

Command:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp_throughput \
  --from-current-checkpoint \
  --auto-patch \
  --write-digests \
  --max-stages 3
```

Result:

```text
stages_attempted -> 3
stages_frozen -> 3
ReportIdentityCheck -> PASS
ActualStage -> sigma_abc_012b_loop_hypothesis_generation
```

Stage outcomes:

| Stage | Validation | Real reviewer | Decision | Checkpoint status |
| --- | --- | --- | --- | --- |
| `sigma_abc_011_center_sector_pilot` | `PASS` | `AGENT_TIMEOUT` | `PROVISIONAL_FREEZE_WITH_REVIEW_DEBT` | `PROVISIONAL_WITH_REVIEW_DEBT` |
| `sigma_abc_012a_loop_sector_inventory` | `PASS` | `AGENT_TIMEOUT` | `PROVISIONAL_FREEZE_WITH_REVIEW_DEBT` | `PROVISIONAL_WITH_REVIEW_DEBT` |
| `sigma_abc_012b_loop_hypothesis_generation` | `PASS` | `AGENT_TIMEOUT` | `PROVISIONAL_FREEZE_WITH_REVIEW_DEBT` | `PROVISIONAL_WITH_REVIEW_DEBT` |

Each reviewer invocation has real evidence:

```text
actually_invoked -> True
stub_used -> False
runtime_status -> AGENT_TIMEOUT
schema_valid -> False
read_only_contract_enforced -> True
review_debt_required -> True
```

The reviewer output was not faked; these stages are provisional, not ordinary
fully reviewed checkpoints.

## Review Debt Gate

Open review debt now allows:

```text
sigma_abc_012b_loop_hypothesis_generation -> allowed
```

Open review debt blocks:

```text
sigma_abc_012c_loop_orbit_canonicalization_promotion -> blocked
sigma_abc_013_global_pre_ibp_assembly -> blocked
sigma_abc_tensorial_ibp_reduction -> blocked
```

## Current Sigma ABC State

```text
Current checkpoint input -> sigma_abc_010_pair_kernel_fusion_pilot
Throughput exploration reached -> sigma_abc_012b_loop_hypothesis_generation
Stage 011 -> provisional review debt
Stage 012A -> provisional review debt
Stage 012B -> provisional review debt
Stage 012C promotion -> not started
Stage 013 -> not started
Tensorial IBP -> not started
Total derivative reduction -> not introduced
Full tensorial correctness claim -> not made
```

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Next Safe Action

Settle the open L1 review debts when reviewer runtime is available:

```bash
python3 scripts/settle_review_debt.py --project sigma_abc
```

or:

```bash
python3 scripts/resume_pending_reviews.py --project sigma_abc --from-pending
```

Do not run 012C promotion, Stage 013, tensorial IBP, or total-derivative
reduction until the relevant review debt is settled or explicitly approved.
