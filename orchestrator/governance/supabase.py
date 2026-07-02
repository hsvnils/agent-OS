"""Supabase-Anbindung (Capability-Muster) fuer die geteilte Datenbasis mit dem HCC.

luna-os ist ein vertrauenswuerdiger Server-Backend und nutzt den **service_role**-Key (umgeht RLS). Nur fuer
die GETEILTEN Team-Flaechen (CRM; spaeter Content/Cutter-Status) -- luna-os-Interna (Antraege/Watch/Memory)
bleiben rein lokal. Schreiben ist **write-through**: primaer nach Supabase, der lokale Store bleibt Quelle +
Offline-Fallback. Ohne Keys -> **Fall-B** (kein Crash, kein Schreiben). Secrets nie im Klartext (Leck-Schutz
im Tool-Layer). Der HTTP-Aufruf ist **injizierbar** -> Self-Checks ohne Netz/Keys gegen Mock-Daten.

Duenne PostgREST-Anbindung (select/upsert/delete) via urllib -- keine neue Dependency.
Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request


def _http(url: str, *, method: str = "GET", headers: dict | None = None, data: bytes | None = None,
          timeout: int = 15):
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8")
        return json.loads(body) if body.strip() else None


class SupabaseAuth:
    def __init__(self, url: str = "", service_key: str = ""):
        self.url = (url or "").rstrip("/")
        self.service_key = service_key or ""

    @classmethod
    def from_env(cls, env: dict | None = None) -> "SupabaseAuth":
        import os
        e = env if env is not None else os.environ
        return cls(url=(e.get("SUPABASE_URL") or "").strip(),
                   service_key=(e.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip())

    def verfuegbar(self) -> bool:
        return bool(self.url and self.service_key)


class SupabaseClient:
    """Duenne PostgREST-Anbindung: `upsert` / `select` / `delete`. `fetch` injizierbar (Tests)."""

    def __init__(self, auth: SupabaseAuth, *, fetch=None):
        self.auth = auth
        self._fetch = fetch or _http

    def verfuegbar(self) -> bool:
        return self.auth.verfuegbar()

    @staticmethod
    def fall_b() -> dict:
        return {"ok": False, "fall_b": True,
                "hinweis": "Supabase nicht konfiguriert -- SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in .env "
                           "noetig (CISO-Freigabe, CEO-Tor). Nur service_role, nie in den Chat/Browser."}

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"apikey": self.auth.service_key, "Authorization": "Bearer " + self.auth.service_key,
             "Content-Type": "application/json"}
        if extra:
            h.update(extra)
        return h

    def upsert(self, tabelle: str, rows, *, on_conflict: str | None = None) -> dict:
        """Insert/Update (merge-duplicates) einer oder mehrerer Zeilen. `on_conflict` = Spalte(n) fuer den
        Upsert-Schluessel (z. B. 'ref'). Best-effort: Fehler werden zurueckgegeben, nicht geworfen."""
        if not self.verfuegbar():
            return self.fall_b()
        if isinstance(rows, dict):
            rows = [rows]
        url = f"{self.auth.url}/rest/v1/{urllib.parse.quote(tabelle)}"
        if on_conflict:
            url += "?on_conflict=" + urllib.parse.quote(on_conflict)
        try:
            self._fetch(url, method="POST", data=json.dumps(rows).encode("utf-8"),
                        headers=self._headers({"Prefer": "resolution=merge-duplicates,return=minimal"}))
        except Exception as exc:
            return {"ok": False, "fehler": str(exc)[:160]}
        return {"ok": True, "anzahl": len(rows)}

    def select(self, tabelle: str, *, params: str = "") -> dict:
        if not self.verfuegbar():
            return self.fall_b()
        url = f"{self.auth.url}/rest/v1/{urllib.parse.quote(tabelle)}"
        if params:
            url += "?" + params
        try:
            d = self._fetch(url, method="GET", headers=self._headers())
        except Exception as exc:
            return {"ok": False, "fehler": str(exc)[:160]}
        return {"ok": True, "rows": d or []}

    def delete(self, tabelle: str, *, params: str) -> dict:
        if not self.verfuegbar():
            return self.fall_b()
        url = f"{self.auth.url}/rest/v1/{urllib.parse.quote(tabelle)}?" + params
        try:
            self._fetch(url, method="DELETE", headers=self._headers({"Prefer": "return=minimal"}))
        except Exception as exc:
            return {"ok": False, "fehler": str(exc)[:160]}
        return {"ok": True}


class MockSupabaseClient(SupabaseClient):
    """Offline-Variante: sammelt Upserts im Speicher -- fuer Self-Checks ohne Netz/Keys."""

    def __init__(self):
        super().__init__(SupabaseAuth(url="https://mock.supabase.co", service_key="mock"))
        self.upserts: list[tuple] = []
        self.deletes: list[tuple] = []
        self.rows: dict[str, list] = {}   # Tests seeden hier vorgefilterte Antworten je Tabelle

    def upsert(self, tabelle, rows, *, on_conflict=None):
        if isinstance(rows, dict):
            rows = [rows]
        self.upserts.append((tabelle, rows, on_conflict))
        return {"ok": True, "anzahl": len(rows)}

    def select(self, tabelle, *, params=""):
        return {"ok": True, "rows": list(self.rows.get(tabelle, []))}

    def delete(self, tabelle, *, params):
        self.deletes.append((tabelle, params))
        return {"ok": True}
