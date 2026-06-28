"""Your Second Brain -- durchsuchbare persoenliche Wissensbasis (event-sourced JSONL).

LUNA merkt sich Wissen (Notizen, Befunde, Snapshots) und durchsucht es lexikalisch. Die
quellen-uebergreifende Suche (intern + Gmail + Kalender + Drive) orchestriert das Tool `brain_suchen`
in `hoa_tools` ueber die vorhandenen Stores und Google-Tools -- dieses Modul haelt den eigenen
Wissensspeicher und die lexikalische Suche.

Token-frugal: reine lexikalische Suche (Term-Overlap + Titel-/Recency-Gewichtung), kein externer Dienst,
kein LLM. Leck-geschuetzt beim Schreiben. Store wird vom NAS-Sync ausgeschlossen und ist gitignored.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from ..governance.leak_guard import redact

_WORT = re.compile(r"[\wäöüß]+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [w for w in _WORT.findall((text or "").lower()) if len(w) > 2]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Brain:
    """Wissensbasis als event-sourced JSONL. Items: typ 'wissen' (titel/text/tags/quelle/ref); 'geloescht'."""

    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []

    def merken(self, text: str, *, titel: str = "", tags: list[str] | None = None,
               quelle: str = "notiz", ref: str = "") -> str:
        """Speichert ein Wissens-Item. Dedup: gleiche `ref` ODER identischer Text -> kein Duplikat."""
        text = (text or "").strip()
        if not text:
            return ""
        for e in self._items():
            if (ref and e.get("ref") == ref) or e.get("text") == text:
                return e.get("id", "")
        bid = "B-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({"ts": _now(), "id": bid, "typ": "wissen", "titel": (titel or "").strip(),
                      "text": text, "tags": tags or [], "quelle": quelle, "ref": ref})
        return bid

    def vergessen(self, bid: str) -> bool:
        if not any(e.get("id") == bid for e in self._items()):
            return False
        self._append({"ts": _now(), "typ": "geloescht", "id": bid})
        return True

    def list(self, limit: int = 50) -> list[dict]:
        return list(reversed(self._items()))[:limit]

    def suchen(self, frage: str, limit: int = 8) -> list[dict]:
        """Lexikalische Suche: Term-Overlap (Titel doppelt gewichtet), dann Aktualitaet."""
        q = set(_tokens(frage))
        if not q:
            return []
        scored: list[tuple[int, dict]] = []
        for e in self._items():
            titel_tokens = set(_tokens(e.get("titel", "")))
            text_tokens = set(_tokens(e.get("text", "")))
            tag_tokens = {t.lower() for t in e.get("tags", [])}
            treffer = len(q & (titel_tokens | text_tokens | tag_tokens))
            if not treffer:
                continue
            score = treffer + len(q & titel_tokens) * 2
            scored.append((score, e))
        scored.sort(key=lambda x: (x[0], x[1].get("ts", "")), reverse=True)
        return [e for _, e in scored[:limit]]

    # -- intern --

    def _items(self) -> list[dict]:
        evs = self._events()
        geloescht = {e.get("id") for e in evs if e.get("typ") == "geloescht"}
        return [e for e in evs if e.get("typ") == "wissen" and e.get("id") not in geloescht]

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
