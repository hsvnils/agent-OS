"""Skill-Werkstatt (SKILL_WERKSTATT S1-S4, CEO 2026-10-16): eigene Skills beobachten, bauen, pruefen, verbessern.

Grundsatz (CEO): **keine fremden Skills uebernehmen** -- von aussen kommen nur Ideen (Name, Zweck, Kategorie). Skills
schreibt LUNA selbst; „trainieren“ = Anleitung + Pruffaelle + Rueckmeldungen, kein Modell-Feintuning.

- **S1 Skill-Radar:** GitHub-Themen (nur Name, Kurzbeschreibung, Sterne) -> Abteilung zuordnen -> „haben wir“ / „Luecke“.
- **S2 Luecken:** Fachagent-Nutzung (ohne Inhalte), Erfahrungsspeicher, verbreitete Luecken aus S1 -> Ideen in der Werkstatt.
- **S3 Werkstatt:** Entwurf + Pruffaelle ueber das Backoffice (lokales Modell, kostenlos), Probelauf **mit und ohne** Skill,
  Urteil je Pruffall; nur wenn der Skill besser ist -> zur Freigabe; aktiv erst nach Klick des CEO.
- **S4 Lernen:** 👍/👎 + Korrektur je Skill; ab 3 neuen Rueckmeldungen neue Version (alt gegen neu geprueft), Freigabe,
  Rueckweg auf die alte Version jederzeit.

Aktive Werkstatt-Skills liegen in `skills_eigen/<abteilung>/<name>/SKILL.md` (NAS, nicht im Git) und werden von
`dept_skills` zusaetzlich geladen (gleicher Name ueberschreibt den Repo-Skill). Alles regelbasiert ausser den
Backoffice-Auftraegen (lokales Modell).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

ABTEILUNGEN = {"berater": "Unternehmensberater", "cao": "Verwaltung (CAO)", "cfo": "Finanzen (CFO)", "cro": "Vertrieb (CRO)",
               "ciso": "Sicherheit (CISO)", "cbo": "Marke (CBO)", "cpo": "Produkt (CPO)", "cto": "Technik (CTO)",
               "cxo": "Erlebnis (CXO)", "cco": "Content (CCO)", "cdo": "Daten (CDO)", "chro": "Personal (CHRO)",
               "clo": "Recht (CLO)", "cko": "Wissen (CKO)", "res": "Researcher", "vid": "Videograf"}
# Stichwoerter (englisch/deutsch) -> Abteilung, fuer die Einordnung fremder Skill-Arten (nur Idee, nie Inhalt)
STICHWORTE = {
    "cfo": ["finance", "invoice", "accounting", "tax", "bookkeeping", "budget", "expense", "rechnung", "steuer"],
    "clo": ["legal", "contract", "compliance", "gdpr", "privacy", "law", "terms", "vertrag", "recht"],
    "ciso": ["security", "pentest", "vulnerab", "secret", "threat", "malware", "sicherheit"],
    "cto": ["coding", "code-review", "developer", "git", "testing", "devops", "debug", "deploy", "refactor"],
    "cco": ["content", "social", "instagram", "tiktok", "copywriting", "marketing", "seo", "blog", "caption"],
    "vid": ["video", "editing", "youtube", "reel", "subtitle", "film", "storyboard"],
    "cro": ["sales", "crm", "lead", "outreach", "pitch", "prospect", "negotiat", "proposal"],
    "cdo": ["data", "analytics", "sql", "dashboard", "chart", "metric", "spreadsheet", "excel"],
    "res": ["research", "search", "scraping", "citation", "fact-check", "summar"],
    "cxo": ["design", "ux", "ui", "accessib", "frontend", "figma"],
    "cpo": ["product", "roadmap", "requirement", "prd", "feature", "user-story"],
    "chro": ["recruit", "hiring", "onboarding", "hr", "interview"],
    "cko": ["knowledge", "memory", "notes", "documentation", "wiki", "obsidian"],
    "cao": ["email", "calendar", "scheduling", "admin", "document", "pdf", "office", "meeting"],
    "berater": ["strategy", "business", "planning", "pricing", "consulting", "market"],
    "cbo": ["brand", "branding", "tone-of-voice", "style-guide", "identity"],
}
# Englische Stichwoerter -> deutsche Entsprechung in unseren Skill-Namen (fuer „haben wir schon“)
SYNONYME = {"invoice": "rechnung", "accounting": "buchhaltung", "tax": "steuer", "expense": "ausgabe", "contract": "vertrag",
            "legal": "recht", "privacy": "datenschutz", "gdpr": "datenschutz", "security": "sicherheit", "sales": "vertrieb",
            "proposal": "angebot", "outreach": "akquise", "negotiat": "verhandl", "research": "recherche", "summar": "zusammenfass",
            "data": "daten", "metric": "kennzahl", "design": "gestalt", "email": "mail", "calendar": "kalender",
            "scheduling": "termin", "meeting": "termin", "document": "dokument", "pricing": "preis", "strategy": "strategie",
            "brand": "marke", "recruit": "personal", "hiring": "personal", "knowledge": "wissen", "notes": "notiz",
            "subtitle": "untertitel", "editing": "schnitt", "storyboard": "drehbuch", "roadmap": "roadmap", "feature": "funktion"}
GITHUB_THEMEN = ("agent-skills", "claude-skills", "ai-agent-skills", "llm-skills")
RUECKMELDUNGEN_FUER_VERSION = 3


def _jetzt() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _wort(t: str) -> set[str]:
    return set(re.findall(r"[a-zäöüß0-9]{3,}", str(t or "").lower()))


# -- Bestand ------------------------------------------------------------------------------------------------------------
def eigene_skills(repo: Path, eigen: Path | None = None) -> list[dict]:
    """Alle unsere Skills: Repo (`skills/`) und Werkstatt (`skills_eigen/`, ueberschreibt gleichnamige)."""
    from .skill_format import parse_skill_card
    out: dict[tuple, dict] = {}
    for quelle, basis in (("repo", Path(repo) / "skills"), ("werkstatt", Path(eigen) if eigen else None)):
        if not basis or not basis.is_dir():
            continue
        for md in sorted(basis.glob("*/*/SKILL.md")):
            card = parse_skill_card(md.read_text(encoding="utf-8", errors="replace"))
            ab, name = md.parent.parent.name, md.parent.name
            out[(ab, name)] = {"abteilung": ab, "name": card.get("name") or name, "ordner": name, "version": card.get("version", ""),
                               "beschreibung": card.get("beschreibung", ""), "quelle": quelle}
    return sorted(out.values(), key=lambda s: (s["abteilung"], s["name"]))


def einordnen(text: str) -> list[str]:
    t = str(text or "").lower()
    return [ab for ab, ws in STICHWORTE.items() if any(re.search(rf"(?<![a-z]){re.escape(w)}", t) for w in ws)]


def aehnlicher_skill(text: str, abteilung: str, skills: list[dict]) -> str:
    """Name eines eigenen Skills derselben Abteilung, der dasselbe Stichwort traegt (sonst '')."""
    treffer = [w for w in STICHWORTE.get(abteilung, []) if re.search(rf"(?<![a-z]){re.escape(w)}", str(text).lower())]
    such = {w.replace("-", " ") for w in treffer} | {SYNONYME[w] for w in treffer if w in SYNONYME}
    for s in skills:
        if s["abteilung"] == abteilung:
            eigen = f"{s['name']} {s['beschreibung']}".lower().replace("-", " ")
            if any(w in eigen for w in such) or _wort(text) & _wort(s["name"].replace("-", " ")):
                return s["name"]
    return ""


# -- Speicher -----------------------------------------------------------------------------------------------------------
_LOCK = threading.Lock()


class Werkstatt:
    """`skills_werkstatt/` (Ideen, Werkstatt-Eintraege, Rueckmeldungen) + `skills_eigen/` (aktive eigene Skills)."""

    def __init__(self, ordner: Path, eigen: Path, repo: Path):
        self.dir, self.eigen, self.repo = Path(ordner), Path(eigen), Path(repo)

    def _lesen(self, name: str) -> dict:
        try:
            return json.loads((self.dir / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _schreiben(self, name: str, d: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix="." + name, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.dir / name)

    def radar(self) -> dict:
        return self._lesen("radar.json")

    def eintraege(self) -> dict:
        return self._lesen("werkstatt.json")

    def rueckmeldungen(self) -> dict:
        return self._lesen("rueckmeldungen.json")

    def skills(self) -> list[dict]:
        return eigene_skills(self.repo, self.eigen)

    # S1 --------------------------------------------------------------------------------------------------------------
    def radar_merken(self, repos: list, jetzt: str) -> list[dict]:
        """GitHub-Treffer (nur Metadaten) einordnen -> neue Ideen zurueck. Kein Inhalt fremder Skills wird gespeichert."""
        skills = self.skills()
        with _LOCK:
            d = self._lesen("radar.json")
            ideen, neu = d.setdefault("ideen", {}), []
            for r in repos:
                if r.name in ideen:
                    ideen[r.name]["sterne"] = r.sterne
                    continue
                text = f"{r.name} {r.beschreibung} {' '.join(r.topics)}"
                abt = einordnen(text)
                x = {"name": r.name, "url": r.url, "sterne": r.sterne, "kurz": " ".join(str(r.beschreibung).split())[:140],
                     "abteilungen": abt, "gesehen": jetzt,
                     "eigener": {a: aehnlicher_skill(text, a, skills) for a in abt}}
                x["status"] = "luecke" if abt and not all(x["eigener"].values()) else ("vorhanden" if abt else "ohne_bezug")
                ideen[r.name] = x
                neu.append(x)
            d["ts"] = jetzt
            self._schreiben("radar.json", d)
        return neu

    # S2 --------------------------------------------------------------------------------------------------------------
    def idee(self, *, abteilung: str, titel: str, warum: str, quelle: str, jetzt: str) -> dict | None:
        """Werkstatt-Idee anlegen (dedupliziert ueber Abteilung + Titel). None, wenn schon vorhanden."""
        if abteilung not in ABTEILUNGEN:
            raise ValueError("Unbekannte Abteilung.")
        k = hashlib.sha1(f"{abteilung}|{titel.lower()}".encode()).hexdigest()[:10]
        with _LOCK:
            d = self._lesen("werkstatt.json")
            if any(e.get("schluessel") == k for e in d.values()):
                return None
            wid = "W-" + uuid.uuid4().hex[:6].upper()
            d[wid] = {"id": wid, "schluessel": k, "abteilung": abteilung, "titel": titel[:120], "warum": warum[:600],
                      "quelle": quelle, "status": "idee", "erstellt": jetzt, "verlauf": [{"ts": jetzt, "text": f"Idee ({quelle})"}],
                      "jobs": {}, "art": "neu"}
            self._schreiben("werkstatt.json", d)
        return d[wid]

    def _aendern(self, wid: str, fn) -> dict:
        with _LOCK:
            d = self._lesen("werkstatt.json")
            if wid not in d:
                raise KeyError(wid)
            fn(d[wid])
            self._schreiben("werkstatt.json", d)
            return d[wid]

    def status(self, wid: str, status: str, text: str, **extra) -> dict:
        def f(e):
            e.update(extra)
            e["status"] = status
            e["verlauf"].append({"ts": _jetzt(), "text": text})
        return self._aendern(wid, f)

    # S4 --------------------------------------------------------------------------------------------------------------
    def rueckmeldung(self, skill: str, *, gut: bool, text: str = "", von: str = "CEO", jetzt: str | None = None) -> dict:
        """skill = „abteilung/name“ eines vorhandenen Skills."""
        ab, _, name = str(skill).partition("/")
        if not any(s["abteilung"] == ab and (s["name"] == name or s["ordner"] == name) for s in self.skills()):
            raise KeyError(skill)
        with _LOCK:
            d = self._lesen("rueckmeldungen.json")
            liste = d.setdefault(f"{ab}/{name}", [])
            liste.append({"ts": jetzt or _jetzt(), "gut": bool(gut), "text": " ".join(str(text or "").split())[:500], "von": von,
                          "verarbeitet": False})
            self._schreiben("rueckmeldungen.json", d)
        return {"skill": f"{ab}/{name}", "anzahl": len(liste)}

    def rueckmeldungen_verarbeitet(self, skill: str) -> None:
        with _LOCK:
            d = self._lesen("rueckmeldungen.json")
            for r in d.get(skill, []):
                r["verarbeitet"] = True
            self._schreiben("rueckmeldungen.json", d)

    # Aktivieren / Rueckweg --------------------------------------------------------------------------------------------
    def skill_text(self, abteilung: str, ordner: str) -> str:
        for p in (self.eigen / abteilung / ordner / "SKILL.md", self.repo / "skills" / abteilung / ordner / "SKILL.md"):
            if p.exists():
                return p.read_text(encoding="utf-8")
        return ""

    def aktivieren(self, wid: str, *, von: str = "CEO") -> dict:
        """Gepruefter Entwurf -> `skills_eigen/<abt>/<name>/SKILL.md`; die bisherige Fassung bleibt als Rueckweg erhalten."""
        e = self.eintraege().get(wid)
        if not e:
            raise KeyError(wid)
        if e["status"] != "zur_freigabe":
            raise ValueError("Nur gepruefte Entwuerfe, die besser waren, koennen aktiviert werden.")
        ordner = self.eigen / e["abteilung"] / e["ordner"]
        ordner.mkdir(parents=True, exist_ok=True)
        alt = self.skill_text(e["abteilung"], e["ordner"])
        if alt:
            (ordner / "versionen").mkdir(exist_ok=True)
            (ordner / "versionen" / f"{_jetzt().replace(':', '-')}.md").write_text(alt, encoding="utf-8")
        (ordner / "SKILL.md").write_text(e["skill_md"], encoding="utf-8")
        (ordner / "pruffaelle.json").write_text(json.dumps(e["pruffaelle"], ensure_ascii=False, indent=1), encoding="utf-8")
        if e.get("art") == "verbesserung":
            self.rueckmeldungen_verarbeitet(f"{e['abteilung']}/{e['skill_name']}")
        return self.status(wid, "aktiv", f"aktiviert ({von})")

    def zurueck(self, abteilung: str, ordner: str) -> dict:
        """Letzte gesicherte Fassung wiederherstellen (bei Repo-Skills ohne Sicherung: Werkstatt-Fassung entfernen)."""
        d = self.eigen / abteilung / ordner
        versionen = sorted((d / "versionen").glob("*.md")) if (d / "versionen").is_dir() else []
        if versionen:
            (d / "SKILL.md").write_text(versionen[-1].read_text(encoding="utf-8"), encoding="utf-8")
            versionen[-1].unlink()
            return {"wiederhergestellt": versionen[-1].stem}
        if (d / "SKILL.md").exists() and (self.repo / "skills" / abteilung / ordner / "SKILL.md").exists():
            (d / "SKILL.md").unlink()
            return {"wiederhergestellt": "Repo-Fassung"}
        raise ValueError("Keine aeltere Fassung vorhanden.")


# -- S3/S4: Auftraege an das Backoffice (lokales Modell) -----------------------------------------------------------------
FORMAT = """Antworte GENAU in diesem Format:
===SKILL===
---
name: <kebab-case-name>
version: {version}
beschreibung: <ein Satz>
lizenz: intern
autor: LUNA Skill-Werkstatt
governance: intern
modell: Richtwert (modell-agnostisch)
---
# Skill: <Titel>

## Wann anwenden
...
## Vorgehen
1. ...
## Ergebnis
...
===PRUEFFAELLE===
[{{"eingabe": "<typische Aufgabe an die Abteilung>", "kriterien": ["<pruefbares Merkmal einer guten Antwort>", "..."]}}]
"""
SYSTEM_ENTWURF = ("Du bist die Skill-Werkstatt von Hanserautisch (Social-Media-Content und Werbung fuer Unternehmen, Hamburg, "
                  "Kleinunternehmer). Du schreibst EIGENE Arbeitsanleitungen (Skills) fuer einen Fachagenten -- nichts aus "
                  "fremden Quellen kopieren, keine Skripte, kein Code, keine Links zum Ausfuehren. Deutsch, knapp, konkret. "
                  "Lege 3 bis 5 Pruffaelle mit je 2 bis 4 klar pruefbaren Kriterien an.")
SYSTEM_URTEIL = ("Du bewertest zwei Antworten auf dieselbe Aufgabe streng nach den Kriterien. Antworte NUR mit JSON: "
                 '{"A": <Zahl erfuellter Kriterien>, "B": <Zahl erfuellter Kriterien>, "besser": "A"|"B"|"gleich"}')


def entwurf_aufgabe(e: dict, skills: list[dict], beispiel: str) -> str:
    vorhanden = ", ".join(s["name"] for s in skills if s["abteilung"] == e["abteilung"]) or "keine"
    return (f"Abteilung: {ABTEILUNGEN[e['abteilung']]}\nGewuenschter Skill: {e['titel']}\nWarum: {e['warum']}\n"
            f"Vorhandene Skills dieser Abteilung (nicht doppeln): {vorhanden}\n\nBeispiel unseres Formats:\n{beispiel[:1500]}\n\n"
            + FORMAT.format(version="1.0.0"))


def verbesserung_aufgabe(skill_md: str, rueckmeldungen: list[dict], version: str) -> str:
    rm = "\n".join(f"- {'👍' if r['gut'] else '👎'} {r['text'] or '(ohne Text)'}" for r in rueckmeldungen)
    return (f"Verbessere diesen Skill anhand der Rueckmeldungen des CEO. Behalte, was gelobt wurde; aendere, was kritisiert "
            f"wurde. Neue Version {version}.\n\nAktueller Skill:\n{skill_md[:5000]}\n\nRueckmeldungen:\n{rm}\n\n"
            + FORMAT.format(version=version))


def entwurf_lesen(text: str) -> tuple[str, list[dict]]:
    """Antwort des Modells -> (SKILL.md, Pruffaelle). ValueError, wenn das Format nicht stimmt."""
    m = re.search(r"===SKILL===\s*(.*?)\s*===PRUEFFAELLE===\s*(.*)$", text or "", re.S)
    if not m:
        raise ValueError("Antwort ohne ===SKILL===/===PRUEFFAELLE===")
    skill = m.group(1).strip()
    j = re.search(r"\[.*\]", m.group(2), re.S)
    try:
        faelle = json.loads(j.group(0)) if j else []
    except ValueError:
        raise ValueError("Pruffaelle sind kein gueltiges JSON") from None
    faelle = [{"eingabe": str(f.get("eingabe", ""))[:800], "kriterien": [str(k)[:200] for k in (f.get("kriterien") or [])][:5]}
              for f in faelle if isinstance(f, dict) and f.get("eingabe") and f.get("kriterien")][:5]
    if len(faelle) < 2:
        raise ValueError("Zu wenige Pruffaelle")
    return skill, faelle


def pruefen_entwurf(skill_md: str) -> tuple[str, list[str]]:
    """Format + Security-Gate in einem Wegwerf-Ordner -> (ordnername, Probleme). Ein abgelehnter Entwurf wird nie aktiv."""
    from .skill_format import parse_skill_card, validiere
    from .skill_gate import pruefe_skill
    card = parse_skill_card(skill_md)
    name = re.sub(r"[^a-z0-9-]", "", str(card.get("name", "")).lower())[:60]
    probleme = []
    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / (name or "entwurf")
        d.mkdir()
        (d / "SKILL.md").write_text(skill_md, encoding="utf-8")
        probleme += [f.titel for f in validiere(d) if f.schwere in ("mittel", "hoch")]
        g = pruefe_skill(d)
        if g.blockiert:
            probleme.append(f"Sicherheits-Gate: {g.verdikt}")
    if not name:
        probleme.append("Name fehlt")
    if (card.get("lizenz") or "").lower() != "intern":
        probleme.append("Lizenz muss „intern“ sein (nur eigene Skills)")
    return name, probleme


def _body(md: str) -> str:
    m = re.match(r"^\s*---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|$)", md or "", re.S)
    return (md[m.end():] if m else md).strip()


def system_fachagent(abteilung: str, skill_md: str = "") -> str:
    s = (f"Du bist der Fachagent {ABTEILUNGEN.get(abteilung, abteilung)} von Hanserautisch (Social-Media-Content und "
         f"Werbung fuer Unternehmen, Hamburg). Antworte auf Deutsch, knapp und konkret.")
    return s + (f"\n\n## Skill\n{_body(skill_md)}" if skill_md else "")


def urteil_lesen(text: str) -> dict:
    m = re.search(r"\{.*?\}", text or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    zahl = lambda x: int(x) if str(x).isdigit() else 0
    return {"A": zahl(d.get("A")), "B": zahl(d.get("B")), "besser": d.get("besser") if d.get("besser") in ("A", "B", "gleich") else "gleich"}


def _reihenfolge(wid: str, i: int) -> bool:
    """Ob die Kandidaten-Antwort als „A“ gezeigt wird (verdeckt, aber nachvollziehbar je Eintrag und Fall)."""
    return int(hashlib.sha1(f"{wid}|{i}".encode()).hexdigest(), 16) % 2 == 0


def tick(w: Werkstatt, bo, *, jetzt: str | None = None) -> list[str]:
    """Ein Schritt fuer alle laufenden Eintraege (Entwurf -> Probelauf -> Urteil -> Ergebnis). `bo` = Backoffice-Store
    (anlegen/get). Gibt Meldungen fuer den CEO zurueck (nur Ergebnisse, die eine Entscheidung brauchen)."""
    meldungen = []
    for wid, e in list(w.eintraege().items()):
        jobs = e.get("jobs") or {}
        try:
            if e["status"] == "entwurf_angefragt":
                r = bo.get(jobs.get("entwurf", ""))
                if r and r.get("status") == "fehlgeschlagen":
                    w.status(wid, "fehler", f"Entwurf fehlgeschlagen: {r.get('grund', '')}"[:200])
                elif r and r.get("status") == "fertig":
                    skill_md, faelle = entwurf_lesen(r.get("ergebnis", ""))
                    name, probleme = pruefen_entwurf(skill_md)
                    if probleme:
                        w.status(wid, "fehler", "Entwurf ungueltig: " + "; ".join(probleme)[:300], skill_md=skill_md)
                        continue
                    ordner = e.get("ordner") or name
                    vergleich = w.skill_text(e["abteilung"], ordner) if e.get("art") == "verbesserung" else ""
                    neu = {}
                    for i, f in enumerate(faelle):
                        neu[f"kand{i}"] = bo.anlegen(f["eingabe"], art="roh", von="Skill-Werkstatt", stumm=True,
                                                     system=system_fachagent(e["abteilung"], skill_md), zweck=f"skill:{wid}:kand{i}")
                        neu[f"verg{i}"] = bo.anlegen(f["eingabe"], art="roh", von="Skill-Werkstatt", stumm=True,
                                                     system=system_fachagent(e["abteilung"], vergleich), zweck=f"skill:{wid}:verg{i}")
                    w.status(wid, "probelauf", f"Entwurf geprueft ({len(faelle)} Pruffaelle) -- Probelauf "
                             + ("alte gegen neue Fassung" if vergleich else "mit und ohne Skill"),
                             skill_md=skill_md, pruffaelle=faelle, ordner=ordner, jobs=jobs | neu)
            elif e["status"] == "probelauf":
                faelle = e["pruffaelle"]
                fertig = {k: bo.get(v) for k, v in jobs.items() if k.startswith(("kand", "verg"))}
                if any((x or {}).get("status") == "fehlgeschlagen" for x in fertig.values()):
                    w.status(wid, "fehler", "Probelauf fehlgeschlagen")
                elif all((x or {}).get("status") == "fertig" for x in fertig.values()):
                    neu = {}
                    for i, f in enumerate(faelle):
                        kand, verg = fertig[f"kand{i}"]["ergebnis"], fertig[f"verg{i}"]["ergebnis"]
                        a, b = (kand, verg) if _reihenfolge(wid, i) else (verg, kand)
                        aufgabe = (f"Aufgabe: {f['eingabe']}\nKriterien:\n" + "\n".join(f"- {k}" for k in f["kriterien"])
                                   + f"\n\nAntwort A:\n{a[:3500]}\n\nAntwort B:\n{b[:3500]}")
                        neu[f"urteil{i}"] = bo.anlegen(aufgabe, art="roh", von="Skill-Werkstatt", stumm=True, system=SYSTEM_URTEIL,
                                                       zweck=f"skill:{wid}:urteil{i}")
                    w.status(wid, "urteil", "Probelauf fertig -- Bewertung je Pruffall", jobs=jobs | neu)
            elif e["status"] == "urteil":
                urteile = {k: bo.get(v) for k, v in jobs.items() if k.startswith("urteil")}
                if any((x or {}).get("status") == "fehlgeschlagen" for x in urteile.values()):
                    w.status(wid, "fehler", "Bewertung fehlgeschlagen")
                elif all((x or {}).get("status") == "fertig" for x in urteile.values()):
                    kand = verg = siege = niederlagen = 0
                    for i in range(len(e["pruffaelle"])):
                        u = urteil_lesen(urteile[f"urteil{i}"]["ergebnis"])
                        vorne = _reihenfolge(wid, i)
                        kand += u["A"] if vorne else u["B"]
                        verg += u["B"] if vorne else u["A"]
                        gewinner = {"A": "kand" if vorne else "verg", "B": "verg" if vorne else "kand"}.get(u["besser"])
                        siege += gewinner == "kand"
                        niederlagen += gewinner == "verg"
                    max_p = sum(len(f["kriterien"]) for f in e["pruffaelle"])
                    ergebnis = {"kandidat": kand, "vergleich": verg, "max": max_p, "siege": siege, "niederlagen": niederlagen}
                    besser = kand > verg or (kand == verg and siege > niederlagen)
                    was = "neue Fassung" if e.get("art") == "verbesserung" else "mit Skill"
                    gegen = "alte Fassung" if e.get("art") == "verbesserung" else "ohne Skill"
                    text = f"{was} {kand}/{max_p} gegen {gegen} {verg}/{max_p} Kriterien"
                    if besser:
                        w.status(wid, "zur_freigabe", f"Besser: {text}", ergebnis=ergebnis)
                        meldungen.append(f"🛠 Skill „{e['titel']}“ ({ABTEILUNGEN[e['abteilung']]}) ist geprüft und besser: {text}. "
                                         "Bitte in LUNA-OS → Skill-Werkstatt freigeben oder verwerfen.")
                    else:
                        w.status(wid, "nicht_besser", f"Nicht besser: {text}", ergebnis=ergebnis)
        except (ValueError, KeyError) as exc:
            w.status(wid, "fehler", f"{exc}"[:200])
    return meldungen


def entwurf_starten(w: Werkstatt, bo, wid: str) -> dict:
    """Idee -> Backoffice-Auftrag fuer den Entwurf (CEO-Klick „Entwurf bauen“)."""
    e = w.eintraege().get(wid)
    if not e:
        raise KeyError(wid)
    if e["status"] not in ("idee", "nicht_besser", "fehler"):
        raise ValueError("Dieser Eintrag ist schon in Arbeit oder fertig.")
    skills = w.skills()
    if e.get("art") == "verbesserung":
        aufgabe = e["aufgabe"]
    else:
        beispiel = next((w.skill_text(s["abteilung"], s["ordner"]) for s in skills if s["abteilung"] == e["abteilung"]),
                        w.skill_text("cpo", "funktionsantrag-bewerten"))
        aufgabe = entwurf_aufgabe(e, skills, beispiel)
    jid = bo.anlegen(aufgabe, art="roh", von="Skill-Werkstatt", stumm=True, system=SYSTEM_ENTWURF, zweck=f"skill:{wid}:entwurf")
    return w.status(wid, "entwurf_angefragt", "Entwurf beim Backoffice angefragt (lokales Modell)", jobs={"entwurf": jid})


def verbesserungen_anstossen(w: Werkstatt, *, jetzt: str | None = None) -> list[dict]:
    """S4: ab 3 neuen Rueckmeldungen je Skill (mind. eine Kritik) einen Werkstatt-Eintrag „Verbesserung“ anlegen."""
    out = []
    laufend = {(e["abteilung"], e.get("skill_name")) for e in w.eintraege().values()
               if e.get("art") == "verbesserung" and e["status"] not in ("aktiv", "verworfen", "nicht_besser", "fehler")}
    for skill, liste in w.rueckmeldungen().items():
        offen = [r for r in liste if not r.get("verarbeitet")]
        ab, _, name = skill.partition("/")
        if len(offen) < RUECKMELDUNGEN_FUER_VERSION or not any(not r["gut"] or r["text"] for r in offen) or (ab, name) in laufend:
            continue
        s = next((x for x in w.skills() if x["abteilung"] == ab and x["name"] == name), None)
        if not s:
            continue
        teile = (s["version"] or "1.0.0").split(".")
        version = f"{teile[0]}.{int(teile[1]) + 1 if len(teile) > 1 and teile[1].isdigit() else 1}.0"
        e = w.idee(abteilung=ab, titel=f"{name} → Version {version}", warum=f"{len(offen)} Rückmeldungen des CEO",
                   quelle="Rückmeldungen", jetzt=jetzt or _jetzt())
        if not e:
            continue
        aufgabe = verbesserung_aufgabe(w.skill_text(ab, s["ordner"]), offen, version)
        out.append(w._aendern(e["id"], lambda x: x.update({"art": "verbesserung", "skill_name": name, "ordner": s["ordner"],
                                                            "aufgabe": aufgabe})))
    return out


# -- S2: Luecken aus der eigenen Arbeit ------------------------------------------------------------------------------------
def luecken(w: Werkstatt, *, nutzung: dict, trajektorien: list[dict], jetzt: str) -> list[dict]:
    """Ideen aus (a) haeufig gefragten Abteilungen ohne/mit wenig Skills oder vielen Fehlern, (b) wiederkehrenden
    erfolgreichen Ablaeufen ohne passenden Skill, (c) verbreiteten Luecken aus dem Skill-Radar (>= 200 Sterne)."""
    skills = w.skills()
    neu = []
    anzahl = {ab: sum(1 for s in skills if s["abteilung"] == ab) for ab in ABTEILUNGEN}
    for ab, n in (nutzung or {}).items():
        if ab not in ABTEILUNGEN or n.get("anzahl", 0) < 5:
            continue
        if anzahl.get(ab, 0) == 0:
            neu.append(w.idee(abteilung=ab, titel=f"Grund-Skill {ABTEILUNGEN[ab]}", jetzt=jetzt, quelle="Nutzung",
                              warum=f"{n['anzahl']}× gefragt in 30 Tagen, noch kein Skill"))
        elif n.get("fehler", 0) / max(1, n["anzahl"]) >= 0.3:
            neu.append(w.idee(abteilung=ab, titel=f"Häufige Fehler {ABTEILUNGEN[ab]} vermeiden", jetzt=jetzt, quelle="Nutzung",
                              warum=f"{n['fehler']} von {n['anzahl']} Anfragen ohne Erfolg (30 Tage)"))
    je_tag: dict[str, int] = {}
    for t in trajektorien or []:
        if t.get("erfolg", True):
            for tag in t.get("tags") or []:
                je_tag[tag.lower()] = je_tag.get(tag.lower(), 0) + 1
    for tag, n in je_tag.items():
        abt = (einordnen(tag) or [None])[0]
        if n >= 3 and abt and not aehnlicher_skill(tag, abt, skills):
            neu.append(w.idee(abteilung=abt, titel=f"Ablauf „{tag}“", jetzt=jetzt, quelle="Erfahrungen",
                              warum=f"{n}× erfolgreich erledigt, noch ohne Skill"))
    for x in (w.radar().get("ideen") or {}).values():
        if x["status"] == "luecke" and x["sterne"] >= 200:
            for ab in x["abteilungen"]:
                if not x["eigener"].get(ab):
                    kat = next((wort for wort in STICHWORTE[ab] if wort in f"{x['name']} {x['kurz']}".lower()), ab)
                    neu.append(w.idee(abteilung=ab, titel=f"Eigener Skill: {kat}", jetzt=jetzt, quelle="Skill-Radar",
                                      warum=f"Verbreitete Skill-Art (z. B. {x['name']}, {x['sterne']} Sterne) -- wir schreiben "
                                            "einen eigenen, nichts wird uebernommen"))
    return [x for x in neu if x]


def radar_bericht(neu: list[dict]) -> str:
    luecken_ = [x for x in neu if x["status"] == "luecke"]
    zeilen = [f"• {', '.join(ABTEILUNGEN[a] for a in x['abteilungen'] if not x['eigener'].get(a))}: {x['name']} ({x['sterne']}★)"
              for x in sorted(luecken_, key=lambda x: -x["sterne"])[:6]]
    return (f"🛠 Skill-Radar: {len(neu)} neue Skill-Arten beobachtet, {len(luecken_)} davon Lücken bei uns."
            + ("\n" + "\n".join(zeilen) if zeilen else "")
            + "\nNur Ideen – übernommen wird nichts. Eigene Skills baut die Skill-Werkstatt in LUNA-OS.")
