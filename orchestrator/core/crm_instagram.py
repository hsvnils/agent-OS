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
        return {"ok": True, "gesehen": gesehen, "neu": neu}
