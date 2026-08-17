"""Regressionstests fuer die proaktive Zustellung.

Hintergrund (17.08.2026): Im Zustellblock von `main()` wurde `tz` benutzt, aber nie zugewiesen. Der
NameError landete im umgebenden `except` -- **fuenf Wochen lang** (09.07.-17.08.) wurde keine einzige
proaktive Meldung zugestellt, 1106 Stueck stapelten sich in der Outbox. Nach aussen sah alles normal aus:
Die Meldungen wurden brav erzeugt, nur nie verschickt. Genau diese Stille pruefen die Tests hier.
"""
import ast
import builtins
import pathlib
import tempfile
import unittest
from datetime import datetime, timedelta

from orchestrator.core.notifications import Notifications

BOT = pathlib.Path(__file__).resolve().parents[1] / "channels" / "telegram" / "bot.py"


class TestKeineUndefiniertenNamen(unittest.TestCase):
    """`main()` muss jeden Namen, den es liest, auch binden -- sonst schluckt der `except` im Zustellblock
    einen NameError und LUNA verstummt lautlos.

    Der Fehler kam **zweimal hintereinander**: erst `tz`, nach dessen Reparatur `datetime` (beide werden
    in bot.py nur innerhalb anderer Funktionen importiert). Deshalb prueft dieser Test nicht mehr einzelne
    Namen, sondern **alle freien Namen** von `main()` gegen Modul-Ebene und Builtins.
    """

    SCOPE_KNOTEN = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)

    def _im_scope(self, rumpf):
        """Knoten dieses Geltungsbereichs -- **ohne** in verschachtelte Funktionen/Klassen abzusteigen.

        `ast.walk` taugt hier nicht: Es steigt in jeden Funktionsrumpf hinab und haette die
        `from datetime import datetime`-Zeilen der anderen Funktionen als modulweit gezaehlt -- der Test
        waere gruen geblieben, obwohl `main()` genau daran scheiterte."""
        for st in rumpf:
            yield st
            if isinstance(st, self.SCOPE_KNOTEN):
                continue                      # eigener Geltungsbereich -> nicht hineinsteigen
            for kind in ast.iter_child_nodes(st):
                yield from self._im_scope([kind])

    def _bindungen(self, rumpf) -> set:
        namen: set[str] = set()
        for x in self._im_scope(rumpf):
            if isinstance(x, (ast.Import, ast.ImportFrom)):
                namen.update((a.asname or a.name).split(".")[0] for a in x.names)
            elif isinstance(x, ast.Name) and isinstance(x.ctx, (ast.Store, ast.Del)):
                namen.add(x.id)
            elif isinstance(x, self.SCOPE_KNOTEN):
                namen.add(getattr(x, "name", ""))
            elif isinstance(x, (ast.Global, ast.Nonlocal)):
                namen.update(x.names)
            elif isinstance(x, ast.ExceptHandler) and x.name:
                namen.add(x.name)
        return namen

    def test_main_bindet_alle_gelesenen_namen(self):
        modul = ast.parse(BOT.read_text("utf-8"))
        main = next((f for f in modul.body if isinstance(f, ast.FunctionDef) and f.name == "main"), None)
        self.assertIsNotNone(main, "main() nicht gefunden")

        args = main.args
        eigene = {a.arg for a in args.args + args.posonlyargs + args.kwonlyargs}
        gebunden = (self._bindungen(main.body) | self._bindungen(modul.body) | eigene | set(dir(builtins)))
        gelesen = {x.id for x in self._im_scope(main.body)
                   if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)}
        frei = sorted(gelesen - gebunden)
        self.assertEqual(frei, [], f"main() liest ungebundene Namen -> NameError im Zustellblock: {frei}")


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
