"""KUNDEN_FINANZEN Etappe 7: Zahlungen, EUeR-Journal, Anlageverzeichnis und die Finanz-Uebersicht fuer LUNA-OS.

Alles wird **nur gelesen und gefaltet** -- die Quelle bleibt die Hash-Kette (`buchhaltung/log.jsonl`):

- Einnahmen = Zahlungseingaenge auf Rechnungen (`rechnung_bezahlt`) + Eigenbelege „Einnahme“,
- Ausgaben  = Zahlungen auf Eingangsbelege (`eingang_bezahlt`) + Eigenbelege „Ausgabe“,
- jeweils nach **Zahlungsdatum** (Zufluss-/Abflussprinzip, § 4 Abs. 3 / § 11 EStG); abweichendes Jahr nur ueber die
  10-Tage-Regel (`zuordnung_jahr`, geprueft in `eigenbelege.zuordnung_pruefen`),
- stornierte Zahlungen/Eigenbelege stehen sichtbar im Journal, zaehlen aber nicht,
- Anlagegueter (> 800 € oder bewusst als Anlage gebucht) wirken ueber die **AfA** (linear, monatsgenau ab Anschaffung;
  Nutzungsdauer 1 Jahr = Computer/Software, voll im Anschaffungsjahr, BMF 22.02.2022), nicht ueber die Zahlung,
- Bewirtung zu 70 % abziehbar.

Die EUeR-Positionen tragen die Bezeichnungen der Anlage EUeR; die amtlichen **Zeilennummern** kommen erst in Etappe 9
(sie aendern sich jaehrlich und werden dort aus der Anleitung des Jahres uebernommen). Schlank nach CEO-Entscheidung 5:
kein Sammelposten, keine Privatanteile.
"""
from __future__ import annotations

import csv
import io
from datetime import date

from .angebote import AngebotStore, summen
from .beauftragung import AuftragBuch
from .buchhaltung import Buchhaltung, jetzt
from .eigenbelege import EINNAHME_KATEGORIEN, EigenbelegStore
from .eingangsbelege import KATEGORIEN, PRIVAT, EingangStore, anteile, teile
from .rechnungen import RechnungStore

POSITIONEN = {                                               # Anzeige-Texte (LUNA-OS) -> echte Umlaute
    "umsatz": "Betriebseinnahmen als umsatzsteuerlicher Kleinunternehmer",
    "barter": "Betriebseinnahmen: Sachleistungen (Barter, Wert der Ware)",
    "anlage_abgang": "Verkauf/private Entnahme von Anlagegütern inkl. GWG (Erlös bzw. Teilwert)",
    "nebenforderung": "Betriebseinnahmen: Verzugszinsen/Mahnkosten (nicht umsatzsteuerbar)",
    "wareneinkauf": "Waren, Roh- und Hilfsstoffe",
    "fremdleistungen": "Bezogene Fremdleistungen",
    "software": "Laufende EDV-Kosten (Software, Abos, Hosting)",
    "werbung": "Werbekosten",
    "telekommunikation": "Aufwendungen für Telekommunikation",
    "buero": "Arbeitsmittel (Bürobedarf, Porto, Fachliteratur)",
    "reise": "Reisekosten (Übernachtung, Reisenebenkosten)",
    "fahrzeug": "Kraftfahrzeugkosten und andere Fahrtkosten",
    "bewirtung": "Bewirtungsaufwendungen (abziehbarer Teil 70 %)",
    "fortbildung": "Fortbildungskosten",
    "gwg": "Aufwendungen für geringwertige Wirtschaftsgüter",
    "anlage": "AfA auf bewegliche Wirtschaftsgüter",
    "gebuehren": "Beiträge, Gebühren, Abgaben und Versicherungen",
    "sonstiges": "Übrige unbeschränkt abziehbare Betriebsausgaben",
    "privat": "Privatanteil – keine Betriebsausgabe",
}
BEWIRTUNG_ANTEIL = 0.7
ZEITRAEUME = {"jahr": range(1, 13), "q1": range(1, 4), "q2": range(4, 7), "q3": range(7, 10), "q4": range(10, 13),
              **{f"m{m:02d}": range(m, m + 1) for m in range(1, 13)}}


def monate_von(zeitraum: str) -> set[int]:
    if zeitraum not in ZEITRAEUME:
        raise ValueError("Zeitraum muss jahr, q1-q4 oder m01-m12 sein.")
    return set(ZEITRAEUME[zeitraum])


VERLUSTVORTRAG = "verlustvortrag_erfasst"


def verlustvortrag(eintraege: list[dict], aus_jahr: int) -> int | None:
    """Verbleibender Verlust aus `aus_jahr` (Angabe des CEO, z. B. aus der EUeR/dem Bescheid des Vorjahres) -- die letzte
    Angabe gilt. Kein Teil der EUeR: das Finanzamt verrechnet ihn nach § 10d EStG mit spaeteren Gewinnen."""
    w = [e["daten"] for e in eintraege if e["typ"] == VERLUSTVORTRAG and int(e["daten"].get("jahr", 0)) == int(aus_jahr)]
    return int(w[-1]["betrag_cent"]) if w else None


def kennzahlen(zeilen: list[dict]) -> dict:
    ein = sum(z["abziehbar_cent"] for z in zeilen if z["art"] == "einnahme" and not z["storniert"])
    aus = sum(z["abziehbar_cent"] for z in zeilen if z["art"] == "ausgabe" and not z["storniert"])
    return {"einnahmen_cent": ein, "ausgaben_cent": aus, "gewinn_cent": ein - aus}
MONATE = ("Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez")


def _abziehbar(kategorie: str, betrag: int) -> int:
    if kategorie == PRIVAT:
        return 0                                             # privater Teil einer gemischten Rechnung (§ 12 EStG)
    if kategorie == "anlage":
        return 0                                             # wirkt ueber die AfA
    if kategorie == "bewirtung":
        return round(betrag * BEWIRTUNG_ANTEIL)
    return betrag


class Finanzen:
    def __init__(self, bh: Buchhaltung, kunden):
        self.bh, self.kunden = bh, kunden

    # -- Grundlagen ----------------------------------------------------------------------------------------------

    def _stand(self, eintraege: list[dict] | None = None) -> dict:
        e = self.bh.eintraege() if eintraege is None else eintraege
        return {"e": e, "rechnungen": RechnungStore._falte(e)[1], "belege": EingangStore._falte(e),
                "eigen": EigenbelegStore._falte(e), "firmen": {f["nummer"]: f["name"] for f in self.kunden.firmen()},
                "firmen_nr": {f["nummer"]: f["anzeige"] for f in self.kunden.firmen()}}

    def journal(self, jahr: int | None = None, st: dict | None = None, firma: str = "") -> list[dict]:
        """Alle Zahlungen als Journalzeilen, nach Zahlungsdatum. `jahr` filtert nach Zuordnungsjahr, `firma` nach
        Stammdaten-Nummer (jede Nummer der Firma, Etappe 14)."""
        st = st or self._stand()
        zeilen = []
        for r in st["rechnungen"].values():
            for i, z in enumerate(r.get("zahlungen") or []):
                if z.get("nebenforderung_cent"):              # Etappe 10: gezahlte Verzugszinsen/Mahnkosten
                    zeilen.append({"datum": z["datum"], "art": "einnahme", "betrag_cent": int(z["nebenforderung_cent"]),
                                   "kategorie": "nebenforderung", "bezug": r["nummer"], "index": i,
                                   "gegenpartei": st["firmen"].get(r.get("firma"), r.get("firma", "")),
                                   "text": f"Verzugszinsen/Mahnkosten zu Rechnung {r['nummer']}",
                                   "zuordnung_jahr": z.get("zuordnung_jahr"), "storniert": bool(z.get("storniert")),
                                   "storno_grund": z.get("storno_grund", ""), "quelle": "rechnung"})
                zeilen.append({"datum": z["datum"], "art": "einnahme", "betrag_cent": int(z.get("betrag_cent") or 0),
                               "kategorie": "umsatz", "bezug": r["nummer"], "index": i,
                               "gegenpartei": st["firmen"].get(r.get("firma"), r.get("firma", "")),
                               "text": f"Zahlung Rechnung {r['nummer']}" + (f" -- {r['titel']}" if r.get("titel") else ""),
                               "zuordnung_jahr": z.get("zuordnung_jahr"), "storniert": bool(z.get("storniert")),
                               "storno_grund": z.get("storno_grund", ""), "quelle": "rechnung"})
        for r in st["rechnungen"].values():                   # Etappe 12: Barter-Ware = Einnahme (+ Anschaffung)
            kunde = st["firmen"].get(r.get("firma"), r.get("firma", ""))
            for v in r.get("ware_vorgaenge") or []:
                if v.get("verwendung") == "leihgabe":
                    continue
                basis = {"datum": v["datum"], "bezug": r["nummer"], "index": None, "gegenpartei": kunde,
                         "zuordnung_jahr": None, "storniert": v["storniert"], "storno_grund": v.get("storno_grund", ""),
                         "quelle": "ware"}
                zeilen.append(basis | {"art": "einnahme", "betrag_cent": v["wert_cent"], "kategorie": "barter",
                                       "text": f"Sachleistung (Barter) zu {r['nummer']}: {v.get('text', '')}"})
                if v.get("verwendung") == "content":
                    zeilen.append(basis | {"art": "ausgabe", "betrag_cent": v["wert_cent"], "kategorie": v["kategorie"],
                                           "text": f"Barter-Ware für Content: {v.get('text', '')}"})
        for x in st["belege"].values():
            f = x.get("felder") or {}
            if not f:
                continue
            tl = teile(f) if (f.get("art") or "ausgabe") == "ausgabe" else [
                {"text": f.get("leistung", ""), "betrag_cent": f.get("betrag_cent", 0), "kategorie": f.get("kategorie", "umsatz")}]
            for i, z in enumerate(x.get("zahlungen") or []):                  # Gutschrift = Einnahme (Geldeingang)
                for t, anteil in zip(tl, anteile(int(z.get("betrag_cent") or 0), tl)):   # Etappe 11: je Position
                    if not anteil and len(tl) > 1:
                        continue
                    zeilen.append({"datum": z["datum"], "art": f.get("art") or "ausgabe", "betrag_cent": anteil,
                                   "kategorie": t["kategorie"], "bezug": x["nummer"], "index": i,
                                   "gegenpartei": f.get("lieferant", ""), "firma": f.get("lieferant_firma", ""),
                                   "text": (t.get("text") if len(tl) > 1 else "") or f.get("leistung") or f.get("rechnungsnummer")
                                   or x.get("dateiname", ""),
                                   "zuordnung_jahr": z.get("zuordnung_jahr"), "storniert": bool(z.get("storniert")),
                                   "storno_grund": z.get("storno_grund", ""), "quelle": "beleg"})
        for x in st["eigen"].values():
            zeilen.append({"datum": x["datum"], "art": x["art"], "betrag_cent": x["betrag_cent"], "kategorie": x["kategorie"],
                           "bezug": x["nummer"], "index": None, "gegenpartei": x.get("gegenpartei", ""), "firma": x.get("firma", ""),
                           "text": x["text"], "zuordnung_jahr": x.get("zuordnung_jahr"),
                           "storniert": x["status"] == "storniert", "storno_grund": x.get("storno_grund", ""),
                           "quelle": "eigenbeleg"})
        for r in st["rechnungen"].values():                   # Kunde der Rechnung (Zahlungen/Barter)
            for z in zeilen:
                if z["bezug"] == r["nummer"]:
                    z.setdefault("firma", r.get("firma", ""))
        for z in zeilen:
            z.setdefault("firma", "")
            z["firma_nr"] = st["firmen_nr"].get(z["firma"], z["firma"])
            z["jahr"] = int(z.get("zuordnung_jahr") or z["datum"][:4])
            # Monat im Zuordnungsjahr (10-Tage-Regel: Januar-Zahlung fuers Vorjahr -> Dezember, umgekehrt Januar)
            z["monat"] = int(z["datum"][5:7]) if int(z["datum"][:4]) == z["jahr"] else (12 if z["datum"][:4] > str(z["jahr"]) else 1)
            z["abziehbar_cent"] = 0 if z["storniert"] else (
                z["betrag_cent"] if z["art"] == "einnahme" else _abziehbar(z["kategorie"], z["betrag_cent"]))
            z["position"] = POSITIONEN.get(z["kategorie"], POSITIONEN["sonstiges"])
        if jahr:
            zeilen = [z for z in zeilen if z["jahr"] == int(jahr)]
        if firma:
            h = self.kunden.haupt(self.kunden._stand()[0], firma)
            zeilen = [z for z in zeilen if z["firma"] == h]
        return sorted(zeilen, key=lambda z: (z["datum"], z["bezug"], z["index"] or 0))

    # -- Anlageverzeichnis ---------------------------------------------------------------------------------------

    @staticmethod
    def _afa_bis(ak: int, anschaffung: date, nd: int, jahr: int) -> int:
        """Kumulierte AfA bis Ende `jahr` (linear, monatsgenau; ND 1 Jahr = voll im Anschaffungsjahr)."""
        if jahr < anschaffung.year:
            return 0
        if nd <= 1:
            return ak
        monate = (jahr - anschaffung.year) * 12 + (12 - anschaffung.month + 1)
        return min(ak, round(ak * monate / (nd * 12)))

    @staticmethod
    def _afa_bis_monat(ak: int, an: date, nd: int, jahr: int, monat: int) -> int:
        """Kumulierte AfA bis Ende (jahr, monat) -- monatsgenau; zum Dezember identisch mit `_afa_bis`."""
        if (jahr, monat) < (an.year, an.month):
            return 0
        if nd <= 1:
            return ak                                            # voll im Anschaffungsmonat
        monate = (jahr - an.year) * 12 + monat - an.month + 1
        return min(ak, round(ak * monate / (nd * 12)))

    def afa_zeilen(self, jahr: int, st: dict | None = None) -> list[dict]:
        """Abschreibung als Monatszeilen (fuer Monats-/Quartalszahlen und Drill-down); Summe = AfA des Jahres.
        Im laufenden Jahr nur bis zum aktuellen Monat (Stand „bisher“ -- keine Abschreibung fuer Monate, die noch kommen)."""
        st = st or self._stand()
        heute = jetzt().date()
        bis_monat = 12 if jahr < heute.year else heute.month if jahr == heute.year else 0
        out = []
        for x, f, bez, ak, nd, an in self._anlage_teile(st):
            vorher = self._afa_bis_monat(ak, an, nd, jahr - 1, 12)
            for m in range(1, bis_monat + 1):
                bis = self._afa_bis_monat(ak, an, nd, jahr, m)
                if bis > vorher:
                    out.append({"datum": f"{jahr}-{m:02d}-01", "jahr": jahr, "monat": m, "art": "ausgabe",
                                "betrag_cent": 0, "abziehbar_cent": bis - vorher, "kategorie": "anlage",
                                "position": POSITIONEN["anlage"], "bezug": x["nummer"], "index": None,
                                "gegenpartei": f.get("lieferant", ""),
                                "text": f"Abschreibung {m:02d}/{jahr}: {bez}",
                                "zuordnung_jahr": None, "storniert": False, "storno_grund": "", "quelle": "afa"})
                vorher = bis
        return out

    def posten(self, jahr: int, zeitraum: str = "jahr", *, art: str = "", kategorie: str = "", gegenpartei: str = "",
               st: dict | None = None) -> list[dict]:
        """Alle Zeilen, die eine Kennzahl ergeben (Zahlungen + monatliche AfA) -- Grundlage fuer jede Zahl im Cockpit und
        fuer den Drill-down. Summe der `abziehbar_cent` (ohne Stornos) = die angezeigte Zahl."""
        st = st or self._stand()
        monate = monate_von(zeitraum)
        z = self.journal(jahr, st) + self.afa_zeilen(jahr, st)
        z = [x for x in z if x["monat"] in monate]
        if art:
            z = [x for x in z if x["art"] == art]
        if kategorie:
            z = [x for x in z if x["kategorie"] == kategorie]
        if gegenpartei:
            z = [x for x in z if (x["gegenpartei"] or "ohne Kunde").lower() == gegenpartei.lower()]
        return sorted(z, key=lambda x: (x["datum"], x["bezug"], x["index"] or 0))

    @staticmethod
    def _anlage_teile(st: dict):
        """Anlagegueter: jede Position mit Kategorie „anlage“ (auch aus einer aufgeteilten Rechnung, Etappe 11)."""
        for x in st["belege"].values():
            f = x.get("felder") or {}
            if x["status"] != "gebucht" or not f.get("rechnungsdatum") or (f.get("art") or "ausgabe") != "ausgabe":
                continue
            for t in teile(f):
                if t["kategorie"] == "anlage":
                    yield (x, f, t.get("text") or f.get("leistung") or f.get("lieferant", ""), abs(int(t["betrag_cent"])),
                           int(t.get("nutzungsdauer_jahre") or f.get("nutzungsdauer_jahre") or 1),
                           date.fromisoformat(f["rechnungsdatum"]))
        for r in st["rechnungen"].values():                   # Barter-Ware als Anlagegut (Etappe 12)
            for v in r.get("ware_vorgaenge") or []:
                if not v["storniert"] and v.get("verwendung") == "content" and v.get("kategorie") == "anlage":
                    yield ({"nummer": r["nummer"], "bezahlt_am": v["datum"]},
                           {"lieferant": st["firmen"].get(r.get("firma"), r.get("firma", ""))}, v.get("text", ""),
                           int(v["wert_cent"]), int(v.get("nutzungsdauer_jahre") or 1), date.fromisoformat(v["datum"]))

    def anlagen(self, jahr: int, st: dict | None = None) -> list[dict]:
        st = st or self._stand()
        out = []
        for x, f, bez, ak, nd, an in self._anlage_teile(st):
            if an.year > jahr:
                continue
            bis, vor = self._afa_bis(ak, an, nd, jahr), self._afa_bis(ak, an, nd, jahr - 1)
            out.append({"beleg": x["nummer"], "bezeichnung": bez,
                        "lieferant": f.get("lieferant", ""), "anschaffung": an.isoformat(), "ak_cent": ak,
                        "nutzungsdauer_jahre": nd, "afa_jahr_cent": bis - vor, "afa_bis_cent": bis,
                        "restwert_cent": ak - bis, "bezahlt": bool(x.get("bezahlt_am"))})
        return sorted(out, key=lambda a: a["anschaffung"])

    # -- EUeR ----------------------------------------------------------------------------------------------------

    def euer(self, jahr: int, st: dict | None = None) -> dict:
        st = st or self._stand()
        j = [z for z in self.posten(jahr, st=st) if not z["storniert"]]
        einnahmen = sum(z["betrag_cent"] for z in j if z["art"] == "einnahme")
        neben = sum(z["betrag_cent"] for z in j if z["art"] == "einnahme" and z["kategorie"] == "nebenforderung")
        barter = sum(z["betrag_cent"] for z in j if z["art"] == "einnahme" and z["kategorie"] == "barter")
        abgang = sum(z["betrag_cent"] for z in j if z["art"] == "einnahme" and z["kategorie"] == "anlage_abgang")
        pos: dict[str, int] = {}
        for z in j:
            if z["art"] == "ausgabe" and z["abziehbar_cent"]:
                pos[z["kategorie"]] = pos.get(z["kategorie"], 0) + z["abziehbar_cent"]
        bew_voll = sum(z["betrag_cent"] for z in j if z["art"] == "ausgabe" and z["kategorie"] == "bewirtung")
        ausgaben = sum(pos.values())
        return {"jahr": jahr, "einnahmen_cent": einnahmen, "ausgaben_cent": ausgaben, "gewinn_cent": einnahmen - ausgaben,
                "einnahmen": [{"kategorie": k, "position": POSITIONEN[k], "betrag_cent": v} for k, v in (
                    ("umsatz", einnahmen - neben - barter - abgang), ("barter", barter), ("nebenforderung", neben),
                    ("anlage_abgang", abgang)) if v or k == "umsatz"],
                "ausgaben": sorted(({"kategorie": k, "position": POSITIONEN[k], "betrag_cent": v} for k, v in pos.items()),
                                   key=lambda p: -p["betrag_cent"]),
                "bewirtung_nicht_abziehbar_cent": bew_voll - round(bew_voll * BEWIRTUNG_ANTEIL),
                "hinweis": "Bezeichnungen wie in der Anlage EÜR; die amtlichen Zeilennummern folgen mit dem Jahresabschluss "
                           "(Etappe 9)."}

    # -- Uebersicht ----------------------------------------------------------------------------------------------

    def uebersicht(self, jahr: int | None = None, zeitraum: str = "jahr") -> dict:
        heute = jetzt().date()
        jahr = int(jahr or heute.year)
        ms = monate_von(zeitraum)
        st = self._stand()
        e, firmen = st["e"], st["firmen"]
        journal = self.journal(None, st)
        p, pv = self.posten(jahr, st=st), self.posten(jahr - 1, st=st)
        j = [z for z in p if z["monat"] in ms and not z["storniert"]]
        monate = []
        for m in range(1, 13):
            k, kv = kennzahlen([z for z in p if z["monat"] == m]), kennzahlen([z for z in pv if z["monat"] == m])
            monate.append({"monat": MONATE[m - 1], "nr": m, "einnahmen_cent": k["einnahmen_cent"],
                           "ausgaben_cent": k["ausgaben_cent"], "vj_einnahmen_cent": kv["einnahmen_cent"],
                           "vj_ausgaben_cent": kv["ausgaben_cent"]})
        quartale = []
        for q in range(1, 5):
            k = kennzahlen([z for z in p if z["monat"] in monate_von(f"q{q}")])
            kv = kennzahlen([z for z in pv if z["monat"] in monate_von(f"q{q}")])
            quartale.append({"quartal": f"q{q}"} | k | {"vj_gewinn_cent": kv["gewinn_cent"], "vj_einnahmen_cent": kv["einnahmen_cent"]})
        # offene Posten
        forder = []
        for r in st["rechnungen"].values():
            if r["status"] == "offen" and r.get("art") != "storno":
                forder.append({"nummer": r["nummer"], "act": "re-detail", "gegenpartei": firmen.get(r["firma"], r["firma"]),
                               "offen_cent": r["geld_cent"] - r["bezahlt_cent"] + (0 if r.get("ware_erhalten") else r.get("ware_cent", 0)),
                               "faellig_am": r.get("faellig_am", ""),
                               "ueberfaellig": r.get("faellig_am", "9") < heute.isoformat()})
        verbind = []
        for x in st["belege"].values():
            f = x.get("felder") or {}
            if x["status"] == "gebucht" and f.get("betrag_cent") and x["bezahlt_cent"] != f["betrag_cent"]:
                (forder if f.get("art") == "einnahme" else verbind).append({"nummer": x["nummer"], "act": "bl-detail",
                                "gegenpartei": f.get("lieferant", ""),
                                "offen_cent": f["betrag_cent"] - x["bezahlt_cent"], "faellig_am": f.get("faellig_am", ""),
                                "ueberfaellig": bool(f.get("faellig_am")) and f["faellig_am"] < heute.isoformat()})
        zu_pruefen = sum(1 for x in st["belege"].values() if x["status"] == "zu_pruefen")
        # Pipeline: offene Angebote, Auftraege ohne Rechnung, Rechnungsentwuerfe
        angebote = [AngebotStore._anreichern(a, heute) for a in AngebotStore._falte(e).values()]
        offen_an = [a for a in angebote if a["anzeige_status"] == "versendet"]
        berechnet = {r.get("auftrag") for r in st["rechnungen"].values()          # Storno-Gegenbeleg zaehlt nicht
                     if r.get("auftrag") and r["status"] != "storniert" and r.get("art") != "storno"}
        auftraege = [a for a in AuftragBuch._falte(e).values() if a["status"] != "storniert" and a["nummer"] not in berechnet]
        auftrag_summe = sum(summen(a["positionen"], a.get("zuschlaege") or [], a.get("rabatt_prozent") or 0)["gesamt_cent"]
                            for a in auftraege)
        entwuerfe = RechnungStore._falte(e)[0]
        rs = RechnungStore(self.bh, self.kunden)
        je_kat: dict[str, int] = {}
        for z in j:
            if z["art"] == "ausgabe" and z["abziehbar_cent"]:
                je_kat[z["kategorie"]] = je_kat.get(z["kategorie"], 0) + z["abziehbar_cent"]
        kategorien = sorted(({"kategorie": k, "name": POSITIONEN.get(k, k), "betrag_cent": v} for k, v in je_kat.items()),
                            key=lambda x: -x["betrag_cent"])
        w = rs.waechter(jahr=jahr, rechnungen=st["rechnungen"], eintraege=e)
        hochrechnung = None
        if jahr == heute.year and w["umsatz_cent"]:
            tage = (heute - date(jahr, 1, 1)).days + 1
            hochrechnung = round(w["umsatz_cent"] * (366 if jahr % 4 == 0 else 365) / tage)
        kunden_umsatz: dict[str, int] = {}
        for z in j:
            if z["art"] == "einnahme":
                kunden_umsatz[z["gegenpartei"] or "ohne Kunde"] = kunden_umsatz.get(z["gegenpartei"] or "ohne Kunde", 0) + z["betrag_cent"]
        jahre = sorted({z["jahr"] for z in journal} | {heute.year, jahr}, reverse=True)
        return {
            "jahr": jahr, "stand": heute.isoformat(), "jahre": jahre,
            "zeitraum": zeitraum,
            "verlustvortrag": vv_info(verlustvortrag(e, jahr - 1), jahr - 1, kennzahlen(p)["gewinn_cent"]),
            "kennzahlen": kennzahlen(j),
            "vorjahr": kennzahlen([z for z in pv if z["monat"] in ms]),
            "afa_cent": sum(z["abziehbar_cent"] for z in j if z["quelle"] == "afa"),
            "monate": monate, "quartale": quartale, "kategorien": kategorien, "hochrechnung_cent": hochrechnung,
            "kunden": sorted(({"name": k, "betrag_cent": v} for k, v in kunden_umsatz.items()), key=lambda k: -k["betrag_cent"])[:5],
            "forderungen": {"summe_cent": sum(x["offen_cent"] for x in forder), "anzahl": len(forder),
                            "ueberfaellig": sum(1 for x in forder if x["ueberfaellig"]),
                            "liste": sorted(forder, key=lambda x: x["faellig_am"])},
            "verbindlichkeiten": {"summe_cent": sum(x["offen_cent"] for x in verbind), "anzahl": len(verbind),
                                  "ueberfaellig": sum(1 for x in verbind if x["ueberfaellig"]),
                                  "liste": sorted(verbind, key=lambda x: x["faellig_am"] or "9")},
            "pipeline": {"angebote_anzahl": len(offen_an), "angebote_cent": sum(a["summe_cent"] for a in offen_an),
                         "auftraege_anzahl": len(auftraege), "auftraege_cent": auftrag_summe,
                         "rechnung_entwuerfe": len(entwuerfe)},
            "belege_zu_pruefen": zu_pruefen,
            "waechter": w,
            "letzte": [z for z in reversed(journal)][:8],
        }


def vv_info(vv: int | None, aus_jahr: int, gewinn_cent: int) -> dict | None:
    """Verlustvortrag gegen den Gewinn des Folgejahres: wie viel ist schon „aufgebraucht“, wie viel bleibt."""
    if vv is None:
        return None
    verrechnet = min(vv, max(gewinn_cent, 0))
    return {"aus_jahr": aus_jahr, "betrag_cent": vv, "gewinn_cent": gewinn_cent, "verrechnet_cent": verrechnet,
            "verbleibend_cent": vv - verrechnet}


def journal_csv(zeilen: list[dict]) -> str:
    """Journal als CSV (Semikolon, deutsches Zahlenformat) -- fuer Excel/Numbers."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Datum", "Jahr", "Art", "Beleg", "Nr.", "Gegenpartei", "Text", "Kategorie", "Betrag EUR", "Abziehbar EUR",
                "Storniert"])
    for z in zeilen:
        w.writerow([z["datum"], z["jahr"], "Einnahme" if z["art"] == "einnahme" else "Ausgabe", z["bezug"],
                    z.get("firma_nr", ""), z["gegenpartei"], z["text"], z["position"], f"{z['betrag_cent'] / 100:.2f}".replace(".", ","),
                    f"{z['abziehbar_cent'] / 100:.2f}".replace(".", ","), "ja" if z["storniert"] else ""])
    return buf.getvalue()


KATEGORIE_NAMEN = {"einnahme": EINNAHME_KATEGORIEN,
                   "ausgabe": {k: v[0] for k, v in KATEGORIEN.items() if k != "anlage"}}
