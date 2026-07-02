# Structured Reviewer Packet

## Stage Name

`<stage_name>`

## Scientific Goal

`<goal>`

## What Changed

`<summary>`

## Key Files

- `<file>`

## Metrics Before / After

```json
{}
```

## Validation Summary

```json
{}
```

## Protected Regressions

- `<regression>`

## Allowed Claims

- `<claim>`

## Forbidden Claims

- `<claim>`

## Reviewer Mode

Default V1 mode:

```text
codex_subagent
```

Manual ChatGPT and OpenAI API review are optional future modes.

## Reviewer Hard Boundary

- Do not edit code or symbolic outputs.
- Do not replace verifier scripts.
- Audit exactness gates, stale inputs, protected regressions, claim boundary, and next action.
- If validation failed, recommend against freezing even if the narrative looks plausible.

## Questions For Reviewer

1. Is the algebra exact?
2. Is the simplification real?
3. Were old or stale tables mixed in?
4. Did protected regressions survive?
5. Is the claim boundary honest?
6. Should this branch freeze, patch, fail, or open next stage?
