"""Collab-Radar Phase 2 -- KI-Analyse je Gespraech (modell-agnostisch).

Nimmt den Verlauf eines Kontakts (ein+ausgehend) und laesst ein **guenstiges** Modell erkennen:
  - `collab`        : geht es um eine Collab/Partnerschaft/Kooperation/Sponsoring? (bool)
  - `zusammenfassung`: worum es geht (kurz)
  - `stand`         : aktueller Stand (kurz)
  - `offene_todos`  : offene Aufgaben / naechste Schritte (Liste)
  - `warten_auf`    : 'uns' | 'kontakt' | 'niemand' (wer ist am Zug?)

**Modell-agnostisch** (AGENTS.md): das LLM ist per `analyse_llm_aus_env` austauschbar -- Claude Haiku
(Anthropic), Gemini Flash (Google, OpenAI-kompatibel) oder OpenAI. Nur bei NEUEN Nachrichten neu analysieren
(`IgInboxStore.braucht_analyse`) -> minimale Kosten. Datenschutz-Hinweis: Gemini **Free-Tier** nutzt Inhalte
zum Training -> fuer private Partner-DMs Bezahl-Tier oder Anthropic waehlen (Modell via `IG_ANALYSE_MODELL`).
"""
from __future__ import annotations

import json

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

_SYSTEM = (
    "Du analysierst einen Instagram-DM-Verlauf zwischen unserem Unternehmen ('Wir') und einem Kontakt. "
    "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt (kein weiterer Text) mit den Feldern: "
    "collab (true/false: geht es um eine Collab/Partnerschaft/Kooperation/Sponsoring/Werbung?), "
    "zusammenfassung (<=200 Zeichen, worum es geht), "
    "stand (<=120 Zeichen, aktueller Stand), "
    "offene_todos (Array kurzer Strings: offene Aufgaben/naechste Schritte; leer wenn keine), "
    "warten_auf ('uns' wenn WIR antworten/handeln muessen, 'kontakt' wenn wir auf den Kontakt warten, "
    "'niemand' wenn nichts offen ist). Antworte auf Deutsch."
)


def _transcript(verlauf: list[dict], *, max_nachrichten: int = 40) -> str:
    """Verlauf (aelteste zuerst) -> kompaktes, richtungs-annotiertes Transkript fuer das Modell. Reine
    Medien-/Reaktions-Nachrichten (ohne Text) werden ausgelassen -> kein Modellaufruf ohne analysierbaren
    Inhalt (spart Kosten)."""
    zeilen = []
    for m in verlauf[-max_nachrichten:]:
        if m.get("medien"):
            continue
        text = (m.get("text") or "").replace("\n", " ").strip()
        if not text:
            continue
        wer = "Wir" if m.get("richtung") == "aus" else "Kontakt"
        zeilen.append(f"{wer}: {text}")
    return "\n".join(zeilen)


def _json_aus_text(s: str) -> dict:
    """Robustes JSON-Parsen: schneidet das erste {...} heraus (Modelle umrahmen JSON gern mit Text)."""
    s = (s or "").strip()
    a, b = s.find("{"), s.rfind("}")
    if a >= 0 and b > a:
        try:
            return json.loads(s[a:b + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def _anthropic_call(modell: str, key: str):
    def call(system, user):
        import anthropic
        r = anthropic.Anthropic(api_key=key).messages.create(
            model=modell, max_tokens=700, system=system, messages=[{"role": "user", "content": user}])
        return "".join(getattr(b, "text", "") for b in r.content if getattr(b, "type", "") == "text")
    return call


def _openai_call(modell: str, key: str, base_url):
    def call(system, user):
        import openai
        r = openai.OpenAI(api_key=key, base_url=base_url or None).chat.completions.create(
            model=modell, max_tokens=700,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return r.choices[0].message.content or ""
    return call


def analyse_llm_aus_env(env: dict):
    """Baut die LLM-Callable `(system, user) -> str` gemaess Config. Provider automatisch:
      - `IG_ANALYSE_BASE_URL` gesetzt -> **eigener/lokaler** OpenAI-kompatibler Endpunkt (Ollama/LM Studio/
        vLLM); Key `IG_ANALYSE_KEY` (Default 'local'). -> spaeterer Wechsel auf lokales LLM = nur .env.
      - Modell `claude*` -> Anthropic (ANTHROPIC_API_KEY)
      - Modell `gemini*` -> Google, OpenAI-kompatibel (GEMINI_API_KEY)
      - sonst (`gpt*` etc.) -> OpenAI (OPENAI_API_KEY)
    Gibt None, wenn kein passender Key vorhanden ist."""
    modell = (env.get("IG_ANALYSE_MODELL") or "gemini-flash-latest").strip()
    low = modell.lower()
    base_url_override = (env.get("IG_ANALYSE_BASE_URL") or "").strip()
    if base_url_override:                                    # lokales/eigenes Modell (OpenAI-kompatibel)
        return _openai_call(modell, env.get("IG_ANALYSE_KEY") or "local", base_url_override)
    if low.startswith("claude"):
        key = env.get("ANTHROPIC_API_KEY")
        return _anthropic_call(modell, key) if key else None
    if low.startswith("gemini"):
        key, base_url = env.get("GEMINI_API_KEY"), GEMINI_BASE_URL
    else:
        key, base_url = env.get("OPENAI_API_KEY"), None
    return _openai_call(modell, key, base_url) if key else None


class IgAnalyzer:
    def __init__(self, *, llm=None, modell: str = "?"):
        self.llm = llm            # Callable(system, user) -> str; None = nicht verfuegbar
        self.modell = modell

    def verfuegbar(self) -> bool:
        return callable(self.llm)

    def analysiere(self, verlauf: list[dict]) -> dict:
        """Ein Gespraech analysieren -> {collab, zusammenfassung, stand, offene_todos, warten_auf, modell}."""
        transcript = _transcript(verlauf)
        if not transcript:
            return {"collab": False, "zusammenfassung": "", "stand": "", "offene_todos": [],
                    "warten_auf": "niemand", "modell": self.modell}
        roh = self.llm(_SYSTEM, transcript)
        d = _json_aus_text(roh)
        todos = d.get("offene_todos") or []
        if isinstance(todos, str):
            todos = [todos]
        warten = str(d.get("warten_auf") or "niemand").lower()
        if warten not in ("uns", "kontakt", "niemand"):
            warten = "niemand"
        return {"collab": bool(d.get("collab")), "zusammenfassung": str(d.get("zusammenfassung") or "")[:240],
                "stand": str(d.get("stand") or "")[:160], "offene_todos": [str(t)[:160] for t in todos][:8],
                "warten_auf": warten, "modell": self.modell}

    def analysiere_store(self, store, *, max_kontakte: int = 50, nur_neue: bool = True) -> dict:
        """Analysiert alle (ggf. nur analysebeduerftigen) Kontakte im Store und speichert das Ergebnis.
        Gibt {ok, analysiert, collab, uebersprungen, modell}."""
        if not self.verfuegbar():
            return {"ok": False, "hinweis": "Kein Analyse-Modell/Key (IG_ANALYSE_MODELL + passender API-Key)."}
        analysiert = collab = uebersprungen = 0
        for c in store.kontakte():
            if analysiert >= max_kontakte:
                break
            cid = c["contact_id"]
            if nur_neue and not store.braucht_analyse(cid):
                uebersprungen += 1
                continue
            verlauf = store.verlauf(cid)
            res = self.analysiere(verlauf)
            res["letzte_nachricht_ts"] = c.get("letzte_ts") or ""
            store.analyse_setzen(cid, res)
            analysiert += 1
            if res.get("collab"):
                collab += 1
        return {"ok": True, "analysiert": analysiert, "collab": collab, "uebersprungen": uebersprungen,
                "modell": self.modell}
