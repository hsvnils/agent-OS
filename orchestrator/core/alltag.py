"""LUNA im Alltag -- Paket A der JARVIS_ALLTAG_ROADMAP (CEO-Go 2026-10-28), regelbasiert, kein Sprachmodell.

- **J2 Sprechfassung:** das Morgen-Briefing als Text fuer die Sprachausgabe (ohne Emojis, Links, Kennungen), gekuerzt
  an einer Satzgrenze. Gesprochen wird nur, wenn der CEO es in den Einstellungen einschaltet (ElevenLabs = Kosten).
- **J3 Abfahrt:** Termine von heute mit Ort -> Fahrzeit ab der Firmenadresse (OSRM, **ohne Live-Verkehr**, daher
  Puffer) -> Erinnerung „in 10 Min. losfahren“ genau einmal je Termin.
- **J4 Kundenpflege:** Kunden ohne Kontakt seit N Tagen, Geburtstage von Ansprechpartnern, Jahrestag einer Kampagne
  -> Punkte im Handlungsbedarf („Zu erledigen“).
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta

# -- J2 Sprechfassung ------------------------------------------------------------------------------------------------

SPRECH_MAX = 2400                                   # ca. 2,5 Minuten
_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍⬀-⯿]")
_URL = re.compile(r"https?://\S+")
_KENNUNG = re.compile(r"\(#[0-9a-f]{3,}\)|\(Details:[^)]*\)|#[0-9a-f]{4,}\b", re.I)


def sprechfassung(text: str, *, max_zeichen: int = SPRECH_MAX) -> str:
    """Briefing-Text -> vorlesbarer Text (Aufzaehlungszeichen zu Saetzen, Symbole weg, an Satzgrenze gekuerzt)."""
    zeilen = []
    for z in (text or "").splitlines():
        z = _KENNUNG.sub("", _URL.sub("", _EMOJI.sub("", z)))
        z = re.sub(r"[*_`>#|]+", "", z).replace("„", "").replace("“", "").replace('"', "")
        z = re.sub(r"^\s*[-•·–]\s*", "", z)
        z = " ".join(z.split()).strip(" :·-")
        if len(z) < 3:
            continue
        zeilen.append(z if z[-1] in ".!?:" else z + ".")
    out = " ".join(zeilen)
    if len(out) <= max_zeichen:
        return out
    schnitt = out[:max_zeichen]
    ende = max(schnitt.rfind(". "), schnitt.rfind("! "), schnitt.rfind("? "))
    return (schnitt[:ende + 1] if ende > max_zeichen // 2 else schnitt.rsplit(" ", 1)[0] + ".") \
        + " Den Rest findest du im Briefing-Text."


# -- J3 Abfahrt ------------------------------------------------------------------------------------------------------

PUFFER = 0.15                                       # +15 % auf die Fahrzeit (kein Live-Verkehr)
PUFFER_MIN = 10
VORLAUF_MIN = 10                                    # so lange vor der Abfahrt kommt die Erinnerung
_ONLINE = re.compile(r"https?://|zoom|teams|meet\.google|google meet|webex|online|telefon|anruf|skype|discord", re.I)


def braucht_fahrt(ort: str) -> bool:
    o = (ort or "").strip()
    return len(o) >= 5 and not _ONLINE.search(o)


def abfahrt(start: datetime, fahrzeit_min: float) -> datetime:
    """Spaeteste Abfahrt: Fahrzeit + Puffer (15 %, mindestens 10 Min.) vor dem Terminbeginn, auf 5 Min. abgerundet."""
    puffer = max(PUFFER_MIN, fahrzeit_min * PUFFER)
    roh = start - timedelta(minutes=math.ceil(fahrzeit_min + puffer))
    return roh - timedelta(minutes=roh.minute % 5, seconds=roh.second, microseconds=roh.microsecond)


def _zeit(t: str) -> datetime | None:
    if not t or "T" not in t:
        return None                                 # ganztaegig -> keine Fahrt-Erinnerung
    try:
        d = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo:
        from zoneinfo import ZoneInfo
        d = d.astimezone(ZoneInfo("Europe/Berlin")).replace(tzinfo=None)
    return d


def faellige_abfahrten(termine: list[dict], jetzt: datetime, fahrzeit, gesendet) -> list[dict]:
    """Termine (Kalender-Agenda) -> Erinnerungen, die jetzt raus muessen. `fahrzeit(ort)` -> Minuten oder None,
    `gesendet(schluessel)` -> bool. Erinnerung ab `VORLAUF_MIN` vor der Abfahrt bis zum Terminbeginn, einmal je Termin."""
    out = []
    for t in termine:
        start = _zeit(t.get("start", ""))
        if not start or start.date() != jetzt.date() or start <= jetzt or not braucht_fahrt(t.get("ort", "")):
            continue
        if start - jetzt > timedelta(hours=6):
            continue                                # weit weg -> noch nicht rechnen (spart Abfragen)
        schluessel = f"abfahrt:{t.get('id', '')}:{start.isoformat(timespec='minutes')}"
        if gesendet(schluessel):
            continue
        minuten = fahrzeit(t["ort"])
        if not minuten or minuten < 5:
            continue
        ab = abfahrt(start, minuten)
        if jetzt >= ab - timedelta(minutes=VORLAUF_MIN):
            out.append({"schluessel": schluessel, "titel": t.get("titel") or "Termin", "ort": t["ort"], "start": start,
                        "abfahrt": ab, "fahrzeit_min": round(minuten)})
    return out


def abfahrt_text(x: dict, jetzt: datetime) -> str:
    rest = int((x["abfahrt"] - jetzt).total_seconds() // 60)
    wann = (f"in {rest} Min. losfahren (spätestens {x['abfahrt']:%H:%M} Uhr)" if rest > 0
            else f"jetzt losfahren (geplant {x['abfahrt']:%H:%M} Uhr)")
    from urllib.parse import quote
    return (f"🚗 {wann}\n{x['titel']} um {x['start']:%H:%M} Uhr\n📍 {x['ort']}\n"
            f"Fahrzeit ca. {x['fahrzeit_min']} Min. ab Büro, mit Puffer – ohne Live-Verkehr.\n"
            f"https://www.google.com/maps/dir/?api=1&destination={quote(x['ort'])}")


# -- J4 Kundenpflege -------------------------------------------------------------------------------------------------

KONTAKT_TAGE = 60
_KONTAKT_TYPEN = ("angebot_", "auftrag_", "rechnung_", "akte_", "konzept_", "posting_", "kundenpflege_", "mail_antwort")
_INTERN = {"posting_erinnert", "angebot_erinnerungen", "rechnung_erinnerung", "akte_mail_offen"}   # LUNA selbst, kein Kontakt


def letzte_kontakte(eintraege: list[dict]) -> dict[str, str]:
    """Firma -> Datum (ISO) des letzten Vorgangs mit ihr (Angebot, Auftrag, Rechnung, Akte/Mail, ..., „gepflegt“)."""
    from .angebote import AngebotStore
    from .beauftragung import AuftragBuch
    vorgang_firma: dict[str, str] = {}
    for a in AngebotStore._falte(eintraege).values():
        vorgang_firma[a["nummer"]] = a["firma"]
    for a in AuftragBuch._falte(eintraege).values():
        vorgang_firma[a["nummer"]] = a["firma"]
    out: dict[str, str] = {}
    for e in eintraege:
        if not str(e.get("typ", "")).startswith(_KONTAKT_TYPEN) or e.get("typ") in _INTERN:
            continue
        d = e.get("daten") or {}
        firma = d.get("firma") or vorgang_firma.get(d.get("nummer") or "") or vorgang_firma.get(d.get("auftrag") or "") \
            or vorgang_firma.get(str(d.get("id", "")).rsplit("-P", 1)[0]) or vorgang_firma.get(d.get("vorgang") or "")
        if firma:
            out[str(firma).upper()] = max(out.get(str(firma).upper(), ""), str(e.get("ts", ""))[:10])
    return out


def kundenpflege(eintraege: list[dict], firmen: list[dict], heute: date, *, tage: int = KONTAKT_TAGE) -> list[dict]:
    """Hinweise: lange kein Kontakt (nur Firmen mit mindestens einem Auftrag), Geburtstag (heute bis in 3 Tagen),
    Jahrestag einer Kampagne (Leistungsbeginn vor einem Jahr, +-3 Tage). -> [{id, art, firma, titel, detail, datum}]"""
    from .beauftragung import AuftragBuch
    letzte = letzte_kontakte(eintraege)
    erledigt = {(e.get("daten") or {}).get("schluessel") for e in eintraege if e.get("typ") == "kundenpflege_erledigt"}
    auftraege = [a for a in AuftragBuch._falte(eintraege).values() if a.get("status") != "storniert"]
    kunden = {a["firma"] for a in auftraege}
    name = {f["nummer"]: f.get("name") or f["nummer"] for f in firmen}
    out = []
    for nr in sorted(kunden):
        zuletzt = letzte.get(nr)
        if not zuletzt or nr not in name:
            continue
        seit = (heute - date.fromisoformat(zuletzt)).days
        if seit >= tage:
            out.append({"id": f"kp-kontakt:{nr}:{zuletzt}", "art": "kontakt", "firma": nr,
                        "titel": f"Lange nichts gehört: {name[nr]}",
                        "detail": f"Letzter Vorgang vor {seit} Tagen ({zuletzt[8:10]}.{zuletzt[5:7]}.) – kurz melden, nächste "
                                  "Kampagne anbieten?", "datum": ""})
    for f in firmen:
        for ap in f.get("ansprechpartner_liste") or []:
            g = geburtstag(ap.get("geburtstag", ""))
            if not g or ap.get("aktiv") is False:
                continue
            for jahr in (heute.year, heute.year + 1):
                try:
                    tag = date(jahr, g[0], g[1])
                except ValueError:
                    tag = date(jahr, 3, 1)          # 29.02. im Nicht-Schaltjahr
                if 0 <= (tag - heute).days <= 3:
                    wer = " ".join(x for x in (ap.get("vorname"), ap.get("nachname")) if x)
                    out.append({"id": f"kp-geburtstag:{ap['nummer']}:{tag.isoformat()}", "art": "geburtstag",
                                "firma": f["nummer"], "titel": f"🎂 Geburtstag {wer} ({f.get('name') or f['nummer']})",
                                "detail": "heute" if tag == heute else f"am {tag:%d.%m.}", "datum": tag.isoformat()})
    for a in auftraege:
        lv = a.get("leistung_von") or a.get("datum") or ""
        try:
            jahrestag = date.fromisoformat(lv[:10]).replace(year=heute.year)
        except ValueError:
            continue
        if lv[:4] == str(heute.year - 1) and abs((jahrestag - heute).days) <= 3:
            out.append({"id": f"kp-jahrestag:{a['nummer']}", "art": "jahrestag", "firma": a["firma"],
                        "titel": f"Vor einem Jahr: {a.get('titel') or a['nummer']} ({name.get(a['firma'], a['firma'])})",
                        "detail": "Kampagne jährt sich – Folgekampagne anbieten?", "datum": jahrestag.isoformat()})
    return [x for x in out if x["id"] not in erledigt]


def geburtstag(wert: str) -> tuple[int, int] | None:
    """„24.12.“, „24.12.1990“, „1990-12-24“ oder „12-24“ -> (Monat, Tag); sonst None."""
    w = (wert or "").strip()
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.?(\d{2,4})?", w) or None
    if m:
        t, mo = int(m.group(1)), int(m.group(2))
    else:
        m = re.fullmatch(r"(?:\d{4}-)?(\d{1,2})-(\d{1,2})", w)
        if not m:
            return None
        mo, t = int(m.group(1)), int(m.group(2))
    if not (1 <= mo <= 12 and 1 <= t <= 31):
        return None
    return mo, t


# -- J2 Sprachausgabe ------------------------------------------------------------------------------------------------

def elevenlabs_tts(text: str, voice_id: str, key: str) -> bytes | None:
    """Spricht Text mit ElevenLabs (eleven_turbo_v2_5) -> MP3-Bytes, None bei Fehler (gemeinsam fuer LUNA-OS und Bot)."""
    import json
    import urllib.request
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
    payload = json.dumps({"text": text, "model_id": "eleven_turbo_v2_5",
                          "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}).encode()
    req = urllib.request.Request(url, data=payload, method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except Exception as exc:
        print(f"[tts] ElevenLabs-Fehler: {str(exc)[:160]}", flush=True)
        return None
