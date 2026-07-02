#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from loop_engine.config import write_json, write_text
from loop_engine.decision import decide_next_action
from loop_engine.reviewer import load_review_result
from loop_engine.safety import hard_stop_reasons
from loop_engine.verifier import load_validation_summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    stage = Path(args.stage)
    decision = decide_next_action(load_validation_summary(stage), load_review_result(stage), hard_stop_reasons(stage))
    payload = {
        "action": decision.action,
        "reason": decision.reason,
        "freeze_allowed": decision.freeze_allowed,
        "caveats": decision.caveats,
        "suggested_next_stage": decision.suggested_next_stage,
        "patch_required": decision.patch_required,
        "retry_after": decision.retry_after,
    }
    write_json(stage / ".loop" / "decision.json", payload)
    if decision.action == "PATCH":
        review = load_review_result(stage)
        issues = "\n".join(f"- {item}" for item in review.get("blocking_issues", [])) or "- see review_result.json"
        instructions = "\n".join(f"- {item}" for item in review.get("patch_instructions", [])) or "- patch according to review"
        write_text(stage / "PATCH_PROMPT.md", f"# Patch Prompt\n\n## Blocking Issues\n\n{issues}\n\n## Patch Instructions\n\n{instructions}\n")
    print(payload)


if __name__ == "__main__":
    main()
