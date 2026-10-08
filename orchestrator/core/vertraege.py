"""Vertragswerk -- Vorlagen-Bibliothek (VERTRAGSWERK_ROADMAP V1/V2, CEO-Entscheidungen 2026-10-05).

Vorlagen (AGB, Kooperationsvertrag, Nutzungsrechte-Vereinbarung, NDA) bestehen aus Paragraphen mit Platzhaltern
(`{Kunde}`, `{Leistungen}` …) und haben **Versionen**. Jede Version hat einen Status: *Entwurf* (Standard; erster Entwurf von Claude Code,
„anwaltliche Pruefung erforderlich“), *geprueft* (mit Pruefer, Datum und optional dem Pruefdokument in der Firmenakte)
oder *ausser Kraft*. **Nur eine gepruefte Version darf an Kunden** (V3/V4). Den Status setzt nur der CEO. Alles steht
als Ereignis `vertrag_vorlage_*` in der Hash-Kette; eine Version wird nie geaendert -- Aenderung = neue Version.
"""
from __future__ import annotations

import re
from datetime import date

from .buchhaltung import Buchhaltung

ARTEN = {"agb": "Allgemeine Geschäftsbedingungen", "kooperation": "Kooperationsvertrag (Content/Influencer)",
         "nutzungsrechte": "Nutzungsrechte-Vereinbarung", "nda": "Vertraulichkeitsvereinbarung (NDA)",
         "einwilligung": "Einwilligung in Bild- und Videoaufnahmen"}          # EINWILLIGUNG_AUFNAHMEN E1
STATUS = ("entwurf", "geprueft", "ausser_kraft")
STATUS_TEXT = {"entwurf": "Entwurf – anwaltliche Prüfung erforderlich", "geprueft": "geprüft", "ausser_kraft": "außer Kraft"}
PLATZHALTER = re.compile(r"\{([A-Za-zÄÖÜäöüß_]+)\}")
MAX_PARAGRAPHEN = 40


def platzhalter(paragraphen: list[dict]) -> list[str]:
    gesehen: list[str] = []
    for p in paragraphen:
        for n in PLATZHALTER.findall(f"{p.get('titel', '')} {p.get('text', '')}"):
            if n not in gesehen:
                gesehen.append(n)
    return gesehen


def _paragraphen(roh) -> list[dict]:
    if not isinstance(roh, list) or not roh:
        raise ValueError("Mindestens ein Paragraph noetig.")
    if len(roh) > MAX_PARAGRAPHEN:
        raise ValueError(f"Hoechstens {MAX_PARAGRAPHEN} Paragraphen.")
    out = []
    for i, p in enumerate(roh, 1):
        titel, text = str((p or {}).get("titel") or "").strip()[:160], str((p or {}).get("text") or "").strip()[:8000]
        if not titel or not text:
            raise ValueError(f"Paragraph {i}: Titel und Text sind Pflicht.")
        out.append({"titel": titel, "text": text})
    return out


class VertragStore:
    def __init__(self, bh: Buchhaltung):
        self.bh = bh

    @staticmethod
    def _falte(eintraege: list[dict]) -> dict[str, dict]:
        out = {a: {"art": a, "name": n, "versionen": []} for a, n in ARTEN.items()}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            if t == "vertrag_vorlage_version" and d.get("art") in out:
                out[d["art"]]["versionen"].append({k: d.get(k) for k in ("version", "titel", "paragraphen", "quelle", "hinweis")}
                                                   | {"angelegt": e["ts"], "von": e.get("von", ""), "status": "entwurf",
                                                      "verlauf": [{"ts": e["ts"], "von": e.get("von", ""), "status": "entwurf"}]})
            elif t == "vertrag_vorlage_status" and d.get("art") in out:
                for v in out[d["art"]]["versionen"]:
                    if v["version"] == d["version"]:
                        v["status"] = d["status"]
                        v |= {k: d.get(k) for k in ("pruefer", "datum", "notiz", "akte_id") if d.get(k)}
                        v["verlauf"].append({"ts": e["ts"], "von": e.get("von", ""), "status": d["status"],
                                             "notiz": d.get("notiz", "")})
        for x in out.values():
            for v in x["versionen"]:
                v["platzhalter"] = platzhalter(v["paragraphen"])
            x["aktuell"] = x["versionen"][-1]["version"] if x["versionen"] else None
            gepr = [v for v in x["versionen"] if v["status"] == "geprueft"]
            x["in_kraft"] = gepr[-1]["version"] if gepr else None        # die juengste gepruefte Version gilt
        return out

    def liste(self) -> list[dict]:
        return [{k: x[k] for k in ("art", "name", "aktuell", "in_kraft")}
                | {"versionen": len(x["versionen"]),
                   "status": (next((v["status"] for v in x["versionen"] if v["version"] == x["aktuell"]), None))}
                for x in self._falte(self.bh.eintraege()).values()]

    def vorlage(self, art: str) -> dict:
        x = self._falte(self.bh.eintraege()).get(art)
        if not x:
            raise KeyError(art)
        return x

    def in_kraft(self, art: str) -> dict | None:
        """Die Version, die an Kunden darf (juengste gepruefte) -- sonst None."""
        x = self.vorlage(art)
        return next((v for v in x["versionen"] if v["version"] == x["in_kraft"]), None)

    def version_anlegen(self, art: str, *, titel: str, paragraphen, quelle: str = "CEO", hinweis: str = "",
                        von: str = "") -> dict:
        if art not in ARTEN:
            raise KeyError(art)
        par = _paragraphen(paragraphen)
        titel = str(titel or ARTEN[art]).strip()[:160]
        nr = len(self.vorlage(art)["versionen"]) + 1
        self.bh.erfassen_geprueft("vertrag_vorlage_version", {"art": art, "version": nr, "titel": titel, "paragraphen": par,
                                                              "quelle": str(quelle)[:60], "hinweis": str(hinweis)[:300]},
                                  von=von, pruefe=lambda e: self._naechste(art, nr, e))
        return {"art": art, "version": nr}

    def _naechste(self, art: str, nr: int, eintraege: list[dict]) -> None:
        if len(self._falte(eintraege)[art]["versionen"]) + 1 != nr:      # unter der Sperre: niemand war schneller
            raise ValueError("Inzwischen gibt es eine neuere Version -- bitte neu laden.")

    def status_setzen(self, art: str, version: int, status: str, *, pruefer: str = "", datum: str = "", notiz: str = "",
                      akte_id: str = "", von: str = "") -> dict:
        if status not in STATUS:
            raise ValueError("Status: entwurf, geprueft oder ausser_kraft.")
        x = self.vorlage(art)
        if not any(v["version"] == int(version) for v in x["versionen"]):
            raise KeyError(f"{art} v{version}")
        d = {"art": art, "version": int(version), "status": status, "notiz": str(notiz or "").strip()[:500]}
        if status == "geprueft":
            pruefer = str(pruefer or "").strip()[:120]
            if not pruefer:
                raise ValueError("Wer hat geprueft? (z. B. Name der Anwaeltin/Kanzlei)")
            try:
                tag = date.fromisoformat(str(datum)[:10]).isoformat()
            except ValueError:
                raise ValueError("Pruefdatum: JJJJ-MM-TT.") from None
            d |= {"pruefer": pruefer, "datum": tag} | ({"akte_id": str(akte_id)[:20]} if akte_id else {})
        self.bh.erfassen("vertrag_vorlage_status", d, von=von)
        return d

    def vergleich(self, art: str, a: int, b: int) -> list[dict]:
        """Paragraph fuer Paragraph (nach Titel): gleich / geaendert / neu / entfernt."""
        x = {v["version"]: v for v in self.vorlage(art)["versionen"]}
        if a not in x or b not in x:
            raise KeyError(f"{art} v{a}/v{b}")
        alt = {p["titel"]: p["text"] for p in x[a]["paragraphen"]}
        neu = {p["titel"]: p["text"] for p in x[b]["paragraphen"]}
        out = []
        for t, txt in neu.items():
            out.append({"titel": t, "art": "neu" if t not in alt else "gleich" if alt[t] == txt else "geaendert",
                        "alt": alt.get(t, ""), "neu": txt})
        out += [{"titel": t, "art": "entfernt", "alt": txt, "neu": ""} for t, txt in alt.items() if t not in neu]
        return out

    def entwuerfe_laden(self, *, von: str = "") -> list[str]:
        """V2: die ersten Entwuerfe (Claude Code, ungeprueft) als Version 1 anlegen -- nur fuer Vorlagen, die noch keine Version haben (CEO-Klick)."""
        from .vertrag_entwuerfe import ENTWUERFE
        neu = []
        for art, e in ENTWUERFE.items():
            if not self.vorlage(art)["versionen"]:
                self.version_anlegen(art, titel=e["titel"], paragraphen=e["paragraphen"], quelle="Entwurf Claude Code (ungeprüft)",
                                     hinweis="Entwurf – anwaltliche Prüfung erforderlich", von=von)
                neu.append(art)
        return neu
