"""App-Wissen (Phase 17, M2) — LUNA kennt die installierten Programme und wofuer sie taugen.

Scannt die installierten macOS-Apps und fuehrt eine **automatisch aktualisierte** Markdown-Registry
(`runner/app_register.md`): App -> wofuer gut -> wie steuerbar. Bei neu installierten Programmen wird die
Registry beim naechsten Scan aktualisiert. LUNA leitet daraus ab, welche App ideal fuer eine Aufgabe ist.

Die kuratierten Faehigkeits-Hinweise (`CAPABILITY_HINTS`) sind committet; die generierte `.md` ist
maschinenspezifisch (gitignored). Auf Nicht-macOS liefert der Scan eine leere Liste (kein Crash).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_APP_DIRS = ["/Applications", "/System/Applications", os.path.expanduser("~/Applications")]
_REGISTER_PATH = Path(__file__).resolve().parent / "app_register.md"

# Kuratierte Faehigkeits-Hinweise: Schluessel = Teilstring des App-Namens (lower).
# zweck = wofuer die App gut ist; steuerung = wie LUNA sie ansteuern kann; schlagworte = fuer Empfehlung.
CAPABILITY_HINTS: dict[str, dict] = {
    "textedit": {"zweck": "Einfache Texte/Notizen schreiben, .txt/.rtf",
                 "steuerung": "AppleScript (reich) — Dokument anlegen + Text setzen",
                 "schlagworte": ["text", "notiz", "schreiben", "tippen", "txt"]},
    "notes": {"zweck": "Notizen, kurze Listen, Sync ueber iCloud",
              "steuerung": "AppleScript — neue Notiz anlegen", "schlagworte": ["notiz", "merken", "liste"]},
    "mail": {"zweck": "E-Mails verfassen/lesen (Senden bleibt CEO-Tor)",
             "steuerung": "AppleScript (reich) — Entwurf anlegen; Senden gesperrt",
             "schlagworte": ["mail", "email", "nachricht", "anschreiben"]},
    "safari": {"zweck": "Webseiten oeffnen/lesen",
               "steuerung": "AppleScript/URL — Tab oeffnen; Klicks via Accessibility",
               "schlagworte": ["web", "browser", "seite", "recherche", "internet"]},
    "google chrome": {"zweck": "Webseiten oeffnen/lesen, Web-Apps",
                      "steuerung": "AppleScript/URL; Klicks via Accessibility",
                      "schlagworte": ["web", "browser", "chrome", "seite"]},
    "finder": {"zweck": "Dateien/Ordner verwalten",
               "steuerung": "AppleScript — oeffnen/verschieben (Loeschen = CEO-Tor)",
               "schlagworte": ["datei", "ordner", "verschieben", "finder"]},
    "calendar": {"zweck": "Termine ansehen/anlegen",
                 "steuerung": "AppleScript / Google-Kalender-Tools (LUNA)",
                 "schlagworte": ["termin", "kalender", "datum"]},
    "reminders": {"zweck": "Erinnerungen/To-dos",
                  "steuerung": "AppleScript — Erinnerung anlegen", "schlagworte": ["erinnerung", "todo", "aufgabe"]},
    "pages": {"zweck": "Formatierte Dokumente",
              "steuerung": "AppleScript (begrenzt)", "schlagworte": ["dokument", "brief", "layout"]},
    "numbers": {"zweck": "Tabellen/Kalkulation",
                "steuerung": "AppleScript (begrenzt)", "schlagworte": ["tabelle", "rechnen", "kalkulation"]},
    "keynote": {"zweck": "Praesentationen",
                "steuerung": "AppleScript", "schlagworte": ["praesentation", "folien", "slides"]},
    "xmind": {"zweck": "Mindmaps / Prozess-Knoten",
              "steuerung": "Accessibility/cliclick (schwaches AppleScript) oder Datei (.xmind)",
              "schlagworte": ["mindmap", "knoten", "prozess", "ast", "xmind"]},
    "terminal": {"zweck": "Shell-Befehle",
                 "steuerung": "Nur mit ausdruecklicher Freigabe (riskant)", "schlagworte": ["shell", "befehl", "terminal"]},
}


def is_macos() -> bool:
    return sys.platform == "darwin"


def scan_installed_apps() -> list[str]:
    """Namen installierter .app-Bundles (ohne .app). Leer auf Nicht-macOS."""
    if not is_macos():
        return []
    found: set[str] = set()
    for d in _APP_DIRS:
        try:
            for entry in os.listdir(d):
                if entry.endswith(".app"):
                    found.add(entry[:-4])
        except FileNotFoundError:
            continue
        except Exception:
            continue
    return sorted(found)


def _hint_for(app_name: str) -> dict | None:
    low = app_name.lower()
    for key, hint in CAPABILITY_HINTS.items():
        if key in low:
            return hint
    return None


def build_register() -> dict:
    """Verbindet Scan + kuratierte Hinweise zu einer Registry-Struktur."""
    apps = scan_installed_apps()
    bekannt, unbekannt = [], []
    for name in apps:
        hint = _hint_for(name)
        if hint:
            bekannt.append({"app": name, "zweck": hint["zweck"], "steuerung": hint["steuerung"]})
        else:
            unbekannt.append(name)
    return {"installiert": len(apps), "bekannt": bekannt, "unbekannt": unbekannt}


def write_register_md(path: Path | None = None) -> Path:
    """Schreibt/aktualisiert die Markdown-Registry. Gibt den Pfad zurueck."""
    from datetime import datetime
    path = Path(path) if path else _REGISTER_PATH
    reg = build_register()
    lines = [
        "# App-Registry — LUNA am Mac (automatisch erzeugt)",
        "",
        "> Generiert von `runner/capabilities.py`. Maschinenspezifisch (nicht versioniert).",
        f"> Stand: {datetime.now().strftime('%Y-%m-%d %H:%M')} — {reg['installiert']} Apps installiert.",
        "",
        "## Bekannte Apps (mit Faehigkeits-Hinweis)",
        "",
        "| App | Wofuer | Steuerung |",
        "|-----|--------|-----------|",
    ]
    for x in reg["bekannt"]:
        lines.append(f"| {x['app']} | {x['zweck']} | {x['steuerung']} |")
    lines += ["", "## Weitere installierte Apps (noch ohne Hinweis)", ""]
    lines.append(", ".join(reg["unbekannt"]) if reg["unbekannt"] else "(keine)")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def recommend_for(aufgabe: str) -> list[dict]:
    """Schlaegt installierte Apps vor, die zur Aufgabe passen (Schlagwort-Treffer)."""
    text = (aufgabe or "").lower()
    if not text:
        return []
    installed = {a.lower(): a for a in scan_installed_apps()}
    treffer = []
    for key, hint in CAPABILITY_HINTS.items():
        if any(w in text for w in hint["schlagworte"]):
            app = next((orig for low, orig in installed.items() if key in low), None)
            treffer.append({"app": app or key.title(), "installiert": app is not None,
                            "zweck": hint["zweck"], "steuerung": hint["steuerung"]})
    treffer.sort(key=lambda t: not t["installiert"])  # installierte zuerst
    return treffer
