"""Backoffice-Worker (FRONTDESK_BACKOFFICE_ROADMAP.md, Etappe 2) -- laeuft als systemd-Dienst auf dem MACO470.

Holt Auftraege ueber die LUNA-OS-API (`/api/backoffice/naechster`), arbeitet sie NACHEINANDER mit dem lokalen Modell
(Ollama, native API, kleiner Kontext, ohne Werkzeuge) ab und meldet das Ergebnis (`/api/backoffice/ergebnis`).

CEO-Entscheidungen (2026-09-26/27): Modell nur laden, wenn Windows genug RAM frei hat, sonst nachts (01-06 Uhr) mit
niedrigerer Schwelle; nach dem Stapel entladen. Bewertungen/Analysen liest Gemini gegen (Stufe 2, 0 EUR). Unbrauchbare
Antworten (Zeichensalat, Wiederholungsschleifen, fremde Schrift) -> ein zweiter Versuch, sonst `fehlgeschlagen`.

Start: `python -m backoffice.worker` (Dienst `backoffice-worker`), Test: `python -m backoffice.worker --einmal`.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.request
from datetime import datetime

from cutter.luna_bridge import LunaBridge
from cutter.pipeline import _lade_env

POWERSHELL = "/mnt/c/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe"
NACHT = (1, 6)

SYSTEM = ("Du bist das Backoffice von LUNA, der Assistentin des CEO Nils Krüger. Du erledigst Aufträge gründlich, "
          "sachlich und vollständig. Schreibe ausschließlich Deutsch mit korrekten Umlauten (ä, ö, ü, ß) — keine "
          "englischen Wörter außer Eigennamen und gängigen Fachbegriffen. Duze den CEO. Kein Vorwort, keine "
          "Meta-Kommentare, direkt das Ergebnis.")

ANWEISUNG = {
    "zusammenfassung": ("Fasse zusammen: die wichtigsten Punkte zuerst, als knappe Stichpunkte. Lass nichts Wichtiges "
                        "weg — Risiken, Probleme und Widersprüche ausdrücklich nennen. Am Ende eine Empfehlung in "
                        "einem Satz."),
    "entwurf": ("Schreibe den Text so, wie Nils ihn selbst verschickt: in der Ich-Form aus Nils' Sicht (niemals über "
                "Nils in der dritten Person). Anrede und Du/Sie nach Vorgabe, sonst höflich per Sie. Unterschrift: "
                "Nils Krüger. Gib nur das Ergebnis aus (bei Mails: Betreff und Text)."),
    "bewertung": ("Bewerte mit diesen Pflichtpunkten, jeweils mit eigenem Urteil (nicht die Vorlage wiederholen): "
                  "1. Worum geht es (ein Satz). 2. Nutzen. 3. Kosten (einmalig und laufend). 4. Risiken — was kann "
                  "schiefgehen, wie merkt man es. 5. Aufwand. 6. Offene Fragen. 7. Empfehlung: freigeben, ablehnen "
                  "oder überarbeiten — mit Begründung."),
    "analyse": ("Analysiere gründlich: Ausgangslage, wichtigste Faktoren, Chancen, Risiken, offene Fragen, "
                "Empfehlung mit Begründung. Trenne Fakten klar von Annahmen."),
    "sonstiges": "Erledige den Auftrag vollständig und übersichtlich.",
}
GEGENLESEN = ("bewertung", "analyse")

WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
MONATE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
          "Dezember")
# BF-28: das lokale Modell kennt das heutige Datum nicht und erfand „Freitag, den 15.11.2024".
NICHTS_ERFINDEN = ("Erfinde keine Daten, Uhrzeiten, Zahlen, Namen oder Fakten, die nicht im Auftrag stehen — wenn etwas "
                   "fehlt, setze einen Platzhalter in eckigen Klammern, z. B. [Datum]. Verändere keine Aussagen des "
                   "Auftrags (was geplant ist, bleibt geplant).")


def datum_text(jetzt: datetime | None = None) -> str:
    jetzt = jetzt or datetime.now()
    return f"Heute ist {WOCHENTAGE[jetzt.weekday()]}, {jetzt.day}. {MONATE[jetzt.month - 1]} {jetzt.year}."


def _log(text: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {text}", flush=True)


# -- reine Entscheidungen (getestet) ------------------------------------------------------------------------------

def ist_nacht(jetzt: datetime | None = None) -> bool:
    jetzt = jetzt or datetime.now()
    return NACHT[0] <= jetzt.hour < NACHT[1]


def darf_laden(verfuegbar_gb: float | None, *, geladen: bool, nacht: bool, schwelle_tag: float,
               schwelle_nacht: float) -> tuple[bool, str]:
    """Modell laden erlaubt? Bereits geladen -> ja. Sonst RAM gegen die Schwelle (nachts niedriger)."""
    if geladen:
        return True, "Modell bereits geladen"
    if verfuegbar_gb is None:
        return False, "Speicher nicht messbar"
    schwelle = schwelle_nacht if nacht else schwelle_tag
    if verfuegbar_gb >= schwelle:
        return True, f"{verfuegbar_gb:.1f} GB verfuegbar >= {schwelle:g} GB"
    return False, f"nur {verfuegbar_gb:.1f} GB verfuegbar (< {schwelle:g} GB{' nachts' if nacht else ''})"


def plausibel(text: str, *, aufgabe: str = "", jetzt: datetime | None = None) -> list[str]:
    """Probleme einer Modellantwort (leer = brauchbar). Bewusst grob: faengt Zeichensalat/Schleifen ab (BF-23) und
    erfundene Jahreszahlen (BF-28: eine Jahreszahl, die weder im Auftrag steht noch dieses/naechstes Jahr ist)."""
    probleme = []
    jahr = (jetzt or datetime.now()).year
    erlaubt = {str(jahr), str(jahr + 1)} | set(re.findall(r"\b(?:19|20)\d\d\b", aufgabe))
    fremd = sorted(set(re.findall(r"\b(?:19|20)\d\d\b", text)) - erlaubt)
    if fremd:
        probleme.append("erfundene Jahreszahl " + ", ".join(fremd))
    if len(text.split()) < 15:
        probleme.append("zu kurz")
    if re.search(r"\b(\w+)(?:\W+\1\b){4,}", text, re.I):
        probleme.append("Wort-Wiederholungsschleife")
    if re.search(r"[぀-ヿ㐀-鿿가-힯]", text):
        probleme.append("fremde Schriftzeichen")
    if re.search(r"(\\\$|\$\\){3,}|(.)\2{15,}", text):
        probleme.append("Zeichensalat")
    zeilen = [z.strip() for z in text.splitlines() if len(z.strip()) > 20]
    if len(zeilen) - len(set(zeilen)) >= 3:
        probleme.append("wiederholte Zeilen")
    return probleme


def nachrichten(auftrag: dict, jetzt: datetime | None = None) -> list[dict]:
    art = auftrag.get("art") if auftrag.get("art") in ANWEISUNG else "sonstiges"
    return [{"role": "system", "content": f"{SYSTEM} {datum_text(jetzt)} {NICHTS_ERFINDEN}\n\n{ANWEISUNG[art]}"},
            {"role": "user", "content": auftrag.get("aufgabe", "")}]


# -- Aussenwelt (im Test ersetzt) ---------------------------------------------------------------------------------

def verfuegbar_gb() -> float | None:
    try:
        out = subprocess.run([POWERSHELL, "-NoProfile", "-Command",
                              "(Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory).AvailableMBytes"],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        return int(out) / 1024
    except Exception:
        return None


class Ollama:
    def __init__(self, url: str, modell: str, *, kontext: int = 8192, timeout: int = 900):
        self.url, self.modell, self.kontext, self.timeout = url.rstrip("/"), modell, kontext, timeout

    def _post(self, pfad: str, body: dict, timeout: int | None = None) -> dict:
        req = urllib.request.Request(self.url + pfad, json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}")

    def geladen(self) -> bool:
        try:
            with urllib.request.urlopen(self.url + "/api/ps", timeout=10) as r:
                return any(m.get("name") == self.modell for m in json.load(r).get("models", []))
        except Exception:
            return False

    def antwort(self, messages: list[dict]) -> str:
        d = self._post("/api/chat", {"model": self.modell, "stream": False, "keep_alive": "5m",
                                     "options": {"num_ctx": self.kontext}, "messages": messages})
        return re.sub(r"<think>.*?</think>\s*", "", (d.get("message") or {}).get("content", ""), flags=re.S).strip()

    def entladen(self) -> None:
        try:
            self._post("/api/generate", {"model": self.modell, "keep_alive": 0}, timeout=60)
        except Exception:
            pass


def gemini_gegenlesen(env: dict, auftrag: dict, entwurf: str) -> str:
    """Stufe 2 der Gegenpruefung (CEO 2026-09-27): Gemini prueft den lokalen Entwurf kritisch. Leer bei Fehler."""
    key = env.get("GEMINI_API_KEY", "")
    if not key:
        return ""
    try:
        import openai
        client = openai.OpenAI(api_key=key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                               timeout=120, max_retries=1)
        r = client.chat.completions.create(model=env.get("BACKOFFICE_GEGENLESER", "gemini-2.5-flash"), messages=[
            {"role": "system", "content": "Du bist ein kritischer Gegenleser. Deutsch, knapp (höchstens 8 Zeilen). "
                                          "Nenne Fehler, fehlende Punkte und ob du die Empfehlung teilst."},
            {"role": "user", "content": f"AUFTRAG:\n{auftrag.get('aufgabe', '')}\n\nENTWURF:\n{entwurf}"}])
        return (r.choices[0].message.content or "").strip()
    except Exception as exc:
        _log(f"Gegenlesen fehlgeschlagen: {str(exc)[:120]}")
        return ""


# -- Ablauf -------------------------------------------------------------------------------------------------------

def verarbeite(auftrag: dict, ollama, gegenleser) -> dict:
    """Einen Auftrag erledigen -> Nutzdaten fuer /api/backoffice/ergebnis. Wirft nie."""
    t = time.time()
    try:
        text, probleme = "", ["kein Versuch"]
        for _ in range(2):                                   # unbrauchbar -> genau ein zweiter Versuch
            text = ollama.antwort(nachrichten(auftrag))
            probleme = plausibel(text, aufgabe=auftrag.get("aufgabe", ""))
            if not probleme:
                break
        if probleme:
            return {"id": auftrag["id"], "ok": False, "grund": "Antwort unbrauchbar: " + ", ".join(probleme)}
        zweit = gegenleser(auftrag, text) if auftrag.get("art") in GEGENLESEN else ""
        return {"id": auftrag["id"], "ok": True, "ergebnis": text, "zweitmeinung": zweit,
                "modell": getattr(ollama, "modell", ""), "dauer_s": round(time.time() - t, 1)}
    except Exception as exc:
        return {"id": auftrag["id"], "ok": False, "grund": f"{type(exc).__name__}: {str(exc)[:200]}"}


_zuletzt_gewartet: list[bool] = [False]   # Zustand fuer den Warte-Hinweis (einmal je Wechsel, kein Dauerlog)


def durchlauf(bridge, ollama, gegenleser, *, messen=verfuegbar_gb, jetzt=None, schwelle_tag=13.0,
              schwelle_nacht=11.0, offene=None) -> int:
    """Warteschlange leer arbeiten (sofern Laden erlaubt). Gibt die Zahl erledigter Auftraege zurueck.
    Wartet der Worker wegen zu wenig RAM, obwohl Auftraege anstehen, steht das EINMAL im Protokoll (2026-09-27:
    ein Tagtest blieb wortlos liegen, weil nur 10,6 GB frei waren)."""
    n = 0
    geladen = ollama.geladen()
    erlaubt, grund = darf_laden(None if geladen else messen(), geladen=geladen, nacht=ist_nacht(jetzt),
                                schwelle_tag=schwelle_tag, schwelle_nacht=schwelle_nacht)
    if not erlaubt:
        anzahl = offene() if offene else None
        if anzahl and not _zuletzt_gewartet[0]:
            _log(f"Wartet: {anzahl} Auftrag/Auftraege offen, aber {grund} — spaetestens ab {NACHT[0]}:00 Uhr.")
            _zuletzt_gewartet[0] = True
        return 0
    if _zuletzt_gewartet[0]:
        _log(f"Speicher reicht wieder ({grund}) — arbeite die Warteschlange ab.")
        _zuletzt_gewartet[0] = False
    while True:
        r = bridge._req("/api/backoffice/naechster")
        auftrag = (r or {}).get("auftrag")
        if not auftrag:
            break
        _log(f"Auftrag #{auftrag.get('kurz')} ({auftrag.get('art')}) — {grund}")
        daten = verarbeite(auftrag, ollama, gegenleser)
        bridge._req("/api/backoffice/ergebnis", method="POST", data=daten, timeout=60)
        _log(f"Auftrag #{auftrag.get('kurz')} -> {'fertig' if daten['ok'] else 'fehlgeschlagen: ' + daten['grund']}")
        n += 1
    if n:
        ollama.entladen()                                    # CEO: nach dem Stapel entladen (BF-22)
        _log(f"{n} Auftrag/Auftraege erledigt, Modell entladen.")
    return n


def _offene(bridge) -> int:
    r = bridge._req("/api/backoffice") or {}
    return sum(1 for a in r.get("auftraege", []) if a.get("status") == "neu")


def loop(*, intervall: float = 60.0, einmal: bool = False) -> None:
    env = _lade_env()
    bridge = LunaBridge.from_env(env)
    bridge.timeout = 30
    ollama = Ollama(env.get("BACKOFFICE_OLLAMA_URL", "http://192.168.178.184:11434"),
                    env.get("BACKOFFICE_MODELL", "qwen3:14b"))
    tag, nacht = float(env.get("BACKOFFICE_RAM_TAG_GB", 13)), float(env.get("BACKOFFICE_RAM_NACHT_GB", 11))
    _log(f"Backoffice-Worker aktiv (Modell {ollama.modell}, RAM-Schwelle {tag:g}/{nacht:g} GB, Nacht {NACHT[0]}-{NACHT[1]} Uhr).")
    while True:
        try:
            if bridge.aktiv():
                durchlauf(bridge, ollama, lambda a, e: gemini_gegenlesen(env, a, e),
                          schwelle_tag=tag, schwelle_nacht=nacht, offene=lambda: _offene(bridge))
        except Exception as exc:                             # nie den Worker mitreissen
            _log(f"Schleifen-Fehler: {exc}")
        if einmal:
            return
        time.sleep(intervall)


def main() -> None:
    ap = argparse.ArgumentParser(description="LUNA Backoffice-Worker (lokales LLM)")
    ap.add_argument("--intervall", type=float, default=60.0)
    ap.add_argument("--einmal", action="store_true")
    a = ap.parse_args()
    loop(intervall=a.intervall, einmal=a.einmal)


if __name__ == "__main__":
    main()
