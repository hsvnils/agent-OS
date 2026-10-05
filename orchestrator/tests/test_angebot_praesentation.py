"""ANGEBOT_PRAESENTATION P1: Canva-Praesentation (DE/EN) je Angebot waehlbar -- Standard Deutsch, eingefroren beim
Anlegen, klickbar im PDF (beide Layouts), im digitalen Beleg und im Mailtext; Altangebote ohne Feld ohne Link."""
import copy
import json
import unittest
import zlib

from orchestrator.core import belegblatt
from orchestrator.core.angebote import AngebotStore, mail_text
from orchestrator.core.katalog import STANDARD, Katalog, pruefe
from orchestrator.tests.test_angebote import FIRMA, POS, _stores

DE, EN = "https://canva.link/so4wrkmr0n7gfq1", "https://canva.link/yyeywahmisjymuw"


def _pdf_text(pdf: bytes) -> str:
    """Rohtext inkl. entpackter Streams (Link-Annotationen stehen als /URI im Klartext)."""
    out, i = [pdf.decode("latin-1")], 0
    while (i := pdf.find(b"stream", i)) != -1:
        s = pdf.find(b"\n", i) + 1
        e = pdf.find(b"endstream", s)
        try:
            out.append(zlib.decompress(pdf[s:e].rstrip(b"\r\n")).decode("latin-1"))
        except zlib.error:
            pass
        i = e
    return "\n".join(out)


class TestKatalog(unittest.TestCase):
    def test_1_standard_und_alte_kataloge(self):
        t = pruefe(copy.deepcopy(STANDARD))["texte"]
        self.assertEqual((t["praesentation_de"], t["praesentation_en"]), (DE, EN))
        alt = copy.deepcopy(STANDARD)
        for f in ("praesentation_de", "praesentation_en", "praesentation_text_de", "praesentation_text_en"):
            alt["texte"].pop(f)                                               # Katalog von vorher (NAS) -> Standard
        self.assertEqual(pruefe(alt)["texte"]["praesentation_de"], DE)
        aus = copy.deepcopy(STANDARD)
        aus["texte"]["praesentation_en"] = ""                                 # bewusst aus
        self.assertEqual(pruefe(aus)["texte"]["praesentation_en"], "")
        aus["texte"]["praesentation_en"] = "http://unsicher.example"
        with self.assertRaises(ValueError):
            pruefe(aus)


class TestAngebot(unittest.TestCase):
    def setUp(self):
        self.bh, self.ks, _, self.k, self.ap = _stores()
        (self.bh.dir / "firmendaten.json").write_text(json.dumps(FIRMA), encoding="utf-8")
        self.st = AngebotStore(self.bh, self.ks, Katalog(self.bh))

    def _neu(self, **extra):
        return self.st.anlegen({"firma": self.k, "ansprechpartner": self.ap, "titel": "Herbst", "positionen": POS} | extra)["nummer"]

    def test_1_standard_deutsch_eingefroren(self):
        nr = self._neu()
        self.assertEqual(self.st.angebot(nr)["praesentation"],
                         {"sprache": "de", "url": DE, "text": "Unsere Präsentation ansehen"})
        k = Katalog(self.bh).laden()
        k["texte"]["praesentation_de"] = "https://canva.link/neu"
        Katalog(self.bh).speichern(k)
        self.assertEqual(self.st.angebot(nr)["praesentation"]["url"], DE)    # bestehendes Angebot unveraendert
        self.assertEqual(self.st.angebot(self._neu())["praesentation"]["url"], "https://canva.link/neu")

    def test_2_englisch_keiner_aendern_ungueltig(self):
        nr = self._neu(praesentation="en")
        self.assertEqual(self.st.angebot(nr)["praesentation"]["text"], "View our presentation")
        self.st.aendern(nr, {"praesentation": ""})
        self.assertEqual(self.st.angebot(nr)["praesentation"], {})
        with self.assertRaises(ValueError):
            self._neu(praesentation="fr")

    def test_3_pdf_beide_layouts_beleg_und_mail(self):
        for layout in ("hanserautisch", "standard"):
            nr = self._neu(layout=layout, praesentation="en")
            pdf = _pdf_text(self.st.pdf(nr, FIRMA))
            self.assertIn(EN, pdf, layout)
            self.assertIn("/URI", pdf, layout)                               # klickbare Link-Annotation
        a = self.st.angebot(nr)
        self.assertEqual(belegblatt.angebot(self.st, a, FIRMA)["praesentation"]["url"], EN)
        _, text = mail_text(a, {}, None, FIRMA)
        self.assertIn(f"View our presentation: {EN}", text)

    def test_4_ohne_link(self):
        nr = self._neu(praesentation="")
        a = self.st.angebot(nr)
        self.assertNotIn("canva.link", _pdf_text(self.st.pdf(nr, FIRMA)))
        self.assertNotIn("canva.link", mail_text(a, {}, None, FIRMA)[1])
        self.assertEqual(belegblatt.angebot(self.st, a, FIRMA)["praesentation"], {})
        alt = dict(a)
        alt.pop("praesentation")                                              # Altangebot vor P1
        self.assertNotIn("canva.link", mail_text(alt, {}, None, FIRMA)[1])


if __name__ == "__main__":
    unittest.main()
