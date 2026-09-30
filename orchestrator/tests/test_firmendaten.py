"""KUNDEN_FINANZEN Etappe 22: oeffentliche Firmendaten aus dem Impressum vorschlagen, nur fuer leere Felder, mit Quelle;
uebernommen wird nur per Klick; keine Privatpersonen; woechentlicher Lauf mit Pause und Obergrenze."""
import unittest
from datetime import timedelta

from orchestrator.core.buchhaltung import jetzt
from orchestrator.core.firmendaten import (FirmenRecherche, impressum_lesen, luecken, offene_vorschlaege, uebernehmen,
                                           wochenlauf)
from orchestrator.tests.test_angebote import ApiBasis, _stores

IMPRESSUM = """<html><head><script>var x = "HRB 99999";</script></head><body><h1>Impressum</h1>
<p>Angaben gemäß § 5 DDG</p><p>Kiez Alm Gastro GmbH<br>Große Freiheit 39 A<br>22767 Hamburg</p>
<p>Telefon: +49 40 123 456 78<br>E-Mail: info@kiezalm.de, Rechnungen: rechnung@kiezalm.de</p>
<p>Registergericht: Amtsgericht Hamburg<br>Registernummer: HRB 123456</p>
<p>Umsatzsteuer-Identifikationsnummer gemäß § 27 a UStG: DE 123 456 789</p></body></html>"""


class _Netz:
    def __init__(self, seiten=None, treffer=None):
        self.seiten, self.treffer, self.abrufe, self.suchen = seiten or {}, treffer or [], [], []

    def suche(self, q):
        self.suchen.append(q)
        return self.treffer

    def abruf(self, url):
        self.abrufe.append(url)
        if url not in self.seiten:
            raise OSError("404")
        return self.seiten[url]


class TestLesen(unittest.TestCase):
    def test_1_impressum(self):
        from orchestrator.core.firmendaten import _text
        v = impressum_lesen(_text(IMPRESSUM))
        self.assertEqual(v, {"strasse": "Große Freiheit 39 A", "plz": "22767", "ort": "Hamburg", "ustid": "DE123456789",
                             "handelsregister": "Amtsgericht Hamburg HRB 123456", "telefon": "+49 40 123 456 78",
                             "rechnungsmail": "rechnung@kiezalm.de"})
        self.assertEqual(impressum_lesen("Musterweg 5, 20095 Hamburg\nKontakt: info@x.de"),
                         {"strasse": "Musterweg 5", "plz": "20095", "ort": "Hamburg"})   # info@ ist keine Rechnungs-Mail
        self.assertEqual(impressum_lesen("Große Freiheit 39 a-b\n22767 Hamburg")["strasse"], "Große Freiheit 39 a-b")
        self.assertEqual(impressum_lesen("HANDS OF GOD GmbH\nKöpenicker Straße 154 A\nAufgang D\n10997 Berlin")["strasse"],
                         "Köpenicker Straße 154 A")                                       # Zusatzzeile dazwischen
        self.assertEqual(impressum_lesen("Umsatzsteuer-Identifikationsnummer\ngemäß §27a Umsatzsteuergesetz: DE365736352")
                         ["ustid"], "DE365736352")

    def test_2_impressum_link_der_startseite(self):
        bh, ks, st, k, ap = _stores()
        nr = ks.firma_anlegen({"name": "Grover Group GmbH", "website": "https://www.grover.com"})["nummer"]
        n = _Netz({"https://www.grover.com": '<a href="/de-de/g-about/impressum">Impressum</a><a href="https://evil.example/impressum">x</a>',
                   "https://www.grover.com/de-de/g-about/impressum": IMPRESSUM.replace("Kiez Alm Gastro GmbH", "Grover Group GmbH")})
        r = FirmenRecherche(ks, abruf=n.abruf).recherchieren(nr)
        self.assertEqual(r["quelle"], "https://www.grover.com/de-de/g-about/impressum")
        self.assertNotIn("https://evil.example/impressum", n.abrufe)                     # nur dieselbe Website
        n2 = _Netz({"https://www.grover.com": '<a href="https://evil.example/impressum">Impressum</a>'})
        nr2 = ks.firma_anlegen({"name": "Grover Zwei GmbH", "website": "https://www.grover.com"})["nummer"]
        FirmenRecherche(ks, abruf=n2.abruf).recherchieren(nr2)
        self.assertNotIn("https://evil.example/impressum", n2.abrufe)                    # auch ohne eigenes Impressum nie


class TestRecherche(unittest.TestCase):
    def _kiez(self):
        bh, ks, st, k, ap = _stores()
        nr = ks.firma_anlegen({"name": "Kiez Alm Gastro GmbH", "plz": "22767", "ort": "Hamburg"})["nummer"]
        return bh, ks, nr

    def test_1_suche_vorschlaege_nur_luecken_und_uebernehmen(self):
        bh, ks, nr = self._kiez()
        n = _Netz({"https://www.kiezalm.de/impressum": IMPRESSUM},
                  [("Kiez Alm – North Data", "https://www.northdata.de/Kiez+Alm"), ("Kiez Alm Hamburg", "https://www.kiezalm.de/")])
        r = FirmenRecherche(ks, suche=n.suche, abruf=n.abruf).recherchieren(nr)
        self.assertEqual(r["quelle"], "https://www.kiezalm.de/impressum")
        self.assertEqual(set(r["vorschlaege"]), {"strasse", "ustid", "handelsregister", "telefon", "rechnungsmail", "website"})
        self.assertNotIn("plz", r["vorschlaege"])                                   # war schon ausgefuellt
        self.assertEqual(ks.firma(nr).get("ustid") or "", "")                        # nichts automatisch uebernommen
        ks.firma_aendern(nr, {"telefon": "040 999"})                                  # inzwischen von Hand eingetragen
        uebernehmen(ks, nr, ["telefon"])
        self.assertEqual(ks.firma(nr)["telefon"], "040 999")                          # nie ueberschreiben
        u = uebernehmen(ks, nr, ["ustid"])
        self.assertEqual((u["uebernommen"], ks.firma(nr)["ustid"]), ({"ustid": "DE123456789"}, "DE123456789"))
        self.assertNotIn("ustid", offene_vorschlaege(bh.eintraege())[nr]["vorschlaege"])
        uebernehmen(ks, nr, None)
        f = ks.firma(nr)
        self.assertEqual((f["handelsregister"], f["website"]), ("Amtsgericht Hamburg HRB 123456", "https://www.kiezalm.de"))
        with self.assertRaises(ValueError):
            uebernehmen(ks, nr, None)                                                 # nichts mehr offen

    def test_2_verwerfen_privat_und_nichts_gefunden(self):
        bh, ks, nr = self._kiez()
        n = _Netz({"https://www.kiezalm.de/impressum": IMPRESSUM}, [("Kiez Alm", "https://www.kiezalm.de")])
        FirmenRecherche(ks, suche=n.suche, abruf=n.abruf).recherchieren(nr)
        uebernehmen(ks, nr, None, verwerfen=True)
        self.assertEqual(ks.firma(nr).get("ustid") or "", "")
        privat = ks.firma_anlegen({"name": "Max Mustermann", "verbraucher": True})["nummer"]
        with self.assertRaises(ValueError):
            FirmenRecherche(ks, suche=n.suche, abruf=n.abruf).recherchieren(privat)
        leer = _Netz(treffer=[("Irgendwas", "https://www.linkedin.com/company/kiez")])
        r = FirmenRecherche(ks, suche=leer.suche, abruf=leer.abruf).recherchieren(nr)
        self.assertEqual((r["vorschlaege"], leer.abrufe), ({}, []))                  # Portale werden nie abgerufen

    def test_3_wochenlauf(self):
        bh, ks, nr = self._kiez()
        for i in range(10):
            ks.firma_anlegen({"name": f"Firma{i} Beispiel GmbH"})
        n = _Netz({"https://www.kiezalm.de/impressum": IMPRESSUM}, [("Kiez Alm", "https://www.kiezalm.de")])
        rec = FirmenRecherche(ks, suche=n.suche, abruf=n.abruf)
        erledigt = wochenlauf(ks, rec, je_lauf=4)
        self.assertEqual(len(n.suchen), 4)                                          # Obergrenze je Lauf
        n.suchen.clear()
        wochenlauf(ks, rec, je_lauf=50)
        geprueft = {e["daten"]["nummer"] for e in bh.eintraege() if e["typ"] == "firma_recherche"}
        self.assertEqual(len(n.suchen), len([f for f in ks.firmen() if luecken(f)]) - 4)   # die 4 pausieren
        n.suchen.clear()
        wochenlauf(ks, rec, je_lauf=50)
        self.assertEqual(n.suchen, [])                                              # alle in der Pause
        wochenlauf(ks, rec, heute=jetzt() + timedelta(days=31), je_lauf=50)
        self.assertEqual(len(n.suchen), len(geprueft))                              # nach 30 Tagen wieder dran
        self.assertIn(nr, erledigt)                                                  # Kiez Alm hatte Vorschlaege


class TestApi(ApiBasis):
    def test_a1_recherche_und_uebernahme(self):
        n = _Netz({"https://www.brandx.de/impressum": IMPRESSUM.replace("Kiez Alm Gastro GmbH", "Brand X GmbH")},
                  [("Brand X", "https://www.brandx.de")])
        self.w._RECHERCHE_TEST = FirmenRecherche(self.w.kunden_store, suche=n.suche, abruf=n.abruf)
        try:
            r = self.c.post(f"/api/crm/kunden/{self.k}/recherche", json={}).json()
            self.assertTrue(r["ok"], r)
            d = self.c.get(f"/api/crm/kunden/{self.k}").json()
            self.assertIn("ustid", d["vorschlaege"])
            u = self.c.post(f"/api/crm/kunden/{self.k}/vorschlaege", json={"felder": ["ustid"]}).json()
            self.assertTrue(u["ok"], u)
            self.assertEqual(self.c.get(f"/api/crm/kunden/{self.k}").json()["firma"]["ustid"], "DE123456789")
        finally:
            self.w._RECHERCHE_TEST = None


if __name__ == "__main__":
    unittest.main()
