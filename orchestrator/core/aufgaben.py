"""Eigene To-dos des CEO (TODOS_ROADMAP T1-T3, CEO 2026-10-27).

Frei formulierte Aufgaben -- anders als die Kachel „Zu erledigen“ (`core/todos.py`), die nur aus den Geschaeftsdaten
abgeleitet wird. Anlegen in LUNA-OS (Bereich „✅ To-dos“) oder per Telegram-Nachricht (LUNA-Werkzeug `todo_anlegen`).

- Speicher `todos/log.jsonl` (nur NAS + Backup, nicht im Git): eine Zeile je Ereignis -- `angelegt`, `geaendert`,
  `erledigt`, `geoeffnet`, `geloescht`, `termin` (Kalender-ID), `erinnert` -- es geht nichts verloren.
- **Erinnerung:** Zeitpunkt `JJJJ-MM-TTTHH:MM` (Europe/Berlin). Ohne Uhrzeit, aber mit Faelligkeit: 09:00 am
  Faelligkeitstag. Dazu ein 15-Minuten-Termin in LUNAs Kalender (CEO als Gast, Q0 Nr. 3) und eine Telegram-Nachricht
  zum Zeitpunkt (Bot, alle 5 min) mit „Erledigt“ / „+1 Std.“ / „morgen“.
- Kalender-Termine von To-dos sind LUNAs **eigene, protokollierte** Termine: anlegen, verschieben und beim Erledigen
  loeschen ohne Rueckfrage (CEO 2026-10-27, wie die Beleg-Erinnerungen 2026-09-28).
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

STANDARD_UHRZEIT = "09:00"
TERMIN_MINUTEN = 15
MAX_TITEL, MAX_NOTIZ = 200, 2000
_DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UHR = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_ZEIT = re.compile(r"^\d{4}-\d{2}-\d{2}T([01]\d|2[0-3]):[0-5]\d$")
_ID = re.compile(r"^A-[0-9a-f]{8}$")


def jetzt_lokal() -> datetime:
    """Ortszeit Europe/Berlin ohne Zeitzone (wie die Eingaben)."""
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Berlin")).replace(tzinfo=None, second=0, microsecond=0)


def _t(x, n: int, *, einzeilig: bool = True) -> str:
    s = str(x or "")
    return (" ".join(s.split()) if einzeilig else s.strip())[:n]


def _pruefe_zeit(faellig: str, uhrzeit: str, erinnerung: str) -> None:
    if faellig and not _DATUM.match(faellig):
        raise ValueError("Fälligkeit bitte als JJJJ-MM-TT.")
    if uhrzeit and not _UHR.match(uhrzeit):
        raise ValueError("Uhrzeit bitte als HH:MM.")
    if uhrzeit and not faellig:
        raise ValueError("Eine Uhrzeit braucht ein Datum.")
    if erinnerung and not _ZEIT.match(erinnerung):
        raise ValueError("Erinnerung bitte als JJJJ-MM-TTTHH:MM.")


def standard_erinnerung(faellig: str, uhrzeit: str) -> str:
    return f"{faellig}T{uhrzeit or STANDARD_UHRZEIT}" if faellig else ""


class AufgabenStore:
    def __init__(self, pfad: Path | str):
        self.pfad = Path(pfad)
        self._lock = threading.Lock()

    # -- Lesen -------------------------------------------------------------------------------------------------------
    def _ereignisse(self) -> list[dict]:
        try:
            zeilen = self.pfad.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out = []
        for z in zeilen:
            try:
                out.append(json.loads(z))
            except ValueError:
                continue
        return out

    def _falte(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in self._ereignisse():
            t, aid, d = e.get("typ"), e.get("id"), e.get("daten") or {}
            if t == "angelegt":
                out[aid] = {"id": aid, "titel": "", "notiz": "", "faellig": "", "uhrzeit": "", "erinnerung": "",
                            "kunde": "", "quelle": "", "status": "offen", "angelegt": e["ts"], "erledigt_am": "",
                            "termin_id": "", "erinnert": "", "von": e.get("von", "")} | d
            elif aid not in out:
                continue
            elif t == "geaendert":
                out[aid].update(d)
            elif t == "erledigt":
                out[aid].update(status="erledigt", erledigt_am=e["ts"])
            elif t == "geoeffnet":
                out[aid].update(status="offen", erledigt_am="")
            elif t == "geloescht":
                out[aid]["status"] = "geloescht"
            elif t == "termin":
                out[aid]["termin_id"] = d.get("termin_id", "")
            elif t == "erinnert":
                out[aid]["erinnert"] = d.get("erinnerung", "")
        return out

    def get(self, aid: str) -> dict | None:
        a = self._falte().get((aid or "").strip())
        return a if a and a["status"] != "geloescht" else None

    def liste(self, *, heute: str | None = None, mit_erledigt: bool = True) -> dict:
        """Gruppiert: ueberfaellig, heute, demnaechst, ohne_datum, erledigt (letzte 30 Tage)."""
        heute = heute or jetzt_lokal().date().isoformat()
        grenze = (datetime.fromisoformat(heute) - timedelta(days=30)).isoformat()
        g: dict[str, list] = {"ueberfaellig": [], "heute": [], "demnaechst": [], "ohne_datum": [], "erledigt": []}
        for a in self._falte().values():
            if a["status"] == "geloescht":
                continue
            if a["status"] == "erledigt":
                if mit_erledigt and a["erledigt_am"] >= grenze:
                    g["erledigt"].append(a)
            elif not a["faellig"]:
                g["ohne_datum"].append(a)
            elif a["faellig"] < heute:
                g["ueberfaellig"].append(a)
            elif a["faellig"] == heute:
                g["heute"].append(a)
            else:
                g["demnaechst"].append(a)
        schl = lambda a: (a["faellig"] or "9999", a["uhrzeit"] or "99", a["angelegt"])
        for k in ("ueberfaellig", "heute", "demnaechst"):
            g[k].sort(key=schl)
        g["ohne_datum"].sort(key=lambda a: a["angelegt"], reverse=True)
        g["erledigt"].sort(key=lambda a: a["erledigt_am"], reverse=True)
        return g

    def faellige_erinnerungen(self, jetzt: datetime | None = None) -> list[dict]:
        """Offene To-dos, deren Erinnerung erreicht ist und die fuer genau diesen Zeitpunkt noch nicht erinnert wurden."""
        j = (jetzt or jetzt_lokal()).strftime("%Y-%m-%dT%H:%M")
        return sorted((a for a in self._falte().values()
                       if a["status"] == "offen" and a["erinnerung"] and a["erinnerung"] <= j and a["erinnert"] != a["erinnerung"]),
                      key=lambda a: a["erinnerung"])

    # -- Schreiben ---------------------------------------------------------------------------------------------------
    def _schreibe(self, typ: str, aid: str, daten: dict | None = None, von: str = "") -> None:
        e = {"ts": datetime.now().isoformat(timespec="seconds"), "typ": typ, "id": aid, "daten": daten or {}, "von": von}
        with self._lock:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            with self.pfad.open("a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def _vorhanden(self, aid: str) -> dict:
        if not _ID.match(aid or ""):
            raise KeyError(aid)
        a = self.get(aid)
        if not a:
            raise KeyError(aid)
        return a

    def anlegen(self, titel: str, *, faellig: str = "", uhrzeit: str = "", erinnerung: str | None = None, notiz: str = "",
                kunde: str = "", quelle: str = "LUNA-OS", von: str = "") -> dict:
        titel = _t(titel, MAX_TITEL)
        if not titel:
            raise ValueError("Titel fehlt.")
        faellig, uhrzeit = (faellig or "").strip(), (uhrzeit or "").strip()
        er = standard_erinnerung(faellig, uhrzeit) if erinnerung is None else (erinnerung or "").strip()
        _pruefe_zeit(faellig, uhrzeit, er)
        if er and not faellig:
            faellig = er[:10]
        aid = "A-" + uuid.uuid4().hex[:8]
        self._schreibe("angelegt", aid, {"titel": titel, "notiz": _t(notiz, MAX_NOTIZ, einzeilig=False), "faellig": faellig,
                                         "uhrzeit": uhrzeit, "erinnerung": er, "kunde": _t(kunde, 20),
                                         "quelle": _t(quelle, 40)}, von)
        return self.get(aid)

    def aendern(self, aid: str, felder: dict, *, von: str = "") -> dict:
        a = self._vorhanden(aid)
        neu: dict = {}
        if "titel" in felder:
            neu["titel"] = _t(felder["titel"], MAX_TITEL)
            if not neu["titel"]:
                raise ValueError("Titel fehlt.")
        if "notiz" in felder:
            neu["notiz"] = _t(felder["notiz"], MAX_NOTIZ, einzeilig=False)
        if "kunde" in felder:
            neu["kunde"] = _t(felder["kunde"], 20)
        for k in ("faellig", "uhrzeit", "erinnerung"):
            if k in felder:
                neu[k] = (felder[k] or "").strip()
        if ("faellig" in neu or "uhrzeit" in neu) and "erinnerung" not in neu and (a["erinnerung"] or a["faellig"] == ""):
            neu["erinnerung"] = standard_erinnerung(neu.get("faellig", a["faellig"]), neu.get("uhrzeit", a["uhrzeit"]))
        z = a | neu
        _pruefe_zeit(z["faellig"], z["uhrzeit"], z["erinnerung"])
        if not neu:
            raise ValueError("Nichts zu ändern.")
        self._schreibe("geaendert", aid, neu, von)
        return self.get(aid)

    def erledigen(self, aid: str, erledigt: bool = True, *, von: str = "") -> dict:
        a = self._vorhanden(aid)
        if (a["status"] == "erledigt") == erledigt:
            return a
        self._schreibe("erledigt" if erledigt else "geoeffnet", aid, None, von)
        return self.get(aid)

    def loeschen(self, aid: str, *, von: str = "") -> dict:
        a = self._vorhanden(aid)
        self._schreibe("geloescht", aid, None, von)
        return a

    def termin_merken(self, aid: str, termin_id: str, *, von: str = "") -> None:
        self._schreibe("termin", aid, {"termin_id": termin_id}, von)

    def erinnert(self, aid: str, erinnerung: str) -> None:
        self._schreibe("erinnert", aid, {"erinnerung": erinnerung}, "LUNA")

    def verschieben(self, aid: str, neue_erinnerung: str, *, von: str = "") -> dict:
        """Erinnerung verschieben (+1 Std., morgen) -- die Faelligkeit wandert mit, wenn sie davor lag."""
        a = self._vorhanden(aid)
        felder = {"erinnerung": neue_erinnerung}
        if not a["faellig"] or a["faellig"] < neue_erinnerung[:10]:
            felder["faellig"] = neue_erinnerung[:10]
        return self.aendern(aid, felder, von=von)


# -- Kalender (LUNAs eigene Termine, ohne Rueckfrage) -------------------------------------------------------------------
def kalender_abgleichen(store: AufgabenStore, google, a: dict, *, von: str = "LUNA") -> str:
    """Termin passend zum To-do anlegen, verschieben oder loeschen. -> Hinweis (leer = ok/nichts zu tun)."""
    if google is None or not getattr(google, "verfuegbar", lambda: False)():
        return "Kalender nicht verbunden -- Erinnerung kommt nur per Telegram."
    jetzt = jetzt_lokal().strftime("%Y-%m-%dT%H:%M")
    soll = a["status"] == "offen" and bool(a["erinnerung"])
    if not soll:
        if a.get("termin_id") and a.get("erinnerung", "") >= jetzt:
            r = google.termin_loeschen(a["termin_id"], bestaetigt=True)
            if r.get("ok") or any(c in str(r.get("hinweis") or "") for c in ("404", "410", "deleted", "Not Found")):
                store.termin_merken(a["id"], "", von=von)
            else:
                return "Kalendertermin konnte nicht gelöscht werden."
        return ""
    start = datetime.fromisoformat(a["erinnerung"])
    s, e = start.strftime("%Y-%m-%dT%H:%M:00"), (start + timedelta(minutes=TERMIN_MINUTEN)).strftime("%Y-%m-%dT%H:%M:00")
    titel = f"✅ {a['titel']}"
    if a.get("termin_id"):
        r = google.termin_aendern(a["termin_id"], titel=titel, start=s, ende=e, bestaetigt=True)
        if r.get("ok"):
            return ""
    beschreibung = (a.get("notiz") or "") + f"\n\nLUNA-To-do {a['id']} -- erledigen in LUNA-OS oder per Telegram."
    r = google.termin_anlegen(titel, s, e, beschreibung=beschreibung.strip(), bestaetigt=True)
    if not r.get("ok"):
        return "Kalendertermin konnte nicht angelegt werden: " + str(r.get("hinweis") or "")[:120]
    store.termin_merken(a["id"], r.get("termin_id") or "", von=von)
    return ""


def zusammenfassung(a: dict) -> str:
    from .beleg_pdf import datum_de
    teile = [f"✅ To-do: {a['titel']}"]
    if a["faellig"]:
        teile.append(f"fällig {datum_de(a['faellig'])}" + (f" {a['uhrzeit']} Uhr" if a["uhrzeit"] else ""))
    if a["erinnerung"]:
        teile.append(f"Erinnerung {datum_de(a['erinnerung'][:10])} {a['erinnerung'][11:16]} Uhr")
    return " · ".join(teile)


def plus_stunde(a: dict, jetzt: datetime | None = None) -> str:
    j = jetzt or jetzt_lokal()
    return (j + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")


def morgen_frueh(jetzt: datetime | None = None) -> str:
    j = jetzt or jetzt_lokal()
    return f"{(j.date() + timedelta(days=1)).isoformat()}T{STANDARD_UHRZEIT}"


# -- Telegram (Bot) ------------------------------------------------------------------------------------------------------
def erinnerungs_knoepfe(aid: str) -> list[list[dict]]:
    return [[{"text": "✓ Erledigt", "callback_data": f"auf:{aid}:ok"}, {"text": "⏰ +1 Std.", "callback_data": f"auf:{aid}:1h"},
             {"text": "⏰ morgen", "callback_data": f"auf:{aid}:morgen"}]]


def erinnerungen_senden(store: AufgabenStore, senden, *, jetzt: datetime | None = None) -> list[str]:
    """Faellige Erinnerungen per Telegram (`senden(text, inline_keyboard) -> bool`); als erinnert gilt nur, was ankam."""
    gesendet = []
    for a in store.faellige_erinnerungen(jetzt):
        text = "⏰ Erinnerung: " + a["titel"] + (f"\n{a['notiz']}" if a.get("notiz") else "")
        if senden(text[:3500], erinnerungs_knoepfe(a["id"])):
            store.erinnert(a["id"], a["erinnerung"])
            gesendet.append(a["id"])
    return gesendet


def knopf(store: AufgabenStore, google, aid: str, aktion: str, *, jetzt: datetime | None = None) -> str:
    """Telegram-Knopf: ok (erledigt), 1h / morgen (verschieben), weg (Rueckgaengig = loeschen). -> Antworttext."""
    try:
        a = store._vorhanden(aid)
    except KeyError:
        return "To-do nicht (mehr) vorhanden."
    if aktion == "ok":
        x = store.erledigen(aid, von="Telegram:CEO")
        kalender_abgleichen(store, google, x, von="Telegram:CEO")
        return f"✓ Erledigt: {a['titel']}"
    if aktion in ("1h", "morgen"):
        x = store.verschieben(aid, plus_stunde(a, jetzt) if aktion == "1h" else morgen_frueh(jetzt), von="Telegram:CEO")
        kalender_abgleichen(store, google, x, von="Telegram:CEO")
        return f"⏰ Verschoben: {a['titel']} · {zusammenfassung(x).split(' · ')[-1]}"
    if aktion == "weg":
        store.loeschen(aid, von="Telegram:CEO")
        kalender_abgleichen(store, google, a | {"status": "geloescht"}, von="Telegram:CEO")
        return f"↶ Rückgängig: „{a['titel']}“ ist gelöscht."
    return "Unbekannte Aktion."
