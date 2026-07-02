"""Write-Through-Projektor: spiegelt den aktuellen CRM-Stand in die geteilten Supabase-Tabellen.

LUNAs `CrmStore` bleibt Quelle + Offline-Fallback (lokales Event-Log). Nach jedem Ereignis ruft der Store
best-effort diesen Projektor, der die gefaltete Zeile per **Upsert** nach Supabase schreibt (relationale
Projektion, Option A). Bei Supabase-Ausfall schlaegt der Upsert fehl -> der Store faengt das ab und arbeitet
lokal weiter (Abgleich spaeter). Alle LUNA-Zeilen tragen `updated_by='luna'` (Vorrang/Nachvollziehbarkeit).

Duck-typed Schnittstelle (der Store kennt nur `.firma/.nachricht/.todo`): so bleibt `crm.py` frei von einer
Supabase-Abhaengigkeit; Tests koennen einen Fake-Projektor injizieren.
"""
from __future__ import annotations


def _ohne_none(row: dict) -> dict:
    return {k: v for k, v in row.items() if v is not None}


class SupabaseCrmProjection:
    def __init__(self, client):
        self.client = client  # SupabaseClient (oder MockSupabaseClient in Tests)

    def firma(self, row: dict) -> dict:
        return self.client.upsert("crm_companies", _ohne_none(row), on_conflict="ref")

    def nachricht(self, row: dict) -> dict:
        return self.client.upsert("crm_messages", _ohne_none(row), on_conflict="extern_id")

    def todo(self, row: dict) -> dict:
        return self.client.upsert("crm_todos", _ohne_none(row), on_conflict="id")
