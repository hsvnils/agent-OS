#!/usr/bin/env python3
"""Betriebs-Waechter auf dem MACO470 (BETRIEB_ROADMAP Etappe 3) -- prueft von aussen, ob NAS/LUNA-OS, Bot, Telegram-
Zustellung und das naechtliche Backup laufen, und meldet Ausfaelle DIREKT per Telegram (unabhaengig von der NAS).

Laeuft alle 15 Minuten ueber `luna-waechter.timer`. Liest nur die `.env` (Werte werden nie ausgegeben), schreibt nur
seinen Zustand nach `~/.local/state/luna-waechter.json`. Logik: `orchestrator/core/betriebswaechter.py`.

Aufruf:  .venv/bin/python deploy/luna_waechter.py           -> pruefen + ggf. melden
         .venv/bin/python deploy/luna_waechter.py --probe   -> nur anzeigen, nichts senden, Zustand unveraendert
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from orchestrator.core.betriebswaechter import backup_info, befunde, entscheiden  # noqa: E402

ENV = ROOT / "orchestrator" / ".env"
ZUSTAND = Path.home() / ".local" / "state" / "luna-waechter.json"
NAS_URL = "http://192.168.178.129:8765/api/betrieb/status"


def _env() -> dict:
    out = {}
    for z in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in z and not z.lstrip().startswith("#"):
            k, v = z.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def nas_status(env: dict) -> dict | None:
    auth = base64.b64encode(f"{env.get('LUNA_OS_USER', 'ceo')}:{env.get('LUNA_OS_PASSWORD', '')}".encode()).decode()
    req = urllib.request.Request(NAS_URL, headers={"Authorization": "Basic " + auth})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception:
        return None


def backup_status() -> dict | None:
    try:
        aus = subprocess.run(["systemctl", "show", "luna-backup.service", "-p", "Result", "-p", "ExecMainExitTimestamp"],
                             capture_output=True, text=True, timeout=15).stdout
    except Exception:
        return None
    return backup_info(aus, datetime.now())


def telegram(env: dict, text: str) -> bool:
    tok, chat = env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_ALLOWED_CHAT_ID", "")
    if not tok or not chat:
        return False
    daten = urllib.parse.urlencode({"chat_id": chat, "text": f"🛡️ Wächter (MACO470): {text}"}).encode()
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=daten, timeout=15) as r:
            return json.loads(r.read()).get("ok") is True
    except Exception:
        return False


def main(argv: list[str]) -> int:
    probe = "--probe" in argv
    env = _env()
    nas, backup = nas_status(env), backup_status()
    aktuell = befunde(nas, backup)
    try:
        zustand = json.loads(ZUSTAND.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        zustand = {}
    meldungen, neu = entscheiden(aktuell, zustand, datetime.now())
    print(f"NAS: {nas} | Backup: {backup} | Befunde: {aktuell or 'keine'} | Meldungen: {len(meldungen)}")
    if probe:
        for m in meldungen:
            print("  (nicht gesendet)", m)
        return 0
    for m in meldungen:
        if not telegram(env, m):
            print("  Telegram-Versand fehlgeschlagen:", m[:80], file=sys.stderr)
    ZUSTAND.parent.mkdir(parents=True, exist_ok=True)
    ZUSTAND.write_text(json.dumps(neu, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
