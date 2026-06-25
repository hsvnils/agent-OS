"""Kanal-unabhaengige konversationelle HoA-Schleife (Anthropic-API + Tools).

Genutzt vom Text-Kanal (Telegram). Fuehrt die Tool-Calling-Schleife: Modell antwortet -> ruft ggf. Tools
(`hoa_tools`) -> Ergebnisse zurueck -> finale Textantwort. Haelt den Gespraechsverlauf. Modell-Client ist
injizierbar -> offline mit Mock testbar (ohne Kosten).
"""
from __future__ import annotations

import json

from .hoa_tools import ToolContext, run_tool, tool_specs

TEXT_SYSTEM_PROMPT = (
    "Du bist LUNA, der Head of Agents des Hanserautisch Agenten-Unternehmens, und sprichst mit dem CEO "
    "(Nils) ueber Telegram. Antworte auf Deutsch, knapp und klar (Text). Beantworte Konversation selbst; nutze "
    "Werkzeuge nur bei Bedarf: 'frage_finance' fuer echte Finanzzahlen, 'delegate' fuer Fachfragen an "
    "Spezialisten (nur Beratung), 'set_budget' wenn der CEO ein Monatsbudget nennt (Zahl vorher bestaetigen). "
    "Aenderungen/Ideen laufen ueber Antraege: 'antrag_stellen' (wird dem CEO vorgelegt, nicht ausgefuehrt), "
    "'antraege_zeigen', 'antrag_freigeben'/'antrag_ablehnen' nur auf ausdrueckliche CEO-Ansage. Einen "
    "freigegebenen Antrag setzt du mit 'antrag_umsetzen' real um (Branch + Tests, kein Merge) und fasst den "
    "Bericht zusammen; nach main nur mit 'antrag_mergen' nach CEO-Bestaetigung. Bei CEO-Tor-Themen (Geld, "
    "Recht, Oeffentlichkeit, neue Kosten, Mandat, Datenloeschung) nichts eigenmaechtig tun, sondern Freigabe "
    "einholen. Stammt ein Auftrag vom CEO, genuegt eine kurze Rueckfrage; eine Idee aus einer Abteilung legst "
    "du dem CEO zuerst als Plan dar. "
    "Weitere Werkzeuge: 'recherche_beauftragen' (Researcher sucht im Web, mit Ticket; 'eskalation=true' fuer "
    "Revision/tiefere Recherche), Google ('mail_suchen/lesen/entwurf/senden', 'kalender_agenda', "
    "'termin_anlegen', 'drive_suchen/lesen', 'tabelle_lesen/schreiben' -- Senden/Aendern nur mit "
    "bestaetigt=true nach CEO-Ja), 'wissensstand'/'dept_briefing'/'github_trends'/'watch_digest' (Monitoring), "
    "'innovation_scouting'/'selbstentwicklung' (Vorschlag als Antrag), 'briefing_jetzt', 'notiz_hinzufuegen', "
    "'systemcheck', 'autonomie_pausieren' (Notbremse). Um dich proaktiv beim CEO zu melden: 'melde_an_ceo' "
    "(Feld 'abteilung' setzen, 'detail' fuer Rueckfragen). "
    "WICHTIG: Schreibe alle Antworten an den CEO mit korrekten deutschen Umlauten (ä, ö, ü, ß) -- niemals ae/oe/ue/ss."
)


class HoaConversation:
    def __init__(self, ctx: ToolContext, *, api_key: str | None = None,
                 model: str = "claude-haiku-4-5", client=None, max_tool_iterations: int = 8):
        self.ctx = ctx
        self.model = model
        self.max_iter = max_tool_iterations
        self.tools = tool_specs()
        self.messages: list[dict] = []
        if client is not None:
            self.client = client
        else:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)

    def respond(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        for _ in range(self.max_iter):
            resp = self.client.messages.create(
                model=self.model, max_tokens=1024, system=TEXT_SYSTEM_PROMPT,
                tools=self.tools, messages=self.messages,
            )
            self.messages.append({"role": "assistant", "content": resp.content})
            tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
            if not tool_uses:
                return _text(resp.content)
            results = []
            for tu in tool_uses:
                out = run_tool(tu.name, dict(tu.input or {}), self.ctx)
                results.append({"type": "tool_result", "tool_use_id": tu.id,
                                "content": json.dumps(out, ensure_ascii=False)})
            self.messages.append({"role": "user", "content": results})
        return "Ich konnte das gerade nicht abschliessen -- bitte praezisiere kurz."


def _text(content) -> str:
    return " ".join(getattr(b, "text", "") for b in content
                    if getattr(b, "type", None) == "text").strip()
