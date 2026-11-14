"""XMind-Dateien erzeugen: Organigramm aus den Charten und Mindmaps/Zeitstrahlen aus JSON.

Aufruf:
    python3 scripts/xmind_bauen.py organigramm                     -> governance/organigramm.xmind
    python3 scripts/xmind_bauen.py json <eingabe.json> <ziel.xmind>

Das Organigramm wird aus `orchestrator/core/subagents.py` (Agentenliste), den Charten (Titel, Rolle) und den
Skill-Ordnern gebaut. So bleibt es nach jeder Charta- oder Skill-Aenderung mit einem Befehl aktuell.

JSON-Format fuer `json`: {"blaetter": [{"titel": "...", "struktur": "timeline|org|logik|karte",
"wurzel": {"titel": "...", "notiz": "...", "kinder": [...], "eingeklappt": false}}]}
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
STRUKTUR = {
    "org": "org.xmind.ui.org-chart.down",
    "timeline": "org.xmind.ui.timeline.horizontal",
    "logik": "org.xmind.ui.logic.right",
    "karte": "org.xmind.ui.map.unbalanced",
}
SKILL_ORDNER = {"res": "res"}          # Abweichungen Agenten-Schluessel -> skills/<ordner>


def thema(titel: str, kinder: list | None = None, notiz: str = "", eingeklappt: bool = False,
          struktur: str = "") -> dict:
    t: dict = {"id": uuid4().hex, "class": "topic", "title": titel}
    if struktur:
        t["structureClass"] = STRUKTUR.get(struktur, struktur)
    if notiz:
        t["notes"] = {"plain": {"content": notiz}}
    if kinder:
        t["children"] = {"attached": kinder}
        if eingeklappt:
            t["branch"] = "folded"
    return t


def aus_dict(d: dict) -> dict:
    return thema(d["titel"], [aus_dict(k) for k in d.get("kinder", [])], d.get("notiz", ""), d.get("eingeklappt", False))


def schreiben(ziel: Path, blaetter: list[tuple[str, dict]]) -> Path:
    inhalt = [{"id": uuid4().hex, "class": "sheet", "title": titel, "rootTopic": wurzel} for titel, wurzel in blaetter]
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("content.json", json.dumps(inhalt, ensure_ascii=False))
        z.writestr("metadata.json", json.dumps({"creator": {"name": "Hanserautisch / scripts/xmind_bauen.py", "version": "1.0"}}))
        z.writestr("manifest.json", json.dumps({"file-entries": {"content.json": {}, "metadata.json": {}}}))
    return ziel


# -- Organigramm ------------------------------------------------------------------------------------------------

def _charten() -> dict[str, str]:
    text = (ROOT / "orchestrator/core/subagents.py").read_text(encoding="utf-8")
    block = text.split("ALL_AGENT_CHARTERS", 1)[1].split("}", 1)[0]
    return dict(re.findall(r'"(\w+)":\s*"(agents/[^"]+)"', block))


def _charta_info(pfad: Path) -> tuple[str, str, str]:
    text = pfad.read_text(encoding="utf-8")
    kopf = re.search(r"^# Agent:\s*(.+)$", text, re.M)
    roh = kopf.group(1).strip() if kopf else pfad.stem
    kuerzel = (re.search(r"\(([^)]*)\)\s*$", roh) or [None, ""])[1]
    titel = re.sub(r"\s*\([^)]*\)\s*$", "", roh).strip()
    if kuerzel.startswith("C") and kuerzel not in titel:
        titel = f"{kuerzel} — {titel}"
    status = (re.search(r"^Status:\s*(\S+)", text, re.M) or [None, ""])[1]
    rolle = text.split("## Rolle", 1)[1].split("##", 1)[0].strip().replace("\n", " ") if "## Rolle" in text else ""
    return titel, status, rolle


def _skills(key: str) -> list[str]:
    ordner = ROOT / "skills" / SKILL_ORDNER.get(key, key)
    return sorted(p.parent.name for p in ordner.glob("*/SKILL.md")) if ordner.is_dir() else []


def organigramm() -> dict:
    charten = _charten()
    unter: dict[str, list] = {"cco": [thema("Video-Cutter (Unter-Agent, laeuft auf dem MACO470)")]}
    abteilungen = []
    for key, rel in sorted(charten.items(), key=lambda kv: Path(kv[1]).name):
        if key == "risk":
            continue
        pfad = ROOT / rel
        nummer = Path(rel).name.split("_", 1)[0]
        titel, status, rolle = _charta_info(pfad)
        kinder = []
        skills = _skills(key)
        if skills:
            kinder.append(thema(f"Skills ({len(skills)})", [thema(s) for s in skills], eingeklappt=True))
        if key == "cio" and "risk" in charten:
            r_titel, r_status, r_rolle = _charta_info(ROOT / charten["risk"])
            kinder.append(thema(f"16a · {r_titel} ({r_status})", notiz=r_rolle))
        kinder += unter.get(key, [])
        zusatz = "" if status == "aktiv" else f" ({status})"
        abteilungen.append(thema(f"{nummer} · {titel}{zusatz}", kinder, notiz=rolle))
    netz = thema("Netz-Agent (eigener Container, einziger Weg ins freie Internet)",
                 notiz="Freie Websuchen nur ueber den Netz-Agenten; keine internen Daten, gepruefte Ergebnis-Formulare.")
    hoa = thema("00 · Head of Agents (LUNA)", abteilungen + [netz],
                notiz="Einziger Gespraechspartner des CEO: zerlegt, delegiert, buendelt, eskaliert.")
    team = thema("Team (Menschen)", [thema("Nils -- CEO, Person 1"), thema("Celine -- Person 2")])
    return thema("CEO (Nils)", [hoa, team], struktur="org")


def main(argv: list[str]) -> int:
    if argv[:1] == ["organigramm"]:
        ziel = schreiben(ROOT / "governance/organigramm.xmind", [("LUNA Organigramm", organigramm())])
    elif argv[:1] == ["json"] and len(argv) == 3:
        daten = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        blaetter = []
        for b in daten["blaetter"]:
            wurzel = aus_dict(b["wurzel"])
            wurzel["structureClass"] = STRUKTUR.get(b.get("struktur", "karte"), b.get("struktur"))
            blaetter.append((b["titel"], wurzel))
        ziel = schreiben(Path(argv[2]), blaetter)
    else:
        print(__doc__)
        return 2
    print(f"geschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
