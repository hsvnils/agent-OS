"""Bruecke Server -> Orb (Phase 17, M5/#3). Schickt native Steuer-Befehle (Tastatur/Maus) an den Orb.

Tastatur/Maus brauchen die Berechtigung Bedienungshilfen — die hat NUR der Orb-`.app`, nicht der
terminal-gestartete Server. Darum legt der Server Befehle als Dateien in `~/.luna_orb/` ab; der Orb
fuehrt sie aus und schreibt das Ergebnis zurueck. Einfache, robuste Datei-Queue (kein Port).
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

DIR = Path(os.path.expanduser("~/.luna_orb"))


def sende(typ: str, timeout: float = 6.0, **kw) -> dict:
    """Schickt einen Befehl an den Orb und wartet auf das Ergebnis. {ok, grund?}."""
    try:
        DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return {"ok": False, "grund": f"Queue-Verzeichnis nicht anlegbar: {str(exc)[:120]}"}
    uid = uuid.uuid4().hex
    cmd = {"typ": typ}
    cmd.update(kw)
    cmd_path = DIR / f"cmd-{uid}.json"
    res_path = DIR / f"res-{uid}.json"
    try:
        cmd_path.write_text(json.dumps(cmd), encoding="utf-8")
    except Exception as exc:
        return {"ok": False, "grund": f"Befehl nicht schreibbar: {str(exc)[:120]}"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        if res_path.exists():
            try:
                data = json.loads(res_path.read_text(encoding="utf-8"))
            except Exception:
                data = {"ok": False, "grund": "Ergebnis unlesbar."}
            try:
                res_path.unlink()
            except Exception:
                pass
            return data
        time.sleep(0.1)
    # Aufraeumen, falls der Orb nicht laeuft.
    try:
        cmd_path.unlink()
    except Exception:
        pass
    return {"ok": False, "grund": "Der LUNA Orb antwortet nicht. Laeuft die App und ist die Steuerung "
                                  "(Bedienungshilfen) erlaubt?"}
