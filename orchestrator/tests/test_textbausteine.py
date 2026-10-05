"""TEXTBAUSTEINE_MAILVERSAND T1-T3: Vorlagen mit Platzhaltern (Standard = bisheriger Text), Signatur ersetzt den Gruss,
Pruefung beim Speichern, Ablage nur auf der NAS, Vorlagenwahl im Versand, .eml-Entwurf fuer Outlook, PDF fuer das
Teilen-Menue und „Als versendet markieren“ ohne Gmail."""
import email
import json
import unittest
from email import policy

from orchestrator.core.angebote import mail_text as angebot_mail_text
from orchestrator.core.konzept import mail_text as konzept_mail_text
from orchestrator.core.mahnungen import mahnung_mail_text
from orchestrator.core.projektbericht import mail_text as bericht_mail_text
from orchestrator.core.rechnungen import rechnung_mail_text
from orchestrator.core.textbausteine import ARTEN, PLATZHALTER, STANDARD, TextbausteinStore, eml, rendern
from orchestrator.tests.test_angebote import ApiBasis

FD = {"inhaber": "Nils Krüger", "firma": "Krüger Onlinehandel und Media"}
AP = {"vorname": "Anna", "nachname": "Muster"}
SIG = "Herzliche Grüße aus Hamburg\nNils Krüger"


class TestStandardTexte(unittest.TestCase):
    """Ohne Signatur und ohne eigene Vorlage entstehen genau die bisherigen Texte (Wortlaut vor T1)."""
    def test_1_angebot(self):
        a = {"nummer": "AN-2026-0001", "titel": "Herbst", "summe_cent": 102000, "gueltig_bis": "2026-10-19",
             "praesentation": {"url": "https://x.y", "text": "Unsere Präsentation ansehen"}}
        self.assertEqual(angebot_mail_text(a, {}, AP, FD), (
            "Angebot AN-2026-0001 – Herbst",
            "Guten Tag Anna Muster,\n\nanbei erhalten Sie unser Angebot AN-2026-0001 zu „Herbst“ über 1.020,00 €. Es ist "
            "gültig bis 19.10.2026.\n\nUnsere Präsentation ansehen: https://x.y\n\nBei Fragen melden Sie sich gerne.\n\n"
            "Mit freundlichen Grüßen\nNils Krüger\nKrüger Onlinehandel und Media"))
        a = a | {"titel": "", "praesentation": {}}
        self.assertEqual(angebot_mail_text(a, {}, None, {})[1],
                         "Sehr geehrte Damen und Herren,\n\nanbei erhalten Sie unser Angebot AN-2026-0001 über 1.020,00 €. "
                         "Es ist gültig bis 19.10.2026.\n\nBei Fragen melden Sie sich gerne.\n\nMit freundlichen Grüßen\n")

    def test_2_storno_mahnung_bericht_konzept(self):
        r = {"nummer": "RE-2026-0009", "art": "storno", "bezug": "RE-2026-0007", "summe_cent": -5000}
        self.assertEqual(rechnung_mail_text(r, AP, FD)[0], "Stornorechnung RE-2026-0009 zu RE-2026-0007")
        m = {"nummer": "MA-2026-0003", "rechnung": "RE-2026-0007", "stufe": 3, "faellig_am": "2026-09-01",
             "summe_cent": 12345, "frist": "2026-10-12"}
        b, t = mahnung_mail_text(m, AP, FD)
        self.assertEqual(b, "3. Mahnung zu Rechnung RE-2026-0007")
        self.assertIn("Anbei erhalten Sie unsere letzte Mahnung (MA-2026-0003).", t)
        self.assertEqual(bericht_mail_text({"auftrag": "AB-2026-0001", "titel": ""}, None, FD, 2),
                         ("Projektbericht AB-2026-0001 (Version 2)",
                          "Moin,\n\nanbei unser Projektbericht zur Kampagne mit den erreichten Zahlen je Posting.\n\n"
                          "Bei Fragen melden Sie sich gern.\n\nViele Grüße\nNils Krüger\nKrüger Onlinehandel und Media"))
        self.assertTrue(konzept_mail_text({"vorgang": "AN-2026-0001", "titel": "Herbst"}, AP, FD, 1)[1]
                        .startswith("Moin Anna Muster,\n\nanbei unser Konzept zu „Herbst“ mit Briefing"))

    def test_3_signatur_und_eigene_vorlage(self):
        w = {"anrede": "Moin Anna,", "nummer": "AN-1", "betrag": "5 €", "zu_titel": "", "gueltig_bis": "1.1.2027"}
        b, t = rendern("angebot", w, FD, vorlage={"betreff": "Ihr Angebot {nummer}", "text": "{anrede}\n\nhier {betrag}."},
                       signatur=SIG)
        self.assertEqual((b, t), ("Ihr Angebot AN-1", "Moin Anna,\n\nhier 5 €.\n\n" + SIG))
        self.assertNotIn("Mit freundlichen Grüßen", t)                         # Signatur ersetzt den Gruss
        for art in ARTEN:                                                        # Standard nutzt nur erlaubte Platzhalter
            TextbausteinStore.pruefe({"vorlagen": {art: [{"name": "x", **STANDARD[art], "standard": True}]}})
            self.assertTrue(PLATZHALTER[art])


class TestStore(ApiBasis):
    def test_1_speichern_pruefen_protokoll(self):
        st = TextbausteinStore(self.w.kunden_store.bh)
        self.assertEqual(st.vorlage("angebot")["id"], "standard")
        with self.assertRaises(ValueError):
            st.speichern({"vorlagen": {"angebot": [{"name": "A", "betreff": "x", "text": "{gibtsnicht}", "standard": True}]}})
        with self.assertRaises(ValueError):
            st.speichern({"vorlagen": {"angebot": [{"name": "A", "betreff": "x", "text": "Klammer { offen", "standard": True}]}})
        r = st.speichern({"signatur": SIG, "vorlagen": {"angebot": [
            {"name": "Erstangebot", "betreff": "Angebot {nummer}", "text": "{anrede}\n\nanbei {nummer}.", "standard": False},
            {"name": "Nachfassen", "betreff": "Nachfrage {nummer}", "text": "{anrede}\n\nkurze Nachfrage.", "standard": False}]}})
        self.assertEqual((r["arten"], r["signatur"]), (["angebot"], True))
        d = st.laden()
        self.assertEqual([v["standard"] for v in d["vorlagen"]["angebot"]], [True, False])   # genau ein Standard
        self.assertEqual(d["vorlagen"]["rechnung"][0]["id"], "standard")                     # andere Arten unberuehrt
        nach = st.vorlage("angebot", d["vorlagen"]["angebot"][1]["id"])
        self.assertEqual(nach["name"], "Nachfassen")
        self.assertEqual(st.vorlage("angebot", "gibtsnicht")["name"], "Erstangebot")
        self.assertTrue((self.w.kunden_store.bh.dir / "textbausteine.json").exists())
        ev = [e for e in self.w.kunden_store.bh.eintraege() if e["typ"] == "textbausteine_geaendert"]
        self.assertEqual(len(ev), 1)
        self.assertNotIn("Hamburg", json.dumps(ev[0]["daten"]))                             # keine Texte in der Kette
        self.assertEqual(st.speichern(st.laden()), {"geaendert": False})


class TestVersand(ApiBasis):
    def setUp(self):
        super().setUp()
        self.nr = self._neu()
        TextbausteinStore(self.w.kunden_store.bh).speichern({"signatur": SIG, "vorlagen": {"angebot": [
            {"id": "standard", "name": "Standard", **STANDARD["angebot"], "standard": True},
            {"id": "kurz", "name": "Kurz", "betreff": "Kurz {nummer}", "text": "{anrede}\n\nanbei {nummer}.", "standard": False}]}})

    def test_1_vorschau_mit_vorlage_und_signatur(self):
        v = self.c.get(f"/api/crm/angebote/{self.nr}/versandvorschau").json()
        self.assertEqual((v["art"], v["vorlage"], [x["name"] for x in v["vorlagen"]]), ("angebot", "standard", ["Standard", "Kurz"]))
        self.assertTrue(v["text"].endswith(SIG))
        k = self.c.get(f"/api/crm/angebote/{self.nr}/versandvorschau?vorlage=kurz").json()
        self.assertEqual(k["betreff"], f"Kurz {self.nr}")
        self.assertTrue(k["text"].startswith("Moin Anna,") or k["text"].startswith("Guten Tag"))

    def test_2_eml_und_pdf(self):
        r = self.c.post(f"/api/crm/mailentwurf/angebot/{self.nr}/eml", json={"an": "anna@brandx.de", "betreff": "B", "text": "T\n\n" + SIG})
        self.assertEqual(r.status_code, 200)
        m = email.message_from_bytes(r.content, policy=policy.default)
        self.assertEqual((m["X-Unsent"], m["To"], m["Subject"]), ("1", "anna@brandx.de", "B"))
        self.assertIn("Herzliche Grüße aus Hamburg", m.get_body(("plain",)).get_content())
        anh = list(m.iter_attachments())
        self.assertEqual(anh[0].get_filename(), f"Angebot_{self.nr}.pdf")
        self.assertTrue(anh[0].get_content().startswith(b"%PDF"))
        p = self.c.get(f"/api/crm/mailentwurf/angebot/{self.nr}/pdf")
        self.assertEqual((p.status_code, p.content[:4]), (200, b"%PDF"))
        self.assertEqual(self.c.get("/api/crm/mailentwurf/gibtsnicht/X/pdf").status_code, 404)
        self.assertEqual(self.c.post(f"/api/crm/mailentwurf/angebot/{self.nr}/eml", json={"betreff": "", "text": ""}).status_code, 400)

    def test_3_als_versendet_ohne_gmail(self):
        vorher = len(self.g.gesendet)
        r = self.c.post(f"/api/crm/angebote/{self.nr}/senden", json={"an": "anna@brandx.de", "betreff": "B", "text": "T",
                                                                     "bestaetigt": True, "kanal": "mail-programm"}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(len(self.g.gesendet), vorher)                            # LUNA hat nichts verschickt
        a = self.c.get(f"/api/crm/angebote/{self.nr}").json()["angebot"]
        self.assertEqual(a["status"], "versendet")
        self.assertEqual(a["versendet_mail"]["kanal"], "mail-programm")
        self.assertTrue(a["pdfs"])                                                 # PDF abgelegt wie beim Gmail-Weg

    def test_4_textbausteine_api(self):
        d = self.c.get("/api/crm/textbausteine").json()
        self.assertEqual(set(d["arten"]), set(ARTEN))
        self.assertEqual(d["textbausteine"]["signatur"], SIG)
        r = self.c.post("/api/crm/textbausteine", json={"textbausteine": {"signatur": "x", "vorlagen": {"mahnung": [
            {"name": "M", "betreff": "{falsch}", "text": "t", "standard": True}]}}}).json()
        self.assertFalse(r["ok"])
        self.assertIn("unbekannte Platzhalter", r["hinweis"])


if __name__ == "__main__":
    unittest.main()
