"""ChannelAdapter -- schmale, dokumentierte Schnittstelle (Adapter-Pattern).

Jeder Front-end-Kanal (Terminal jetzt; Live-Voice/Telegram geplant) programmiert
gegen diese Schnittstelle. Der HoA-Kern bleibt davon unberuehrt.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ChannelAdapter(ABC):
    @abstractmethod
    def next_message(self) -> str | None:
        """Naechste CEO-Nachricht, oder None fuer Ende der Sitzung."""

    @abstractmethod
    def emit(self, chunk: str) -> None:
        """Antwort-Teilstueck (Stream) ausgeben."""

    def run(self, core) -> None:
        """Sitzungsschleife: Nachricht -> Kern -> Antwort-Stream -> Ausgabe."""
        while True:
            message = self.next_message()
            if message is None:
                break
            for chunk in core.handle(message):
                self.emit(chunk)
            self.emit("\n")
