from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import Iterable


DEFAULT_FILE_TOOLS = ("Read", "Edit", "MultiEdit", "Write")
DEFAULT_SAFE_BASH_PREFIXES = {
    "python3 -m pytest",
    "python3 -m compileall",
    "rg",
    "sed",
    "test",
    "mkdir",
}


@dataclass(frozen=True)
class PermissionPolicy:
    declared_commands: list[str]
    allowed_tools: list[str]
    claude_allowed_tools_arg: str


def _iter_fenced_blocks(markdown: str) -> Iterable[tuple[str, str]]:
    pattern = re.compile(r"```(?P<lang>[A-Za-z0-9_-]*)\n(?P<body>.*?)```", re.DOTALL)
    for match in pattern.finditer(markdown):
        yield match.group("lang").strip().lower(), match.group("body")


def extract_declared_commands(plan_text: str) -> list[str]:
    """Extract executable commands from plan ``Run:`` fenced bash blocks.

    The parser is intentionally conservative. It only considers fenced
    blocks whose language is ``bash`` or ``sh`` and whose nearby heading says
    ``Run``. Blocks under ``Do not run`` or plain ``text`` examples are ignored.
    """

    commands: list[str] = []
    for match in re.finditer(r"```(?P<lang>[A-Za-z0-9_-]*)\n(?P<body>.*?)```", plan_text, re.DOTALL):
        lang = match.group("lang").strip().lower()
        if lang not in {"bash", "sh", "shell"}:
            continue
        prefix = plan_text[max(0, match.start() - 160) : match.start()].lower()
        if "do not run" in prefix[-80:]:
            continue
        if "run" not in prefix:
            continue
        for raw_line in match.group("body").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            commands.append(line)
    return commands


def _command_prefix(command: str) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    if not parts:
        return None
    if parts[:3] == ["python3", "-m", "pytest"]:
        return "python3 -m pytest"
    if parts[:3] == ["python3", "-m", "compileall"]:
        return "python3 -m compileall"
    if len(parts) >= 2 and parts[0] == "python3" and parts[1].startswith("scripts/") and parts[1].endswith(".py"):
        return f"python3 {parts[1]}"
    if parts[0] in DEFAULT_SAFE_BASH_PREFIXES:
        return parts[0]
    return None


def command_to_allowed_tool(command: str) -> str | None:
    prefix = _command_prefix(command)
    if not prefix:
        return None
    return f"Bash({prefix}:*)"


def build_allowed_tools(
    plan_text: str,
    *,
    file_tools: Iterable[str] = DEFAULT_FILE_TOOLS,
    extra_bash_prefixes: Iterable[str] = (),
) -> list[str]:
    tools: list[str] = []
    seen: set[str] = set()
    for tool in file_tools:
        if tool not in seen:
            tools.append(tool)
            seen.add(tool)
    for command in extract_declared_commands(plan_text):
        tool = command_to_allowed_tool(command)
        if tool and tool not in seen:
            tools.append(tool)
            seen.add(tool)
    for prefix in extra_bash_prefixes:
        tool = f"Bash({prefix}:*)"
        if tool not in seen:
            tools.append(tool)
            seen.add(tool)
    return tools


def build_permission_policy(plan_text: str) -> PermissionPolicy:
    tools = build_allowed_tools(plan_text)
    return PermissionPolicy(
        declared_commands=extract_declared_commands(plan_text),
        allowed_tools=tools,
        claude_allowed_tools_arg=",".join(tools),
    )


def classify_executor_runtime_text(text: str) -> dict[str, object]:
    lowered = text.lower()
    if "not in allowed tools" in lowered or "tool use denied" in lowered or "permission denied" in lowered:
        return {
            "kind": "EXECUTOR_UNAUTHORIZED_COMMAND",
            "patch_required": True,
            "freeze_allowed": False,
            "issue": "EXECUTOR_UNAUTHORIZED_COMMAND: command was not present in generated allowedTools; split the plan or declare the command explicitly.",
        }
    if "timed out" in lowered or "timeout" in lowered:
        return {
            "kind": "EXECUTOR_TIMEOUT",
            "patch_required": False,
            "freeze_allowed": False,
            "issue": "EXECUTOR_TIMEOUT: executor exceeded the configured timeout; rerun with a smaller plan or longer explicit budget.",
        }
    return {
        "kind": "EXECUTOR_UNKNOWN",
        "patch_required": False,
        "freeze_allowed": False,
        "issue": "EXECUTOR_UNKNOWN: no known executor runtime marker was found.",
    }
