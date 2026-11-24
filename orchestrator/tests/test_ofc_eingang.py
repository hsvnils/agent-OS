"""OFC_ROADMAP O5: Zahlungseingaenge der Mitglieder -- Erkennen (Name, Betrag, Mitteilung, Code), eindeutig automatisch,
Teilzahlung, Sammelzahlung fuer 2 Spiele, falscher Betrag, unbekannter Name, Rueckzahlung, Dublette, Mitteilung entscheidet,
Alias lernen, Saldo, Ticketstatus bezahlt, Dry-Run, Endpunkte nur CEO. Fixtures ohne echte Daten."""
import os
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest import mock

from orchestrator.core import ofc
from orchestrator.core import ofc_eingang as oe
from orchestrator.core.ofc_store import OfcStore, import_anwenden, spiel_detail, uebersicht
from orchestrator.tests.test_angebote import ApiBasis
from orchestrator.tests.test_ofc import HEIM, _pdf_als_text


def _pp(betreff: str, text: str, mid: str, datum: str = "Wed, 07 Oct 2026 10:00:00 +0200") -> dict:
    m = EmailMessage()
    m["From"], m["Subject"], m["Date"], m["Message-ID"] = "service@paypal.de", betreff, datum, mid
    m.set_content(text)
    return {"uid": "1", "roh": m.as_bytes()}


def _erhalten(name: str, betrag: str, mitteilung: str = "", tc: str = "1EE11111EE1111111", mid: str = "<e1@paypal.de>"):
    mt = f"Mitteilung von {name}:\n{mitteilung}\n\n" if mitteilung else ""
    return _pp("Sie haben eine Zahlung erhalten", f"Hallo Max!\n{name} hat Ihnen {betrag}\xa0€\xa0EUR gesendet\n"
               f"Erhaltener Betrag\n{betrag}\xa0€\xa0EUR\n{mt}Transaktionscode\n{tc}\n7. Oktober 2026\n", mid)


def _ordner(saison: Path, name: str, rnr: str, gegner: str, namen: list[str]):
    o = saison / name
    o.mkdir(parents=True)
    (o / "Rechnung.pdf").write_text(HEIM.replace("262236181415", rnr).replace("FC Bayern Muenchen", gegner), encoding="utf-8")
    for i, n in enumerate(namen, 1):
        (o / f"{rnr}-{i}-{n}.pdf").write_text(f"Ticketnummer: {rnr}-{i}", encoding="utf-8")


class _Basis(unittest.TestCase):
    """Zwei Spiele je 2 Tickets zu 35,00: FCB (Erika Muster, Ben Beispiel), SGE (Erika Muster, Carla)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.s = self.d / "Tickets 26-27"
        _ordner(self.s, "HSV vs FCB", "262236181415", "FC Bayern Muenchen", ["Erika Muster", "Ben Beispiel"])
        _ordner(self.s, "HSV vs SGE", "262236187777", "Eintracht Frankfurt", ["Erika Muster", "Carla"])
        self.st = OfcStore(self.d / "fanclub")
        self.p = mock.patch.object(ofc, "pdf_text", _pdf_als_text)
        self.p.start()
        import_anwenden(self.st, self.s)

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def bezahlt(self):
        return {nr for nr, x in oe.bezahlt_stand(self.st.stand())["tickets"].items() if x["bezahlt"]}


class TestLesen(unittest.TestCase):
    def test_1_felder_rueckzahlung_fremde(self):
        e = oe.eingang_lesen(_erhalten("Ben Beispiel", "35,00", "Bayern 1 Karte")["roh"])
        self.assertEqual((e["name"], e["betrag_cent"], e["mitteilung"], e["transaktionscode"], e["datum"], e["id"]),
                         ("Ben Beispiel", 3500, "Bayern 1 Karte", "1EE11111EE1111111", "2026-10-07", "e-1EE11111EE1111111"))
        r = oe.eingang_lesen(_pp("Rückzahlung an Ben Beispiel gesendet", "Sie haben eine Rückzahlung an Ben Beispiel gesendet\n"
                                 "Betrag 35,00\xa0€\xa0EUR\nTransaktionscode\n2RR22222RR2222222\n", "<r@paypal.de>")["roh"])
        self.assertEqual((r["name"], r["betrag_cent"], r["rueckzahlung"]), ("Ben Beispiel", -3500, True))
        self.assertIsNone(oe.eingang_lesen(_pp("Beleg für Ihre Zahlung an CTS EVENTIM", "Sie haben 70,00 € an CTS EVENTIM gezahlt",
                                               "<g@paypal.de>")["roh"]))                       # eigene Zahlung -> O4
        a = _erhalten("Ben Beispiel", "35,00")
        self.assertEqual(len(oe.eingaenge_aus_mails([a, a])), 1)                           # Dublette


class TestZuordnung(_Basis):
    def test_2_eindeutig_automatisch_dry_run(self):
        n = len(self.st.eintraege())
        v = oe.eingang_plan(self.st, [_erhalten("Ben Beispiel", "35,00")])
        self.assertEqual(len(self.st.eintraege()), n)
        e = v["neu"][0]
        self.assertEqual((e["zuordnung"], e["tickets"]), ("auto", ["262236181415-2"]))
        oe.eingang_anwenden(self.st, [_erhalten("Ben Beispiel", "35,00")])
        self.assertEqual(self.bezahlt(), {"262236181415-2"})
        self.assertEqual(oe.eingang_plan(self.st, [_erhalten("Ben Beispiel", "35,00")])["neu"], [])
        d = spiel_detail(self.st, "HSV vs FCB")
        self.assertEqual([t.get("bezahlt") for t in d["tickets"]], [False, True])
        self.assertEqual([x["karten_bezahlt"] for x in uebersicht(self.st)["spiele"] if x["id"] == "HSV vs FCB"], [1])

    def test_3_zwei_spiele_mitteilung_entscheidet_sonst_offen(self):
        e = oe.eingang_plan(self.st, [_erhalten("Erika Muster", "35,00")])["neu"][0]
        self.assertEqual(e["zuordnung"], "offen")                                         # FCB oder SGE?
        self.assertEqual({v["spiel"] for v in e["vorschlaege"]}, {"HSV vs FCB", "HSV vs SGE"})
        e = oe.eingang_plan(self.st, [_erhalten("Erika Muster", "35,00", "Frankfurt")])["neu"][0]
        self.assertEqual((e["zuordnung"], e["tickets"]), ("auto", ["262236187777-1"]))

    def test_4_sammelzahlung_fuer_zwei_spiele(self):
        e = oe.eingang_plan(self.st, [_erhalten("Erika Muster", "70,00")])["neu"][0]
        self.assertEqual((e["zuordnung"], sorted(e["tickets"])), ("auto", ["262236181415-1", "262236187777-1"]))

    def test_5_falscher_betrag_unbekannter_name_teilzahlung_saldo(self):
        self.assertEqual(oe.eingang_plan(self.st, [_erhalten("Ben Beispiel", "30,00")])["neu"][0]["zuordnung"], "offen")
        u = oe.eingang_plan(self.st, [_erhalten("Fremde Person", "35,00", tc="3FF33333FF3333333", mid="<u@paypal.de>")])["neu"][0]
        self.assertEqual((u["zuordnung"], u["vorschlaege"]), ("offen", []))
        oe.eingang_anwenden(self.st, [_erhalten("Ben Beispiel", "30,00")])
        eid = "e-1EE11111EE1111111"
        oe.eingang_zuordnen(self.st, eid, ["262236181415-2"])                              # Teilzahlung per Klick
        x = oe.bezahlt_stand(self.st.stand())
        self.assertEqual((x["tickets"]["262236181415-2"]["bezahlt"], x["tickets"]["262236181415-2"]["bezahlt_cent"], x["saldo"]["Ben Beispiel"]),
                         (False, 3000, -500))
        d = spiel_detail(self.st, "HSV vs FCB")["tickets"][1]
        self.assertEqual((d["bezahlt"], d["bezahlt_cent"]), (False, 3000))

    def test_6_rueckzahlung_ignorieren_loesen(self):
        oe.eingang_anwenden(self.st, [_erhalten("Ben Beispiel", "35,00")])
        r = _pp("Rückzahlung an Ben Beispiel gesendet", "Sie haben eine Rückzahlung an Ben Beispiel gesendet\nBetrag 35,00\xa0€\xa0EUR\n"
                "Transaktionscode\n2RR22222RR2222222\n", "<r@paypal.de>")
        v = oe.eingang_plan(self.st, [r])["neu"][0]
        self.assertEqual((v["betrag_cent"], v["zuordnung"]), (-3500, "offen"))
        oe.eingang_anwenden(self.st, [r])
        oe.eingang_zuordnen(self.st, v["id"], ["262236181415-2"])
        x = oe.bezahlt_stand(self.st.stand())
        self.assertFalse(x["tickets"]["262236181415-2"]["bezahlt"])                         # zurueckgezahlt
        self.assertEqual(x["saldo"]["Ben Beispiel"], -3500)
        oe.eingang_zuordnen(self.st, "e-1EE11111EE1111111", [], ignorieren=True)
        self.assertEqual(self.st.stand()["eingaenge"]["e-1EE11111EE1111111"]["zuordnung"], "ignoriert")
        self.assertEqual(oe.eingang_zuordnen(self.st, "e-1EE11111EE1111111", [])["zuordnung"], "offen")
        self.assertFalse(oe.eingang_zuordnen(self.st, "gibtsnicht", [])["ok"])
        self.assertFalse(oe.eingang_zuordnen(self.st, "e-1EE11111EE1111111", ["x-1"])["ok"])

    def test_7_alias_wird_gelernt(self):
        p = _erhalten("Benjamin B. Beispiel", "35,00", tc="4AA44444AA4444444", mid="<a@paypal.de>")
        e = oe.eingang_plan(self.st, [p])["neu"][0]
        self.assertEqual(e["zuordnung"], "offen")
        oe.eingang_anwenden(self.st, [p])
        r = oe.eingang_zuordnen(self.st, e["id"], ["262236187777-2"])                    # Carla, per Klick
        self.assertEqual(r["aliase_neu"], ["Carla"])
        oe.eingang_zuordnen(self.st, e["id"], [])                                         # wieder loesen
        q = _erhalten("Benjamin B. Beispiel", "35,00", tc="5AA55555AA5555555", mid="<b@paypal.de>")
        e2 = oe.eingang_plan(self.st, [q])["neu"][0]
        self.assertEqual((e2["zuordnung"], e2["tickets"]), ("auto", ["262236187777-2"]))     # ueber den Alias erkannt

    def test_8_lauf_fehler_ohne_text(self):
        pf = mock.Mock(verfuegbar=mock.Mock(return_value=True), posteingang=mock.Mock(side_effect=OSError("pw=geheim")))
        r = oe.lauf(self.st, pf)
        self.assertFalse(r["ok"]); self.assertNotIn("geheim", r["hinweis"])


class TestApi(ApiBasis):
    def test_9_endpunkte(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(ofc, "pdf_text", _pdf_als_text), \
                mock.patch.dict(os.environ, {"OFC_NAS_ORDNER": d}), mock.patch.object(self.w, "ROOT", Path(d)):
            s = Path(d) / "Tickets 26-27"
            _ordner(s, "HSV vs FCB", "262236181415", "FC Bayern Muenchen", ["Erika Muster", "Ben Beispiel"])
            self.c.post("/api/ofc/import", json={"bestaetigt": True})
            pf = mock.Mock(verfuegbar=mock.Mock(return_value=True),
                           posteingang=mock.Mock(return_value=[_erhalten("Ben Beispiel", "35,00"),
                                                               _erhalten("Fremde Person", "10,00", tc="6BB66666BB6666666", mid="<f@p>")]))
            with mock.patch.object(self.w, "_ofc_postfach", return_value=pf):
                v = self.c.get("/api/ofc/eingaenge/vorschau").json()
                self.assertEqual((v["auto"], v["offen"]), (1, 1))
                self.assertFalse(self.c.post("/api/ofc/eingaenge/abholen", json={}).json()["ok"])
                self.c.post("/api/ofc/eingaenge/abholen", json={"bestaetigt": True})
                e = self.c.get("/api/ofc/eingaenge").json()
                self.assertEqual((len(e["eingaenge"]), sum(1 for t in e["tickets"] if t["bezahlt"])), (2, 1))
                r = self.c.post("/api/ofc/eingang/e-6BB66666BB6666666/zuordnen", json={"tickets": ["262236181415-1"]}).json()
                self.assertEqual(r["zuordnung"], "manuell")
                self.assertEqual({x["name"]: x["saldo_cent"] for x in self.c.get("/api/ofc/eingaenge").json()["saldo"]},
                                 {"Fremde Person": -2500})
                self.assertFalse(self.c.post("/api/ofc/eingang/e-6BB66666BB6666666/zuordnen", json={"tickets": "x"}).json()["ok"])
                with mock.patch.object(self.w, "_ceo_user", return_value={"role": "team", "allowed_modules": ["finanzen"]}):
                    for url in ("/api/ofc/eingaenge", "/api/ofc/eingaenge/vorschau"):
                        self.assertEqual(self.c.get(url).status_code, 403, url)
                    self.assertEqual(self.c.post("/api/ofc/eingang/e-6BB66666BB6666666/zuordnen", json={"tickets": []}).status_code, 403)


class TestNachbesserung(_Basis):
    def test_10_abgeschlossen_zaehlt_mitteilung_anderes_spiel_nicht_auto(self):
        from orchestrator.core.ofc_store import ofc as _o
        ab = self.s / _o.ABGESCHLOSSEN
        ab.mkdir()
        (self.s / "HSV vs FCB").rename(ab / "HSV vs FCB")
        import_anwenden(self.st, self.s)
        e = oe.eingang_plan(self.st, [_erhalten("Ben Beispiel", "35,00")])["neu"][0]
        self.assertEqual((e["zuordnung"], e["tickets"]), ("auto", ["262236181415-2"]))   # abgeschlossenes Spiel
        e = oe.eingang_plan(self.st, [_erhalten("Ben Beispiel", "35,00", "Frankfurt")])["neu"][0]
        self.assertEqual(e["zuordnung"], "offen")                                     # Mitteilung nennt anderes Spiel

    def test_11_alte_fassung_neu_bewertet_klick_bleibt(self):
        self.st.erfassen("ofc_eingang", {"id": "e-1EE11111EE1111111", "name": "Ben Beispiel", "betrag_cent": 3500,
                                         "datum": "2026-10-07", "zuordnung": "offen", "tickets": [], "v": 1})
        self.st.erfassen("ofc_eingang", {"id": "e-klick", "name": "Carla", "betrag_cent": 3500, "datum": "2026-10-01",
                                         "zuordnung": "manuell", "tickets": ["262236187777-2"], "v": 1})
        v = oe.eingang_plan(self.st, [_erhalten("Ben Beispiel", "35,00")])
        self.assertEqual([(e["id"], e["zuordnung"]) for e in v["neu"]], [("e-1EE11111EE1111111", "auto")])
        oe.eingang_anwenden(self.st, [_erhalten("Ben Beispiel", "35,00")])
        self.assertEqual(self.bezahlt(), {"262236181415-2", "262236187777-2"})
        self.assertEqual(oe.eingang_plan(self.st, [_erhalten("Ben Beispiel", "35,00")])["neu"], [])


class TestV3(unittest.TestCase):
    """Fassung 3: Ticketnamen wie „28B-ReneSchnettler“, Spiel aus der Mitteilung (Spitznamen, Pokal, Heim/Auswaerts),
    freie Karten, aufgerundet, Teilzahlungen, Preis unbekannt, Bank/Trikot -> info, Klick wird nie neu bewertet."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        s = self.d / "Tickets 26-27"
        _ordner(s, "HSVvsBMG", "262230000001", "Borussia Moenchengladbach", ["28B-ErikaMuster", "Frei"])
        _ordner(s, "HSVvsSGE - DFB-Pokal", "262230000002", "Eintracht Frankfurt", ["20A - Ben", "Carla"])
        _ordner(s, "SGEvsHSV", "262230000003", "Eintracht Frankfurt", ["Ben", "Dora"])
        self.st = OfcStore(self.d / "fanclub")
        self.p = mock.patch.object(ofc, "pdf_text", _pdf_als_text)
        self.p.start()
        import_anwenden(self.st, s)

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def plan(self, *mails):
        return {e["id"]: e for e in oe.eingang_plan(self.st, list(mails))["neu"]}

    def test_12_ticketname_zusammengeschrieben_und_spitzname(self):
        self.assertEqual(oe._ticket_woerter("28BOkkaHammen"), {"okka", "hammen"})
        self.assertEqual(oe._ticket_woerter("28B-ReneSchnettler"), {"rene", "schnettler"})
        self.assertEqual(oe._ticket_woerter("Johannes1"), {"johannes"})
        self.assertTrue(oe._frei("Frei") and oe._frei("") and not oe._frei("Ben"))
        e = self.plan(_erhalten("Érika Muster", "35,00"))["e-1EE11111EE1111111"]
        self.assertEqual((e["zuordnung"], e["tickets"]), ("auto", ["262230000001-1"]))
        e = self.plan(_erhalten("Max Neu", "35,00", "HSV - Gladbach"))["e-1EE11111EE1111111"]
        self.assertEqual((e["zuordnung"], e["tickets"]), ("auto", ["262230000001-2"]))        # freie Karte im genannten Spiel

    def test_13_pokal_heim_auswaerts(self):
        e = self.plan(_erhalten("Ben Beispiel", "35,00", "Frankfurt DFB-Pokal"))["e-1EE11111EE1111111"]
        self.assertEqual((e["zuordnung"], e["tickets"]), ("auto", ["262230000002-1"]))
        e = self.plan(_erhalten("Ben Beispiel", "35,00", "Karten in Frankfurt"))["e-1EE11111EE1111111"]
        self.assertEqual((e["zuordnung"], e["tickets"]), ("auto", ["262230000003-1"]))
        e = self.plan(_erhalten("Ben Beispiel", "35,00", "Frankfurt"))["e-1EE11111EE1111111"]
        self.assertEqual(e["zuordnung"], "offen")                                         # Pokal oder auswaerts?
        e = self.plan(_erhalten("Ben Beispiel", "35,00", "Gladbach vs HSV"))["e-1EE11111EE1111111"]
        self.assertEqual(e["zuordnung"], "offen")                                         # nur das Heimspiel im Bestand

    def test_14_aufgerundet_wahl_teilzahlungen(self):
        e = self.plan(_erhalten("Max Neu", "37,00", "Gladbach"))["e-1EE11111EE1111111"]
        self.assertEqual((e["zuordnung"], e["tickets"]), ("auto", ["262230000001-2"]))
        self.assertTrue(any(g.startswith("aufgerundet (+2,00") for g in e["vorschlaege"][0]["gruende"]))
        e = self.plan(_erhalten("Ben Beispiel", "70,00", "Pokal"))["e-1EE11111EE1111111"]
        self.assertEqual((e["zuordnung"], e["wahl"]["karten"], e["wahl"]["tickets"]), ("offen", 2, ["262230000002-1"]))
        v = self.plan(_erhalten("Dora D.", "34,00"), _erhalten("Dora D.", "1,00", tc="7CC77777CC7777777", mid="<t@p>"))
        self.assertEqual({(e["zuordnung"], tuple(e["tickets"])) for e in v.values()}, {("auto", ("262230000003-2",))})
        oe.eingang_anwenden(self.st, [_erhalten("Dora D.", "34,00"), _erhalten("Dora D.", "1,00", tc="7CC77777CC7777777", mid="<t@p>")])
        self.assertTrue(oe.bezahlt_stand(self.st.stand())["tickets"]["262230000003-2"]["bezahlt"])

    def test_15_bank_trikot_info_und_klick_bleibt(self):
        b = _pp("Sie haben eine Rückzahlung gesendet", "Sie haben eine Rückzahlung an Hamburger Sparkasse AG ••1234 gesendet\n"
                "Betrag 50,00\xa0€\xa0EUR\nTransaktionscode\n8BB88888BB8888888\n", "<b@p>")
        t = _erhalten("Carla Neu", "16,00", "Trikot", tc="9TT99999TT9999999", mid="<tr@p>")
        v = self.plan(b, t)
        self.assertEqual(sorted(e["zuordnung"] for e in v.values()), ["info", "info"])
        oe.eingang_anwenden(self.st, [b, t, _erhalten("Max Neu", "35,00", "Gladbach")])
        self.assertEqual(oe.eingang_plan(self.st, [b, t, _erhalten("Max Neu", "35,00", "Gladbach")])["neu"], [])   # unveraendert: nichts neu
        oe.eingang_zuordnen(self.st, "e-1EE11111EE1111111", [])                            # CEO loest per Klick
        self.assertEqual(oe.eingang_plan(self.st, [_erhalten("Max Neu", "35,00", "Gladbach")])["neu"], [])
        self.assertTrue(self.st.stand()["eingaenge"]["e-1EE11111EE1111111"]["von_hand"])

    def test_16_offene_werden_mit_neuem_alias_neu_bewertet(self):
        p = _erhalten("Gerd Vater", "70,00", "Pokal")
        oe.eingang_anwenden(self.st, [p])
        self.assertEqual(self.st.stand()["eingaenge"]["e-1EE11111EE1111111"]["zuordnung"], "offen")
        self.st.erfassen("ofc_alias", {"zahler": "gerd vater", "name": "20A - Ben"})
        self.st.erfassen("ofc_alias", {"zahler": "gerd vater", "name": "Carla"})
        e = oe.eingang_plan(self.st, [p])
        self.assertEqual((e["neu_bewertet"], e["neu"][0]["zuordnung"]), (1, "auto"))
