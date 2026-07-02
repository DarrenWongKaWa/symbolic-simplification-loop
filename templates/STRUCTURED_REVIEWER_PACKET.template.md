# Structured Reviewer Packet

This is the generic name for `GPT_REVIEW_PACKET.template.md`. The reviewer can be a Codex subagent, manual ChatGPT reviewer, or future OpenAI API reviewer.

Default V1 mode:

```text
codex_subagent
```

The reviewer audits; the verifier proves.

Routine branch review uses Codex subagents. Major checkpoint and paper-claim review should also receive web-GPT scientific audit.

Do not confuse this symbolic reviewer-agent audit with Codex app `/review`, which is for code diffs and inline comments.
