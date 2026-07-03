# External tools and how they relate

This document explains how three projects relate to each other. It is
the source of truth for "what is `loop-engineering`" and "what is
Langflow" within the construction loop.

## The three projects

### 1. `symbolic-simplification-loop` (this repo)

* The main repo being developed.
* Holds the **scientific runtime** for symbolic simplification: stage
  planning, validation summaries, reviewer outputs, completion
  matrices, human signoff, checkpoint boundaries, agent bus, job
  envelopes, ready markers, failed artifacts, and schema-validated
  state.
* The **scientific runtime is the source of truth** for running
  symbolic simplification. The construction loop must not bypass or
  shadow it.

### 2. `cobusgreyling/loop-engineering` (external)

* External construction-loop reference.
* Used for **methodology**: skills, sub-agents, maker/checker split,
  state, budget, audit, run logs, and human gates.
* **Not vendored, copied, or submoduled** into this repo.
* **Not a replacement for the scientific runtime.** It does not know
  about checkpoints, signoff, or the verifier.

> The construction loop documented under `docs/dev/construction_loop/`
> borrows concepts and wording from `loop-engineering`. It does not
> import its code.

### 3. `langflow-ai/langflow` (future candidate)

* A possible future UI / cockpit layer for visualizing state,
  artifacts, prompts, reviews, and human gates.
* **Should not replace** the verifier, the reviewer, or the
  signoff logic. A visualization layer that can bypass gates is a
  safety regression, not an improvement.

## What this means in practice

* `loop-engineering` is the construction methodology.
* `langflow` is a future UI/cockpit candidate.
* This repo's scientific runtime is authoritative.

The four development roles (`CodexPlanner`, `ClaudeCodeExecutor`,
`CodexReviewer`, `HumanIntegrator`) are a local adaptation of the
loop-engineering idea. They are not a literal port.

## Forbidden relationships

To keep these layers clean, the construction loop must not:

* Vendor, copy, or submodule `loop-engineering` into this repo.
* Run `npx @cobusgreyling/loop-init .` (or any similar initializer)
  inside this repo's root.
* Treat Langflow (or any other UI layer) as a replacement for the
  scientific verifier, reviewer, or signoff logic.
* Re-route scientific outputs through a construction-loop task.
