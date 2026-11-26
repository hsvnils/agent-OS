"""Kennzahlen der Hanserautisch-App (APP_KENNZAHLEN_ROADMAP AK1/AK3, CEO-Go 2026-11-26).

LUNA holt einmal taeglich die Tagessummen der App ueber eine feste HTTPS-Function (nur GET, eigenes Lese-Token) und legt
sie im Archiv `app_kennzahlen/log.jsonl` auf der NAS ab. Das Archiv ist die Quelle aller Zeitreihen, auch wenn die App
einmal nicht erreichbar ist.

Schutzregeln (CISO AK0, CEO):
- Token nur aus der Umgebung (`HANSERAUTISCH_LUNA_API_TOKEN`), nie in Log, Fehlertext, Rueckgabe, Datei oder Repo.
- Nur diese eine Adresse, nur GET, TLS mit Zertifikatspruefung, Zeitlimit; Antwort wird auf das Schema geprueft.
- Abo- und Umsatzzahlen gehen an **kein** KI-Modell: kein Chat-Werkzeug, Meldungen entstehen hier im Code und werden in
  den Chat-Werkzeugen fuer Meldungen ausgeblendet (`QUELLE`).
"""
from __future__ import annotations

import json
import os
import re
import ssl
import threading
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

QUELLE_URL = "https://yygrgcvepxrfbiaxvrmb.supabase.co/functions/v1/luna-kennzahlen"
TOKEN_ENV = "HANSERAUTISCH_LUNA_API_TOKEN"
QUELLE = "app_kennzahlen"                     # Kennung der Meldungen (Outbox) -> von Chat-Werkzeugen ausgeblendet
MESSBEGINN = "2026-05-14"
MAX_TAGE = 400
START = (6, 30)                              # taeglicher Lauf ab 06:30 Berlin
FRISCHE_PRUEFUNG = (6, 45)                   # tagesabschluss_lauf fuer gestern muss um 06:45 da sein
FRISCHE_STUNDEN = 30
WIEDERHOLEN_MIN = (5, 15, 45)                # nach 502 (und Netzfehlern)
MODERATION_STUNDEN = 24
FUNCTION_FEHLER_MAX = 5
ABO_MEILENSTEINE = (100, 250, 500, 750, 1000)
ZEITLIMIT = 60

_DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_KENNZAHL = re.compile(r"^[a-z0-9_]{1,64}$")

# Kennzahl-Katalog (Uebergabe Teil B, Abschnitt 3): art ereignis = je Tag (fehlende Zeile = 0 ab `ab`),
# moment = Zustand am Tagesende (erst ab 2026-11-24; fehlende Zeile = kein Wert), lauf = Tagesabschluss;
# luecke = nur an Spieltagen (Datum = letzter Anpfiff), fehlende Tage sind kein Spieltag statt 0.
KATALOG: dict[str, dict] = {
    "registrierungen": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Registrierungen"},
    "registrierte_gesamt": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Registrierte gesamt", "stand": True},
    "kontoloeschungen": {"ab": "2026-11-25", "art": "ereignis", "einheit": "anzahl", "text": "Kontolöschungen"},
    "tipps": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Tipps"},
    "tippende_konten": {"ab": "2026-05-14", "art": "ereignis", "luecke": True, "einheit": "anzahl", "text": "Tippende Konten je Spieltag"},
    "tippquote_registriert": {"ab": "2026-05-14", "art": "ereignis", "luecke": True, "einheit": "quote", "text": "Tippquote je Spieltag"},
    "chatnachrichten": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Chatnachrichten"},
    "chatnachrichten_entfernt": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Chat: entfernt"},
    "chatnachrichten_stunde": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Chat je Stunde"},
    "checkins": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Check-ins"},
    "freundschaften_angenommen": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Freundschaften"},
    "fangesaenge": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Fangesänge"},
    "fangesang_bewertungen": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Fangesang-Bewertungen"},
    "mitfahrangebote": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Mitfahren"},
    "stadionbewertungen": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Stadionbewertungen"},
    "abos_neu": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Neue Abos"},
    "abo_bewegungen": {"ab": "2026-11-25", "art": "ereignis", "einheit": "anzahl", "text": "Abo-Bewegungen"},
    "pushes": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Pushes"},
    "pushes_art": {"ab": "2026-05-14", "art": "ereignis", "einheit": "anzahl", "text": "Pushes je Art"},
    "cron_laeufe": {"ab": "2026-11-18", "art": "ereignis", "einheit": "anzahl", "text": "Cron-Läufe"},
    "cron_fehlschlaege": {"ab": "2026-11-18", "art": "ereignis", "einheit": "anzahl", "text": "Cron-Fehlschläge"},
    "function_fehler": {"ab": "2026-11-25", "art": "ereignis", "einheit": "anzahl", "text": "Function-Fehler"},
    "function_fehler_stunden_erfasst": {"ab": "2026-11-25", "art": "ereignis", "einheit": "stunden", "text": "Function-Fehler: erfasste Stunden"},
    "registrierte_stand": {"ab": "2026-11-24", "art": "moment", "einheit": "anzahl", "text": "Konten (Stand)"},
    "abos_aktiv": {"ab": "2026-11-24", "art": "moment", "einheit": "anzahl", "text": "Aktive Abos"},
    "abo_mrr_brutto": {"ab": "2026-11-24", "art": "moment", "einheit": "euro", "text": "MRR brutto"},
    "abo_mrr_netto": {"ab": "2026-11-24", "art": "moment", "einheit": "euro", "text": "MRR netto (Schätzung)"},
    "abo_aequivalente": {"ab": "2026-11-24", "art": "moment", "einheit": "anzahl", "text": "Abo-Äquivalente"},
    "umwandlung_registriert": {"ab": "2026-11-24", "art": "moment", "einheit": "quote", "text": "Umwandlung"},
    "geschenke_auslaufend_30_tage": {"ab": "2026-11-24", "art": "moment", "einheit": "anzahl", "text": "Geschenke, die auslaufen"},
    "push_geraete": {"ab": "2026-11-24", "art": "moment", "einheit": "anzahl", "text": "Push-Geräte"},
    "push_quote": {"ab": "2026-11-24", "art": "moment", "einheit": "quote", "text": "Push-Quote"},
    "store_datenstand_stunden": {"ab": "2026-11-24", "art": "moment", "einheit": "stunden", "text": "Store-Datenstand"},
    "lieblingsverein": {"ab": "2026-11-24", "art": "moment", "einheit": "anzahl", "text": "Lieblingsvereine"},
    "freundschaftsanfragen_offen": {"ab": "2026-11-24", "art": "moment", "einheit": "anzahl", "text": "Offene Freundschaftsanfragen"},
    "moderation_offen": {"ab": "2026-11-24", "art": "moment", "einheit": "anzahl", "text": "Offene Moderation"},
    "moderation_aeltester_stunden": {"ab": "2026-11-24", "art": "moment", "einheit": "stunden", "text": "Ältester offener Eintrag"},
    "datenbank_mb": {"ab": "2026-11-24", "art": "moment", "einheit": "mb", "text": "Datenbankgröße"},
    "tagesabschluss_lauf": {"ab": "2026-05-14", "art": "lauf", "einheit": "anzahl", "text": "Tagesabschluss-Lauf"},
}


class AbrufFehler(Exception):
    """Fehler beim Abruf -- enthaelt nur Status und einen festen Text, nie Token oder Antwort-Inhalt."""

    def __init__(self, status: int, text: str):
        super().__init__(f"{status}: {text}")
        self.status = status
        self.text = text


# -- Zeit ----------------------------------------------------------------------------------------------------------

def _tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Berlin")
    except Exception:                                         # pragma: no cover - ohne tzdata
        return timezone(timedelta(hours=1))


def jetzt_berlin() -> datetime:
    return datetime.now(_tz())


def _iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_ts(s) -> datetime | None:
    if not isinstance(s, str) or not s:
        return None
    t = s.strip().replace("Z", "+00:00").replace(" ", "T", 1)
    m = re.match(r"^(.*T\d{2}:\d{2}:\d{2})(\.\d+)?(.*)$", t)  # Bruchteile auf 6 Stellen bringen (Python < 3.11)
    if m:
        frac = (m.group(2) or "")[:7]
        t = m.group(1) + (frac.ljust(7, "0") if frac else "") + m.group(3)
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def abschnitte(von: str, bis: str, heute: date) -> list[tuple[str, str]]:
    """Zeitraum in Abschnitte von hoechstens 400 Tagen; `bis` nie nach heute (Berlin); leer, wenn von > bis."""
    a, b = date.fromisoformat(von), min(date.fromisoformat(bis), heute)
    out = []
    while a <= b:
        e = min(b, a + timedelta(days=MAX_TAGE - 1))
        out.append((a.isoformat(), e.isoformat()))
        a = e + timedelta(days=1)
    return out


# -- Abruf ---------------------------------------------------------------------------------------------------------

def token_vorhanden(env=None) -> bool:
    return bool(((env if env is not None else os.environ).get(TOKEN_ENV) or "").strip())


_FEHLERTEXT = {400: "Zeitraum falsch (Fehler im eigenen Code)", 401: "Token fehlt oder falsch",
               405: "falsche Methode (Fehler im eigenen Code)", 500: "Function in der App nicht eingerichtet",
               502: "Datenbank der App nicht erreichbar"}


def _urlopen(req, timeout):                                   # TLS mit Zertifikatspruefung (Standard-Kontext)
    return urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context())


def abrufen(von: str, bis: str, *, env=None, oeffnen=None) -> dict:
    """Ein GET an die feste Adresse. Gibt die geprueften Zeilen zurueck oder wirft `AbrufFehler` (ohne Geheimnisse)."""
    if not (_DATUM.match(von or "") and _DATUM.match(bis or "")):
        raise AbrufFehler(400, "Zeitraum falsch (Fehler im eigenen Code)")
    tok = ((env if env is not None else os.environ).get(TOKEN_ENV) or "").strip()
    if not tok:
        raise AbrufFehler(401, "Token fehlt in der Umgebung")
    req = urllib.request.Request(f"{QUELLE_URL}?von={von}&bis={bis}", method="GET",
                                 headers={"Authorization": "Bearer " + tok, "Accept": "application/json",
                                          "User-Agent": "LUNA-app-kennzahlen"})
    try:
        with (oeffnen or _urlopen)(req, ZEITLIMIT) as r:
            body = r.read(20_000_000)
    except urllib.error.HTTPError as exc:
        code = int(getattr(exc, "code", 0) or 0)
        raise AbrufFehler(code, _FEHLERTEXT.get(code, "unerwartete Antwort")) from None
    except Exception as exc:                                  # Netz, TLS, Zeitlimit -- nur der Typ, nie der Text
        raise AbrufFehler(0, f"Verbindung fehlgeschlagen ({exc.__class__.__name__})") from None
    try:
        j = json.loads(body.decode("utf-8"))
    except Exception:
        raise AbrufFehler(200, "Antwort ist kein gueltiges JSON") from None
    return schema_pruefen(j)


def schema_pruefen(j) -> dict:
    """Prueft die Antwort. Ungueltige Gesamtantwort -> AbrufFehler; ungueltige Zeilen werden verworfen und gezaehlt."""
    if not isinstance(j, dict) or j.get("ok") is not True or not isinstance(j.get("zeilen"), list):
        raise AbrufFehler(200, "Antwort hat nicht das erwartete Format")
    gut, verworfen = [], 0
    for z in j["zeilen"]:
        if not isinstance(z, dict):
            verworfen += 1
            continue
        d, k, d1, d2, w, st = (z.get("datum"), z.get("kennzahl"), z.get("dim1", ""), z.get("dim2", ""),
                               z.get("wert"), z.get("stand"))
        d1 = "" if d1 is None else d1
        d2 = "" if d2 is None else d2
        if not (isinstance(d, str) and _DATUM.match(d) and isinstance(k, str) and _KENNZAHL.match(k)
                and isinstance(d1, str) and isinstance(d2, str) and len(d1) <= 120 and len(d2) <= 120
                and isinstance(w, (int, float)) and not isinstance(w, bool) and w == w and _parse_ts(st)):
            verworfen += 1
            continue
        gut.append({"datum": d, "kennzahl": k, "dim1": d1, "dim2": d2, "wert": w, "stand": st})
    return {"zeilen": gut, "verworfen": verworfen, "anzahl": j.get("anzahl"),
            "revision": str(j.get("revision") or "")[:40]}


# -- Archiv --------------------------------------------------------------------------------------------------------

def _schluessel(z: dict) -> str:
    return "\x1f".join((z["datum"], z["kennzahl"], z.get("dim1", ""), z.get("dim2", "")))


class Archiv:
    """Ereignis-Log `log.jsonl`: `wert` (Upsert nach `stand`), `abruf` (nur Zaehlungen), `meldung` (einmal je Anlass)."""

    def __init__(self, ordner: str | Path):
        self.pfad = Path(ordner) / "log.jsonl"
        self._lock = threading.Lock()
        self._cache: tuple | None = None

    def _append(self, evs: list[dict]) -> None:
        if not evs:
            return
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pfad, "a", encoding="utf-8") as f:
            for e in evs:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def _laden(self) -> dict:
        try:
            st = self.pfad.stat()
            sig = (st.st_mtime_ns, st.st_size)
        except FileNotFoundError:
            return {"werte": {}, "abrufe": [], "meldungen": set()}
        if self._cache and self._cache[0] == sig:
            return self._cache[1]
        werte, abrufe, meldungen = {}, [], set()
        with open(self.pfad, encoding="utf-8") as f:
            for zeile in f:
                try:
                    e = json.loads(zeile)
                except ValueError:
                    continue
                t = e.get("typ")
                if t == "wert":
                    k = _schluessel(e)
                    alt = werte.get(k)
                    if alt is None or (_parse_ts(e["stand"]) or datetime.min.replace(tzinfo=timezone.utc)) > (
                            _parse_ts(alt["stand"]) or datetime.min.replace(tzinfo=timezone.utc)):
                        werte[k] = e
                elif t == "abruf":
                    abrufe.append(e)
                elif t == "meldung":
                    meldungen.add(e.get("schluessel"))
        d = {"werte": werte, "abrufe": abrufe, "meldungen": meldungen}
        self._cache = (sig, d)
        return d

    def werte(self) -> dict:
        return self._laden()["werte"]

    def abrufe(self) -> list[dict]:
        return self._laden()["abrufe"]

    def uebernehmen(self, zeilen: list[dict], abgerufen_am: str) -> tuple[int, int]:
        """Upsert: neuer Schluessel -> neu; neuerer `stand` -> aktualisiert; sonst nichts. Gibt (neu, aktualisiert)."""
        with self._lock:
            werte = self.werte()
            neu = akt = 0
            evs, gesehen = [], {}
            for z in zeilen:
                k = _schluessel(z)
                alt = gesehen.get(k) or werte.get(k)
                if alt is not None and (_parse_ts(z["stand"]) or datetime.min.replace(tzinfo=timezone.utc)) <= (
                        _parse_ts(alt["stand"]) or datetime.min.replace(tzinfo=timezone.utc)):
                    continue
                if k in werte or k in gesehen:
                    akt += 1
                else:
                    neu += 1
                e = {"typ": "wert", **z, "abgerufen_am": abgerufen_am}
                gesehen[k] = e
                evs.append(e)
            self._append(evs)
            return neu, akt

    def protokoll(self, ev: dict) -> None:
        with self._lock:
            self._append([{"typ": "abruf", **ev}])

    def gemeldet(self, schluessel: str) -> bool:
        return schluessel in self._laden()["meldungen"]

    def melden_vermerken(self, schluessel: str, ts: str) -> None:
        with self._lock:
            self._append([{"typ": "meldung", "schluessel": schluessel, "ts": ts}])

    def letzter_tag(self) -> str | None:
        w = self.werte()
        return max((v["datum"] for v in w.values()), default=None)

    def leer(self) -> bool:
        return not self.werte()


# -- Abholen (Erstabruf, taeglich, Nachholen, manuell) -------------------------------------------------------------

def zeitraum(archiv: Archiv, heute: date) -> tuple[str, str]:
    """Erstabruf ab Messbeginn; sonst ab min(gestern-3, letzter gespeicherter Tag-3) bis gestern."""
    gestern = heute - timedelta(days=1)
    lt = archiv.letzter_tag()
    if not lt:
        return MESSBEGINN, gestern.isoformat()
    von = min(gestern - timedelta(days=3), date.fromisoformat(lt) - timedelta(days=3))
    return max(von, date.fromisoformat(MESSBEGINN)).isoformat(), gestern.isoformat()


def abholen(archiv: Archiv, *, art: str = "lauf", jetzt: datetime | None = None, abruf=abrufen, env=None) -> dict:
    """Holt den faelligen Zeitraum in Abschnitten, speichert per Upsert und protokolliert (nur Zaehlungen)."""
    jetzt = jetzt or jetzt_berlin()
    heute = jetzt.astimezone(_tz()).date()
    von, bis = zeitraum(archiv, heute)
    ts = _iso(jetzt)
    erg = {"ok": True, "status": 200, "von": von, "bis": bis, "zeilen": 0, "neu": 0, "aktualisiert": 0, "verworfen": 0}
    for a, b in abschnitte(von, bis, heute):
        try:
            r = abruf(a, b, env=env) if env is not None else abruf(a, b)
        except AbrufFehler as exc:
            erg.update(ok=False, status=exc.status, fehler=exc.text)
            break
        n, u = archiv.uebernehmen(r["zeilen"], ts)
        erg["zeilen"] += len(r["zeilen"])
        erg["neu"] += n
        erg["aktualisiert"] += u
        erg["verworfen"] += r.get("verworfen", 0)
        if isinstance(r.get("anzahl"), int) and r["anzahl"] != len(r["zeilen"]) + r.get("verworfen", 0):
            erg["anzahl_abweichung"] = True
    archiv.protokoll({"ts": ts, "art": art, **{k: v for k, v in erg.items() if k != "ok"}, "ok": erg["ok"]})
    return erg


# -- Taeglicher Lauf und Meldungen ---------------------------------------------------------------------------------

def _berlin_tag(ts: str) -> str:
    t = _parse_ts(ts)
    return t.astimezone(_tz()).date().isoformat() if t else ""


def _melde(archiv: Archiv, notify, schluessel: str, text: str, jetzt: datetime, kategorie: str = "fehler") -> bool:
    if archiv.gemeldet(schluessel):
        return False
    archiv.melden_vermerken(schluessel, _iso(jetzt))
    if notify:
        notify("📱 App: " + text, abteilung="CDO", kategorie=kategorie, quelle=QUELLE, nach_briefing=False)
    return True


def lauf(archiv: Archiv, *, jetzt: datetime | None = None, notify=None, abruf=abrufen, env=None) -> dict:
    """Wird jede Minute aufgerufen. Holt bei Faelligkeit ab (06:30, Wiederholung 5/15/45 Min.), prueft und meldet."""
    jetzt = (jetzt or jetzt_berlin()).astimezone(_tz())
    heute = jetzt.date().isoformat()
    gestern = (jetzt.date() - timedelta(days=1)).isoformat()
    heutige = [a for a in archiv.abrufe() if a.get("art") == "lauf" and _berlin_tag(a.get("ts", "")) == heute]
    erfolg = any(a.get("ok") and a.get("bis") == gestern for a in heutige)
    out = {"abgeholt": False}
    if not erfolg:
        fehl = [a for a in heutige if not a.get("ok")]
        stopp = any(a.get("status") in (400, 401, 405, 500) or (a.get("status") == 200) for a in fehl)
        faellig = False
        if not stopp and len(fehl) <= len(WIEDERHOLEN_MIN):
            if not fehl:
                faellig = archiv.leer() or (jetzt.hour, jetzt.minute) >= START
            else:
                letzt = _parse_ts(fehl[-1]["ts"])
                faellig = bool(letzt) and jetzt >= letzt + timedelta(minutes=WIEDERHOLEN_MIN[len(fehl) - 1])
        if faellig:
            erg = abholen(archiv, art="lauf", jetzt=jetzt, abruf=abruf, env=env)
            out.update(abgeholt=True, ergebnis=erg)
            if erg["ok"]:
                erfolg = True
            else:
                fehl.append(erg)
                st = erg.get("status")
                if st == 401:
                    _melde(archiv, notify, f"401:{heute}", "Abruf abgelehnt (401) – Token fehlt oder ist gesperrt. "
                           "LUNA versucht es heute nicht erneut.", jetzt)
                elif st in (400, 405, 500) or st == 200:
                    _melde(archiv, notify, f"fehler:{heute}", f"Abruf fehlgeschlagen ({st}: {erg.get('fehler', '')}). "
                           "Kein neuer Versuch heute.", jetzt)
                elif len(fehl) >= 2:
                    _melde(archiv, notify, f"zweimal:{heute}", f"Zwei Abrufe hintereinander gescheitert ({st or 'Netz'}: "
                           f"{erg.get('fehler', '')}). LUNA versucht es weiter.", jetzt)
                if len(fehl) > len(WIEDERHOLEN_MIN) and st not in (400, 401, 405, 500, 200):
                    _melde(archiv, notify, f"aufgegeben:{heute}", "Alle Abrufversuche heute gescheitert. Daten fehlen bis "
                           "morgen; „Jetzt abrufen“ in LUNA-OS versucht es von Hand.", jetzt)
    if erfolg:
        out["meldungen"] = pruefen(archiv, jetzt=jetzt, notify=notify)
    return out


def _summe(werte: dict, datum: str, kennzahl: str) -> tuple[float, int]:
    s, n = 0.0, 0
    for v in werte.values():
        if v["datum"] == datum and v["kennzahl"] == kennzahl:
            s += v["wert"]
            n += 1
    return s, n


def _letzter_wert(werte: dict, kennzahl: str, dim1: str = "", dim2: str = "") -> tuple[str, float] | None:
    best = None
    for v in werte.values():
        if v["kennzahl"] == kennzahl and v.get("dim1", "") == dim1 and v.get("dim2", "") == dim2:
            if best is None or v["datum"] > best[0]:
                best = (v["datum"], v["wert"])
    return best


def pruefen(archiv: Archiv, *, jetzt: datetime, notify=None) -> list[str]:
    """Inhaltliche Meldungen nach einem erfolgreichen Abruf -- jede nur einmal je Anlass."""
    jetzt = jetzt.astimezone(_tz())
    gestern = (jetzt.date() - timedelta(days=1)).isoformat()
    w = archiv.werte()
    gesendet = []

    def m(schl, text, kat="fehler"):
        if _melde(archiv, notify, schl, text, jetzt, kat):
            gesendet.append(schl)

    if (jetzt.hour, jetzt.minute) >= FRISCHE_PRUEFUNG:
        ta = [v for v in w.values() if v["kennzahl"] == "tagesabschluss_lauf" and v["datum"] == gestern]
        st = max((_parse_ts(v["stand"]) for v in ta), default=None)
        if not ta:
            m(f"frische:{gestern}", f"Kein Tagesabschluss-Lauf der App für {gestern} – der Nachtlauf ist wohl ausgefallen.")
        elif st and jetzt - st > timedelta(hours=FRISCHE_STUNDEN):
            m(f"frische:{gestern}", f"Tagesabschluss-Lauf für {gestern} ist älter als {FRISCHE_STUNDEN} Stunden.")
    for v in w.values():
        if v["kennzahl"] == "moderation_aeltester_stunden" and v["datum"] == gestern and v["wert"] > MODERATION_STUNDEN:
            m(f"moderation:{gestern}:{v.get('dim1', '')}",
              f"Offene Moderation ({v.get('dim1') or 'gesamt'}) wartet seit über {MODERATION_STUNDEN} Stunden.")
    cron, _ = _summe(w, gestern, "cron_fehlschlaege")
    if cron > 0:
        m(f"cron:{gestern}", f"Cronjobs der App am {gestern}: {int(cron)} Fehlschläge.")
    fn, _ = _summe(w, gestern, "function_fehler")
    if fn > FUNCTION_FEHLER_MAX:
        m(f"function:{gestern}", f"Function-Fehler der App am {gestern}: {int(fn)} (Grenze {FUNCTION_FEHLER_MAX}).")
    # Meilensteine: einmal je Schwelle. Beim allerersten Abruf bereits erreichte Schwellen still vermerken.
    basis = archiv.gemeldet("meilenstein-basis")
    aeq = _letzter_wert(w, "abo_aequivalente")
    reg = _letzter_wert(w, "registrierte_gesamt")
    schwellen = []
    if aeq:
        schwellen += [(f"meilenstein:abo:{s}", f"🎉 {s} Abo-Äquivalente erreicht (Ziel 1.000).")
                      for s in ABO_MEILENSTEINE if aeq[1] >= s]
    if reg:
        schwellen += [(f"meilenstein:reg:{t}", f"🎉 {t:,} registrierte Konten erreicht.".replace(",", "."))
                      for t in range(1000, int(reg[1]) + 1, 1000)]
    for schl, text in schwellen:
        if basis:
            m(schl, text, "info")
        elif not archiv.gemeldet(schl):
            archiv.melden_vermerken(schl, _iso(jetzt))
    if not basis:
        archiv.melden_vermerken("meilenstein-basis", _iso(jetzt))
    return gesendet


# -- Auswertung fuer LUNA-OS (deterministisch, kein Modell) --------------------------------------------------------

def status(archiv: Archiv, env=None) -> dict:
    """Nur Zaehlungen und Zeitpunkte -- keine Werte."""
    w = archiv.werte()
    ab = archiv.abrufe()
    letzt = ab[-1] if ab else None
    unbekannt = sorted({v["kennzahl"] for v in w.values()} - set(KATALOG))
    return {"ok": True, "token": token_vorhanden(env), "zeilen": len(w),
            "tage": len({v["datum"] for v in w.values()}), "erster_tag": min((v["datum"] for v in w.values()), default=None),
            "letzter_tag": max((v["datum"] for v in w.values()), default=None),
            "datenstand": max((v["stand"] for v in w.values()), key=lambda s: _parse_ts(s), default=None),
            "letzter_abruf": {k: letzt.get(k) for k in ("ts", "art", "status", "ok", "von", "bis", "zeilen", "neu",
                                                        "aktualisiert", "verworfen", "fehler")} if letzt else None,
            "abrufe": len(ab), "unbekannt": unbekannt,
            "zeilen_je_kennzahl": _zaehle(w)}


def _zaehle(w: dict) -> dict:
    c: dict[str, int] = {}
    for v in w.values():
        c[v["kennzahl"]] = c.get(v["kennzahl"], 0) + 1
    return dict(sorted(c.items()))


def stoerung(archiv: Archiv, *, heute: date | None = None, env=None) -> str | None:
    """Glocke in LUNA-OS (CEO E4): Text einer Stoerung (ohne Werte) oder None."""
    heute = heute or jetzt_berlin().date()
    if not token_vorhanden(env):
        return "Token für die App-Kennzahlen fehlt in der Umgebung"
    ab = [a for a in archiv.abrufe() if a.get("art") in ("lauf", "manuell")]
    if ab and not ab[-1].get("ok"):
        return f"Letzter Abruf der App-Kennzahlen gescheitert ({ab[-1].get('status') or 'Netz'})"
    lt = archiv.letzter_tag()
    if lt and date.fromisoformat(lt) < heute - timedelta(days=2) and (jetzt_berlin().hour, jetzt_berlin().minute) >= START:
        return f"App-Kennzahlen nicht aktuell (letzter Tag {lt})"
    return None


_ZEILE = re.compile(r"^[\s|,;\"']*([a-z][a-z0-9_]*)[\s|,;\"']+(\d+)[\s|,;\"']+(-?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?)")


def abgleich(archiv: Archiv, datum: str, text: str) -> dict:
    """Kontroll-Abgleich (AK2): Ergebnis der Supabase-Kontrollabfrage (kennzahl, zeilen, summe) gegen das Archiv."""
    if not _DATUM.match(datum or ""):
        return {"ok": False, "hinweis": "Datum als JJJJ-MM-TT angeben."}
    soll = {}
    for zeile in (text or "").splitlines():
        mm = _ZEILE.match(zeile.strip())
        if mm and mm.group(1) not in ("kennzahl", "zeilen", "summe"):
            soll[mm.group(1)] = (int(mm.group(2)), float(mm.group(3).replace(",", ".")))
    if not soll:
        return {"ok": False, "hinweis": "Keine Zeilen erkannt. Erwartet: kennzahl, zeilen, summe je Zeile."}
    w = archiv.werte()
    ist = {}
    for v in w.values():
        if v["datum"] == datum:
            n, s = ist.get(v["kennzahl"], (0, 0.0))
            ist[v["kennzahl"]] = (n + 1, s + v["wert"])
    zeilen = []
    for k in sorted(set(soll) | set(ist)):
        sn, ss = soll.get(k, (0, 0.0))
        i_n, i_s = ist.get(k, (0, 0.0))
        gleich = sn == i_n and abs(ss - i_s) <= max(1e-6, 1e-9 * abs(ss))
        zeilen.append({"kennzahl": k, "zeilen_soll": sn, "zeilen_ist": i_n, "summe_soll": ss, "summe_ist": round(i_s, 9),
                       "gleich": gleich})
    return {"ok": True, "datum": datum, "gleich": all(z["gleich"] for z in zeilen), "zeilen": zeilen,
            "abweichend": sum(1 for z in zeilen if not z["gleich"])}


def saison_start(heute: date) -> date:
    """Saison = 01.07. bis 30.06. (CEO E2)."""
    return date(heute.year if heute.month >= 7 else heute.year - 1, 7, 1)


def auswertung(archiv: Archiv, zeitraum: str = "30", heute: date | None = None) -> dict:
    """Daten fuer die Kachel: Tagesreihen je (kennzahl, dim1, dim2) im Zeitraum, fehlende Tage = 0 ab Messbeginn."""
    heute = heute or jetzt_berlin().date()
    gestern = heute - timedelta(days=1)
    w = archiv.werte()
    erster = date.fromisoformat(min((v["datum"] for v in w.values()), default=MESSBEGINN))
    if zeitraum == "7":
        von = gestern - timedelta(days=6)
    elif zeitraum == "saison":
        von = saison_start(heute)
    elif zeitraum == "alles":
        von = min(erster, date.fromisoformat(MESSBEGINN))
    else:
        zeitraum, von = "30", gestern - timedelta(days=29)
    tage = [(von + timedelta(days=i)).isoformat() for i in range((gestern - von).days + 1)]
    reihen: dict[str, dict] = {}
    for v in w.values():
        if v["kennzahl"] not in KATALOG:
            continue
        k = "|".join((v["kennzahl"], v.get("dim1", ""), v.get("dim2", "")))
        reihen.setdefault(k, {"kennzahl": v["kennzahl"], "dim1": v.get("dim1", ""), "dim2": v.get("dim2", ""), "werte": {}})
        reihen[k]["werte"][v["datum"]] = v["wert"]
    out = []
    for r in reihen.values():
        kat = KATALOG[r["kennzahl"]]
        werte = []
        for t in tage:
            if t in r["werte"]:
                werte.append(r["werte"][t])
            elif kat["art"] == "ereignis" and t >= kat["ab"] and not kat.get("stand") and not kat.get("luecke"):
                werte.append(0)
            else:
                werte.append(None)
        r_alle = sorted(r["werte"].items())
        letzt = r_alle[-1] if r_alle else (None, None)
        out.append({"kennzahl": r["kennzahl"], "dim1": r["dim1"], "dim2": r["dim2"], "werte": werte,
                    "letzter_tag": letzt[0], "letzter_wert": letzt[1]})
    unbekannt = len({v["kennzahl"] for v in w.values()} - set(KATALOG))
    return {"ok": True, "zeitraum": zeitraum, "von": tage[0] if tage else None, "bis": gestern.isoformat(), "tage": tage,
            "reihen": out, "katalog": KATALOG, "unbekannt": unbekannt, "ziel_abo_aequivalente": 1000}


# -- CLI (nur Zaehlungen) ------------------------------------------------------------------------------------------

def _main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="App-Kennzahlen: Abruf (Ausgabe nur Zaehlungen, nie Werte)")
    p.add_argument("--ordner", default=str(Path(__file__).resolve().parents[2] / "app_kennzahlen"))
    p.add_argument("--dry-run", action="store_true", help="abrufen und zaehlen, nichts speichern")
    p.add_argument("--jetzt", action="store_true", help="faelligen Zeitraum abholen und speichern")
    a = p.parse_args(argv)
    ar = Archiv(a.ordner)
    if a.dry_run:
        heute = jetzt_berlin().date()
        von, bis = zeitraum(ar, heute)
        c: dict[str, int] = {}
        try:
            for x, y in abschnitte(von, bis, heute):
                for z in abrufen(x, y)["zeilen"]:
                    c[z["kennzahl"]] = c.get(z["kennzahl"], 0) + 1
        except AbrufFehler as exc:
            print(f"Fehler {exc.status}: {exc.text}")
            return 1
        print(f"Zeitraum {von} bis {bis}: {sum(c.values())} Zeilen, {len(c)} Kennzahlen")
        print(", ".join(f"{k}:{n}" for k, n in sorted(c.items())))
        return 0
    if a.jetzt:
        erg = abholen(ar, art="manuell")
        print({k: v for k, v in erg.items()})
        return 0 if erg["ok"] else 1
    s = status(ar)
    print({k: s[k] for k in ("token", "zeilen", "tage", "erster_tag", "letzter_tag", "letzter_abruf", "unbekannt")})
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
