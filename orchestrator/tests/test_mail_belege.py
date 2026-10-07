"""KUNDEN_FINANZEN Etappe 13 (CEO 2026-09-29): Abo-Rechnungen ohne PDF (Rechnung im Mailtext), Quittung neben der
Rechnung als Zahlungsnachweis, automatische Weiterleitungen mit Original-Absender. Nachbauten echter Mails (anonymisiert).
"""
import unittest
from email.message import EmailMessage

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.eingangsbelege import (BELEG_ABSENDER_STANDARD, MAIL_ABGELEGT, auto_weitergeleitet, mail_eingang_pruefen, vorschlag_regeln)
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_eingangsbelege import TEXT, _pdf, _store

ABS = ["hsvnils@icloud.com", "hanserautisch@gmail.com", "moin@hanserautisch.de"]
MOIN = '"Nils" <moin@hanserautisch.de>'

APPLE = """<html><body><div>Herzliche Grüße<br>Nils</div>
<div>Anfang der weitergeleiteten Nachricht:</div>
<blockquote><div><b>Von:</b> Apple &lt;no_reply@email.apple.com&gt;</div>
<div><b>Betreff:</b> Deine Rechnung von Apple</div>
<div><b>Datum:</b> 19. September 2026 um 08:03:12 MESZ</div>
<div><b>An:</b> hsvnils@icloud.com</div>
<table><tr><td>Beleg und Verlängerungsmitteilung</td></tr><tr><td>18. September 2026</td></tr>
<tr><td>Bestellnummer:</td><td>MNMTS2HNJV</td></tr>
<tr><td>AppleCare+ Versicherungsschutz</td></tr><tr><td>Nächstes Rechnungsdatum: 19. Oktober 2026</td></tr>
<tr><td>4,49 €</td></tr><tr><td>Der Preis beinhaltet 19% Versicherungssteuer</td></tr></table>
<a href="https://support.apple.com/billing?x=1">Support</a></blockquote></body></html>"""

PAYPAL = """Anfang der weitergeleiteten Nachricht:
Von: PayPal <service@paypal.de>
Betreff: Beleg für Ihre Zahlung an DAZN DACH GmbH
Datum: 30. August 2026 um 10:00:00 MESZ
An: Nils <hsvnils@icloud.com>

Hallo Nils!
Sie haben 44,99 € EUR an DAZN DACH GmbH gezahlt
Händler DAZN DACH GmbH
Transaktionsdatum 30.08.2026
Transaktionscode: 2HW13614NU6157424
Gesamtbetrag 44,99 € EUR"""


def _mail(von, betreff, *, html="", text="", anhaenge=(), auth="echt", koepfe=None):
    m = EmailMessage()
    dom = von.split("@")[-1].rstrip(">")
    if auth == "echt":                          # so setzt mx.google.com den Kopf beim Empfang
        m["Authentication-Results"] = f"mx.google.com; dkim=pass header.i=@{dom}; spf=pass; dmarc=pass header.from={dom}"
    elif isinstance(auth, str) and auth.startswith("mx.google.com"):
        m["Authentication-Results"] = auth
    else:
        m["Authentication-Results"] = f"mx.google.com; dkim=fail header.i=@{dom}; dmarc=fail header.from={dom}"
    m["From"], m["Subject"] = von, betreff
    for k, w in (koepfe or {}).items():
        m[k] = w
    if html:
        m.set_content("siehe HTML")
        m.add_alternative(html, subtype="html")
    else:
        m.set_content(text or "x")
    for name, daten in anhaenge:
        m.add_attachment(daten, maintype="application", subtype="pdf", filename=name)
    return m.as_bytes()


class _G:
    def __init__(self, mails):
        self.mails, self.abgelegt, self.abrufe = mails, [], []
    def verfuegbar(self): return True
    def mail_suchen(self, q, max_results=10):
        import email
        from email import policy
        self.q = q
        return {"ok": True, "mails": [{"id": k, "von": str(email.message_from_bytes(r, policy=policy.default)["From"]),
                                       "betreff": str(email.message_from_bytes(r, policy=policy.default)["Subject"])}
                                      for k, r in self.mails.items()]}
    def mail_roh(self, mid):
        self.abrufe.append(mid)
        return {"ok": True, "roh": self.mails[mid]}
    def mail_ablegen(self, mid, ordner):
        self.abgelegt.append((mid, ordner))
        return {"ok": True}


def _alle(st):
    return {x["nummer"]: x for x in st._falte(st.bh.eintraege()).values()}


class TestMailOhnePdf(unittest.TestCase):
    def test_1_apple_rechnung_im_mailtext(self):
        st = _store()
        roh = _mail(MOIN, "Fwd: Deine Rechnung von Apple", html=APPLE)
        g = _G({"a1": roh})
        neu = mail_eingang_pruefen(st, g, absender=ABS)
        self.assertEqual(len(neu), 1)
        b = st.get(neu[0])
        v = b["vorschlag"]
        self.assertEqual((v["lieferant"], v["rechnungsnummer"], v["rechnungsdatum"], v["betrag"]),
                         ("Apple", "MNMTS2HNJV", "2026-09-18", "4,49"))            # nicht „Nächstes Rechnungsdatum“
        self.assertIn("Versicherung", " ".join(v["hinweise"]))
        self.assertEqual((b["quelle"], b["text_quelle"], b["mail_id"], b["mime"]), ("mail", "mail", "a1", "application/pdf"))
        self.assertEqual(len(b["belege"]), 2)                                       # PDF-Ansicht + Original
        self.assertEqual((st.bh.dir / b["belege"][1]["pfad"]).read_bytes(), roh)    # .eml unveraendert
        self.assertNotIn("support.apple.com", b["text"])                           # Links raus
        self.assertEqual(g.abgelegt, [("a1", "LUNA/Rechnungen/2026")])
        self.assertIn("to:(", g.q)
        self.assertNotIn("has:attachment", g.q)

    def test_2_paypal_haendler_und_hinweise(self):
        st = _store()
        neu = mail_eingang_pruefen(st, _G({"p1": _mail(MOIN, "WG: Beleg für Ihre Zahlung an DAZN DACH GmbH", text=PAYPAL)}),
                                   absender=ABS)
        v = st.get(neu[0])["vorschlag"]
        self.assertEqual((v["lieferant"], v["rechnungsnummer"], v["rechnungsdatum"], v["betrag"]),
                         ("DAZN DACH GmbH", "2HW13614NU6157424", "2026-08-30", "44,99"))
        h = " ".join(v["hinweise"])
        self.assertIn("Streaming", h)
        self.assertIn("PayPal-Zahlungsbeleg", h)

    def test_3_keine_rechnung_bleibt_liegen(self):
        """Antwort an LUNA (nicht weitergeleitet) und Weiterleitung ohne Betrag sind keine Belege -> Posteingang."""
        st = _store()
        g = _G({"r1": _mail('"Nils" <hsvnils@icloud.com>', "Re: Angebot AN-2026-0002",
                            text="Passt, bitte Rechnung über 500,00 € schicken."),
                "n1": _mail(MOIN, "Fwd: Neuigkeiten", text="Anfang der weitergeleiteten Nachricht:\nVon: Shop <a@shop.de>\n\n"
                                                           "Unsere neuen Produkte und Ihre Rechnung-Einstellungen")})
        self.assertEqual(mail_eingang_pruefen(st, g, absender=ABS), [])
        self.assertEqual(g.abgelegt, [])
        self.assertEqual(_alle(st), {})

    def test_4_dublette_ueber_rechnungsnummer(self):
        """Apple-Developer-Beleg war schon hochgeladen -> dieselbe Rechnung per Mail wird nicht zum zweiten Beleg."""
        st = _store()
        nr = st.aufnehmen(_pdf(TEXT), "apple.pdf")["nummer"]
        st.buchen(nr, {"lieferant": "Apple", "rechnungsnummer": "W1544208136", "rechnungsdatum": "2026-05-23",
                       "betrag": "99,00", "kategorie": "software"})
        g = _G({"d1": _mail(MOIN, "Fwd: Auftragsbestätigung W1544208136",
                            text="Anfang der weitergeleiteten Nachricht:\nVon: Apple Store <order@orders.apple.com>\n"
                                 "Datum: 23. Mai 2026\n\nBestellnummer: W1544208136\nBestellsumme 99,00 €")})
        self.assertEqual(mail_eingang_pruefen(st, g, absender=ABS), [])
        self.assertEqual(g.abgelegt, [("d1", f"LUNA/Doppelt/{jetzt().year}")])
        self.assertEqual(len(_alle(st)), 1)

    def test_5_rechnung_und_quittung_ein_beleg(self):
        st = _store()
        inv = _pdf("Anthropic, PBC\nInvoice number PXE7RQGJ-0008\nTotal 107,10 EUR")
        rec = _pdf("Anthropic, PBC\nReceipt number 2188\nDate paid September 25, 2026\nAmount paid 107,10 EUR")
        g = _G({"s1": _mail(MOIN, "Fwd: Your receipt from Anthropic", text="siehe Anhang",
                            anhaenge=[("Invoice-PXE7RQGJ-0008.pdf", inv), ("Receipt-2188.pdf", rec)])})
        neu = mail_eingang_pruefen(st, g, absender=ABS)
        self.assertEqual(len(neu), 1)
        b = st.get(neu[0])
        self.assertEqual(b["dateiname"], "Invoice-PXE7RQGJ-0008.pdf")
        self.assertEqual([x.get("rolle") for x in b["belege"]], [None, "zahlungsnachweis"])
        self.assertEqual((st.bh.dir / b["belege"][1]["pfad"]).read_bytes(), rec)

    def test_6_als_nachweis_nachtraeglich(self):
        """Live-Fall ER-0033/0034: Quittung wurde eigener Beleg -> an die Rechnung haengen, sich selbst verwerfen."""
        st = _store()
        a = st.aufnehmen(_pdf("Invoice " + "a" * 40), "Invoice.pdf")["nummer"]
        b = st.aufnehmen(_pdf("Receipt " + "b" * 40), "Receipt.pdf")["nummer"]
        with self.assertRaises(ValueError):
            st.als_nachweis(a, a)
        st.als_nachweis(b, a)
        self.assertEqual(st.get(b)["status"], "verworfen")
        self.assertIn(f"Zahlungsnachweis zu {a}", st.get(b)["grund"])
        self.assertEqual([x.get("name") for x in st.get(a)["belege"]][1:], ["Receipt.pdf"])
        with self.assertRaises(ValueError):
            st.als_nachweis(b, a)                                                    # schon verworfen


class TestAutoWeiterleitung(unittest.TestCase):
    APPLE_DIREKT = dict(html=APPLE.replace("Anfang der weitergeleiteten Nachricht:", ""))

    def test_1_original_absender_ueber_eigenes_postfach(self):
        st = _store()
        echt = _mail("Apple <no_reply@email.apple.com>", "Deine Rechnung von Apple", koepfe={"To": "hsvnils@icloud.com"},
                     **self.APPLE_DIREKT)
        gmail = _mail("PayPal <service@paypal.de>", "Beleg für Ihre Zahlung an DAZN DACH GmbH", text=PAYPAL,
                      auth="mx.google.com; dkim=pass header.i=@paypal.de; spf=pass smtp.mailfrom="
                           "hanserautisch+caf_=luna=gmail.com@gmail.com; dmarc=pass header.from=paypal.de")
        fremd = _mail("Shop <rechnung@shop.example>", "Ihre Rechnung", text="Rechnung 10,00 €",
                      koepfe={"To": "jemand@example.com"})
        falsch = _mail("Apple <no_reply@email.apple.com>", "Deine Rechnung von Apple", auth="fail",
                       koepfe={"To": "hsvnils@icloud.com"}, **self.APPLE_DIREKT)
        werbung = _mail("Shop <news@shop.example>", "Neue Angebote", text="Nur heute 10,00 €",
                        koepfe={"To": "hsvnils@icloud.com"})
        self.assertTrue(auto_weitergeleitet(echt, ABS))
        self.assertTrue(auto_weitergeleitet(gmail, ABS))
        self.assertFalse(auto_weitergeleitet(fremd, ABS))                            # nicht an eigene Adresse
        self.assertFalse(auto_weitergeleitet(falsch, ABS))                           # DKIM/DMARC fehlgeschlagen
        # 2026-10-07: All-Inkl-Rechnungen gehen an rechnung@hanserautisch.de und werden an LUNA weitergeleitet
        allinkl = _mail("ALL-INKL.COM <buchhaltung@all-inkl.com>", "Rechnung 2261262856", text="Summe brutto 23,13 €",
                        auth="mx.google.com; dkim=pass header.i=@all-inkl.com; dmarc=pass header.from=all-inkl.com",
                        koepfe={"To": "rechnung@hanserautisch.de"})
        std = [a for a in BELEG_ABSENDER_STANDARD.split(",") if a]
        self.assertTrue(auto_weitergeleitet(allinkl, std))
        self.assertFalse(auto_weitergeleitet(allinkl, ABS))                          # Gegenprobe: alte Liste ohne rechnung@
        self.assertFalse(any(a.startswith("luna") for a in std))                    # LUNAs eigene Postfaecher nie als Absender
        self.assertIn("hsvnils@icloud.com", std)                                     # Bestehende bleiben
        g = _G({"e1": echt, "g1": gmail, "f1": fremd, "x1": falsch, "w1": werbung})
        neu = mail_eingang_pruefen(st, g, absender=ABS)
        self.assertEqual(len(neu), 2)
        self.assertEqual(sorted(st.get(n)["vorschlag"]["lieferant"] for n in neu), ["Apple", "DAZN DACH GmbH"])
        self.assertNotIn("w1", g.abrufe)                                             # ohne Rechnungswort nie geladen
        self.assertEqual(sorted(m for m, _ in g.abgelegt), ["e1", "g1"])
        self.assertEqual(sum(1 for e in st.bh.eintraege() if e["typ"] == MAIL_ABGELEGT), 2)


class TestRegelnEnglisch(unittest.TestCase):
    def test_stripe_rechnung(self):
        t = ("Page 1 of 1\nInvoice\nInvoice number PXE7RQGJ\x000008\nDate of issue September 25, 2026\n"
             "Anthropic, PBC @anthropic\n548 Market Street\nBill to\nhanserautisch\nTotal €107.10")
        v = vorschlag_regeln(t)
        self.assertEqual((v["lieferant"], v["rechnungsnummer"], v["rechnungsdatum"], v["betrag"]),
                         ("Anthropic, PBC", "PXE7RQGJ-0008", "2026-09-25", "107,10"))
        v = vorschlag_regeln("INVOICE\nSupabase Pte. Ltd.\nInvoice number WAOFNM-00007\nInvoice date Sep 21, 2026\n"
                             "Amount due $35.00")
        self.assertEqual((v["lieferant"], v["rechnungsdatum"], v["waehrung"], v["betrag_fremd"]),
                         ("Supabase Pte. Ltd.", "2026-09-21", "USD", "35,00"))


class TestMailBelegApi(ApiBasis):
    def test_datei_und_nachweis(self):
        from orchestrator.core.eingangsbelege import EingangStore
        st = EingangStore(self.w.kunden_store.bh)
        mail_eingang_pruefen(st, _G({"a1": _mail(MOIN, "Fwd: Deine Rechnung von Apple", html=APPLE)}), absender=ABS)
        nr = next(iter(_alle(st)))
        r = self.c.get(f"/api/finanzen/belege/{nr}/datei?i=1")
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r.headers["content-disposition"])
        self.assertTrue(r.headers["content-type"].startswith("message/rfc822"))
        self.assertEqual(self.c.get(f"/api/finanzen/belege/{nr}/datei?i=5").status_code, 404)
        q = st.aufnehmen(_pdf("Receipt " + "q" * 40), "Receipt.pdf")["nummer"]
        r = self.c.post(f"/api/finanzen/belege/{q}/als-nachweis", json={"zu": nr}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.c.get(f"/api/finanzen/belege/{nr}/datei?i=2").content[:5], b"%PDF-")
        self.assertFalse(self.c.post(f"/api/finanzen/belege/{q}/als-nachweis", json={"zu": nr}).json()["ok"])


if __name__ == "__main__":
    unittest.main()
