"""Phase 19 -- CRM-Akte trackt Mails.

Ordnet **Gmail-Mails** bestehenden CRM-Firmen zu (Kanal `mail`), sodass die Unternehmensakte in der
Collab-CRM-App E-Mails **neben** den Instagram-DMs zeigt (und die kanaluebergreifende Timeline, Phase 20).

Als Loop (governance/autonomie-stufen.md, L1): fuer jede bestehende CRM-Firma per Gmail-Suche
(`google.mail_suchen(firmenname)`) passende Mails holen und als CRM-Nachricht erfassen. **Dedup** ueber
`extern_id = "mail:<gmail-id>"` (nachricht_erfassen ueberspringt Duplikate). Nur **Lesen/Spiegeln** --
Senden bleibt gated (Mensch-Tor). Token-frugal: kein LLM, nur die (kostenlose) Gmail-API.

Bewusst konservativ: es werden **keine** neuen Firmen aus Mails angelegt -- Mails haengen sich nur an
bereits bekannte Kooperations-Firmen. So bleibt das CRM sauber (kein Newsletter-Rauschen).

Eigene Identitaet (BF-85): eine CRM-"Firma", deren Name in einer eigenen Adresse des CEO steckt (z. B. das Meta-Test-
konto "hsvnils"), ist kein Gegenueber -- die Gmail-Suche nach ihr traefe jede Mail und jede Weiterleitung des CEO.
Solche Firmen werden uebersprungen. Mails des CEO zaehlen als "aus", seine Weiterleitungen (WG:/Fwd:) als "ein".
"""
from __future__ import annotations

import re

from . import input_guard   # Phase 23: eingehende Fremd-Inhalte auf Prompt-Injection pruefen/markieren


_WEITER = re.compile(r"(?i)^\s*(?:wg|fwd?|weitergeleitet)\s*:")


_ANBIETER = {"gmail", "googlemail", "icloud", "me", "mac", "gmx", "web", "outlook", "hotmail", "yahoo", "tonline", "posteo"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


class CrmMailTracker:
    def __init__(self, *, crm, google, eigene_adresse: str = "", secrets: list[str] | None = None,
                 notify=None, ceo_adressen: list[str] | None = None):
        self.crm = crm                       # CrmStore
        self.google = google                 # GoogleWorkspace (mail_suchen) oder None
        self.eigene = (eigene_adresse or "").strip().lower()
        self.ceo = [a.strip().lower() for a in (ceo_adressen or []) if "@" in a]
        self.secrets = secrets or []
        self.notify = notify                 # Phase 23<->21: CISO-Meldung bei Prompt-Injection (oder None)

    def _verfuegbar(self) -> bool:
        return (self.crm is not None and self.google is not None
                and getattr(self.google, "verfuegbar", lambda: False)())

    def ist_eigene_identitaet(self, firma: str) -> bool:
        """True, wenn der Firmenname Teil einer eigenen Adresse ist (Postfachname oder Domain)."""
        n = _norm(firma)
        if len(n) < 4:
            return False
        teile = set()
        for a in self.ceo + ([self.eigene] if "@" in self.eigene else []):
            lokal, _, dom = a.partition("@")
            teile |= {_norm(lokal), *(_norm(x) for x in dom.split(".")[:-1])}
        return n in (teile - _ANBIETER)

    def _richtung(self, von: str, betreff: str) -> str:
        v = von.lower()
        if self.eigene and self.eigene in v:
            return "aus"
        if any(a in v for a in self.ceo):
            return "ein" if _WEITER.match(betreff or "") else "aus"
        return "ein"

    def lauf(self, *, max_firmen: int = 8, pro_firma: int = 5) -> dict:
        """Ein Durchlauf: bis zu `max_firmen` Firmen, je bis zu `pro_firma` Gmail-Treffer als CRM-Mail
        erfassen (dedupliziert). Gibt {ok, erfasst, firmen}."""
        if not self._verfuegbar():
            return {"ok": False, "erfasst": 0, "hinweis": "CRM oder Google nicht verfuegbar."}
        firmen = [f.get("firma") for f in self.crm.firmen()
                  if f.get("firma") and not self.ist_eigene_identitaet(f.get("firma"))][:max_firmen]
        erfasst = 0
        for firma in firmen:
            r = self.google.mail_suchen(firma, max_results=pro_firma)
            if not r.get("ok"):
                continue
            for m in r.get("mails", []):
                von = (m.get("von") or "").strip()
                richtung = self._richtung(von, m.get("betreff") or "")
                text = (m.get("betreff") or "(kein Betreff)").strip()
                if m.get("snippet"):
                    text += " — " + str(m["snippet"])[:200]
                # Phase 23: Fremd-Inhalt vor dem Speichern auf Prompt-Injection pruefen und ggf. markieren,
                # damit LUNA/Timeline die Nachricht als potenziell manipulativ erkennt (Lesen bleibt sicher).
                text, guard = input_guard.markiere_wenn_verdaechtig(text, quelle="mail")
                mid = self.crm.nachricht_erfassen(
                    firma, text, quelle="mail", richtung=richtung, absender=von,
                    extern_id="mail:" + str(m.get("id", "")), kategorie="mail")
                if mid:
                    erfasst += 1
                    if guard.injection and self.notify:
                        try:
                            self.notify(input_guard.melde_text("mail", von, guard),
                                        abteilung="CISO/Security", kategorie="security", quelle="input-guard")
                        except Exception:
                            pass
        return {"ok": True, "erfasst": erfasst, "firmen": len(firmen)}
