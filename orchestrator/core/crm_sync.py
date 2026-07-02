"""Rueckschreiben (Supabase -> luna-os): holt im HCC gemachte CRM-Aenderungen und wendet sie lokal an.

Gegenstueck zum Write-Through (`crm_projection`). Zusammen ergibt das die **bidirektionale 1:1**-Synchron-
isierung der geteilten CRM-Basis. **Vorrang luna-os:** wir uebernehmen nur Zeilen mit `updated_by='hcc'` und
projizieren sie NICHT zurueck (Loop-Schutz -- Supabase hat die Aenderung ja schon). Cursor-basiert
(`updated_at`), damit wir keine Aenderung doppelt anwenden. Best-effort: Supabase-Ausfall -> kein Crash.
"""
from __future__ import annotations

from pathlib import Path


class CrmSync:
    def __init__(self, store, client, *, cursor_path: str | Path):
        self.store = store            # CrmStore
        self.client = client          # SupabaseClient
        self.cursor_path = Path(cursor_path)

    def _cursor(self) -> str:
        try:
            return self.cursor_path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""

    def _set_cursor(self, ts: str) -> None:
        try:
            self.cursor_path.parent.mkdir(parents=True, exist_ok=True)
            self.cursor_path.write_text(ts, encoding="utf-8")
        except Exception:
            pass

    def pull(self) -> dict:
        if not self.client.verfuegbar():
            return {"ok": False, "fall_b": True}
        cur = self._cursor()
        gt = f"&updated_at=gt.{cur}" if cur else ""
        uebernommen, maxts = 0, cur

        comp = self.client.select(
            "crm_companies",
            params="updated_by=eq.hcc&select=firma,status,updated_at&order=updated_at.asc" + gt)
        for row in comp.get("rows", []) if comp.get("ok") else []:
            self.store.uebernehmen_status_extern(row.get("firma"), row.get("status"))
            uebernommen += 1
            maxts = max(maxts or "", row.get("updated_at") or "")

        todo = self.client.select(
            "crm_todos",
            params="updated_by=eq.hcc&status=eq.erledigt&select=id,updated_at&order=updated_at.asc" + gt)
        for row in todo.get("rows", []) if todo.get("ok") else []:
            self.store.uebernehmen_todo_extern(row.get("id"), "erledigt")
            uebernommen += 1
            maxts = max(maxts or "", row.get("updated_at") or "")

        if maxts and maxts != cur:
            self._set_cursor(maxts)
        return {"ok": True, "uebernommen": uebernommen}
