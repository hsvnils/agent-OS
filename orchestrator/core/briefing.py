"""Morgen-/Abend-Briefing + manuelle Agenda.

Der CEO bekommt 08:00 (DE) ein **Morgen-Briefing** (was ueber Nacht erledigt/passiert ist, was heute ansteht)
und 20:00 (DE) ein **Abend-Briefing** (was heute erledigt wurde, was nachts ansteht). Manuell hinzugefuegte
Punkte (`Agenda`) fliessen mit ein.

**Token-frugal:** rein regelbasiert aus den vorhandenen Stores (Antraege, Research-Tickets, Watch-Funde,
Agenda) zusammengestellt -- kein LLM. Texte fuer Telegram mit Umlauten.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from ..governance.leak_guard import redact


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Agenda:
    """Manuelle Aufgaben/Notizen, die in die Briefings einfliessen (event-sourced JSONL)."""

    def __init__(self, path: str | Path, *, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = secrets or []

    def notiz(self, text: str, *, art: str = "aufgabe") -> str:
        nid = "AG-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({"ts": _now(), "id": nid, "typ": "notiz", "art": art, "text": text})
        return nid

    def erledigen(self, nid: str) -> bool:
        if not any(e.get("id") == nid and e.get("typ") == "notiz" for e in self._events()):
            return False
        self._append({"ts": _now(), "id": nid, "typ": "erledigt"})
        return True

    def offene(self) -> list[dict]:
        erled = {e["id"] for e in self._events() if e.get("typ") == "erledigt"}
        return [e for e in self._events() if e.get("typ") == "notiz" and e["id"] not in erled]

    def seit(self, start: datetime) -> list[dict]:
        return [e for e in self._events() if e.get("typ") == "notiz" and _ts(e) and _ts(e) >= start]

    def briefing_gesendet(self, art: str, datum: str) -> bool:
        return any(e.get("typ") == "briefing" and e.get("art") == art and e.get("datum") == datum
                   for e in self._events())

    def markiere_briefing(self, art: str, datum: str) -> None:
        self._append({"ts": _now(), "typ": "briefing", "art": art, "datum": datum})

    def _append(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps(event, ensure_ascii=False), self.secrets)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _events(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out


def _ts(e: dict):
    try:
        return datetime.fromisoformat(e.get("ts", ""))
    except ValueError:
        return None


class Briefing:
    def __init__(self, *, antraege=None, research=None, watch=None, agenda=None,
                 secrets: list[str] | None = None):
        self.antraege = antraege
        self.research = research
        self.watch = watch
        self.agenda = agenda
        self.secrets = secrets or []

    def _fenster_start(self, art: str, jetzt: datetime) -> datetime:
        if art == "morgen":  # seit gestern 20:00 (ueber Nacht)
            return (jetzt - timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)
        return jetzt.replace(hour=8, minute=0, second=0, microsecond=0)  # abend: seit heute 08:00

    def erstellen(self, art: str = "morgen", *, jetzt: datetime | None = None) -> str:
        jetzt = jetzt or datetime.now()
        start = self._fenster_start(art, jetzt)
        kopf = ("Guten Morgen! Hier dein Morgen-Briefing" if art == "morgen"
                else "Guten Abend! Hier dein Abend-Briefing")
        zeile = f"{kopf} ({jetzt.strftime('%d.%m.%Y %H:%M')}):"

        erledigt = self._erledigt_im_fenster(start)
        offen = self._offene_punkte()
        manuell = self._manuell_neu(start)

        getan_titel = "Über Nacht erledigt/passiert" if art == "morgen" else "Heute erledigt/passiert"
        ansteht_titel = "Heute steht an" if art == "morgen" else "Für die Nacht steht an"

        teile = [zeile, "", f"{getan_titel}:"]
        teile += [f"  - {x}" for x in erledigt] or ["  - (nichts protokolliert)"]
        teile += ["", f"{ansteht_titel}:"]
        teile += [f"  - {x}" for x in offen] or ["  - (keine offenen Punkte)"]
        if manuell:
            teile += ["", "Manuell hinzugefügt:"] + [f"  - {x}" for x in manuell]
        return redact("\n".join(teile), self.secrets)

    # -- Datenquellen (alle kostenlos) --

    def _erledigt_im_fenster(self, start: datetime) -> list[str]:
        out: list[str] = []
        if self.antraege is not None:
            for a in self.antraege.list():
                letzte = a.get("verlauf", [])
                if letzte and _tsstr(letzte[-1].get("ts")) and _tsstr(letzte[-1]["ts"]) >= start \
                        and a.get("status") in ("freigegeben", "erledigt", "abgelehnt"):
                    out.append(f"Antrag '{a.get('titel', '')[:50]}' [{a.get('antrag_id')}] -> {a.get('status')}")
        if self.research is not None:
            for t in self.research.list("erledigt"):
                if t.get("verlauf") and _tsstr(t['verlauf'][-1].get('ts')) \
                        and _tsstr(t['verlauf'][-1]['ts']) >= start:
                    out.append(f"Researcher: '{(t.get('frage') or '')[:50]}' erledigt")
        if self.watch is not None:
            funde = [f for f in self.watch.store.findings(200) if _tsstr(f.get("ts")) and _tsstr(f["ts"]) >= start]
            if funde:
                out.append(f"Watcher/Researcher: {len(funde)} neue Funde gesammelt")
        return out[:15]

    def _offene_punkte(self) -> list[str]:
        out: list[str] = []
        if self.antraege is not None:
            for a in self.antraege.list():
                if a.get("status") in ("eingereicht", "freigegeben"):
                    out.append(f"Antrag '{a.get('titel', '')[:50]}' [{a.get('antrag_id')}] "
                               f"({a.get('status')}) -- wartet auf dich")
        if self.agenda is not None:
            for n in self.agenda.offene():
                out.append(f"Aufgabe: {n.get('text', '')[:60]} [{n.get('id')}]")
        return out[:15]

    def _manuell_neu(self, start: datetime) -> list[str]:
        if self.agenda is None:
            return []
        return [f"{n.get('text', '')[:70]}" for n in self.agenda.seit(start)][:10]


def _tsstr(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except (ValueError, TypeError):
        return None
