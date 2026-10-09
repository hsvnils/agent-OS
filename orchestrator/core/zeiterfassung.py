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
from datetime import date, datetime, timedelta

from .beleg_pdf import eur
from .buchhaltung import jetzt

# ZEITERFASSUNG_GRUND Z1 (CEO 2026-10-09): feste Gruende der Arbeitszeit; bei „Sonstiges“ kurzer Text in `taetigkeit`.
# Feld heisst `arbeit` (nicht `grund` -- `grund` ist schon die Begruendung einer Korrektur/eines Stornos).
ARBEITEN = {"dreh": "Dreharbeiten", "post": "Postproduktion & Schnitt", "konzept": "Konzept & Abstimmung",
            "sonstiges": "Sonstiges"}
_ALT_ARBEIT = (("dreh", "dreh"), ("schnitt", "post"), ("post", "post"), ("edit", "post"), ("konzept", "konzept"),
               ("abstimm", "konzept"), ("planung", "konzept"), ("meeting", "konzept"))
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
        je_pos = []                                         # Z3: Nachkalkulation je Leistung (Zeit einer Position zugeordnet)
        for i, p in enumerate(auftrag.get("positionen") or [], 1):
            zp = [x for x in z if int(x.get("position") or 0) == i]
            if not zp:
                continue
            m = sum(x.get("minuten", 0) for x in zp)
            um = int(p.get("gesamt_cent") or 0)
            k = sum(x["kosten_cent"] + x["fahrt_cent"] for x in zp)
            je_pos.append({"position": i, "beschreibung": p.get("beschreibung", ""), "katalog_id": p.get("katalog_id", ""),
                           "umsatz_cent": um, "minuten": m, "kosten_cent": k, "db_cent": um - k,
                           "stundenlohn_cent": round(um * 60 / m) if m else None})
        return {"umsatz_cent": umsatz, "minuten": minuten, "zeit_cent": zeit_cent, "fahrt_cent": fahrt_cent, "km": km,
                "db_cent": db, "stundenlohn_cent": round((umsatz - fahrt_cent) * 60 / minuten) if minuten else None,
                "eintraege": len(z), "je_position": je_pos,
                "ohne_position_min": sum(x.get("minuten", 0) for x in z if not int(x.get("position") or 0))}

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

    def stoppen(self, *, ende: str = "", taetigkeit: str = "", pause_min=None, arbeit: str = "", von: str = "") -> dict:
        x = self.laufend()
        if not x:
            raise ValueError("Es laeuft keine Zeit.")
        e = _zeit(ende) if ende else _jetzt_lokal()
        if e < _zeit(x["start"]):
            raise ValueError("Ende liegt vor dem Start.")
        brutto = round((e - _zeit(x["start"])).total_seconds() / 60)
        pause = _pause(pause_min, brutto)
        a = _arbeit(arbeit, taetigkeit)
        satz = self.einstellungen()["stundensatz_cent"]
        self.bh.erfassen("zeit_stopp", {"id": x["id"], "ende": e.isoformat(), "satz_cent": satz}
                         | ({"arbeit": a} if a else {})
                         | ({"taetigkeit": _taetigkeit(taetigkeit)} if taetigkeit else {})
                         | ({"pause_min": pause} if pause else {}), von=von)
        m = brutto - pause
        return {"id": x["id"], "auftrag": x["auftrag"], "firma": x["firma"], "minuten": m,
                "kosten_cent": round(m * satz / 60), "satz_cent": satz}

    def eintragen(self, *, auftrag: str = "", firma: str = "", datum: str, von_uhr: str = "", bis_uhr: str = "",
                  minuten=None, notiz: str = "", adresse: str = "", taetigkeit: str = "", pause_min=None,
                  arbeit: str = "", arbeit_pflicht: bool = False, quelle: str = "manuell", von: str = "") -> dict:
        """Manuell: Datum + von/bis (HH:MM) oder Dauer in Minuten. `arbeit_pflicht`: Nachtragen im OS/Telegram (Z1)."""
        a = _arbeit(arbeit, taetigkeit)
        if arbeit_pflicht and not a:
            raise ValueError("Bitte den Grund waehlen (Dreharbeiten, Postproduktion & Schnitt, Konzept & Abstimmung, Sonstiges).")
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
        brutto = round((e - s).total_seconds() / 60)
        if not 0 < brutto <= MAX_MINUTEN:
            raise ValueError("Dauer zwischen 1 Minute und 24 Stunden.")
        pause = _pause(pause_min, brutto)
        m = brutto - pause
        zid = "Z-" + uuid.uuid4().hex[:8]
        satz = self.einstellungen()["stundensatz_cent"]
        self.bh.erfassen("zeit_eintrag", {"id": zid, "auftrag": auftrag, "firma": firma, "start": s.isoformat(),
                                          "ende": e.isoformat(), "satz_cent": satz, "notiz": (notiz or "").strip()[:300],
                                          "adresse": (adresse or "").strip()[:200], "quelle": quelle}
                         | ({"arbeit": a} if a else {})
                         | ({"taetigkeit": _taetigkeit(taetigkeit)} if taetigkeit else {})
                         | ({"pause_min": pause} if pause else {}), von=von)
        return {"id": zid, "minuten": m, "kosten_cent": round(m * satz / 60)}

    # -- PROJEKTZEITEN Z1: Stundenzettel, Taetigkeit, Korrektur ---------------------------------------------------------

    def details_setzen(self, zid: str, *, taetigkeit=None, pause_min=None, notiz=None, position=None, arbeit=None,
                       von: str = "") -> dict:
        x = self._falte().get(zid)
        if not x or x["storniert"]:
            raise KeyError(zid)
        d = {"id": zid}
        if position is not None:                            # Z3: Zeit einer Auftragsposition zuordnen (0 = keine)
            try:
                n = int(position or 0)
            except (TypeError, ValueError):
                raise ValueError("Position: Nummer der Auftragsposition.") from None
            a = self.auftraege.auftrag(x.get("auftrag") or "") if self.auftraege and x.get("auftrag") else None
            if n and (not a or not 1 <= n <= len(a["positionen"])):
                raise ValueError("Diese Position gibt es im Auftrag nicht.")
            d["position"] = n
        if arbeit is not None:
            d["arbeit"] = _arbeit(arbeit, taetigkeit if taetigkeit is not None else x.get("taetigkeit", ""))
        if taetigkeit is not None:
            d["taetigkeit"] = _taetigkeit(taetigkeit)
        if pause_min is not None:
            brutto = round((_zeit(x["ende"]) - _zeit(x["start"])).total_seconds() / 60) if x.get("ende") else MAX_MINUTEN
            d["pause_min"] = _pause(pause_min, brutto)
        if notiz is not None:
            d["notiz"] = str(notiz).strip()[:300]
        if len(d) == 1:
            raise ValueError("Nichts zu aendern.")
        self.bh.erfassen("zeit_details", d, von=von)
        return d

    def korrigieren(self, zid: str, *, datum: str, von_uhr: str, bis_uhr: str, pause_min=None, taetigkeit=None,
                    grund: str = "", arbeit=None, von: str = "") -> dict:
        """Ein/Aus/Pause eines beendeten Eintrags aendern (Verlauf bleibt). Nicht mehr, wenn schon abgerechnet."""
        x = self._falte().get(zid)
        if not x or x["storniert"]:
            raise KeyError(zid)
        if x["laeuft"]:
            raise ValueError("Die Zeit laeuft noch -- erst stoppen.")
        if x.get("abgerechnet"):
            raise ValueError(f"Schon mit {x['abgerechnet']} abgerechnet -- dort erst stornieren.")
        if not str(grund or "").strip():
            raise ValueError("Bitte kurz begruenden (z. B. „Ende vergessen zu stoppen“).")
        try:
            tag = datetime.fromisoformat(str(datum)[:10]).date()
            s = datetime.combine(tag, datetime.strptime(von_uhr, "%H:%M").time())
            e = datetime.combine(tag, datetime.strptime(bis_uhr, "%H:%M").time())
        except ValueError:
            raise ValueError("Datum TT.MM.JJJJ bzw. Uhrzeit HH:MM.") from None
        if e <= s:
            e += timedelta(days=1)
        if s.date() > _jetzt_lokal().date():
            raise ValueError("Datum liegt in der Zukunft.")
        brutto = round((e - s).total_seconds() / 60)
        if not 0 < brutto <= MAX_MINUTEN:
            raise ValueError("Dauer zwischen 1 Minute und 24 Stunden.")
        d = {"id": zid, "start": s.isoformat(), "ende": e.isoformat(), "pause_min": _pause(pause_min, brutto),
             "grund": str(grund).strip()[:200]} | ({"taetigkeit": _taetigkeit(taetigkeit)} if taetigkeit is not None else {}) \
            | ({"arbeit": _arbeit(arbeit, taetigkeit if taetigkeit is not None else x.get("taetigkeit", ""))} if arbeit is not None else {})
        self.bh.erfassen("zeit_korrigiert", d, von=von)
        return {"id": zid, "minuten": brutto - d["pause_min"]}

    def taetigkeiten(self, n: int = 3) -> list[str]:
        """Zuletzt genutzte Taetigkeiten (fuer Knoepfe im Zeit-Fenster und in Telegram)."""
        out: list[str] = []
        for x in sorted(self._falte().values(), key=lambda x: x.get("ende") or x["start"], reverse=True):
            t = (x.get("taetigkeit") or "").strip()
            if t and t not in out:
                out.append(t)
            if len(out) >= n:
                break
        return out

    def stundenzettel(self, auftrag: str) -> dict:
        """Wie Positionen: je Eintrag Datum, Ein, Aus, Pause, Dauer, Taetigkeit, km -- Summen je Tag und gesamt."""
        zeilen, tage = [], {}
        for x in self.fuer_auftrag(auftrag):
            if x["laeuft"]:
                continue
            km = sum(f.get("km") or 0 for f in x["fahrten"])
            z = {"id": x["id"], "datum": x["start"][:10], "von": x["start"][11:16], "bis": str(x.get("ende") or "")[11:16],
                 "pause_min": int(x.get("pause_min") or 0), "minuten": x.get("minuten", 0),
                 "taetigkeit": arbeit_text(x), "arbeit": arbeit_von(x), "taetigkeit_frei": x.get("taetigkeit", ""),
                 "notiz": x.get("notiz", ""), "km": km, "quelle": x.get("quelle", ""),
                 "kosten_cent": x["kosten_cent"], "fahrt_cent": x["fahrt_cent"], "abgerechnet": x.get("abgerechnet", ""),
                 "km_abgerechnet": x.get("km_abgerechnet", ""), "position": int(x.get("position") or 0),
                 "korrigiert": len(x.get("korrekturen") or [])}
            zeilen.append(z)
            t = tage.setdefault(z["datum"], {"datum": z["datum"], "minuten": 0, "km": 0})
            t["minuten"] += z["minuten"]
            t["km"] += km
        return {"eintraege": zeilen, "tage": sorted(tage.values(), key=lambda t: t["datum"]),
                "summe": {"minuten": sum(z["minuten"] for z in zeilen), "km": sum(z["km"] for z in zeilen),
                          "kosten_cent": sum(z["kosten_cent"] for z in zeilen),
                          "fahrt_cent": sum(z["fahrt_cent"] for z in zeilen)}}

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
        if x.get("abgerechnet") or x.get("km_abgerechnet"):
            raise ValueError(f"Schon auf {x.get('abgerechnet') or x['km_abgerechnet']} abgerechnet -- erst die Rechnung stornieren.")
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
        if x.get("km_abgerechnet"):
            raise ValueError(f"Die Fahrt ist schon auf {x['km_abgerechnet']} abgerechnet -- erst die Rechnung stornieren.")
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


# ZEITERFASSUNG_GRUND Z2: Zeit per Telegram nachtragen, z. B. „Gestern 3 Stunden Schnitt fuer CR Container“ oder
# „09.10. 10-14 Uhr Dreh AB-2026-0001“. Regelbasiert; gebraucht werden Tag + (Zeitspanne oder Dauer) + Grund oder Ziel.
_NT_TAG = re.compile(r"(?i)\b(heute|gestern|vorgestern)\b|\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})?(?!\d)")
_NT_SPANNE = re.compile(r"(?i)\b(?:von\s+)?(\d{1,2})(?:[:.](\d{2}))?\s*(?:uhr\s*)?(?:-|–|bis)\s*(\d{1,2})(?:[:.](\d{2}))?\s*uhr\b"
                        r"|\b(\d{1,2}):(\d{2})\s*(?:-|–|bis)\s*(\d{1,2}):(\d{2})\b")
_NT_DAUER = re.compile(r"(?i)\b(\d{1,2})(?:[.,](\d{1,2}))?\s*(?:h\b|std\b|std\.|stunden?\b)|\b(\d{1,2}):(\d{2})\s*(?:h\b|std|stunden?)"
                       r"|\b(\d{1,3})\s*(?:min\b|minuten\b)")
_NT_GRUND = (("dreh", r"dreh|gedreht|filmen|gefilmt|aufnahm"), ("post", r"schnitt|geschnitten|schneiden|postpro|edit|color|bearbeit"),
             ("konzept", r"konzept|abstimm|meeting|telefonat|planung|besprechung|call\b"))
_NT_ZIEL = re.compile(r"(?i)\b(AB-\d{4}-\d{3,5})\b|\b(?:f[üu]r|bei|zu|an)\s+(.+)$")


def nachtrag(text: str, heute: date | None = None) -> dict | None:
    """-> {datum, von_uhr, bis_uhr | minuten, arbeit, auftrag, ziel} oder None (normaler Chat). Kein Speichern."""
    t = " ".join(str(text or "").split())
    if not t or "?" in t or len(t) > 200:
        return None
    heute = heute or _jetzt_lokal().date()
    m = _NT_TAG.search(t)
    if not m:
        return None
    if m.group(1):
        tag = heute - timedelta(days={"heute": 0, "gestern": 1, "vorgestern": 2}[m.group(1).lower()])
    else:
        j = m.group(4)
        jahr = heute.year if not j else (2000 + int(j) if len(j) == 2 else int(j))
        try:
            tag = date(jahr, int(m.group(3)), int(m.group(2)))
        except ValueError:
            return None
        if not j and tag > heute:                                       # „28.12.“ im Januar = Vorjahr
            tag = tag.replace(year=jahr - 1)
    out: dict = {"datum": tag.isoformat()}
    if (s := _NT_SPANNE.search(t)):
        g = s.groups()
        a = (g[0], g[1], g[2], g[3]) if g[0] else (g[4], g[5], g[6], g[7])
        out |= {"von_uhr": f"{int(a[0]):02d}:{int(a[1] or 0):02d}", "bis_uhr": f"{int(a[2]):02d}:{int(a[3] or 0):02d}"}
    elif (d := _NT_DAUER.search(t)):
        g = d.groups()
        if g[0]:
            out["minuten"] = int(g[0]) * 60 + round(int(g[1]) * 60 / (10 ** len(g[1]))) if g[1] else int(g[0]) * 60
        elif g[2]:
            out["minuten"] = int(g[2]) * 60 + int(g[3])
        else:
            out["minuten"] = int(g[4])
    else:
        return None
    low = t.lower()
    out["arbeit"] = next((k for k, muster in _NT_GRUND if re.search(muster, low)), "")
    z = _NT_ZIEL.search(t)
    out["auftrag"] = (z.group(1) or "").upper() if z else ""
    out["ziel"] = (z.group(2) or "").strip(" .,!") if z and not z.group(1) else ""
    if not (out["arbeit"] or out["auftrag"] or out["ziel"] or re.search(r"(?i)nachtrag|zeit|gearbeitet", low)):
        return None                                                      # nur Datum + Dauer reicht nicht (Chat)
    return out


def nachtrag_text(n: dict, ziel_name: str = "") -> str:
    tag = date.fromisoformat(n["datum"])
    zeit = f"{n['von_uhr']}–{n['bis_uhr']} Uhr" if n.get("von_uhr") else dauer_text(int(n.get("minuten") or 0))
    return (f"{tag.strftime('%d.%m.%Y')} · {zeit} · {ARBEITEN.get(n.get('arbeit'), 'Grund fehlt')}"
            + (f" · {ziel_name}" if ziel_name else ""))


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


def _taetigkeit(t) -> str:
    return " ".join(str(t or "").split())[:60]


def _arbeit(a, taetigkeit="") -> str:
    """Grund pruefen: '' = keiner; sonst Schluessel aus ARBEITEN (auch die Beschriftung wird erkannt)."""
    a = str(a or "").strip()
    if not a:
        return ""
    k = a.lower() if a.lower() in ARBEITEN else next((k for k, v in ARBEITEN.items() if v.lower() == a.lower()), "")
    if not k:
        raise ValueError(f"Grund muss einer von {', '.join(ARBEITEN.values())} sein.")
    if k == "sonstiges" and not _taetigkeit(taetigkeit):
        raise ValueError("Bei „Sonstiges“ bitte kurz beschreiben, was du gemacht hast.")
    return k


def arbeit_von(x: dict) -> str:
    """Grund eines Eintrags; alte Freitexte (vor Z1) werden zugeordnet, sonst „sonstiges“ -- ohne Angabe ''."""
    if x.get("arbeit") in ARBEITEN:
        return x["arbeit"]
    t = str(x.get("taetigkeit") or "").lower()
    if not t:
        return ""
    return next((k for w, k in _ALT_ARBEIT if w in t), "sonstiges")


def arbeit_text(x: dict) -> str:
    """Anzeige: „Dreharbeiten“, „Sonstiges: Messe“; ein Zusatztext (alt oder frei) haengt mit „ – “ an."""
    k, t = arbeit_von(x), _taetigkeit(x.get("taetigkeit"))
    if not k:
        return ""
    name = ARBEITEN[k]
    if k == "sonstiges":
        return f"{name}: {t}" if t else name
    if not x.get("arbeit") and len(t.split()) <= 1:                     # alter Einwort-Freitext („Dreh“) = nur der Grund
        return name
    return f"{name} – {t}" if t and t.lower() != name.lower() else name


def _pause(p, brutto: int) -> int:
    if p in (None, ""):
        return 0
    try:
        m = int(float(str(p).replace(",", ".")))
    except ValueError:
        raise ValueError("Pause in Minuten.") from None
    if not 0 <= m < brutto:
        raise ValueError("Pause muss kuerzer sein als die Zeit selbst.")
    return m


def erinnerung_faellig(x: dict | None, jetzt_: datetime | None = None) -> bool:
    if not x:
        return False
    return (jetzt_ or _jetzt_lokal()) - _zeit(x["start"]) >= timedelta(hours=ERINNERN_STUNDEN)



def falte_zeiten(eintraege: list[dict]) -> dict[str, dict]:
    """Zeiteintraege aus der Kette (auch fuer Finanzen/Export, ohne Store-Objekt)."""
    out: dict[str, dict] = {}
    for e in eintraege:
        d, t = e["daten"], e["typ"]
        if t == "rechnung_festgeschrieben":               # Z2: abgerechnet = auf einer festgeschriebenen Rechnung
            if d.get("art") == "storno":                    # Storno gibt die Zeiten der Original-Rechnung frei
                for x in out.values():
                    x |= {k: "" for k in ("abgerechnet", "km_abgerechnet") if x.get(k) and x[k] == d.get("bezug")}
            pz = d.get("projektzeiten") or {}
            for i in pz.get("zeiten") or []:
                if i in out:
                    out[i] |= {"abgerechnet": d["nummer"], "abgerechnet_satz_cent": pz.get("satz_cent")}
            for i in pz.get("km") or []:
                if i in out:
                    out[i]["km_abgerechnet"] = d["nummer"]
            continue
        if t in ("zeit_start", "zeit_eintrag"):
            out[d["id"]] = dict(d) | {"ts": e["ts"], "fahrten": [], "storniert": False, "abgerechnet": "", "km_abgerechnet": ""}
        elif d.get("id") not in out:
            continue
        elif t == "zeit_stopp":
            out[d["id"]] |= {"ende": d["ende"], "satz_cent": d["satz_cent"]} \
                | {k: d[k] for k in ("taetigkeit", "pause_min", "arbeit") if k in d}
        elif t == "zeit_details":                           # PROJEKTZEITEN Z1: Taetigkeit/Pause/Notiz nachtragen (Z3: Position)
            out[d["id"]] |= {k: d[k] for k in ("taetigkeit", "pause_min", "notiz", "position", "arbeit") if k in d}
        elif t == "zeit_korrigiert":                        # Z1: Ein/Aus/Pause korrigiert, Verlauf bleibt in der Kette
            x = out[d["id"]]
            x.setdefault("korrekturen", []).append({"ts": e["ts"], "von": e.get("von", ""), "grund": d.get("grund", ""),
                                                     "vorher": {k: x.get(k) for k in ("start", "ende", "pause_min")}})
            x |= {k: d[k] for k in ("start", "ende", "pause_min", "taetigkeit", "arbeit") if k in d}
        elif t == "zeit_fahrt":
            out[d["id"]]["fahrten"] = [{k: d.get(k) for k in ("km", "quelle", "adresse", "betrag_cent")}]   # letzte gilt
        elif t == "zeit_storniert":
            out[d["id"]] |= {"storniert": True, "grund": d.get("grund", "")}
        elif t == "zeit_zugeordnet":
            out[d["id"]]["auftrag"] = d["auftrag"]
    for x in out.values():
        if x.get("ende"):
            brutto = round((_zeit(x["ende"]) - _zeit(x["start"])).total_seconds() / 60)
            x["minuten"] = max(0, brutto - int(x.get("pause_min") or 0))           # Z1: Pause zaehlt nicht
        x["laeuft"] = not x.get("ende") and not x["storniert"]
        x["kosten_cent"] = round(x.get("minuten", 0) * (x.get("satz_cent") or 0) / 60)
        x["fahrt_cent"] = sum(f.get("betrag_cent") or 0 for f in x["fahrten"])
    return out


def auswertung(eintraege: list[dict], von: str, bis: str, firmen: dict | None = None) -> dict:
    """PROJEKTZEITEN Z3: Zeiten im Zeitraum [von, bis] (Tage, inklusive) -- je Kunde, Taetigkeit, Woche, Monat, Auftrag.
    Nur beendete, nicht stornierte Eintraege; Stunden sind intern (kalkulatorisch), nichts davon ist eine Buchung."""
    firmen = firmen or {}
    zeilen = []
    for x in sorted(falte_zeiten(eintraege).values(), key=lambda x: x["start"]):
        tag = str(x["start"])[:10]
        if x["storniert"] or x["laeuft"] or not (von <= tag <= bis):
            continue
        km = sum(f.get("km") or 0 for f in x["fahrten"])
        iso = date.fromisoformat(tag).isocalendar()
        zeilen.append({"id": x["id"], "datum": tag, "von": str(x["start"])[11:16], "bis": str(x.get("ende") or "")[11:16],
                       "pause_min": int(x.get("pause_min") or 0), "minuten": x.get("minuten", 0), "km": km,
                       "taetigkeit": arbeit_text(x), "arbeit": ARBEITEN.get(arbeit_von(x), ""),
                       "auftrag": x.get("auftrag") or "", "firma": x.get("firma") or "",
                       "firma_name": firmen.get(x.get("firma"), x.get("firma") or ""), "kosten_cent": x["kosten_cent"],
                       "fahrt_cent": x["fahrt_cent"], "abgerechnet": x.get("abgerechnet") or "",
                       "woche": f"{iso[0]}-W{iso[1]:02d}", "monat": tag[:7]})

    def gruppe(feld, name=None):
        g: dict = {}
        for z in zeilen:
            k = z[feld] or "—"
            r = g.setdefault(k, {"schluessel": k, "name": (name(z) if name else k), "minuten": 0, "km": 0, "kosten_cent": 0})
            r["minuten"] += z["minuten"]
            r["km"] += z["km"]
            r["kosten_cent"] += z["kosten_cent"] + z["fahrt_cent"]
        return sorted(g.values(), key=lambda r: -r["minuten"])
    return {"von": von, "bis": bis, "zeilen": zeilen,
            "summe": {"minuten": sum(z["minuten"] for z in zeilen), "km": sum(z["km"] for z in zeilen),
                      "kosten_cent": sum(z["kosten_cent"] + z["fahrt_cent"] for z in zeilen), "eintraege": len(zeilen)},
            "je_kunde": gruppe("firma", lambda z: z["firma_name"]), "je_taetigkeit": gruppe("arbeit"),
            "je_auftrag": gruppe("auftrag"),
            "je_woche": sorted(gruppe("woche"), key=lambda r: r["schluessel"]),
            "je_monat": sorted(gruppe("monat"), key=lambda r: r["schluessel"])}


def auswertung_csv(a: dict) -> str:
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Datum", "Ein", "Aus", "Pause (min)", "Dauer (h)", "Grund", "Kunde", "Auftrag", "km",
                "Kosten EUR (kalkulatorisch)", "Abgerechnet auf"])
    for z in a["zeilen"]:
        w.writerow([f"{z['datum'][8:10]}.{z['datum'][5:7]}.{z['datum'][:4]}", z["von"], z["bis"], z["pause_min"],
                    f"{z['minuten'] / 60:.2f}".replace(".", ","), z["taetigkeit"], z["firma_name"], z["auftrag"], z["km"],
                    f"{(z['kosten_cent'] + z['fahrt_cent']) / 100:.2f}".replace(".", ","), z["abgerechnet"]])
    return "\ufeff" + buf.getvalue()


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
