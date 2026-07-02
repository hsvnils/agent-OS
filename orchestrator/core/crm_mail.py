"""Phase 19 -- CRM-Akte trackt Mails.

Ordnet **Gmail-Mails** bestehenden CRM-Firmen zu (Kanal `mail`), sodass die Unternehmensakte in der
Collab-CRM-App E-Mails **neben** den Instagram-DMs zeigt (und die kanaluebergreifende Timeline, Phase 20).

Als Loop (governance/autonomie-stufen.md, L1): fuer jede bestehende CRM-Firma per Gmail-Suche
(`google.mail_suchen(firmenname)`) passende Mails holen und als CRM-Nachricht erfassen. **Dedup** ueber
`extern_id = "mail:<gmail-id>"` (nachricht_erfassen ueberspringt Duplikate). Nur **Lesen/Spiegeln** --
Senden bleibt gated (Mensch-Tor). Token-frugal: kein LLM, nur die (kostenlose) Gmail-API.

Bewusst konservativ: es werden **keine** neuen Firmen aus Mails angelegt -- Mails haengen sich nur an
bereits bekannte Kooperations-Firmen. So bleibt das CRM sauber (kein Newsletter-Rauschen).
"""
from __future__ import annotations

from . import input_guard   # Phase 23: eingehende Fremd-Inhalte auf Prompt-Injection pruefen/markieren


class CrmMailTracker:
    def __init__(self, *, crm, google, eigene_adresse: str = "", secrets: list[str] | None = None):
        self.crm = crm                       # CrmStore
        self.google = google                 # GoogleWorkspace (mail_suchen) oder None
        self.eigene = (eigene_adresse or "").strip().lower()
        self.secrets = secrets or []

    def _verfuegbar(self) -> bool:
        return (self.crm is not None and self.google is not None
                and getattr(self.google, "verfuegbar", lambda: False)())

    def lauf(self, *, max_firmen: int = 8, pro_firma: int = 5) -> dict:
        """Ein Durchlauf: bis zu `max_firmen` Firmen, je bis zu `pro_firma` Gmail-Treffer als CRM-Mail
        erfassen (dedupliziert). Gibt {ok, erfasst, firmen}."""
        if not self._verfuegbar():
            return {"ok": False, "erfasst": 0, "hinweis": "CRM oder Google nicht verfuegbar."}
        firmen = [f.get("firma") for f in self.crm.firmen() if f.get("firma")][:max_firmen]
        erfasst = 0
        for firma in firmen:
            r = self.google.mail_suchen(firma, max_results=pro_firma)
            if not r.get("ok"):
                continue
            for m in r.get("mails", []):
                von = (m.get("von") or "").strip()
                richtung = "aus" if (self.eigene and self.eigene in von.lower()) else "ein"
                text = (m.get("betreff") or "(kein Betreff)").strip()
                if m.get("snippet"):
                    text += " — " + str(m["snippet"])[:200]
                # Phase 23: Fremd-Inhalt vor dem Speichern auf Prompt-Injection pruefen und ggf. markieren,
                # damit LUNA/Timeline die Nachricht als potenziell manipulativ erkennt (Lesen bleibt sicher).
                text, _guard = input_guard.markiere_wenn_verdaechtig(text, quelle="mail")
                mid = self.crm.nachricht_erfassen(
                    firma, text, quelle="mail", richtung=richtung, absender=von,
                    extern_id="mail:" + str(m.get("id", "")), kategorie="mail")
                if mid:
                    erfasst += 1
        return {"ok": True, "erfasst": erfasst, "firmen": len(firmen)}
