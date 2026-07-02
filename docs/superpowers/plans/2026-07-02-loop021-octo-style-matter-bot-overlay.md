# PLAN.md — Loop 021 Octo-Style Matter/Bot Metadata Overlay

## Branch

```text
loop_021_octo_style_matter_bot_overlay
```

## Purpose

Add a lightweight Octo-style organizational layer around the existing
`symbolic-simplification-loop` trust engine.

This is not a runner rewrite. The existing loop remains the authority for:

```text
PLAN -> EXECUTE -> VERIFY -> REVIEW -> DECIDE -> CHECKPOINT
```

The Octo-style overlay only organizes:

```text
Space / Channel / Matter / Thread / Bot / Context / Taste / Skill
```

## External Reference

Mininglamp-OSS OCTO is an open workplace architecture for humans and AI agents.
Useful reference repositories:

```text
https://github.com/Mininglamp-OSS/octo-server
https://github.com/Mininglamp-OSS/octo-matter
https://github.com/Mininglamp-OSS/octo-web
https://github.com/Mininglamp-OSS/octo-adapters
```

Concept mapping used here:

```text
OCTO server/orchestration  -> repo-local loop orchestration context
OCTO matter/task service   -> repo-local Matter YAML files
OCTO channels/threads      -> scientific work channels and run/review threads
OCTO agents/Lobsters       -> fixed reviewer/executor/hypothesis bot identities
```

## Hard Boundaries

Do not modify `sigma_abc` physics.
Do not start 012C promotion.
Do not start Stage 013.
Do not start tensorial IBP.
Do not introduce total-derivative reduction.
Do not claim full tensorial `sigma_{\mu\alpha\beta}` correctness.
Do not give the Octo overlay freeze authority.
Do not replace existing validation, review, decision, signoff, or checkpoint logic.

## Architecture Principle

```text
Matter says: this is the task.
Channel says: this is the collaboration lane.
Profile says: this is allowed.
Verifier says: math passes.
Reviewer says: claim boundary is safe.
Human says: caveats are accepted.
freeze_preconditions says: checkpoint may freeze.
```

The Octo overlay must not bypass `freeze_preconditions`.

## Minimal Repo Overlay

Create:

```text
.octo/
  space.yaml
  bots/
    main_executor.yaml
    algebra_reviewer.yaml
    physics_reviewer.yaml
    software_reviewer.yaml
    scientific_meta_reviewer.yaml
    hypothesis_agent.yaml
    failure_archivist.yaml
    human_scientist.yaml
  channels/
    sigma_abc_pre_ibp.yaml
    sigma_abc_promotion.yaml
    sigma_abc_global_assembly.yaml
    sigma_abc_ibp.yaml
    sigma_abc_paper.yaml
  matters/
    M001_materialize_012a_012b.yaml
    M002_012c_loop_candidate_promotion.yaml
    M003_global_pre_ibp_assembly.yaml
    M004_tensorial_ibp_conjecture.yaml
    M005_compact_closed_form.yaml
    M006_paper_supplement.yaml
  threads/
    README.md
  context/
    permanent_caveats.yaml
    protected_benchmarks.yaml
    checkpoint_index.yaml
    report_index.yaml
  taste/
    wangjiahua_research_taste.yaml
  skills/
    symbolic_reconstruction_identity.yaml
    xxx_projection_regression.yaml
    completion_matrix_protocol.yaml
    ibp_conjecture_search.yaml
```

## Matter Definitions

### M001 materialize 012A/012B

```text
status: active
mode: pipeline
profile: sigma_abc_hypothesis_pre_ibp_throughput
success:
  - deepest_physical_checkpoint == sigma_abc_012b_loop_hypothesis_generation
  - 012A artifacts physically exist
  - 012B artifacts physically exist
forbidden:
  - 012C promotion
  - Stage013
  - IBP
  - total_derivative
```

### M002 012C loop candidate promotion

```text
status: locked_until_M001_complete
mode: critic + roundtable
profile: sigma_abc_loop_candidate_promotion
review_lane: L2_FULL_PANEL
success:
  - 012C frozen
  - Stage013 not started
forbidden:
  - Stage013
  - IBP
```

### M003 global pre-IBP assembly

```text
status: locked_until_M002_complete
mode: split + critic
profile: sigma_abc_global_assembly_pre_ibp
review_lane: L2_FULL_PANEL
forbidden:
  - IBP
  - total_derivative
```

### M004 tensorial IBP conjecture

```text
status: locked_until_M003_complete
mode: swarm
requires_human_approval: approve IBP
allow:
  - propose_ibp_ansatz
  - archive_failed_conjectures
forbid:
  - promote_total_derivative_without_validation
```

## Scripts

Add only read-only/status scripts in the first pass:

```text
loop_engine/octo_registry.py
scripts/octo_status.py
```

`scripts/octo_status.py` should print:

```text
Current Matter: M001_materialize_012a_012b
Current Physical Checkpoint: sigma_abc_010_pair_kernel_fusion_pilot
Next Allowed Human Gate: approve Phase 5 rerun
Blocked Matters:
  M002_012c_loop_candidate_promotion until M001 complete
  M003_global_pre_ibp_assembly until M002 complete
  M004_tensorial_ibp_conjecture until M003 complete
```

Do not add a `--matter` runner entrypoint in this branch. That can be a later
integration after the overlay proves useful.

## Tests

Add tests for:

```text
.octo/space.yaml parses
all bot YAML files parse
all channel YAML files parse
all matter YAML files parse
M001/M002/M003/M004 lock dependencies are valid
octo_status.py prints current matter and blocked matters
Octo overlay has no freeze authority fields
permanent DC caveat is present
sigma_xxx protected benchmark is present
```

## Commands

Run:

```bash
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
python3 scripts/octo_status.py
```

## Acceptance Criteria

```text
pytest PASS
compileall PASS
octo_status.py PASS
.octo metadata exists and parses
M001/M002/M003/M004 statuses reflect current sigma_abc order
No runner logic changed beyond optional read-only octo_registry import
No sigma_abc physics modified
No 012C promotion
No Stage013
No tensorial IBP
No total derivative
No freeze authority moved into Octo overlay
```

## Final Report

Write:

```text
docs/devlog/loop_engine/LOOP_021_OCTO_STYLE_MATTER_BOT_OVERLAY_REPORT.md
```

Include:

```text
files created
Octo concepts mapped
current Matter status
blocked Matter status
tests run
boundary confirmation
recommended next command
```

## Timing Recommendation

This branch is best run after the upstream 012A/012B materialization path is
stable. It may be prepared earlier as metadata only, but it must not interrupt
the current `sigma_abc` preparation/promotion gates.
