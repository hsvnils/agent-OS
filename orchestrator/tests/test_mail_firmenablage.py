"""Mail-Ablage 2026-11-19 (CEO: „Ich leite LUNA die Mail weiter, spreche sie klar an und bitte um etwas, dann muss das auch
funktionieren“). Faelle aus dem Live-Betrieb:
- Outlook-Weiterleitung einer EIGENEN Mail („Von: nils@… <nils@…>“, „An: tf@mail-sports.com <…>“): Absender wurde nicht
  gelesen, und die Firma steht beim Empfaenger -> landete unter „Mail zuordnen“;
- gleiche Marke unter anderer Endung (elvir@handsofgod.de <-> handsofgod.football);
- Weiterleitung vom iPhone (hsvnils@icloud.com) mit Bitte -> Auftrag;
- LUNA-Werkzeug `akte_ablegen`: Ablage beim genannten Kunden, auch bevor der Akten-Abgleich lief; Gegenproben."""
import tempfile
import unittest
from pathlib import Path

from orchestrator.core.eingangsbelege import _kopf_adresse, mail_text, weiterleitung
from orchestrator.core.firmenakte import Firmenakte, firma_zu_adresse, mails_pruefen
from orchestrator.core.mail_auftraege import MailAuftragStore, ist_auftrag, nachricht, neue_auftraege
from orchestrator.tests.test_angebote import _stores
from orchestrator.tests.test_mail_belege import ABS, _G, _mail

LUNA = "luna.hanserautisch@gmail.com"
NILS = "nils@hanserautisch.de"
OUTLOOK = """Moin Luna,
Bitte beim Kunden ablegen und Erinnerung zum Nachfassen für in 7 Tagen anlegen.
Danke
Herzliche Grüße aus Hamburg
Nils Krüger
________________________________
Von: nils@hanserautisch.de <nils@hanserautisch.de>
Gesendet: Donnerstag, 19. November 2026 11:26
An: tf@mail-sports.com <tf@mail-sports.com>
Betreff: Hanserautisch - Gespräch auf der Messe
Moin Herr Froese,
wir hatten gestern gesprochen.
"""
IPHONE = """Moin Luna, bitte beim Kunden ablegen.

Von meinem iPhone gesendet

Anfang der weitergeleiteten Nachricht:

Von: Elvir <elvir@handsofgod.de>
Datum: 17. November 2026 um 10:00:00 MEZ
An: Nils <hsvnils@icloud.com>
Betreff: Ideen + Info

Hi Nils, anbei Ideen.
"""
ABS_ALLE = ABS + [NILS]


def _setup():
    bh, ks, st, k, ap = _stores()
    ms = ks.firma_anlegen({"name": "MAIL-SPORTS LTD", "typ": "lieferant", "rechnungsmail": "office@mail-sports.com",
                           "website": "https://mailsports.de/impressum"})["nummer"]
    hog = ks.firma_anlegen({"name": "Hands of God GmbH", "website": "https://www.handsofgod.football"})["nummer"]
    return bh, ks, ms, hog, Firmenakte(bh, ks)


class TestKopf(unittest.TestCase):
    def test_1_outlook_adresse_doppelt(self):
        self.assertEqual(_kopf_adresse("nils@hanserautisch.de <nils@hanserautisch.de>"), ("", NILS))
        self.assertEqual(_kopf_adresse("Anna <anna@brandx.de>"), ("Anna", "anna@brandx.de"))
        self.assertEqual(_kopf_adresse("x@y.de<mailto:x@y.de>")[1], "x@y.de")
        self.assertEqual(_kopf_adresse("ohne Adresse"), ("ohne Adresse", ""))
        roh = _mail(f"Nils <{NILS}>", "WG: Messe", text=OUTLOOK)
        orig, _rest, mark = weiterleitung(roh, mail_text(roh))
        self.assertEqual((orig["von"], orig["an"], mark), (NILS, ["tf@mail-sports.com"], True))

    def test_2_marke_andere_endung(self):
        bh, ks, ms, hog, akte = _setup()
        f = akte._firmen_mit_ansprechpartnern()
        self.assertEqual(firma_zu_adresse(f, "elvir@handsofgod.de"), hog)
        self.assertEqual(firma_zu_adresse(f, "tf@mail-sports.com"), ms)                  # Domain der Rechnungsmail
        self.assertEqual(firma_zu_adresse(f, "a@mailsports.com"), ms)                     # Marke ohne Bindestrich
        self.assertEqual(firma_zu_adresse(f, "a@hog.de"), "")                              # Gegenprobe: zu kurz
        self.assertEqual(firma_zu_adresse(f, "a@handsofgod.gmail.com"), "")               # Gegenprobe: andere Marke
        ks.firma_anlegen({"name": "Hands of God Shop", "website": "https://handsofgod.shop"})
        self.assertEqual(firma_zu_adresse(akte._firmen_mit_ansprechpartnern(), "elvir@handsofgod.de"), "")  # zwei -> keine


class TestAblage(unittest.TestCase):
    def test_1_eigene_mail_weitergeleitet_landet_beim_empfaenger(self):
        bh, ks, ms, hog, akte = _setup()
        g = _G({"o1": _mail(f"Nils <{NILS}>", "WG: Messe", text=OUTLOOK),
                "i1": _mail("Nils <hsvnils@icloud.com>", "Fwd: Ideen + Info", text=IPHONE)})
        mails_pruefen(akte, g, ceo=ABS_ALLE, luna=LUNA)
        self.assertEqual(akte.offene(), [])
        self.assertEqual([x["titel"] for x in akte.akte(ms)], ["Hanserautisch - Gespräch auf der Messe"])
        self.assertEqual([x["titel"] for x in akte.akte(hog)], ["Ideen + Info"])

    def test_2_gegenprobe_unbekannter_empfaenger_wartet(self):
        bh, ks, ms, hog, akte = _setup()
        g = _G({"o1": _mail(f"Nils <{NILS}>", "WG: Messe", text=OUTLOOK.replace("tf@mail-sports.com", "a@fremd-firma.de"))})
        mails_pruefen(akte, g, ceo=ABS_ALLE, luna=LUNA)
        self.assertEqual([m["titel"] for m in akte.offene()], ["Hanserautisch - Gespräch auf der Messe"])


class TestAuftrag(unittest.TestCase):
    def test_1_iphone_und_outlook_sind_auftraege(self):
        st = MailAuftragStore(Path(tempfile.mkdtemp()) / "log.jsonl")
        g = _G({})
        neue_auftraege(g, st, ceo=ABS_ALLE)                                                # erster Lauf: Bestand
        g.mails = {"i1": _mail("Nils <hsvnils@icloud.com>", "Fwd: Ideen + Info", text=IPHONE),
                   "o1": _mail(f"Nils <{NILS}>", "WG: Messe", text=OUTLOOK)}
        a = {x["id"]: x for x in neue_auftraege(g, st, ceo=ABS_ALLE)}
        self.assertEqual(set(a), {"i1", "o1"})
        self.assertIn("seine eigene Mail an tf@mail-sports.com", nachricht(a["o1"]))
        self.assertIn("urspruenglich von Elvir", nachricht(a["i1"]))
        self.assertIn("akte_ablegen", nachricht(a["o1"]))
        self.assertTrue(ist_auftrag("Mail beim Kunden ablegen"))
        self.assertFalse(ist_auftrag("Zur Info"))


class TestWerkzeug(unittest.TestCase):
    def _ctx(self, bh, g):
        from orchestrator.core.hoa_tools import ToolContext
        root = Path(tempfile.mkdtemp())
        (root / "buchhaltung").symlink_to(bh.dir)
        return ToolContext(core=None, antraege=None, engine=None, finance_dir=root, repo_root=root, leak_secrets=[],
                           google=g, secret_dict={"BELEG_ABSENDER": ",".join(ABS_ALLE), "GOOGLE_ACCOUNT_EMAIL": LUNA})

    def test_1_vor_dem_abgleich_mit_name(self):
        from orchestrator.core.hoa_tools import run_tool
        bh, ks, ms, hog, akte = _setup()
        fremd = OUTLOOK.replace("tf@mail-sports.com", "patrick@unbekannt.de")
        g = _G({"m1": _mail(f"Nils <{NILS}>", "WG: Alta", text=fremd)})
        ctx = self._ctx(bh, g)
        r = run_tool("akte_ablegen", {"mail_id": "m1", "firma": "mail-sports"}, ctx)
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["firma"], r["name"]), (ms, "MAIL-SPORTS LTD"))
        self.assertEqual([x["mail_id"] for x in akte.akte(ms)], ["m1"])
        again = run_tool("akte_ablegen", {"mail_id": "m1", "firma": ms}, ctx)              # idempotent
        self.assertTrue(again["ok"] and "schon" in again["hinweis"])
        self.assertEqual(len(akte.akte(ms)), 1)
        self.assertEqual(mails_pruefen(akte, g, ceo=ABS_ALLE, luna=LUNA), [])             # Abgleich legt nicht doppelt ab
        anders = run_tool("akte_ablegen", {"mail_id": "m1", "firma": hog}, ctx)
        self.assertFalse(anders["ok"])                                                     # Gegenprobe: kein Umhaengen

    def test_2_wartende_mail_zuordnen_und_gegenproben(self):
        from orchestrator.core.hoa_tools import run_tool
        bh, ks, ms, hog, akte = _setup()
        g = _G({"m2": _mail(f"Nils <{NILS}>", "WG: X", text=OUTLOOK.replace("tf@mail-sports.com", "a@fremd.de"))})
        mails_pruefen(akte, g, ceo=ABS_ALLE, luna=LUNA)
        self.assertEqual(len(akte.offene()), 1)
        ctx = self._ctx(bh, g)
        ohne = run_tool("akte_ablegen", {"mail_id": "m2"}, ctx)
        self.assertFalse(ohne["ok"])                                                       # ohne Firma: nachfragen
        unbekannt = run_tool("akte_ablegen", {"mail_id": "m2", "firma": "Gibtsnicht AG"}, ctx)
        self.assertFalse(unbekannt["ok"])
        self.assertIn("firma_anlegen", unbekannt["hinweis"])
        r = run_tool("akte_ablegen", {"mail_id": "m2", "firma": "Hands of God"}, ctx)
        self.assertTrue(r["ok"], r)
        self.assertEqual((akte.offene(), [x["mail_id"] for x in akte.akte(hog)]), ([], ["m2"]))

    def test_3_registriert(self):
        from orchestrator.core.hoa_tools import tool_specs
        from orchestrator.core.input_guard import AKTIONS_WERKZEUGE
        from orchestrator.core.werkzeugauswahl import auswahl
        self.assertIn("akte_ablegen", {s["name"] for s in tool_specs()})
        self.assertIn("akte_ablegen", AKTIONS_WERKZEUGE)
        self.assertIn("akte_ablegen", auswahl(nachricht({"id": "x", "betreff": "b", "von": "v", "auftrag": "Bitte ablegen"}))[0])


if __name__ == "__main__":
    unittest.main()
