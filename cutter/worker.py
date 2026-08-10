"""Cutter-Worker -- laeuft auf dem MACO470 (WSL2-Ubuntu) als Dauerdienst.

Zwei Quellen, ein Prozess:

  1. **Queue** (LUNA-OS-API `/api/cutter/queue`): manuelle Auftraege aus der Weboberflaeche.
     - `note` enthaelt JSON mit `typ=="reel"` -> **Themen-Reel** ueber `reel_daily.lauf` (Thema, Einzelspiel
       oder alle Spiele, Min-/Max-Laenge) -> fertiges Reel per Bridge zur CEO-Freigabe einreichen.
     - sonst -> **Ordner-Job**: der Projektordner wird in der lokalen Inbox erwartet (wie beim Mac-Watcher).
  2. **Lokale Inbox** (`~/CutterInbox/<projekt>/`): Camp-Betrieb -- Material per scp/USB ablegen, der
     Worker schneidet automatisch, sobald der Ordner „ruhig" ist. Funktioniert auch ohne Internet
     (die Bridge schluckt Fehler; fertige Reels bleiben in der Outbox liegen).

**Genau EIN Worker** darf die Queue abarbeiten (der Mac-Watcher wird per `CUTTER_QUEUE_POLL=0`
stillgelegt). Deshalb kein Claiming-Protokoll: der sofortige `melden(status="running")` nimmt den Job
aus der `queued`-Liste und genuegt als De-facto-Claim. Kaeme je ein zweiter Worker dazu, muesste ein
echtes Claiming nach `docs/cutter-worker-plan.md` nachgeruestet werden.

Start:  python -m cutter.worker        (als systemd-Dienst `cutter-worker`)
Env:    LUNA_OS_URL/_USER/_PASSWORD (Bridge) · REEL_SOURCE/_OUTBOX/_STATE · CUTTER_INBOX/_OUTBOX
Kein Posten -- Veroeffentlichen bleibt CEO-Tor.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from . import melden, reel_daily
from .luna_bridge import LunaBridge
from .pipeline import _lade_env
from .watch import MARKER, _stabil, _verarbeite


def _log(text: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {text}", flush=True)


def reel_params(job: dict) -> dict | None:
    """Reel-Job? Parameter stecken als JSON im `note`-Feld (`typ=="reel"`). Sonst None (Ordner-Job)."""
    note = job.get("note")
    if not note:
        return None
    try:
        d = json.loads(note)
    except (ValueError, TypeError):
        return None
    return d if isinstance(d, dict) and d.get("typ") == "reel" else None


def _pfad(env: dict, key: str, fallback: str) -> Path:
    return Path(os.environ.get(key) or env.get(key) or fallback).expanduser()


def verarbeite_reel_job(job: dict, *, source: Path, outbox: Path, state: Path,
                        bridge: LunaBridge, token: str = "", chat: str = "") -> dict:
    """Einen Themen-Reel-Job bauen und zur CEO-Freigabe einreichen. Wirft nie -- gibt den Bericht zurueck."""
    p = reel_params(job) or {}
    job_id, label = job.get("id", ""), job.get("projekt", "Reel")
    bridge.melden(job_id=job_id, projekt=label, status="running")     # zugleich De-facto-Claim
    _log(f"Reel-Job '{label}': Thema={p.get('thema') or 'Auto'} "
         f"{'alle Spiele' if p.get('alle_spiele') else p.get('spiel') or '?'}")
    try:
        res = reel_daily.lauf(
            source=source, outbox=outbox, state=state,
            thema_name=p.get("thema") or None, alle_spiele=bool(p.get("alle_spiele")),
            spiel=p.get("spiel") or None, ziel_dauer=float(p.get("max_dauer") or 45),
            min_dauer=float(p.get("min_dauer") or 15), schnell_index=True)
    except Exception as exc:                                          # nie den Worker mitreissen
        res = {"ok": False, "fehler": f"Reel-Bau abgestuerzt: {exc}"}

    if res.get("ok"):
        meta = {k: res.get(k) for k in ("datum", "thema", "caption", "dauer_sek", "spiele")}
        r = bridge.reel_einreichen(res["reel"], meta)
        eingereicht = bool(r and r.get("ok"))
        bridge.melden(job_id=job_id, projekt=label, status="done", dauer_sek=res.get("dauer_sek"),
                      clips_verwendet=res.get("verwendet"), reel_datei=res.get("reel"),
                      note="eingereicht" if eingereicht else "gebaut (Einreichen fehlgeschlagen)")
        _log(f"fertig: {res.get('dauer_sek')}s, {res.get('verwendet')} Clips, "
             f"{'eingereicht' if eingereicht else 'NICHT eingereicht'}")
        if token and chat:
            melden.sende_text(token, chat,
                              f"🎬 Reel '{label}' fertig — {res.get('verwendet')} Clips, "
                              f"{res.get('dauer_sek')}s. "
                              + ("Wartet auf deine Freigabe." if eingereicht
                                 else "Einreichen fehlgeschlagen (liegt in der Outbox)."))
    else:
        grund = str(res.get("fehler") or res.get("hinweis") or "unbekannt")
        bridge.melden(job_id=job_id, projekt=label, status="failed", fehler=grund[:300])
        _log(f"FEHLER: {grund}")
        if token and chat:
            melden.sende_text(token, chat, f"🎬 Reel '{label}' nicht erstellt — {grund}")
    return res


def loop(*, intervall: float = 20.0, ruhe_sek: float = 30.0, ziel_dauer: float = 45.0,
         einmal: bool = False) -> None:
    env = _lade_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat = env.get("TELEGRAM_ALLOWED_CHAT_ID", "")
    bridge = LunaBridge.from_env(env)
    inbox = _pfad(env, "CUTTER_INBOX", "~/CutterInbox")
    outbox = _pfad(env, "CUTTER_OUTBOX", "~/CutterOutbox")
    reel_source = _pfad(env, "REEL_SOURCE", "/mnt/nas-clips")
    reel_outbox = _pfad(env, "REEL_OUTBOX", "~/ReelOutbox")
    reel_state = _pfad(env, "REEL_STATE", "~/ReelState")
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)

    _log(f"Cutter-Worker aktiv. Inbox: {inbox} -> Outbox: {outbox}")
    _log(f"Reel-Quelle: {reel_source} | Bridge: {'an' if bridge.aktiv() else 'AUS (nur lokal)'}"
         + (" | Telegram: an" if token and chat else ""))

    while True:
        try:
            for job in (bridge.offene_jobs() if bridge.aktiv() else []):
                if reel_params(job) is not None:                      # manueller Themen-Reel
                    verarbeite_reel_job(job, source=reel_source, outbox=reel_outbox, state=reel_state,
                                        bridge=bridge, token=token, chat=chat)
                    continue
                projekt = inbox / (job.get("projekt") or "")          # Ordner-Job aus der Weboberflaeche
                if projekt.is_dir():
                    _verarbeite(projekt, outbox, ziel_dauer, token, chat, bridge, job.get("id", ""))
                else:
                    bridge.melden(job_id=job.get("id", ""), projekt=job.get("projekt", ""),
                                  status="failed", fehler="Ordner nicht in der Cutter-Inbox gefunden.")
            for projekt in sorted(p for p in inbox.iterdir() if p.is_dir()):   # Camp: lokale Inbox
                if (projekt / MARKER).exists():
                    continue
                if _stabil(projekt, ruhe_sek):
                    _verarbeite(projekt, outbox, ziel_dauer, token, chat, bridge)
        except Exception as exc:                                      # nie den Worker mitreissen
            _log(f"Schleifen-Fehler: {exc}")
        if einmal:
            return
        time.sleep(intervall)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Cutter-Worker -- Queue (LUNA-OS) + lokale Inbox.")
    p.add_argument("--intervall", type=float, default=20.0, help="Poll-Intervall in Sekunden (Default 20).")
    p.add_argument("--ruhe", type=float, default=30.0, help="Ruhe-Sekunden, bis ein Inbox-Ordner fertig gilt.")
    p.add_argument("--dauer", type=float, default=45.0, help="Ziel-Gesamtlaenge fuer Ordner-Jobs (Sekunden).")
    p.add_argument("--einmal", action="store_true", help="Nur ein Durchlauf (zum Testen).")
    a = p.parse_args(argv)
    loop(intervall=a.intervall, ruhe_sek=a.ruhe, ziel_dauer=a.dauer, einmal=a.einmal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
