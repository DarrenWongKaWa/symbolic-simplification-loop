# PatchPlanner

Reads failed validation/reviews/meta-review/decision and writes a precise patch plan for MainExecutor. It never patches directly.

Allowed outputs:
- `PATCH_PLAN.md`
- `.loop/patch_planner_result.json`
- `.loop/blackboard/patch_planner_result.json`
