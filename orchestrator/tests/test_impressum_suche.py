"""IMPRESSUM_SUCHE I1: Kundendaten aus dem Impressum einer eingegebenen Website (nur Vorschlag) -- und nie Abrufe ins Heimnetz."""
import unittest

from orchestrator.core.firmendaten import (FirmenRecherche, NichtOeffentlich, _SichereUmleitung, aus_impressum, name_lesen,
                                           oeffentlich)
from orchestrator.tests.test_angebote import ApiBasis

IMPRESSUM = """<html><body><nav>Start | Speisekarte | Impressum</nav><h1>Impressum</h1>
<p>Angaben gemäß § 5 DDG</p><p>Kiez Alm Gastro GmbH<br>Spielbudenplatz 21<br>20359 Hamburg</p>
<p>Vertreten durch die Geschäftsführerin Lena Wirt</p><p>Telefon: +49 40 123456-0<br>E-Mail: info@kiezalm.de<br>
Rechnungen: rechnung@kiezalm.de</p><p>Registergericht: Amtsgericht Hamburg<br>HRB 123456</p>
<p>Umsatzsteuer-Identifikationsnummer gemäß § 27a UStG: DE 123 456 789</p></body></html>"""
START = '<html><body><a href="/rechtliches/impressum">Impressum</a> Willkommen auf der Alm!</body></html>'


def aufloesen(ips):
    return lambda host, port: [(None, None, None, "", (ip, 0)) for ip in ips]


class TestSchutz(unittest.TestCase):
    def test_nur_oeffentliche_adressen(self):
        ok = aufloesen(["93.184.216.34"])
        self.assertEqual(oeffentlich("https://kiezalm.de/impressum", aufloesen=ok), "https://kiezalm.de/impressum")
        for url, ips in [("http://nas.local/", ["192.168.178.129"]), ("http://fritz.box/", ["192.168.178.1"]),
                         ("http://localhost:80/", ["127.0.0.1"]), ("https://x.de/", ["10.0.0.5"]), ("https://x.de/", ["169.254.1.1"]),
                         ("https://x.de/", ["::1"]), ("https://x.de/", ["fe80::1%eth0"]), ("https://x.de/", ["93.184.216.34", "192.168.0.2"]),
                         ("https://x.de/", ["100.64.0.1"])]:
            with self.assertRaises(NichtOeffentlich, msg=(url, ips)):
                oeffentlich(url, aufloesen=aufloesen(ips))
        for url in ("ftp://x.de/", "file:///etc/passwd", "https://user:pw@x.de/", "https://x.de:8765/", "x.de"):
            with self.assertRaises(NichtOeffentlich, msg=url):
                oeffentlich(url, aufloesen=ok)

    def test_umleitung_ins_heimnetz(self):
        with self.assertRaises(NichtOeffentlich):
            _SichereUmleitung().redirect_request(None, None, 302, "Found", {}, "http://192.168.178.129:8765/api/")
        with self.assertRaises(NichtOeffentlich):
            aus_impressum("http://127.0.0.1/impressum")                          # echter Abruf -> sofort abgelehnt


class TestLesen(unittest.TestCase):
    def test_name(self):
        self.assertEqual(name_lesen("Impressum\nAngaben gemäß § 5\nKiez Alm Gastro GmbH\nSpielbudenplatz 21"), "Kiez Alm Gastro GmbH")
        self.assertEqual(name_lesen("Vertreten durch die Muster Verwaltungs GmbH\nMuster Media UG (haftungsbeschränkt)"),
                         "Muster Media UG (haftungsbeschränkt)")
        self.assertEqual(name_lesen("Willkommen\nKontakt"), "")

    def test_echte_schreibweisen(self):
        from orchestrator.core.firmendaten import impressum_lesen
        hsv = ("HSV Fußball Management AG\nVorstand: Dr. Eric Huwer\nHandelsregister des Amtsgerichtes Hamburg:\nHRB 191603\n"
               "USt-Id-Nr.:\nDE118717273")
        self.assertEqual(impressum_lesen(hsv)["handelsregister"], "Amtsgericht Hamburg HRB 191603")
        self.assertEqual(impressum_lesen("Hauptstraße 68\n02742 Friedersdorf\nUmsatzsteuer-ID : DE 212657916")["ustid"], "DE212657916")
        self.assertEqual(impressum_lesen("Muster AG\nVorstand: Max\nHRB 4711")["handelsregister"], "HRB 4711")   # kein „Amtsgericht Vorstand“

    def test_aus_impressum(self):
        seiten = {"https://kiezalm.de": START, "https://kiezalm.de/rechtliches/impressum": IMPRESSUM}
        abgerufen = []

        def abruf(url):
            abgerufen.append(url)
            if url not in seiten:
                raise OSError("404")
            return seiten[url]
        r = aus_impressum("kiezalm.de", abruf=abruf)
        self.assertEqual(r["quelle"], "https://kiezalm.de/rechtliches/impressum")
        self.assertEqual(r["vorschlaege"], {"name": "Kiez Alm Gastro GmbH", "strasse": "Spielbudenplatz 21", "plz": "20359",
                                            "ort": "Hamburg", "ustid": "DE123456789", "handelsregister": "Amtsgericht Hamburg HRB 123456",
                                            "telefon": "+49 40 123456-0", "rechnungsmail": "rechnung@kiezalm.de",
                                            "website": "https://kiezalm.de"})
        r = aus_impressum("https://leer.de", abruf=lambda u: "<p>Nur Werbung</p>")
        self.assertEqual(r["vorschlaege"], {})
        self.assertIn("direkten Link", r["hinweis"])
        with self.assertRaises(ValueError):
            aus_impressum("  ")


class TestApi(ApiBasis):
    def test_endpunkt(self):
        seiten = {"https://kiezalm.de/impressum": IMPRESSUM}
        self.w._RECHERCHE_TEST = FirmenRecherche(self.w.kunden_store, abruf=lambda u: seiten.get(u, ""))
        try:
            r = self.c.post("/api/crm/impressum-suche", json={"url": "https://kiezalm.de/impressum"}).json()
        finally:
            self.w._RECHERCHE_TEST = None
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["vorschlaege"]["name"], r["vorschlaege"]["plz"]), ("Kiez Alm Gastro GmbH", "20359"))
        self.assertEqual(len(self.w.kunden_store.firmen()), 1)                  # nichts angelegt, nur Vorschlag
        r = self.c.post("/api/crm/impressum-suche", json={"url": "http://192.168.178.129:8765/"}).json()
        self.assertEqual(r["ok"], False)
        self.assertIn("Web-Ports", r["hinweis"])


if __name__ == "__main__":
    unittest.main()
