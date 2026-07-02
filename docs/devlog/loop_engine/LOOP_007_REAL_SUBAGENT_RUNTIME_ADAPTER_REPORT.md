# Loop 007 Real Subagent Runtime Adapter Report

## Scope

This branch adds the runtime adapter layer needed before production profiles can
invoke independent reviewer agents with auditable evidence.

No `sigma_abc` physics was changed.  Stage 011 was not started.  No frozen
checkpoint was modified.

## Adapters Implemented

- `CommandAgentAdapter`: runs an explicitly configured command and records full
  invocation evidence.
- `CodexSubagentAdapter`: command-backed adapter name reserved for a configured
  Codex subagent command.
- `DryRunStubAdapter`: allowed only for dry-run and test profiles; it is not
  valid freeze evidence.
- `ManualAdapter`: present as an explicit unsupported production mode; autonomous
  production profiles cannot use it.

## Production Runtime Detection

Runtime availability is resolved from:

```text
agents/runtime.local.yaml
```

If this local file is absent, production profiles that require real agent
invocation stop with:

```text
StopReason -> AGENT_RUNTIME_UNAVAILABLE
ProductionRunStarted -> False
IBPApprovalRequired -> False
AgentRuntimeRequired -> True
```

The runner now writes:

```text
SIGMA_ABC_PRODUCTION_BLOCKED_AGENT_RUNTIME.md
SIGMA_ABC_AGENT_RUNTIME_REQUIRED.md
```

It does not write a new `SIGMA_ABC_HUMAN_APPROVAL_REQUIRED_FOR_IBP.md` for this
runtime blocker.

## Invocation Evidence

Every real command invocation writes:

```text
.loop/agent_invocations/<agent_name>/
  prompt.md
  input_manifest.json
  command.txt
  stdout.txt
  stderr.txt
  exit_code.txt
  output_hash.txt
  invocation_summary.json
```

`invocation_summary.json` records:

```json
{
  "actually_invoked": true,
  "stub_used": false,
  "schema_valid": true,
  "read_only_contract_enforced": true
}
```

Production freeze evidence is valid only when the command exits successfully,
the output validates against the expected schema, no stub is used, and the
read-only contract passes.

## Stub Fallback

Production profiles must not silently fall back to stubs.  Test profiles can use
stub mode only when their profile explicitly allows it.

## Read-Only Contract

Before invoking reviewer agents, protected files are hashed.  After invocation,
the hashes are checked again.  If a protected file changes, the invocation is
marked:

```text
ReviewerModifiedProtectedFiles -> True
Decision -> HARD_STOP
```

## Runtime Configuration

Use:

```text
agents/runtime.local.example.yaml
```

as the template for:

```text
agents/runtime.local.yaml
```

The exact Codex command is intentionally not guessed by this repo.  A local
command must be configured by the user.

## Sigma ABC Production Status

`sigma_abc_hypothesis_pre_ibp` still cannot run production stages in this
environment until a real local agent runtime command is configured.

Current stop reason:

```text
AGENT_RUNTIME_UNAVAILABLE
```

This is not an IBP-approval blocker.

## Claim Boundary

- No tensorial IBP was started.
- No total-derivative reduction was started.
- No `sigma_abc` physics simplification was started by this branch.
- The permanent caveat remains:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```
