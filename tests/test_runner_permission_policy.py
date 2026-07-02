from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from loop_engine.executor_permission_policy import (
    build_allowed_tools,
    classify_executor_runtime_text,
    extract_declared_commands,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_extract_declared_commands_from_plan_run_blocks() -> None:
    plan = """
# Plan

Run:

```bash
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
rg "PASS" docs/devlog
```

Do not run:

```text
python3 scripts/run_autonomous_loop.py --project sigma_abc
```
"""

    assert extract_declared_commands(plan) == [
        "python3 -m pytest -q",
        "python3 -m compileall loop_engine scripts tests",
        'rg "PASS" docs/devlog',
    ]


def test_build_allowed_tools_is_derived_from_declared_commands_only() -> None:
    plan = """
Run:

```bash
python3 scripts/smoke_runner_output_isolation.py
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
sed -n '1,40p' README.md
```
"""

    tools = build_allowed_tools(plan)

    assert "Read" in tools
    assert "Edit" in tools
    assert "MultiEdit" in tools
    assert "Write" in tools
    assert "Bash(python3 scripts/smoke_runner_output_isolation.py:*)" in tools
    assert "Bash(python3 -m pytest:*)" in tools
    assert "Bash(python3 -m compileall:*)" in tools
    assert "Bash(sed:*)" in tools
    assert "Bash(find:*)" not in tools
    assert "Bash(cat:*)" not in tools


def test_executor_runtime_classifies_unauthorized_tool_request() -> None:
    text = "Tool use denied: Bash(ls:*) is not in allowed tools."

    result = classify_executor_runtime_text(text)

    assert result["kind"] == "EXECUTOR_UNAUTHORIZED_COMMAND"
    assert result["patch_required"] is True
    assert "allowedTools" in result["issue"]


def test_build_claude_allowed_tools_script_outputs_json(tmp_path: Path) -> None:
    plan = tmp_path / "PLAN.md"
    plan.write_text(
        """
Run:

```bash
python3 -m pytest -q
python3 -m compileall loop_engine scripts tests
```
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "build_claude_allowed_tools.py"),
            "--plan",
            str(plan),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["overall_gate"] == "PASS"
    assert "Bash(python3 -m pytest:*)" in payload["allowed_tools"]
    assert "Bash(python3 -m compileall:*)" in payload["allowed_tools"]
    assert payload["claude_allowed_tools_arg"]


def test_build_claude_allowed_tools_require_bash_fails_without_run_commands(tmp_path: Path) -> None:
    plan = tmp_path / "PLAN.md"
    plan.write_text("# Plan\n\nNo execution commands are declared here.\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "build_claude_allowed_tools.py"),
            "--plan",
            str(plan),
            "--require-bash",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["overall_gate"] == "FAIL"
    assert "no Bash tools" in payload["issues"][0]
