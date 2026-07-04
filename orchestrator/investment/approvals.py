"""Freigabe-Speicher fuer 1-Tap-Entscheidungen per Telegram (Ja/Nein-Buttons, Schritt 5).

Entkoppelt **Erzeugung** (ein Tool/Flow legt eine Freigabe-Anfrage an) von **Zustellung** (der Bot-Loop
schickt offene, noch nicht gesendete Anfragen als Inline-Keyboard) -- gleiches Muster wie die Notifications-
Outbox. Append-only JSONL, Zustand je `id` gefaltet (spaetere Ereignisse ueberschreiben Felder). Der Klick
(`callback_query`) entscheidet die Anfrage; `entscheiden()` ist idempotent (eine Anfrage wird nur einmal
entschieden). Kein Geld/kein Trade hier drin -- nur der Entscheidungs-Kanal.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from ..governance.leak_guard import redact


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ApprovalStore:
    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []

    def add(self, typ: str, payload: dict, *, frage: str) -> str:
        aid = "APV-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({"ts": _now(), "id": aid, "typ": typ, "payload": payload, "frage": frage,
                      "status": "offen", "gesendet": False})
        return aid

    def get(self, aid: str) -> dict | None:
        return self._fold().get(aid)

    def offen(self) -> list[dict]:
        return [a for a in self._fold().values() if a.get("status") == "offen"]

    def pending_unsent(self) -> list[dict]:
        return [a for a in self._fold().values() if a.get("status") == "offen" and not a.get("gesendet")]

    def mark_sent(self, aid: str) -> None:
        self._append({"ts": _now(), "id": aid, "gesendet": True})

    def entscheiden(self, aid: str, ja: bool, *, akteur: str = "CEO", ergebnis: str | None = None) -> dict | None:
        """Idempotent: entscheidet nur eine noch offene Anfrage. -> gefalteter Stand oder None."""
        a = self.get(aid)
        if not a or a.get("status") != "offen":
            return None
        self._append({"ts": _now(), "id": aid, "status": ("genehmigt" if ja else "abgelehnt"),
                      "akteur": akteur, "ergebnis": ergebnis})
        return self.get(aid)

    # -- intern --
    def _fold(self) -> dict[str, dict]:
        stand: dict[str, dict] = {}
        for e in self._events():
            aid = e.get("id")
            if not aid:
                continue
            cur = stand.setdefault(aid, {})
            for k, v in e.items():
                if k != "ts":
                    cur[k] = v
            cur["ts"] = e.get("ts")
        return stand

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
