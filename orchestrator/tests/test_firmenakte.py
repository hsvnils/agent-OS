"""KUNDEN_FINANZEN Etappe 24: Firmenakte -- Dokumente je Firma (mit Bezug zur Rechnung), weitergeleitete Mails und
Mails mit LUNA in CC/BCC landen bei der passenden Firma, unklare in „Mail zuordnen“; Belege bleiben beim Beleg-Abruf."""
import base64
import unittest

from orchestrator.core.firmenakte import Firmenakte, firma_zu_adresse, mails_pruefen
from orchestrator.core.todos import geschaefts_todos
from orchestrator.tests.test_angebote import ApiBasis, _stores
from orchestrator.tests.test_eingangsbelege import _pdf
from orchestrator.tests.test_mail_belege import ABS, MOIN, PAYPAL, _G, _mail

LUNA = "luna.hanserautisch@gmail.com"
ANWALT = """Sehr geehrter Herr Krüger,

in Sachen Kiez Alm Gastro GmbH ./. Krüger zeigen wir die Vertretung an. Unsere Mandantin bestreitet die Forderung.

Mit freundlichen Grüßen
Kanzlei Recht & Ordnung"""


def _setup():
    bh, ks, st, k, ap = _stores()                  # K-00001 Brand X mit rechnung@brandx.de, AP anna@brandx.de
    kiez = ks.firma_anlegen({"name": "Kiez Alm Gastro GmbH", "website": "https://www.kiez-alm.de"})["nummer"]
    return bh, ks, k, kiez, Firmenakte(bh, ks)


def _weiter(text, orig_von, betreff="Ihre Forderung"):
    return (f"Bitte bei Kiezalm ablegen\n\nVon meinem iPhone gesendet\n\nAnfang der weitergeleiteten Nachricht:\n\n"
            f"Von: {orig_von}\nBetreff: {betreff}\nDatum: 1. Oktober 2026 um 10:00:00 MESZ\nAn: Nils <moin@hanserautisch.de>\n\n{text}")


class TestZuordnung(unittest.TestCase):
    def test_1_adressen(self):
        bh, ks, k, kiez, akte = _setup()
        firmen = ks.firmen()
        self.assertEqual(firma_zu_adresse(firmen, "anna@brandx.de"), k)                  # Ansprechpartner
        self.assertEqual(firma_zu_adresse(firmen, "buchhaltung@brandx.de"), k)           # Domain
        self.assertEqual(firma_zu_adresse(firmen, "info@kiez-alm.de"), kiez)              # Website-Domain
        ks.ansprechpartner_anlegen(kiez, {"vorname": "Chef", "mail": "chef.kiez@gmail.com"})
        firmen = akte._firmen_mit_ansprechpartnern()
        self.assertEqual(firma_zu_adresse(firmen, "chef.kiez@gmail.com"), kiez)          # exakte Adresse ja
        self.assertEqual(firma_zu_adresse(firmen, "irgendwer@gmail.com"), "")             # Freemail nie per Domain

    def test_2_dokument_mit_bezug(self):
        bh, ks, k, kiez, akte = _setup()
        r = akte.hochladen(kiez, _pdf("Anwaltsschreiben"), "anwalt.pdf", titel="Schreiben der Anwältin", art="anwalt",
                           bezug="rg-11052026")
        self.assertEqual([x["titel"] for x in akte.akte(kiez)], ["Schreiben der Anwältin"])
        self.assertEqual([x["id"] for x in akte.zu_bezug("RG-11052026")], [r["id"]])
        for falsch in ({"art": "quatsch"}, {"bezug": "irgendwas"}):
            with self.assertRaises(ValueError):
                akte.hochladen(kiez, b"x", "x.pdf", **falsch)
        with self.assertRaises(KeyError):
            akte.hochladen("K-99999", b"x", "x.pdf")


class TestMails(unittest.TestCase):
    def test_1_weitergeleitet_cc_und_zuordnen(self):
        bh, ks, k, kiez, akte = _setup()
        weiter = _mail(MOIN, "WG: Ihre Forderung", text=_weiter(ANWALT, "Kanzlei <post@kiez-alm.de>"))
        cc = _mail("Anna <anna@brandx.de>", "Re: Kampagne", text="Passt so!", koepfe={"To": "moin@hanserautisch.de",
                                                                                     "Cc": LUNA})
        unklar = _mail(MOIN, "WG: Anfrage", text=_weiter("Hallo!", "Fremd <x@unbekannt-firma.de>", "Anfrage"))
        beleg = _mail(MOIN, "WG: Beleg für Ihre Zahlung an DAZN DACH GmbH", text=PAYPAL)
        fremd = _mail("Newsletter <news@shop.de>", "Angebot der Woche", text="Kaufen!")
        g = _G({"w1": weiter, "c1": cc, "u1": unklar, "b1": beleg, "n1": fremd})
        neu = mails_pruefen(akte, g, ceo=ABS, luna=LUNA)
        self.assertEqual(len(neu), 3)                                                     # kein Beleg, kein Newsletter
        kz = akte.akte(kiez)[0]
        self.assertEqual((kz["art"], kz["titel"], kz["notiz"], kz["mail_von"]),
                         ("mail", "Ihre Forderung", "Bitte bei Kiezalm ablegen", "post@kiez-alm.de"))
        self.assertTrue(bh.dir.joinpath(kz["dateien"][1]["pfad"]).read_bytes().startswith(b"Authentication-Results"))
        self.assertEqual([x["titel"] for x in akte.akte(k)], ["Kampagne"])
        offen = akte.offene()
        self.assertEqual([m["titel"] for m in offen], ["Anfrage"])
        self.assertIn(f"akte:{offen[0]['id']}", {t["id"] for t in geschaefts_todos(bh, ks)})
        akte.zuordnen(offen[0]["id"], kiez)
        self.assertEqual((akte.offene(), len(akte.akte(kiez))), ([], 2))
        self.assertEqual(mails_pruefen(akte, g, ceo=ABS, luna=LUNA), [])                  # idempotent
        with self.assertRaises(ValueError):
            akte.zuordnen(offen[0]["id"], kiez)

    def test_1a_ansprechpartner_mit_freemail(self):
        bh, ks, k, kiez, akte = _setup()
        ks.ansprechpartner_anlegen(kiez, {"vorname": "Chef", "mail": "chef.kiez@gmail.com"})
        m = _mail("Chef <chef.kiez@gmail.com>", "Termin", text="Morgen?", koepfe={"To": "moin@hanserautisch.de", "Cc": LUNA})
        mails_pruefen(akte, _G({"a1": m}), ceo=ABS, luna=LUNA)
        self.assertEqual([x["titel"] for x in akte.akte(kiez)], ["Termin"])

    def test_1b_zwei_firmen_in_einer_mail(self):
        bh, ks, k, kiez, akte = _setup()
        beide = _mail(MOIN, "Abstimmung", text="Hallo zusammen", koepfe={"To": "anna@brandx.de", "Cc": f"info@kiez-alm.de, {LUNA}"})
        mails_pruefen(akte, _G({"z1": beide}), ceo=ABS, luna=LUNA)
        self.assertEqual((akte.akte(k), akte.akte(kiez)), ([], []))
        self.assertEqual(sorted(akte.offene()[0]["kandidaten"]), sorted([k, kiez]))       # du entscheidest

    def test_2_gefaelschte_weiterleitung(self):
        bh, ks, k, kiez, akte = _setup()
        falsch = _mail(MOIN, "WG: Ihre Forderung", text=_weiter(ANWALT, "Kanzlei <post@kiez-alm.de>"), auth="falsch")
        self.assertEqual(mails_pruefen(akte, _G({"f1": falsch}), ceo=ABS, luna=LUNA), [])


class TestApi(ApiBasis):
    def test_a1_hochladen_ansehen_rechnung(self):
        r = self.c.post(f"/api/crm/kunden/{self.k}/akte", json={
            "datei": {"name": "vertrag.pdf", "daten": base64.b64encode(_pdf("Vertrag")).decode()}, "art": "vertrag",
            "titel": "Rahmenvertrag", "bezug": "RE-2026-0001"}).json()
        self.assertTrue(r["ok"], r)
        a = self.c.get(f"/api/crm/kunden/{self.k}/akte").json()
        self.assertEqual(a["dokumente"][0]["titel"], "Rahmenvertrag")
        f = self.c.get(f"/api/crm/akte/{r['id']}/datei")
        self.assertEqual((f.status_code, f.headers["content-type"]), (200, "application/pdf"))
        self.assertEqual(self.c.get(f"/api/crm/akte/{r['id']}/datei?i=5").status_code, 404)


if __name__ == "__main__":
    unittest.main()
