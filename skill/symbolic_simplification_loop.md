# Symbolic Simplification Loop

Use this workflow for staged symbolic simplification in theoretical physics.

## Lifecycle

Every stage follows:

```text
PLAN -> EXECUTE -> VERIFY -> PACKET -> REVIEW -> DECIDE
```

Only frozen checkpoints may be used as authoritative inputs for later stages.

## Invariants

- A simplification claim requires exact reconstruction evidence.
- An IBP claim requires an exported primitive `F`.
- A projection benchmark claim requires symbolic or numerical regression.
- Claims must be narrower than validations.

## Roles

- Planner: writes staged plans from the human task brief.
- Executor: runs scripts and exports tables, reports, metrics, and validation summaries.
- Verifier: checks exactness and protected regressions.
- Reviewer: critiques review packets and returns structured JSON.
- Integrator: freezes checkpoints and opens next stages.

## Reference Benchmark

The reference case is projected one-dimensional `sigma^xxx`:

```text
118 raw rows -> 208 coefficient rows -> 7 kernels -> 4 kernels + dF_pair_total
```

Any future tensorial `sigma_abc` derivation must pass projection to this checkpoint.

## Reviewer Mode

Do not interpret "GPT review" as necessarily manual ChatGPT review. The review phase is a generic structured reviewer pass.

V1 default conceptual mode:

```text
mode = "codex_subagent"
```

Other allowed future modes:

```text
mode = "manual_chatgpt"
mode = "openai_api"
```

The reviewer must not edit files. It audits the packet and returns `review_result.json`. The verifier remains responsible for mathematical proof gates.

Routine branches should use read-only Codex subagents:

```text
AlgebraReviewer
PhysicsReviewer
SoftwareReviewer
```

Major checkpoints and paper-level scientific claims should additionally go to web GPT for high-level scientific audit and next-branch planning.
