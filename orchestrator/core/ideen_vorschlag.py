"""Ideen- und Skript-Vorschlaege aus dem Briefing (KUNDEN_CHECKLISTE C3, CEO 2026-10-26).

Der Content-Agent (Charta `agents/10_cco-content.md` + Skills `skills/cco/*`, u. a. „briefing-zu-konzept“ und
„hook-und-skript“, als System-Prompt) bekommt das Briefing einer Konzept-Mappe und liefert **3 Ideen mit je einem
Skript-Geruest** (Hook, Text, Call to Action, Laenge). Nichts wird gespeichert -- der CEO uebernimmt einzelne Ideen per
Klick als Idee der Mappe (Status „idee“, Skript-Geruest in der Beschreibung). An das Modell gehen nur Briefing-Inhalte,
Kampagnentitel, Leistungen und die Titel vorhandener Ideen; **keine** Freigabe-Personen, Notizen oder Kontaktdaten.
Vorgeschlagen wird erst, wenn Ziel, Zielgruppe, Kernbotschaft und Tonalitaet im Briefing stehen.
"""
from __future__ import annotations

import json
import re

from .konzept import BRIEFING

QUELLE = "Content-Agent (Vorschlag)"
ANZAHL = 3
PFLICHT = ("ziel", "zielgruppe", "botschaft", "tonalitaet")
_BRIEFING_OHNE = {"freigabe_an", "notizen"}                    # koennen Namen/Interna enthalten

AUFTRAG = """Entwickle aus dem folgenden Briefing genau 3 unterschiedliche Content-Ideen fuer Social Media (Hochformat 9:16)
mit je einem Skript-Geruest. Nutze deine Skills (Briefing zu Konzept, Hook und Skript, Reel-Dramaturgie). Keine Idee, die
schon in der Mappe steht. Antworte NUR mit einem JSON-Objekt ohne weiteren Text:
{"ideen": [{"titel": "kurz", "beschreibung": "2-4 Saetze: Was passiert, warum es zum Ziel passt", "format": "z. B. Reel",
  "ziel": "welches Ziel aus dem Briefing", "hook": "erste 3 Sekunden", "text": "Ablauf / Voice-over in Stichpunkten",
  "cta": "Call to Action", "laenge": "z. B. 20-30 s"}]}
Deutsch, im Ton des Briefings, nichts erfinden, was dem Briefing widerspricht; Pflichtangaben und Don'ts beachten."""

GRENZEN = {"titel": 160, "beschreibung": 900, "format": 60, "ziel": 60, "hook": 300, "text": 700, "cta": 200, "laenge": 40}


def fehlende(mappe: dict) -> list[str]:
    b = mappe.get("briefing") or {}
    labels = {k: lbl for k, lbl, _ in BRIEFING}
    return [labels[k] for k in PFLICHT if not str(b.get(k) or "").strip()]


def kontext(mappe: dict, titel: str = "", slots: list[dict] | None = None) -> str:
    b = mappe.get("briefing") or {}
    teile = (["# Kampagne", f"- Titel: {titel}"] if titel else []) + ["# Briefing"] + [
        f"- {label}: {b[k]}" for k, label, _ in BRIEFING if b.get(k) and k not in _BRIEFING_OHNE]
    leistungen = [s.get("titel") or s.get("beschreibung") for s in slots or [] if (s.get("titel") or s.get("beschreibung"))]
    if leistungen:
        teile += ["# Gebuchte Leistungen"] + [f"- {x}" for x in leistungen[:20]]
    ideen = [i.get("titel", "") for i in (mappe.get("ideen") or {}).values() if i.get("titel")]
    if ideen:
        teile += ["# Ideen, die schon in der Mappe stehen"] + [f"- {x}" for x in ideen[:30]]
    return "\n".join(teile)


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError("Der Content-Agent hat keinen auswertbaren Vorschlag geliefert -- bitte erneut versuchen.")
    return json.loads(m.group(0))


def pruefen(roh: dict) -> list[dict]:
    out = []
    for i in (roh.get("ideen") or [])[:ANZAHL]:
        if isinstance(i, dict) and str(i.get("titel") or "").strip():
            out.append({k: str(i.get(k) or "").strip()[:n] for k, n in GRENZEN.items()})
    if not out:
        raise ValueError("Der Content-Agent hat keine Ideen vorgeschlagen -- bitte erneut versuchen.")
    return out


def vorschlag(mappe: dict, *, system: str, client, modell: str, titel: str = "", slots: list[dict] | None = None) -> dict:
    offen = fehlende(mappe)
    if offen:
        raise ValueError("Briefing unvollständig – bitte erst ausfüllen: " + ", ".join(offen) + ".")
    r = client.chat.completions.create(model=modell, max_tokens=6000, messages=[
        {"role": "system", "content": system}, {"role": "user", "content": f"{AUFTRAG}\n\n{kontext(mappe, titel, slots)}"}])
    return {"ideen": pruefen(_json(r.choices[0].message.content or "")), "quelle": QUELLE}


def als_idee(i: dict) -> dict:
    """Vorschlag -> Felder fuer `KonzeptStore.idee` (Skript-Geruest in der Beschreibung, max. 2000 Zeichen)."""
    geruest = "\n".join(x for x in (f"Hook: {i['hook']}" if i.get("hook") else "", f"Ablauf: {i['text']}" if i.get("text") else "",
                                     f"CTA: {i['cta']}" if i.get("cta") else "", f"Länge: {i['laenge']}" if i.get("laenge") else "") if x)
    text = (i.get("beschreibung") or "") + (f"\n\nSkript-Gerüst ({QUELLE})\n{geruest}" if geruest else "")
    return {"titel": i["titel"], "beschreibung": text[:2000], "format": i.get("format", ""), "ziel": i.get("ziel", "")}
