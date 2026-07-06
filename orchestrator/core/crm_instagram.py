"""Collab-CRM -- Instagram-DM-Poll (Graph Conversations API) fuers eigene Konto.

Ergaenzt den Webhook-Pfad: pollt die DM-Threads des eigenen Kontos (`InstagramConversations`) und speist neue
EINGEHENDE Nachrichten in denselben CRM-Pfad wie Webhook/Mail (`CrmStore.verarbeite_eingang` -> Klassifikation,
Input-Guard/Phase 23, To-do, Notifier). Eigene (ausgehende) Nachrichten werden uebersprungen; Dedup laeuft
ueber die Message-ID (`extern_id`) im CRM. Braucht KEINE Advanced-Access-Review (eigenes Konto, nur Lesen).
"""
from __future__ import annotations


class CrmInstagramTracker:
    def __init__(self, *, crm, reader, secrets: list[str] | None = None, notify=None):
        self.crm = crm
        self.reader = reader
        self.secrets = secrets or []
        self.notify = notify

    def verfuegbar(self) -> bool:
        return self.reader is not None and getattr(self.reader, "verfuegbar", False)

    def lauf(self, *, max_konv: int = 20) -> dict:
        """Pollt Threads + neue eingehende DMs -> CRM. Gibt {ok, gesehen, neu}."""
        if not self.verfuegbar():
            return {"ok": False, "hinweis": "Instagram-Token/IG-User-ID fehlt (INSTAGRAM_ACCESS_TOKEN/"
                                            "INSTAGRAM_PAGE_TOKEN + INSTAGRAM_IG_USER_ID)."}
        gesehen = 0
        neu = 0
        for conv in self.reader.konversationen()[:max_konv]:
            for m in self.reader.nachrichten(conv):
                if not m.get("text") or m.get("from_id") == self.reader.own_id:
                    continue                                   # leer oder eigene ausgehende Nachricht
                gesehen += 1
                firma = m.get("from_username") or m.get("from_id") or "unbekannt"
                res = self.crm.verarbeite_eingang(firma, m["text"], quelle="instagram",
                                                  absender=m.get("from_id", ""), extern_id=m.get("id", ""))
                if res.get("mid"):                             # "" bei Duplikat (Dedup ueber extern_id)
                    neu += 1
        ergebnis = {"ok": True, "gesehen": gesehen, "neu": neu}
        fehler = getattr(self.reader, "letzter_fehler", "")
        if not gesehen and fehler:                             # 0 Nachrichten + API-Fehler -> sichtbar machen
            ergebnis["api_fehler"] = fehler
        return ergebnis

    def backfill(self, *, wochen: int = 8, max_konv: int = 50, max_seiten: int = 40) -> dict:
        """EINMALIGER Rueck-Scan: blaettert je Thread bis `wochen` Wochen zurueck und speist alle eingehenden
        Text-DMs in den CRM-Pfad (dedupliziert ueber `extern_id` -> keine Doppel mit dem laufenden Poll).
        Gibt {ok, wochen, threads, gesehen, neu}. Braucht `reader.nachrichten_seit`.
        """
        if not self.verfuegbar():
            return {"ok": False, "hinweis": "Instagram-Token/IG-User-ID fehlt (INSTAGRAM_USER_TOKEN + "
                                            "INSTAGRAM_APP_SECRET oder INSTAGRAM_ACCESS_TOKEN + INSTAGRAM_IG_USER_ID)."}
        if not hasattr(self.reader, "nachrichten_seit"):
            return {"ok": False, "hinweis": "Reader kann nicht zurueckblaettern (nachrichten_seit fehlt)."}
        import time
        seit_ts = time.time() - max(1, wochen) * 7 * 86400
        threads = gesehen = neu = 0
        for conv in self.reader.konversationen(limit=max_konv):
            threads += 1
            for m in self.reader.nachrichten_seit(conv, seit_ts=seit_ts, max_seiten=max_seiten):
                if not m.get("text") or m.get("from_id") == self.reader.own_id:
                    continue                                   # leer oder eigene ausgehende Nachricht
                gesehen += 1
                firma = m.get("from_username") or m.get("from_id") or "unbekannt"
                res = self.crm.verarbeite_eingang(firma, m["text"], quelle="instagram",
                                                  absender=m.get("from_id", ""), extern_id=m.get("id", ""))
                if res.get("mid"):                             # "" bei Duplikat (Dedup ueber extern_id)
                    neu += 1
        ergebnis = {"ok": True, "wochen": wochen, "threads": threads, "gesehen": gesehen, "neu": neu}
        fehler = getattr(self.reader, "letzter_fehler", "")
        if not gesehen and fehler:
            ergebnis["api_fehler"] = fehler
        return ergebnis
