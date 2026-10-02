"""Betriebs-Monitoring Ende-zu-Ende (BETRIEB_ROADMAP Etappe 3, CEO-Go 2026-09-29).

Die Betriebswacht (`core/betriebswacht.py`) laeuft **im** Bot auf der NAS -- faellt die NAS oder der Bot aus, schweigt
sie mit. Dieser Waechter prueft deshalb **von aussen** (MACO470, `deploy/luna_waechter.py`, alle 15 Minuten):

  1. **LUNA-OS erreichbar** -- `GET /api/betrieb/status` auf der NAS antwortet.
  2. **Bot lebt**           -- der Bot schreibt im 15-Minuten-Abruf einen Herzschlag (`herzschlag_schreiben`).
  3. **Zustellung**         -- keine Telegram-Meldung haengt laenger als 30 Minuten in der Outbox
                               (`notifications/log.jsonl`: `queued` ohne `sent`; Lehre „erzeugt ist nicht angekommen“).
  4. **Backup**             -- der naechtliche `luna-backup.service` auf dem MACO470 lief erfolgreich (< 26 h).

Gemeldet wird **direkt per Telegram vom MACO470** (zweiter Weg, unabhaengig von der NAS), nur bei Aenderungen: ein Befund
muss zwei Laeufe in Folge bestehen (kein Alarm beim Container-Neustart), dann eine Meldung; bleibt er, eine Erinnerung
je 24 h; ist er weg, „wieder in Ordnung“. Regelbasiert, kein LLM, keine Kosten.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

BOT_STUMM_MIN = 45          # drei verpasste 15-Minuten-Abrufe
ZUSTELLUNG_MIN = 30         # aelteste unzugestellte Meldung
BACKUP_STUNDEN = 26         # naechtlicher Lauf 03:20 + Puffer
ERINNERN_STUNDEN = 24

# Nutzersichtbar (Telegram) -> echte Umlaute; eigener Text fuer die Entwarnung (CEO-Hinweis 2026-09-29)
TEXTE = {
    "luna_os": "LUNA-OS auf der NAS ist nicht erreichbar (Container luna-os oder die NAS selbst).",
    "bot_stumm": "Der Telegram-Bot auf der NAS meldet sich nicht mehr (kein Herzschlag).",
    "zustellung": "Telegram-Meldungen werden nicht zugestellt (sie hängen in der Warteschlange).",
    "backup": "Das nächtliche Backup auf dem MACO470 ist ausgefallen oder fehlgeschlagen.",
}
OK_TEXTE = {
    "luna_os": "LUNA-OS auf der NAS ist wieder erreichbar.",
    "bot_stumm": "Der Telegram-Bot auf der NAS meldet sich wieder.",
    "zustellung": "Telegram-Meldungen werden wieder zugestellt.",
    "backup": "Das Backup auf dem MACO470 ist wieder gelaufen.",
}


# -- NAS-Seite: Herzschlag (Bot) und Status (LUNA-OS) ----------------------------------------------------------------

def herzschlag_schreiben(pfad: Path, jetzt: float | None = None) -> None:
    """Vom Bot im 15-Minuten-Abruf: Zeitpunkt als Epoche (zeitzonenfrei) atomar schreiben."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(".tmp")
    tmp.write_text(json.dumps({"ts": jetzt if jetzt is not None else time.time()}), encoding="utf-8")
    tmp.replace(pfad)


BRIEFING_STUNDE = 8           # Morgen-Briefing (deutsche Zeit); Briefing-Meldungen zaehlen erst ab dann als offen


def _naechstes_briefing(ts: str) -> str:
    """BF-52: Zeitstempel (Uhr des Containers, ohne Zone) -> naechstes Morgen-Briefing ab diesem Moment, wieder als
    Container-Ortszeit ohne Zone. So zaehlt eine nachts eingereihte Briefing-Meldung erst ab 08:00 als „haengend“."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    try:
        t = datetime.fromisoformat(ts).astimezone()              # naive = Ortszeit des Prozesses (Container: UTC)
    except ValueError:
        return ts
    berlin = t.astimezone(ZoneInfo("Europe/Berlin"))
    b = berlin.replace(hour=BRIEFING_STUNDE, minute=0, second=0, microsecond=0)
    if b < berlin:
        b += timedelta(days=1)
    return b.astimezone(t.tzinfo).replace(tzinfo=None).isoformat(timespec="seconds")


def status(herzschlag: Path, notifications_log: Path, *, jetzt: float | None = None) -> dict:
    """Fuer `GET /api/betrieb/status`: Alter des Bot-Herzschlags und der aeltesten unzugestellten Meldung (Minuten)."""
    jetzt = jetzt if jetzt is not None else time.time()
    try:
        bot_min = round((jetzt - float(json.loads(herzschlag.read_text(encoding="utf-8"))["ts"])) / 60, 1)
    except (OSError, ValueError, KeyError, TypeError):
        bot_min = None
    queued, sent = {}, set()
    try:
        for zeile in notifications_log.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(zeile)
            except ValueError:
                continue
            if e.get("typ") == "queued":
                ts = e.get("ts", "")
                if e.get("nach_briefing") and ts:          # BF-52: wartet absichtlich aufs Morgen-Briefing
                    ts = _naechstes_briefing(ts)
                queued[e.get("id")] = ts
            elif e.get("typ") == "sent":
                sent.add(e.get("id"))
    except OSError:
        pass
    jetzt_iso = datetime.fromtimestamp(jetzt).isoformat(timespec="seconds")
    offen = [ts for nid, ts in queued.items() if nid not in sent and ts and ts <= jetzt_iso]   # Briefing-Meldungen erst ab 08:00
    aelteste = None
    if offen:                                   # ts ohne Zeitzone = Uhr des Containers -> gegen dieselbe Uhr rechnen
        try:
            aelteste = round((datetime.fromtimestamp(jetzt) - datetime.fromisoformat(min(offen))).total_seconds() / 60, 1)
        except ValueError:
            aelteste = None
    return {"bot_alter_min": bot_min, "unzugestellt": len(offen), "aelteste_unzugestellt_min": aelteste}


# -- MACO470-Seite: pruefen und melden -------------------------------------------------------------------------------

def befunde(nas: dict | None, backup: dict | None) -> list[str]:
    """`nas` = Antwort von /api/betrieb/status (None = nicht erreichbar); `backup` = {ok, alter_h} (None = unbekannt)."""
    out = []
    if nas is None:
        out.append("luna_os")
    else:
        if nas.get("bot_alter_min") is None or nas["bot_alter_min"] > BOT_STUMM_MIN:
            out.append("bot_stumm")
        if (nas.get("aelteste_unzugestellt_min") or 0) > ZUSTELLUNG_MIN:
            out.append("zustellung")
    if backup is not None and (not backup.get("ok") or (backup.get("alter_h") or 0) > BACKUP_STUNDEN):
        out.append("backup")
    return out


def entscheiden(aktuell: list[str], zustand: dict, jetzt: datetime) -> tuple[list[str], dict]:
    """-> (zu sendende Meldungen, neuer Zustand). Zustand: {schluessel: {"seit", "laeufe", "gemeldet"}}."""
    neu, meldungen = {}, []
    for k in aktuell:
        z = dict(zustand.get(k) or {"seit": jetzt.isoformat(timespec="minutes"), "laeufe": 0, "gemeldet": ""})
        z["laeufe"] = int(z.get("laeufe", 0)) + 1
        if z["laeufe"] >= 2:
            letzte = datetime.fromisoformat(z["gemeldet"]) if z.get("gemeldet") else None
            if letzte is None:
                meldungen.append(f"⚠️ {TEXTE[k]} (seit {datetime.fromisoformat(z['seit']).strftime('%d.%m. %H:%M')})")
                z["gemeldet"] = jetzt.isoformat(timespec="minutes")
            elif jetzt - letzte >= timedelta(hours=ERINNERN_STUNDEN):
                meldungen.append(f"⏰ Weiterhin: {TEXTE[k]} (seit {datetime.fromisoformat(z['seit']).strftime('%d.%m. %H:%M')})")
                z["gemeldet"] = jetzt.isoformat(timespec="minutes")
        neu[k] = z
    for k, z in zustand.items():
        if k not in neu and z.get("gemeldet"):
            meldungen.append(f"✅ Wieder in Ordnung: {OK_TEXTE.get(k, k)}")
    return meldungen, neu


def backup_info(systemctl_ausgabe: str, jetzt: datetime) -> dict | None:
    """Aus `systemctl show luna-backup.service -p Result -p ExecMainExitTimestamp`: {ok, alter_h} oder None."""
    felder = dict(z.split("=", 1) for z in systemctl_ausgabe.splitlines() if "=" in z)
    ergebnis, ende = felder.get("Result", ""), felder.get("ExecMainExitTimestamp", "").strip()
    if not ergebnis:
        return None
    if not ende or ende == "n/a":
        return {"ok": False, "alter_h": None}
    try:                                         # z. B. "Tue 2026-09-29 03:20:42 CEST"
        zeit = datetime.strptime(" ".join(ende.split()[1:3]), "%Y-%m-%d %H:%M:%S")
    except (ValueError, IndexError):
        return None
    return {"ok": ergebnis == "success", "alter_h": round((jetzt - zeit).total_seconds() / 3600, 1)}
