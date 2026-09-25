"""Lokales LLM (Ollama auf dem MACO470, M6) als OpenAI-kompatibler Anbieter -- per .env zuschaltbar.

Ziel (CEO 2026-09-25): API-Token Richtung Anthropic/OpenAI so niedrig wie moeglich halten; lange Antwortzeiten
des lokalen Modells sind in Ordnung. Deshalb kann das lokale Modell je Bereich ZUERST gefragt werden (Cloud nur
noch als Fallback) oder ZULETZT (nur als Notnagel, wenn alle Cloud-Anbieter ausfallen).

.env-Schluessel (alle optional; ohne BASE_URL + MODEL + Modus bleibt alles wie bisher):
  LOCAL_LLM_BASE_URL     z. B. http://192.168.178.184:11434/v1
  LOCAL_LLM_MODEL        z. B. qwen3:30b-a3b
  LOCAL_LLM_FACHAGENTEN  zuerst | zuletzt | aus   (FallbackBackend: Fachagenten, CFO-, Self-Dev-, Content-Jobs)
  LOCAL_LLM_CHAT         zuerst | zuletzt | aus   (ModelRouter: Telegram-/Web-Chat mit Werkzeugen)
  LOCAL_LLM_TIMEOUT      Sekunden je Aufruf (Standard 300 -- Denkschritte dauern)
  LOCAL_LLM_MAX_TOKENS   Standard 4096 (Denkschritte verbrauchen Tokens; 1024 reicht nicht)
  LOCAL_LLM_KEY          beliebig (Ollama prueft keinen Key)

Wichtig (docs/bekannte-fehler.md BF-17): Das Kontextfenster muss am Ollama-Server gross genug sein
(OLLAMA_CONTEXT_LENGTH >= 16384), sonst kuerzt Ollama LUNAs Werkzeugliste still.
"""
from __future__ import annotations

import re
import urllib.request

BEREICHE = ("fachagenten", "chat")
MODI = ("zuerst", "zuletzt")

_DENKTEXT = re.compile(r"<think>.*?</think>\s*", re.S)


def eintrag(secrets: dict, bereich: str) -> dict | None:
    """Fallback-Eintrag fuer ModelRouter/FallbackBackend -- oder None, wenn fuer `bereich` nicht aktiv."""
    s = secrets or {}
    url, modell = (s.get("LOCAL_LLM_BASE_URL") or "").strip(), (s.get("LOCAL_LLM_MODEL") or "").strip()
    modus = (s.get(f"LOCAL_LLM_{bereich.upper()}") or "aus").strip().lower()
    if not url or not modell or modus not in MODI:
        return None
    return {"name": "lokal", "key": s.get("LOCAL_LLM_KEY") or "lokal", "base_url": url, "model": modell,
            "zuerst": modus == "zuerst", "timeout": _zahl(s.get("LOCAL_LLM_TIMEOUT"), 300.0),
            "max_tokens": int(_zahl(s.get("LOCAL_LLM_MAX_TOKENS"), 4096)), "max_retries": 0,
            "kuerzung_pruefen": True}


def geschaetzte_tokens(*teile) -> int:
    """Grobe Token-Schaetzung (JSON-Zeichen / 3,5) -- nur um stilles Kuerzen durch den Server zu erkennen."""
    import json
    return int(sum(len(json.dumps(t, ensure_ascii=False, default=str)) for t in teile) / 3.5)


def gekuerzt(gemeldet: int, geschaetzt: int) -> bool:
    """Ollama kuerzt einen zu langen Prompt STILL (BF-17) und meldet dann deutlich weniger prompt_tokens, als
    geschickt wurden (gemessen: 2.050 statt ~11.800). Weniger als die Haelfte der Schaetzung = gekuerzt."""
    return geschaetzt > 2000 and 0 < gemeldet < geschaetzt * 0.5


def aktiv(secrets: dict) -> bool:
    return any(eintrag(secrets, b) for b in BEREICHE)


def ohne_denktext(text: str | None) -> str:
    """Entfernt <think>…</think>-Bloecke (Qwen3 u. a.), die manche Server in den Inhalt schreiben."""
    return _DENKTEXT.sub("", text or "").strip()


def erreichbar(base_url: str, timeout: float = 3.0) -> tuple[bool, str]:
    """Leichter Health-Check ohne LLM-Aufruf: GET <base_url>/models."""
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/models", timeout=timeout) as r:
            return (r.status == 200, "" if r.status == 200 else f"HTTP {r.status}")
    except Exception as exc:  # noqa: BLE001 -- jeder Fehler heisst: nicht erreichbar
        return False, f"nicht erreichbar ({exc.__class__.__name__}) -- MACO470/Ollama pruefen; Cloud uebernimmt."


def _zahl(wert, standard: float) -> float:
    try:
        return float(wert) if wert not in (None, "") else standard
    except ValueError:
        return standard
