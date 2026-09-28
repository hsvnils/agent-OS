"""KUNDEN_FINANZEN Etappe 6: Eingangsrechnungen -- Auslesen (E-Rechnung, PDF-Text), Vorschlag, Aufnahme (atomar,
doppelt erkannt), Buchen, Zahlung, Verwerfen."""
import io
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.buchhaltung import Buchhaltung, jetzt
from orchestrator.core.eingangsbelege import (EingangStore, auslesen, e_rechnung_lesen, kategorie_raten,
                                              vorschlag_llm, vorschlag_regeln)

UBL = b"""<?xml version="1.0" encoding="UTF-8"?>
<ubl:Invoice xmlns:ubl="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
  xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
  xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>R-2026-4711</cbc:ID><cbc:IssueDate>2026-09-15</cbc:IssueDate><cbc:DueDate>2026-09-29</cbc:DueDate>
  <cac:AccountingSupplierParty><cac:Party><cac:PartyName><cbc:Name>Kamera Profi GmbH</cbc:Name></cac:PartyName>
    <cac:PartyLegalEntity><cbc:RegistrationName>Kamera Profi GmbH</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party></cac:AccountingSupplierParty>
  <cac:LegalMonetaryTotal><cbc:PayableAmount currencyID="EUR">349.90</cbc:PayableAmount></cac:LegalMonetaryTotal>
  <cac:InvoiceLine><cac:Item><cbc:Name>Funkmikrofon</cbc:Name></cac:Item></cac:InvoiceLine>
</ubl:Invoice>"""
CII = b"""<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
  xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
  xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocument><ram:ID>INV-88</ram:ID><ram:IssueDateTime><udt:DateTimeString format="102">20260910</udt:DateTimeString></ram:IssueDateTime></rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:IncludedSupplyChainTradeLineItem><ram:SpecifiedTradeProduct><ram:Name>Adobe Creative Cloud</ram:Name></ram:SpecifiedTradeProduct></ram:IncludedSupplyChainTradeLineItem>
    <ram:ApplicableHeaderTradeAgreement><ram:SellerTradeParty><ram:Name>Adobe Ireland Ltd</ram:Name></ram:SellerTradeParty></ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeSettlement><ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation><ram:GrandTotalAmount>71.39</ram:GrandTotalAmount><ram:DuePayableAmount>71.39</ram:DuePayableAmount></ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""
TEXT = """Druckerei Nord GmbH
Hafenstrasse 3, 20095 Hamburg
Rechnungsnummer: DN-2026-0815
Rechnungsdatum: 12.09.2026
Pos 1  500 T-Shirts Druck         1.190,00 EUR
Gesamtbetrag                      1.190,00 EUR
Zahlbar bis 26.09.2026"""


def _pdf(text: str, anhang: bytes | None = None) -> bytes:
    from fpdf import FPDF
    p = FPDF(); p.add_page(); p.set_font("Helvetica", size=11)
    for z in text.splitlines():
        p.cell(0, 6, z, new_x="LMARGIN", new_y="NEXT")
    roh = bytes(p.output())
    if anhang is None:
        return roh
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(roh)))
    w.add_attachment("factur-x.xml", anhang)
    out = io.BytesIO(); w.write(out)
    return out.getvalue()


def _store():
    return EingangStore(Buchhaltung(Path(tempfile.mkdtemp()) / "buchhaltung"))


class TestAuslesen(unittest.TestCase):
    def test_1_xrechnung_ubl_und_cii(self):
        u = e_rechnung_lesen(UBL)
        self.assertEqual((u["lieferant"], u["rechnungsnummer"], u["rechnungsdatum"], u["betrag"], u["faellig_am"]),
                         ("Kamera Profi GmbH", "R-2026-4711", "2026-09-15", "349,90", "2026-09-29"))
        c = e_rechnung_lesen(CII)
        self.assertEqual((c["lieferant"], c["rechnungsnummer"], c["rechnungsdatum"], c["betrag"], c["leistung"]),
                         ("Adobe Ireland Ltd", "INV-88", "2026-09-10", "71,39", "Adobe Creative Cloud"))
        self.assertIsNone(e_rechnung_lesen(b"<html>kein</html>"))
        self.assertIsNone(e_rechnung_lesen(b"nicht mal xml"))

    def test_2_xml_bombe_wird_abgewiesen(self):
        bombe = b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;">]><Invoice>&b;</Invoice>'
        self.assertIsNone(e_rechnung_lesen(bombe))

    def test_3_pdf_text_und_zugferd_anhang(self):
        a = auslesen(_pdf(TEXT), "rechnung.pdf")
        self.assertEqual(a["text_quelle"], "pdf-text")
        self.assertIn("DN-2026-0815", a["text"])
        z = auslesen(_pdf(TEXT, anhang=CII), "zugferd.pdf")
        self.assertEqual(z["e_rechnung"]["rechnungsnummer"], "INV-88")
        self.assertEqual(auslesen(UBL, "x.xml")["e_rechnung"]["betrag"], "349,90")

    def test_4_regel_vorschlag(self):
        v = vorschlag_regeln(TEXT)
        self.assertEqual((v["lieferant"], v["rechnungsnummer"], v["rechnungsdatum"], v["betrag"], v["kategorie"]),
                         ("Druckerei Nord GmbH", "DN-2026-0815", "2026-09-12", "1.190,00", "wareneinkauf"))
        e = vorschlag_regeln(TEXT, e_rechnung_lesen(UBL))
        self.assertEqual((e["lieferant"], e["betrag"], e["quelle"]), ("Kamera Profi GmbH", "349,90", "e-rechnung"))
        self.assertEqual(kategorie_raten("Adobe Creative Cloud Abo"), "software")
        self.assertEqual(kategorie_raten("irgendwas"), "sonstiges")

    def test_4b_regel_vorschlag_shop_rechnung(self):
        """Echter Aufbau (Calumet): Absenderzeile mit ·, Belegnummer, Auftragsdatum VOR Belegdatum, Zusteller DHL."""
        t = ("Photo Video Shop GmbH · Friesenweg 12 · 22763 Hamburg\nPhoto Video Shop GmbH\nRechnung\n"
             "Auftragsdatum: 21.09.2026\nBelegdatum: 22.09.2026\nBelegnummer: RG143556\nZusteller: DHL\nVersandart: DE\n"
             "1 SmallRig Cage Kit 4336 für Sony Alpha 6700 1 Stk. 19,0 % 51,92 € 51,92 €\n"
             "Gesamtbetrag (netto) 43,63 €\nGesamtbetrag (brutto) 51,92 €\n")
        v = vorschlag_regeln(t)
        self.assertEqual((v["lieferant"], v["rechnungsnummer"], v["rechnungsdatum"], v["betrag"], v["kategorie"]),
                         ("Photo Video Shop GmbH", "RG143556", "2026-09-22", "51,92", "gwg"))

    def test_5_llm_antwort_tolerant(self):
        v = vorschlag_llm('Hier: {"lieferant": "Druckerei Nord", "rechnungsnummer": "DN-1", "rechnungsdatum": "2026-09-12", '
                          '"betrag": "1190", "faellig_am": "gestern", "leistung": "T-Shirts", "kategorie": "wareneinkauf"} fertig')
        self.assertEqual((v["betrag"], v["faellig_am"], v["kategorie"]), ("1.190,00", "", "wareneinkauf"))
        self.assertIsNone(vorschlag_llm("kein json"))
        self.assertEqual(vorschlag_llm('{"kategorie": "erfunden", "betrag": "abc"}')["kategorie"], "")


class TestEingangStore(unittest.TestCase):
    def test_1_aufnehmen_atomar_und_doppelt(self):
        st = _store()
        r = st.aufnehmen(_pdf(TEXT), "Druckerei.pdf", von="LUNA-OS:ceo")
        self.assertEqual(r["nummer"], f"ER-{jetzt().year}-0001")
        self.assertEqual(r["vorschlag"]["rechnungsnummer"], "DN-2026-0815")
        x = st.get(r["nummer"])
        self.assertEqual((x["status"], x["belege"][0]["sha256"] and True), ("zu_pruefen", True))
        self.assertTrue((st.bh.dir / x["belege"][0]["pfad"]).read_bytes().startswith(b"%PDF"))
        self.assertEqual(st.aufnehmen(_pdf(TEXT), "nochmal.pdf"), {"nummer": r["nummer"], "doppelt": True})
        self.assertEqual(len(st.bh.eintraege("beleg")), 1)                             # nicht doppelt abgelegt
        for falsch, name in ((b"", "leer.pdf"), (b"x", "virus.exe")):
            with self.assertRaises(ValueError):
                st.aufnehmen(falsch, name)
        self.assertEqual(len([e for e in st.bh.eintraege("nummer") if e["daten"]["kreis"] == "ER"]), 1)
        self.assertEqual((st.bh.pruefe_kette(), st.bh.pruefe_belege()), ([], []))

    def test_2_buchen_mit_korrektur_und_doppelter_rechnungsnummer(self):
        st = _store()
        a = st.aufnehmen(_pdf(TEXT), "a.pdf")["nummer"]
        b = st.aufnehmen(UBL, "b.xml")["nummer"]
        felder = {"lieferant": "Druckerei Nord GmbH", "rechnungsnummer": "DN-2026-0815", "rechnungsdatum": "2026-09-12",
                  "betrag": "1.190,00", "kategorie": "wareneinkauf"}
        for kaputt in ({"lieferant": ""}, {"betrag": "abc"}, {"kategorie": "quatsch"}, {"rechnungsdatum": "12.09.2026"}):
            with self.assertRaises(ValueError, msg=kaputt):
                st.buchen(a, felder | kaputt)
        st.buchen(a, felder)
        self.assertEqual((st.get(a)["status"], st.get(a)["felder"]["betrag_cent"]), ("gebucht", 119000))
        st.buchen(a, felder | {"betrag": "1.180,00", "notiz": "Skonto"})               # Korrektur = neuer Eintrag
        self.assertEqual(st.get(a)["felder"]["betrag_cent"], 118000)
        self.assertEqual(len(st.bh.eintraege("eingang_gebucht")), 2)
        with self.assertRaises(ValueError):
            st.buchen(b, felder)                                                        # gleiche Rechnung doppelt
        st.buchen(b, felder | {"trotz_doppelt": True})
        self.assertEqual(st.liste()[0]["status"], "gebucht")

    def test_3_bezahlt_und_verworfen(self):
        st = _store()
        a = st.aufnehmen(_pdf(TEXT), "a.pdf")["nummer"]
        with self.assertRaises(ValueError):
            st.bezahlt(a, jetzt().date().isoformat())                                   # erst buchen
        st.buchen(a, {"lieferant": "X", "rechnungsdatum": "2026-09-12", "betrag": "10", "kategorie": "buero"})
        self.assertEqual(st.bezahlt(a, "")["bezahlt_am"], jetzt().date().isoformat())
        b = st.aufnehmen(UBL, "b.xml")["nummer"]
        with self.assertRaises(ValueError):
            st.verwerfen(b, "")
        st.verwerfen(b, "versehentlich hochgeladen")
        self.assertEqual(st.get(b)["status"], "verworfen")
        with self.assertRaises(ValueError):
            st.verwerfen(a, "gebucht")                                                  # gebuchte nicht
        self.assertTrue((st.bh.dir / st.get(b)["belege"][0]["pfad"]).exists())         # Datei bleibt

    def test_4_llm_vorschlag_ergaenzt(self):
        st = _store()
        a = st.aufnehmen(_pdf(TEXT), "a.pdf")["nummer"]
        st.vorschlag_ergaenzen(a, {"lieferant": "Druckerei Nord GmbH (KI)", "betrag": "", "quelle": "backoffice"})
        v = st.get(a)["vorschlag"]
        self.assertEqual((v["lieferant"], v["betrag"], v["quelle"]), ("Druckerei Nord GmbH (KI)", "1.190,00", "backoffice"))


if __name__ == "__main__":
    unittest.main()


class _Google:
    """Minimaler Google-Ersatz fuer den Mail-Eingang."""
    def __init__(self, mails):
        self.mails, self.abrufe = mails, 0
    def verfuegbar(self): return True
    def mail_suchen(self, q, max_results=10):
        self.q = q
        return {"ok": True, "mails": [{"id": mid, "von": von} for mid, (von, _) in self.mails.items()]}
    def mail_roh(self, mid):
        self.abrufe += 1
        from email.message import EmailMessage
        von, anh = self.mails[mid]
        m = EmailMessage(); m["From"] = von; m["Subject"] = "Fwd: Rechnung"; m.set_content("siehe Anhang")
        for name, daten in anh:
            m.add_attachment(daten, maintype="application", subtype="octet-stream", filename=name)
        return {"ok": True, "roh": m.as_bytes()}


class TestAnbindungen(unittest.TestCase):
    def test_1_mail_eingang_nur_eigene_absender(self):
        from orchestrator.core.auftraege import AuftragStore
        from orchestrator.core.eingangsbelege import mail_eingang_pruefen
        st = _store()
        bo = AuftragStore(Path(tempfile.mkdtemp()) / "b.jsonl")
        g = _Google({"m1": ("Nils <hsvnils@icloud.com>", [("Rechnung.pdf", _pdf(TEXT)), ("logo.gif", b"GIF89a")]),
                     "m2": ("Betrueger <evil@example.com>", [("Rechnung.pdf", _pdf("Fremd " * 20))])})
        meldungen = []
        neu = mail_eingang_pruefen(st, g, absender=["hsvnils@icloud.com"], backoffice=bo,
                                   notify=lambda t, **k: meldungen.append(t))
        self.assertEqual(neu, [f"ER-{jetzt().year}-0001"])                              # nur m1, nur PDF
        self.assertIn("from:(hsvnils@icloud.com)", g.q)
        x = st.get(neu[0])
        self.assertEqual((x["quelle"], x["mail_id"]), ("mail", "m1"))
        self.assertEqual(bo.get(x["llm_auftrag"])["zweck"], f"beleg:{neu[0]}")           # KI-Vorschlag angefordert
        self.assertEqual(len(meldungen), 1)
        self.assertEqual(mail_eingang_pruefen(st, g, absender=["hsvnils@icloud.com"]), [])   # idempotent
        self.assertEqual(g.abrufe, 1)                                                    # m1 einmal, m2 (fremd) nie geladen

    def test_1b_apple_mail_weiterleitung_inline_verschachtelt(self):
        """BF-36: Apple Mail leitet die PDF als inline-Teil in multipart/alternative > multipart/mixed weiter;
        Logos aus dem HTML (Content-ID/klein) sind keine Belege."""
        from email.mime.application import MIMEApplication
        from email.mime.image import MIMEImage
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from orchestrator.core.eingangsbelege import anhaenge
        pdf = _pdf(TEXT)
        aussen, innen = MIMEMultipart("alternative"), MIMEMultipart("mixed")
        innen.attach(MIMEText("<p>Weitergeleitet</p>", "html"))
        logo = MIMEImage(b"\xff\xd8\xff" + b"0" * 5000, "jpeg")
        logo.add_header("Content-Disposition", "inline", filename="logo.jpg"); logo.add_header("Content-ID", "<l1>")
        innen.attach(logo)
        teil = MIMEApplication(pdf, "pdf")
        teil.add_header("Content-Disposition", "inline", filename="Calumet - Rechnung RG1.pdf")
        innen.attach(teil)
        aussen.attach(innen)
        self.assertEqual(anhaenge(aussen.as_bytes()), [("Calumet - Rechnung RG1.pdf", pdf)])

    def test_2_backoffice_ergebnis_wird_uebernommen(self):
        from orchestrator.core.auftraege import AuftragStore
        from orchestrator.core.eingangsbelege import llm_beauftragen, llm_ergebnisse_uebernehmen
        st = _store()
        bo = AuftragStore(Path(tempfile.mkdtemp()) / "b.jsonl")
        nr = st.aufnehmen(_pdf(TEXT), "a.pdf")["nummer"]
        aid = llm_beauftragen(st, bo, nr)
        self.assertEqual(llm_ergebnisse_uebernehmen(st, bo), 0)                          # noch nicht fertig
        bo.naechster()
        bo.fertig(aid, ergebnis='{"lieferant": "Druckerei Nord GmbH", "betrag": "1.190,00", "kategorie": "wareneinkauf",'
                                ' "rechnungsdatum": "2026-09-12", "rechnungsnummer": "DN-2026-0815", "faellig_am": "2026-09-26",'
                                ' "leistung": "500 T-Shirts"}')
        self.assertEqual(llm_ergebnisse_uebernehmen(st, bo), 1)
        v = st.get(nr)["vorschlag"]
        self.assertEqual((v["quelle"], v["faellig_am"], v["leistung"]), ("backoffice", "2026-09-26", "500 T-Shirts"))
        self.assertEqual(llm_ergebnisse_uebernehmen(st, bo), 0)                          # nur einmal


class TestBelegApi(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from orchestrator.channels.web import app as webapp
        from orchestrator.core.auftraege import AuftragStore
        from orchestrator.tests.test_angebote import _stores
        self.w = webapp
        self.orig = (webapp.kunden_store, webapp.backoffice)
        bh, ks, *_ = _stores()
        webapp.kunden_store, webapp.backoffice = ks, AuftragStore(bh.dir.parent / "b.jsonl")
        self.c = TestClient(webapp.app)

    def tearDown(self):
        self.w.kunden_store, self.w.backoffice = self.orig

    def test_1_hochladen_buchen_lieferant(self):
        import base64
        r = self.c.post("/api/finanzen/belege/hochladen", json={"dateien": [
            {"name": "Druckerei.pdf", "daten": base64.b64encode(_pdf(TEXT)).decode()},
            {"name": "boese.exe", "daten": base64.b64encode(b"MZ").decode()},
            {"name": "kaputt.pdf", "daten": "!!!kein base64"}]}).json()
        self.assertEqual([e["ok"] for e in r["ergebnisse"]], [True, False, False])
        nr = r["ergebnisse"][0]["nummer"]
        d = self.c.get(f"/api/finanzen/belege/{nr}").json()
        self.assertEqual((d["beleg"]["vorschlag"]["rechnungsnummer"], d["ki_status"]), ("DN-2026-0815", "neu"))
        datei = self.c.get(f"/api/finanzen/belege/{nr}/datei")
        self.assertEqual((datei.status_code, datei.headers["content-type"]), (200, "application/pdf"))
        self.assertNotIn("content-security-policy", datei.headers)                      # PDF muss im Rahmen anzeigbar sein
        b = self.c.post(f"/api/finanzen/belege/{nr}/buchen", json={"lieferant_anlegen": True, "felder": {
            "lieferant": "Druckerei Nord GmbH", "rechnungsnummer": "DN-2026-0815", "rechnungsdatum": "2026-09-12",
            "betrag": "1.190,00", "kategorie": "wareneinkauf"}}).json()
        self.assertTrue(b["ok"], b)
        k = b["felder"]["lieferant_firma"]
        self.assertEqual(self.w.kunden_store.firma(k)["typ"], "lieferant")               # im Kundenstamm als Lieferant
        self.assertTrue(self.c.post(f"/api/finanzen/belege/{nr}/bezahlt", json={}).json()["ok"])
        self.assertEqual(self.c.get("/api/finanzen/belege").json()["belege"][0]["status"], "gebucht")

    def test_2_rechte(self):
        from orchestrator.core.team_auth import erlaubte_apps, modul_fuer_pfad
        self.assertEqual(modul_fuer_pfad("POST", "/api/finanzen/belege/hochladen"), "finanzen")
        self.assertNotIn("belege", erlaubte_apps({"role": "team", "allowed_modules": ["crm"]}))
