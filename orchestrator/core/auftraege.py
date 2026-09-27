"""Backoffice-Auftraege (FRONTDESK_BACKOFFICE_ROADMAP.md) -- Warteschlange fuer Hintergrund-Arbeit des lokalen LLM.

Der Frontdesk (Chat) legt Auftraege an, der Backoffice-Worker auf dem MACO470 holt sie ueber die LUNA-OS-API
(`/api/backoffice/*`), arbeitet sie nacheinander ab und meldet das Ergebnis zurueck. Append-only JSONL wie die
Research-Tickets: jedes Ereignis eine Zeile, der Zustand ergibt sich aus der Faltung (`_fold`).

Lebenszyklus: neu -> in_arbeit -> fertig | fehlgeschlagen (haengende in_arbeit fallen nach `aufraeumen` auf neu zurueck).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from ..governance.leak_guard import redact

STATUSES = ("neu", "in_arbeit", "fertig", "fehlgeschlagen")
ARTEN = ("zusammenfassung", "entwurf", "bewertung", "analyse", "sonstiges", "roh")   # roh = Job-Auftrag mit eigenem System-Prompt
_FELDER = ("art", "aufgabe", "von", "ergebnis", "zweitmeinung", "modell", "dauer_s", "grund", "meldung", "system", "zweck",
           "stumm")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def kurz_id(auftrag_id: str) -> str:
    return (auftrag_id or "").split("-")[-1]


class AuftragStore:
    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []

    # -- Schreiben -------------------------------------------------------------------------------------------------

    def anlegen(self, aufgabe: str, *, art: str = "sonstiges", von: str = "CEO", system: str = "", zweck: str = "",
                stumm: bool = False) -> str:
        """`stumm`: Job-internes Ergebnis (Etappe 4) -- keine Meldung an den CEO, der Job verarbeitet es selbst."""
        aufgabe = (aufgabe or "").strip()
        if not aufgabe:
            raise ValueError("Leerer Auftrag.")
        art = art if art in ARTEN else "sonstiges"
        # BO = Backoffice -- Antraege heissen A-..., Second-Brain-Eintraege B-... (BF-29); sonst zum Verwechseln aehnlich.
        aid = "BO-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({"ts": _now(), "id": aid, "event": "neu", "art": art, "aufgabe": aufgabe[:12000], "von": von,
                      "system": system[:8000] or None, "zweck": zweck or None, "stumm": True if stumm else None})
        return aid

    def naechster(self) -> dict | None:
        """Aeltesten neuen Auftrag holen und als in_arbeit markieren (genau ein Worker -> kein Wettlauf)."""
        offen = sorted(self.list("neu"), key=lambda a: a["verlauf"][0]["ts"])
        if not offen:
            return None
        self._transition(offen[0]["id"], "in_arbeit")
        return self.get(offen[0]["id"])

    def fertig(self, auftrag_id: str, *, ergebnis: str, modell: str = "", dauer_s: float = 0,
               zweitmeinung: str = "", meldung: str = "einzeln") -> bool:
        return self._transition(auftrag_id, "fertig", ergebnis=ergebnis[:20000], modell=modell,
                                dauer_s=round(float(dauer_s or 0), 1), zweitmeinung=zweitmeinung[:6000] or None,
                                meldung=meldung)

    def fehlschlag(self, auftrag_id: str, *, grund: str, meldung: str = "einzeln") -> bool:
        return self._transition(auftrag_id, "fehlgeschlagen", grund=(grund or "")[:500], meldung=meldung)

    def aufraeumen(self, stunden: float = 2) -> int:
        """Auftraege, die laenger als `stunden` in_arbeit haengen (Worker abgestuerzt), zurueck auf neu."""
        grenze = datetime.now() - timedelta(hours=stunden)
        n = 0
        for a in self.list("in_arbeit"):
            if _ts(a["verlauf"][-1]["ts"]) < grenze:
                self._transition(a["id"], "neu", grund="haengend, erneut eingereiht")
                n += 1
        return n

    # -- Lesen -----------------------------------------------------------------------------------------------------

    def get(self, auftrag_id: str) -> dict | None:
        state = self._fold()
        if auftrag_id in state:
            return state[auftrag_id]
        treffer = [a for k, a in state.items() if kurz_id(k) == auftrag_id.lstrip("#")]
        return treffer[0] if len(treffer) == 1 else None

    def list(self, status: str | None = None) -> list[dict]:
        items = list(self._fold().values())
        if status:
            items = [a for a in items if a.get("status") == status]
        items.sort(key=lambda a: a["verlauf"][-1]["ts"], reverse=True)
        return items

    def fuer_briefing(self, seit: datetime) -> list[dict]:
        """Seit `seit` fertig/fehlgeschlagen und fuer das Briefing (statt Einzelmeldung) vorgesehen."""
        return [a for a in self.list() if a.get("meldung") == "briefing"
                and a.get("status") in ("fertig", "fehlgeschlagen") and _ts(a["verlauf"][-1]["ts"]) >= seit]

    # -- intern ----------------------------------------------------------------------------------------------------

    def _transition(self, auftrag_id: str, event: str, **extra) -> bool:
        if event not in STATUSES:
            raise ValueError(f"Unbekannter Status: {event}")
        if auftrag_id not in self._fold():
            return False
        self._append({"ts": _now(), "id": auftrag_id, "event": event, **{k: v for k, v in extra.items() if v is not None}})
        return True

    def _append(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(redact(json.dumps(event, ensure_ascii=False), self.secrets) + "\n")

    def _events(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out

    def _fold(self) -> dict[str, dict]:
        state: dict[str, dict] = {}
        for e in self._events():
            aid = e.get("id")
            if not aid:
                continue
            cur = state.setdefault(aid, {"id": aid, "kurz": kurz_id(aid), "verlauf": []})
            for k in _FELDER:
                if e.get(k) is not None:
                    cur[k] = e[k]
            cur["status"] = e.get("event", cur.get("status"))
            cur["verlauf"].append({"ts": e.get("ts"), "event": e.get("event")})
        return state


def _ts(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return datetime.min


def briefing_zeilen(store: AuftragStore, seit: datetime) -> list[str]:
    """Zeilen fuer das Morgen-Briefing: nachts im Backoffice erledigte Auftraege (CEO-Entscheidung 2026-09-26)."""
    zeilen = []
    for a in store.fuer_briefing(seit):
        titel = " ".join(a.get("aufgabe", "").split())[:80]
        if a["status"] == "fertig":
            zeilen.append(f"#{a['kurz']} {titel} — erledigt (Ergebnis: schreib „zeig Auftrag #{a['kurz']}\")")
        else:
            zeilen.append(f"#{a['kurz']} {titel} — fehlgeschlagen: {a.get('grund', '')[:80]}")
    return zeilen
