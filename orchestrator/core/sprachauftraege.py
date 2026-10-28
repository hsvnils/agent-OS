"""Sprachauftraege (JARVIS_ALLTAG J2b) -- Warteschlange fuer die lokale LUNA-Stimme auf dem MACO470.

Der Bot legt einen Auftrag an (heute: die Sprechfassung des Morgen-Briefings), der Sprach-Arbeiter auf dem MACO470
(`sprachdienst/worker.py`) holt ihn ueber die LUNA-OS-API (`/api/sprache/*`), spricht ihn mit der festgehaltenen
Stimme C (Qwen3-TTS, lokal) und laedt die MP3 zurueck. Der Bot schickt sie dann per Telegram. Kein Cloud-Dienst.

Append-only JSONL wie die Backoffice-Auftraege; die MP3 liegt daneben als `<id>.mp3` und wird nach `AUFBEWAHRUNG_TAGE`
entfernt (Sprachfassung, jederzeit aus dem Briefing-Text neu erzeugbar).

Lebenszyklus: neu -> in_arbeit -> fertig | fehlgeschlagen -> gesendet (haengende in_arbeit fallen auf neu zurueck).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from ..governance.leak_guard import redact

STATUSES = ("neu", "in_arbeit", "fertig", "fehlgeschlagen", "gesendet")
_FELDER = ("text", "zweck", "modell", "dauer_s", "sprache_s", "grund")
MAX_MP3 = 25 * 1024 * 1024
AUFBEWAHRUNG_TAGE = 30


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class SprachStore:
    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.dir = self.path.parent
        self.secrets = secrets or []

    def anlegen(self, text: str, *, zweck: str) -> str:
        text = (text or "").strip()
        if not text:
            raise ValueError("Leerer Sprachauftrag.")
        sid = "SP-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({"ts": _now(), "id": sid, "event": "neu", "text": text[:6000], "zweck": zweck})
        return sid

    def naechster(self) -> dict | None:
        """Aeltesten neuen Auftrag holen und als in_arbeit markieren (genau ein Worker -> kein Wettlauf)."""
        offen = sorted(self.list("neu"), key=lambda a: a["verlauf"][0]["ts"])
        if not offen:
            return None
        self._transition(offen[0]["id"], "in_arbeit")
        return self.get(offen[0]["id"])

    def fertig(self, sid: str, mp3: bytes, *, modell: str = "", dauer_s: float = 0, sprache_s: float = 0) -> bool:
        a = self.get(sid)
        if a is None or a.get("status") != "in_arbeit":
            return False
        if not mp3 or len(mp3) > MAX_MP3 or not (mp3[:3] == b"ID3" or mp3[:1] == b"\xff"):
            raise ValueError("Keine gueltige MP3.")
        self.dir.mkdir(parents=True, exist_ok=True)
        self.mp3_pfad(sid).write_bytes(mp3)
        return self._transition(sid, "fertig", modell=modell, dauer_s=round(float(dauer_s or 0), 1),
                                sprache_s=round(float(sprache_s or 0), 1))

    def fehlschlag(self, sid: str, *, grund: str) -> bool:
        return self._transition(sid, "fehlgeschlagen", grund=(grund or "unbekannt")[:300])

    def gesendet(self, sid: str) -> bool:
        return self._transition(sid, "gesendet")

    def aufraeumen(self, stunden: float = 1, jetzt: datetime | None = None) -> int:
        """Haengende in_arbeit (Worker abgestuerzt) zurueck auf neu; alte MP3-Dateien entfernen."""
        jetzt = jetzt or datetime.now()
        n = 0
        for a in self.list("in_arbeit"):
            if datetime.fromisoformat(a["verlauf"][-1]["ts"]) < jetzt - timedelta(hours=stunden):
                self._transition(a["id"], "neu", grund="haengend, erneut eingereiht")
                n += 1
        grenze = (jetzt - timedelta(days=AUFBEWAHRUNG_TAGE)).timestamp()
        for p in self.dir.glob("SP-*.mp3") if self.dir.is_dir() else ():
            if p.stat().st_mtime < grenze:
                p.unlink(missing_ok=True)
        return n

    # -- Lesen -----------------------------------------------------------------------------------------------------

    def mp3_pfad(self, sid: str) -> Path:
        return self.dir / f"{Path(sid).name}.mp3"

    def get(self, sid: str) -> dict | None:
        return self._fold().get(sid)

    def zum_zweck(self, zweck: str) -> dict | None:
        """Juengster Auftrag zu einem Zweck (z. B. `briefing:2026-10-29`)."""
        treffer = [a for a in self.list() if a.get("zweck") == zweck]
        return treffer[0] if treffer else None

    def list(self, status: str | None = None) -> list[dict]:
        items = [a for a in self._fold().values() if not status or a.get("status") == status]
        items.sort(key=lambda a: a["verlauf"][0]["ts"], reverse=True)
        return items

    # -- intern ----------------------------------------------------------------------------------------------------

    def _transition(self, sid: str, event: str, **extra) -> bool:
        if event not in STATUSES:
            raise ValueError(f"Unbekannter Status: {event}")
        if sid not in self._fold():
            return False
        self._append({"ts": _now(), "id": sid, "event": event, **{k: v for k, v in extra.items() if v not in (None, "")}})
        return True

    def _append(self, event: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(redact(json.dumps(event, ensure_ascii=False), self.secrets) + "\n")

    def _fold(self) -> dict[str, dict]:
        state: dict[str, dict] = {}
        if not self.path.exists():
            return state
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = e.get("id")
            if not sid:
                continue
            cur = state.setdefault(sid, {"id": sid, "verlauf": []})
            for k in _FELDER:
                if e.get(k) is not None:
                    cur[k] = e[k]
            cur["status"] = e.get("event", cur.get("status"))
            cur["verlauf"].append({"ts": e.get("ts"), "event": e.get("event")})
        return state


SPAETESTENS = 10          # Uhr: bis dahin muss die Sprachfassung des Morgen-Briefings fertig sein, sonst bleibt es beim Text


def briefing_schritt(store: SprachStore, datum: str, jetzt: datetime, briefing_text: str | None) -> tuple[str, dict | None]:
    """Ein Minuten-Schritt fuer das Morgen-Briefing als Sprachnachricht. `briefing_text` = heutige Sprechfassung (None,
    solange das Briefing noch nicht raus ist). Rueckgabe (aktion, auftrag): `senden` (MP3 liegt bereit), `hinweis`
    (heute keine Sprachfassung -- Grund im Auftrag) oder `""` (nichts zu tun). Legt den Auftrag selbst an und bricht
    nach `SPAETESTENS` Uhr ab; einmal je Tag (Zweck `briefing:<datum>`)."""
    zweck = f"briefing:{datum}"
    a = store.zum_zweck(zweck)
    if a is None:
        if briefing_text and jetzt.hour < SPAETESTENS:
            store.anlegen(briefing_text, zweck=zweck)
        return "", None
    if a["status"] == "fertig":
        return "senden", a
    if a["status"] in ("neu", "in_arbeit") and jetzt.hour >= SPAETESTENS:
        store.fehlschlag(a["id"], grund=f"bis {SPAETESTENS}:00 Uhr nicht fertig (MACO470 aus oder ausgelastet?)")
        a = store.get(a["id"])
    return ("hinweis", a) if a["status"] == "fehlgeschlagen" else ("", None)
