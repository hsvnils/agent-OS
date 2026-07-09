"""Ordner-Watcher fuer den unbeaufsichtigten Betrieb auf dem Mac.

Idee: Du legst deine Clips in einen Projekt-Unterordner des **Inbox**-Ordners. Sobald dort eine
Weile nichts Neues mehr dazukommt (Upload fertig), schneidet der Watcher automatisch ein Reel und
legt es in den **Outbox**-Ordner. Du musst nicht am Rechner sitzen -- nur den Mac anlassen.

Start:  python -m cutter.watch
Default-Ordner:  ~/CutterInbox  ->  ~/CutterOutbox  (per Argument/Env aenderbar).
Kein Posten -- nur die fertige Datei (Instagram-Posten bleibt CEO-Tor).
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from . import melden
from .ffmpeg_ops import clips_im_ordner
from .luna_bridge import LunaBridge
from .pipeline import _lade_env, schneide_ordner

MARKER = ".cutter_status.json"


def _stabil(ordner: Path, ruhe_sek: float) -> bool:
    """True, wenn seit `ruhe_sek` keine Datei im Ordner mehr geaendert wurde (Upload fertig)."""
    clips = clips_im_ordner(ordner)
    if not clips:
        return False
    juengste = max(p.stat().st_mtime for p in clips)
    return (time.time() - juengste) >= ruhe_sek


def _verarbeite(projekt: Path, outbox: Path, ziel_dauer: float, token: str = "", chat: str = "",
                bridge: LunaBridge | None = None, job_id: str = "") -> None:
    ausgabe = outbox / f"{projekt.name}_reel.mp4"
    print(f"[{datetime.now():%H:%M:%S}] schneide '{projekt.name}' ...", flush=True)
    if bridge is not None and bridge.aktiv():
        bridge.melden(job_id=job_id, projekt=projekt.name, status="running")
    bericht = schneide_ordner(projekt, ausgabe, ziel_dauer=ziel_dauer)
    (projekt / MARKER).write_text(json.dumps(
        {"ts": datetime.now().isoformat(timespec="seconds"), **bericht}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    # K5: Status an LUNA-OS melden (sichtbar in der Cutter-App). Best-effort.
    if bridge is not None and bridge.aktiv():
        if bericht.get("ok"):
            try:
                groesse_mb = round(ausgabe.stat().st_size / (1024 * 1024), 1) if ausgabe.exists() else None
            except OSError:
                groesse_mb = None
            bridge.melden(job_id=job_id, projekt=projekt.name, status="done",
                          clips_verwendet=bericht.get("verwendet"), dauer_sek=bericht.get("dauer_sek"),
                          untertitel=str(bericht.get("untertitel")), reel_datei=ausgabe.name,
                          groesse_mb=groesse_mb)
        else:
            bridge.melden(job_id=job_id, projekt=projekt.name, status="failed",
                          fehler=str(bericht.get("fehler", ""))[:300])
    if bericht.get("ok"):
        print(f"[{datetime.now():%H:%M:%S}] fertig -> {ausgabe} "
              f"({bericht['verwendet']} Clips, {bericht['dauer_sek']}s, "
              f"Untertitel: {bericht['untertitel']})", flush=True)
        # V2: Reel an den LUNA-Chat melden (Senden an den CEO selbst -- kein CEO-Tor).
        if token and chat:
            cap = (f"🎬 Cutter: Reel '{projekt.name}' fertig — {bericht['verwendet']} Clips, "
                   f"{bericht['dauer_sek']}s, Untertitel: {bericht['untertitel']}. "
                   f"Musik + Posten machst du in Instagram.")
            if not melden.sende_reel(token, chat, ausgabe, cap):
                melden.sende_text(token, chat, cap + f"\n(Video zu gross fuer Telegram? Datei: {ausgabe})")
    else:
        print(f"[{datetime.now():%H:%M:%S}] FEHLER: {bericht.get('fehler')}", flush=True)
        if token and chat:
            melden.sende_text(token, chat, f"🎬 Cutter: '{projekt.name}' fehlgeschlagen — {bericht.get('fehler')}")


def _reel_params(job: dict) -> dict | None:
    """Reel-Job? Die Parameter stecken als JSON im `note`-Feld (typ=='reel'). Sonst None (normaler Cut-Job)."""
    note = job.get("note")
    if not note:
        return None
    try:
        d = json.loads(note)
    except Exception:
        return None
    return d if isinstance(d, dict) and d.get("typ") == "reel" else None


def _verarbeite_reel(job: dict, reel_src, reel_out, reel_state, token: str, chat: str,
                     bridge: LunaBridge | None) -> None:
    """Manuellen Themen-Reel bauen (reel_daily.lauf) und zur CEO-Freigabe einreichen. Best-effort, nie Absturz."""
    from . import reel_daily
    p = _reel_params(job) or {}
    job_id, label = job.get("id", ""), job.get("projekt", "Reel")
    if not reel_src:
        if bridge:
            bridge.melden(job_id=job_id, projekt=label, status="failed",
                          fehler="REEL_SOURCE im Watcher nicht gesetzt (Env in der watch-plist ergaenzen).")
        return
    if bridge:
        bridge.melden(job_id=job_id, projekt=label, status="running")
    try:
        res = reel_daily.lauf(source=reel_src, outbox=reel_out, state=reel_state,
                              thema_name=p.get("thema") or None, alle_spiele=bool(p.get("alle_spiele")),
                              spiel=p.get("spiel") or None, ziel_dauer=float(p.get("max_dauer") or 45),
                              min_dauer=float(p.get("min_dauer") or 15), schnell_index=True)
    except Exception as exc:                               # nie den Watcher mitreissen
        res = {"ok": False, "fehler": f"Reel-Bau abgestuerzt: {exc}"}
    if res.get("ok"):
        eingereicht = False
        if bridge and bridge.aktiv():
            meta = {k: res.get(k) for k in ("datum", "thema", "caption", "dauer_sek", "spiele")}
            r = bridge.reel_einreichen(res["reel"], meta)
            eingereicht = bool(r and r.get("ok"))
        if bridge:
            bridge.melden(job_id=job_id, projekt=label, status="done", dauer_sek=res.get("dauer_sek"),
                          reel_datei=res.get("reel"),
                          note="eingereicht" if eingereicht else "gebaut (nicht eingereicht)")
        if token and chat:
            melden.sende_text(token, chat, f"🎬 Manuelles Reel '{label}' fertig — {res.get('verwendet')} "
                                           f"Clips, {res.get('dauer_sek')}s. Wartet auf deine Freigabe.")
    else:
        grund = res.get("fehler") or res.get("hinweis") or "unbekannt"
        if bridge:
            bridge.melden(job_id=job_id, projekt=label, status="failed", fehler=grund)
        if token and chat:
            melden.sende_text(token, chat, f"🎬 Reel '{label}' nicht erstellt — {grund}")


def loop(inbox: Path, outbox: Path, *, intervall: float = 15.0, ruhe_sek: float = 30.0,
         ziel_dauer: float = 45.0, einmal: bool = False) -> None:
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    env = _lade_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat = env.get("TELEGRAM_ALLOWED_CHAT_ID", "")
    bridge = LunaBridge.from_env(env)   # K5: Status/Queue via LUNA-OS-API (nur wenn LUNA_OS_URL+Passwort da)
    print(f"Cutter-Watcher aktiv. Inbox: {inbox}  ->  Outbox: {outbox}"
          + (" | Telegram-Meldung: an" if token and chat else "")
          + (" | LUNA-OS-Bruecke: an" if bridge.aktiv() else ""), flush=True)
    print("Lege Clips in einen Unterordner der Inbox -- der Schnitt startet automatisch.", flush=True)
    # Reel-Pfade fuer manuelle Themen-Reels (aus der Env; ohne REEL_SOURCE bleiben Reel-Jobs deaktiviert).
    reel_src = Path(os.environ["REEL_SOURCE"]).expanduser() if os.environ.get("REEL_SOURCE") else None
    reel_out = Path(os.environ.get("REEL_OUTBOX") or "").expanduser() if os.environ.get("REEL_OUTBOX") else outbox
    reel_state = Path(os.environ["REEL_STATE"]).expanduser() if os.environ.get("REEL_STATE") else (outbox.parent / "reel_state")
    while True:
        try:
            # K5: von LUNA-OS angestossene Jobs zuerst (auch wenn der Ordner schon einen Marker hat).
            for job in (bridge.offene_jobs() if bridge.aktiv() else []):
                if _reel_params(job) is not None:          # manueller Themen-Reel (kein Inbox-Ordner)
                    _verarbeite_reel(job, reel_src, reel_out, reel_state, token, chat, bridge)
                    continue
                projekt = inbox / (job.get("projekt") or "")
                if projekt.is_dir():
                    _verarbeite(projekt, outbox, ziel_dauer, token, chat, bridge, job.get("id", ""))
                else:
                    bridge.melden(job_id=job.get("id", ""), projekt=job.get("projekt", ""),
                                  status="failed", fehler="Ordner nicht in der Cutter-Inbox gefunden.")
            for projekt in sorted(p for p in inbox.iterdir() if p.is_dir()):
                if (projekt / MARKER).exists():
                    continue
                if _stabil(projekt, ruhe_sek):
                    _verarbeite(projekt, outbox, ziel_dauer, token, chat, bridge)
        except Exception as exc:                       # nie den Watcher mitreissen
            print(f"[watch] Fehler: {exc}", flush=True)
        if einmal:
            return
        time.sleep(intervall)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Cutter-Watcher -- unbeaufsichtigter Auto-Schnitt.")
    p.add_argument("--inbox", default=os.environ.get("CUTTER_INBOX", str(Path.home() / "CutterInbox")))
    p.add_argument("--outbox", default=os.environ.get("CUTTER_OUTBOX", str(Path.home() / "CutterOutbox")))
    p.add_argument("--dauer", type=float, default=45.0, help="Ziel-Gesamtlaenge (Sekunden).")
    p.add_argument("--ruhe", type=float, default=30.0, help="Ruhe-Sekunden bis Upload als fertig gilt.")
    p.add_argument("--einmal", action="store_true", help="Nur einen Durchlauf (zum Testen).")
    a = p.parse_args(argv)
    loop(Path(a.inbox), Path(a.outbox), ruhe_sek=a.ruhe, ziel_dauer=a.dauer, einmal=a.einmal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
