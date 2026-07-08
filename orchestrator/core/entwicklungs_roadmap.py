"""Entwicklungs-Roadmap (event-sourced, append-only).

Jeder vom CEO **freigegebene** Antrag landet automatisch hier -- als Arbeitspunkt, den Claude Code spaeter
abruft, abarbeitet und als umgesetzt markiert. Befuellt wird die Roadmap ausschliesslich ueber den Hook in
`Antraege.freigeben()` (der einzige Choke-Point fuer CEO-Freigaben: Telegram-Chat + Web-App). LUNA erhaelt
KEIN Tool, das hier direkt schreibt -> ein Eintrag entsteht nur nach ausdruecklicher CEO-Freigabe, nie autonom.

Bewusst abgegrenzt von: Antraegen (`antraege/`, Entscheidungs-Lebenszyklus), Research-Tickets (`research/`),
Changelog (Datei-Provenienz) und Gedaechtnis (`memory/`). Append-only JSONL; Zustand je Punkt aus Events
gefaltet; leck-geschuetzt. Zusaetzlich wird eine gerenderte, umlaut-freie `roadmap.md` geschrieben (fuer den
SSH-Abruf durch Claude Code).

Lebenszyklus:

    offen -> in_arbeit -> umgesetzt | verworfen
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..governance.leak_guard import redact

STATUSES = ("offen", "in_arbeit", "umgesetzt", "verworfen")
_BASE_FIELDS = ("titel", "beschreibung", "kategorie", "von", "quelle", "antrag_id", "freigegeben_ts", "notiz")
_GLYPH = {"offen": "\U0001F533", "in_arbeit": "\U0001F7E1", "umgesetzt": "✅", "verworfen": "✖"}

# .md-Konvention (AGENTS.md 6): keine Umlaute/scharfes S im lesbaren Text.
_UML = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe",
                      "Ü": "Ue", "ß": "ss"})


def _ascii(text: str) -> str:
    return (text or "").translate(_UML)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class EntwicklungsRoadmap:
    def __init__(self, path: str | Path, *, secrets: list[str] | None = None,
                 changelog: Callable[..., None] | None = None, md_pfad: str | Path | None = None):
        self.path = Path(path)
        self.secrets = secrets or []
        self.changelog = changelog
        self.md_pfad = Path(md_pfad) if md_pfad else self.path.with_name("roadmap.md")

    # -- schreiben --

    def aufnehmen(self, antrag: dict, *, render: bool = True) -> str | None:
        """Nimmt einen (gefalteten) Antrag als Roadmap-Punkt auf. Idempotent per `antrag_id`
        (schon vorhanden -> None). Wird nur vom Freigabe-Hook / Backfill aufgerufen."""
        if not isinstance(antrag, dict):
            return None
        antrag_id = str(antrag.get("antrag_id") or "").strip()
        if antrag_id and self._hat_antrag(antrag_id):
            return None                                     # schon auf der Roadmap
        von = str(antrag.get("von") or "")
        quelle = "self-dev" if "selbst-entwicklung" in von.lower() else "antrag"
        roadmap_id = "E-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self._append({
            "ts": _now(), "roadmap_id": roadmap_id, "event": "offen",
            "titel": str(antrag.get("titel") or "(ohne Titel)"),
            "beschreibung": str(antrag.get("beschreibung") or ""),
            "kategorie": str(antrag.get("kategorie") or ""),
            "von": von, "quelle": quelle, "antrag_id": antrag_id,
            "freigegeben_ts": self._freigabe_ts(antrag),
        })
        self._log("Head of Agents", f"Roadmap-Punkt aufgenommen ({roadmap_id}): {antrag.get('titel')}",
                  f"nach CEO-Freigabe von {antrag_id or '?'}", antrag_id or roadmap_id)
        if render:
            self.render_md()
        return roadmap_id

    def in_arbeit(self, roadmap_id: str) -> bool:
        ok = self._transition(roadmap_id, "in_arbeit")
        if ok:
            self.render_md()
        return ok

    def umsetzen(self, roadmap_id: str, *, notiz: str = "") -> bool:
        ok = self._transition(roadmap_id, "umgesetzt", **({"notiz": notiz} if notiz else {}))
        if ok:
            self._log("Claude Code", f"Roadmap-Punkt umgesetzt ({roadmap_id})", notiz or "erledigt", roadmap_id)
            self.render_md()
        return ok

    def verwerfen(self, roadmap_id: str, *, grund: str = "") -> bool:
        ok = self._transition(roadmap_id, "verworfen", **({"grund": grund} if grund else {}))
        if ok:
            self.render_md()
        return ok

    # -- lesen --

    def get(self, roadmap_id: str) -> dict | None:
        return self._fold().get(roadmap_id)

    def list(self, status: str | None = None) -> list[dict]:
        items = list(self._fold().values())
        if status:
            items = [i for i in items if i.get("status") == status]
        items.sort(key=lambda i: i["verlauf"][-1]["ts"] if i.get("verlauf") else "", reverse=True)
        return items

    # -- Backfill (vergangene Freigaben) --

    def backfill(self, antraege) -> int:
        """Nimmt alle Antraege auf, die je ein `freigegeben`-Event hatten (auch wenn ihr aktueller
        Status inzwischen in_umsetzung/erledigt ist). Idempotent. Gibt Anzahl neu aufgenommener zurueck."""
        n = 0
        for a in antraege.list():
            if any(s.get("event") == "freigegeben" for s in a.get("verlauf", [])):
                if self.aufnehmen(a, render=False) is not None:
                    n += 1
        self.render_md()
        return n

    # -- Markdown-Ausgabe (fuer den SSH-Abruf) --

    def als_markdown(self) -> str:
        items = self.list()
        z: list[str] = [
            "# Entwicklungs-Roadmap (aus freigegebenen Antraegen)",
            "",
            "> Automatisch befuellt: jeder vom CEO **freigegebene** Antrag landet hier -- nur nach Freigabe,",
            "> nie autonom. Claude Code ruft die Liste ab, arbeitet Punkte ab und markiert sie als umgesetzt.",
            "> Quelle der Wahrheit: `entwicklung/roadmap.jsonl` (event-sourced). Legende: "
            + " · ".join(f"{g} {s}" for s, g in _GLYPH.items()),
            "",
            "## Index",
            "",
            "| Task | Freigegeben | Status | Quelle / Antrag |",
            "|------|-------------|--------|-----------------|",
        ]
        for it in items:
            titel = _ascii(str(it.get("titel") or "(ohne Titel)")).replace("|", "/")[:90]
            frei = str(it.get("freigegeben_ts") or "")[:10]
            st = it.get("status", "offen")
            quelle = f"{it.get('quelle') or ''} / {it.get('antrag_id') or '-'}"
            z.append(f"| {titel} | {frei} | {_GLYPH.get(st, '')} {st} | {quelle} |")
        z += ["", "## Eintraege (neueste oben)", ""]
        for it in items:
            st = it.get("status", "offen")
            z.append(f"### {_GLYPH.get(st, '')} {_ascii(str(it.get('titel') or '(ohne Titel)'))}  "
                     f"({it.get('roadmap_id')})")
            besch = _ascii(str(it.get("beschreibung") or "")).strip()
            if besch:
                z.append(besch)
            z.append(f"- **Status:** {st} · **Von:** {_ascii(str(it.get('von') or ''))} "
                     f"· **Quelle:** {it.get('quelle')} · **Antrag:** {it.get('antrag_id') or '-'} "
                     f"· **Freigegeben:** {str(it.get('freigegeben_ts') or '')[:19]}")
            if it.get("notiz"):
                z.append(f"- **Notiz:** {_ascii(str(it.get('notiz')))}")
            z.append("")
        return "\n".join(z).rstrip() + "\n"

    def render_md(self, pfad: str | Path | None = None) -> None:
        ziel = Path(pfad) if pfad else self.md_pfad
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(self.als_markdown(), encoding="utf-8")

    # -- intern --

    def _hat_antrag(self, antrag_id: str) -> bool:
        return any(i.get("antrag_id") == antrag_id for i in self._fold().values())

    @staticmethod
    def _freigabe_ts(antrag: dict) -> str:
        for s in reversed(antrag.get("verlauf", []) or []):
            if s.get("event") == "freigegeben" and s.get("ts"):
                return s["ts"]
        return _now()

    def _append(self, event: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = redact(json.dumps(event, ensure_ascii=False), self.secrets)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _transition(self, roadmap_id: str, event: str, **extra) -> bool:
        if event not in STATUSES:
            raise ValueError(f"Unbekannter Status: {event}")
        if self.get(roadmap_id) is None:
            return False
        self._append({"ts": _now(), "roadmap_id": roadmap_id, "event": event, **extra})
        return True

    def _events(self) -> list[dict]:
        if not self.path.exists():
            return []
        out: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def _fold(self) -> dict[str, dict]:
        state: dict[str, dict] = {}
        for e in self._events():
            rid = e.get("roadmap_id")
            if not rid:
                continue
            cur = state.setdefault(rid, {"roadmap_id": rid, "verlauf": []})
            for k in _BASE_FIELDS:
                if e.get(k) is not None:
                    cur[k] = e[k]
            cur["status"] = e.get("event", cur.get("status"))
            schritt = {"ts": e.get("ts"), "event": e.get("event")}
            for k in ("grund", "notiz"):
                if k in e:
                    schritt[k] = e[k]
            cur["verlauf"].append(schritt)
        return state

    def _log(self, actor: str, was: str, warum: str, betroffen: str) -> None:
        if self.changelog:
            self.changelog(actor, was, warum, betroffen)


# -- CLI: Backfill / Rendern / Status setzen (im Container oder host-seitig via ssh) --

def _main() -> None:
    import argparse

    root = Path(__file__).resolve().parents[2]           # repo root
    rm = EntwicklungsRoadmap(root / "entwicklung" / "roadmap.jsonl")
    p = argparse.ArgumentParser(description="Entwicklungs-Roadmap: Backfill / Rendern / Status.")
    p.add_argument("--backfill", action="store_true", help="Alle je freigegebenen Antraege aufnehmen.")
    p.add_argument("--render", action="store_true", help="roadmap.md neu schreiben.")
    p.add_argument("--list", action="store_true", help="Punkte auflisten.")
    p.add_argument("--umsetzen", metavar="ID", help="Punkt als umgesetzt markieren.")
    p.add_argument("--verwerfen", metavar="ID", help="Punkt verwerfen.")
    p.add_argument("--notiz", default="", help="Notiz (z. B. Commit) fuer --umsetzen.")
    p.add_argument("--grund", default="", help="Grund fuer --verwerfen.")
    a = p.parse_args()

    if a.backfill:
        from .antraege import Antraege
        n = rm.backfill(Antraege(root / "antraege" / "log.jsonl"))
        print(f"Backfill: {n} Punkt(e) neu aufgenommen. -> {rm.md_pfad}")
    if a.umsetzen:
        print("umgesetzt:", rm.umsetzen(a.umsetzen, notiz=a.notiz))
    if a.verwerfen:
        print("verworfen:", rm.verwerfen(a.verwerfen, grund=a.grund))
    if a.render:
        rm.render_md()
        print(f"gerendert -> {rm.md_pfad}")
    if a.list or not any((a.backfill, a.umsetzen, a.verwerfen, a.render)):
        for it in rm.list():
            print(f"{_GLYPH.get(it.get('status',''), '')} {it.get('roadmap_id')} [{it.get('status')}] "
                  f"{_ascii(str(it.get('titel') or ''))[:70]}  (Antrag {it.get('antrag_id')})")


if __name__ == "__main__":
    _main()
