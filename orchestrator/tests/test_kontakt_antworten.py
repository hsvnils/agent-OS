"""KONTAKTE K3: Antworten auf freie Mails an Ansprechpartner (Kennung aus `kontakt_mail_gesendet`) -> Firmenakte mit
Firma + Ansprechpartner, Meldung „Antwort von <Name> (<Firma>)“; nur ueber In-Reply-To/References, nie ueber den Betreff;
fremde Mails bleiben unberuehrt; Dry-Run schreibt nichts."""
from unittest import mock

from orchestrator.core.firmenakte import Firmenakte
from orchestrator.core.mail_antworten import (KONTAKT_GESENDET, antworten_pruefen, ap_zu_adresse, kontakt_mail_vermerken,
                                              kontakt_mails)
from orchestrator.tests.test_allinkl_mail import ENV
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_mail_antworten import CEO, Postfach, antwort

KEN = "luna-" + "c" * 24
MID = f"<{KEN}@hanserautisch.de>"


class TestKontaktAntwort(ApiBasis):
    def setUp(self):
        super().setUp()
        self.ks, self.bh = self.w.kunden_store, self.w.kunden_store.bh
        self.ap = self.ks.firma(self.k)["ansprechpartner_liste"][0]

    def _vermerken(self, ap=None):
        kontakt_mail_vermerken(self.bh, firma=self.k, ansprechpartner=self.ap["nummer"] if ap is None else ap,
                               message_id=MID, betreff="Hallo Anna", an=["anna@brandx.de"], von="test")

    def test_1_vermerk(self):
        with self.assertRaises(ValueError):
            kontakt_mail_vermerken(self.bh, firma=self.k, ansprechpartner="", message_id="<abc@x.de>")   # keine LUNA-Kennung
        self._vermerken()
        km = kontakt_mails(self.bh.eintraege())
        self.assertEqual((km[KEN]["firma"], km[KEN]["ansprechpartner"]), (self.k, self.ap["nummer"]))

    def test_2_antwort_in_reply_to_und_references(self):
        self._vermerken()
        a1 = antwort("Anna <anna@brandx.de>", "Re: Hallo Anna", "Klingt gut!\n\nAm Montag schrieb LUNA:\n> alt", auf=MID)
        a2 = antwort("Bob <bob@brandx.de>", "AW: Hallo Anna", "Ich uebernehme.", mid="<b2@brandx.de>")
        import email
        from email import policy
        m2 = email.message_from_bytes(a2, policy=policy.default)
        m2["References"] = f"<irgendwas@x.de> {MID}"                                   # nur ueber References
        meldungen = []
        pf = Postfach([a1, m2.as_bytes(),
                       antwort("fremd@spam.de", "Re: Hallo Anna", "Gewinn!", mid="<s1@x>"),        # Betreff gleich, keine Kennung
                       antwort("anna@brandx.de", "Hallo nochmal", "ohne Bezug", mid="<s2@x>")])
        neu = antworten_pruefen(self.bh, self.ks, pf, eigene=CEO + ["luna@hanserautisch.de"],
                                notify=lambda t, **kw: meldungen.append(t))
        self.assertEqual([(x["nummer"], x["art"], x["ablage"]) for x in neu], [(self.k, "kontakt", "akte")] * 2)
        self.assertEqual(neu[0]["ansprechpartner"], self.ap["nummer"])                 # Anna = hinterlegter AP
        self.assertEqual(neu[1]["ansprechpartner"], self.ap["nummer"])                 # Bob unbekannt -> AP der Mail
        doks = [d for d in self.c.get(f"/api/crm/kunden/{self.k}/akte").json()["dokumente"] if d["art"] == "mail"]
        self.assertEqual(len(doks), 2)
        self.assertTrue(all(d["firma"] == self.k and d["ansprechpartner"] == self.ap["nummer"] for d in doks))
        name = f"{self.ap['vorname']} {self.ap['nachname']}".strip()
        self.assertTrue(meldungen[0].startswith(f"✉️ Antwort von {name} ("), meldungen[0])
        self.assertIn("Klingt gut!", meldungen[0])
        self.assertNotIn("alt", meldungen[0])
        self.assertEqual(Firmenakte(self.bh, self.ks).offene(), [])                    # fremde Mails nicht in "zuordnen"
        self.assertEqual(antworten_pruefen(self.bh, self.ks, pf, eigene=CEO), [])     # genau einmal

    def test_3_ohne_vermerk_nichts(self):
        """Gegenprobe: ohne gesendete freie Mail wird eine Antwort mit fremder Kennung nicht zugeordnet."""
        pf = Postfach([antwort("anna@brandx.de", "Re: Hallo Anna", "x", auf=MID)])
        self.assertEqual(antworten_pruefen(self.bh, self.ks, pf, eigene=CEO), [])
        self.assertFalse([e for e in self.bh.eintraege() if e["typ"] in ("akte_dokument", "akte_mail_offen")])

    def test_4_ceo_antwort_ignoriert(self):
        self._vermerken()
        pf = Postfach([antwort("Nils <nils@hanserautisch.de>", "Re: Hallo Anna", "intern", auf=MID)])
        self.assertEqual(antworten_pruefen(self.bh, self.ks, pf, eigene=CEO), [])

    def test_5_trocken_schreibt_nichts(self):
        self._vermerken(ap="")
        vorher = len(self.bh.eintraege())
        meldungen = []
        pf = Postfach([antwort("Anna <anna@brandx.de>", "Re: Hallo", "ok", auf=MID)])
        t = antworten_pruefen(self.bh, self.ks, pf, eigene=CEO, trocken=True, notify=lambda t, **kw: meldungen.append(t))
        self.assertEqual([(x["nummer"], x["ablage"], x["ansprechpartner"]) for x in t],
                         [(self.k, "trocken", self.ap["nummer"])])                    # AP ueber die Absenderadresse
        self.assertEqual((len(self.bh.eintraege()), meldungen), (vorher, []))
        with mock.patch.object(self.w, "_google_secrets", return_value=ENV), \
             mock.patch("orchestrator.governance.allinkl_mail.AllInklMail.posteingang", lambda s, tage=30: pf.posteingang()):
            r = self.c.get("/api/crm/antworten/trocken").json()
        self.assertTrue(r["ok"], r)
        self.assertEqual([(x["nummer"], x["art"]) for x in r["treffer"]], [(self.k, "kontakt")])
        self.assertEqual(len(self.bh.eintraege()), vorher)

    def test_6_ap_bei_belegantwort(self):
        """Auch Antworten auf Belege/Vorstellungen tragen den Ansprechpartner, wenn die Absenderadresse hinterlegt ist."""
        self.assertEqual(ap_zu_adresse(self.ks, self.k, "ANNA@brandx.de")["nummer"], self.ap["nummer"])
        self.assertIsNone(ap_zu_adresse(self.ks, self.k, "bob@brandx.de"))
        self.assertIsNone(ap_zu_adresse(self.ks, "", "anna@brandx.de"))
        self.assertEqual(KONTAKT_GESENDET, "kontakt_mail_gesendet")
