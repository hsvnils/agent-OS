"""KUNDEN_FINANZEN Etappe 9: Jahresabschluss -- Abschluss-Pruefung, EUeR je Zeile (Eingabehilfe fuer ELSTER),
EUeR als PDF und der Export fuer Finanzamt/Steuerberater (Datenzugriff § 147 Abs. 6 AO).

Alles wird aus der Hash-Kette **gelesen**; nichts wird veraendert. Der Export (ZIP) enthaelt:
- die maschinenlesbaren Tabellen des Jahres (CSV, Semikolon, UTF-8) mit Beschreibung `index.xml`
  (Beschreibungsstandard fuer die Datenueberlassung, GoBD Rz. 164 ff.),
- die vollstaendige Hash-Kette `kassenbuch/log.jsonl` samt Pruefergebnis (Unveraenderbarkeit nachpruefbar),
- alle Belegdateien, auf die das Jahr verweist, im Original (unveraendert, Pfad und SHA-256 wie im Kassenbuch),
- die EUeR als PDF und eine LIESMICH-Datei.
"""
from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from datetime import date
from pathlib import Path

from .beleg_pdf import DEJAVU, _latin1, eur
from .buchhaltung import Buchhaltung, jetzt
from .eigenbelege import EigenbelegStore
from .eingangsbelege import KATEGORIEN, EingangStore
from .euer_zeilen import zeile, zeilen_hinweis
from .finanzen import POSITIONEN, Finanzen
from .rechnungen import RechnungStore
from .todos import QUITTUNG, beginn_buchhaltung


def _d(iso: str) -> str:
    """ISO -> TT.MM.JJJJ (leer bleibt leer)."""
    s = str(iso or "")[:10]
    return f"{s[8:10]}.{s[5:7]}.{s[:4]}" if len(s) == 10 else ""


def _b(cent_betrag) -> str:
    """Cent -> 1234,56 (ohne Tausenderpunkt, fuer Tabellen/Pruefsoftware)."""
    c = int(cent_betrag or 0)
    return f"{'-' if c < 0 else ''}{abs(c) // 100},{abs(c) % 100:02d}"


def _csv(kopf: list[str], zeilen: list[list]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    w.writerow(kopf)
    for z in zeilen:
        w.writerow(["" if x is None else x for x in z])
    return buf.getvalue().encode("utf-8")


# -- Abschluss-Pruefung ---------------------------------------------------------------------------------------------

def abschluss_check(bh: Buchhaltung, kunden, jahr: int, heute: date | None = None) -> list[dict]:
    """Was vor der Steuererklaerung erledigt sein sollte. `ok=False` + `pflicht=True` = muss vorher geklaert werden."""
    heute = heute or jetzt().date()
    e = bh.eintraege()
    punkte = []

    def p(ok, pflicht, text, detail="", ziel=""):
        punkte.append({"ok": bool(ok), "pflicht": pflicht, "text": text, "detail": detail, "ziel": ziel})

    befunde = bh.pruefe_kette() + bh.pruefe_belege()
    p(not befunde, True, "Kassenbuch unverändert (Hash-Kette und Belegdateien geprüft)",
      "; ".join(befunde[:3]) if befunde else f"{len(e)} Einträge, {len(bh.eintraege('beleg'))} Belegdateien")
    ende = min(12, heute.month - 1) if jahr == heute.year else 12
    quittiert = {x["daten"].get("schluessel") for x in e if x["typ"] == QUITTUNG}
    start = beginn_buchhaltung(e) or f"{jahr}-13"
    faellig = [f"{jahr}-{m:02d}" for m in range(1, ende + 1) if f"{jahr}-{m:02d}" >= start]
    offen = [m for m in faellig if f"monat:{m}" not in quittiert]
    p(not offen, True, "Alle Monate mit dem Kontoauszug abgeglichen",
      ("offen: " + ", ".join(f"{x[5:]}/{x[:4]}" for x in offen)) if offen
      else f"{len(faellig)} Monat(e) bestätigt" if faellig else "noch kein abgeschlossener Monat", "finanzen:uebersicht")
    belege = EingangStore._falte(e)
    zp = [x["nummer"] for x in belege.values() if x["status"] == "zu_pruefen"]
    p(not zp, True, "Alle Belege geprüft und gebucht", ", ".join(zp[:6]) + (" …" if len(zp) > 6 else ""), "belege:pruefen")
    entwuerfe, rechnungen = RechnungStore._falte(e)
    p(not entwuerfe, False, "Keine offenen Rechnungsentwürfe", f"{len(entwuerfe)} Entwurf/Entwürfe" if entwuerfe else "",
      "rechnungen:entwuerfe")
    ford = [r["nummer"] for r in rechnungen.values() if r["status"] == "offen" and r.get("art") != "storno"]
    p(not ford, False, "Alle Ausgangsrechnungen bezahlt",
      (", ".join(ford[:6]) + " -- zählen erst im Jahr des Zahlungseingangs") if ford else "", "rechnungen:offen")
    unbez = [x["nummer"] for x in belege.values() if x["status"] == "gebucht"
             and (x.get("felder") or {}).get("betrag_cent") and x.get("bezahlt_cent", 0) != x["felder"]["betrag_cent"]]
    p(not unbez, False, "Alle gebuchten Belege bezahlt bzw. Geld eingegangen",
      (", ".join(unbez[:6]) + " -- zählen erst im Jahr der Zahlung") if unbez else "", "belege:gebucht")
    return punkte


# -- EUeR je Zeile ----------------------------------------------------------------------------------------------------

def verlustvortrag_hinweis(bh: Buchhaltung, f: Finanzen, jahr: int) -> dict | None:
    from .finanzen import verlustvortrag, vv_info
    return vv_info(verlustvortrag(bh.eintraege(), jahr - 1), jahr - 1, f.euer(jahr)["gewinn_cent"])


def euer_zeilen(f: Finanzen, jahr: int) -> dict:
    """EUeR des Jahres mit amtlicher Zeile je Position (Eingabehilfe fuer ELSTER)."""
    eu = f.euer(jahr)
    zeilen = []
    neben = sum(p["betrag_cent"] for p in eu["einnahmen"] if p["kategorie"] == "nebenforderung")
    abgang = sum(p["betrag_cent"] for p in eu["einnahmen"] if p["kategorie"] == "anlage_abgang")
    einnahmen = [{"kategorie": "umsatz", "position": POSITIONEN["umsatz"], "betrag_cent": eu["einnahmen_cent"] - abgang}]
    if neben:                                   # Zeile 12 = alle Einnahmen (auch Barter), 13 nachrichtlich nicht steuerbare
        einnahmen.append({"kategorie": "nebenforderung", "position": POSITIONEN["nebenforderung"], "betrag_cent": neben})
    if abgang:                                  # Zeile 19: Verkauf/Entnahme von Anlagegütern inkl. GWG (Etappe 12)
        einnahmen.append({"kategorie": "anlage_abgang", "position": POSITIONEN["anlage_abgang"], "betrag_cent": abgang})
    eu = eu | {"einnahmen": einnahmen}
    for p in eu["einnahmen"] + eu["ausgaben"]:
        z = zeile(jahr, p["kategorie"])
        zeilen.append({"art": "einnahme" if p in eu["einnahmen"] else "ausgabe", "kategorie": p["kategorie"],
                       "position": p["position"], "zeile": z["zeile"], "kz": z["kz"], "amtlich": z["text"],
                       "betrag_cent": p["betrag_cent"]})
    if eu["bewirtung_nicht_abziehbar_cent"]:
        z = zeile(jahr, "bewirtung_nicht_abziehbar")
        zeilen.append({"art": "hinweis", "kategorie": "bewirtung_nicht_abziehbar", "position": "Bewirtung, nicht abziehbarer Teil (30 %)",
                       "zeile": z["zeile"], "kz": z["kz"], "amtlich": z["text"], "betrag_cent": eu["bewirtung_nicht_abziehbar_cent"]})
    nr = lambda z: int(z["zeile"]) if str(z["zeile"]).isdigit() else 999
    zeilen.sort(key=lambda z: (z["art"] != "einnahme", nr(z), z["art"] == "hinweis"))   # Reihenfolge des Formulars
    return eu | {"zeilen": zeilen, "zeilen_hinweis": zeilen_hinweis(jahr)}


def euer_pdf(f: Finanzen, jahr: int, firmendaten: dict) -> bytes:
    """EUeR des Jahres als PDF (fuer die eigenen Unterlagen / Steuerberater)."""
    from fpdf import FPDF
    ez = euer_zeilen(f, jahr)
    unicode_ok = (DEJAVU / "DejaVuSans.ttf").exists() and (DEJAVU / "DejaVuSans-Bold.ttf").exists()
    T = (lambda s: str(s or "")) if unicode_ok else _latin1
    pdf = FPDF(format="A4")
    if unicode_ok:
        pdf.add_font("DejaVu", "", str(DEJAVU / "DejaVuSans.ttf"))
        pdf.add_font("DejaVu", "B", str(DEJAVU / "DejaVuSans-Bold.ttf"))
        S = "DejaVu"
    else:
        S = "Helvetica"
    pdf.set_title(T(f"EÜR {jahr}"))
    pdf.add_page()
    pdf.set_font(S, "B", 16)
    pdf.cell(0, 9, T(f"Einnahmen-Überschuss-Rechnung {jahr}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(S, size=9)
    kopf = " · ".join(x for x in (firmendaten.get("firma"), firmendaten.get("inhaber"),
                                   f"Steuernummer {firmendaten['steuernummer']}" if firmendaten.get("steuernummer") else "") if x)
    pdf.cell(0, 5, T(kopf), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, T(f"Kleinunternehmer nach § 19 UStG · Gewinnermittlung nach § 4 Abs. 3 EStG · erstellt {_d(jetzt().date().isoformat())}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    def zeile_pdf(zl, text, betrag, fett=False, kz=""):
        pdf.set_font(S, "B" if fett else "", 10)
        pdf.cell(16, 7, T(zl), border="B")
        pdf.set_font(S, "", 8)
        pdf.cell(16, 7, T(f"Kz {kz}" if kz else ""), border="B")
        pdf.set_font(S, "B" if fett else "", 9)
        pdf.cell(118, 7, T(text), border="B")
        pdf.cell(0, 7, T(eur(betrag)), border="B", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(S, "B", 9)
    pdf.cell(16, 6, T("Zeile")); pdf.cell(16, 6, T("Kz")); pdf.cell(118, 6, T("Position (Anlage EÜR)")); pdf.cell(0, 6, T("Betrag"), align="R", new_x="LMARGIN", new_y="NEXT")
    for z in [x for x in ez["zeilen"] if x["art"] == "einnahme"]:
        zeile_pdf(z["zeile"], z["amtlich"] or z["position"], z["betrag_cent"], kz=z["kz"])
    zeile_pdf("", "Summe Betriebseinnahmen", ez["einnahmen_cent"], True)
    pdf.ln(3)
    for z in [x for x in ez["zeilen"] if x["art"] == "ausgabe"]:
        zeile_pdf(z["zeile"], z["amtlich"] or z["position"], z["betrag_cent"], kz=z["kz"])
    zeile_pdf("", "Summe Betriebsausgaben", ez["ausgaben_cent"], True)
    pdf.ln(3)
    zeile_pdf("", ("Gewinn" if ez["gewinn_cent"] >= 0 else "Verlust") + " (berechnet ELSTER)", ez["gewinn_cent"], True)
    for z in [x for x in ez["zeilen"] if x["art"] == "hinweis"]:
        pdf.ln(2)
        pdf.set_font(S, size=9)
        pdf.cell(0, 5, T(f"Zeile {z['zeile'] or '?'} (Kz {z['kz'] or '?'}): {z['position']} {eur(z['betrag_cent'])}"),
                 new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font(S, size=8)
    pdf.multi_cell(0, 4, T(ez["zeilen_hinweis"] + " Zufluss-/Abflussprinzip (Zahlungsdatum), 10-Tage-Regel berücksichtigt; "
                         "Kleinunternehmer: Bruttobeträge. Erstellt aus dem unveränderbaren Kassenbuch von LUNA-OS -- "
                         "Entwurf, die Verantwortung für die Erklärung liegt beim Steuerpflichtigen."))
    return bytes(pdf.output())


# -- Export -----------------------------------------------------------------------------------------------------------

TABELLEN = {                                                 # Dateiname -> (Beschreibung, [(Spalte, Typ)])
    "journal.csv": ("Journal: alle Zahlungen des Jahres nach Zahlungsdatum (Zufluss/Abfluss)",
                    [("Datum", "datum"), ("Zuordnungsjahr", "text"), ("Art", "text"), ("Beleg", "text"),
                     ("Gegenpartei", "text"), ("Text", "text"), ("Kategorie", "text"), ("Position_EUeR", "text"),
                     ("Zeile_EUeR", "text"), ("Betrag", "zahl"), ("Absetzbar", "zahl"), ("Storniert", "text"),
                     ("Stornogrund", "text"), ("Partner_Nr", "text")]),
    "euer.csv": ("EUeR des Jahres je Position (Zeile/Kennzahl der Anlage EUeR)",
                 [("Zeile", "text"), ("Kennzahl", "text"), ("Position", "text"), ("Art", "text"), ("Betrag", "zahl")]),
    "anlagen.csv": ("Anlageverzeichnis mit AfA", [("Beleg", "text"), ("Gegenstand", "text"), ("Lieferant", "text"),
                                                  ("Anschaffung", "datum"), ("Anschaffungskosten", "zahl"),
                                                  ("Nutzungsdauer_Jahre", "text"), ("AfA_Jahr", "zahl"),
                                                  ("AfA_kumuliert", "zahl"), ("Restwert", "zahl")]),
    "ausgangsrechnungen.csv": ("Ausgangsrechnungen und Stornorechnungen mit Rechnungsdatum im Jahr",
                               [("Nummer", "text"), ("Art", "text"), ("Bezug", "text"), ("Rechnungsdatum", "datum"),
                                ("Faellig", "datum"), ("Kunde_Nr", "text"), ("Kunde", "text"), ("Titel", "text"),
                                ("Betrag", "zahl"), ("Bezahlt", "zahl"), ("Status", "text"), ("Datei", "text"),
                                ("SHA256", "text"), ("Warenwert_Barter", "zahl"), ("Ware_erhalten", "datum")]),
    "eingangsbelege.csv": ("Eingangsbelege (Eingangsrechnungen, Gutschriften) mit Belegdatum oder Eingang im Jahr",
                           [("Nummer", "text"), ("Art", "text"), ("Eingang", "datum"), ("Belegdatum", "datum"),
                            ("Aussteller", "text"), ("Rechnungsnummer", "text"), ("Kategorie", "text"),
                            ("Betrag", "zahl"), ("Bezahlt", "zahl"), ("Status", "text"), ("Datei", "text"),
                            ("SHA256", "text"), ("Aufteilung", "text"), ("Lieferant_Nr", "text")]),
    "eigenbelege.csv": ("Eigenbelege (Zahlungen ohne eigene Rechnung) im Jahr",
                        [("Nummer", "text"), ("Art", "text"), ("Datum", "datum"), ("Kategorie", "text"), ("Text", "text"),
                         ("Gegenpartei", "text"), ("Referenz", "text"), ("Betrag", "zahl"), ("Status", "text"),
                         ("Stornogrund", "text"), ("Partner_Nr", "text")]),
    "kunden.csv": ("Stammdaten Kunden, Lieferanten und Partner", [("Nummer", "text"), ("Name", "text"), ("Typ", "text"),
                                                                   ("Strasse", "text"), ("PLZ", "text"), ("Ort", "text"),
                                                                   ("Land", "text"), ("USt_IdNr", "text"), ("Aktiv", "text"),
                                                                   ("Rollennummer", "text"), ("Weitere_Nummern", "text"),
                                                                   ("Steuernummer", "text"), ("Unsere_Kundennummer", "text"),
                                                                   ("Vertraege", "text"), ("Zahlungsweg", "text")]),
}


def _kat_name(k: str) -> str:
    return POSITIONEN.get(k) or (KATEGORIEN.get(k) or (k,))[0]


def export_zip(bh: Buchhaltung, kunden, jahr: int, firmendaten: dict) -> bytes:
    f = Finanzen(bh, kunden)
    e = bh.eintraege()
    firmen = {x["nummer"]: x for x in kunden.firmen()}
    tabellen: dict[str, list[list]] = {}
    tabellen["journal.csv"] = [
        [_d(z["datum"]), z["jahr"], "Einnahme" if z["art"] == "einnahme" else "Ausgabe", z["bezug"], z["gegenpartei"],
         z["text"], z["kategorie"], z["position"], zeile(jahr, z["kategorie"])["zeile"], _b(z["betrag_cent"]),
         _b(z["abziehbar_cent"]), "ja" if z["storniert"] else "", z.get("storno_grund", ""), z.get("firma_nr", "")]
        for z in f.journal(jahr)]
    ez = euer_zeilen(f, jahr)
    tabellen["euer.csv"] = [[z["zeile"], z["kz"], z["amtlich"] or z["position"], z["art"], _b(z["betrag_cent"])]
                            for z in ez["zeilen"]] + [
        ["", "", "Summe Betriebseinnahmen", "summe", _b(ez["einnahmen_cent"])],
        ["", "", "Summe Betriebsausgaben", "summe", _b(ez["ausgaben_cent"])],
        ["", "", "Gewinn/Verlust", "summe", _b(ez["gewinn_cent"])]]
    tabellen["anlagen.csv"] = [[a["beleg"], a["bezeichnung"], a["lieferant"], _d(a["anschaffung"]), _b(a["ak_cent"]),
                                a["nutzungsdauer_jahre"], _b(a["afa_jahr_cent"]), _b(a["afa_bis_cent"]), _b(a["restwert_cent"])]
                               for a in f.anlagen(jahr)]
    _, rechnungen = RechnungStore._falte(e)
    tabellen["ausgangsrechnungen.csv"] = [
        [r["nummer"], r.get("art", "rechnung"), r.get("bezug", ""), _d(r.get("rechnungsdatum")), _d(r.get("faellig_am")),
         r.get("firma", ""), (firmen.get(r.get("firma")) or {}).get("name", ""), r.get("titel", ""), _b(r["summe_cent"]),
         _b(r.get("bezahlt_cent", 0)), r["status"], (r.get("belege") or [{}])[0].get("pfad", ""),
         (r.get("belege") or [{}])[0].get("sha256", ""), _b(r.get("ware_cent", 0)) if r.get("ware_cent") else "",
         _d((r.get("ware_erhalten") or {}).get("datum"))]
        for r in sorted(rechnungen.values(), key=lambda r: r["nummer"]) if str(r.get("rechnungsdatum", ""))[:4] == str(jahr)]
    tabellen["eingangsbelege.csv"] = []
    for x in sorted(EingangStore._falte(e).values(), key=lambda x: x["nummer"]):
        fe = x.get("felder") or {}
        if str(fe.get("rechnungsdatum") or x["eingegangen"])[:4] != str(jahr):
            continue
        tabellen["eingangsbelege.csv"].append(
            [x["nummer"], fe.get("art", "ausgabe"), _d(x["eingegangen"]), _d(fe.get("rechnungsdatum")), fe.get("lieferant", ""),
             fe.get("rechnungsnummer", ""), _kat_name(fe.get("kategorie", "")) if fe.get("kategorie") else "",
             _b(fe.get("betrag_cent")) if fe else "", _b(x.get("bezahlt_cent", 0)), x["status"],
             (x.get("belege") or [{}])[0].get("pfad", ""), (x.get("belege") or [{}])[0].get("sha256", ""),
             " | ".join(f"{t['text']}: {_b(t['betrag_cent'])} ({'privat' if t['kategorie'] == 'privat' else _kat_name(t['kategorie'])})"
                        for t in fe.get("aufteilung") or []),
             (firmen.get(fe.get("lieferant_firma")) or {}).get("anzeige", fe.get("lieferant_firma", ""))])
    tabellen["eigenbelege.csv"] = [
        [x["nummer"], x["art"], _d(x["datum"]), _kat_name(x["kategorie"]), x["text"], x.get("gegenpartei", ""),
         x.get("referenz", ""), _b(x["betrag_cent"]), x["status"], x.get("storno_grund", ""),
         (firmen.get(x.get("firma")) or {}).get("anzeige", x.get("firma", ""))]
        for x in sorted(EigenbelegStore._falte(e).values(), key=lambda x: x["nummer"])
        if str(x.get("zuordnung_jahr") or x["datum"][:4]) == str(jahr)]
    tabellen["kunden.csv"] = [[x["nummer"], x.get("name", ""), x.get("typ", ""), x.get("strasse", ""), x.get("plz", ""),
                               x.get("ort", ""), x.get("land", ""), x.get("ustid", ""), "ja" if x.get("aktiv") else "nein",
                               x.get("anzeige", ""), " ".join(n for n in x.get("nummern", []) if n != x.get("anzeige")),
                               x.get("steuernummer", ""), x.get("kundennummer_bei", ""),
                               " | ".join(f"{v['bezeichnung']}: {v['nummer']}" for v in x.get("vertraege") or []),
                               x.get("zahlungsweg", "")]
                              for x in firmen.values()]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, zeilen in tabellen.items():
            z.writestr(name, _csv([s for s, _ in TABELLEN[name][1]], zeilen))
        z.writestr("index.xml", index_xml(jahr, firmendaten))
        dtd = Path(__file__).with_name("gdpdu-01-09-2004.dtd")
        if dtd.exists():
            z.writestr("gdpdu-01-09-2004.dtd", dtd.read_bytes())
        log = bh.log.read_bytes() if bh.log.exists() else b""
        z.writestr("kassenbuch/log.jsonl", log)
        befunde = bh.pruefe_kette() + bh.pruefe_belege()
        z.writestr("kassenbuch/pruefung.txt",
                   (f"Pruefung der Hash-Kette am {_d(jetzt().date().isoformat())}: "
                    + ("in Ordnung" if not befunde else "BEFUNDE:\n" + "\n".join(befunde))
                    + f"\nEintraege: {len(e)}\nSHA-256 von log.jsonl: {hashlib.sha256(log).hexdigest()}\n").encode("utf-8"))
        # Belegdateien: alles, worauf eine Zeile des Jahres verweist (auch wenn die Datei erst im Folgejahr einging,
        # z. B. Dezember-Rechnung im Januar erhalten) + alle Dateien, die im Jahr abgelegt wurden
        pfade = {r[11] for r in tabellen["ausgangsrechnungen.csv"] if r[11]}
        pfade |= {r[10] for r in tabellen["eingangsbelege.csv"] if r[10]}
        nummern = {r[0] for r in tabellen["eingangsbelege.csv"]}           # auch Original-Mail/Quittung (Etappe 13)
        pfade |= {b["pfad"] for x in EingangStore._falte(e).values() if x["nummer"] in nummern for b in x.get("belege") or []}
        pfade |= {n["pfad"] for r in rechnungen.values() for v in r.get("ware_vorgaenge") or []
                  if str(v.get("datum", ""))[:4] == str(jahr) for n in v.get("nachweise") or []}
        pfade |= {b["daten"]["pfad"] for b in bh.eintraege("beleg") if str(b["daten"].get("jahr")) == str(jahr)}
        anzahl = 0
        for pf in sorted(pfade):
            if (bh.dir / pf).exists():
                z.writestr(pf, (bh.dir / pf).read_bytes())
                anzahl += 1
        z.writestr(f"EUER_{jahr}.pdf", euer_pdf(f, jahr, firmendaten))
        z.writestr("LIESMICH.txt", liesmich(jahr, firmendaten, tabellen, anzahl, not befunde).encode("utf-8"))
    return buf.getvalue()


def liesmich(jahr: int, fd: dict, tabellen: dict, belege: int, kette_ok: bool) -> str:
    zeilen = "\n".join(f"- {n}: {TABELLEN[n][0]} ({len(t)} Zeilen)" for n, t in tabellen.items())
    return f"""Buchhaltungs-Export {jahr} -- {fd.get('firma', '')} ({fd.get('inhaber', '')})
Steuernummer: {fd.get('steuernummer', '')}
Erstellt: {_d(jetzt().date().isoformat())} aus LUNA-OS (Eigenbau), Kleinunternehmer nach § 19 UStG, EUeR nach § 4 Abs. 3 EStG.

Inhalt
{zeilen}
- index.xml (+ gdpdu-01-09-2004.dtd): Beschreibung der Tabellen nach dem Beschreibungsstandard fuer die Datenueberlassung
- kassenbuch/log.jsonl: vollstaendiges, unveraenderbares Kassenbuch (Hash-Kette, jeder Eintrag enthaelt den Hash
  des vorigen); kassenbuch/pruefung.txt: Ergebnis der Pruefung ({'in Ordnung' if kette_ok else 'BEFUNDE -- siehe Datei'})
- belege/<Eingangsjahr>/: {belege} Belegdateien im Original (Name beginnt mit den ersten 16 Zeichen des SHA-256);
  Spalte „Datei“ der Tabellen verweist darauf
- EUER_{jahr}.pdf: Einnahmen-Ueberschuss-Rechnung mit Zeilen der Anlage EUeR

Tabellen: UTF-8, Semikolon, Datum TT.MM.JJJJ, Betraege in Euro mit Komma (1234,56), Kleinunternehmer = Bruttobetraege.
Verfahrensdokumentation: docs/verfahrensdokumentation-buchhaltung.md im Projekt.
"""


def index_xml(jahr: int, fd: dict) -> str:
    """Beschreibung der CSV-Tabellen nach dem Beschreibungsstandard (GDPdU-DTD 01-09-2004)."""
    from xml.sax.saxutils import escape as x
    typ = {"text": "<AlphaNumeric/>", "datum": "<Date><Format>DD.MM.YYYY</Format></Date>",
           "zahl": "<Numeric><Accuracy>2</Accuracy></Numeric>"}
    tabs = []
    for name, (beschreibung, spalten) in TABELLEN.items():
        cols = "\n".join(f"        <VariableColumn><Name>{x(s)}</Name>{typ[t]}</VariableColumn>" for s, t in spalten)
        tabs.append(f"""    <Table>
      <URL>{x(name)}</URL>
      <Name>{x(name[:-4])}</Name>
      <Description>{x(beschreibung)}</Description>
      <Validity><Range><From>01.01.{jahr}</From><To>31.12.{jahr}</To></Range></Validity>
      <UTF8/>
      <DecimalSymbol>,</DecimalSymbol>
      <DigitGroupingSymbol>.</DigitGroupingSymbol>
      <VariableLength>
        <ColumnDelimiter>;</ColumnDelimiter>
        <RecordDelimiter>&#13;&#10;</RecordDelimiter>
        <TextEncapsulator>"</TextEncapsulator>
{cols}
      </VariableLength>
    </Table>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE DataSet SYSTEM "gdpdu-01-09-2004.dtd">
<DataSet>
  <Version>1.0</Version>
  <DataSupplier>
    <Name>{x(fd.get('firma', ''))}</Name>
    <Location>{x(' '.join(str(fd.get(k, '')) for k in ('strasse', 'plz', 'ort')).strip())}</Location>
    <Comment>Buchhaltung {jahr} aus LUNA-OS; Kleinunternehmer (§ 19 UStG), EUeR</Comment>
  </DataSupplier>
  <Media>
    <Name>Export {jahr}</Name>
{chr(10).join(tabs)}
  </Media>
</DataSet>
"""


def jahre_mit_daten(bh: Buchhaltung) -> list[int]:
    return sorted({int(x["ts"][:4]) for x in bh.eintraege()} | {jetzt().year}, reverse=True)

