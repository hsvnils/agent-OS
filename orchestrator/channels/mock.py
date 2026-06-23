"""Mock-Kanal-Adapter fuer Offline-Self-Checks (kein Terminal, kein Modell)."""
from __future__ import annotations

from .base import ChannelAdapter


class MockAdapter(ChannelAdapter):
    def __init__(self, inputs: list[str]):
        self.inputs = list(inputs)
        self.outputs: list[str] = []

    def next_message(self) -> str | None:
        return self.inputs.pop(0) if self.inputs else None

    def emit(self, chunk: str) -> None:
        self.outputs.append(chunk)

    def text(self) -> str:
        return "".join(self.outputs)
