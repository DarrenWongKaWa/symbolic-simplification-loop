# Profile Runner Dry Run

ProfileStatus -> COMPLETE
CurrentCheckpoint -> sigma_abc_012b_loop_hypothesis_generation
NextStage -> sigma_abc_012c_loop_orbit_canonicalization_promotion
HypothesisSearchEnabled -> True
AutoPatchEnabled -> True
ConjectureLedgerEnabled -> True
FailedConjecturesArchived -> True
NamedStageDigestsEnabled -> True
ScientificMetaReviewerEnabled -> True
StopBeforeIBP -> True
RealAgentInvocationRequired -> True
AgentInvocationEvidenceRequired -> True
ProductionStubForbidden -> True
AgentRuntimeStatus -> AVAILABLE
Adapter -> command
ProductionRunAllowed -> True
MissingAgentCommands -> []
ReviewLane -> L2_FULL_PANEL
FullPanelRequired -> True
OpenReviewDebt -> False
CandidatePromotionAllowed -> True
IBPAllowed -> False
TotalDerivativePromotionAllowed -> False
StopBeforeGlobalAssembly -> True
ExpectedProfile -> sigma_abc_loop_candidate_promotion
ActualProfile -> sigma_abc_loop_candidate_promotion
ExpectedStage -> sigma_abc_012c_loop_orbit_canonicalization_promotion
ActualStage -> sigma_abc_012c_loop_orbit_canonicalization_promotion
ReportIdentityCheck -> PASS

Current checkpoint: sigma_abc_012b_loop_hypothesis_generation
Next allowed stage: sigma_abc_012c_loop_orbit_canonicalization_promotion
Allowed stage list:
- sigma_abc_012c_loop_orbit_canonicalization_promotion
Stop-after stage: sigma_abc_012c_loop_orbit_canonicalization_promotion
Protected benchmarks:
- sigma_xxx_projection
Permanent caveats:
- DCProjectionTo1D is INHERITED_PASS, not direct full tensorial DC-series PASS.
- Stage001DCCaveatPreserved
- DCProjectionTo1D -> INHERITED_PASS
Forbidden actions:
- full tensorial sigma_abc correctness
- direct full tensorial DC-series PASS
- full equality to projected sigma_xxx final formula before projection validation
Hard-stop conditions:
- forbidden tag: kernel_fusion
- forbidden tag: ibp_reduction
- forbidden tag: tensorial_simplification
- stop file: STOP
- stop file: .loop/protected_regression_failed
- stop file: .loop/human_approval_required
Reviewer mode: codex_subagent
Patch limits:
- max_patch_attempts_per_stage: None
