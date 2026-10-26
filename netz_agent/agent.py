"""Netz-Agent in Quarantaene (NETZ_AGENT_ROADMAP.md, Q1): holt Auftraege aus `netz_queue/auftraege/`, sucht ueber Brave,
oeffnet nur Seiten aus den Suchtreffern und schreibt das Ergebnis nach `netz_queue/ergebnisse/`.

Laeuft im eigenen Container `luna-netz`, der nur `netz_agent/` (lesend) und `netz_queue/` sieht -- keine LUNA-Dateien,
keine LUNA-.env, nur `BRAVE_API_KEY` und (Q2) `ANTHROPIC_API_KEY` aus dem eigenen Workspace „luna-netz“. Ergebnis =
Treffer + Seitentexte + gepruefter Formular (`formular.py`, Claude Haiku 5.5 ohne Werkzeuge); LUNA behandelt alles als
fremde Daten. Standardbibliothek + Anthropic-SDK aus dem Image; importiert nichts aus LUNA.

Auftrag: {"id": "<a-z0-9-, 8-40>", "art": "suche", "frage": "<= 300 Zeichen", "max_seiten": 0-5}
Ergebnis: {"id", "ok", "frage", "treffer": [{titel, url, auszug}], "seiten": [{url, titel, text, status}|{url, fehler}],
           "fehler", "fertig"}
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import abruf

ID = re.compile(r"^[a-z0-9-]{8,40}$")
MAX_FRAGE = 300
MAX_SEITEN = 5
MAX_TREFFER = 8
BRAVE = "https://api.search.brave.com/res/v1/web/search"


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def brave_suche(frage: str, schluessel: str, anzahl: int = MAX_TREFFER, *, versuche: int = 2, pause: float = 3.0) -> list[dict]:
    q = urllib.parse.urlencode({"q": frage, "count": anzahl, "safesearch": "moderate"})
    req = urllib.request.Request(f"{BRAVE}?{q}", headers={"Accept": "application/json", "X-Subscription-Token": schluessel,
                                                        "User-Agent": abruf.AGENT})
    for v in range(versuche):                              # BF-73: Namensaufloesung kurz nach dem Start -> zweiter Versuch
        try:
            with urllib.request.urlopen(req, timeout=abruf.TIMEOUT) as r:
                d = json.loads(r.read(abruf.MAX_BYTES).decode("utf-8", "replace"))
            break
        except urllib.error.URLError:
            if v + 1 >= versuche:
                raise
            time.sleep(pause)
    out = []
    for t in ((d.get("web") or {}).get("results") or [])[:anzahl]:
        url = str(t.get("url") or "")
        if url.startswith(("http://", "https://")):
            out.append({"titel": str(t.get("title") or "")[:300], "url": url[:1000],
                        "auszug": re.sub(r"<[^>]+>", "", str(t.get("description") or ""))[:600]})
    return out


def pruefe_auftrag(a: dict) -> dict:
    if not isinstance(a, dict) or a.get("art") != "suche":
        raise ValueError("Unbekannte Auftragsart")
    if not ID.match(str(a.get("id") or "")):
        raise ValueError("Ungueltige Auftrags-ID")
    frage = " ".join(str(a.get("frage") or "").split())
    if not frage or len(frage) > MAX_FRAGE:
        raise ValueError(f"Frage fehlt oder ist laenger als {MAX_FRAGE} Zeichen")
    n = int(a.get("max_seiten") or 0)
    return {"id": a["id"], "art": "suche", "frage": frage, "max_seiten": max(0, min(n, MAX_SEITEN))}


class Agent:
    def __init__(self, queue: Path | str, schluessel: str, *, suche=brave_suche, hole=abruf.hole, modell_client=None):
        self.q = Path(queue)
        self.schluessel = schluessel
        self.suche, self.hole = suche, hole
        self.modell_client = modell_client                 # Q2: Anthropic-Client (None -> kein Formular, nur Rohdaten)
        for d in ("auftraege", "in_arbeit", "ergebnisse"):
            (self.q / d).mkdir(parents=True, exist_ok=True)

    def _schreibe(self, name: str, daten: dict) -> None:
        ziel = self.q / "ergebnisse" / name
        tmp = ziel.with_suffix(".tmp")
        tmp.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
        tmp.replace(ziel)

    def bearbeite(self, a: dict) -> dict:
        a = pruefe_auftrag(a)
        treffer = self.suche(a["frage"], self.schluessel)
        seiten = []
        for t in treffer[:a["max_seiten"]]:                       # nur Seiten aus den Suchtreffern
            try:
                seiten.append(self.hole(t["url"]))
            except Exception as exc:                               # Abgelehnt, Zeitueberschreitung, HTTP-Fehler
                seiten.append({"url": t["url"], "fehler": f"{exc.__class__.__name__}: {str(exc)[:200]}"})
        formular = None
        if self.modell_client is not None:
            from . import formular as _formular
            try:
                formular = _formular.erstellen(a["frage"], treffer, seiten, client=self.modell_client)
            except Exception as exc:                           # Formular ist Zusatz -- Rohdaten gehen trotzdem zurueck
                formular = {"fehler": f"{exc.__class__.__name__}: {str(exc)[:200]}"}
        return {"id": a["id"], "ok": True, "frage": a["frage"], "treffer": treffer, "seiten": seiten, "formular": formular,
                "fehler": "", "fertig": _jetzt()}

    def ein_durchlauf(self, *, trocken: bool = False) -> int:
        n = 0
        for datei in sorted((self.q / "auftraege").glob("*.json")):
            if not ID.match(datei.stem):
                datei.unlink(missing_ok=True)
                continue
            arbeit = self.q / "in_arbeit" / datei.name
            try:
                datei.replace(arbeit)                              # Auftrag uebernehmen (atomar)
            except OSError:
                continue
            try:
                a = json.loads(arbeit.read_text(encoding="utf-8"))
                if trocken:
                    print(f"[netz-agent] trocken: {pruefe_auftrag(a)}", flush=True)
                    arbeit.replace(datei)                          # zurueck in die Warteschlange
                    n += 1
                    continue
                e = self.bearbeite(a)
            except Exception as exc:
                e = {"id": datei.stem, "ok": False, "frage": "", "treffer": [], "seiten": [],
                     "fehler": f"{exc.__class__.__name__}: {str(exc)[:200]}", "fertig": _jetzt()}
            self._schreibe(datei.name, e)
            arbeit.unlink(missing_ok=True)
            n += 1
        return n


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="LUNA Netz-Agent (Quarantaene)")
    p.add_argument("--queue", default=os.environ.get("NETZ_QUEUE", "/app/netz_queue"))
    p.add_argument("--dry-run", action="store_true", help="Auftraege nur pruefen und anzeigen, nichts abrufen")
    p.add_argument("--einmal", action="store_true")
    args = p.parse_args()
    schluessel = os.environ.get("BRAVE_API_KEY", "")
    if not schluessel and not args.dry_run:
        raise SystemExit("BRAVE_API_KEY fehlt (netz_agent/.env)")
    modell_client = None
    if os.environ.get("ANTHROPIC_API_KEY") and not args.dry_run:
        import anthropic
        modell_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=90, max_retries=1)
    agent = Agent(args.queue, schluessel, modell_client=modell_client)
    print(f"[netz-agent] bereit, Warteschlange {args.queue}{' (trocken)' if args.dry_run else ''}", flush=True)
    while True:
        n = agent.ein_durchlauf(trocken=args.dry_run)
        if n:
            print(f"[netz-agent] {n} Auftrag/Auftraege bearbeitet", flush=True)
        if args.einmal:
            return
        time.sleep(5)
