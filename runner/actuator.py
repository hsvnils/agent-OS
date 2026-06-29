"""Aktuator (Phase 17, M3) — LUNA bedient den Mac, hinter vier Schutzschichten.

Schutzschichten vor JEDER Aktion (Governance, AGENTS.md/autonomie-stufen.md):
1. **Allowlist (Least-Privilege):** nur explizit freigegebene App + Verb. Start: nur TextEdit/text_schreiben.
2. **Vorschau -> Bestaetigung:** Standardmodus „bestaetigen" liefert erst eine Vorschau; Ausfuehrung erst
   nach CEO-Ja. Modus „sofort" ueberspringt die Bestaetigung NUR fuer benigne, umkehrbare Aktionen —
   **CEO-Tor-Kategorien (Geld/Recht/Oeffentlichkeit/Loeschen) werden IMMER bestaetigt.**
3. **Not-Aus:** `~/.luna_orb_killswitch` (vom Orb gesetzt) sperrt jede Aktion.
4. **Audit:** jede Vorschau/Ausfuehrung wird protokolliert (aktivitaet/log.jsonl, ueber den Tool-Handler).

Auf Nicht-macOS verweigert der Aktuator kontrolliert (kein Eingriff), damit die NAS-LUNA unangetastet bleibt.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

_TIMEOUT = 15
KILLSWITCH_PATH = Path(os.path.expanduser("~/.luna_orb_killswitch"))
MODE_PATH = Path(os.path.expanduser("~/.luna_orb_mode"))

MODE_CONFIRM = "bestaetigen"
MODE_INSTANT = "sofort"

# Allowlist: App -> Verb -> Spezifikation. kategorie: 'benign' (umkehrbar) | 'ceo_tor' (immer bestaetigen).
ALLOWLIST: dict[str, dict[str, dict]] = {
    "TextEdit": {
        "text_schreiben": {
            "kategorie": "benign",
            "beschreibung": "Neues TextEdit-Dokument anlegen und Text einfuegen (umkehrbar).",
        },
    },
}


def is_macos() -> bool:
    return sys.platform == "darwin"


# -- Modus (zwei Modi, vom CEO umschaltbar) --

def get_mode() -> str:
    try:
        m = MODE_PATH.read_text(encoding="utf-8").strip().lower()
    except Exception:
        m = ""
    return MODE_INSTANT if m == MODE_INSTANT else MODE_CONFIRM


def set_mode(mode: str) -> str:
    m = MODE_INSTANT if (mode or "").strip().lower() in (MODE_INSTANT, "instant", "auto", "direkt") else MODE_CONFIRM
    try:
        MODE_PATH.write_text(m + "\n", encoding="utf-8")
    except Exception:
        pass
    return m


# -- Not-Aus --

def is_stopped() -> bool:
    return KILLSWITCH_PATH.exists()


# -- Allowlist-Pruefung --

def allowed(app: str, verb: str) -> dict | None:
    return ALLOWLIST.get(app, {}).get(verb)


def allowlist_text() -> str:
    teile = []
    for app, verbs in ALLOWLIST.items():
        teile.append(f"{app}: " + ", ".join(verbs.keys()))
    return " | ".join(teile)


# -- Planung + Ausfuehrung --

def plan(app: str, verb: str, inhalt: str) -> dict:
    """Prueft Schutzschichten und entscheidet, ob bestaetigt werden muss. Fuehrt NICHT aus."""
    if not is_macos():
        return {"ok": False, "grund": "Aktuator nur am Mac verfuegbar."}
    if is_stopped():
        return {"ok": False, "grund": "NOT-AUS aktiv — Steuerung gesperrt. Erst im Orb aufheben."}
    spec = allowed(app, verb)
    if spec is None:
        return {"ok": False, "grund": f"Nicht in der Allowlist. Erlaubt: {allowlist_text()}",
                "allowlist": allowlist_text()}
    kategorie = spec.get("kategorie", "benign")
    mode = get_mode()
    # CEO-Tor IMMER bestaetigen; benigne nur im Bestaetigen-Modus.
    confirm_required = (kategorie == "ceo_tor") or (mode != MODE_INSTANT)
    return {"ok": True, "app": app, "verb": verb, "inhalt": inhalt, "kategorie": kategorie,
            "modus": mode, "bestaetigung_noetig": confirm_required,
            "beschreibung": spec.get("beschreibung", "")}


def execute(app: str, verb: str, inhalt: str) -> dict:
    """Fuehrt die (zuvor geplante + freigegebene) Aktion aus."""
    if not is_macos():
        return {"ausgefuehrt": False, "grund": "nur am Mac"}
    if is_stopped():
        return {"ausgefuehrt": False, "grund": "NOT-AUS aktiv"}
    if allowed(app, verb) is None:
        return {"ausgefuehrt": False, "grund": "nicht in Allowlist"}
    if app == "TextEdit" and verb == "text_schreiben":
        return _textedit_schreiben(inhalt)
    return {"ausgefuehrt": False, "grund": "Verb nicht implementiert"}


def _ensure_running(app: str, sekunden: float = 3.0) -> bool:
    """Startet die App (LaunchServices) und wartet, bis ihr Prozess laeuft."""
    subprocess.run(["open", "-a", app], capture_output=True, text=True, timeout=_TIMEOUT)
    deadline = time.time() + sekunden
    while time.time() < deadline:
        if subprocess.run(["pgrep", "-x", app], capture_output=True).returncode == 0:
            return True
        time.sleep(0.2)
    return False


def _textedit_schreiben(inhalt: str) -> dict:
    if not _ensure_running("TextEdit"):
        return {"ausgefuehrt": False, "grund": "TextEdit liess sich nicht starten."}
    # Text wird als argv uebergeben (keine AppleScript-Injection ueber String-Interpolation).
    script = (
        "on run argv\n"
        "set theText to item 1 of argv\n"
        'tell application "TextEdit"\n'
        "  activate\n"
        "  make new document with properties {text:theText}\n"
        "end tell\n"
        "end run"
    )
    try:
        p = subprocess.run(["osascript", "-e", script, inhalt],
                           capture_output=True, text=True, timeout=_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"ausgefuehrt": False, "grund": "timeout (evtl. Berechtigungsdialog fuer Automation)."}
    except Exception as exc:  # pragma: no cover
        return {"ausgefuehrt": False, "grund": str(exc)[:200]}
    if p.returncode != 0:
        return {"ausgefuehrt": False, "grund": (p.stderr or "osascript-Fehler").strip()[:300]}
    return {"ausgefuehrt": True, "app": "TextEdit", "zeichen": len(inhalt)}
