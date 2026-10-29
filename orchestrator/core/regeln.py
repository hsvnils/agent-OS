"""Feste Regeln des CEO fuer LUNA (JARVIS_ALLTAG J7 „LUNA lernt aus Korrekturen“, CEO-Go 2026-10-29).

Korrigiert der CEO LUNA (Schreibweise, Format, Vorgehen), schlaegt LUNA mit dem Werkzeug `regel_vorschlagen` eine
feste Regel vor. **Erst nach Bestaetigung des CEO gilt sie** (Knopf in Telegram oder LUNA-OS); danach steht sie in jedem
Gespraech im System-Prompt. Kein Modell-Training -- nur eine Liste von Anweisungen, jederzeit loeschbar.

- Speicher `regeln/log.jsonl` (nur NAS + Backup, nicht im Git): eine Zeile je Ereignis -- `vorgeschlagen`,
  `bestaetigt`, `abgelehnt`, `geloescht`; es geht nichts verloren.
- Schutz: Regeltexte mit Injection-Muster (`core/input_guard.pruefe`) werden gar nicht erst vorgeschlagen; das
  Werkzeug steht in `AKTIONS_WERKZEUGE` (nach Fremdtext-Verdacht im Zug gesperrt). Hoechstens `MAX_AKTIV` Regeln,
  je `MAX_TEXT` Zeichen, damit der Prompt klein bleibt.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path

MAX_TEXT, MAX_ANLASS = 200, 300
MAX_AKTIV = 30
_ID = re.compile(r"^R-[0-9a-f]{8}$")


def _t(x, n: int) -> str:
    return " ".join(str(x or "").split())[:n]


def _schluessel(text: str) -> str:
    return re.sub(r"[^\w]+", " ", text.lower()).strip()


class RegelStore:
    def __init__(self, pfad: Path | str):
        self.pfad = Path(pfad)
        self._lock = threading.Lock()

    # -- Lesen -------------------------------------------------------------------------------------------------------
    def _falte(self) -> dict[str, dict]:
        try:
            zeilen = self.pfad.read_text(encoding="utf-8").splitlines()
        except OSError:
            return {}
        out: dict[str, dict] = {}
        for z in zeilen:
            try:
                e = json.loads(z)
            except ValueError:
                continue
            rid, t, d = e.get("id"), e.get("typ"), e.get("daten") or {}
            if t == "vorgeschlagen":
                out[rid] = {"id": rid, "text": d.get("text", ""), "anlass": d.get("anlass", ""), "status": "offen",
                            "vorgeschlagen_am": e.get("ts", ""), "entschieden_am": "", "von": e.get("von", "")}
            elif rid in out and t in ("bestaetigt", "abgelehnt", "geloescht"):
                out[rid] |= {"status": t, "entschieden_am": e.get("ts", "")}
        return out

    def get(self, rid: str) -> dict | None:
        return self._falte().get((rid or "").strip())

    def liste(self) -> dict:
        """Gruppiert: aktiv (bestaetigt), offen (wartet auf den CEO); neueste zuerst."""
        alle = sorted(self._falte().values(), key=lambda r: r["vorgeschlagen_am"], reverse=True)
        return {"aktiv": [r for r in alle if r["status"] == "bestaetigt"],
                "offen": [r for r in alle if r["status"] == "offen"]}

    def aktive(self) -> list[dict]:
        """Bestaetigte Regeln, aelteste zuerst (stabile Nummerierung im Prompt)."""
        return sorted((r for r in self._falte().values() if r["status"] == "bestaetigt"),
                      key=lambda r: r["vorgeschlagen_am"])

    # -- Schreiben -----------------------------------------------------------------------------------------------------
    def _schreibe(self, typ: str, rid: str, daten: dict | None = None, von: str = "") -> None:
        e = {"ts": datetime.now().isoformat(timespec="seconds"), "typ": typ, "id": rid, "daten": daten or {}, "von": von}
        with self._lock:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            with self.pfad.open("a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def vorschlagen(self, text: str, *, anlass: str = "", von: str = "LUNA") -> dict:
        """Neuer Vorschlag (Status offen). Gleicher Text schon aktiv/offen -> den vorhandenen zurueck (`doppelt`)."""
        from .input_guard import pruefe
        text, anlass = _t(text, MAX_TEXT), _t(anlass, MAX_ANLASS)
        if len(text) < 5:
            raise ValueError("Regeltext fehlt oder ist zu kurz.")
        if pruefe(text).verdaechtig:
            raise ValueError("Der Regeltext sieht nach einer eingeschleusten Anweisung aus -- nicht vorgeschlagen.")
        for r in self._falte().values():
            if r["status"] in ("offen", "bestaetigt") and _schluessel(r["text"]) == _schluessel(text):
                return r | {"doppelt": True}
        if len(self.aktive()) >= MAX_AKTIV:
            raise ValueError(f"Schon {MAX_AKTIV} feste Regeln -- bitte erst eine alte in LUNA-OS löschen.")
        rid = "R-" + uuid.uuid4().hex[:8]
        self._schreibe("vorgeschlagen", rid, {"text": text, "anlass": anlass}, von)
        return self.get(rid)

    def entscheiden(self, rid: str, aktion: str, *, von: str = "") -> dict:
        """aktion: bestaetigen | ablehnen (nur offene) | loeschen (offene oder aktive)."""
        r = self.get(rid) if _ID.match(rid or "") else None
        if not r or r["status"] in ("abgelehnt", "geloescht"):
            raise KeyError(rid)
        typ = {"bestaetigen": "bestaetigt", "ablehnen": "abgelehnt", "loeschen": "geloescht"}.get(aktion)
        if not typ:
            raise ValueError("Unbekannte Aktion.")
        if r["status"] == "bestaetigt" and typ != "geloescht":
            return r                                   # schon entschieden (doppelter Klick) -> nichts aendern
        if typ == "bestaetigt" and len(self.aktive()) >= MAX_AKTIV:
            raise ValueError(f"Schon {MAX_AKTIV} feste Regeln -- bitte erst eine alte in LUNA-OS löschen.")
        self._schreibe(typ, r["id"], None, von)
        return self.get(r["id"])


def prompt_text(regeln: list[dict]) -> str:
    """Abschnitt fuer den System-Prompt (leer, wenn es keine Regeln gibt)."""
    if not regeln:
        return ""
    zeilen = " ".join(f"({i}) {r['text']}" for i, r in enumerate(regeln, 1))
    return (" FESTE REGELN DES CEO (von ihm bestaetigt, gelten immer und gehen allgemeinen Gewohnheiten vor): "
            + zeilen)


def knopf(store: RegelStore, rid: str, aktion: str, *, von: str = "Telegram:CEO") -> str:
    """Telegram-Knopf `rgl:<id>:ja|nein` -> kurze Antwort fuer den CEO."""
    try:
        r = store.entscheiden(rid, "bestaetigen" if aktion == "ja" else "ablehnen", von=von)
    except KeyError:
        return "Diesen Vorschlag gibt es nicht mehr."
    except ValueError as exc:
        return f"⚠️ {exc}"
    if r["status"] == "bestaetigt":
        return f"🧠 Gemerkt als feste Regel: „{r['text']}“ – gilt ab der nächsten Nachricht. Liste in LUNA-OS → Einstellungen."
    return "Okay, keine Regel daraus gemacht."
