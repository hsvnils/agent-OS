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
    """Echtes Backend auf Basis des Claude Agent SDK.

    Wird ERST ab GATE B aktiviert. Die exakten SDK-Bindings (ClaudeSDKClient,
    ClaudeAgentOptions, AgentDefinition, Hooks) werden vor Aktivierung gegen
    `anthropics/claude-agent-sdk-python` verifiziert. Bis dahin bewusst nicht
    implementiert, damit nichts auf ungepruefte API-Namen baut.
    """

    def __init__(self, model_map: dict[str, str], effort_map: dict[str, str]):
        self.model_map = model_map
        self.effort_map = effort_map

    def respond(self, agent_key: str, system_prompt: str, message: str, context: dict) -> str:
        raise NotImplementedError(
            "AgentSdkBackend wird vor GATE B (verifizierte SDK-Bindings + ANTHROPIC_API_KEY) "
            "aktiviert. Bis dahin dry_run=true (MockBackend) verwenden."
        )
