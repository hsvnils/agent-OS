"""Reel-Freigabe-Store (Reel-Pipeline Stufe C) -- event-sourced JSONL.

Haelt die vom Mac-Cutter eingereichten Tages-Reels, die auf die CEO-Freigabe warten (Auto-Posten =
Oeffentlichkeit = CEO-Tor, AGENTS.md 4). Der Zustand je Reel wird aus den Events gefaltet. Nur Tracken/
Freigeben -- der eigentliche Facebook-Upload (Stufe D) liest die **freigegebenen** Reels.

Status-Lebenszyklus:  wartet -> freigegeben | abgelehnt ; nach dem Upload -> gepostet | fehler.
Append-only JSONL; gitignored + vom NAS-Sync ausgeschlossen (Live-Daten).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

STATUS = ("wartet", "freigegeben", "abgelehnt", "gepostet", "fehler")
_FELDER = ("id", "datum", "thema", "caption", "video", "spiele", "dauer_sek", "clips", "status")


class ReelStore:
    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self.pfad.parent.mkdir(parents=True, exist_ok=True)

    def _append(self, ev: dict) -> None:
        ev["ts"] = datetime.now().isoformat(timespec="seconds")
        with self.pfad.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def _events(self) -> list[dict]:
        if not self.pfad.exists():
            return []
        out: list[dict] = []
        for line in self.pfad.read_text("utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
        return out

    def einreichen(self, *, datum: str, thema: str, caption: str, video: str, rid: str | None = None,
                   spiele: list | None = None, dauer_sek: float | None = None,
                   clips: list | None = None) -> str:
        """Neues Reel im Status 'wartet' anlegen -> Reel-ID."""
        rid = rid or uuid.uuid4().hex[:12]
        self._append({"typ": "einreichen", "id": rid, "datum": datum, "thema": thema, "caption": caption,
                      "video": video, "spiele": spiele or [], "dauer_sek": dauer_sek,
                      "clips": clips or [], "status": "wartet"})
        return rid

    def status_setzen(self, rid: str, status: str, **felder) -> bool:
        """Status (+ optionale Felder wie fb_video_id/fehler) fortschreiben. False bei unbekanntem Status
        oder unbekannter Reel-ID."""
        if status not in STATUS or rid not in self._falten():
            return False
        self._append({"typ": "status", "id": rid, "status": status,
                      **{k: v for k, v in felder.items() if v is not None}})
        return True

    def _falten(self) -> dict[str, dict]:
        reels: dict[str, dict] = {}
        for ev in self._events():
            rid = ev.get("id")
            if not rid:
                continue
            if ev.get("typ") == "einreichen":
                reels[rid] = {k: ev.get(k) for k in _FELDER}
                reels[rid]["ts"] = ev.get("ts")
            elif ev.get("typ") == "status" and rid in reels:
                reels[rid].update({k: v for k, v in ev.items() if k not in ("typ", "id")})
        return reels

    def liste(self, *, status: str | None = None, limit: int = 60) -> list[dict]:
        reels = list(self._falten().values())
        reels.sort(key=lambda r: r.get("ts") or "", reverse=True)
        if status:
            reels = [r for r in reels if r.get("status") == status]
        return reels[:limit]

    def holen(self, rid: str) -> dict | None:
        return self._falten().get(rid)
