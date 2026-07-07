"""Reel-Pipeline (optional) -- Gemini-Video-Content-Tagging fuer den Clip-Index (CEO-Tor).

Laesst die Gemini-Video-KI die noch ungetaggten Clips ANSEHEN und vergibt Inhalts-Tags (tor/jubel/choreo/…)
ins Index-Feld `themen`. Damit kann die Tages-Auswahl (`reel_select`) gezielt zum Tagesthema passende Clips
bevorzugen -- echte Inhaltserkennung statt nur Audio-Energie-Proxy.

**Standardmaessig AUS.** Laeuft nur mit `CUTTER_VIDEO_KI=1` UND `GEMINI_API_KEY`. Sendet 360p-Proxys der
Clips an Google (Paid-Tier). Kosten grob ~0,1-0,3 Cent je Clip, einmalig (Ergebnis wird im Index gecacht);
Fan-Clips zeigen erkennbare Personen -> bewusste CEO-Entscheidung. Bei jedem Fehler wird die Charge
uebersprungen (nie Absturz); der Clip bleibt ungetaggt und wird beim naechsten Lauf erneut versucht.

CLI:  python -m cutter.reel_tag --state <REEL_STATE> [--charge 8] [--max 0]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from . import reel_source as rq
from .pipeline import _lade_env


def tagge_index(state: Path, *, charge: int = 8, max_clips: int = 0) -> dict:
    """Taggt ungetaggte Clips im Index via Gemini-Video-KI. Gibt {ok, getaggt, offen} bzw. {ok:false, hinweis}."""
    env = _lade_env()
    if str(env.get("CUTTER_VIDEO_KI", "")).strip().lower() not in ("1", "true", "yes", "on"):
        return {"ok": False, "hinweis": "CUTTER_VIDEO_KI ist nicht aktiv (CEO-Tor: Clips gehen zu Google)."}
    key = env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        return {"ok": False, "hinweis": "GEMINI_API_KEY fehlt."}

    from .gemini_video import GeminiVideoClient, tags_via_video
    index_pfad = Path(state) / "clip_index.json"
    clips = rq.lade_index(index_pfad)
    if not clips:
        return {"ok": False, "hinweis": "Clip-Index leer -- erst den Index bauen (reel_daily/reel_source)."}
    offen = [c for c in clips if not c.get("themen")]
    if max_clips:
        offen = offen[:max_clips]
    if not offen:
        return {"ok": True, "getaggt": 0, "offen": 0, "hinweis": "Alle Clips bereits getaggt."}

    client = GeminiVideoClient(key, model=(env.get("CUTTER_VIDEO_MODEL") or "gemini-2.5-flash-lite"))
    per_pfad: dict[str, list] = {}
    for i in range(0, len(offen), max(1, charge)):
        res = tags_via_video([c["pfad"] for c in offen[i:i + charge]], client)
        if res:
            per_pfad.update(res)

    for c in clips:                                        # Tags zurueck in den Index (Cache)
        if c["pfad"] in per_pfad:
            c["themen"] = per_pfad[c["pfad"]]
    index_pfad.write_text(json.dumps({"stand": time.strftime("%Y-%m-%dT%H:%M:%S"), "clips": clips},
                                     ensure_ascii=False, indent=2), "utf-8")
    return {"ok": True, "getaggt": len(per_pfad), "offen": len(offen) - len(per_pfad)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Reel-Pipeline -- Gemini-Video-Content-Tagging (opt-in, CEO-Tor).")
    p.add_argument("--state", default=None, help="Status-Verzeichnis mit clip_index.json. Env REEL_STATE.")
    p.add_argument("--charge", type=int, default=8, help="Clips je Gemini-Anfrage (Default 8).")
    p.add_argument("--max", type=int, default=0, help="Max. Clips diesen Lauf taggen (0 = alle offenen).")
    a = p.parse_args(argv)
    state = Path(a.state).expanduser() if a.state else Path(os.environ.get("REEL_STATE", "~/ReelState")).expanduser()
    res = tagge_index(state, charge=a.charge, max_clips=a.max)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
