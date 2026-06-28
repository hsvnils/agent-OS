"""On-Screen-Awareness (Phase 17, M2) — LUNA „sieht", was auf dem Mac los ist.

L1-Wahrnehmung ueber macOS-Bordmittel (osascript/System Events): welche App ist vorne, welcher
Fenstertitel, welche Apps laufen. Kein Eingriff, nur Lesen. Auf Nicht-macOS degradiert alles zu
`verfuegbar=False` (keine Exception), damit die NAS-LUNA unangetastet bleibt.

Tiefe Wahrnehmung (Screenshot/Accessibility-Baum) liefert spaeter die native Swift-App (saubere
Permissions am .app-Bundle) bzw. Claude Computer-Use; hier bleibt es bei strukturiertem App-Kontext.
"""
from __future__ import annotations

import subprocess
import sys

_TIMEOUT = 5


def is_macos() -> bool:
    return sys.platform == "darwin"


def _osascript(script: str) -> tuple[bool, str]:
    """Fuehrt ein AppleScript aus. (ok, ausgabe-oder-fehler)."""
    if not is_macos():
        return False, "nicht-macOS"
    try:
        p = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, ("timeout — vermutlich offener Berechtigungsdialog (Automation/Bedienungshilfen "
                       "fuer die ausfuehrende App noch nicht erlaubt).")
    except Exception as exc:  # pragma: no cover - Systemfehler
        return False, str(exc)[:200]
    if p.returncode != 0:
        return False, (p.stderr or "osascript-Fehler").strip()[:300]
    return True, (p.stdout or "").strip()


def frontmost_app() -> dict:
    """Vorderste App + Fenstertitel. {verfuegbar, app, fenster, hinweis?}."""
    if not is_macos():
        return {"verfuegbar": False, "hinweis": "On-Screen-Awareness nur am Mac verfuegbar."}
    script = (
        'tell application "System Events"\n'
        '  set frontApp to name of first application process whose frontmost is true\n'
        '  set winTitle to ""\n'
        '  try\n'
        '    tell process frontApp to set winTitle to name of front window\n'
        '  end try\n'
        'end tell\n'
        'return frontApp & "||" & winTitle'
    )
    ok, out = _osascript(script)
    if not ok:
        return {"verfuegbar": False, "hinweis": _permission_hint(out)}
    app, _, fenster = out.partition("||")
    return {"verfuegbar": True, "app": app.strip(), "fenster": fenster.strip()}


def running_apps() -> dict:
    """Sichtbar laufende Apps (keine Hintergrunddienste). {verfuegbar, apps}."""
    if not is_macos():
        return {"verfuegbar": False, "apps": []}
    script = (
        'tell application "System Events" to get name of every application process '
        'whose background only is false'
    )
    ok, out = _osascript(script)
    if not ok:
        return {"verfuegbar": False, "apps": [], "hinweis": _permission_hint(out)}
    apps = [a.strip() for a in out.split(",") if a.strip()]
    return {"verfuegbar": True, "apps": sorted(set(apps))}


def snapshot() -> dict:
    """Kompakter Wahrnehmungs-Schnappschuss fuer LUNA (vorne + laufende Apps)."""
    front = frontmost_app()
    runs = running_apps()
    return {
        "verfuegbar": front.get("verfuegbar", False) or runs.get("verfuegbar", False),
        "vordergrund": front,
        "laufende_apps": runs.get("apps", []),
        "hinweis": front.get("hinweis") or runs.get("hinweis"),
    }


def _permission_hint(err: str) -> str:
    low = (err or "").lower()
    if ("not allowed" in low or "assistive" in low or "1002" in low or "accessibility" in low
            or "timeout" in low or "-1743" in low):
        return ("Berechtigung fehlt: System-Einstellungen -> Datenschutz & Sicherheit -> "
                "Bedienungshilfen/Automation fuer die ausfuehrende App (bzw. den LUNA-Orb) freigeben.")
    return f"Konnte den Bildschirm-Kontext nicht lesen: {err}"
