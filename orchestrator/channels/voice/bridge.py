"""Voice-Bruecke: framework-unabhaengige Andockstelle Sprache <-> HoA-Kern.

Nimmt erkannten Text (aus STT) und liefert gesprochenen Text zurueck -- plus optional
eine Panel-Anweisung (show_panel) fuer die Browser-Oberflaeche. Kennt KEIN Pipecat/Audio
-> offline testbar. Der HoA-Kern bleibt unveraendert das Gehirn (Tor/Memory/Delegation).

Trennung:
- Reine Anzeige-Wuensche (Kostenuebersicht etc.) sind lesend -> Panel direkt, KEIN CEO-Tor.
- Alle anderen Anweisungen laufen durch den HoA-Kern (mit Tor, Gedaechtnis, Delegation);
  beruehrt eine Anweisung ein Tor, liefert der Kern eine gesprochene Freigabe-Anfrage.
"""
from __future__ import annotations

from dataclasses import dataclass

from ...governance.leak_guard import redact
from .panels import build_panel, detect_panel_intent


@dataclass
class BridgeResult:
    spoken: str
    panel: dict | None = None


class HoaBridge:
    def __init__(self, core, *, leak_secrets: list[str] | None = None, finance_dir=None):
        self.core = core
        self.leak_secrets = leak_secrets or []
        self.finance_dir = finance_dir

    def respond(self, text: str) -> BridgeResult:
        text = (text or "").strip()
        if not text:
            return BridgeResult(spoken="")

        # 1. Reiner Anzeige-Wunsch? -> Panel (lesend, kein Tor), kurze gesprochene Bestaetigung.
        intent = detect_panel_intent(text)
        if intent is not None:
            typ, daten = intent
            panel = build_panel(typ, daten, finance_dir=self.finance_dir,
                                secrets=self.leak_secrets)
            return BridgeResult(
                spoken=self._redact(_spoken_for_panel(typ)),
                panel=panel,
            )

        # 2. Sonst: HoA-Kern (Gehirn) -> gesprochene Antwort (Stream gebuendelt).
        spoken = "".join(self.core.handle(text))
        return BridgeResult(spoken=self._redact(spoken), panel=None)

    def _redact(self, s: str) -> str:
        return redact(s, self.leak_secrets)


def _spoken_for_panel(typ: str) -> str:
    # Gesprochene Texte (an den CEO) mit echten Umlauten -- bewusst nicht ASCII.
    if typ == "kostenuebersicht":
        return "Hier ist deine Kostenübersicht."
    if typ == "tabelle":
        return "Ich blende dir die Tabelle ein."
    return "Hier ist die gewünschte Einblendung."
