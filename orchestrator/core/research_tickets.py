"""Research-Tickets (event-sourced, append-only) -- Phase 8.5.

Nachverfolgbare Recherche-Auftraege des Researcher (Agent 15): welche Abteilung hat was gefragt --
mit ID, Status, Zeit, Provider, Befund und Quellen. Bewusst **abgegrenzt** von:
- Antraegen (`antraege/`)   -- Entscheidungs-Tickets mit CEO-Freigabe-Lebenszyklus,
- Changelog                 -- Datei-Provenienz,
- Gedaechtnis (`memory/`)   -- Aufgaben-Erinnerung.

Append-only JSONL; Zustand je Ticket wird aus den Events gefaltet. Leck-geschuetzt.
Lebenszyklus:

    offen -> in_arbeit -> erledigt | fehlgeschlagen
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..governance.leak_guard import redact

STATUSES = ("offen", "in_arbeit", "erledigt", "fehlgeschlagen")
_BASE_FIELDS = ("abteilung", "frage", "provider", "stufe", "befund", "quellen", "grund")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ResearchTickets:
    def __init__(self, path: str | Path, *, secrets: list[str] | None = None,
                 changelog: Callable[..., None] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []
        self.changelog = changelog

    # -- schreiben --

    def erstellen(self, frage: str, *, abteilung: str = "Head of Agents") -> str:
        ticket_id = "R-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({
            "ts": _now(), "ticket_id": ticket_id, "event": "offen",
            "abteilung": abteilung, "frage": frage,
        })
        self._log("Researcher", f"Research-Ticket angelegt ({ticket_id}): {frage[:60]}",
                  f"angefragt von {abteilung}", ticket_id)
        return ticket_id

    def in_arbeit(self, ticket_id: str) -> bool:
        return self._transition(ticket_id, "in_arbeit")

    def erledigen(self, ticket_id: str, *, provider: str, befund: str, quellen: list[str] | None = None,
                  stufe: str = "") -> bool:
        ok = self._transition(ticket_id, "erledigt", provider=provider, befund=befund,
                              quellen=list(quellen or []), stufe=stufe)
        if ok:
            self._log("Researcher", f"Research-Ticket erledigt ({ticket_id})",
                      f"Provider {provider}, {len(quellen or [])} Quellen", ticket_id)
        return ok

    def fehlschlag(self, ticket_id: str, *, grund: str = "") -> bool:
        ok = self._transition(ticket_id, "fehlgeschlagen", grund=grund)
        if ok:
            self._log("Researcher", f"Research-Ticket fehlgeschlagen ({ticket_id})",
                      grund or "kein Befund", ticket_id)
        return ok

    # -- lesen --

    def get(self, ticket_id: str) -> dict | None:
        return self._fold().get(ticket_id)

    def list(self, status: str | None = None) -> list[dict]:
        items = list(self._fold().values())
        if status:
            items = [t for t in items if t.get("status") == status]
        items.sort(key=lambda t: t["verlauf"][-1]["ts"] if t.get("verlauf") else "", reverse=True)
        return items

    # -- intern --

    def _append(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps(event, ensure_ascii=False), self.secrets)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _transition(self, ticket_id: str, event: str, **extra) -> bool:
        if event not in STATUSES:
            raise ValueError(f"Unbekannter Status: {event}")
        if self.get(ticket_id) is None:
            return False
        self._append({"ts": _now(), "ticket_id": ticket_id, "event": event, **extra})
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
            tid = e.get("ticket_id")
            if not tid:
                continue
            cur = state.setdefault(tid, {"ticket_id": tid, "verlauf": []})
            for k in _BASE_FIELDS:
                if e.get(k) is not None:
                    cur[k] = e[k]
            cur["status"] = e.get("event", cur.get("status"))
            schritt = {"ts": e.get("ts"), "event": e.get("event")}
            if "grund" in e:
                schritt["grund"] = e["grund"]
            cur["verlauf"].append(schritt)
        return state

    def _log(self, actor: str, was: str, warum: str, betroffen: str) -> None:
        if self.changelog:
            self.changelog(actor, was, warum, betroffen)
