"""Instagram-Postfach-Archiv (Collab-Radar, Phase 1) -- event-sourced JSONL.

Spiegelt das **gesamte** Postfach je Kontakt: eingehende UND ausgehende Nachrichten (Text + Medien-Marker),
dedupliziert ueber die Meta-Message-ID. Fundament fuer die KI-Analyse (Phase 2), die Collab-Radar-Ansicht
(Phase 3) und die Nachfass-Reminder (Phase 4). Reines Lesen/Spiegeln -- kein Senden.

Anders als `CrmStore` (nur eingehende Kooperations-Anfragen) ist dies das **vollstaendige Gespraechs-Archiv**.
Append-only JSONL, Zustand je Kontakt aus den Events gefaltet. Leck-geschuetzt; gitignored + Sync-ausgeschlossen.

Events: `nachricht` (id=Meta-Message-ID, richtung ein/aus, text, medien, ts_msg) · `analyse` (KI-Ergebnis je
Kontakt) · `gesehen` (Read-Webhook) · `reminder` (Nachfass gemeldet).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..governance.leak_guard import redact

RICHTUNGEN = ("ein", "aus")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class IgInboxStore:
    def __init__(self, path: str | Path, *, secrets: list[str] | None = None,
                 changelog: Callable[..., None] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []
        self.changelog = changelog
        self._id_cache: set[str] | None = None      # Message-IDs (Dedup), lazy + on-append gepflegt

    # -- schreiben --
    def nachricht_hinzu(self, contact_id: str, contact_name: str, *, richtung: str, text: str,
                        medien: bool, extern_id: str, ts_msg: str = "") -> str:
        """Eine Nachricht (ein/aus) eines Kontakts erfassen. `extern_id` (Meta-Message-ID) dedupliziert.
        Gibt die ID zurueck (== extern_id) oder "" bei fehlender ID/Duplikat."""
        if not extern_id:
            return ""                                # ohne stabile ID kein sicheres Dedup -> ueberspringen
        ids = self._ids()
        if extern_id in ids:
            return ""
        self._append({"ts": _now(), "event": "nachricht", "id": extern_id, "contact_id": str(contact_id),
                      "contact_name": contact_name or str(contact_id), "richtung": richtung,
                      "text": text or "", "medien": bool(medien), "ts_msg": ts_msg or ""})
        ids.add(extern_id)
        return extern_id

    def analyse_setzen(self, contact_id: str, analyse: dict) -> None:
        """KI-Analyse je Kontakt ablegen (Phase 2). `analyse`: collab, zusammenfassung, stand, offene_todos,
        warten_auf, letzte_nachricht_ts, modell."""
        ev = {"ts": _now(), "event": "analyse", "contact_id": str(contact_id)}
        ev.update({k: analyse.get(k) for k in ("collab", "zusammenfassung", "stand", "offene_todos",
                                               "warten_auf", "letzte_nachricht_ts", "modell")})
        self._append(ev)

    def gesehen_setzen(self, contact_id: str, *, seen_ts: str = "", seen_mid: str = "") -> None:
        """Read-Webhook: unsere Nachricht(en) an diesen Kontakt wurden gesehen (Phase 4)."""
        self._append({"ts": _now(), "event": "gesehen", "contact_id": str(contact_id),
                      "seen_ts": seen_ts or _now(), "seen_mid": seen_mid})

    def reminder_setzen(self, contact_id: str) -> None:
        """Vermerkt, dass fuer diesen Kontakt ein Nachfass-Reminder gemeldet wurde (Phase 4, Anti-Spam)."""
        self._append({"ts": _now(), "event": "reminder", "contact_id": str(contact_id), "reminder_ts": _now()})

    # -- lesen (gefaltet) --
    def verlauf(self, contact_id: str, *, limit: int = 500) -> list[dict]:
        """Nachrichten eines Kontakts chronologisch (aelteste zuerst)."""
        cid = str(contact_id)
        msgs = [{k: e.get(k) for k in ("id", "richtung", "text", "medien", "ts_msg", "ts")}
                for e in self._events() if e.get("event") == "nachricht" and str(e.get("contact_id")) == cid]
        msgs.sort(key=lambda m: m.get("ts_msg") or m.get("ts") or "")
        return msgs[-limit:]

    def kontakte(self) -> list[dict]:
        """Gefalteter Stand je Kontakt: Nachrichtenzahlen, letzte Nachricht/Richtung, letzte Analyse,
        gesehen/reminder-Zeitpunkte."""
        k: dict[str, dict] = {}
        for e in self._events():
            ev = e.get("event")
            cid = str(e.get("contact_id") or "")
            if not cid:
                continue
            c = k.setdefault(cid, {"contact_id": cid, "name": cid, "nachrichten": 0, "ein": 0, "aus": 0,
                                   "letzte_ts": None, "letzte_richtung": None, "letzter_text": "",
                                   "analyse": None, "gesehen_ts": None, "reminder_ts": None})
            if ev == "nachricht":
                c["name"] = e.get("contact_name") or c["name"]
                c["nachrichten"] += 1
                c["ein" if e.get("richtung") == "ein" else "aus"] += 1
                ts = e.get("ts_msg") or e.get("ts") or ""
                if not c["letzte_ts"] or ts >= c["letzte_ts"]:
                    c["letzte_ts"] = ts
                    c["letzte_richtung"] = e.get("richtung")
                    c["letzter_text"] = (e.get("text") or "") if not e.get("medien") else "[Medien]"
            elif ev == "analyse":
                c["analyse"] = {kk: e.get(kk) for kk in ("collab", "zusammenfassung", "stand",
                                                         "offene_todos", "warten_auf", "letzte_nachricht_ts",
                                                         "modell", "ts")}
            elif ev == "gesehen":
                c["gesehen_ts"] = e.get("seen_ts") or e.get("ts")
            elif ev == "reminder":
                c["reminder_ts"] = e.get("reminder_ts") or e.get("ts")
        return list(k.values())

    def zustand(self, contact_id: str) -> dict:
        cid = str(contact_id)
        for c in self.kontakte():
            if c["contact_id"] == cid:
                return c
        return {}

    def braucht_analyse(self, contact_id: str) -> bool:
        """True, wenn es Nachrichten neuer als die letzte Analyse gibt (Phase 2: nur dann neu analysieren)."""
        c = self.zustand(contact_id)
        if not c.get("nachrichten"):
            return False
        analyse = c.get("analyse") or {}
        return not analyse or (c.get("letzte_ts") or "") > (analyse.get("letzte_nachricht_ts") or "")

    # -- intern --
    def _ids(self) -> set[str]:
        if self._id_cache is None:
            self._id_cache = {e.get("id") for e in self._events()
                              if e.get("event") == "nachricht" and e.get("id")}
        return self._id_cache

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


class IgInboxSync:
    """Zieht das VOLLE Postfach (ein- und ausgehend) und spiegelt es in den `IgInboxStore`."""

    def __init__(self, *, store: IgInboxStore, reader):
        self.store = store
        self.reader = reader

    def verfuegbar(self) -> bool:
        return self.reader is not None and getattr(self.reader, "verfuegbar", False)

    def voll_sync(self, *, wochen: int = 8, max_konv: int = 50, max_seiten: int = 40,
                  zeit_budget_s: int = 90) -> dict:
        """Alle Threads durchgehen, je Thread bis `wochen` Wochen zurueckblaettern und JEDE Nachricht
        (ein/aus, Text+Medien) ins Archiv spiegeln (dedupliziert). Hartes Zeit-Budget -> antwortet immer;
        `teilweise=True` bei Abbruch (erneut ausloesen, Dedup verhindert Doppel)."""
        if not self.verfuegbar():
            return {"ok": False, "hinweis": "Instagram-Token/IG-User-ID fehlt."}
        import time
        deadline = time.time() + max(10, zeit_budget_s)
        seit_ts = time.time() - max(1, wochen) * 7 * 86400
        own = str(getattr(self.reader, "own_id", ""))
        threads = nachrichten = neu = 0
        abgebrochen = False
        for conv in self.reader.konversationen(limit=max_konv, deadline=deadline):
            if time.time() > deadline:
                abgebrochen = True
                break
            kontakt = self.reader.kontakt(conv) if hasattr(self.reader, "kontakt") else {}
            cid = kontakt.get("id") or conv
            cname = kontakt.get("username") or cid
            threads += 1
            for m in self.reader.nachrichten_seit(conv, seit_ts=seit_ts, max_seiten=max_seiten,
                                                  deadline=deadline):
                nachrichten += 1
                richtung = "aus" if str(m.get("from_id")) == own else "ein"
                medien = not (m.get("text") or "").strip()
                mid = self.store.nachricht_hinzu(cid, cname, richtung=richtung, text=m.get("text", ""),
                                                 medien=medien, extern_id=m.get("id", ""), ts_msg=m.get("ts", ""))
                if mid:
                    neu += 1
            if getattr(self.reader, "unvollstaendig", False):   # Thread durch Fehler/Deadline abgeschnitten
                abgebrochen = True
        # `teilweise`: durch Zeit-Budget ODER transienten Meta-Fehler abgeschnitten -> erneut ausloesen
        # holt (dedupliziert) den Rest.
        teilweise = time.time() > deadline or abgebrochen
        ergebnis = {"ok": True, "threads": threads, "nachrichten": nachrichten, "neu": neu,
                    "teilweise": teilweise}
        fehler = getattr(self.reader, "letzter_fehler", "")
        if teilweise and fehler:
            ergebnis["hinweis"] = ("Scan abgebrochen (Zeit-Budget/Meta-Aussetzer) -> Teilergebnis. Erneut "
                                   "ausloesen holt den Rest (dedupliziert).")
        return ergebnis
