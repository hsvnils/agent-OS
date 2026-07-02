"""Collab-CRM-Store (kanalagnostisch, event-sourced JSONL).

Erfasst eingehende Kooperations-/Sponsoring-Anfragen aus verschiedenen Kanaelen (Feld `quelle`:
instagram|telegram|gmail|manuell) als leichtgewichtiges CRM: Unternehmen/Kontakt, Nachrichten-Verlauf,
Pipeline-Status und To-do-Vorschlaege. **Nur lesen/tracken/vorschlagen -- kein Senden** (Oeffentlichkeit =
CEO-Tor). Fundament fuers geplante Partner-/Akten-System; Instagram ist nur der erste Kanal.

Append-only JSONL; der Zustand je Firma wird aus den Events gefaltet. Leck-geschuetzt beim Schreiben.
Gitignored + vom NAS-Sync ausgeschlossen. Abgegrenzt von Antraegen (Freigaben) und Second Brain (Wissen).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..governance.leak_guard import redact

STUFEN = ("neu", "in_gespraech", "angebot", "vereinbart", "abgelehnt")
QUELLEN = ("instagram", "telegram", "gmail", "manuell")
RICHTUNGEN = ("ein", "aus")

# Regelbasierte Klassifikation (token-frugal, kostenlos) -- Kooperations-Signalwoerter.
_KOOP_KEYWORDS = ("kooperation", "koop", "collab", "zusammenarbeit", "zusammen arbeiten", "sponsor",
                  "sponsoring", "werbung", "kampagne", "partnerschaft", "partner", "anfrage", "barter",
                  "produkttest", "rabattcode", "affiliate", "brand deal", "brand", "marke", "influencer")


def klassifiziere(text: str) -> str:
    """Regelbasiert: 'kooperation' bei Koop-Signalwoertern, sonst 'unklar'. Kein LLM (token-frugal);
    eine tiefere Einschaetzung kann LUNA bei Bedarf via delegate an den CRO-Fachagenten anfordern."""
    t = (text or "").lower()
    return "kooperation" if any(k in t for k in _KOOP_KEYWORDS) else "unklar"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _key(firma: str) -> str:
    """Normalisierter Firmen-Schluessel (case-insensitiv) fuer die Zuordnung der Events."""
    return (firma or "").strip().lower()


def _id(prefix: str) -> str:
    return prefix + "-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]


class CrmStore:
    def __init__(self, path: str | Path, *, secrets: list[str] | None = None,
                 changelog: Callable[..., None] | None = None, projektor=None):
        self.path = Path(path)
        self.secrets = secrets or []
        self.changelog = changelog
        self.projektor = projektor  # optional: Write-Through nach Supabase (duck-typed .firma/.nachricht/.todo)

    # -- Write-Through-Projektion (best-effort; lokaler Store bleibt Quelle + Fallback) --
    def _projiziere_firma(self, firma: str) -> None:
        if not self.projektor:
            return
        k = _key(firma)
        for f in self.firmen():
            if _key(f.get("firma")) == k:
                try:
                    self.projektor.firma({"ref": k, "firma": f.get("firma"), "status": f.get("status"),
                                          "quelle": f.get("quelle"), "nachrichten": f.get("nachrichten"),
                                          "letzter_kontakt": f.get("letzter_kontakt"), "updated_by": "luna"})
                except Exception:
                    pass
                return

    def _projiziere(self, methode: str, payload: dict) -> None:
        if not self.projektor:
            return
        try:
            getattr(self.projektor, methode)(payload)
        except Exception:
            pass

    # -- schreiben --
    def nachricht_erfassen(self, firma: str, text: str, *, quelle: str = "manuell", richtung: str = "ein",
                           absender: str = "", extern_id: str = "", kategorie: str = "") -> str:
        """Erfasst eine (eingehende) Nachricht einer Firma. `extern_id` (z. B. Meta-Message-ID) dedupliziert
        Webhook-Wiederholungen. Neue Firma bekommt automatisch Status 'neu'. Gibt "" bei leer/Duplikat."""
        firma = (firma or "").strip()
        if not firma or not (text or "").strip():
            return ""
        if extern_id and any(e.get("extern_id") == extern_id
                             for e in self._events() if e.get("event") == "nachricht"):
            return ""  # Dedup: schon erfasst (Webhook-Retry)
        mid = _id("M")
        self._append({"ts": _now(), "id": mid, "event": "nachricht", "firma": firma, "quelle": quelle,
                      "richtung": richtung, "text": text, "absender": absender, "extern_id": extern_id,
                      "kategorie": kategorie})
        if not self._letzter_status(firma):
            self._append({"ts": _now(), "id": _id("S"), "event": "status", "firma": firma, "status": "neu"})
        # Write-Through: erst die Firma (FK-Ziel), dann die Nachricht.
        self._projiziere_firma(firma)
        self._projiziere("nachricht", {"extern_id": extern_id or None, "ref": _key(firma), "firma": firma,
                                       "richtung": richtung, "quelle": quelle, "kategorie": kategorie,
                                       "text": text, "ts": _now()})
        return mid

    def verarbeite_eingang(self, firma: str, text: str, *, quelle: str = "instagram", absender: str = "",
                           extern_id: str = "") -> dict:
        """Erfasst eine eingehende DM inkl. regelbasierter Klassifikation und legt bei einer NEUEN
        Kooperationsanfrage automatisch ein 'pruefen'-To-do an. Gibt {mid, kategorie, todo_id, firma}.
        Basis fuer Webhook (Instagram) und kuenftige Kanaele (Telegram/Gmail)."""
        firma = (firma or "").strip()
        kategorie = klassifiziere(text)
        neu = self._letzter_status(firma) is None
        mid = self.nachricht_erfassen(firma, text, quelle=quelle, richtung="ein", absender=absender,
                                      extern_id=extern_id, kategorie=kategorie)
        todo_id = ""
        if mid and kategorie == "kooperation" and neu:
            todo_id = self.todo_hinzufuegen(firma, f"Neue Kooperationsanfrage von {firma} pruefen/antworten",
                                            begruendung="Erstkontakt via " + quelle)
        return {"mid": mid, "kategorie": kategorie, "todo_id": todo_id, "firma": firma, "neu": neu}

    def status_setzen(self, firma: str, status: str) -> str:
        if status not in STUFEN:
            raise ValueError(f"Unbekannter Status: {status}")
        sid = _id("S")
        self._append({"ts": _now(), "id": sid, "event": "status", "firma": (firma or "").strip(),
                      "status": status})
        self._projiziere_firma(firma)
        return sid

    def todo_hinzufuegen(self, firma: str, vorschlag: str, *, faellig: str = "", begruendung: str = "") -> str:
        tid = _id("T")
        firma = (firma or "").strip()
        self._append({"ts": _now(), "id": tid, "event": "todo", "firma": firma,
                      "vorschlag": vorschlag, "faellig": faellig, "begruendung": begruendung, "status": "offen"})
        self._projiziere_firma(firma)  # sicherstellen, dass die Firma (FK-Ziel) existiert
        self._projiziere("todo", {"id": tid, "ref": _key(firma), "firma": firma, "vorschlag": vorschlag,
                                  "begruendung": begruendung, "faellig": faellig, "status": "offen",
                                  "updated_by": "luna"})
        return tid

    def todo_erledigen(self, todo_id: str) -> bool:
        self._append({"ts": _now(), "id": _id("TE"), "event": "todo_erledigt", "todo_id": todo_id})
        for t in self.todos(nur_offen=False):
            if t.get("id") == todo_id:
                self._projiziere("todo", {"id": todo_id, "ref": _key(t.get("firma")), "firma": t.get("firma"),
                                          "vorschlag": t.get("vorschlag"), "begruendung": t.get("begruendung"),
                                          "faellig": t.get("faellig"), "status": "erledigt",
                                          "updated_by": "luna"})
                break
        return True

    # -- Rueckschreiben: externe (HCC-)Aenderungen lokal uebernehmen, OHNE zurueck zu projizieren --
    def uebernehmen_status_extern(self, firma: str, status: str) -> bool:
        """Wendet eine im HCC gemachte Statusaenderung lokal an. Kein Write-Through zurueck (Loop-Schutz);
        Supabase hat die Aenderung bereits. Kein Effekt, wenn der Status lokal schon so ist."""
        if status not in STUFEN:
            return False
        firma = (firma or "").strip()
        if self._letzter_status(firma) == status:
            return False
        self._append({"ts": _now(), "id": _id("S"), "event": "status", "firma": firma,
                      "status": status, "quelle_sync": "hcc"})
        return True

    def uebernehmen_todo_extern(self, todo_id: str, status: str) -> bool:
        """Uebernimmt eine im HCC gemachte To-do-Aenderung (aktuell: 'erledigt') lokal, ohne Rueck-Projektion."""
        if status != "erledigt":
            return False
        offen = {t.get("id") for t in self.todos(nur_offen=True)}
        if todo_id not in offen:
            return False  # schon erledigt oder unbekannt
        self._append({"ts": _now(), "id": _id("TE"), "event": "todo_erledigt", "todo_id": todo_id,
                      "quelle_sync": "hcc"})
        return True

    # -- lesen (gefaltet) --
    def _letzter_status(self, firma: str) -> str | None:
        st, k = None, _key(firma)
        for e in self._events():
            if e.get("event") == "status" and _key(e.get("firma")) == k:
                st = e.get("status")
        return st

    def konversation(self, firma: str) -> list[dict]:
        k = _key(firma)
        return [e for e in self._events() if e.get("event") == "nachricht" and _key(e.get("firma")) == k]

    def timeline(self, *, firma: str | None = None, limit: int = 100) -> list[dict]:
        """Phase 20: Nachrichten **kanaluebergreifend** (Instagram/Mail/Telegram/...) chronologisch,
        neueste zuerst. Optional auf eine Firma gefiltert. Feld `quelle` = Kanal."""
        k = _key(firma) if firma else None
        felder = ("id", "firma", "quelle", "richtung", "text", "absender", "kategorie", "ts")
        msgs = [{f: e.get(f) for f in felder} for e in self._events()
                if e.get("event") == "nachricht" and (k is None or _key(e.get("firma")) == k)]
        msgs.sort(key=lambda m: m.get("ts") or "", reverse=True)
        return msgs[:limit]

    def firmen(self) -> list[dict]:
        """Gefalteter Stand je Firma: Status, Nachrichtenzahl, letzter Kontakt, Quelle."""
        firmen: dict[str, dict] = {}
        for e in self._events():
            ev, k = e.get("event"), _key(e.get("firma"))
            if not k:
                continue
            f = firmen.setdefault(k, {"firma": e.get("firma"), "status": "neu", "nachrichten": 0,
                                      "letzter_kontakt": None, "quelle": e.get("quelle")})
            if e.get("firma"):
                f["firma"] = e.get("firma")
            if ev == "nachricht":
                f["nachrichten"] += 1
                f["letzter_kontakt"] = e.get("ts")
                f["quelle"] = e.get("quelle") or f["quelle"]
            elif ev == "status":
                f["status"] = e.get("status", f["status"])
        return list(firmen.values())

    def todos(self, *, nur_offen: bool = True) -> list[dict]:
        erledigt = {e.get("todo_id") for e in self._events() if e.get("event") == "todo_erledigt"}
        out = []
        for e in self._events():
            if e.get("event") != "todo":
                continue
            status = "erledigt" if e.get("id") in erledigt else "offen"
            if nur_offen and status == "erledigt":
                continue
            out.append({k: e.get(k) for k in ("id", "firma", "vorschlag", "faellig", "begruendung", "ts")}
                       | {"status": status})
        return out

    def uebersicht(self) -> dict:
        firmen = self.firmen()
        pipeline = {s: 0 for s in STUFEN}
        for f in firmen:
            pipeline[f.get("status", "neu")] = pipeline.get(f.get("status", "neu"), 0) + 1
        return {"firmen_gesamt": len(firmen), "pipeline": pipeline,
                "offene_todos": len(self.todos(nur_offen=True))}

    # -- intern --
    def _append(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps(event, ensure_ascii=False), self.secrets)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _events(self) -> list[dict]:
        if not self.path.exists():
            return []
        out: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out
