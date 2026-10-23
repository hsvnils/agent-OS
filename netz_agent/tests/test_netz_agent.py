"""NETZ_AGENT Q1: Quarantaene-Container -- sichere Abrufe (nur oeffentliche Adressen, Port 80/443, Weiterleitungen geprueft,
Groessen-/Typgrenzen), Warteschlange (Auftrag -> Ergebnis, nur Treffer-Seiten), Trennung von LUNA (kein Import, Compose
nur mit zwei Ordnern und eigener .env)."""
import ast
import json
import re
import socket
import tempfile
import unittest
from pathlib import Path

from netz_agent import abruf
from netz_agent.agent import Agent, pruefe_auftrag

ROOT = Path(__file__).resolve().parents[2]
DNS = {"example.org": "93.184.216.34", "boese.example": "192.168.178.1", "lokal.example": "127.0.0.1",
       "meta.example": "169.254.169.254", "cgnat.example": "100.64.0.1", "v6.example": "::1",
       "gemischt.example": ["93.184.216.34", "10.0.0.5"], "gemappt.example": "::ffff:192.168.0.1"}


def aufloesen(host, port, type=None):
    ips = DNS.get(host)
    if ips is None:
        raise socket.gaierror("unbekannt")
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in (ips if isinstance(ips, list) else [ips])]


class _Antwort:
    def __init__(self, status=200, kopf=None, koerper=b""):
        self.status, self._kopf, self._k = status, kopf or {}, koerper

    def getheader(self, n, std=None):
        return self._kopf.get(n, std)

    def read(self, n=-1):
        return self._k if n < 0 else self._k[:n]


def verbindung_mit(antworten: dict):
    gesehen = []

    class _Con:
        def __init__(self, host, ip, port, timeout):
            self.host, self.ip = host, ip

        def request(self, methode, pfad, headers=None):
            gesehen.append((self.host, self.ip, pfad))

        def getresponse(self):
            return antworten[self.host]

        def close(self):
            pass
    return _Con, gesehen


class TestAbruf(unittest.TestCase):
    def test_1_nur_oeffentlich(self):
        self.assertEqual(abruf.pruefe_url("https://example.org/a?b=1", aufloesen)[1:], ("example.org", 443, "/a?b=1", "93.184.216.34"))
        for url in ("http://boese.example/", "http://lokal.example/", "http://meta.example/latest", "http://cgnat.example/",
                    "http://v6.example/", "http://gemischt.example/", "http://gemappt.example/", "ftp://example.org/x",
                    "file:///etc/passwd", "https://example.org:8443/", "https://user:pw@example.org/", "http:///x",
                    "https://gibtsnicht.example/"):
            with self.assertRaises(abruf.Abgelehnt, msg=url):
                abruf.pruefe_url(url, aufloesen)

    def test_2_weiterleitung_ins_heimnetz(self):
        con, gesehen = verbindung_mit({"example.org": _Antwort(302, {"Location": "http://boese.example/admin"})})
        with self.assertRaisesRegex(abruf.Abgelehnt, "oeffentliche"):
            abruf.hole("https://example.org/", aufloesen=aufloesen, verbindung=con)
        self.assertEqual(gesehen, [("example.org", "93.184.216.34", "/")])          # Heimnetz nie kontaktiert

    def test_3_typ_groesse_text(self):
        con, _ = verbindung_mit({"example.org": _Antwort(200, {"Content-Type": "application/pdf"}, b"%PDF")})
        with self.assertRaisesRegex(abruf.Abgelehnt, "Inhaltstyp"):
            abruf.hole("https://example.org/", aufloesen=aufloesen, verbindung=con)
        html = (b"<html><head><title>Preise 2026</title><script>stiehl()</script><style>x{}</style></head><body>"
                b"<p>Reel ab 500 EUR</p>" + b"<p>" + b"x" * (abruf.MAX_BYTES + 5000) + b"</p></body></html>")
        con, _ = verbindung_mit({"example.org": _Antwort(200, {"Content-Type": "text/html; charset=utf-8"}, html)})
        s = abruf.hole("https://example.org/", aufloesen=aufloesen, verbindung=con)
        self.assertEqual(s["titel"], "Preise 2026")
        self.assertIn("Reel ab 500 EUR", s["text"])
        self.assertNotIn("stiehl", s["text"])
        self.assertLessEqual(len(s["text"]), abruf.MAX_TEXT)


class TestWarteschlange(unittest.TestCase):
    def setUp(self):
        self.q = Path(tempfile.mkdtemp())
        self.geholt = []
        treffer = [{"titel": f"T{i}", "url": f"https://example.org/{i}", "auszug": "a"} for i in range(8)]
        self.agent = Agent(self.q, "schluessel", suche=lambda f, s: treffer,
                           hole=lambda u: self.geholt.append(u) or {"url": u, "titel": "", "text": "Inhalt", "status": 200})

    def auftrag(self, name, daten):
        (self.q / "auftraege" / f"{name}.json").write_text(json.dumps(daten), encoding="utf-8")

    def test_4_auftrag_ergebnis(self):
        self.auftrag("auftrag-0001", {"id": "auftrag-0001", "art": "suche", "frage": "Preise Stadion-Reels 2026", "max_seiten": 9})
        self.auftrag("../boese", {"id": "x"})
        self.auftrag("auftrag-0002", {"id": "auftrag-0002", "art": "datei_lesen", "pfad": "/app/orchestrator/.env"})
        self.assertEqual(self.agent.ein_durchlauf(), 2)
        e = json.loads((self.q / "ergebnisse" / "auftrag-0001.json").read_text(encoding="utf-8"))
        self.assertTrue(e["ok"])
        self.assertEqual(len(e["seiten"]), 5)                                        # hoechstens 5 Seiten
        self.assertEqual(self.geholt, [f"https://example.org/{i}" for i in range(5)])  # nur Treffer-URLs
        f = json.loads((self.q / "ergebnisse" / "auftrag-0002.json").read_text(encoding="utf-8"))
        self.assertFalse(f["ok"])
        self.assertIn("Auftragsart", f["fehler"])
        self.assertEqual(list((self.q / "auftraege").iterdir()), [])
        self.assertEqual(list((self.q / "in_arbeit").iterdir()), [])

    def test_5_trocken_und_pruefung(self):
        self.auftrag("auftrag-0003", {"id": "auftrag-0003", "art": "suche", "frage": "x", "max_seiten": 1})
        self.assertEqual(self.agent.ein_durchlauf(trocken=True), 1)
        self.assertTrue((self.q / "auftraege" / "auftrag-0003.json").exists())        # bleibt liegen
        self.assertEqual((self.geholt, list((self.q / "ergebnisse").iterdir())), ([], []))
        with self.assertRaises(ValueError):
            pruefe_auftrag({"id": "auftrag-0004", "art": "suche", "frage": "x" * 301})
        with self.assertRaises(ValueError):
            pruefe_auftrag({"id": "A B", "art": "suche", "frage": "x"})


class TestTrennung(unittest.TestCase):
    def test_6_kein_lunacode_und_compose(self):
        for datei in (ROOT / "netz_agent").glob("*.py"):
            for knoten in ast.walk(ast.parse(datei.read_text(encoding="utf-8"))):
                namen = [a.name for a in knoten.names] if isinstance(knoten, ast.Import) else \
                    [knoten.module or ""] if isinstance(knoten, ast.ImportFrom) else []
                self.assertFalse([n for n in namen if n.startswith(("orchestrator", "backoffice", "cutter"))], datei)
        compose = (ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")
        block = re.search(r"\n  luna-netz:\n(.*?)(?=\n  [a-z]|\Z)", compose, re.S)
        self.assertIsNotNone(block, "Dienst luna-netz fehlt")
        b = block.group(1)
        mounts = re.findall(r"^\s+- (/volume1/\S+)$", b, re.M)
        self.assertEqual(sorted(m.split(":")[0].rsplit("/", 1)[1] for m in mounts if ":/app/" in m), ["netz_agent", "netz_queue"])
        self.assertIn("netz_agent:ro", b)
        self.assertNotIn("orchestrator/.env", b)
        self.assertIn("netz_agent/.env", b)
        self.assertNotIn("ports:", b)
        self.assertIn("read_only: true", b)
        self.assertIn("no-new-privileges", b)


if __name__ == "__main__":
    unittest.main()
