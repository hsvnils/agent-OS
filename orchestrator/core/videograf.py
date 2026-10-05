"""Videograf-Vorschlaege in der Konzept-Mappe (VIDEOGRAF_ROADMAP V3, CEO 2026-10-05).

Agent 17 (Charta `agents/17_videograf.md` + Skills `skills/vid/*` als System-Prompt) bekommt den Kontext einer Idee bzw.
eines Skripts aus der Konzept-Mappe und liefert einen **Vorschlag**: Shotlist-Szenen (Felder wie die Szenen der Mappe),
Licht/Ton, Equipment, Ablauf. Nichts wird gespeichert -- der CEO uebernimmt einzelne Szenen per Klick (Quelle
„Videograf-Agent (Vorschlag)“). An das Modell gehen Briefing, Idee/Skript, vorhandene Szenen und Drehort/-zeit; **keine**
Ansprechpartner, Telefonnummern, Freigabe-Personen oder Notizen (koennen Personenbezug haben).
"""
from __future__ import annotations

import json
import re

from .konzept import BRIEFING, SKRIPT, SZENE

QUELLE = "Videograf-Agent (Vorschlag)"
MODELL = "gemini-2.5-flash"
MAX_SZENEN = 15
_BRIEFING_OHNE = {"freigabe_an", "notizen"}                    # koennen Namen/Interna enthalten
_DREH_MIT = ("datum", "zeit", "ort", "mitbringen")              # ohne Ansprechpartner/Telefon

AUFTRAG = """Erstelle als Videograf-Berater einen Vorschlag fuer den Dreh der folgenden Idee bzw. des Skripts. Nutze deine
Skills (Shotlist, Bildsprache/Kamera, Licht/Ton, Equipment/Drehplan, B-Roll). Hochformat 9:16, Hook-Shot zuerst, 8-15
Szenen, keine Szenen doppeln, die schon in der Shotlist stehen. Antworte NUR mit einem JSON-Objekt ohne weiteren Text:
{"szenen": [{"titel": "kurze Bezeichnung", "einstellung": "Einstellungsgroesse, Perspektive, Bewegung", "ort": "",
  "requisite": "Personen/Requisite", "dauer": "z. B. 3 s", "notiz": "Ton/Licht/Hinweis"}],
 "licht_ton": "2-4 Saetze", "equipment": ["..."], "ablauf": "2-4 Saetze zum Drehablauf", "hinweise": "Risiken/Rechte als Hinweis"}
Deutsch, praxisnah, nichts erfinden, was dem Briefing widerspricht."""


def kontext(mappe: dict, art: str, bezug: str, slots: list[dict] | None = None) -> str:
    """Kontexttext fuer das Modell -- nur Inhalte ohne Kontaktdaten."""
    b = mappe.get("briefing") or {}
    teile = ["# Briefing"] + [f"- {label}: {b[k]}" for k, label, _ in BRIEFING if b.get(k) and k not in _BRIEFING_OHNE]
    if art == "idee":
        i = (mappe.get("ideen") or {}).get(bezug)
        if not i:
            raise KeyError(bezug)
        teile += ["# Idee", f"- Titel: {i.get('titel', '')}"] + [f"- {k}: {i[k]}" for k in ("beschreibung", "format", "ziel") if i.get(k)]
    elif art == "skript":
        s = (mappe.get("skripte") or {}).get(bezug)
        if not s:
            raise KeyError(bezug)
        slot = next((x for x in slots or [] if f"S-{x['position']}-{x['nr']}" == bezug), {})
        teile += ["# Skript" + (f" ({slot['titel']})" if slot.get("titel") else "")] + [
            f"- {label}: {s[k]}" for k, label, _ in SKRIPT if s.get(k)]
    else:
        raise ValueError("Bezug: idee oder skript.")
    vorhanden = [z for z in mappe.get("szenen_liste") or []]
    if vorhanden:
        teile += ["# Bereits in der Shotlist"] + [f"- {z.get('titel', '')} ({z.get('einstellung', '')})" for z in vorhanden]
    d = mappe.get("dreh") or {}
    if any(d.get(k) for k in _DREH_MIT):
        teile += ["# Drehplan"] + [f"- {k}: {d[k]}" for k in _DREH_MIT if d.get(k)]
    return "\n".join(teile)


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError("Der Videograf hat keinen auswertbaren Vorschlag geliefert -- bitte erneut versuchen.")
    return json.loads(m.group(0))


def pruefen(roh: dict) -> dict:
    """Modell-Antwort -> {szenen: [{SZENE-Felder}], licht_ton, equipment, ablauf, hinweise} (gekuerzt, validiert)."""
    grenzen = {k: n for k, _, n in SZENE}
    szenen = []
    for z in (roh.get("szenen") or [])[:MAX_SZENEN]:
        if not isinstance(z, dict) or not str(z.get("titel") or "").strip():
            continue
        szenen.append({k: str(z.get(k) or "").strip()[:n] for k, n in grenzen.items()})
    if not szenen:
        raise ValueError("Der Videograf hat keine Szenen vorgeschlagen -- bitte erneut versuchen.")
    eq = roh.get("equipment") or []
    eq = [str(x).strip()[:120] for x in (eq if isinstance(eq, list) else [eq]) if str(x).strip()][:20]
    return {"szenen": szenen, "equipment": eq,
            **{k: str(roh.get(k) or "").strip()[:1500] for k in ("licht_ton", "ablauf", "hinweise")}}


def vorschlag(mappe: dict, art: str, bezug: str, *, system: str, client, modell: str = MODELL,
              slots: list[dict] | None = None) -> dict:
    nutzer = f"{AUFTRAG}\n\n{kontext(mappe, art, bezug, slots)}"
    r = client.chat.completions.create(model=modell, max_tokens=6000, messages=[
        {"role": "system", "content": system}, {"role": "user", "content": nutzer}])
    return pruefen(_json(r.choices[0].message.content or "")) | {"art": art, "bezug": bezug, "quelle": QUELLE}
