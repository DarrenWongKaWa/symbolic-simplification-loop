# Integrator Role

The integrator decides whether to freeze, patch, fail, or open the next stage.

## Freeze Conditions

A stage cannot be frozen unless:

- `validation_summary.overall_gate == "PASS"`
- `review_result.verdict` is `PASS` or `PASS_WITH_CAVEAT`
- `CLAIM_BOUNDARY.md` exists
- `checkpoint_manifest.json` exists or can be generated

## Rules

- If validation failed, do not freeze regardless of review.
- If review says `PASS`, freeze checkpoint.
- If review says `PASS_WITH_CAVEAT`, freeze with caveat.
- If review says `NEEDS_PATCH`, generate `PATCH_PROMPT.md`.
- If review says `FAILED`, archive failed stage.
- If review suggests `OPEN_NEXT_STAGE`, freeze current checkpoint first.

## Hard Stops

- `max_patch_attempts`
- repeated same error
- protected regression failed
- human approval required
- `STOP` file exists

