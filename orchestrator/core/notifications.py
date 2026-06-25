"""Proaktive Benachrichtigungen -- durable Outbox fuer Push an den CEO (Telegram).

Jede Stelle im System (Watcher, Researcher, Abteilung ueber LUNA, Selbst-Entwicklung) legt eine Nachricht
in die Outbox; der Telegram-Bot stellt sie **unaufgefordert** zu. Damit meldet sich LUNA von selbst, statt
nur auf Anfragen zu antworten. **Keine Token** -- reine Telegram-API.

Durable (event-sourced JSONL `notifications/log.jsonl`): queued -> sent. Dedupliziert (gleiche Nachricht
nicht mehrfach innerhalb eines Zeitfensters), leck-geschuetzt. Zustellung ueberlebt Neustarts.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from ..governance.leak_guard import redact


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Notifications:
    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []

    def enqueue(self, text: str, *, kategorie: str = "info", quelle: str = "",
                dedup_stunden: float = 12) -> str | None:
        """Nachricht in die Outbox legen. Gibt die ID zurueck (oder None, wenn dedupliziert/leer)."""
        text = (text or "").strip()
        if not text or self._kuerzlich(text, dedup_stunden):
            return None
        nid = "N-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({"ts": _now(), "id": nid, "typ": "queued", "kategorie": kategorie,
                      "quelle": quelle, "text": text})
        return nid

    def pending(self) -> list[dict]:
        """Noch nicht zugestellte Nachrichten, aelteste zuerst."""
        gesendet = {e["id"] for e in self._events() if e.get("typ") == "sent"}
        return [e for e in self._events()
                if e.get("typ") == "queued" and e.get("id") not in gesendet]

    def mark_sent(self, nid: str) -> None:
        self._append({"ts": _now(), "id": nid, "typ": "sent"})

    # -- intern --

    def _kuerzlich(self, text: str, stunden: float) -> bool:
        grenze = datetime.now() - timedelta(hours=stunden)
        for e in self._events():
            if e.get("typ") == "queued" and e.get("text") == text:
                try:
                    if datetime.fromisoformat(e["ts"]) >= grenze:
                        return True
                except (ValueError, KeyError):
                    continue
        return False

    def _append(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps(event, ensure_ascii=False), self.secrets)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _events(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out
