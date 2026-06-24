"""Antrags-/Freigabe-Workflow (event-sourced, append-only).

Ein Antrag ist die einzige Bruecke fuer Aenderungen/Beschaffungen/Ideen: Abteilungen/HoA reichen ein,
der CEO entscheidet. Lebenszyklus:

    eingereicht -> freigegeben | abgelehnt ; freigegeben -> in_umsetzung -> erledigt | fehlgeschlagen

Append-only JSONL; der Zustand je Antrag wird aus den Events gefaltet. Leck-geschuetzt. Abgegrenzt von
Changelog (Datei-Provenienz) und Gedaechtnis (Aufgaben-Erinnerung). Jede Transition kann einen
Changelog-Eintrag ausloesen (Callback). Siehe PHASE6_PLAN.md / governance/antraege.md.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..governance.leak_guard import redact

STATUSES = (
    "eingereicht", "freigegeben", "abgelehnt", "in_umsetzung", "erledigt", "fehlgeschlagen",
)
_BASE_FIELDS = ("von", "titel", "beschreibung", "kategorie", "betroffen")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Antraege:
    def __init__(self, path: str | Path, *, secrets: list[str] | None = None,
                 changelog: Callable[..., None] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []
        self.changelog = changelog

    # -- schreiben --

    def stellen(self, titel: str, beschreibung: str, *, von: str = "Head of Agents",
                kategorie: str = "", betroffen: str = "") -> str:
        antrag_id = "A-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({
            "ts": _now(), "antrag_id": antrag_id, "event": "eingereicht", "von": von,
            "titel": titel, "beschreibung": beschreibung, "kategorie": kategorie, "betroffen": betroffen,
        })
        self._log("Head of Agents", f"Antrag eingereicht ({antrag_id}): {titel}",
                  f"von {von}", betroffen or "-")
        return antrag_id

    def freigeben(self, antrag_id: str, *, akteur: str = "CEO") -> bool:
        ok = self._transition(antrag_id, "freigegeben", akteur=akteur)
        if ok:
            self._log("CEO", f"Antrag freigegeben: {antrag_id}", "CEO-Freigabe ueber HoA", antrag_id)
        return ok

    def ablehnen(self, antrag_id: str, *, grund: str = "", akteur: str = "CEO") -> bool:
        ok = self._transition(antrag_id, "abgelehnt", grund=grund, akteur=akteur)
        if ok:
            self._log("CEO", f"Antrag abgelehnt: {antrag_id}", grund or "CEO-Entscheidung", antrag_id)
        return ok

    def status_setzen(self, antrag_id: str, status: str, **extra) -> bool:
        """Fuer Phase 7: in_umsetzung/erledigt/fehlgeschlagen."""
        return self._transition(antrag_id, status, **extra)

    # -- lesen --

    def get(self, antrag_id: str) -> dict | None:
        return self._fold().get(antrag_id)

    def list(self, status: str | None = None) -> list[dict]:
        items = list(self._fold().values())
        if status:
            items = [a for a in items if a.get("status") == status]
        items.sort(key=lambda a: a["verlauf"][-1]["ts"] if a.get("verlauf") else "", reverse=True)
        return items

    # -- intern --

    def _append(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps(event, ensure_ascii=False), self.secrets)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _transition(self, antrag_id: str, event: str, **extra) -> bool:
        if event not in STATUSES:
            raise ValueError(f"Unbekannter Status: {event}")
        if self.get(antrag_id) is None:
            return False
        self._append({"ts": _now(), "antrag_id": antrag_id, "event": event, **extra})
        return True

    def _events(self) -> list[dict]:
        if not self.path.exists():
            return []
        out: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def _fold(self) -> dict[str, dict]:
        state: dict[str, dict] = {}
        for e in self._events():
            aid = e.get("antrag_id")
            if not aid:
                continue
            cur = state.setdefault(aid, {"antrag_id": aid, "verlauf": []})
            for k in _BASE_FIELDS:
                if e.get(k):
                    cur[k] = e[k]
            cur["status"] = e.get("event", cur.get("status"))
            schritt = {"ts": e.get("ts"), "event": e.get("event")}
            for k in ("grund", "akteur"):
                if k in e:
                    schritt[k] = e[k]
            cur["verlauf"].append(schritt)
        return state

    def _log(self, actor: str, was: str, warum: str, betroffen: str) -> None:
        if self.changelog:
            self.changelog(actor, was, warum, betroffen)
