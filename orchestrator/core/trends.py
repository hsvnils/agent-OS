"""content_ops -- Trends (K1): Supabase-gestuetzter Store mit lokalem Offline-Cache.

Neue Architektur (Konsolidierung in LUNA-OS): **Supabase = primaere DB**, luna-os haelt eine lokale
Cache-/Fallback-Kopie (JSONL). Lesen bevorzugt Supabase und aktualisiert den Cache; ist Supabase nicht
erreichbar, wird aus dem Cache gelesen. Schreiben (Statuswechsel) geht per Upsert nach Supabase + Cache.
Leck-geschuetzt (Cache via redact). Tabelle `trend_signals` (aus dem alten HCC uebernommen).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..governance.leak_guard import redact

TREND_STATUSES = ("new", "reviewing", "draft_created", "approved", "published", "ignored")
_FELDER = "id,title,description,source_type,source_name,source_url,relevance,score,status,tags,created_at,updated_at"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class TrendStore:
    def __init__(self, client, cache_path: str | Path, *, secrets: list[str] | None = None):
        self.client = client            # SupabaseClient
        self.cache_path = Path(cache_path)
        self.secrets = secrets or []

    def list(self, limit: int = 100) -> list[dict]:
        """Neueste Trends zuerst. Primaer aus Supabase (Cache wird aktualisiert); Fallback: lokaler Cache."""
        if self.client is not None and self.client.verfuegbar():
            r = self.client.select("trend_signals",
                                   params=f"select={_FELDER}&order=created_at.desc&limit={int(limit)}")
            if r.get("ok"):
                rows = r.get("rows", [])
                self._cache_schreiben(rows)
                return rows
        return self._cache_lesen()[:limit]

    def status_setzen(self, trend_id: str, status: str) -> dict:
        if status not in TREND_STATUSES:
            return {"ok": False, "fehler": f"Unbekannter Status: {status}"}
        if self.client is None or not self.client.verfuegbar():
            return {"ok": False, "fall_b": True, "hinweis": "Supabase nicht verfuegbar -- Statuswechsel offline nicht moeglich."}
        r = self.client.upsert("trend_signals", {"id": trend_id, "status": status, "updated_at": _now()},
                               on_conflict="id")
        if r.get("ok"):
            self._cache_status(trend_id, status)
        return r

    # -- lokaler Cache --
    def _cache_schreiben(self, rows: list[dict]) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(redact(json.dumps(row, ensure_ascii=False), self.secrets) + "\n")
        except Exception:
            pass

    def _cache_lesen(self) -> list[dict]:
        if not self.cache_path.exists():
            return []
        out = []
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out

    def _cache_status(self, trend_id: str, status: str) -> None:
        rows = self._cache_lesen()
        for row in rows:
            if row.get("id") == trend_id:
                row["status"] = status
        self._cache_schreiben(rows)
