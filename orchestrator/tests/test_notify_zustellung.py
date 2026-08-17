"""Regressionstests fuer die proaktive Zustellung.

Hintergrund (17.08.2026): Im Zustellblock von `main()` wurde `tz` benutzt, aber nie zugewiesen. Der
NameError landete im umgebenden `except` -- **fuenf Wochen lang** (09.07.-17.08.) wurde keine einzige
proaktive Meldung zugestellt, 1106 Stueck stapelten sich in der Outbox. Nach aussen sah alles normal aus:
Die Meldungen wurden brav erzeugt, nur nie verschickt. Genau diese Stille pruefen die Tests hier.
"""
import ast
import pathlib
import tempfile
import unittest
from datetime import datetime, timedelta

from orchestrator.core.notifications import Notifications

BOT = pathlib.Path(__file__).resolve().parents[1] / "channels" / "telegram" / "bot.py"


class TestKeineUndefiniertenNamen(unittest.TestCase):
    """Jede Funktion in bot.py muss die Namen, die sie liest, auch selbst binden (oder aus dem Modul
    beziehen). Der teuerste Fehler dieses Projekts war genau so ein freier Name in einem try-Block."""

    def _modul(self):
        return ast.parse(BOT.read_text("utf-8"))

    def _gebunden(self, fn) -> set:
        namen = set(a.arg for a in fn.args.args + fn.args.kwonlyargs)
        for x in ast.walk(fn):
            if isinstance(x, (ast.Import, ast.ImportFrom)):
                namen.update((a.asname or a.name).split(".")[0] for a in x.names)
            elif isinstance(x, ast.Name) and isinstance(x.ctx, (ast.Store, ast.Del)):
                namen.add(x.id)
            elif isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                namen.add(x.name)
            elif isinstance(x, (ast.Global, ast.Nonlocal)):
                namen.update(x.names)
            elif isinstance(x, ast.ExceptHandler) and x.name:
                namen.add(x.name)
        return namen

    def test_main_bindet_tz(self):
        modul = self._modul()
        modulweit = {n.id for x in modul.body if isinstance(x, ast.Assign)      # nur echte Modul-Ebene
                     for n in ast.walk(x.targets[0]) if isinstance(n, ast.Name)}
        for fn in modul.body:
            if isinstance(fn, ast.FunctionDef) and fn.name == "main":
                nutzt_tz = any(isinstance(x, ast.Name) and x.id == "tz" for x in ast.walk(fn))
                self.assertTrue(nutzt_tz, "Zustellblock benutzt tz nicht mehr -- Test anpassen.")
                self.assertIn("tz", self._gebunden(fn) | modulweit,
                              "main() liest 'tz', bindet es aber nicht -> NameError verschluckt "
                              "saemtliche proaktiven Meldungen.")
                return
        self.fail("main() nicht gefunden")


class TestOutboxLawine(unittest.TestCase):
    def _store(self, d):
        return Notifications(pathlib.Path(d) / "log.jsonl")

    def test_alte_meldungen_werden_verworfen(self):
        with tempfile.TemporaryDirectory() as d:
            n = self._store(d)
            alt_id = n.enqueue("Uralte Warnung", kategorie="fehler")
            # Zeitstempel kuenstlich altern lassen
            p = pathlib.Path(d) / "log.jsonl"
            alt = (datetime.now() - timedelta(days=9)).isoformat(timespec="seconds")
            p.write_text(p.read_text("utf-8").replace(f'"ts": "{n._events()[0]["ts"]}"', f'"ts": "{alt}"'),
                         "utf-8")
            neu_id = n.enqueue("Frische Warnung", kategorie="fehler")
            self.assertEqual(n.verwerfe_alte(stunden=24), 1)
            offen = [e["id"] for e in n.pending()]
            self.assertEqual(offen, [neu_id])
            self.assertNotIn(alt_id, offen)

    def test_ohne_altlasten_passiert_nichts(self):
        with tempfile.TemporaryDirectory() as d:
            n = self._store(d)
            n.enqueue("Frisch", kategorie="info")
            self.assertEqual(n.verwerfe_alte(stunden=24), 0)
            self.assertEqual(len(n.pending()), 1)

    def test_kaputter_zeitstempel_gilt_als_alt(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "log.jsonl"
            p.write_text('{"ts": "kaputt", "id": "N-1", "typ": "queued", "text": "x"}\n', "utf-8")
            n = Notifications(p)
            self.assertEqual(n.verwerfe_alte(stunden=24), 1)
            self.assertEqual(n.pending(), [])


if __name__ == "__main__":
    unittest.main()
