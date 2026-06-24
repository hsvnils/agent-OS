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

import re
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
        consolidated = "".join(self.core.handle(text))
        return BridgeResult(spoken=self._redact(_voice_clean(consolidated)), panel=None)

    def _redact(self, s: str) -> str:
        return redact(s, self.leak_secrets)


_MD = re.compile(r"[#*`>|_]+")


def _voice_clean(text: str) -> str:
    """Macht aus der konsolidierten HoA-Antwort einen sprechbaren Text.

    Entfernt den Bundle-Rahmen ("Konsolidierte Antwort an den CEO:", "Auftrag: ..."),
    die Agenten-Praefixe ("- berater: ") und grobe Markdown-Zeichen. CEO-Tor-Antworten
    (kein Bundle-Header) werden unveraendert gesprochen.
    """
    lines = text.splitlines()
    if not lines or not lines[0].startswith("Konsolidierte Antwort"):
        return text.strip()
    out: list[str] = []
    for ln in lines[1:]:
        s = ln.strip()
        if not s or s.startswith("Auftrag:"):
            continue
        if set(s) <= set("-:| "):  # Markdown-Tabellentrenner ueberspringen
            continue
        if s.startswith("- "):  # "- berater: <text>" -> "<text>"
            s = s[2:]
            head, sep, rest = s.partition(": ")
            if sep and head in ("berater", "cto"):
                s = rest
        s = _MD.sub("", s).strip()
        if s:
            out.append(s)
    return " ".join(out).strip() or text.strip()


def _spoken_for_panel(typ: str) -> str:
    # Gesprochene Texte (an den CEO) mit echten Umlauten -- bewusst nicht ASCII.
    if typ == "kostenuebersicht":
        return "Hier ist deine Kostenübersicht."
    if typ == "tabelle":
        return "Ich blende dir die Tabelle ein."
    return "Hier ist die gewünschte Einblendung."
