# Loop 006 Hypothesis Driven Symbolic Search Report

## Branch

`loop_006_hypothesis_driven_symbolic_search`

## Scope

This branch extends loop infrastructure with conjecture/candidate search. It
does not modify frozen `sigma_abc` outputs, does not start a new production
`sigma_abc` stage, and does not promote speculative formulas without verifier
approval.

## New Agent Roles

- `StructureHypothesisAgent`
- `CandidateBuilderAgent`
- `CandidateRankerAgent`
- `FailureArchivistAgent`

Their role files live under `skill/`, and structured agent configs live under
`agents/`.

## New Ledger And Schemas

Implemented:

```text
loop_engine/conjecture_ledger.py
schemas/conjecture.schema.json
schemas/candidate_result.schema.json
schemas/candidate_ranking.schema.json
schemas/failure_archive.schema.json
```

Conjectures are always recorded, including failed ones. Candidate outputs stay
isolated under:

```text
candidates/<conjecture_id>/
failed_conjectures/<conjecture_id>/
.loop/conjectures/
```

## Promotion Rule

Only verified candidates may be promoted:

```text
candidate validation PASS
protected benchmarks PASS
promotion_allowed -> True
```

Unverified candidates are rejected. Normal failed conjectures are archived and
do not hard-stop the stage.

## IBP Boundary

If a candidate needs total derivatives or IBP while the profile does not allow
IBP speculation, the candidate is marked:

```text
REQUIRES_IBP_APPROVAL
```

It is not marked `PASS`, and it is not promoted.

## Mock Search Profile

Added:

```text
profiles/test_hypothesis_search_loop.yaml
```

The mock search proposes two toy conjectures:

```text
conjecture_001 -> validation FAIL -> archived
conjecture_002 -> validation PASS -> promoted
```

This exercises the hypothesis pipeline without touching `sigma_abc` physics.

## Human-Readable Search Summary

Hypothesis-enabled stages write:

```text
reports/stage_<stage_id>_hypothesis_search_summary.md
reports/stage_<stage_id>_hypothesis_search_summary.tex
reports/stage_<stage_id>_hypothesis_search_summary.pdf
```

The summary records conjectures proposed, candidates built, pass/fail/archive
counts, best candidate, and claim boundary.

## Stage 010 Retrospective Conjecture

Created:

```text
reports/stage_010_pair_band_pair_family_grouping_conjecture.json
```

It records the historical conjecture:

```text
The 912 pair-sector rows can be grouped into 3 band-pair families.
PairFusionDifference -> 0.
XXXPairProjectionRegression -> PASS.
Status -> PROMOTED.
```

This is retrospective metadata only and does not rewrite Stage 010 outputs.

## Commands To Verify

```bash
python3 -m pytest tests/test_hypothesis_search.py -q
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
python3 scripts/run_autonomous_loop.py --project mock --profile test_hypothesis_search_loop --clean
```

## Claim Boundary

Allowed:

- Claim the loop can record conjectures and isolated candidates.
- Claim failed conjectures are archived rather than hidden.
- Claim verified toy candidates can be promoted in the mock profile.

Forbidden:

- Do not claim any new `sigma_abc` physics simplification.
- Do not claim speculative hypotheses are scientific results.
- Do not claim IBP candidates pass without IBP approval.
- Do not modify frozen scientific outputs.

## Persistent Caveat

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
