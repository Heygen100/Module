# scop: inline
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Any


class DoxteamPlugin:
    name = "doxteam"
    version = "0.2.0"
    author = "@dev_dolbaeb"
    description = "DoxTeam kernel command tools"

    tool_registry = (
        "doxteam.command",
        "doxteam.config",
        "doxteam.modules",
        "doxteam.install",
        "doxteam.reload",
    )

    dangerous_tools = {"doxteam.command", "doxteam.install", "doxteam.reload"}

    tool_docs = {
        "doxteam.command": {
            "desc": "Execute any DoxTeam userbot command",
            "args": "command (str) or cmd (str) — command text (prefix auto-added)",
            "body": "command text",
            "returns": "Confirmation text with the performed action details, or an error message.",
            "example": "{\"tool\": \"doxteam.command\", \"args\": {\"command\": \"ping\"}}",
            "notes": "Userbot command prefix is added automatically when needed.",
        },
        "doxteam.config": {
            "desc": "Get or set DoxTeam module configuration",
            "args": "command (str) or query (str) — config command like 'module.key=value'",
            "body": "config command",
            "returns": "Text result with the requested data, or an error message.",
            "example": "{\"tool\": \"doxteam.config\", \"args\": {\"query\": \"OpenAgent.system_prompt\"}}",
            "notes": "Userbot command prefix is added automatically when needed.",
        },
        "doxteam.modules": {
            "desc": "List loaded DoxTeam modules",
            "args": "command (str) or query (str)",
            "body": "not used",
            "returns": "Text result with the requested data, or an error message.",
            "example": "{\"tool\": \"doxteam.modules\", \"args\": {}}",
            "notes": "Userbot command prefix is added automatically when needed.",
        },
        "doxteam.install": {
            "desc": "Install a module from a repo URL",
            "args": "command (str) or query (str) — module URL or name",
            "body": "URL or name",
            "returns": "Confirmation text with the performed action details, or an error message.",
            "example": "{\"tool\": \"doxteam.install\", \"args\": {\"query\": \"https://example.com/module.py\"}}",
            "notes": "Userbot command prefix is added automatically when needed.",
        },
        "doxteam.reload": {
            "desc": "Reload all modules (equivalent to .restart)",
            "args": "none",
            "body": "not used",
            "returns": "Confirmation text with the performed action details, or an error message.",
            "example": "{\"tool\": \"doxteam.reload\", \"args\": {}}",
            "notes": "Userbot command prefix is added automatically when needed.",
        },
    }

    tool_map = {
        "doxteam": "cmd_doxteam",
        "doxteam.command": "cmd_doxteam",
        "doxteam.config": "cmd_doxteam",
        "doxteam.modules": "cmd_doxteam",
        "doxteam.install": "cmd_doxteam",
        "doxteam.reload": "cmd_doxteam",
    }

    def __init__(self, agent: Any) -> None:
        self.agent = agent
    
    async def cmd_doxteam(self, tool_name: str, attrs_raw: str, body: str, source_event: Any) -> str:
        command_map = {
            "doxteam.modules": "modules",
            "doxteam.config": "cfg",
            "doxteam.install": "dlm",
            "doxteam.reload": "restart",
        }
        attrs = self.agent._parse_xml_attrs(attrs_raw)
        command = (
            command_map.get(tool_name, "")
            or attrs.get("command")
            or attrs.get("cmd")
            or attrs.get("text")
            or attrs.get("query")
            or body.strip()
        )
        command = command.strip()
        if not command:
            return "Empty DoxTeam command"
        prefix = getattr(self.agent.kernel, "custom_prefix", ".") or "."
        if not command.startswith(prefix):
            command = prefix + command
        
        cmd_name = command[len(prefix):].split(maxsplit=1)[0].lower()
        if cmd_name in {"oa", "agent"}:
            return "Blocked recursive OpenAgent command"
        
        event = self.agent._DoxTeamEvent(self.agent, source_event, command)
        try:
            handled = await self.agent.kernel.process_command(event)
        except Exception as exc:
            await self.agent.kernel.handle_error(exc, source="OpenAgent:doxteam", event=source_event)
            return f"DoxTeam command failed: {exc}"
        output = event.output or f"Command handled: {handled}"
        return output[-6000:]
