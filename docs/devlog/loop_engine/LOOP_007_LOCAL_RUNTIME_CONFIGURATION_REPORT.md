# Loop 007 Local Runtime Configuration Report

## Scope

This report covers local real-agent runtime configuration for production
`sigma_abc` profiles.  No `sigma_abc` physics simplification was intentionally
started, no tensorial IBP was started, and frozen physics checkpoints were not
modified as part of the runtime configuration work.

## Local Command Used

Native Codex subagent invocation through a dedicated `codex exec --agent`
interface is not available in the installed CLI.  The available command is
non-interactive `codex exec`.

The configured local runtime therefore uses a command adapter that launches an
independent Codex process per reviewer through:

```text
bash scripts/local_codex_agent_runner.sh {agent_name} {prompt_path} {output_path} {stage_dir}
```

The wrapper invokes:

```text
codex exec --skip-git-repo-check --sandbox read-only \
  --output-schema schemas/review_result.codex.schema.json \
  --output-last-message {output_path} \
  -C {stage_dir} -
```

The canonical loop adapter still records invocation evidence under:

```text
.loop/agent_invocations/<agent_name>/
```

## Native Codex Subagent Availability

```text
codex --help -> available
codex exec --help -> available
which codex -> /Applications/Codex.app/Contents/Resources/codex
native codex exec --agent -> not available in this CLI help surface
```

## Wrapper Used

```text
WrapperUsed -> True
WrapperPath -> scripts/local_codex_agent_runner.sh
Adapter -> command
DryRunStubAdapterUsedForSigmaABCProduction -> False
```

## runtime.local.yaml Summary

Configured profiles:

```text
sigma_abc_hypothesis_pre_ibp -> command adapter
test_hypothesis_search_loop_real_agent -> command adapter
```

No secrets are stored in `agents/runtime.local.yaml`; it contains local command
paths only.

## Runtime Check

Command:

```bash
python3 scripts/check_agent_runtime.py --profile sigma_abc_hypothesis_pre_ibp
```

Observed result:

```text
AgentRuntimeStatus -> AVAILABLE
Adapter -> command
ProductionRunAllowed -> True
StubUsed -> False
MissingAgentCommands -> []
```

## Sigma ABC Dry Run

Command:

```bash
python3 scripts/run_autonomous_loop.py \
  --project sigma_abc \
  --profile sigma_abc_hypothesis_pre_ibp \
  --dry-run \
  --from-current-checkpoint
```

Observed required fields:

```text
ProfileStatus -> COMPLETE
CurrentCheckpoint -> sigma_abc_010_pair_kernel_fusion_pilot
NextStage -> sigma_abc_011_center_sector_pilot
HypothesisSearchEnabled -> True
RealAgentInvocationRequired -> True
AgentRuntimeStatus -> AVAILABLE
ProductionRunAllowed -> True
StopBeforeIBP -> True
```

Permanent caveat preserved:

```text
DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.
```

## Mock Real-Agent Test Result

An isolated real-agent invocation was successfully exercised during this
configuration pass before the later clean mock run removed that smoke-test
directory.  In that successful invocation:

```text
actually_invoked -> True
stub_used -> False
exit_code -> 0
schema_valid -> True
read_only_contract_enforced -> True
freeze_evidence_valid -> True
```

The final full mock real-agent loop was rerun after the test suite, but the
live Codex account hit a usage limit during reviewer invocations.  The command
adapter still produced real invocation evidence and did not fall back to a
stub:

```text
actually_invoked -> True
stub_used -> False
exit_code -> 1
schema_valid -> False
freeze_evidence_valid -> False
```

The blocking stderr was:

```text
You've hit your usage limit. Upgrade to Pro, visit Codex settings/usage to
purchase more credits or try again at Jun 30th, 2026 1:01 AM.
```

Therefore the final mock real-agent loop did not freeze:

```text
stages_attempted -> 1
stages_frozen -> 0
decision -> RETRY_AFTER_RUNTIME_LIMIT
freeze_allowed -> False
patch_required -> False
retry_after -> Jun 30th, 2026 1:01 AM
blocker -> Codex usage limit, not wrapper/schema/stub fallback
```

The decision layer now treats quota exhaustion as a retryable external runtime
limit rather than a patchable code failure.  Ordinary invalid invocation
evidence still routes to `PATCH`; usage/quota-limit evidence routes to
`RETRY_AFTER_RUNTIME_LIMIT`.

## Verification Commands

```bash
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
python3 scripts/check_agent_runtime.py --profile sigma_abc_hypothesis_pre_ibp
python3 scripts/run_autonomous_loop.py --project mock --profile test_hypothesis_search_loop_real_agent --clean
python3 scripts/run_autonomous_loop.py --project sigma_abc --profile sigma_abc_hypothesis_pre_ibp --dry-run --from-current-checkpoint
```

Fresh verification snapshot after the final edits:

```text
pytest -> 77 passed, 1 warning
compileall -> PASS
check_agent_runtime sigma_abc_hypothesis_pre_ibp -> AVAILABLE, Adapter command, StubUsed False
sigma_abc dry-run -> PASS, NextStage sigma_abc_011_center_sector_pilot, ProductionRunAllowed True
Stage011ArtifactPresent -> False
```

## Current Production Status

```text
LocalRuntimeConfigured -> True
CommandRuntimeAvailable -> True
StubUsed -> False
SigmaABCDryRunPASS -> True
Stage011StartedByFinalDryRun -> False
MockRealAgentLoopPASS -> False
ProductionCanStartNow -> False
Blocker -> Codex usage limit during real reviewer invocation
RetryDecision -> RETRY_AFTER_RUNTIME_LIMIT
PatchRequiredForQuota -> False
```

## Recommended Next Step

After the Codex usage limit resets, rerun:

```bash
python3 scripts/run_autonomous_loop.py \
  --project mock \
  --profile test_hypothesis_search_loop_real_agent \
  --clean
```

If that freezes with real invocation evidence, then production may be started
manually with the already-configured `sigma_abc_hypothesis_pre_ibp` profile.

Do not start `sigma_abc` production automatically from this report.
