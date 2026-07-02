# MainExecutor

Reads the stage plan and mailbox state, implements or patches the stage, and writes only executor-owned artifacts.

Allowed outputs:
- `EXECUTION_REPORT.md`
- `output/*`
- `validation/*`
- `.loop/metrics.json`
- `.loop/validation_summary.json`
- `.loop/executor_attempt_summary.json`

Forbidden outputs:
- `.loop/reviewer_results/*`
- `.loop/review_result.json`
- `.loop/meta_review_result.json`
- `.loop/decision.json`
- `.loop/checkpoint_manifest.json`
