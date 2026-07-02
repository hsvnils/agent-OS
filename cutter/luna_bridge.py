"""K5 -- HTTP-Bruecke Mac-Cutter <-> LUNA-OS (NAS).

Der Cutter laeuft lokal auf dem Mac, LUNA-OS auf der NAS. Statt einen Supabase-service_role-Key auf den
Mac zu legen, spricht der Cutter nur mit der **LUNA-OS-API** (HTTP-Basic-Login): er meldet Job-Status
(`/api/cutter/report`) und holt offene Jobs (`/api/cutter/queue`). LUNA-OS besitzt Supabase allein.

Konfiguration in orchestrator/.env (auf dem Mac):
  LUNA_OS_URL=https://os.hanserautisch.synology.me
  LUNA_OS_USER=ceo
  LUNA_OS_PASSWORD=...            (dasselbe Passwort wie der LUNA-OS-Login)

Ohne URL/Passwort ist die Bruecke **inaktiv** -- der Cutter arbeitet dann wie bisher rein lokal (Marker +
Telegram). Keine neue Dependency (nur urllib). Fehler werden geschluckt (nie den Watcher mitreissen).
"""
from __future__ import annotations

import base64
import json
import urllib.request


class LunaBridge:
    def __init__(self, base_url: str, user: str, passwort: str, *, timeout: int = 15):
        self.base = (base_url or "").rstrip("/")
        self._user = user or "ceo"
        self._pw = passwort or ""
        self.timeout = timeout

    @classmethod
    def from_env(cls, env: dict) -> "LunaBridge":
        return cls(env.get("LUNA_OS_URL", ""), env.get("LUNA_OS_USER", "ceo"),
                   env.get("LUNA_OS_PASSWORD", ""))

    def aktiv(self) -> bool:
        return bool(self.base and self._pw)

    def _req(self, pfad: str, *, method: str = "GET", data: dict | None = None):
        if not self.aktiv():
            return None
        token = base64.b64encode(f"{self._user}:{self._pw}".encode()).decode()
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(
            self.base + pfad, method=method, data=body,
            headers={"Authorization": "Basic " + token,
                     **({"Content-Type": "application/json"} if body else {})})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                txt = r.read().decode("utf-8")
                return json.loads(txt) if txt.strip() else {}
        except Exception as exc:
            print(f"[luna-bridge] {method} {pfad} fehlgeschlagen: {str(exc)[:120]}", flush=True)
            return None

    def offene_jobs(self) -> list[dict]:
        """Von LUNA-OS in die Warteschlange gestellte Jobs (queued)."""
        r = self._req("/api/cutter/queue")
        return (r or {}).get("jobs", []) if r else []

    def melden(self, *, job_id: str = "", projekt: str = "", status: str = "running", **felder) -> None:
        """Job-Status an LUNA-OS melden. Mit job_id -> vorhandene Zeile aktualisieren (aus der Warteschlange),
        sonst neue Zeile (auto-verarbeiteter Ordner)."""
        nutzdaten = {"status": status, "projekt": projekt}
        if job_id:
            nutzdaten["job_id"] = job_id
        nutzdaten.update({k: v for k, v in felder.items() if v is not None})
        self._req("/api/cutter/report", method="POST", data=nutzdaten)
