"""Zentrales Agenten-Aktivitaetsprotokoll (Antrag adc5).

Ein einziger, durchsuchbarer Ereignis-Strom ueber das, was die Agenten tun -- zur laufenden Ueberwachung
von Prozessen und Effizienz. Bewusst **kostenlos** und leichtgewichtig: event-sourced JSONL
(`aktivitaet/log.jsonl`), kein LLM, keine externe DB (im Gegensatz zum CFO-Kostenvoranschlag, der eine
Cloud-DB skizzierte -- hier nicht noetig, da die bestehende Store-Architektur ausreicht).

Gespeist wird das Protokoll **zentral** an den vorhandenen Engstellen (Changelog-Callback fuer den
Antrags-Lebenszyklus/Execution, Fachagenten-Delegation) -- nicht durch Instrumentierung jedes Agenten.
Leck-geschuetzt (redact) und vom Code-Sync ausgenommen (Live-Daten).
"""
from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from ..governance.leak_guard import redact


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Aktivitaet:
    """Append-only JSONL: je Eintrag Zeitpunkt, Akteur (Agent/Rolle), Aktion, Kategorie, Detail, Bezug."""

    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []

    def log(self, akteur: str, aktion: str, *, kategorie: str = "aktion",
            detail: str = "", bezug: str = "") -> str:
        """Ein Ereignis protokollieren. Gibt die Ereignis-ID zurueck (leerer Akteur/Aktion -> kein Eintrag)."""
        akteur = (akteur or "").strip()
        aktion = (aktion or "").strip()
        if not akteur and not aktion:
            return ""
        eid = "AK-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({"ts": _now(), "id": eid, "akteur": akteur, "aktion": aktion,
                      "kategorie": kategorie, "detail": (detail or "")[:500], "bezug": (bezug or "")[:80]})
        return eid

    def letzte(self, n: int = 20, *, akteur: str | None = None,
               kategorie: str | None = None) -> list[dict]:
        """Die juengsten Eintraege (neueste zuerst), optional nach Akteur/Kategorie gefiltert."""
        out = self._events()
        if akteur:
            a = akteur.lower()
            out = [e for e in out if a in (e.get("akteur", "") or "").lower()]
        if kategorie:
            out = [e for e in out if e.get("kategorie") == kategorie]
        return list(reversed(out))[:max(1, n)]

    def seit(self, start: datetime) -> list[dict]:
        return [e for e in self._events() if _ts(e) and _ts(e) >= start]

    def zusammenfassung(self, *, stunden: float = 24) -> dict:
        """Kompakte Effizienz-/Prozess-Sicht: Anzahl je Akteur und je Kategorie im Zeitfenster."""
        start = datetime.now() - timedelta(hours=stunden)
        fenster = self.seit(start)
        return {
            "stunden": stunden,
            "gesamt": len(fenster),
            "je_akteur": dict(Counter(e.get("akteur", "?") for e in fenster).most_common(15)),
            "je_kategorie": dict(Counter(e.get("kategorie", "?") for e in fenster).most_common()),
        }

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


def _ts(e: dict):
    try:
        return datetime.fromisoformat(e.get("ts", ""))
    except (ValueError, TypeError):
        return None
