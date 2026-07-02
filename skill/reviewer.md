# Reviewer Role

The reviewer reads a compact review packet and returns structured JSON. It can be a Codex subagent, manual ChatGPT reviewer, or future OpenAI API reviewer.

## V1 Default

```text
mode = "codex_subagent"
```

The main Codex agent executes the stage. Verifier scripts produce `validation_summary.json`. The reviewer subagent reads only the packet and selected validation artifacts, then returns `review_result.json`.

## Routine Reviewer Roles

Use three read-only Codex subagents for routine branch review:

```text
AlgebraReviewer:
  checks Old - New - dF, row counts, validation gates, and protected algebraic regressions.

PhysicsReviewer:
  checks basis, symmetry, index conventions, external-kernel convention maps, and claim boundary.

SoftwareReviewer:
  checks repo hygiene, stale files, pre/post-IBP table provenance, reproducibility, and report/output consistency.
```

Role-specific review JSON should be saved under `.loop/reviewer_results/` and then aggregated into `.loop/review_result.json`. The decision engine reads the aggregate result. Older `.loop/reviews/` paths may appear in legacy notes only.

## Major Checkpoint Policy

Use web GPT for major checkpoints, paper claims, final scientific audits, and next research branch planning.

## Not Codex App Review

Codex app `/review` is for code diffs and inline comments. The symbolic reviewer-agent audit is for validation gates, row provenance, convention maps, protected regressions, and scientific claim boundaries.

## Hard Boundary

- The reviewer must not edit code or symbolic outputs.
- The reviewer must not rerun the symbolic pipeline as a substitute for verifier scripts.
- The reviewer cannot override failed validation.
- A review `PASS` is only an audit verdict; freezing still requires `validation_summary.overall_gate == "PASS"`.

## Questions To Answer

- Is the algebra exact?
- Is the simplification real?
- Were old or stale tables mixed in?
- Did protected regressions survive?
- Is the claim boundary honest?
- Should this branch freeze, patch, fail, or open next stage?

## Verdicts

- `PASS`
- `PASS_WITH_CAVEAT`
- `NEEDS_PATCH`
- `FAILED`

Manual ChatGPT review and API review are optional modes, not the definition of review.
