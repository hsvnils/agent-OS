"""Telegram-Meldung des Cutter Agents (V2): fertiges Reel an den CEO-Chat schicken.

Nutzt dasselbe Bot-Token wie LUNA (Senden ist zustandslos -- kollidiert NICHT mit dem NAS-Poller,
nur EIN getUpdates-Poller darf laufen, aber Senden duerfen mehrere). Die Meldung erscheint im
LUNA-Chat. Posten auf Instagram bleibt CEO-Tor -- hier geht die Datei nur an den CEO selbst.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

API = "https://api.telegram.org"


def sende_reel(token: str, chat_id: str, video: Path, caption: str = "") -> bool:
    """Sendet das fertige Reel als Video an den CEO-Chat. <=50 MB (Bot-API-Limit)."""
    if not token or not chat_id or not Path(video).exists():
        return False
    grenze = "----cutter" + uuid.uuid4().hex
    teile: list[bytes] = []

    def feld(name: str, wert: str):
        teile.append(f"--{grenze}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                     f"{wert}\r\n".encode())

    feld("chat_id", str(chat_id))
    if caption:
        feld("caption", caption[:1000])
    feld("supports_streaming", "true")
    teile.append((f"--{grenze}\r\nContent-Disposition: form-data; name=\"video\"; "
                  f"filename=\"{Path(video).name}\"\r\nContent-Type: video/mp4\r\n\r\n").encode())
    teile.append(Path(video).read_bytes())
    teile.append(f"\r\n--{grenze}--\r\n".encode())
    req = urllib.request.Request(
        f"{API}/bot{token}/sendVideo", data=b"".join(teile),
        headers={"Content-Type": f"multipart/form-data; boundary={grenze}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception:
        return False


def sende_text(token: str, chat_id: str, text: str) -> bool:
    if not token or not chat_id:
        return False
    data = urllib.parse.urlencode({"chat_id": str(chat_id), "text": text[:4000]}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{API}/bot{token}/sendMessage", data=data),
                                    timeout=30) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception:
        return False
