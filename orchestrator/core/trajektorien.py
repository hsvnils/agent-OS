"""Phase 26 -- Trajektorien-Store ("was hat funktioniert").

Speichert erfolgreiche Ablaeufe (Aufgabe -> Vorgehen -> Ergebnis) als event-sourced JSONL und findet zu einer
neuen Aufgabe **aehnliche vergangene Trajektorien** per BM25 (`ranking`). So kann LUNA aus bewaehrten
Loesungswegen schoepfen, ohne teure Wiederholung -- lokal, token-frugal, keine Datenausleitung.

Gleiches Muster wie `brain.Brain`: append-only, Leck-Schutz beim Schreiben, Store wird vom NAS-Sync
ausgeschlossen und ist gitignored.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from ..governance.leak_guard import redact
from . import ranking


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class TrajektorienStore:
    """Erfolgreiche Ablaeufe als JSONL. Items: typ 'trajektorie' (aufgabe/vorgehen/ergebnis/erfolg/tags); 'geloescht'."""

    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []

    def merken(self, aufgabe: str, vorgehen: str, *, ergebnis: str = "", erfolg: bool = True,
               tags: list[str] | None = None, ref: str = "") -> str:
        """Speichert eine Trajektorie. Dedup: gleiche `ref` ODER identische (aufgabe+vorgehen)."""
        aufgabe = (aufgabe or "").strip()
        vorgehen = (vorgehen or "").strip()
        if not aufgabe or not vorgehen:
            return ""
        for e in self._items():
            if (ref and e.get("ref") == ref) or (e.get("aufgabe") == aufgabe and e.get("vorgehen") == vorgehen):
                return e.get("id", "")
        tid = "T-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({"ts": _now(), "id": tid, "typ": "trajektorie", "aufgabe": aufgabe,
                      "vorgehen": vorgehen, "ergebnis": (ergebnis or "").strip(), "erfolg": bool(erfolg),
                      "tags": tags or [], "ref": ref})
        return tid

    def vergessen(self, tid: str) -> bool:
        if not any(e.get("id") == tid for e in self._items()):
            return False
        self._append({"ts": _now(), "typ": "geloescht", "id": tid})
        return True

    def list(self, limit: int = 50) -> list[dict]:
        return list(reversed(self._items()))[:limit]

    def aehnliche(self, aufgabe: str, limit: int = 5, *, nur_erfolg: bool = True) -> list[dict]:
        """Findet zu `aufgabe` aehnliche vergangene Trajektorien per BM25 (Aufgabe hoeher gewichtet)."""
        items = [e for e in self._items() if (e.get("erfolg", True) or not nur_erfolg)]
        if not items:
            return []
        items = sorted(items, key=lambda e: e.get("ts", ""), reverse=True)
        dokumente: list[tuple] = []
        for e in items:
            toks = (ranking.tokenize(e.get("aufgabe", "")) * 2      # Aufgabe doppelt gewichtet
                    + ranking.tokenize(e.get("vorgehen", ""))
                    + ranking.tokenize(" ".join(e.get("tags", []))))
            dokumente.append((e.get("id"), toks))
        rang = ranking.bm25_ranking(aufgabe, dokumente)
        nach_id = {e.get("id"): e for e in items}
        return [nach_id[k] for k, _ in rang[:limit] if k in nach_id]

    # -- intern --

    def _items(self) -> list[dict]:
        evs = self._events()
        geloescht = {e.get("id") for e in evs if e.get("typ") == "geloescht"}
        return [e for e in evs if e.get("typ") == "trajektorie" and e.get("id") not in geloescht]

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
