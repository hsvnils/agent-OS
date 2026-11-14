"""Organigramm als XMind: wird aus Charten und Skill-Ordnern gebaut und muss aktuell im Repo liegen."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("xmind_bauen", ROOT / "scripts" / "xmind_bauen.py")
xb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(xb)


def _titel(thema: dict) -> list[str]:
    out = [thema["title"]]
    for k in thema.get("children", {}).get("attached", []):
        out += _titel(k)
    return out


class Organigramm(unittest.TestCase):
    def test_alle_agenten_mit_nummer(self):
        titel = _titel(xb.organigramm())
        for key, rel in xb._charten().items():
            nummer = Path(rel).name.split("_", 1)[0]
            self.assertTrue(any(t.startswith(f"{nummer} · ") for t in titel), (key, nummer))
        self.assertTrue(any(t.startswith("18 · CMO") for t in titel))

    def test_skills_kommen_aus_den_ordnern(self):
        titel = _titel(xb.organigramm())
        self.assertIn("monetarisierungsplan", titel)
        self.assertIn("partner-zielprofil", titel)

    def test_datei_im_repo_ist_aktuell(self):
        """Nach Charta- oder Skill-Aenderung: python3 scripts/xmind_bauen.py organigramm"""
        im_repo = json.loads(zipfile.ZipFile(ROOT / "governance" / "organigramm.xmind").read("content.json"))
        self.assertEqual(_titel(im_repo[0]["rootTopic"]), _titel(xb.organigramm()))


class AusJson(unittest.TestCase):
    def test_zeitstrahl_struktur_und_notizen(self):
        with tempfile.TemporaryDirectory() as d:
            ein, ziel = Path(d) / "a.json", Path(d) / "a.xmind"
            ein.write_text(json.dumps({"blaetter": [{"titel": "Weg", "struktur": "timeline", "wurzel": {
                "titel": "Start", "kinder": [{"titel": "Q1", "notiz": "Ziel"}]}}]}), encoding="utf-8")
            self.assertEqual(xb.main(["json", str(ein), str(ziel)]), 0)
            blatt = json.loads(zipfile.ZipFile(ziel).read("content.json"))[0]
        self.assertEqual(blatt["rootTopic"]["structureClass"], "org.xmind.ui.timeline.horizontal")
        self.assertEqual(blatt["rootTopic"]["children"]["attached"][0]["notes"]["plain"]["content"], "Ziel")


if __name__ == "__main__":
    unittest.main()
