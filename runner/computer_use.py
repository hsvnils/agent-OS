"""Generischer Sprach-Steuer-Loop (Phase 17, M6) — LUNA bedient den Mac „per Hingucken".

Das Iron-Man-Herzstueck: aus EINEM gesprochenen Ziel macht LUNA eine Kette atomarer Handgriffe, jeweils
**sehen -> entscheiden -> handeln -> wieder sehen**, bis das Ziel erreicht ist. Modell = Gemini-Vision
(gratis, kein Anthropic-Tor). Jede Aktion laeuft durch DASSELBE Tor wie der Aktuator (`runner/actuator.py`):
Not-Aus, Allowlist, Audit.

Verhalten (CEO-Wahl 2026-07-08, „Ansagen & handeln"): benigne, ungefaehrliche Schritte fuehrt LUNA direkt
aus und sagt jeden an. Sie **haelt an und fragt zurueck**, sobald der naechste Schritt

- **gefaehrlich/CEO-Tor** ist (Geld/Recht/Oeffentlichkeit/Loeschen: senden, loeschen, kaufen, posten, ...), oder
- die Modell-**Konfidenz zu niedrig** ist, oder
- das Modell selbst eine **Rueckfrage** stellt.

Harte Bremsen greifen immer: Not-Aus (`~/.luna_orb_killswitch`) stoppt sofort, `max_schritte` deckelt die
Kette, und gefaehrliche Schritte werden NIE automatisch ausgefuehrt.

Der Loop ist **dependency-injected** (Screenshot/Entscheidung/Ausfuehrung als Callables) -> reine Logik,
komplett ohne Mac/Gemini unit-testbar. Die Produktions-Verdrahtung (Orb-Screenshot, Gemini, Aktuator) sitzt
im Tool-Handler (`rechner_ziel`).
"""
from __future__ import annotations

import json
import re
from typing import Callable

# Erlaubte atomare Aktionen, die das Modell vorschlagen darf.
AKTIONEN = ("klick", "tippe", "taste", "oeffne_app", "fertig", "frage")

# Deckel + Schwellen (bewusst konservativ).
MAX_SCHRITTE_STD = 8
KONFIDENZ_SCHWELLE = 0.55
DECIDE_VERSUCHE = 3          # so oft neu fragen, wenn das Modell keine brauchbare Aktion liefert

# Toleranz gegen englische / synonyme Aktionsnamen (Modelle weichen manchmal vom Schema ab).
_ACTION_ALIAS = {
    "click": "klick", "tap": "klick",
    "type": "tippe", "tippen": "tippe", "write": "tippe", "input": "tippe",
    "key": "taste", "press": "taste", "hotkey": "taste", "shortcut": "taste", "keypress": "taste",
    "open": "oeffne_app", "open_app": "oeffne_app", "launch": "oeffne_app", "app_oeffnen": "oeffne_app",
    "oeffne": "oeffne_app", "starte": "oeffne_app",
    "done": "fertig", "finish": "fertig", "complete": "fertig", "finished": "fertig",
    "ask": "frage", "question": "frage",
}

# Woerter, die eine Aktion als gefaehrlich/CEO-Tor markieren (Geld/Recht/Oeffentlichkeit/Loeschen).
# Wird gegen das Ziel des Klicks/den Text/die Begruendung geprueft.
_GEFAHR_WORTE = (
    "loesch", "delete", "entfern", "papierkorb", "trash", "verwerf", "formatier", "deinstallier",
    "uninstall", "senden", "send", "abschicken", "absenden", "verschick", "posten", "post ",
    "veroeffentlich", "publish", "teilen", "share", "tweet", "kauf", "buy", "bestell", "bezahl",
    "pay", "checkout", "ueberweis", "transfer", "abo", "kuendig", "unwiderruflich", "permanently",
    "endgueltig", "zuruecksetzen", "reset", "werkseinstell", "passwort aendern", "logout", "abmelden",
)

# Tastenkuerzel, die fuer sich schon gefaehrlich sind (Loeschen/Beenden).
_GEFAHR_TASTEN = ("cmd+delete", "cmd+backspace", "cmd+shift+delete", "shift+delete", "cmd+q")


SYSTEM_HINWEIS = (
    "Du bist LUNAs Kopf am Mac. Du siehst einen Screenshot und sollst das Ziel des Nutzers Schritt fuer "
    "Schritt umsetzen. Antworte mit GENAU EINER naechsten atomaren Aktion als striktem JSON-Objekt, ohne "
    "Text drumherum. Felder: 'aktion' (einer von: klick, tippe, taste, oeffne_app, fertig, frage), "
    "'begruendung' (kurz, was du tust), 'konfidenz' (0..1). Je nach Aktion zusaetzlich: klick -> 'x','y' "
    "als NORMIERTE Koordinaten 0..1 (Bruchteil der Bildbreite/-hoehe, Ziel = Mitte des Elements); tippe -> "
    "'text'; taste -> 'kuerzel' (z. B. 'cmd+s','return','cmd+l'); oeffne_app -> 'app' (App-Name); fertig -> "
    "'ergebnis' (Ziel erreicht); frage -> 'text' (wenn du eine Info vom Nutzer brauchst). Waehle 'fertig', "
    "sobald das Ziel sichtbar erreicht ist. Erfinde keine Koordinaten, wenn das Element nicht sichtbar ist — "
    "dann lieber 'frage' oder scrolle via 'taste'."
)


def parse_aktion(text: str) -> dict | None:
    """Extrahiert das Aktions-JSON aus der Modellantwort (auch aus ```json-Bloecken). None bei kaputt/leer."""
    if not text:
        return None
    roh = text.strip()
    if "```" in roh:                                    # ```json ... ``` entpacken
        m = re.search(r"```(?:json)?\s*(.*?)```", roh, re.DOTALL)
        if m:
            roh = m.group(1).strip()
    if not roh.startswith("{"):                         # erstes JSON-Objekt herausschneiden
        i, j = roh.find("{"), roh.rfind("}")
        if i == -1 or j <= i:
            return None
        roh = roh[i:j + 1]
    try:
        d = json.loads(roh)
    except Exception:
        return None
    return d if isinstance(d, dict) else None


def validiere_aktion(d: dict) -> dict:
    """Prueft die geparste Aktion gegen das Schema. {ok, aktion?, ...} oder {ok:False, grund}."""
    if not isinstance(d, dict):
        return {"ok": False, "grund": "Keine Aktion."}
    art = str(d.get("aktion") or d.get("action") or "").strip().lower()
    art = _ACTION_ALIAS.get(art, art)
    if art not in AKTIONEN:
        return {"ok": False, "grund": f"Unbekannte Aktion '{art}'. Erlaubt: {', '.join(AKTIONEN)}."}
    try:
        konf = float(d.get("konfidenz", 1.0))
    except (TypeError, ValueError):
        konf = 1.0
    konf = max(0.0, min(1.0, konf))
    aus = {"ok": True, "aktion": art, "begruendung": str(d.get("begruendung", "")).strip()[:300],
           "konfidenz": konf}
    if art == "klick":
        try:
            x, y = float(d["x"]), float(d["y"])
        except (KeyError, TypeError, ValueError):
            return {"ok": False, "grund": "klick braucht normierte x,y (0..1)."}
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            return {"ok": False, "grund": "x,y muessen normiert sein (0..1)."}
        aus["x"], aus["y"] = x, y
    elif art == "tippe":
        text = str(d.get("text") or d.get("value") or d.get("input") or "")
        if not text:
            return {"ok": False, "grund": "tippe braucht 'text'."}
        aus["text"] = text
    elif art == "taste":
        kuerzel = str(d.get("kuerzel") or d.get("key") or d.get("shortcut") or d.get("hotkey") or "").strip()
        if not kuerzel:
            return {"ok": False, "grund": "taste braucht 'kuerzel'."}
        aus["kuerzel"] = kuerzel
    elif art == "oeffne_app":
        app = str(d.get("app") or d.get("app_name") or d.get("application") or "").strip()
        if not app:
            return {"ok": False, "grund": "oeffne_app braucht 'app'."}
        aus["app"] = app
    elif art == "fertig":
        aus["ergebnis"] = str(d.get("ergebnis", "")).strip()[:400]
    elif art == "frage":
        aus["text"] = str(d.get("text", "")).strip()[:400]
    return aus


def ist_gefaehrlich(aktion: dict) -> bool:
    """True, wenn die Aktion in eine CEO-Tor-Kategorie faellt (Geld/Recht/Oeffentlichkeit/Loeschen) und
    daher NIE automatisch ausgefuehrt werden darf. Prueft Tastenkuerzel + Begruendung/Text auf Gefahrwoerter."""
    art = aktion.get("aktion")
    if art == "taste":
        if aktion.get("kuerzel", "").lower().replace(" ", "") in _GEFAHR_TASTEN:
            return True
    heu = " ".join(str(aktion.get(k, "")) for k in ("begruendung", "text", "app")).lower()
    return any(w in heu for w in _GEFAHR_WORTE)


def map_klick(nx: float, ny: float, breite: int, hoehe: int) -> tuple[int, int]:
    """Normierte Koordinaten (0..1) -> Bildschirmpunkte. Geklemmt auf den sichtbaren Bereich."""
    x = int(round(max(0.0, min(1.0, nx)) * max(1, breite)))
    y = int(round(max(0.0, min(1.0, ny)) * max(1, hoehe)))
    return x, y


def beschreibe(aktion: dict) -> str:
    """Kurze deutsche Ansage der Aktion (fuer die Sprachausgabe)."""
    art = aktion.get("aktion")
    if art == "klick":
        return f"Ich klicke auf {aktion.get('begruendung') or 'das Element'}."
    if art == "tippe":
        return f"Ich tippe: {aktion.get('text', '')[:60]}"
    if art == "taste":
        return f"Ich druecke {aktion.get('kuerzel')}."
    if art == "oeffne_app":
        return f"Ich oeffne {aktion.get('app')}."
    if art == "fertig":
        return aktion.get("ergebnis") or "Fertig."
    if art == "frage":
        return aktion.get("text") or "Ich habe eine Rueckfrage."
    return "…"


def fuehre_ziel_aus(ziel: str, *, screenshot: Callable[[], dict], entscheide: Callable[[str, bytes, list], str],
                    handle: Callable[[dict, dict], dict], gestoppt: Callable[[], bool] = lambda: False,
                    max_schritte: int = MAX_SCHRITTE_STD,
                    konfidenz_schwelle: float = KONFIDENZ_SCHWELLE,
                    audit: Callable[[str, str], None] | None = None) -> dict:
    """Der Loop. Alle Aussenwelt-Zugriffe sind injiziert -> reine, testbare Logik.

    - `screenshot()` -> {ok, bild(bytes), breite, hoehe} | {ok:False, grund}
    - `entscheide(ziel, bild, verlauf)` -> Rohantwort des Vision-Modells (str)
    - `handle(aktion, shot)` -> {ausgefuehrt, ...} (fuehrt die konkrete, gegatete Aktion aus)
    - `gestoppt()` -> True, wenn Not-Aus aktiv
    - `audit(kurz, detail)` -> Protokoll (optional)

    Rueckgabe: {status, schritte:[...], ansage}. status in
    fertig | bestaetigung | frage | max_erreicht | gestoppt | fehler.
    """
    ziel = (ziel or "").strip()
    if not ziel:
        return {"status": "fehler", "schritte": [], "ansage": "Kein Ziel angegeben."}

    def _log(kurz: str, detail: str = "") -> None:
        if audit:
            try:
                audit(kurz, detail)
            except Exception:
                pass

    schritte: list[dict] = []
    verlauf: list[str] = []
    _log("Ziel-Loop gestartet", ziel[:200])
    for _ in range(max(1, int(max_schritte))):
        if gestoppt():
            return {"status": "gestoppt", "schritte": schritte,
                    "ansage": "Not-Aus aktiv — ich stoppe. Heb ihn im Orb auf, dann geht es weiter."}
        shot = screenshot() or {}
        if not shot.get("ok"):
            return {"status": "fehler", "schritte": schritte,
                    "ansage": f"Ich sehe den Bildschirm nicht: {shot.get('grund', 'kein Screenshot')}."}
        aktion = None
        for _versuch in range(max(1, DECIDE_VERSUCHE)):     # Modell liefert mal Prosa statt JSON -> neu fragen
            roh = entscheide(ziel, shot.get("bild") or b"", list(verlauf))
            pruef = validiere_aktion(parse_aktion(roh) or {})
            if pruef.get("ok"):
                aktion = pruef
                break
            _log("Antwort unbrauchbar, neuer Versuch", pruef.get("grund", ""))
        if aktion is None:
            return {"status": "fehler", "schritte": schritte,
                    "ansage": "Ich komme mit dem naechsten Schritt gerade nicht klar. Sag es mir bitte "
                              "nochmal oder etwas konkreter."}
        ansage = beschreibe(aktion)

        if aktion["aktion"] == "fertig":
            schritte.append({"aktion": "fertig", "ansage": ansage})
            _log("Ziel erreicht", ansage[:200])
            return {"status": "fertig", "schritte": schritte, "ansage": ansage}
        if aktion["aktion"] == "frage":
            schritte.append({"aktion": "frage", "ansage": ansage})
            return {"status": "frage", "schritte": schritte, "ansage": ansage, "frage": ansage}

        # Harte Bremse: gefaehrlich/CEO-Tor ODER unsicher -> anhalten und zurueckfragen (NICHT ausfuehren).
        if ist_gefaehrlich(aktion):
            schritte.append({"aktion": aktion["aktion"], "ansage": ansage, "gehalten": "ceo_tor"})
            _log("Angehalten (CEO-Tor)", ansage[:200])
            return {"status": "bestaetigung", "schritte": schritte, "pending": aktion,
                    "ansage": f"Achtung, naechster Schritt ist heikel: {ansage} Soll ich das wirklich tun? "
                              "Bitte ausdruecklich bestaetigen — oder sag mir einen anderen Weg.",
                    "grund": "ceo_tor"}
        if aktion["konfidenz"] < konfidenz_schwelle:
            schritte.append({"aktion": aktion["aktion"], "ansage": ansage, "gehalten": "unsicher"})
            _log("Angehalten (unsicher)", ansage[:200])
            return {"status": "bestaetigung", "schritte": schritte, "pending": aktion,
                    "ansage": f"Ich bin unsicher: {ansage} Soll ich so weitermachen?", "grund": "unsicher"}

        # Benigne, sichere Aktion -> ausfuehren + ansagen.
        res = handle(aktion, shot) or {}
        schritte.append({"aktion": aktion["aktion"], "ansage": ansage,
                         "ausgefuehrt": bool(res.get("ausgefuehrt")), "res": res})
        _log(f"Schritt: {aktion['aktion']}", ansage[:200])
        if not res.get("ausgefuehrt"):
            return {"status": "fehler", "schritte": schritte,
                    "ansage": f"Der Schritt ging nicht: {res.get('grund', 'unbekannt')}. Ich stoppe hier."}
        verlauf.append(ansage)

    return {"status": "max_erreicht", "schritte": schritte,
            "ansage": f"Ich habe {max_schritte} Schritte gemacht und pausiere. Soll ich weitermachen?"}
