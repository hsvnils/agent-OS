"""Zweck/Begruendung am Beleg (CEO 2026-09-30): Text des CEO ueber einer weitergeleiteten Rechnung wird als Zweck
gespeichert (betriebliche Veranlassung), ist in LUNA-OS aenderbar und steht im Export fuer den Steuerberater."""
import unittest

from orchestrator.core.eingangsbelege import datei_importieren, mail_eingang_pruefen, zweck_aus_mail
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_eingangsbelege import TEXT, _pdf, _store
from orchestrator.tests.test_mail_belege import ABS, APPLE, MOIN, PAYPAL, _G, _mail

GRUND = ("Für das Drehen von Content im Athleticum gekauft – Medizincheck auf dem Laufband, "
         "dafür saubere Schuhe")


def _weiter(zweck: str, original: str = PAYPAL) -> str:
    return f"{zweck}\n\nVon meinem iPhone gesendet\n\n{original}"


class TestZweck(unittest.TestCase):
    def test_1_zweck_aus_mail(self):
        self.assertEqual(zweck_aus_mail(_mail(MOIN, "Fwd: Beleg", text=_weiter(GRUND))), GRUND)
        self.assertEqual(zweck_aus_mail(_mail(MOIN, "Fwd: Beleg", text=_weiter("Viele Grüße\nNils"))), "")   # nur Gruss
        self.assertEqual(zweck_aus_mail(_mail(MOIN, "Fwd: Rechnung", html=APPLE)), "")                      # Gruss im HTML
        self.assertEqual(zweck_aus_mail(_mail("PayPal <service@paypal.de>", "Beleg", text=PAYPAL)), "")      # keine Weiterleitung

    def test_2_weiterleitung_mit_grund_und_nachtrag_zum_doppelten(self):
        st = _store()
        neu = mail_eingang_pruefen(st, _G({"m1": _mail(MOIN, "WG: Beleg für Ihre Zahlung an DAZN DACH GmbH",
                                                       text=_weiter(GRUND))}), absender=ABS)
        self.assertEqual(st.get(neu[0])["zweck"], GRUND)
        st2 = _store()                                                     # erst ohne Grund, dann mit Grund nochmal
        nr = mail_eingang_pruefen(st2, _G({"m1": _mail(MOIN, "WG: Beleg für Ihre Zahlung an DAZN DACH GmbH",
                                                       text=PAYPAL)}), absender=ABS)[0]
        self.assertNotIn("zweck", st2.get(nr))
        mail_eingang_pruefen(st2, _G({"m2": _mail(MOIN, "WG: nochmal mit Grund", text=_weiter("Für DAZN-Content"))}),
                             absender=ABS)
        self.assertEqual(st2.get(nr)["zweck"], "Für DAZN-Content")

    def test_3_pdf_anhang_und_eml_import(self):
        st = _store()
        roh = _mail(MOIN, "Fwd: Ihre Rechnung", text=_weiter("Druck für das Stadion-Banner"),
                    anhaenge=[("Rechnung.pdf", _pdf(TEXT))])
        nr = mail_eingang_pruefen(st, _G({"m1": roh}), absender=ABS)[0]
        self.assertEqual(st.get(nr)["zweck"], "Druck für das Stadion-Banner")
        st3 = _store()
        r = datei_importieren(st3, _mail(MOIN, "Fwd: Beleg", text=_weiter("Hosting für die App")), "x.eml")
        self.assertEqual(st3.get(r[0]["nummer"])["zweck"], "Hosting für die App")

    def test_4_nachtragen_aendern_verlauf(self):
        st = _store()
        nr = datei_importieren(st, _pdf(TEXT), "Rechnung.pdf")[0]["nummer"]
        st.zweck_setzen(nr, "  Banner   für den Dreh ")
        self.assertEqual(st.get(nr)["zweck"], "Banner für den Dreh")
        with self.assertRaises(ValueError):
            st.zweck_setzen(nr, "Banner für den Dreh")                      # keine Aenderung
        st.zweck_setzen(nr, "")                                            # darf auch geleert werden
        self.assertEqual(st.get(nr)["zweck"], "")
        self.assertEqual(sum("zweck" in (v.get("felder") or []) for v in st.get(nr)["verlauf"]), 2)


class TestApi(ApiBasis):
    def test_a1_endpunkt_und_export(self):
        import base64
        import io
        import zipfile
        r = self.c.post("/api/finanzen/belege/hochladen",
                        json={"dateien": [{"name": "R.pdf", "daten": base64.b64encode(_pdf(TEXT)).decode()}]}).json()
        nr = r["ergebnisse"][0]["nummer"]
        z = self.c.post(f"/api/finanzen/belege/{nr}/zweck", json={"zweck": GRUND}).json()
        self.assertTrue(z["ok"], z)
        self.assertEqual(self.c.get(f"/api/finanzen/belege/{nr}").json()["beleg"]["zweck"], GRUND)
        ex = self.c.get("/api/finanzen/abschluss/export?jahr=2026")
        self.assertEqual(ex.status_code, 200)
        csv = zipfile.ZipFile(io.BytesIO(ex.content)).read("eingangsbelege.csv").decode("utf-8-sig")
        self.assertIn("Zweck", csv.splitlines()[0])
        self.assertIn("Medizincheck", csv)


if __name__ == "__main__":
    unittest.main()
