# Compact Review Packet: {{stage_name}}

This template is rendered by `scripts/build_compact_review_packet.py`.

Required contents:

- stage id and slug
- review lane and risk classification
- stage goal
- validation gate summary
- identity type
- claimed output
- not-claimed output
- changed outputs
- claim boundary
- caveats
- protected benchmark status
- forbidden actions status
- exact reviewer questions

The compact packet intentionally excludes full notebooks, full ledgers, full
stdout, and large symbolic expressions unless the risk classifier requires a
full-panel review.

The exact reviewer questions must include:

```text
PASS as what?
NOT PASS as what?
What was actually validated?
What was only inherited/deferred?
What caveats must be preserved?
Was any overclaim detected?
Is freeze allowed?
Is human approval required before the next stage?
Which review lane was used and why?
What should the next safe stage be?
```
