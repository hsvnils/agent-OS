import types
import unittest
from pathlib import Path

from cutter.gemini_video import _parse_order, reihenfolge_via_video


def _auswahl(name, typ="sprache"):
    return types.SimpleNamespace(clip=types.SimpleNamespace(pfad=Path(name)), typ=typ, transkript=[])


class FakeClient:
    """Simuliert die Gemini-Video-API ohne Netz."""

    def __init__(self, order_text="[0]", *, fail_upload=False, fail_active=False):
        self.order_text = order_text
        self.fail_upload = fail_upload
        self.fail_active = fail_active
        self.uploaded = []

    def upload(self, pfad, mime="video/mp4"):
        if self.fail_upload:
            return None
        self.uploaded.append(pfad)
        return {"uri": f"files/{len(self.uploaded)}", "name": f"files/{len(self.uploaded)}", "mime": mime}

    def warte_aktiv(self, name, **kw):
        return not self.fail_active

    def generate(self, parts):
        self.letzte_parts = parts
        return self.order_text


class TestParseOrder(unittest.TestCase):
    def test_saubere_liste(self):
        self.assertEqual(_parse_order("[2,0,1]", 3), [2, 0, 1])

    def test_text_drumherum(self):
        self.assertEqual(_parse_order("Reihenfolge: [1,0]. Fertig.", 2), [1, 0])

    def test_ungueltige_und_doppelte_indizes_gefiltert(self):
        self.assertEqual(_parse_order("[2,0,5,0,1]", 3), [2, 0, 1])   # 5 out of range, 0 doppelt

    def test_kein_json(self):
        self.assertIsNone(_parse_order("keine liste hier", 3))

    def test_leere_gueltige_liste_ist_none(self):
        self.assertIsNone(_parse_order("[9,10]", 3))                  # nichts im Bereich -> None


class TestReihenfolgeViaVideo(unittest.TestCase):
    def setUp(self):
        self.aus = [_auswahl("a.mp4"), _auswahl("b.mp4", "broll"), _auswahl("c.mp4")]

    def test_ok_reihenfolge(self):
        client = FakeClient("[2,0,1]")
        order = reihenfolge_via_video(self.aus, client, downsample=False)
        self.assertEqual(order, [2, 0, 1])
        self.assertEqual(len(client.uploaded), 3)                    # alle Clips hochgeladen

    def test_upload_fehler_faellt_zurueck(self):
        self.assertIsNone(reihenfolge_via_video(self.aus, FakeClient(fail_upload=True), downsample=False))

    def test_datei_nicht_aktiv_faellt_zurueck(self):
        self.assertIsNone(reihenfolge_via_video(self.aus, FakeClient(fail_active=True), downsample=False))

    def test_unbrauchbare_antwort_ist_none(self):
        self.assertIsNone(reihenfolge_via_video(self.aus, FakeClient("weiss nicht"), downsample=False))

    def test_parts_enthalten_video_und_prompt(self):
        client = FakeClient("[0,1,2]")
        reihenfolge_via_video(self.aus, client, downsample=False)
        arten = [("file_data" in p) for p in client.letzte_parts]
        self.assertEqual(sum(arten), 3)                              # drei Video-Parts
        self.assertIn("JSON-Liste", client.letzte_parts[-1]["text"])  # Abschluss-Prompt


if __name__ == "__main__":
    unittest.main()
