"""Zeiterfassung und Nachkalkulation je Auftrag (KUNDEN_FINANZEN Etappe 25, CEO 2026-09-30).

**Nur intern** (CEO: „Stundenerfassung ist fuer das interne Kosten-Tracking und nichts, was wir dem Kunden zeigen oder
irgendwo andrucken muessen“) -- keine Zeiten in PDFs, Mails oder beim Kunden.

- **Stundensatz (kalkulatorisch):** Brutto-Monatslohn des Arbeitgebers x 12 / (Wochenstunden x 52) -- CEO-Entscheidung
  Brutto. Nur fuer die Kalkulation, **keine Buchung** (eigene Arbeitszeit ist in der EUeR keine Betriebsausgabe).
  Einstellung in `buchhaltung/zeiterfassung.json` (nur NAS, nicht im Git).
- **Zeiten:** Start/Stopp (Telegram „Bin auf dem Weg zu …“ / „Bin wieder zuhause“, Fahrzeit zaehlt) oder manuell (Datum,
  von-bis bzw. Dauer). Immer an einem Auftrag `AB-` (oder vorlaeufig nur an der Firma, dann To-do „Zeit zuordnen“).
- **Fahrten:** Kilometer Hin + Rueck ab der Firmenadresse (OpenStreetMap, `core/routen.py`) oder von Hand -> ebenfalls
  **nur kalkulatorisch** mit 0,30 EUR/km (CEO 2026-09-30: Firmenwagen des Arbeitgebers, real keine Kosten -- „was es
  kosten wuerde, wenn man selbststaendig waere“). **Kein Eigenbeleg, keine Buchung, nicht in der EUeR.**
- **Nachkalkulation:** Auftragssumme (Geldanteil) minus kalkulatorische Zeit- und Fahrtkosten -> Deckungsbeitrag und
  effektiver Stundenlohn („als waere ich selbststaendig“).

Ereignisse: `zeit_start`, `zeit_stopp`, `zeit_eintrag`, `zeit_fahrt`, `zeit_storniert`, `zeit_zugeordnet`.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta

from .beleg_pdf import eur
from .buchhaltung import jetzt

KM_SATZ_CENT = 30                        # kalkulatorisch, angelehnt an die Kilometerpauschale (je gefahrenem km)
ERINNERN_STUNDEN = 10
MAX_MINUTEN = 24 * 60


def _zeit(s: str) -> datetime:
    d = datetime.fromisoformat(str(s)[:19])
    return d


def _jetzt_lokal() -> datetime:
    return jetzt().replace(tzinfo=None, microsecond=0)


class Zeiterfassung:
    def __init__(self, bh, kunden, *, auftraege=None, routen=None, heimadresse: str = ""):
        self.bh, self.kunden, self.auftraege, self.routen = bh, kunden, auftraege, routen
        self.heimadresse = heimadresse
        self.pfad = bh.dir / "zeiterfassung.json"

    # -- Einstellungen (Stundensatz) ------------------------------------------------------------------------------------

    def einstellungen(self) -> dict:
        try:
            e = json.loads(self.pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            e = {}
        brutto, std = int(e.get("monatsbrutto_cent") or 0), float(e.get("wochenstunden") or 0)
        satz = round(brutto * 12 / (std * 52)) if brutto and std else 0
        return {"monatsbrutto_cent": brutto, "wochenstunden": std, "stundensatz_cent": satz, "km_satz_cent": KM_SATZ_CENT}

    def einstellen(self, monatsbrutto, wochenstunden, *, von: str = "") -> dict:
        from .beleg_pdf import cent
        try:
            b = cent(monatsbrutto)
            s = float(str(wochenstunden).replace(",", "."))
        except (TypeError, ValueError):
            raise ValueError("Monatsbrutto in Euro und Wochenstunden als Zahl angeben.") from None
        if not (0 < b <= 100_000_00 and 1 <= s <= 80):
            raise ValueError("Monatsbrutto 0-100.000 EUR, Wochenstunden 1-80.")
        tmp = self.pfad.with_suffix(".tmp")
        tmp.write_text(json.dumps({"monatsbrutto_cent": b, "wochenstunden": s}), encoding="utf-8")
        tmp.replace(self.pfad)
        e = self.einstellungen()
        self.bh.erfassen("zeit_einstellung", {"stundensatz_cent": e["stundensatz_cent"]}, von=von)   # Betrag nur als Satz
        return e

    # -- Lesen --------------------------------------------------------------------------------------------------------

    def _falte(self, eintraege: list[dict] | None = None) -> dict[str, dict]:
        return falte_zeiten(self.bh.eintraege() if eintraege is None else eintraege)

    def laufend(self) -> dict | None:
        return next((x for x in self._falte().values() if x["laeuft"]), None)

    def fuer_auftrag(self, auftrag: str) -> list[dict]:
        return sorted((x for x in self._falte().values() if x.get("auftrag") == auftrag and not x["storniert"]),
                      key=lambda x: x["start"])

    def nachkalkulation(self, auftrag: dict) -> dict:
        z = self.fuer_auftrag(auftrag["nummer"])
        minuten = sum(x.get("minuten", 0) for x in z)
        zeit_cent = sum(x["kosten_cent"] for x in z)
        fahrt_cent = sum(x["fahrt_cent"] for x in z)
        km = sum(f.get("km") or 0 for x in z for f in x["fahrten"])
        umsatz = int(auftrag.get("geld_cent", auftrag.get("summe_cent", 0)) or 0)
        db = umsatz - zeit_cent - fahrt_cent
        return {"umsatz_cent": umsatz, "minuten": minuten, "zeit_cent": zeit_cent, "fahrt_cent": fahrt_cent, "km": km,
                "db_cent": db, "stundenlohn_cent": round((umsatz - fahrt_cent) * 60 / minuten) if minuten else None,
                "eintraege": len(z)}

    # -- Schreiben ----------------------------------------------------------------------------------------------------

    def _ziel(self, auftrag: str, firma: str) -> tuple[str, str]:
        """-> (Auftragsnummer, Firmennummer) -- Auftrag muss existieren und darf nicht storniert sein."""
        if auftrag:
            a = self.auftraege.auftrag(auftrag) if self.auftraege else None
            if not a:
                raise ValueError(f"Auftrag {auftrag} gibt es nicht.")
            if a["status"] == "storniert":
                raise ValueError(f"{auftrag} ist storniert.")
            if a["status"] == "erledigt":                   # Etappe 30: geliefert -> keine Zeit mehr
                raise ValueError(f"{a['nummer']} ist geliefert -- keine Zeit mehr buchbar (bei Nachlieferung erst "
                                 "„Wieder öffnen“).")
            return a["nummer"], a["firma"]
        f = self.kunden.firma(firma) if firma else None
        if not f:
            raise ValueError("Bitte einen Auftrag (oder zumindest die Firma) angeben.")
        return "", f["nummer"]

    def starten(self, *, auftrag: str = "", firma: str = "", adresse: str = "", quelle: str = "LUNA-OS", von: str = "") -> dict:
        if self.laufend():
            raise ValueError("Es laeuft schon eine Zeit -- erst stoppen.")
        auftrag, firma = self._ziel(auftrag, firma)
        zid = "Z-" + uuid.uuid4().hex[:8]
        start = _jetzt_lokal().isoformat()
        self.bh.erfassen("zeit_start", {"id": zid, "auftrag": auftrag, "firma": firma, "start": start,
                                        "adresse": (adresse or "").strip()[:200], "quelle": quelle}, von=von)
        return {"id": zid, "auftrag": auftrag, "firma": firma, "start": start}

    def stoppen(self, *, ende: str = "", von: str = "") -> dict:
        x = self.laufend()
        if not x:
            raise ValueError("Es laeuft keine Zeit.")
        e = _zeit(ende) if ende else _jetzt_lokal()
        if e < _zeit(x["start"]):
            raise ValueError("Ende liegt vor dem Start.")
        satz = self.einstellungen()["stundensatz_cent"]
        self.bh.erfassen("zeit_stopp", {"id": x["id"], "ende": e.isoformat(), "satz_cent": satz}, von=von)
        m = round((e - _zeit(x["start"])).total_seconds() / 60)
        return {"id": x["id"], "auftrag": x["auftrag"], "firma": x["firma"], "minuten": m,
                "kosten_cent": round(m * satz / 60), "satz_cent": satz}

    def eintragen(self, *, auftrag: str = "", firma: str = "", datum: str, von_uhr: str = "", bis_uhr: str = "",
                  minuten=None, notiz: str = "", adresse: str = "", von: str = "") -> dict:
        """Manuell: Datum + von/bis (HH:MM) oder Dauer in Minuten."""
        auftrag, firma = self._ziel(auftrag, firma)
        try:
            tag = datetime.fromisoformat(str(datum)[:10])
        except ValueError:
            raise ValueError("Datum ungueltig.") from None
        if tag.date() > _jetzt_lokal().date():
            raise ValueError("Datum liegt in der Zukunft.")
        if von_uhr and bis_uhr:
            try:
                s = datetime.combine(tag.date(), datetime.strptime(von_uhr, "%H:%M").time())
                e = datetime.combine(tag.date(), datetime.strptime(bis_uhr, "%H:%M").time())
            except ValueError:
                raise ValueError("Uhrzeit als HH:MM.") from None
            if e <= s:
                e += timedelta(days=1)                                           # ueber Mitternacht
        else:
            try:
                m = int(minuten)
            except (TypeError, ValueError):
                raise ValueError("Von/bis oder Dauer in Minuten angeben.") from None
            s, e = datetime.combine(tag.date(), datetime.min.time()).replace(hour=9), None
            e = s + timedelta(minutes=m)
        m = round((e - s).total_seconds() / 60)
        if not 0 < m <= MAX_MINUTEN:
            raise ValueError("Dauer zwischen 1 Minute und 24 Stunden.")
        zid = "Z-" + uuid.uuid4().hex[:8]
        satz = self.einstellungen()["stundensatz_cent"]
        self.bh.erfassen("zeit_eintrag", {"id": zid, "auftrag": auftrag, "firma": firma, "start": s.isoformat(),
                                          "ende": e.isoformat(), "satz_cent": satz, "notiz": (notiz or "").strip()[:300],
                                          "adresse": (adresse or "").strip()[:200], "quelle": "manuell"}, von=von)
        return {"id": zid, "minuten": m, "kosten_cent": round(m * satz / 60)}

    def zuordnen(self, zid: str, auftrag: str, *, von: str = "") -> dict:
        x = self._falte().get(zid)
        if not x:
            raise KeyError(zid)
        nr, firma = self._ziel(auftrag, "")
        self.bh.erfassen("zeit_zugeordnet", {"id": zid, "auftrag": nr}, von=von)
        return {"id": zid, "auftrag": nr}

    def stornieren(self, zid: str, grund: str, *, von: str = "") -> dict:
        x = self._falte().get(zid)
        if not x or x["storniert"]:
            raise ValueError("Diesen Eintrag gibt es nicht (mehr).")
        if not (grund or "").strip():
            raise ValueError("Bitte einen Grund angeben.")
        self.bh.erfassen("zeit_storniert", {"id": zid, "grund": grund.strip()[:200]}, von=von)
        return {"id": zid, "storniert": True}

    def adresse_fuer(self, x: dict) -> str:
        if x.get("adresse"):
            return x["adresse"]
        f = self.kunden.firma(x.get("firma") or "") or {}
        return " ".join(v for v in (f.get("strasse"), f.get("plz"), f.get("ort")) if v)

    def km_vorschlag(self, zid: str, adresse: str = "") -> dict:
        """Kilometer Hin + Rueck ab der Firmenadresse zur Dreh-/Firmenadresse (OpenStreetMap), ohne zu buchen."""
        x = self._falte().get(zid)
        if not x:
            raise KeyError(zid)
        ziel = (adresse or "").strip() or self.adresse_fuer(x)
        km = self.routen.km_hin_zurueck(self.heimadresse, ziel) if (self.routen and ziel and self.heimadresse) else None
        return {"id": zid, "adresse": ziel, "km": km, "betrag_cent": km * KM_SATZ_CENT if km else None}

    def fahrt_erfassen(self, zid: str, *, km=None, adresse: str = "", von: str = "") -> dict:
        """Fahrt **kalkulatorisch** erfassen (0,30 EUR/km, keine Buchung). Ohne km: aus der Route (Hin + Rueck).
        Erneut erfassen korrigiert (letzter Eintrag gilt)."""
        x = self._falte().get(zid)
        if not x or x["storniert"]:
            raise ValueError("Diesen Zeiteintrag gibt es nicht (mehr).")
        quelle = "hand"
        if km in (None, ""):
            v = self.km_vorschlag(zid, adresse)
            km, adresse, quelle = v["km"], v["adresse"], "osm"
            if not km:
                raise ValueError("Strecke nicht gefunden -- bitte die Kilometer selbst eintragen.")
        try:
            km = int(round(float(str(km).replace(",", "."))))
        except (TypeError, ValueError):
            raise ValueError("Kilometer als Zahl.") from None
        if not 0 <= km <= 3000:
            raise ValueError("Kilometer zwischen 0 und 3000.")
        betrag = km * KM_SATZ_CENT
        self.bh.erfassen("zeit_fahrt", {"id": zid, "km": km, "quelle": quelle, "adresse": (adresse or self.adresse_fuer(x))[:200],
                                        "betrag_cent": betrag}, von=von)
        return {"id": zid, "km": km, "betrag_cent": betrag}


# -- Telegram-Befehle -------------------------------------------------------------------------------------------------

_START = re.compile(r"(?i)\b(?:(?:bin|mache mich)\s+(?:jetzt\s+)?auf\s+(?:dem|den)\s+weg|fahre\s+(?:jetzt\s+)?los|"
                    r"fahre\s+(?:jetzt\s+)?)\s*(?:zu[rm]?|nach|ins?|zum)\s+(?P<ziel>.{2,80}?)\s*[.!]?\s*$")
_STOPP = re.compile(r"(?i)\b(?:(?:bin|wieder)\s+(?:wieder\s+)?(?:zu\s?hause|daheim|zur[üu]ck)|zeit\s+stopp|"
                    r"feierabend|(?:fahre|bin\s+auf\s+dem\s+weg)\s+(?:jetzt\s+)?(?:wieder\s+)?nach\s+hause)\b")
_KM = re.compile(r"(?i)^\s*(\d{1,4}(?:[.,]\d)?)\s*(?:km|kilometer)\s*$")


def befehl(text: str) -> dict | None:
    """„Bin auf dem Weg zu CR Container“ -> {art: start, ziel}; „Bin wieder zuhause“ -> {art: stopp};
    „42 km“ -> {art: km, km}. Sonst None (normaler Chat)."""
    t = (text or "").strip()
    if not t or "?" in t or len(t) > 160:
        return None
    if (m := _KM.match(t)):
        return {"art": "km", "km": m.group(1).replace(",", ".")}
    if _STOPP.search(t):
        return {"art": "stopp"}
    if (m := _START.search(t)):
        return {"art": "start", "ziel": m.group("ziel").strip(" .,!")}
    return None


def firma_finden(kunden, ziel: str) -> str:
    """Firma zum Ziel aus der Nachricht: Name enthalten oder kennzeichnendes Namenswort (≥ 4 Zeichen)."""
    z = (ziel or "").lower()
    beste = ""
    for f in kunden.firmen():
        if not f.get("aktiv", True):
            continue
        n = f["name"].lower()
        woerter = [w for w in re.findall(r"[a-zäöüß0-9]{4,}", n) if w not in ("gmbh", "trading", "gastro", "group")]
        if n in z or z in n or any(w in z for w in woerter):
            if not beste or len(f["name"]) > len(beste[1]):
                beste = (f["nummer"], f["name"])
    return beste[0] if beste else ""


def offene_auftraege(auftraege, firma: str) -> list[dict]:
    return [a for a in auftraege.liste() if a["firma"] == firma and a["status"] == "beauftragt"]


def dauer_text(minuten: int) -> str:
    return f"{minuten // 60}:{minuten % 60:02d} h"


def erinnerung_faellig(x: dict | None, jetzt_: datetime | None = None) -> bool:
    if not x:
        return False
    return (jetzt_ or _jetzt_lokal()) - _zeit(x["start"]) >= timedelta(hours=ERINNERN_STUNDEN)



def falte_zeiten(eintraege: list[dict]) -> dict[str, dict]:
    """Zeiteintraege aus der Kette (auch fuer Finanzen/Export, ohne Store-Objekt)."""
    out: dict[str, dict] = {}
    for e in eintraege:
        d, t = e["daten"], e["typ"]
        if t in ("zeit_start", "zeit_eintrag"):
            out[d["id"]] = dict(d) | {"ts": e["ts"], "fahrten": [], "storniert": False}
        elif d.get("id") not in out:
            continue
        elif t == "zeit_stopp":
            out[d["id"]] |= {"ende": d["ende"], "satz_cent": d["satz_cent"]}
        elif t == "zeit_fahrt":
            out[d["id"]]["fahrten"] = [{k: d.get(k) for k in ("km", "quelle", "adresse", "betrag_cent")}]   # letzte gilt
        elif t == "zeit_storniert":
            out[d["id"]] |= {"storniert": True, "grund": d.get("grund", "")}
        elif t == "zeit_zugeordnet":
            out[d["id"]]["auftrag"] = d["auftrag"]
    for x in out.values():
        if x.get("ende"):
            x["minuten"] = max(0, round((_zeit(x["ende"]) - _zeit(x["start"])).total_seconds() / 60))
        x["laeuft"] = not x.get("ende") and not x["storniert"]
        x["kosten_cent"] = round(x.get("minuten", 0) * (x.get("satz_cent") or 0) / 60)
        x["fahrt_cent"] = sum(f.get("betrag_cent") or 0 for f in x["fahrten"])
    return out


def kalkulatorisch(eintraege: list[dict], jahr: int, monate: set[int] | None = None, firmen: dict | None = None) -> dict:
    """Etappe 26: kalkulatorische Kosten (eigene Arbeitszeit + Fahrten) -- **nie** Teil von EUeR/Gewinn, nur Zusatz.
    -> {zeit_cent, fahrt_cent, summe_cent, minuten, km, monate: [{nr, ...}], zeilen: [...] }"""
    firmen = firmen or {}
    je = {m: {"nr": m, "zeit_cent": 0, "fahrt_cent": 0, "minuten": 0, "km": 0} for m in range(1, 13)}
    zeilen = []
    for x in sorted(falte_zeiten(eintraege).values(), key=lambda x: x["start"]):
        if x["storniert"] or x["laeuft"] or str(x["start"])[:4] != str(jahr):
            continue
        m = int(str(x["start"])[5:7])
        if monate and m not in monate:
            continue
        km = sum(f.get("km") or 0 for f in x["fahrten"])
        je[m]["zeit_cent"] += x["kosten_cent"]
        je[m]["fahrt_cent"] += x["fahrt_cent"]
        je[m]["minuten"] += x.get("minuten", 0)
        je[m]["km"] += km
        wer = firmen.get(x.get("firma"), x.get("firma", ""))
        zeilen.append({"datum": str(x["start"])[:10], "art": "Arbeitszeit", "auftrag": x.get("auftrag", ""), "gegenpartei": wer,
                       "menge": f"{x.get('minuten', 0) / 60:.2f} h".replace(".", ","), "betrag_cent": x["kosten_cent"]})
        if x["fahrt_cent"]:
            zeilen.append({"datum": str(x["start"])[:10], "art": "Fahrt", "auftrag": x.get("auftrag", ""), "gegenpartei": wer,
                           "menge": f"{km} km", "betrag_cent": x["fahrt_cent"]})
    summe = {k: sum(v[k] for v in je.values()) for k in ("zeit_cent", "fahrt_cent", "minuten", "km")}
    return summe | {"summe_cent": summe["zeit_cent"] + summe["fahrt_cent"], "monate": list(je.values()), "zeilen": zeilen,
                    "hinweis": "Kalkulatorisch (eigene Arbeitszeit, Fahrten mit Firmenwagen) -- keine Betriebsausgaben, "
                               "nicht in der EUeR."}


def kalkulatorisch_csv(k: dict) -> str:
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Datum", "Art", "Auftrag", "Gegenpartei", "Menge", "Betrag EUR (kalkulatorisch)", "Hinweis"])
    for z in k["zeilen"]:
        w.writerow([f"{z['datum'][8:10]}.{z['datum'][5:7]}.{z['datum'][:4]}", z["art"], z["auftrag"], z["gegenpartei"],
                    z["menge"], f"{z['betrag_cent'] / 100:.2f}".replace(".", ","), "keine Betriebsausgabe"])
    return buf.getvalue()
