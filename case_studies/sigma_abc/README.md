# Case Study — sigma_abc

This directory is the planned landing zone for the `sigma_abc`
case-study artifacts once they are migrated out of the repo root.

In the current reorganization pass (Loop 020 step batch / repo
hygiene), `sigma_abc/` and the `sigma_abc_*` profile / identity /
benchmark / project files remain at the repo root and inside
existing top-level directories (`profiles/`, `identities/`,
`benchmarks/`, `projects/`, `policies/`, `sigma_abc/`). The move
is **deferred** because:

1. Tests currently reference `sigma_abc/*` and `projects/sigma_abc/*`
   paths directly. A blind move in this pass would break the
   trust-stack tests (`tests/test_sigma_abc_*` and
   `tests/test_loop014_017_*`).
2. Several SIGMA_ABC human-approval text files and bench reports
   are referenced as evidence in `docs/devlog/sigma_abc/`. Their
   lineage to the live `sigma_abc/` workdir is preserved by leaving
   the originals in place.
3. The reorganization is intended to be infrastructure-only. Loop
   trust-stack behaviour and the sigma_abc scientific content are
   explicitly NOT modified.

## Current Layout (Read-only Inventory)

The sigma_abc workdir currently lives across the following top-level
locations in the repo root. They are NOT migrated in this pass.

```text
projects/sigma_abc/loop.yaml
profiles/sigma_abc_*.yaml
identities/sigma_abc.default_identities.yaml
benchmarks/sigma_xxx_projection.yaml (if present; check root)
policies/sigma_abc_* (if present; check root)
sigma_abc/                  (full workdir; research-only)
```

## Future Migration Path (Not Executed In This Pass)

When a future reorganization pass is approved, the following mapping
applies:

```text
projects/sigma_abc/                       -> case_studies/sigma_abc/project/
profiles/sigma_abc_*.yaml                 -> case_studies/sigma_abc/profiles/
identities/sigma_abc.default_identities.yaml
                                            -> case_studies/sigma_abc/identities/
benchmarks/sigma_xxx_projection.yaml      -> case_studies/sigma_abc/benchmarks/
policies/sigma_abc_*                      -> case_studies/sigma_abc/policies/
sigma_abc/                                -> case_studies/sigma_abc/
SIGMA_ABC_*_REPORT.md                     -> case_studies/sigma_abc/reports_curated/
sigma_abc/conventions/                    -> case_studies/sigma_abc/conventions/
```

A migration pass that performs this mapping must:

1. Update `tests/test_sigma_abc_*` to reference the new paths.
2. Update `loop_engine/config.py` paths lookup.
3. Verify all 177 tests still pass.
4. Verify `compileall` is clean.
5. Verify the trust-stack invariants (boundary audit, identity
   traceability, completion matrix) still pass for the sigma_abc
   case study under the new location.

Until that pass runs, the case study's primary material remains
at the repo root and is referenced from this document.

## Boundary

- This case study is **research workdir**, not production code.
- No 012C promotion has run. No Stage 013 has run.
- No tensorial IBP, no total derivative, no claim of full tensorial
  sigma_abc correctness.
- Permanent caveat:
  `DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial
  DC-series PASS.`
