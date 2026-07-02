# Repository Audit

## Scope

This audit covers the `symbolic-simplification-loop` infrastructure repo. It does not audit or run any `sigma_abc` physics simplification.

## Structure

- Python package: `loop_engine/`
- CLI scripts: `scripts/`
- JSON schemas: `schemas/`
- Markdown/JSON templates: `templates/`
- Role instructions: `skill/`
- Reference benchmark: `examples/sigma_xxx_case/`
- Future-project template: `examples/sigma_abc_template/`
- Tests: `tests/`

## Inventory

- Files discovered: 662
- Directories discovered: 189

## Lifecycle Coverage

- Stage initialization: present.
- Validation summary schema: present.
- Structured review packet generation: present.
- Read-only reviewer role prompts: present for AlgebraReviewer, PhysicsReviewer, and SoftwareReviewer.
- Decision engine: present.
- Checkpoint freezer: present.
- Sigma_xxx benchmark metadata: present.
- Sigma_abc project template: present.

## Boundary

The repo is an orchestration framework. It does not perform symbolic physics simplification by itself.
