"""BF-94: Telegram muss die echten Masse des Reels bekommen, sonst zerrt die App das Bild."""
from __future__ import annotations

import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cutter import ffmpeg_ops as fo
from cutter import melden


def _felder(body: bytes) -> dict[str, str]:
    text = body.decode("latin-1")
    return dict(re.findall(r'name="(\w+)"\r\n\r\n(.*?)\r\n', text))


class Masse(unittest.TestCase):
    def _sende(self, info):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f, \
                mock.patch.object(fo, "probe", return_value=info), \
                mock.patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps({"ok": True}).encode())) as url:
            self.assertTrue(melden.sende_reel("t", "1", Path(f.name), "c"))
        return _felder(url.call_args[0][0].data)

    def test_hochformat_wird_mitgeschickt(self):
        f = self._sende(fo.ClipInfo(Path("x"), 41.4, True, 1080, 1920))
        self.assertEqual((f["width"], f["height"], f["duration"]), ("1080", "1920", "41"))

    def test_ohne_messung_trotzdem_versand_ohne_falsche_masse(self):
        f = self._sende(None)
        self.assertNotIn("width", f)
        self.assertNotIn("height", f)
        self.assertEqual(f["chat_id"], "1")


if __name__ == "__main__":
    unittest.main()
