"""Gedaechtnis-Suche ueber alle Geschaeftsdaten (JARVIS_ALLTAG J8, CEO-Go 2026-10-29).

Fragen wie „Was hat Kiez Alm letztes Jahr gebucht und wie lief es?“ beantwortet LUNA mit Quellenangaben. Dafuer sammelt
`dokumente` aus den vorhandenen Speichern je Vorgang einen kurzen Text (Firma, Angebot, Auftrag mit Projektbericht,
Rechnung, Eingangsbeleg, Firmenakte, eigenes To-do, gemerktes Wissen, Research-Ticket, Antrag) -- nur lesen, nichts
wird veraendert.

`suchen` mischt zwei Ranglisten per Reciprocal Rank Fusion:
- **Wortsuche** (BM25, `core/ranking.py`) -- wie bisher, laeuft immer;
- **Bedeutungssuche** -- Suchmodell `qwen3-embedding:0.6b` im Ollama auf dem MACO470 (Heimnetz, kostenlos). Die
  Vektoren liegen in `gedaechtnis/vektoren.json` (abgeleitet, jederzeit neu berechenbar; nur NAS, nicht im Git, kein
  Backup). Ist der MACO470 aus, faellt die Suche still auf die Wortsuche zurueck.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import threading
from pathlib import Path

from . import ranking

MODELL_STANDARD = "qwen3-embedding:0.6b"
INDEX = "gedaechtnis/vektoren.json"     # relativ zum Repo-Wurzelverzeichnis (nur NAS)
# Qwen3-Embedding: Anfragen mit Aufgabenbeschreibung einbetten, Dokumente ohne (Modellkarte).
ANWEISUNG = ("Instruct: Finde Eintraege aus den Geschaeftsdaten (Firmen, Angebote, Auftraege, Rechnungen, Belege, "
             "Notizen), die die Frage beantworten\nQuery: ")
MAX_TEXT = 1500                 # Zeichen je Dokument fuer das Suchmodell
STAPEL = 32                     # Dokumente je Aufruf an Ollama
RRF_K = 60


def _eur(cent) -> str:
    from .beleg_pdf import eur
    try:
        return eur(int(cent or 0))
    except (TypeError, ValueError):
        return ""


def _datum_de(iso: str) -> str:
    iso = str(iso or "")[:10]
    return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}" if len(iso) == 10 else ""


def _doc(quelle: str, ref: str, titel: str, text: str, datum: str = "") -> dict:
    return {"id": f"{quelle}:{ref}", "quelle": quelle, "ref": ref, "titel": " ".join(str(titel).split())[:120],
            "text": " ".join(str(text).split()), "datum": str(datum or "")[:10]}


# -- Dokumente sammeln (nur lesen) -----------------------------------------------------------------------------------------
def _geschaeft(root: Path) -> list[dict]:
    bh_dir = root / "buchhaltung"
    if not (bh_dir / "log.jsonl").exists():
        return []
    from .angebote import AngebotStore
    from .beauftragung import AuftragBuch
    from .buchhaltung import Buchhaltung
    from .firmenakte import Firmenakte
    from .katalog import Katalog
    from .kunden import KundenStore
    from .rechnungen import RechnungStore
    bh = Buchhaltung(bh_dir)
    ks = KundenStore(bh)
    out: list[dict] = []
    firmen = ks.firmen()
    name = {f["nummer"]: f["name"] for f in firmen}
    for f in firmen:
        teile = [f["name"], {"kunde": "Kunde", "lieferant": "Lieferant", "partner": "Partner"}.get(f.get("typ"), ""),
                 f"Nummer {f.get('anzeige') or f['nummer']}", " ".join(x for x in (f.get("plz"), f.get("ort")) if x),
                 f.get("website") or "", f.get("notiz") or "", "" if f.get("aktiv", True) else "inaktiv"]
        out.append(_doc("firma", f.get("anzeige") or f["nummer"], f["name"], " · ".join(t for t in teile if t),
                        f.get("angelegt", "")))
    try:
        akte = Firmenakte(bh, ks)
        for f in firmen:
            for d in akte.akte(f["nummer"]):
                out.append(_doc("akte", d.get("id", ""), d.get("titel") or "Dokument",
                                f"{name.get(f['nummer'], '')} · {d.get('art', '')} · {d.get('notiz', '')}"
                                + (f" · Bezug {d['bezug']}" if d.get("bezug") else ""), d.get("datum") or d.get("ts")))
    except Exception:
        pass
    an = AngebotStore(bh, ks, Katalog(bh))
    for a in an.liste():
        voll = an.angebot(a["nummer"]) or {}
        pos = "; ".join(p.get("beschreibung", "") + (f" ({p['detail']})" if p.get("detail") else "")
                        for p in voll.get("positionen") or [])
        out.append(_doc("angebot", a["nummer"], f"Angebot {a['nummer']} {a.get('titel', '')}",
                        f"Angebot {a['nummer']} an {a.get('firma_name', '')} vom {_datum_de(a.get('datum'))}: "
                        f"{a.get('titel', '')}, {_eur(a.get('summe_cent'))}, Status {a.get('anzeige_status') or a.get('status')}."
                        f" Positionen: {pos}", a.get("datum")))
    # Projektberichte + Kennzahlen je Auftrag aus der Kette (letzter Stand gewinnt)
    fazit: dict[str, str] = {}
    zahlen: dict[str, dict] = {}
    for e in bh.eintraege():
        d = e.get("daten") or {}
        if e.get("typ") == "auftrag_bericht" and d.get("nummer"):
            fazit[d["nummer"]] = d.get("fazit", "")
        elif e.get("typ") == "posting_kennzahlen" and d.get("id"):
            zahlen[str(d["id"]).split("-P")[0]] = d.get("werte") or {}
    for a in AuftragBuch(bh, ks, an).liste():
        nr = a["nummer"]
        w = zahlen.get(nr) or {}
        kz = ", ".join(f"{k} {v:,}".replace(",", ".") for k, v in w.items() if isinstance(v, int) and k != "wiedergabe_s")
        out.append(_doc("auftrag", nr, f"Auftrag {nr} {a.get('titel', '')}",
                        f"Auftrag {nr} von {a.get('firma_name', '')}: {a.get('titel', '')}, "
                        + (f"Leistung {_datum_de(a.get('leistung_von'))} bis {_datum_de(a.get('leistung_bis'))}, "
                           if a.get("leistung_von") else "")
                        + f"{_eur(a.get('summe_cent'))}, Status {a.get('status')}"
                        + (f", aus Angebot {a['angebot']}" if a.get("angebot") else "")
                        + (f". Kennzahlen: {kz}" if kz else "") + (f". Projektbericht: {fazit[nr]}" if nr in fazit else ""),
                        a.get("datum")))
    for r in RechnungStore(bh, ks, Katalog(bh)).uebersicht()["rechnungen"]:
        out.append(_doc("rechnung", r["nummer"], f"Rechnung {r['nummer']} {r.get('titel') or ''}",
                        f"Rechnung {r['nummer']} an {r.get('firma_name', '')} vom {_datum_de(r.get('rechnungsdatum'))}"
                        f"{(': ' + r['titel']) if r.get('titel') else ''}, {_eur(r.get('summe_cent'))}, Status {r.get('status')}"
                        + (", ueberfaellig" if r.get("ueberfaellig") else "")
                        + (f", zu Auftrag {r['auftrag']}" if r.get("auftrag") else ""), r.get("rechnungsdatum")))
    try:
        from .eingangsbelege import EINNAHME_KATEGORIEN, KATEGORIEN, EingangStore
        kat = {k: v[0] for k, v in KATEGORIEN.items()} | EINNAHME_KATEGORIEN
        je_lieferant: dict[str, list[dict]] = {}
        for b in EingangStore(bh).liste():
            if b.get("status") == "verworfen":
                continue
            art = "Gutschrift/Einnahme" if b.get("art") == "einnahme" else "Ausgabe"
            k = kat.get(b.get("kategorie") or "", b.get("kategorie") or "-")
            out.append(_doc("beleg", b["nummer"], f"Beleg {b['nummer']} {b.get('lieferant') or ''}",
                            f"Eingangsbeleg {b['nummer']} ({art}) von {b.get('lieferant') or 'unbekannt'} vom "
                            f"{_datum_de(b.get('rechnungsdatum'))}, {_eur(b.get('betrag_cent'))}, Kategorie {k}, "
                            f"Status {b.get('status')}", b.get("rechnungsdatum") or b.get("eingegangen")))
            if b.get("lieferant") and art == "Ausgabe":
                je_lieferant.setdefault(b["lieferant"], []).append(b | {"_kat": k})
        # Je Lieferant eine Zusammenfassung -- beantwortet „Was kostet uns X im Monat?“ ohne zehn Einzelbelege
        for lf, bs in je_lieferant.items():
            if len(bs) < 2:
                continue
            bs.sort(key=lambda b: b.get("rechnungsdatum") or "")
            letzt = bs[-1]
            out.append(_doc("ausgaben", lf, f"Ausgaben bei {lf}",
                            f"Laufende Ausgaben bei {lf} (Kategorie {letzt['_kat']}): {len(bs)} Belege vom "
                            f"{_datum_de(bs[0].get('rechnungsdatum'))} bis {_datum_de(letzt.get('rechnungsdatum'))}, "
                            f"zusammen {_eur(sum(int(b.get('betrag_cent') or 0) for b in bs))}, zuletzt "
                            f"{_eur(letzt.get('betrag_cent'))} ({letzt['nummer']})", letzt.get("rechnungsdatum")))
    except Exception:
        pass
    return out


def dokumente(root: Path | str, *, brain=None, research=None, antraege=None) -> list[dict]:
    """Alle durchsuchbaren Vorgaenge. Jede Quelle einzeln abgesichert -- eine kaputte Quelle blockiert nie die Suche."""
    root = Path(root)
    out: list[dict] = []
    try:
        out += _geschaeft(root)
    except Exception as exc:
        print(f"[gedaechtnis] Geschaeftsdaten: {exc.__class__.__name__}: {str(exc)[:120]}", flush=True)
    try:
        from .aufgaben import AufgabenStore
        for gruppe, liste in AufgabenStore(root / "todos" / "log.jsonl").liste().items():
            for t in liste:
                out.append(_doc("todo", t["id"], f"To-do {t['titel']}",
                                f"Eigenes To-do: {t['titel']}. {t.get('notiz') or ''} "
                                f"{'erledigt' if gruppe == 'erledigt' else 'offen'}"
                                + (f", faellig {_datum_de(t['faellig'])}" if t.get("faellig") else ""),
                                t.get("faellig") or t.get("angelegt")))
    except Exception:
        pass
    if brain is not None:
        try:
            for e in brain.list(limit=1000):
                out.append(_doc("wissen", e.get("id", ""), e.get("titel") or e.get("text", "")[:60],
                                f"{e.get('titel', '')} {e.get('text', '')} {' '.join(e.get('tags') or [])}", e.get("ts")))
        except Exception:
            pass
    if research is not None:
        try:
            for t in research.list():
                out.append(_doc("research", t.get("ticket_id", ""), t.get("frage", "")[:100],
                                f"Research-Ticket ({t.get('status', '')}): {t.get('frage', '')} {t.get('befund') or ''}",
                                (t.get("verlauf") or [{}])[0].get("ts", "")))
        except Exception:
            pass
    if antraege is not None:
        try:
            for a in antraege.list():
                if a.get("status") in ("abgelehnt", "geloescht"):    # verworfene Ideen sind kein Wissen (und Rauschen)
                    continue
                out.append(_doc("antrag", a.get("antrag_id", ""), a.get("titel", ""),
                                f"Antrag ({a.get('status', '')}): {a.get('titel', '')} {a.get('beschreibung') or ''}",
                                (a.get("verlauf") or [{}])[0].get("ts", "")))
        except Exception:
            pass
    return out


# -- Suchmodell (Ollama auf dem MACO470) -----------------------------------------------------------------------------------
class Einbetter:
    """Ollama `/api/embed`. Liefert normierte Vektoren oder None (Modell nicht erreichbar)."""

    def __init__(self, url: str, modell: str = MODELL_STANDARD, timeout: float = 20):
        self.url, self.modell, self.timeout = url.rstrip("/"), modell, timeout

    def einbetten(self, texte: list[str], *, timeout: float | None = None) -> list[list[float]] | None:
        if not texte:
            return []
        from .lokal_llm import einbetten
        vek = einbetten(self.url, self.modell, [t[:MAX_TEXT] for t in texte], timeout=timeout or self.timeout)
        if vek is None:
            return None
        out = []
        for v in vek:
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([round(x / n, 5) for x in v])
        return out


def einbetter_aus(secrets: dict | None) -> Einbetter | None:
    """`GEDAECHTNIS_EMBED_URL` oder die Ollama-Adresse aus `LOCAL_LLM_BASE_URL` (ohne /v1); `GEDAECHTNIS=aus` schaltet ab."""
    s = secrets or {}
    if str(s.get("GEDAECHTNIS", "")).strip().lower() in ("aus", "0", "false", "nein"):
        return None
    url = (s.get("GEDAECHTNIS_EMBED_URL") or "").strip()
    if not url:
        basis = (s.get("LOCAL_LLM_BASE_URL") or "").strip().rstrip("/")
        url = basis[:-3] if basis.endswith("/v1") else basis
    if not url:
        return None
    return Einbetter(url, (s.get("GEDAECHTNIS_MODELL") or "").strip() or MODELL_STANDARD)


def _hash(d: dict) -> str:
    return hashlib.sha1((d["titel"] + "\n" + d["text"][:MAX_TEXT]).encode()).hexdigest()[:16]


class VektorIndex:
    """`{modell, v: {doc_id: {h, e}}}` -- je Dokument der Text-Hash und der Vektor; geaenderte Texte werden neu berechnet."""

    _lock = threading.Lock()

    def __init__(self, pfad: Path | str):
        self.pfad = Path(pfad)
        self._daten: dict | None = None

    def _lade(self, modell: str) -> dict:
        if self._daten is None:
            try:
                d = json.loads(self.pfad.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                d = {}
            self._daten = d if d.get("modell") == modell else {"modell": modell, "v": {}}
        return self._daten

    def aktualisieren(self, docs: list[dict], einbetter: Einbetter, *, max_neu: int | None = None) -> int:
        """Fehlende/geaenderte Vektoren berechnen (hoechstens `max_neu`), Weggefallene entfernen. -> Anzahl neu."""
        d = self._lade(einbetter.modell)
        v = d["v"]
        ids = {x["id"] for x in docs}
        weg = [k for k in v if k not in ids]
        offen = [x for x in docs if (v.get(x["id"]) or {}).get("h") != _hash(x)]
        if max_neu is not None:
            offen = offen[:max_neu]
        neu = 0
        for i in range(0, len(offen), STAPEL):
            teil = offen[i:i + STAPEL]
            vek = einbetter.einbetten([f"{x['titel']}\n{x['text']}" for x in teil])
            if vek is None:
                break
            for x, e in zip(teil, vek):
                v[x["id"]] = {"h": _hash(x), "e": e}
            neu += len(teil)
        for k in weg:
            v.pop(k, None)
        if neu or weg:
            self._speichern()
        return neu

    def _speichern(self) -> None:
        with self._lock:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.pfad.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._daten, separators=(",", ":")), encoding="utf-8")
            os.replace(tmp, self.pfad)

    def vektor(self, doc: dict) -> list[float] | None:
        x = ((self._daten or {}).get("v") or {}).get(doc["id"])
        return x["e"] if x and x.get("h") == _hash(doc) else None


# -- Suche -------------------------------------------------------------------------------------------------------------
def wortsuche(frage: str, docs: list[dict]) -> list[str]:
    rang = ranking.bm25_ranking(frage, [(x["id"], ranking.tokenize(x["titel"]) * 2 + ranking.tokenize(x["text"]))
                                        for x in docs])
    return [k for k, _ in rang]


def suchen(frage: str, docs: list[dict], *, index: VektorIndex | None = None, einbetter: Einbetter | None = None,
           limit: int = 8, max_neu: int = STAPEL) -> dict:
    """-> {modus: "bedeutung+wort" | "wort", treffer: [doc + rang]}. Neue Dokumente werden nebenbei eingebettet."""
    nach_id = {x["id"]: x for x in docs}
    listen = [wortsuche(frage, docs)]
    modus = "wort"
    if index is not None and einbetter is not None and docs:
        index.aktualisieren(docs, einbetter, max_neu=max_neu)
        q = einbetter.einbetten([ANWEISUNG + frage], timeout=8)
        if q:
            sims = [(x["id"], sum(a * b for a, b in zip(q[0], vec))) for x in docs if (vec := index.vektor(x))]
            if sims:
                sims.sort(key=lambda t: t[1], reverse=True)
                listen.append([k for k, _ in sims[:50]])
                modus = "bedeutung+wort"
    punkte: dict[str, float] = {}
    for liste in listen:
        for rang, k in enumerate(liste[:50]):
            punkte[k] = punkte.get(k, 0.0) + 1.0 / (RRF_K + rang + 1)
    beste = sorted(punkte, key=lambda k: punkte[k], reverse=True)[:limit]
    return {"modus": modus, "treffer": [nach_id[k] for k in beste]}


def hintergrund_aktualisieren(root: Path | str, secrets: dict | None, **quellen) -> int:
    """Fuer den Bot-Takt: ganzen Index nachziehen (Erstaufbau, neue Vorgaenge). Fehler -> 0."""
    e = einbetter_aus(secrets)
    if e is None:
        return 0
    try:
        return VektorIndex(Path(root) / INDEX).aktualisieren(dokumente(root, **quellen), e)
    except Exception as exc:
        print(f"[gedaechtnis] Index: {exc.__class__.__name__}: {str(exc)[:120]}", flush=True)
        return 0
