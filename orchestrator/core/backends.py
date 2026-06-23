"""Pluggable Modell-Backends.

- MockBackend: deterministisch, ohne Kosten/Netz -> fuer Dry-Run/Self-Checks.
- AgentSdkBackend: echtes Claude Agent SDK -> erst ab GATE B aktiviert.
"""
from __future__ import annotations

from typing import Callable, Protocol


class BackendError(Exception):
    """Modell-/Backend-Aufruf fehlgeschlagen (z. B. API-, Auth- oder Guthaben-Fehler).

    Traegt eine bereits CEO-taugliche, umlautfreie Meldung -- der HoA gibt sie als
    saubere Antwort aus, statt mit einem Traceback abzustuerzen.
    """


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
        max_turns: int = 4,
    ):
        self.model_map = model_map
        self.effort_map = effort_map
        self.allowed_tools_map = allowed_tools_map or {}
        self.gate = gate  # optionaler CeoGate fuer SDK-PreToolUse-Hook
        self.max_turns = max_turns

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

        # Schlanke, deterministische Subagenten: nur unser komponierter System-Prompt,
        # KEIN Projekt-CLAUDE.md/Skills (setting_sources=[]) und KEINE externen MCP-Server
        # (strict_mcp_config). Das senkt den Kontext-Overhead und verhindert, dass das
        # agentische Modell den (knappen) Turn fuer Tool-Versuche statt fuer eine Textantwort
        # verbraucht. allowed_tools bleibt restriktiv (Default: keine Tools).
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            model=self.model_map.get(agent_key, "claude-opus-4-8"),
            allowed_tools=self.allowed_tools_map.get(agent_key, []),
            max_turns=self.max_turns,
            setting_sources=[],
            mcp_servers={},
            strict_mcp_config=True,
            hooks=self._build_hooks(),
        )
        parts: list[str] = []
        try:
            async for msg in query(prompt=message, options=options):
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            parts.append(block.text)
        except Exception as exc:  # SDK-/CLI-/API-Fehler nicht als Traceback durchreichen
            raise BackendError(self._readable_error(agent_key, exc)) from exc
        return "".join(parts).strip()

    @staticmethod
    def _readable_error(agent_key: str, exc: Exception) -> str:
        """Macht aus einem rohen SDK-Fehler eine umlautfreie CEO-Meldung.

        Das Agent SDK kollabiert den konkreten API-Grund (z. B. 'Credit balance is
        too low') zu einer generischen Meldung. Wo erkennbar, geben wir einen
        Hinweis; sonst listen wir die haeufigen Ursachen auf.
        """
        raw = str(exc).strip() or exc.__class__.__name__
        low = raw.lower()
        if "credit" in low or "balance" in low:
            hinweis = "Anthropic-API-Guthaben zu niedrig -- unter console.anthropic.com (Billing) aufladen."
        elif "401" in low or "auth" in low or "api key" in low or "api-key" in low:
            hinweis = "Authentifizierung pruefen -- ANTHROPIC_API_KEY in orchestrator/.env."
        elif "model" in low or "not found" in low or "404" in low:
            hinweis = "Modell-Verfuegbarkeit pruefen (config.toml [models])."
        else:
            hinweis = (
                "Haeufige Ursachen: API-Guthaben zu niedrig, Authentifizierung "
                "(ANTHROPIC_API_KEY) oder Modell-Verfuegbarkeit. Details siehe Log."
            )
        return f"Modellaufruf fuer '{agent_key}' fehlgeschlagen ({raw}). {hinweis}"

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
