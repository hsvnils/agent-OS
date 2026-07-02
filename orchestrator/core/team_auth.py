"""K4 -- Team-Auth + Rollen fuer LUNA-OS (Mehr-Nutzer-Login statt Single-CEO-Basic-Auth).

Leichtgewichtig und ohne neue Dependency: Nutzer liegen in der Supabase-Tabelle `luna_os_users`
(username, password_hash, role, allowed_modules text[], is_active). LUNA-OS ist ein vertrauenswuerdiger
Server (service_role) und prueft die Zugangsdaten selbst -- Transport bleibt HTTP-Basic. Passwoerter werden
mit PBKDF2-HMAC-SHA256 (stdlib) gehasht; **nie** im Klartext gespeichert oder geloggt.

Rollen/Module (angelehnt an das HCC-Modell profiles.role/allowed_modules):
- Rolle **owner** = Superuser (alle Module).
- sonst entscheidet **allowed_modules** (Liste) je Nutzer.
- Module: content_ops, crm, invest, administration.

Graceful: fehlt die Tabelle (CEO hat die Migration noch nicht ausgefuehrt) oder Supabase -> `verify` liefert
None und `liste` []. Der env-CEO (LUNA_OS_USER/PASSWORD) bleibt als Superuser davon unberuehrt (in app.py).
"""
from __future__ import annotations

import hashlib
import hmac
import os

# -- Module + Rollen ---------------------------------------------------------

MODULE = ("content_ops", "crm", "invest", "administration")
MODUL_LABELS = {
    "content_ops": "Content (Trends/Ideen/Drafts/Quellen/AI-Inbox)",
    "crm": "Collab-CRM",
    "invest": "Investment",
    "administration": "Administration (Auftraege/Chat/System)",
}
# Welche LUNA-OS-App gehoert zu welchem Modul (SSOT fuer die Frontend-Sichtbarkeit).
APP_MODUL = {
    "trends": "content_ops", "ideas": "content_ops", "drafts": "content_ops",
    "quellen": "content_ops", "aiinbox": "content_ops",
    "crm": "crm",
    "investment": "invest",
    "auftraege": "administration", "meldungen": "administration", "aktivitaet": "administration",
    "research": "administration", "agenten": "administration", "lagebild": "administration",
    "wissen": "administration", "finance": "administration", "luna": "administration",
    "team": "administration",
}
# Sinnvolle Voreinstellung je Rolle, wenn beim Anlegen keine Module angegeben werden.
ROLLE_STANDARD_MODULE = {
    "owner": list(MODULE),
    "admin": list(MODULE),
    "team": ["content_ops", "crm"],
    "content": ["content_ops"],
    "viewer": ["content_ops"],
}


def module_fuer_rolle(rolle: str) -> list[str]:
    return list(ROLLE_STANDARD_MODULE.get((rolle or "").strip().lower(), ["content_ops"]))


def hat_modul(user: dict, modul: str) -> bool:
    """Owner sieht alles; sonst muss das Modul in allowed_modules stehen."""
    if not user:
        return False
    if (user.get("role") or "").strip().lower() == "owner":
        return True
    return modul in (user.get("allowed_modules") or [])


def erlaubte_apps(user: dict) -> list[str]:
    """App-IDs, die dieser Nutzer sehen darf (immer inkl. 'home')."""
    apps = ["home"] + [app for app, modul in APP_MODUL.items() if hat_modul(user, modul)]
    return apps


# -- Passwort-Hashing (PBKDF2, stdlib) --------------------------------------

_ALGO = "pbkdf2_sha256"
_ITER = 200_000


def hash_passwort(passwort: str, *, iterationen: int = _ITER, salt: bytes | None = None) -> str:
    salt = salt if salt is not None else os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", (passwort or "").encode("utf-8"), salt, iterationen)
    return f"{_ALGO}${iterationen}${salt.hex()}${dk.hex()}"


def pruefe_passwort(passwort: str, gespeichert: str) -> bool:
    try:
        algo, iterationen, salt_hex, hash_hex = (gespeichert or "").split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac("sha256", (passwort or "").encode("utf-8"),
                                 bytes.fromhex(salt_hex), int(iterationen))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), hash_hex)


# -- Nutzer-Store (Supabase) -------------------------------------------------

_FELDER = "id,username,display_name,role,allowed_modules,is_active,created_at,updated_at"


class TeamAuth:
    """Nutzerverwaltung + Login gegen die Supabase-Tabelle `luna_os_users`.

    `client` = SupabaseClient (service_role) oder None. Ohne Client/Tabelle degradiert alles sauber
    (verify -> None, liste -> []). `verify` filtert in Python (robust gegen Mock, der Filter ignoriert).
    """

    TABELLE = "luna_os_users"

    def __init__(self, client, *, changelog=None):
        self.client = client
        self.changelog = changelog

    def verfuegbar(self) -> bool:
        return self.client is not None and self.client.verfuegbar()

    def _alle(self) -> list[dict]:
        if not self.verfuegbar():
            return []
        r = self.client.select(self.TABELLE, params=f"select={_FELDER},password_hash")
        return r.get("rows", []) if r.get("ok") else []

    def verify(self, username: str, passwort: str) -> dict | None:
        """Login-Pruefung: aktiver Nutzer mit passendem Passwort-Hash -> Nutzer-Dict (ohne Hash)."""
        username = (username or "").strip()
        if not username:
            return None
        for row in self._alle():
            if row.get("username") == username and row.get("is_active", True):
                if pruefe_passwort(passwort, row.get("password_hash", "")):
                    return {k: row.get(k) for k in _FELDER.split(",")}
                return None
        return None

    def liste(self) -> list[dict]:
        """Alle Nutzer ohne Passwort-Hash (fuer Anzeige/Admin)."""
        return [{k: row.get(k) for k in _FELDER.split(",")} for row in self._alle()]

    def anlegen(self, username: str, passwort: str, *, role: str = "content",
                allowed_modules: list[str] | None = None, display_name: str = "") -> dict:
        """Neuen Nutzer anlegen / Passwort+Rolle aktualisieren (Upsert auf username)."""
        if not self.verfuegbar():
            return {"ok": False, "hinweis": "Nutzer-Tabelle nicht verfuegbar (Supabase/Migration fehlt)."}
        username = (username or "").strip()
        if not username or not passwort:
            return {"ok": False, "hinweis": "username und passwort sind Pflicht."}
        module = allowed_modules if allowed_modules is not None else module_fuer_rolle(role)
        module = [m for m in module if m in MODULE]
        row = {"username": username, "password_hash": hash_passwort(passwort),
               "display_name": display_name or username, "role": (role or "content").strip().lower(),
               "allowed_modules": module, "is_active": True}
        r = self.client.upsert(self.TABELLE, row, on_conflict="username")
        if r.get("ok"):
            self._log("K4/Team-Auth", f"LUNA-OS-Nutzer angelegt/aktualisiert: {username} ({row['role']})",
                      "CEO/Admin", self.TABELLE)
        return r

    def setzen_aktiv(self, username: str, aktiv: bool) -> dict:
        if not self.verfuegbar():
            return {"ok": False, "hinweis": "Nutzer-Tabelle nicht verfuegbar."}
        import urllib.parse
        r = self.client.update(self.TABELLE, {"is_active": bool(aktiv)},
                               params="username=eq." + urllib.parse.quote((username or "").strip()))
        if r.get("ok"):
            self._log("K4/Team-Auth", f"LUNA-OS-Nutzer {'aktiviert' if aktiv else 'deaktiviert'}: {username}",
                      "CEO/Admin", self.TABELLE)
        return r

    def _log(self, actor: str, was: str, warum: str, betroffen: str) -> None:
        if self.changelog:
            try:
                self.changelog(actor, was, warum, betroffen)
            except Exception:
                pass


# -- Pfad -> Modul (Backend-Enforcement) -------------------------------------

# App-spezifische Endpunkt-Praefixe je Modul. GET+POST beide gated.
_MODUL_PFADE = {
    "content_ops": ("/api/trends", "/api/ideas", "/api/drafts", "/api/sources", "/api/ai-inbox"),
    "crm": ("/api/crm",),
    "invest": ("/api/investment",),
}
# Administrative Aktionen (nur owner/admin bzw. administration-Modul).
_ADMIN_POST_PREFIXE = ("/api/antraege/",)
_ADMIN_PFADE = ("/api/chat", "/api/tts", "/api/sehen")
_ADMIN_PREFIXE = ("/api/team",)   # Team-Verwaltung: GET+POST nur administration


def modul_fuer_pfad(method: str, pfad: str) -> str | None:
    """Welches Modul ein Request braucht -- None = Kernendpunkt (jeder aktive Nutzer)."""
    for modul, prefixe in _MODUL_PFADE.items():
        if any(pfad.startswith(p) for p in prefixe):
            return modul
    if pfad in _ADMIN_PFADE or any(pfad.startswith(p) for p in _ADMIN_PREFIXE):
        return "administration"
    if method.upper() == "POST" and any(pfad.startswith(p) for p in _ADMIN_POST_PREFIXE):
        return "administration"
    if method.upper() == "POST" and pfad == "/api/brain":
        return "administration"
    return None


# -- CLI (Nutzerverwaltung, lokal/auf der NAS -- Passwort bleibt ausserhalb des Chats) ----------------

def _cli() -> int:
    """`python -m orchestrator.core.team_auth <add|list|deactivate> ...` gegen Supabase aus orchestrator/.env.

    Beispiele:
      add <username> <passwort> [rolle=content] [modul,modul]   Nutzer anlegen/aktualisieren
      list                                                       Nutzer anzeigen (ohne Hash)
      deactivate <username>                                      Nutzer deaktivieren
    """
    import sys
    from pathlib import Path
    from ..governance.supabase import SupabaseAuth, SupabaseClient

    root = Path(__file__).resolve().parents[2]
    env: dict[str, str] = {}
    envfile = root / "orchestrator" / ".env"
    if envfile.exists():
        for line in envfile.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    ta = TeamAuth(SupabaseClient(SupabaseAuth.from_env(env)))
    if not ta.verfuegbar():
        print("FEHLER: Supabase nicht konfiguriert (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in .env).")
        return 2
    args = sys.argv[1:]
    cmd = args[0] if args else "list"
    if cmd == "add" and len(args) >= 3:
        rolle = args[3] if len(args) >= 4 else "content"
        module = args[4].split(",") if len(args) >= 5 else None
        r = ta.anlegen(args[1], args[2], role=rolle, allowed_modules=module)
        print("OK" if r.get("ok") else f"FEHLER: {r.get('hinweis') or r.get('fehler')}")
        return 0 if r.get("ok") else 1
    if cmd == "deactivate" and len(args) >= 2:
        r = ta.setzen_aktiv(args[1], False)
        print("OK" if r.get("ok") else f"FEHLER: {r.get('hinweis') or r.get('fehler')}")
        return 0 if r.get("ok") else 1
    if cmd == "list":
        for u in ta.liste():
            print(f"- {u.get('username')} | {u.get('role')} | {u.get('allowed_modules')} | "
                  f"{'aktiv' if u.get('is_active', True) else 'inaktiv'}")
        return 0
    print(_cli.__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
