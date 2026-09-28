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
from .eingangsbelege import KATEGORIEN, EingangStore
from .rechnungen import RechnungStore

POSITIONEN = {                                               # Anzeige-Texte (LUNA-OS) -> echte Umlaute
    "umsatz": "Betriebseinnahmen als umsatzsteuerlicher Kleinunternehmer",
    "wareneinkauf": "Waren, Roh- und Hilfsstoffe",
    "fremdleistungen": "Bezogene Fremdleistungen",
    "software": "Laufende EDV-Kosten (Software, Abos, Hosting)",
    "werbung": "Werbekosten",
    "telekommunikation": "Aufwendungen für Telekommunikation",
    "buero": "Übrige Betriebsausgaben: Bürobedarf, Porto",
    "reise": "Reisekosten (Übernachtung, Reisenebenkosten)",
    "fahrzeug": "Kraftfahrzeugkosten und andere Fahrtkosten",
    "bewirtung": "Bewirtungsaufwendungen (abziehbarer Teil 70 %)",
    "fortbildung": "Fortbildungskosten",
    "gwg": "Aufwendungen für geringwertige Wirtschaftsgüter",
    "anlage": "AfA auf bewegliche Wirtschaftsgüter",
    "gebuehren": "Beiträge, Gebühren, Abgaben und Versicherungen",
    "sonstiges": "Übrige unbeschränkt abziehbare Betriebsausgaben",
}
BEWIRTUNG_ANTEIL = 0.7
MONATE = ("Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez")


def _abziehbar(kategorie: str, betrag: int) -> int:
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
                "eigen": EigenbelegStore._falte(e), "firmen": {f["nummer"]: f["name"] for f in self.kunden.firmen()}}

    def journal(self, jahr: int | None = None, st: dict | None = None) -> list[dict]:
        """Alle Zahlungen als Journalzeilen, nach Zahlungsdatum. `jahr` filtert nach Zuordnungsjahr."""
        st = st or self._stand()
        zeilen = []
        for r in st["rechnungen"].values():
            for i, z in enumerate(r.get("zahlungen") or []):
                zeilen.append({"datum": z["datum"], "art": "einnahme", "betrag_cent": int(z.get("betrag_cent") or 0),
                               "kategorie": "umsatz", "bezug": r["nummer"], "index": i,
                               "gegenpartei": st["firmen"].get(r.get("firma"), r.get("firma", "")),
                               "text": f"Zahlung Rechnung {r['nummer']}" + (f" -- {r['titel']}" if r.get("titel") else ""),
                               "zuordnung_jahr": z.get("zuordnung_jahr"), "storniert": bool(z.get("storniert")),
                               "storno_grund": z.get("storno_grund", ""), "quelle": "rechnung"})
        for x in st["belege"].values():
            f = x.get("felder") or {}
            if not f:
                continue
            for i, z in enumerate(x.get("zahlungen") or []):
                zeilen.append({"datum": z["datum"], "art": "ausgabe", "betrag_cent": int(z.get("betrag_cent") or 0),
                               "kategorie": f.get("kategorie", "sonstiges"), "bezug": x["nummer"], "index": i,
                               "gegenpartei": f.get("lieferant", ""),
                               "text": f.get("leistung") or f.get("rechnungsnummer") or x.get("dateiname", ""),
                               "zuordnung_jahr": z.get("zuordnung_jahr"), "storniert": bool(z.get("storniert")),
                               "storno_grund": z.get("storno_grund", ""), "quelle": "beleg"})
        for x in st["eigen"].values():
            zeilen.append({"datum": x["datum"], "art": x["art"], "betrag_cent": x["betrag_cent"], "kategorie": x["kategorie"],
                           "bezug": x["nummer"], "index": None, "gegenpartei": x.get("gegenpartei", ""),
                           "text": x["text"], "zuordnung_jahr": x.get("zuordnung_jahr"),
                           "storniert": x["status"] == "storniert", "storno_grund": x.get("storno_grund", ""),
                           "quelle": "eigenbeleg"})
        for z in zeilen:
            z["jahr"] = int(z.get("zuordnung_jahr") or z["datum"][:4])
            z["abziehbar_cent"] = 0 if z["storniert"] else (
                z["betrag_cent"] if z["art"] == "einnahme" else _abziehbar(z["kategorie"], z["betrag_cent"]))
            z["position"] = POSITIONEN.get(z["kategorie"], POSITIONEN["sonstiges"])
        if jahr:
            zeilen = [z for z in zeilen if z["jahr"] == int(jahr)]
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

    def anlagen(self, jahr: int, st: dict | None = None) -> list[dict]:
        st = st or self._stand()
        out = []
        for x in st["belege"].values():
            f = x.get("felder") or {}
            if x["status"] != "gebucht" or f.get("kategorie") != "anlage" or not f.get("rechnungsdatum"):
                continue
            ak, nd = abs(int(f["betrag_cent"])), int(f.get("nutzungsdauer_jahre") or 1)
            an = date.fromisoformat(f["rechnungsdatum"])
            if an.year > jahr:
                continue
            bis, vor = self._afa_bis(ak, an, nd, jahr), self._afa_bis(ak, an, nd, jahr - 1)
            out.append({"beleg": x["nummer"], "bezeichnung": f.get("leistung") or f.get("lieferant", ""),
                        "lieferant": f.get("lieferant", ""), "anschaffung": an.isoformat(), "ak_cent": ak,
                        "nutzungsdauer_jahre": nd, "afa_jahr_cent": bis - vor, "afa_bis_cent": bis,
                        "restwert_cent": ak - bis, "bezahlt": bool(x.get("bezahlt_am"))})
        return sorted(out, key=lambda a: a["anschaffung"])

    # -- EUeR ----------------------------------------------------------------------------------------------------

    def euer(self, jahr: int, st: dict | None = None) -> dict:
        st = st or self._stand()
        j = [z for z in self.journal(jahr, st) if not z["storniert"]]
        einnahmen = sum(z["betrag_cent"] for z in j if z["art"] == "einnahme")
        pos: dict[str, int] = {}
        for z in j:
            if z["art"] == "ausgabe" and z["kategorie"] != "anlage":
                pos[z["kategorie"]] = pos.get(z["kategorie"], 0) + z["abziehbar_cent"]
        afa = sum(a["afa_jahr_cent"] for a in self.anlagen(jahr, st))
        if afa:
            pos["anlage"] = afa
        bew_voll = sum(z["betrag_cent"] for z in j if z["art"] == "ausgabe" and z["kategorie"] == "bewirtung")
        ausgaben = sum(pos.values())
        return {"jahr": jahr, "einnahmen_cent": einnahmen, "ausgaben_cent": ausgaben, "gewinn_cent": einnahmen - ausgaben,
                "einnahmen": [{"kategorie": "umsatz", "position": POSITIONEN["umsatz"], "betrag_cent": einnahmen}],
                "ausgaben": sorted(({"kategorie": k, "position": POSITIONEN[k], "betrag_cent": v} for k, v in pos.items()),
                                   key=lambda p: -p["betrag_cent"]),
                "bewirtung_nicht_abziehbar_cent": bew_voll - round(bew_voll * BEWIRTUNG_ANTEIL),
                "hinweis": "Bezeichnungen wie in der Anlage EÜR; die amtlichen Zeilennummern folgen mit dem Jahresabschluss "
                           "(Etappe 9)."}

    # -- Uebersicht ----------------------------------------------------------------------------------------------

    def uebersicht(self, jahr: int | None = None) -> dict:
        heute = jetzt().date()
        jahr = int(jahr or heute.year)
        st = self._stand()
        e, firmen = st["e"], st["firmen"]
        eu = self.euer(jahr, st)
        vj = self.euer(jahr - 1, st)
        journal = self.journal(None, st)
        j = [z for z in journal if z["jahr"] == jahr and not z["storniert"]]
        monate = [{"monat": MONATE[m], "einnahmen_cent": 0, "ausgaben_cent": 0} for m in range(12)]
        for z in j:
            m = int(z["datum"][5:7]) - 1 if int(z["datum"][:4]) == jahr else (11 if z["datum"][:4] > str(jahr) else 0)
            monate[m]["einnahmen_cent" if z["art"] == "einnahme" else "ausgaben_cent"] += z["abziehbar_cent"]
        # offene Posten
        forder = []
        for r in st["rechnungen"].values():
            if r["status"] == "offen" and r.get("art") != "storno":
                forder.append({"nummer": r["nummer"], "gegenpartei": firmen.get(r["firma"], r["firma"]),
                               "offen_cent": r["summe_cent"] - r["bezahlt_cent"], "faellig_am": r.get("faellig_am", ""),
                               "ueberfaellig": r.get("faellig_am", "9") < heute.isoformat()})
        verbind = []
        for x in st["belege"].values():
            f = x.get("felder") or {}
            if x["status"] == "gebucht" and f.get("betrag_cent") and x["bezahlt_cent"] != f["betrag_cent"]:
                verbind.append({"nummer": x["nummer"], "gegenpartei": f.get("lieferant", ""),
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
        kategorien = [{"kategorie": p["kategorie"], "name": POSITIONEN[p["kategorie"]], "betrag_cent": p["betrag_cent"]}
                      for p in eu["ausgaben"]]
        kunden_umsatz: dict[str, int] = {}
        for z in j:
            if z["art"] == "einnahme":
                kunden_umsatz[z["gegenpartei"] or "ohne Kunde"] = kunden_umsatz.get(z["gegenpartei"] or "ohne Kunde", 0) + z["betrag_cent"]
        jahre = sorted({z["jahr"] for z in journal} | {heute.year, jahr}, reverse=True)
        return {
            "jahr": jahr, "stand": heute.isoformat(), "jahre": jahre,
            "kennzahlen": {k: eu[k] for k in ("einnahmen_cent", "ausgaben_cent", "gewinn_cent")},
            "vorjahr": {k: vj[k] for k in ("einnahmen_cent", "ausgaben_cent", "gewinn_cent")},
            "afa_cent": next((p["betrag_cent"] for p in eu["ausgaben"] if p["kategorie"] == "anlage"), 0),
            "monate": monate, "kategorien": kategorien,
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
            "waechter": rs.waechter(jahr=jahr, rechnungen=st["rechnungen"], eintraege=e),
            "letzte": [z for z in reversed(journal)][:8],
        }


def journal_csv(zeilen: list[dict]) -> str:
    """Journal als CSV (Semikolon, deutsches Zahlenformat) -- fuer Excel/Numbers."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Datum", "Jahr", "Art", "Beleg", "Gegenpartei", "Text", "Kategorie", "Betrag EUR", "Abziehbar EUR",
                "Storniert"])
    for z in zeilen:
        w.writerow([z["datum"], z["jahr"], "Einnahme" if z["art"] == "einnahme" else "Ausgabe", z["bezug"],
                    z["gegenpartei"], z["text"], z["position"], f"{z['betrag_cent'] / 100:.2f}".replace(".", ","),
                    f"{z['abziehbar_cent'] / 100:.2f}".replace(".", ","), "ja" if z["storniert"] else ""])
    return buf.getvalue()


KATEGORIE_NAMEN = {"einnahme": EINNAHME_KATEGORIEN,
                   "ausgabe": {k: v[0] for k, v in KATEGORIEN.items() if k != "anlage"}}
