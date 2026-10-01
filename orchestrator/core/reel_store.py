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
from datetime import date, datetime
from pathlib import Path

STATUS = ("wartet", "freigegeben", "abgelehnt", "gepostet", "fehler", "verfallen")
VERFALL_TAGE = 30            # REELS_ROADMAP (CEO 2026-10-01): ohne Entscheidung nach 30 Tagen verfallen
LOESCH_TAGE = 14             # Video abgelehnter/verfallener Reels 14 Tage nach der Entscheidung loeschen
BREMSE_AB = 10               # ab so vielen wartenden Reels schneidet der Nachtlauf kein neues
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
                reels[rid]["ts"] = reels[rid]["eingereicht"] = ev.get("ts")
            elif ev.get("typ") == "status" and rid in reels:
                reels[rid].update({k: v for k, v in ev.items() if k not in ("typ", "id")})
                reels[rid]["entschieden"] = ev.get("ts")
            elif ev.get("typ") == "video_geloescht" and rid in reels:
                reels[rid]["video_geloescht"] = ev.get("ts")
        return reels

    def liste(self, *, status: str | None = None, limit: int = 60) -> list[dict]:
        reels = list(self._falten().values())
        reels.sort(key=lambda r: r.get("ts") or "", reverse=True)
        if status:
            reels = [r for r in reels if r.get("status") == status]
        return reels[:limit]

    def holen(self, rid: str) -> dict | None:
        return self._falten().get(rid)

    def wartend(self) -> int:
        return sum(1 for r in self._falten().values() if r.get("status") == "wartet")

    def bremse(self) -> dict:
        """Nachschub-Bremse fuer den Nachtlauf: ab BREMSE_AB wartenden Reels wird nicht geschnitten."""
        n = self.wartend()
        return {"wartet": n, "bremse": n >= BREMSE_AB, "ab": BREMSE_AB}

    def uebersprungen(self, *, grund: str, wartet: int | None = None) -> None:
        """Nachtlauf hat wegen der Bremse nicht geschnitten -- zaehlt fuer die Betriebs-Wacht als „aktiv“."""
        self._append({"typ": "uebersprungen", "grund": str(grund)[:200], "wartet": wartet})

    def zuletzt_aktiv(self) -> str | None:
        """Juengstes Einreichen ODER bewusstes Ueberspringen (Bremse) -- eine gebremste Nacht ist kein Ausfall."""
        stempel = [e.get("ts") for e in self._events() if e.get("typ") in ("einreichen", "uebersprungen") and e.get("ts")]
        return max(stempel) if stempel else None

    def aufraeumen(self, heute: date | None = None) -> dict:
        """Taeglich: wartende Reels nach VERFALL_TAGE -> `verfallen`; Videos von `abgelehnt`/`verfallen` nach
        LOESCH_TAGE ab der Entscheidung loeschen (gepostete nie). Idempotent. -> {verfallen: [ids], geloescht: [ids]}"""
        heute = heute or date.today()
        out = {"verfallen": [], "geloescht": []}
        for rid, r in self._falten().items():
            if r.get("status") == "wartet" and r.get("eingereicht") and \
                    (heute - date.fromisoformat(r["eingereicht"][:10])).days > VERFALL_TAGE:
                self.status_setzen(rid, "verfallen", grund=f"{VERFALL_TAGE} Tage ohne Entscheidung")
                out["verfallen"].append(rid)
        ordner = self.pfad.parent.resolve()
        for rid, r in self._falten().items():
            if r.get("status") not in ("abgelehnt", "verfallen") or r.get("video_geloescht") or not r.get("entschieden") \
                    or rid in out["verfallen"]:
                continue
            if (heute - date.fromisoformat(r["entschieden"][:10])).days < LOESCH_TAGE:
                continue
            datei = ordner / Path(str(r.get("video") or "")).name           # nur im eigenen Ordner, nur MP4
            if datei.suffix.lower() != ".mp4":
                continue
            try:
                datei.unlink(missing_ok=True)
            except OSError:
                continue
            self._append({"typ": "video_geloescht", "id": rid, "datei": datei.name})
            out["geloescht"].append(rid)
        return out

    def zuletzt_eingereicht(self) -> str | None:
        """Zeitstempel des zuletzt **eingereichten** Reels (None, wenn es keines gibt).

        Bewusst nicht ueber `liste()`: dort ueberschreibt eine spaetere Statusaenderung (freigegeben,
        gepostet) das `ts`. Fuer die Betriebs-Wacht zaehlt aber, wann zuletzt ein Reel **entstanden** ist --
        sonst wuerde die Freigabe eines alten Reels einen ausgefallenen Nachtlauf verdecken."""
        stempel = [e.get("ts") for e in self._events() if e.get("typ") == "einreichen" and e.get("ts")]
        return max(stempel) if stempel else None
