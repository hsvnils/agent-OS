"""Pluggable Modell-Backends.

- MockBackend: deterministisch, ohne Kosten/Netz -> fuer Dry-Run/Self-Checks.
- AgentSdkBackend: echtes Claude Agent SDK -> erst ab GATE B aktiviert.
"""
from __future__ import annotations

from typing import Callable, Protocol


class Backend(Protocol):
    def respond(self, agent_key: str, system_prompt: str, message: str, context: dict) -> str: ...


class MockBackend:
    """Deterministisches Backend ohne echte Modellaufrufe.

    `scripted` erlaubt je Agent eine Funktion (message, context) -> str.
    Konvention: gibt ein Ergebnis mit Prefix 'BLOCKED' zurueck, wenn die
    Aufgabe (simuliert) ausserhalb des Mandats liegt.
    """

    def __init__(self, scripted: dict[str, Callable[[str, dict], str]] | None = None):
        self.scripted = scripted or {}
        self.calls: list[tuple[str, str]] = []

    def respond(self, agent_key: str, system_prompt: str, message: str, context: dict) -> str:
        self.calls.append((agent_key, message))
        if agent_key in self.scripted:
            return self.scripted[agent_key](message, context)
        if "BLOCK:" in message:
            return "BLOCKED: " + message.split("BLOCK:", 1)[1].strip()
        return f"[{agent_key}] Ergebnis zu: {message.strip()}"


class AgentSdkBackend:
    """Echtes Backend auf Basis des Claude Agent SDK (Python).

    Bindings gegen `anthropics/claude-agent-sdk-python` verifiziert:
    `query`, `ClaudeAgentOptions`, `HookMatcher`, `AssistantMessage`, `TextBlock`.
    Lazy import (Top-Level bleibt SDK-frei, damit Offline-Self-Checks ohne SDK
    laufen). Wird beim GATE-B-Mini-Lauf real ausgefuehrt (benoetigt
    claude-agent-sdk, Claude CLI und ANTHROPIC_API_KEY).
    """

    def __init__(
        self,
        model_map: dict[str, str],
        effort_map: dict[str, str],
        *,
        allowed_tools_map: dict[str, list[str]] | None = None,
        gate=None,
    ):
        self.model_map = model_map
        self.effort_map = effort_map
        self.allowed_tools_map = allowed_tools_map or {}
        self.gate = gate  # optionaler CeoGate fuer SDK-PreToolUse-Hook

    def respond(self, agent_key: str, system_prompt: str, message: str, context: dict) -> str:
        import asyncio

        return asyncio.run(self._arespond(agent_key, system_prompt, message))

    async def _arespond(self, agent_key: str, system_prompt: str, message: str) -> str:
        from claude_agent_sdk import (  # lazy: nur im Live-Pfad benoetigt
            AssistantMessage,
            ClaudeAgentOptions,
            TextBlock,
            query,
        )

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            model=self.model_map.get(agent_key, "claude-opus-4-8"),
            allowed_tools=self.allowed_tools_map.get(agent_key, []),
            max_turns=1,
            hooks=self._build_hooks(),
        )
        parts: list[str] = []
        async for msg in query(prompt=message, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
        return "".join(parts).strip()

    def _build_hooks(self):
        if self.gate is None:
            return None
        from claude_agent_sdk import HookMatcher

        gate = self.gate

        async def pre_tool(input_data, tool_use_id, context):
            # CEO-Tor auch auf SDK-Tool-Aufrufe: bei Treffer verweigern.
            result = gate.check(str(input_data))
            if result.blocked:
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"CEO-Tor ({result.category}): {result.freigabe_anfrage}"
                        ),
                    }
                }
            return {}

        return {"PreToolUse": [HookMatcher(matcher="*", hooks=[pre_tool])]}
