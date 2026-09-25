#!/usr/bin/env python3
"""Doku-Check: prueft, dass Doku und Code nicht auseinanderlaufen (AGENTS.md 6, governance/roadmap-workflow.md).

Prueft:
  1. Roadmaps  -- jede `<THEMA>_ROADMAP.md` im Root steht im Roadmap-Verzeichnis von `ROADMAP.md`;
                  neue (nicht Bestand) haben den Pflicht-Header mit gueltigem Status.
  2. Hosts     -- jeder externe Host im Code steht in `docs/datenfluesse.md` (oder ist dort ignoriert), und
                  jeder dort gefuehrte Host kommt im Code noch vor.
  3. Tabellen  -- dasselbe fuer Supabase-Tabellen.
  4. Speicher  -- dasselbe fuer lokale JSON/JSONL-Stores unter ROOT.

Die Soll-Listen stehen maschinenlesbar in `docs/datenfluesse.md` in Codebloecken ```doku-check:<name>```.

Aufruf:  python3 scripts/doku_check.py          -> Bericht, Exit 1 bei Abweichung
         python3 scripts/doku_check.py --liste  -> nur gefundene Ist-Mengen ausgeben (zum Nachtragen)
Rein lesend, ohne Netz, ohne Abhaengigkeiten ausser der Standardbibliothek.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOKU = ROOT / "docs" / "datenfluesse.md"

# Code, der gescannt wird (Tests, Vendor-Code und Umgebungen nicht).
SCAN_DIRS = ["orchestrator", "cutter", "deploy", "runner", "reel_freigabe", "mac", "scripts"]
SCAN_ENDUNGEN = {".py", ".sh", ".js", ".swift", ".yml", ".yaml", ".plist"}
SKIP_TEILE = {"tests", "vendor", ".venv", "node_modules", "__pycache__", ".worktrees"}

# Roadmaps, die vor dem Workflow entstanden sind (governance/roadmap-workflow.md, Abschnitt „Bestand").
ROADMAP_BESTAND = {"INVESTMENT_ROADMAP.md", "HCC_INTEGRATION_ROADMAP.md"}
ROADMAP_HEADER = ["Status", "Stand", "Arbeitsbranch", "Basiscommit", "Naechster Schritt", "Hinweis"]
ROADMAP_STATUS = {"geplant", "in Umsetzung", "abgeschlossen", "verworfen"}

RE_HOST = re.compile(r"https?://([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})")
RE_TABELLE = re.compile(
    r"""(?:\.(?:select|insert|upsert|update|delete)\(\s*|ContentStore\([^,()]+,\s*|TABELLE\s*=\s*)["']([a-z][a-z0-9_]+)["']""")
RE_SPEICHER = re.compile(r"""ROOT\s*/\s*["']([a-z_]+)["']\s*/\s*["']([^"']+\.jsonl?)["']""")
RE_BLOCK = re.compile(r"```doku-check:([a-z-]+)\n(.*?)```", re.S)


def _code_dateien():
    for d in SCAN_DIRS:
        basis = ROOT / d
        if not basis.is_dir():
            continue
        for p in basis.rglob("*"):
            if p.is_file() and p.suffix in SCAN_ENDUNGEN and not (SKIP_TEILE & set(p.relative_to(ROOT).parts)):
                yield p


def ist_mengen() -> dict[str, dict[str, set[str]]]:
    """Gefundene Hosts/Tabellen/Speicher -> {name: {datei, ...}} (Fundstellen fuer den Bericht)."""
    funde: dict[str, dict[str, set[str]]] = {"hosts": {}, "tabellen": {}, "speicher": {}}
    for p in _code_dateien():
        rel = str(p.relative_to(ROOT))
        text = p.read_text(encoding="utf-8", errors="replace")
        for h in RE_HOST.findall(text):
            funde["hosts"].setdefault(h.lower(), set()).add(rel)
        if p.suffix == ".py":
            for t in RE_TABELLE.findall(text):
                funde["tabellen"].setdefault(t, set()).add(rel)
            for a, b in RE_SPEICHER.findall(text):
                funde["speicher"].setdefault(f"{a}/{b}", set()).add(rel)
    # Investment-Loop fuehrt seine Supabase-Tabellen als Tupel TABELLEN (nicht investment/store.py -- dort
    # sind TABELLEN nur Event-Typen im JSONL-Log).
    loop = ROOT / "orchestrator" / "investment" / "loop_store.py"
    if loop.exists():
        for node in ast.walk(ast.parse(loop.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "TABELLEN" for t in node.targets):
                for elt in getattr(node.value, "elts", []):
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        funde["tabellen"].setdefault(elt.value, set()).add(str(loop.relative_to(ROOT)))
    return funde


def soll_mengen(text: str) -> dict[str, set[str]]:
    bloecke: dict[str, set[str]] = {}
    for name, inhalt in RE_BLOCK.findall(text):
        eintraege = set()
        for zeile in inhalt.splitlines():
            wert = zeile.split("#", 1)[0].strip()
            if wert:
                eintraege.add(wert.lower() if name.startswith("hosts") else wert)
        bloecke[name] = eintraege
    return bloecke


def _ignoriert(host: str, muster: set[str]) -> bool:
    for m in muster:
        if m.startswith("*.") and (host.endswith(m[1:]) or host == m[2:]):
            return True
        if m.endswith(".*") and host.startswith(m[:-1]):
            return True
        if host == m:
            return True
    return False


def pruefe_roadmaps() -> list[str]:
    fehler = []
    master = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    for p in sorted(ROOT.glob("*_ROADMAP.md")):
        if p.name not in master:
            fehler.append(f"Roadmap {p.name} fehlt im Roadmap-Verzeichnis von ROADMAP.md")
        if p.name in ROADMAP_BESTAND:
            continue
        kopf = p.read_text(encoding="utf-8").splitlines()[:25]
        felder = {}
        for z in kopf:
            m = re.match(r"-\s*([A-Za-z ]+):\s*(.*)", z)
            if m:
                felder[m.group(1).strip()] = m.group(2).strip()
        for f in ROADMAP_HEADER:
            if not felder.get(f):
                fehler.append(f"Roadmap {p.name}: Pflicht-Header-Feld „{f}“ fehlt oder ist leer")
        if felder.get("Status") and felder["Status"] not in ROADMAP_STATUS:
            fehler.append(f"Roadmap {p.name}: Status „{felder['Status']}“ ungueltig ({' | '.join(sorted(ROADMAP_STATUS))})")
    return fehler


def pruefe_datenfluesse() -> list[str]:
    if not DOKU.exists():
        return [f"{DOKU.relative_to(ROOT)} fehlt"]
    soll = soll_mengen(DOKU.read_text(encoding="utf-8"))
    ist = ist_mengen()
    fehler = []
    for name in ("hosts", "tabellen", "speicher"):
        if name not in soll:
            fehler.append(f"docs/datenfluesse.md: Block ```doku-check:{name}``` fehlt")
            continue
        ignoriert = soll.get(f"{name}-ignoriert", set())
        for wert, dateien in sorted(ist[name].items()):
            if wert in soll[name]:
                continue
            if name == "hosts" and _ignoriert(wert, ignoriert):
                continue
            fehler.append(f"{name}: „{wert}“ im Code ({', '.join(sorted(dateien)[:3])}), aber nicht in "
                          f"docs/datenfluesse.md -> dort eintragen (oder unter {name}-ignoriert)")
        for wert in sorted(soll[name] - set(ist[name])):
            fehler.append(f"{name}: „{wert}“ steht in docs/datenfluesse.md, kommt im Code nicht mehr vor "
                          f"-> Doku bereinigen")
    return fehler


def hinweise_speicher() -> list[str]:
    """Nicht-blockierende Hinweise: Live-Speicher ohne Deploy-Schutz bzw. ohne Backup (siehe bekannte-fehler.md)."""
    sync = (ROOT / "deploy" / "sync-to-nas.sh").read_text(encoding="utf-8")
    backup = (ROOT / "deploy" / "backup-from-nas.sh").read_text(encoding="utf-8")
    geschuetzt = set(re.findall(r"--exclude='\./([^'*]+)'", sync))
    gesichert = set(re.findall(r"^\s+([a-z_/.-]+\.jsonl?)\s*$", backup, re.M))
    out = []
    for s in sorted(ist_mengen()["speicher"]):
        ordner = s.split("/")[0]
        if s not in geschuetzt and ordner not in geschuetzt:
            out.append(f"Deploy-Schutz fehlt: {s} (sync-to-nas.sh wuerde eine lokale Kopie auf die NAS schieben)")
        if s not in gesichert:
            out.append(f"kein Backup: {s}")
    return out


def main(argv: list[str]) -> int:
    if "--liste" in argv:
        for name, werte in ist_mengen().items():
            print(f"## {name} ({len(werte)})")
            for w, dateien in sorted(werte.items()):
                print(f"{w:45s} # {', '.join(sorted(dateien)[:3])}")
        return 0
    fehler = pruefe_roadmaps() + pruefe_datenfluesse()
    hinweise = hinweise_speicher()
    if hinweise:
        print(f"Hinweise (blockieren nicht, Stand siehe docs/bekannte-fehler.md): {len(hinweise)}")
        for h in hinweise:
            print(f"  ~ {h}")
    if fehler:
        print(f"Doku-Check: {len(fehler)} Abweichung(en)")
        for f in fehler:
            print(f"  - {f}")
        return 1
    print("Doku-Check: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
