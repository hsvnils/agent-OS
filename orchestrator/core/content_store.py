"""content_ops -- generischer Supabase-gestuetzter Store mit lokalem Offline-Cache.

Fuer die geteilten content_ops-Tabellen (trend_signals, ideas, content_drafts, sources ...): **Supabase = DB**,
lokaler JSONL-Cache als Offline-Fallback. Lesen bevorzugt Supabase (aktualisiert Cache); Status-/Teil-Updates
via **PATCH** (nicht Upsert -> keine NOT-NULL-Probleme). Leck-geschuetzt. Ein Store je Tabelle (parametriert).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..governance.leak_guard import redact

# Feld-Listen + gueltige Status je content_ops-Tabelle (aus dem HCC-Schema uebernommen).
TREND_FELDER = "id,title,description,source_type,source_name,source_url,relevance,score,status,tags,created_at,updated_at"
TREND_STATUSES = ("new", "reviewing", "draft_created", "approved", "published", "ignored")
IDEA_FELDER = "id,title,description,status,category,tags,source_type,ai_summary,next_steps,created_at,updated_at"
IDEA_STATUSES = ("inbox", "sorted", "planned", "in_progress", "done", "archived")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ContentStore:
    def __init__(self, client, tabelle: str, felder: str, cache_path: str | Path, *,
                 statuses: tuple = (), order: str = "created_at.desc", secrets: list[str] | None = None):
        self.client = client
        self.tabelle = tabelle
        self.felder = felder
        self.cache_path = Path(cache_path)
        self.statuses = tuple(statuses)
        self.order = order
        self.secrets = secrets or []

    def list(self, limit: int = 100) -> list[dict]:
        """Neueste zuerst; primaer aus Supabase (Cache-Update), Fallback lokaler Cache."""
        if self.client is not None and self.client.verfuegbar():
            r = self.client.select(self.tabelle,
                                   params=f"select={self.felder}&order={self.order}&limit={int(limit)}")
            if r.get("ok"):
                rows = r.get("rows", [])
                self._cache_schreiben(rows)
                return rows
        return self._cache_lesen()[:limit]

    def status_setzen(self, rid: str, status: str) -> dict:
        if self.statuses and status not in self.statuses:
            return {"ok": False, "fehler": f"Unbekannter Status: {status}"}
        if self.client is None or not self.client.verfuegbar():
            return {"ok": False, "fall_b": True,
                    "hinweis": "Supabase nicht verfuegbar -- Statuswechsel offline nicht moeglich."}
        r = self.client.update(self.tabelle, {"status": status, "updated_at": _now()}, params=f"id=eq.{rid}")
        if r.get("ok"):
            self._cache_status(rid, status)
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

    def _cache_status(self, rid: str, status: str) -> None:
        rows = self._cache_lesen()
        for row in rows:
            if row.get("id") == rid:
                row["status"] = status
        self._cache_schreiben(rows)
