"""Insights-Screenshots auslesen (PROJEKTBERICHT P2, CEO-Entscheidung 2026-10-02: Gemini liest die Bilder).

Ein oder mehrere Screenshots eines Postings gehen an Gemini (OpenAI-kompatible Schnittstelle, Paket `openai` ist schon
im Image); zurueck kommen nur die Felder des Formats als ganze Zahlen. Die Werte sind ein **Vorschlag** -- gespeichert
wird erst nach „✅ Stimmt“ des CEO (Telegram) bzw. „Speichern“ im Formular. Datenschutz: `docs/datenschutz-ki-nutzung.md`.
"""
from __future__ import annotations

import base64
import json
import re

from .model_router import GEMINI_BASE_URL

MODELL = "gemini-flash-latest"
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".heic": "image/heic"}


def _prompt(felder: list[tuple[str, str]], format_name: str) -> str:
    liste = "\n".join(f'- "{k}": {l}' for k, l in felder)
    return (f"Das sind Screenshots der Instagram/Facebook-Statistik (Insights) EINES {format_name}s. Lies die Zahlen ab "
            f"und antworte NUR mit einem JSON-Objekt mit diesen Schluesseln (ganze Zahlen, ohne Tausenderpunkte; "
            f"Wiedergabezeit in Sekunden; fehlt ein Wert, lass den Schluessel weg; nichts schaetzen):\n{liste}\n"
            "Hinweise: „Aufrufe“/„Views“ = aufrufe; „Erreichte Konten“/„Accounts reached“ = reichweite; "
            "„Impressionen“/„Impressions“ = impressionen; 1,2 Tsd. = 1200; 1,2 Mio. = 1200000.")


def zahlen_aus_antwort(text: str, felder: list[tuple[str, str]]) -> dict:
    """JSON aus der Modell-Antwort ziehen und streng pruefen: nur bekannte Felder, nur ganze Zahlen >= 0."""
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        roh = json.loads(m.group(0)) if m else {}
    except ValueError:
        roh = {}
    erlaubt = {k for k, _ in felder}
    out = {}
    for k, v in (roh if isinstance(roh, dict) else {}).items():
        if k not in erlaubt or isinstance(v, bool):
            continue
        if isinstance(v, str):
            v = v.strip().replace(".", "").replace(" ", "").replace(",", ".")
        try:
            n = int(round(float(v)))
        except (TypeError, ValueError):
            continue
        if 0 <= n <= 2_000_000_000:
            out[k] = n
    return out


def lesen(bilder: list[tuple[bytes, str]], felder: list[tuple[str, str]], format_name: str, *, key: str,
          modell: str = MODELL, client=None) -> dict:
    """Bilder [(daten, dateiname)] -> {feld: zahl}. `client` nur fuer Tests (OpenAI-kompatibel)."""
    if not bilder:
        return {}
    if client is None:
        if not key:
            raise ValueError("Kein Gemini-Schluessel -- bitte die Zahlen im Formular eintragen.")
        import openai
        client = openai.OpenAI(api_key=key, base_url=GEMINI_BASE_URL, timeout=60)
    inhalt = [{"type": "text", "text": _prompt(felder, format_name)}]
    for daten, name in bilder[:4]:
        endung = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ".jpg"
        url = f"data:{MIME.get(endung, 'image/jpeg')};base64,{base64.b64encode(daten).decode()}"
        inhalt.append({"type": "image_url", "image_url": {"url": url}})
    r = client.chat.completions.create(model=modell, messages=[{"role": "user", "content": inhalt}], max_tokens=2000)
    return zahlen_aus_antwort(r.choices[0].message.content or "", felder)
