"""CLI: python -m cutter <ordner> [Optionen] -- schneidet einen Ordner zu einem Reel."""
from __future__ import annotations

import argparse
import json
import sys

from .pipeline import schneide_ordner


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Cutter Agent -- Ordner mit Clips -> Instagram-Reel (9:16).")
    p.add_argument("ordner", help="Ordner mit den Clips.")
    p.add_argument("--ausgabe", default=None, help="Ziel-MP4 (Default: <ordner>/<name>_reel.mp4).")
    p.add_argument("--dauer", type=float, default=45.0, help="Ziel-Gesamtlaenge in Sekunden (Default 45).")
    p.add_argument("--ohne-gemini", action="store_true", help="Keine KI-Reihenfolge (Dateiname-Reihenfolge).")
    p.add_argument("--ohne-transkript", action="store_true", help="Keine Transkription/Untertitel.")
    a = p.parse_args(argv)

    bericht = schneide_ordner(a.ordner, a.ausgabe, ziel_dauer=a.dauer,
                              transkribieren=not a.ohne_transkript, gemini=not a.ohne_gemini)
    print(json.dumps(bericht, ensure_ascii=False, indent=2))
    return 0 if bericht.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
