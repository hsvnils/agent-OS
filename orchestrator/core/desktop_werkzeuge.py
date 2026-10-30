"""Paket D L2 -- LUNA-Desktop (MACO470) nutzt LUNAs Werkzeuge (RECHNER_STEUERUNG_ROADMAP.md, CEO-Go 2026-10-30).

Das Gespraech fuehrt das **lokale Modell auf dem MACO470** (kein Cloud-Modell); die Werkzeuge laufen hier auf der NAS
mit LUNAs Daten und denselben Schutzregeln wie im Telegram-Chat (Fremdtext-Markierung I1, Handlungs-Sperre I3).

Grenzen (CISO, 2026-10-30):
- nur die feste Liste `ERLAUBT` -- Lesen, eigene To-dos/Notizen, Entwuerfe; Termine und Firmen nur mit Vorschau und
  `bestaetigt` nach dem gesprochenen „Ja“ des CEO (prueft der Desktop vor dem Senden);
- **nichts sendet, loescht oder kostet**: kein `mail_senden`, `termin_loeschen`, `delegate` (Cloud), keine Antraege,
  kein Investment, keine Web-Recherche;
- Zugang nur ueber das Maschinenkonto der Rolle `maschine` mit Modul `desktop` (`team_auth`), das ausschliesslich
  `/api/desktop/*` erreicht.
"""
from __future__ import annotations

import json
import threading

ERLAUBT = (
    "lagebild", "brain_suchen", "brain_merken", "notiz_hinzufuegen", "agenda_zeigen",
    "todos_zeigen", "todo_anlegen", "todo_erledigen",
    "kalender_agenda", "kalender_kollisionen", "termin_anlegen", "termin_aendern",
    "posteingang", "mail_suchen", "mail_lesen", "mail_entwurf",
    "firma_anlegen", "crm_zeigen", "auftraege_zeigen",
)
MAX_ERGEBNIS = 6000                 # Zeichen je Werkzeug-Ergebnis an das lokale Modell (Kontext 8k Token)
MAX_ZUEGE = 20


def specs() -> list[dict]:
    """Werkzeug-Beschreibungen der erlaubten Werkzeuge (Format wie `hoa_tools.tool_specs`)."""
    from .hoa_tools import tool_specs
    return [s for s in tool_specs() if s["name"] in ERLAUBT]


def gruppen() -> list[dict]:
    """Stichwoerter je Werkzeuggruppe (aus `werkzeugauswahl`) -> erlaubte Werkzeuge. Der Desktop erkennt daran Saetze, die
    nur mit Werkzeug beantwortet werden duerfen (Werkzeugpflicht gegen erfundene Antworten des lokalen Modells)."""
    from .werkzeugauswahl import GRUPPEN
    out = []
    for name, g in GRUPPEN.items():
        w = [x for x in g["werkzeuge"] if x in ERLAUBT]
        if w:
            out.append({"gruppe": name, "stichwoerter": g["stichwoerter"], "werkzeuge": w})
    return out


def kuerzen(ergebnis) -> str:
    text = json.dumps(ergebnis, ensure_ascii=False, default=str)
    return text if len(text) <= MAX_ERGEBNIS else text[:MAX_ERGEBNIS] + " …(gekuerzt)"


class DesktopWerkzeuge:
    """Fuehrt ein erlaubtes Werkzeug im LUNA-Kontext aus. `zug` = ein gesprochener Auftrag: Injection-Verdacht aus einem
    Werkzeug sperrt Aktionen fuer den Rest dieses Zugs (wie `HoaConversation` je Nachricht)."""

    def __init__(self, ctx_holen):
        self.ctx_holen = ctx_holen
        self._lock = threading.Lock()
        self._verdacht: dict[str, list] = {}

    def ausfuehren(self, name: str, args: dict | None, zug: str) -> dict:
        if name not in ERLAUBT:
            return {"ok": False, "fehler": f"Werkzeug '{name}' ist fuer den Desktop nicht freigegeben."}
        ctx = self.ctx_holen()
        if ctx is None:
            return {"ok": False, "fehler": "LUNA-Kontext nicht verfuegbar."}
        from .hoa_tools import run_tool
        with self._lock:
            if zug not in self._verdacht and len(self._verdacht) >= MAX_ZUEGE:
                self._verdacht.pop(next(iter(self._verdacht)))
            alt_v, alt_k = ctx.fremd_verdacht, ctx.knoepfe
            ctx.fremd_verdacht, ctx.knoepfe = self._verdacht.setdefault(str(zug or ""), []), []
            try:
                res = run_tool(name, dict(args or {}), ctx)
            finally:
                ctx.fremd_verdacht, ctx.knoepfe = alt_v, alt_k
        return {"ok": True, "ergebnis": kuerzen(res)}
