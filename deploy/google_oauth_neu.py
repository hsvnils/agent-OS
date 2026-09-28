"""Google-Zugang von LUNA erneuern (BF-33) -- auf dem MACO470, ohne client_secret.json und ohne Werte anzuzeigen.

Liest GOOGLE_OAUTH_CLIENT_ID/SECRET aus orchestrator/.env, zeigt einen Google-Link; der CEO oeffnet ihn im Browser auf
dem MACO470 (Windows-Chrome erreicht den WSL-Port ueber localhost), meldet sich mit dem LUNA-Google-Konto an und stimmt zu.
Danach: neuen Refresh-Token mit einem echten Kalender-Abruf pruefen, alte .env nach ~/env-backups/ sichern, Token in die
.env des MACO470 und der NAS schreiben (Token nur ueber stdin, nie als Argument oder Ausgabe).

Nutzung:  .venv/bin/python deploy/google_oauth_neu.py [--port 8799] [--ohne-nas]
          .venv/bin/python deploy/google_oauth_neu.py --nur-nas   (Token aus der MACO470-.env auf die NAS uebertragen)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from orchestrator.governance.google_workspace import SCOPES  # noqa: E402

ENV = ROOT / "orchestrator" / ".env"
NAS_ENV = "/volume1/docker/ki-unternehmen/orchestrator/.env"
SCHLUESSEL = "GOOGLE_OAUTH_REFRESH_TOKEN"

# Laeuft auf der NAS (Host-Python): ersetzt genau eine Zeile, Token kommt ueber stdin.
_NAS_SKRIPT = f"""
import sys, os
p = {NAS_ENV!r}
tok = sys.stdin.read().strip()
z = open(p, encoding="utf-8").read().splitlines()
n = [f"{SCHLUESSEL}=" + tok if l.startswith("{SCHLUESSEL}=") else l for l in z]
if n == z and not any(l.startswith("{SCHLUESSEL}=") for l in z):
    n.append("{SCHLUESSEL}=" + tok)
tmp = p + ".neu"
open(tmp, "w", encoding="utf-8").write("\\n".join(n) + "\\n")
os.chmod(tmp, os.stat(p).st_mode)
os.replace(tmp, p)
print("NAS-.env aktualisiert")
"""


def _env_wert(name: str) -> str:
    for z in ENV.read_text(encoding="utf-8").splitlines():
        if z.startswith(name + "="):
            return z.split("=", 1)[1].strip()
    return ""


def _env_setzen(tok: str) -> None:
    z = ENV.read_text(encoding="utf-8").splitlines()
    n = [f"{SCHLUESSEL}={tok}" if l.startswith(SCHLUESSEL + "=") else l for l in z]
    if not any(l.startswith(SCHLUESSEL + "=") for l in z):
        n.append(f"{SCHLUESSEL}={tok}")
    tmp = ENV.with_name(".env.neu")
    tmp.write_text("\n".join(n) + "\n", encoding="utf-8")
    shutil.copymode(ENV, tmp)
    tmp.replace(ENV)


def nas_setzen(tok: str) -> bool:
    """Token in die NAS-.env schreiben. ssh fuegt Argumente zu EINER Shell-Zeile zusammen -- mehrzeiliger Python-Code
    zerfiel dabei (Befund 2026-09-28). Deshalb das Skript base64-kodiert als einzelnes Wort, der Token ueber stdin."""
    import base64
    code = base64.b64encode(_NAS_SKRIPT.encode()).decode()
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "luna-nas",
                        f"python3 -c \"import base64;exec(base64.b64decode('{code}'))\""],
                       input=tok, text=True, capture_output=True, timeout=60)
    print(r.stdout.strip() or f"FEHLER NAS: {r.stderr.strip()[:200]}")
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8799)
    ap.add_argument("--ohne-nas", action="store_true")
    ap.add_argument("--nur-nas", action="store_true")
    ap.add_argument("--erwartet", default="", help="Nur dieses Google-Konto akzeptieren (z. B. luna.hanserautisch@gmail.com)")
    a = ap.parse_args()
    if a.nur_nas:
        tok = _env_wert(SCHLUESSEL)
        return 0 if tok and nas_setzen(tok) else 1
    cid, sec = _env_wert("GOOGLE_OAUTH_CLIENT_ID"), _env_wert("GOOGLE_OAUTH_CLIENT_SECRET")
    if not cid or not sec:
        print("FEHLER: GOOGLE_OAUTH_CLIENT_ID/SECRET fehlen in orchestrator/.env")
        return 1
    from google_auth_oauthlib.flow import InstalledAppFlow
    konfig = {"installed": {"client_id": cid, "client_secret": sec, "redirect_uris": ["http://localhost"],
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token"}}
    flow = InstalledAppFlow.from_client_config(konfig, SCOPES)
    creds = flow.run_local_server(host="localhost", port=a.port, open_browser=False, prompt="consent",
                                  authorization_prompt_message="LINK: {url}",
                                  success_message="Fertig -- LUNA hat den Google-Zugang. Fenster kann zu.")
    if not creds.refresh_token:
        print("FEHLER: kein Refresh-Token erhalten (Zugriff neu zustimmen).")
        return 1
    # Wirkung pruefen, bevor irgendetwas ueberschrieben wird
    from googleapiclient.discovery import build
    build("calendar", "v3", credentials=creds, cache_discovery=False).events().list(
        calendarId="primary", maxResults=1).execute()
    print("Test: Kalender-Abruf mit neuem Zugang ok")
    konto = build("gmail", "v1", credentials=creds, cache_discovery=False).users().getProfile(userId="me").execute()
    konto = (konto.get("emailAddress") or "").lower()
    print(f"Angemeldetes Konto: {konto}")
    if a.erwartet and konto != a.erwartet.lower():
        print(f"ABBRUCH: erwartet {a.erwartet} -- nichts geaendert. Bitte mit dem richtigen Konto erneut bestaetigen.")
        return 2
    ziel = Path.home() / "env-backups" / f"orchestrator.env.{datetime.now():%Y%m%d-%H%M%S}.vor-google-neu"
    ziel.parent.mkdir(exist_ok=True)
    shutil.copy2(ENV, ziel)
    ziel.chmod(0o600)
    _env_setzen(creds.refresh_token)
    print(f"MACO470-.env aktualisiert (Sicherung: {ziel})")
    if not a.ohne_nas:
        if not nas_setzen(creds.refresh_token):
            return 1
    print("Fertig. Jetzt die NAS-Container neu starten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
