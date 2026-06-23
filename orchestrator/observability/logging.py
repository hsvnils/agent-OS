"""Strukturiertes Logging aller Tool-/Delegations-Aufrufe + Token-Schaetzung.

Speist spaeter den CFO. Standard: In-Memory + optional Datei-Sink.
"""
from __future__ import annotations

from typing import Callable


def estimate_tokens(text: str) -> int:
    # grobe Schaetzung (~4 Zeichen/Token); echte Zahlen liefert das Modell-Backend.
    return max(1, len(text) // 4)


class Logger:
    def __init__(self, sink: Callable[[dict], None] | None = None):
        self.events: list[dict] = []
        self.sink = sink

    def log(self, kind: str, key: str, detail: str = "", tokens: int | None = None) -> None:
        ev = {
            "kind": kind,
            "key": key,
            "detail": str(detail)[:200],
            "tokens_est": tokens if tokens is not None else estimate_tokens(str(detail)),
        }
        self.events.append(ev)
        if self.sink:
            self.sink(ev)
