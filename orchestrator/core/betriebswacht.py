"""Betriebs-Wacht -- merkt, wenn die 24/7-Maschinen still stehen.

Hintergrund (2026-08-17): Zwei Ausfaelle blieben tagelang unbemerkt -- der Cutter-Worker auf dem MACO470
lief nach jedem WSL-Leerlauf nicht mehr, und der naechtliche Reel-Lauf brach seit dem 11.08. an leeren
Spielordnern ab. Beides war **stumm**: kein Job, keine Meldung, kein Alarm. Genau diese Stille ueberwacht
dieses Modul.

Vier Befunde, alle **regelbasiert und kostenlos** (kein LLM, kein Token):

  1. **Queue steht**  -- ein `queued`-Auftrag liegt laenger als `stau_min` -> niemand holt ihn ab.
  2. **Job haengt**   -- ein `running`-Auftrag laeuft laenger als `haenger_min` -> Worker mittendrin gestorben.
  3. **Worker stumm** -- der letzte Queue-Abruf ist aelter als `herz_min` (Herzschlag der Web-App).
  4. **Kein Reel**    -- seit `reel_stunden` wurde kein Reel eingereicht -> die Nacht ist ausgefallen.

Der Meldetext je Befund ist **bewusst konstant** (keine Minutenangabe), damit die Dedup-Logik der
`Notifications` greift und nicht alle 15 Minuten dieselbe Meldung neu schickt. Alles Variable steht im
`detail`-Feld, das der CEO per Rueckfrage abrufen kann.
"""
from __future__ import annotations

from datetime import datetime

# Schluessel -> Meldetext (konstant, damit die Dedup der Notifications greift).
TEXTE = {
    "queue_stau": "Cutter-Queue steht — Aufträge werden nicht abgeholt.",
    "job_haengt": "Ein Cutter-Auftrag hängt seit Stunden im Status „läuft“.",
    "worker_stumm": "Der Cutter-Worker (MACO470) meldet sich nicht mehr.",
    "kein_reel": "Kein neues Reel — der nächtliche Lauf hat nichts geliefert.",
}


def _ts(wert) -> datetime | None:
    """ISO-Zeitstempel oder Unix-Sekunden robust zu datetime. Unlesbares -> None (kein Fehlalarm)."""
    if wert is None or wert == "":
        return None
    if isinstance(wert, (int, float)):
        try:
            return datetime.fromtimestamp(float(wert))
        except (OverflowError, OSError, ValueError):
            return None
    text = str(wert).strip().replace("Z", "")
    if "+" in text[10:]:                       # Zeitzonen-Offset abschneiden -> naive Ortszeit
        text = text[:10] + text[10:].split("+")[0]
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _alter_min(wert, jetzt: datetime) -> float | None:
    t = _ts(wert)
    return None if t is None else (jetzt - t).total_seconds() / 60.0


def _dauer(minuten: float) -> str:
    if minuten < 90:
        return f"{minuten:.0f} Minuten"
    if minuten < 60 * 48:
        return f"{minuten / 60:.1f} Stunden"
    return f"{minuten / 1440:.1f} Tagen"


def pruefe(*, jobs: list[dict] | None = None, herzschlag=None, letztes_reel=None,
           jetzt: datetime | None = None, stau_min: float = 30, haenger_min: float = 90,
           herz_min: float = 20, reel_stunden: float = 30) -> list[dict]:
    """Prueft den Betriebszustand und gibt die Befunde zurueck (leer = alles in Ordnung).

    `jobs`: Cutter-Jobs (Felder status/created_at/updated_at/projekt) -- aus dem lokalen Job-Cache.
    `herzschlag`: Zeitstempel des letzten Queue-Abrufs; None -> Pruefung 3 entfaellt (kein Fehlalarm,
    solange die Web-App den Herzschlag noch nicht schreibt).
    `letztes_reel`: Zeitstempel des zuletzt eingereichten Reels; None -> Pruefung 4 entfaellt.
    Jeder Befund: {schluessel, text, detail}.
    """
    jetzt = jetzt or datetime.now()
    jobs = jobs or []
    befunde: list[dict] = []

    wartend = [(j, a) for j in jobs if (j.get("status") == "queued")
               and (a := _alter_min(j.get("created_at"), jetzt)) is not None and a > stau_min]
    if wartend:
        aeltester = max(wartend, key=lambda p: p[1])
        befunde.append({
            "schluessel": "queue_stau", "text": TEXTE["queue_stau"],
            "detail": (f"{len(wartend)} Auftrag/Auftraege wartet seit ueber {stau_min:.0f} Minuten. "
                       f"Aeltester: „{aeltester[0].get('projekt', '?')}“ seit {_dauer(aeltester[1])}. "
                       f"Pruefen: laeuft der Dienst `cutter-worker` auf dem MACO470? "
                       f"(WSL-Instanz kann heruntergefahren sein.)")})

    haengend = [(j, a) for j in jobs if (j.get("status") == "running")
                and (a := _alter_min(j.get("updated_at") or j.get("created_at"), jetzt)) is not None
                and a > haenger_min]
    if haengend:
        aeltester = max(haengend, key=lambda p: p[1])
        befunde.append({
            "schluessel": "job_haengt", "text": TEXTE["job_haengt"],
            "detail": (f"{len(haengend)} Auftrag/Auftraege im Status „running“. Aeltester: "
                       f"„{aeltester[0].get('projekt', '?')}“ seit {_dauer(aeltester[1])}. "
                       f"Wahrscheinlich ist der Worker mitten im Schnitt gestorben.")})

    herz = _alter_min(herzschlag, jetzt)
    if herz is not None and herz > herz_min:
        befunde.append({
            "schluessel": "worker_stumm", "text": TEXTE["worker_stumm"],
            "detail": (f"Letzter Queue-Abruf vor {_dauer(herz)} (normal alle 20 Sekunden). "
                       f"Der Worker holt also nichts mehr ab — auch wenn gerade nichts wartet.")})

    reel = _alter_min(letztes_reel, jetzt)
    if reel is not None and reel > reel_stunden * 60:
        befunde.append({
            "schluessel": "kein_reel", "text": TEXTE["kein_reel"],
            "detail": (f"Letztes eingereichtes Reel vor {_dauer(reel)}. Der naechtliche Lauf auf der NAS "
                       f"laeuft um 03:00 — entweder er startet nicht oder er findet keine Clips.")})

    return befunde
