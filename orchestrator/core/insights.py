"""Proaktive Tages-Insights (Lagebild) -- Jarvis Intelligent Feature.

Buendelt regelbasiert (token-frugal, kein LLM) das aktuelle Lagebild fuer den CEO:
- Entscheidungen, die auf dich warten (Antraege 'eingereicht'/'freigegeben'),
- heutige Termine (Kalender, live ueber Google/Phase 11),
- wichtige/ungelesene Mails (live ueber Google),
- offene Research-Tickets,
- manuelle Agenda-Punkte.

`daten()` liefert eine strukturierte Form (fuer LUNA-OS), `lagebild()` einen kurzen deutschen Text
(fuer Voice/Telegram). Google ist optional -- ohne Zugriff bleibt das Lagebild auf interne Stores beschraenkt.
"""
from __future__ import annotations

from datetime import date, datetime

from ..governance.leak_guard import redact


class Insights:
    def __init__(self, *, antraege=None, research=None, agenda=None, google=None,
                 secrets: list[str] | None = None):
        self.antraege = antraege
        self.research = research
        self.agenda = agenda
        self.google = google
        self.secrets = secrets or []

    def daten(self, *, jetzt: datetime | None = None) -> dict:
        jetzt = jetzt or datetime.now()
        return {
            "entscheidungen": self._entscheidungen(),
            "termine_heute": self._termine_heute(jetzt),
            "mails": self._mails(),
            "tickets": self._offene_tickets(),
            "agenda": self._agenda(),
        }

    def lagebild(self, *, jetzt: datetime | None = None) -> str:
        jetzt = jetzt or datetime.now()
        d = self.daten(jetzt=jetzt)
        teile = [f"Lagebild ({jetzt.strftime('%d.%m.%Y %H:%M')}):", ""]

        ent = d["entscheidungen"]
        teile.append(f"Auf dich warten {len(ent)} Entscheidung(en):" if ent else "Keine offenen Entscheidungen. 👍")
        teile += [f"  - {x['titel']} [{x['id']}] ({x['status']})" for x in ent[:6]]

        if d["termine_heute"]:
            teile += ["", f"Heute im Kalender ({len(d['termine_heute'])}):"]
            teile += [f"  - {t['zeit']} {t['titel']}" for t in d["termine_heute"][:6]]
        m = d["mails"]
        if m.get("verfuegbar"):
            teile += ["", f"Ungelesene Mails: {m['anzahl']}" + (":" if m.get("liste") else ".")]
            teile += [f"  - {x['von']}: {x['betreff']}" for x in m.get("liste", [])[:4]]
        if d["tickets"]:
            teile += ["", f"Offene Research-Tickets: {len(d['tickets'])}"]
        if d["agenda"]:
            teile += ["", "Deine Agenda:"]
            teile += [f"  - {x}" for x in d["agenda"][:6]]
        return redact("\n".join(teile), self.secrets)

    # -- Datenquellen --

    def _entscheidungen(self) -> list[dict]:
        out: list[dict] = []
        if self.antraege is None:
            return out
        for a in self.antraege.list():
            if a.get("status") in ("eingereicht", "freigegeben"):
                out.append({"id": a.get("antrag_id"), "status": a.get("status"),
                            "titel": (a.get("titel") or "(ohne Titel)").lstrip("*").strip()[:70]})
        # 'eingereicht' (Entscheidung noetig) zuerst
        out.sort(key=lambda x: 0 if x["status"] == "eingereicht" else 1)
        return out

    def _termine_heute(self, jetzt: datetime) -> list[dict]:
        if self.google is None:
            return []
        try:
            res = self.google.kalender_agenda(tage=1)
        except Exception:
            return []
        if not res or not res.get("ok"):
            return []
        heute = jetzt.date().isoformat()
        out = []
        for t in res.get("termine", []):
            start = str(t.get("start") or "")
            if start.startswith(heute):
                zeit = start[11:16] if "T" in start else "ganztags"
                out.append({"zeit": zeit, "titel": (t.get("titel") or "")[:70]})
        return out

    def _mails(self) -> dict:
        if self.google is None:
            return {"verfuegbar": False, "anzahl": 0, "liste": []}
        try:
            res = self.google.neue_mails(max_results=10)
        except Exception:
            return {"verfuegbar": False, "anzahl": 0, "liste": []}
        if not res or not res.get("ok"):
            return {"verfuegbar": False, "anzahl": 0, "liste": []}
        mails = res.get("mails", [])
        return {"verfuegbar": True, "anzahl": len(mails),
                "liste": [{"von": (m.get("von") or "")[:40], "betreff": (m.get("betreff") or "")[:60]}
                          for m in mails]}

    def _offene_tickets(self) -> list[dict]:
        if self.research is None:
            return []
        out = []
        for status in ("offen", "in_arbeit"):
            for t in self.research.list(status):
                out.append({"id": t.get("ticket_id"), "frage": (t.get("frage") or "")[:70]})
        return out

    def _agenda(self) -> list[str]:
        if self.agenda is None:
            return []
        return [f"{n.get('text', '')[:70]} [{n.get('id')}]" for n in self.agenda.offene()]
