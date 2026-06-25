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
    "Tickets: dein aktiver Stand sind die OFFENEN Tickets ('offene_tickets', abteilungsuebergreifend); "
    "geschlossene liegen im Abteilungsarchiv und holst du nur bei Bedarf ('abteilung_tickets'). "
    "Kostensenkung: 'kosten_optimierung' laesst den CFO Freeware-/Token-Sparpotenziale pruefen. "
    "Du hast KEINE Timer-/Erinnerungsfunktion: versprich NIEMALS, dich 'in X Minuten' von selbst zu melden. "
    "Erledige Aufgaben sofort, oder sage klar, dass der CEO nachfragen soll; fuer Hintergrund-Ergebnisse "
    "meldet sich der Watcher/Self-Maintenance ohnehin automatisch via 'melde_an_ceo'. "
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
        self._repariere_verlauf()  # evtl. kaputten Tail (tool_use ohne tool_result) entfernen
        self.messages.append({"role": "user", "content": user_text})
        for _ in range(self.max_iter):
            try:
                resp = self.client.messages.create(
                    model=self.model, max_tokens=1024, system=TEXT_SYSTEM_PROMPT,
                    tools=self.tools, messages=self.messages,
                )
            except Exception as exc:
                # Kaputter Verlauf (z. B. 'tool_use ids ohne tool_result') -> Verlauf zuruecksetzen
                # und EINMAL frisch versuchen, damit der Chat nicht dauerhaft blockiert.
                if self._ist_verlauf_fehler(exc):
                    self.messages = [{"role": "user", "content": user_text}]
                    try:
                        resp = self.client.messages.create(
                            model=self.model, max_tokens=1024, system=TEXT_SYSTEM_PROMPT,
                            tools=self.tools, messages=self.messages)
                    except Exception as exc2:
                        self.messages = []
                        return _fehlertext(exc2)
                else:
                    return _fehlertext(exc)
            self.messages.append({"role": "assistant", "content": resp.content})
            tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
            if not tool_uses:
                return _text(resp.content)
            # WICHTIG: JEDES tool_use bekommt ein tool_result -- auch bei Tool-Fehler. Sonst wird der
            # Verlauf ungueltig und die Anthropic-API lehnt jede weitere Nachricht ab (400).
            results = []
            for tu in tool_uses:
                try:
                    out = run_tool(tu.name, dict(tu.input or {}), self.ctx)
                except Exception as exc:
                    out = {"ok": False, "fehler": f"Werkzeug '{tu.name}' fehlgeschlagen: {str(exc)[:240]}"}
                results.append({"type": "tool_result", "tool_use_id": tu.id,
                                "content": json.dumps(out, ensure_ascii=False)})
            self.messages.append({"role": "user", "content": results})
        return "Ich konnte das gerade nicht abschliessen -- bitte praezisiere kurz."

    def _repariere_verlauf(self) -> None:
        """Entfernt einen unvollstaendigen Tail: endet der Verlauf mit einem Assistant-tool_use ohne
        folgendes tool_result, ist er fuer eine neue Nutzer-Nachricht ungueltig -> abschneiden."""
        while self.messages:
            last = self.messages[-1]
            content = last.get("content")
            hat_tool_use = isinstance(content, list) and any(
                getattr(b, "type", None) == "tool_use" or (isinstance(b, dict) and b.get("type") == "tool_use")
                for b in content)
            if last.get("role") == "assistant" and hat_tool_use:
                self.messages.pop()
            else:
                break

    @staticmethod
    def _ist_verlauf_fehler(exc: Exception) -> bool:
        s = str(exc).lower()
        return "tool_result" in s or "tool_use" in s or ("400" in s and "invalid_request" in s)


def _text(content) -> str:
    return " ".join(getattr(b, "text", "") for b in content
                    if getattr(b, "type", None) == "text").strip()


def _fehlertext(exc: Exception) -> str:
    low = str(exc).lower()
    if "credit" in low or "balance" in low:
        return "Mein Modell-Guthaben ist gerade zu niedrig. Bitte spaeter erneut versuchen."
    if "overloaded" in low or "rate" in low or "529" in low or "429" in low:
        return "Die KI ist gerade ueberlastet. Bitte in einem Moment erneut fragen."
    return "Es gab gerade einen technischen Fehler. Ich habe den Verlauf bereinigt -- bitte stell die Frage neu."
