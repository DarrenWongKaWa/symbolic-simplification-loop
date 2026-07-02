# Scientific Reviewer Audit

```text
AlgebraReviewerExists -> True
PhysicsReviewerExists -> True
SoftwareReviewerExists -> True
AggregateReviewExists -> True
AutonomousRunnerExists -> True
```

## Existing Reviewer Loop

The repo already contains the three local read-only reviewer role templates:

- `skill/algebra_reviewer.md`
- `skill/physics_reviewer.md`
- `skill/software_reviewer.md`

The repo also contains structured reviewer execution and aggregation:

- `scripts/run_reviewer_agents.py`
- `scripts/aggregate_review_results.py`
- `.loop/reviewer_results/*.json`
- `.loop/review_result.json`

The autonomous runner exists at:

- `scripts/run_autonomous_loop.py`

## New Loop-004 Extension

This branch adds a senior scientific meta-review layer after ordinary reviewer
aggregation and before checkpoint freeze.  It is still repo-local and does not
call external ChatGPT or modify symbolic physics outputs.
