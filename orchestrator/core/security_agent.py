"""Phase 21 -- Cybersecurity-Agent (CISO-Ausbau).

Kostenloser, **regelbasierter** Sicherheits-Audit (kein LLM) entlang der drei vom CEO gefragten
Stossrichtungen: **Zugriffe verhindern · Luecken finden · Luecken schliessen.** Entworfen als Loop nach
`governance/autonomie-stufen.md`:

- **L1 (melden):** `audit()` sammelt Befunde, `lauf()` meldet sie an den CEO (Notifier).
- **L2 (vorschlagen):** `lauf(als_antrag=True)` buendelt die Befunde + Empfehlungen zu EINEM entscheidungs-
  reifen **Antrag** (Phase 6). **Keine autonome Systemaenderung** -- Sperren/Aendern/Key-Rotation bleibt
  CEO-Tor (AGENTS.md 4/5.7: CISO autorisiert, CTO setzt um).

Checks (alle lokal, kostenlos, deterministisch, injizierbar -> Self-Checks ohne Netz):
1. **Secret-Hygiene:** `.gitignore` deckt Secrets/Datenstores; **keine Secrets in git getrackt**.
2. **Hardening:** Login-Schutz aktiv (`LUNA_OS_PASSWORD`), Leck-Schutz vorhanden.
3. **Dependencies (best-effort):** `pip-audit` (falls verfuegbar) -> bekannte CVEs; sonst Empfehlung.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# Punkte je Schwere fuer den Risiko-Score (0-100), angelehnt an SkillSpector-Gewichtung.
_SCORE_PUNKTE = {"hoch": 25, "mittel": 10, "niedrig": 5}

# Muster, die in .gitignore stehen MUESSEN (Secrets/Zugaenge). Substring-Match gegen die .gitignore.
_PFLICHT_IGNORE = (".env", "client_secret", "token")
# Getrackte Dateien, die NIE im Repo landen duerfen (Secret-Leak). *.example ist erlaubt.
_SECRET_TRACKED = (".env", "client_secret", "credentials.json")

SCHWEREN = ("hoch", "mittel", "niedrig", "ok")


@dataclass
class Finding:
    kategorie: str
    schwere: str            # hoch | mittel | niedrig | ok
    titel: str
    detail: str = ""
    empfehlung: str = ""


class SecurityAgent:
    def __init__(self, *, repo_root, env: dict | None = None, secrets: list[str] | None = None,
                 run: Callable[[list], str] | None = None, http: Callable[[str, dict], dict] | None = None,
                 notify=None, antraege=None, changelog=None):
        self.root = Path(repo_root)
        self.env = env or {}
        self.secrets = secrets or []
        self.run = run                 # injizierbarer Kommando-Runner (git ls-files, pip-audit) -> stdout
        self.http = http               # injizierbarer HTTP-POST (url, json) -> dict (OSV.dev); None = uebersprungen
        self.notify = notify
        self.antraege = antraege
        self.changelog = changelog

    # -- Audit --

    def audit(self) -> list[Finding]:
        checks = (self._check_secret_hygiene() + self._check_hardening()
                  + self._check_dependencies() + self._check_code_security())
        if self.http is not None:      # OSV.dev nur wenn ein HTTP-Client verdrahtet ist (sonst kein Rauschen)
            checks += self._check_osv()
        return checks

    def _check_secret_hygiene(self) -> list[Finding]:
        out: list[Finding] = []
        gi = self.root / ".gitignore"
        text = gi.read_text(encoding="utf-8") if gi.exists() else ""
        fehlend = [m for m in _PFLICHT_IGNORE if m not in text]
        if not gi.exists():
            out.append(Finding("secret-hygiene", "hoch", "Keine .gitignore vorhanden",
                               "Secrets/Datenstores koennten versehentlich commitet werden.",
                               ".gitignore anlegen (mind. .env, client_secret*, *token*.json)."))
        elif fehlend:
            out.append(Finding("secret-hygiene", "hoch", "Secret-Muster fehlen in .gitignore",
                               "Nicht abgedeckt: " + ", ".join(fehlend),
                               "Diese Muster in .gitignore ergaenzen."))
        else:
            out.append(Finding("secret-hygiene", "ok", ".gitignore deckt Secrets/Datenstores", "", ""))
        # Sind Secrets versehentlich in git getrackt?
        tracked = self._git_tracked()
        if tracked is not None:
            leaks = [p for p in tracked if self._sieht_geheim_aus(p)]
            if leaks:
                out.append(Finding("secret-leak", "hoch", "Moegliche Secrets in git getrackt",
                                   "Getrackt: " + ", ".join(leaks[:8]),
                                   "Aus dem Index entfernen (git rm --cached), gitignoren, betroffene "
                                   "Keys ROTIEREN (CEO/CISO)."))
            else:
                out.append(Finding("secret-leak", "ok", "Keine Secrets im git-Index", "", ""))
        return out

    def _check_hardening(self) -> list[Finding]:
        out: list[Finding] = []
        if not (self.env.get("LUNA_OS_PASSWORD") or "").strip():
            out.append(Finding("hardening", "mittel", "LUNA-OS-Login evtl. offen",
                               "LUNA_OS_PASSWORD ist nicht gesetzt -> ohne Passwort ist die Weboberflaeche "
                               "offen (nur relevant auf dem Web-Host).",
                               "LUNA_OS_PASSWORD in der Host-.env setzen (starkes Passwort)."))
        else:
            out.append(Finding("hardening", "ok", "LUNA-OS-Login aktiv (Passwort gesetzt)", "", ""))
        # Leck-Schutz vorhanden?
        try:
            from ..governance.leak_guard import is_redactable_secret  # noqa: F401
            out.append(Finding("hardening", "ok", "Leck-Schutz aktiv (leak_guard)", "", ""))
        except Exception:
            out.append(Finding("hardening", "hoch", "Leck-Schutz fehlt",
                               "leak_guard nicht importierbar.", "Leck-Schutz wiederherstellen."))
        return out

    def _check_dependencies(self) -> list[Finding]:
        if self.run is None:
            return [Finding("dependencies", "niedrig", "Dependency-Audit nicht ausgefuehrt",
                            "Kein Kommando-Runner verfuegbar.",
                            "Regelmaessig `pip-audit` laufen lassen (bekannte CVEs in Abhaengigkeiten).")]
        roh = self.run(["pip-audit", "-f", "json"]) or ""
        if not roh.strip():
            return [Finding("dependencies", "niedrig", "pip-audit nicht verfuegbar",
                            "pip-audit lieferte keine Ausgabe (nicht installiert?).",
                            "pip-audit installieren + regelmaessig ausfuehren (CVE-Scan der Dependencies).")]
        try:
            data = json.loads(roh)
            deps = data.get("dependencies", data) if isinstance(data, dict) else data
            verwundbar = [d for d in deps if d.get("vulns")]
        except (ValueError, AttributeError, TypeError):
            return [Finding("dependencies", "niedrig", "pip-audit-Ausgabe nicht lesbar", roh[:120], "")]
        if verwundbar:
            liste = "; ".join(self._fmt_vuln(d) for d in verwundbar[:8])
            return [Finding("dependencies", "hoch", f"{len(verwundbar)} verwundbare Abhaengigkeit(en)",
                            "CVE-behaftet: " + liste,
                            "Betroffene Pakete aktualisieren (Antrag/PR; Tests gruen halten).")]
        return [Finding("dependencies", "ok", "Keine bekannten CVEs in den Dependencies", "", "")]

    def _check_code_security(self, unterordner: str = "orchestrator") -> list[Finding]:
        """Statischer AST-Scan des eigenen Codes auf riskante Aufrufe (SkillSpector-Muster).

        Praezise: flaggt nur echte Call-Knoten (keine Strings/Kommentare) und NICHT das sichere
        `subprocess.run([...])` -- nur `shell=True` ist der Ausloeser. Tests/Test-Dateien werden uebersprungen.
        """
        basis = self.root / unterordner
        if not basis.exists():
            return [Finding("code-security", "ok", "Kein Code-Verzeichnis zum Scannen", "", "")]
        treffer: list[tuple[str, str, int, str]] = []   # (schwere, datei, zeile, muster)
        for pfad in sorted(basis.rglob("*.py")):
            posix = pfad.as_posix()
            if "/tests/" in posix or pfad.name.startswith("test_"):
                continue
            try:
                baum = ast.parse(pfad.read_text(encoding="utf-8"))
            except (OSError, SyntaxError, ValueError):
                continue
            rel = pfad.relative_to(self.root).as_posix()
            for knoten in ast.walk(baum):
                if isinstance(knoten, ast.Call):
                    befund = self._einstufen_call(knoten)
                    if befund:
                        schwere, muster = befund
                        treffer.append((schwere, rel, getattr(knoten, "lineno", 0), muster))
        if not treffer:
            return [Finding("code-security", "ok", "Keine riskanten Code-Aufrufe gefunden", "", "")]

        def _zeilen(ts):
            return "; ".join(f"{datei}:{zeile} ({muster})" for _, datei, zeile, muster in ts[:8])

        out: list[Finding] = []
        hoch = [t for t in treffer if t[0] == "hoch"]
        mittel = [t for t in treffer if t[0] == "mittel"]
        if hoch:
            out.append(Finding("code-security", "hoch", f"{len(hoch)} riskante(r) Code-Aufruf(e)",
                               _zeilen(hoch),
                               "Pruefen/absichern: kein shell=True, kein eval/exec/os.system auf "
                               "Fremd-Eingaben (Fix als Branch+Tests)."))
        if mittel:
            out.append(Finding("code-security", "mittel", f"{len(mittel)} potenziell riskante(r) Code-Aufruf(e)",
                               _zeilen(mittel),
                               "Sichere Varianten nutzen (yaml.safe_load; kein pickle auf Fremddaten)."))
        return out

    @staticmethod
    def _einstufen_call(knoten: ast.Call) -> tuple[str, str] | None:
        """Stuft einen AST-Call ein -> (schwere, muster) oder None. Deterministisch, ohne Ausfuehrung."""
        f = knoten.func
        if isinstance(f, ast.Name):
            if f.id in ("eval", "exec"):
                return ("hoch", f"{f.id}()")
            if f.id == "__import__":
                return ("mittel", "__import__()")
        if isinstance(f, ast.Attribute):
            attr = f.attr
            wurzel = f.value.id if isinstance(f.value, ast.Name) else None
            if wurzel == "os" and attr in ("system", "popen"):
                return ("hoch", f"os.{attr}()")
            # subprocess NUR mit shell=True (sicheres Listen-argv bleibt unbeanstandet)
            if wurzel == "subprocess" or attr in ("run", "call", "Popen", "check_output", "check_call"):
                for kw in knoten.keywords:
                    if (kw.arg == "shell" and isinstance(kw.value, ast.Constant)
                            and kw.value.value is True):
                        return ("hoch", f"{attr}(shell=True)")
            if wurzel == "pickle" and attr in ("load", "loads"):
                return ("mittel", f"pickle.{attr}()")
            if wurzel == "yaml" and attr == "load":
                if not any(kw.arg == "Loader" for kw in knoten.keywords):
                    return ("mittel", "yaml.load(ohne Loader)")
        return None

    @staticmethod
    def _fmt_vuln(d: dict) -> str:
        """'<name> <version> [<CVE-ids>] -> fix: <versions>' -- macht den Befund umsetzbar."""
        vs = d.get("vulns") or []
        ids = ", ".join(str(v.get("id")) for v in vs if v.get("id"))
        fixes = ", ".join(fx for v in vs for fx in (v.get("fix_versions") or []))
        teil = f"{d.get('name')} {d.get('version')}"
        if ids:
            teil += f" [{ids}]"
        if fixes:
            teil += f" -> fix: {fixes}"
        return teil

    def _check_osv(self) -> list[Finding]:
        """Gepinnte Dependencies (deploy/Dockerfile) unabhaengig von pip-audit gegen OSV.dev pruefen.

        Ergaenzt `_check_dependencies` (das die INSTALLIERTE Umgebung scannt) um einen Check der DEKLARIERTEN
        Pins -- faengt eine verwundbare Pin-Version an der Quelle, ohne dass pip installiert sein muss.
        """
        pins = self._dockerfile_pins()
        if not pins:
            return [Finding("supply-chain", "ok", "Keine gepinnten Dependencies gefunden", "", "")]
        verwundbar: list[str] = []
        for name, version in pins:
            try:
                res = self.http("https://api.osv.dev/v1/query",
                                {"package": {"name": name, "ecosystem": "PyPI"}, "version": version})
            except Exception:
                res = None
            vulns = (res or {}).get("vulns") if isinstance(res, dict) else None
            if vulns:
                ids = ", ".join(str(v.get("id")) for v in vulns[:3] if v.get("id"))
                verwundbar.append(f"{name} {version}" + (f" [{ids}]" if ids else ""))
        if verwundbar:
            return [Finding("supply-chain", "hoch",
                            f"{len(verwundbar)} gepinnte Dependency(s) mit OSV-CVE",
                            "OSV.dev: " + "; ".join(verwundbar[:8]),
                            "Betroffene Pins anheben (deploy/Dockerfile; Branch+Tests).")]
        return [Finding("supply-chain", "ok",
                        f"{len(pins)} gepinnte Dependencies ohne bekannte OSV-CVEs", "", "")]

    def _dockerfile_pins(self) -> list[tuple[str, str]]:
        """Liest exakte Pins ('name==version') aus deploy/Dockerfile. Nur ==-Pins (>= wird bewusst ignoriert)."""
        df = self.root / "deploy" / "Dockerfile"
        if not df.exists():
            return []
        try:
            text = df.read_text(encoding="utf-8")
        except OSError:
            return []
        gesehen: dict[str, str] = {}
        for m in re.finditer(r'"([A-Za-z0-9._-]+)==([0-9][A-Za-z0-9.\-_]*)"', text):
            gesehen[m.group(1)] = m.group(2)   # letzter Pin je Paket gewinnt
        return sorted(gesehen.items())

    # -- Loop --

    def lauf(self, *, als_antrag: bool = False) -> dict:
        findings = self.audit()
        luecken = [f for f in findings if f.schwere != "ok"]
        hoch = [f for f in luecken if f.schwere == "hoch"]
        score = min(100, sum(_SCORE_PUNKTE.get(f.schwere, 0) for f in luecken))
        if luecken and self.notify:
            detail = "\n".join(
                f"- [{f.schwere}] {f.titel}: "
                + " | ".join(t for t in (f.detail, f.empfehlung) if t)
                for f in luecken)
            try:
                self.notify(f"Sicherheits-Audit: {len(luecken)} Befund(e)"
                            + (f", davon {len(hoch)} hoch" if hoch else "")
                            + f" (Risiko-Score {score}/100).",
                            abteilung="CISO/Security", kategorie="security", quelle="security-audit",
                            detail=detail)
            except Exception:
                pass
        antrag_id = None
        if als_antrag and luecken and self.antraege is not None:
            antrag_id = self.antraege.stellen(
                titel=f"Sicherheits-Audit: {len(luecken)} Befund(e) beheben",
                beschreibung=self._antrag_text(luecken), von="CISO/Security",
                kategorie="Sicherheit/Remediation (CEO-Tor)")
        if self.changelog and luecken:
            try:
                self.changelog("CISO/Security", f"Sicherheits-Audit: {len(luecken)} Befund(e)",
                               "regelbasierter Audit (L1/L2)", "security")
            except Exception:
                pass
        return {"ok": True, "befunde": len(luecken), "hoch": len(hoch), "score": score,
                "antrag_id": antrag_id, "findings": [f.__dict__ for f in findings]}

    # -- intern --

    def _git_tracked(self) -> list[str] | None:
        if self.run is None:
            return None
        out = self.run(["git", "-C", str(self.root), "ls-files"])
        if not out:
            return None
        return [p.strip() for p in out.splitlines() if p.strip()]

    @staticmethod
    def _sieht_geheim_aus(pfad: str) -> bool:
        p = pfad.lower()
        if p.endswith(".example") or "sample" in p or "template" in p:
            return False
        base = p.rsplit("/", 1)[-1]
        if base == ".env" or p.endswith("/.env"):
            return True
        if any(m in base for m in ("client_secret", "credentials")):
            return True
        if "token" in base and base.endswith(".json"):
            return True
        return False

    def _antrag_text(self, luecken: list[Finding]) -> str:
        zeilen = ["Sicherheits-Audit (CISO/Security) -- Befunde + Empfehlungen. Umsetzung = CEO-Tor "
                  "(Aenderungen als Branch+Tests, kein Auto-Merge; Key-Rotation manuell).", ""]
        for f in sorted(luecken, key=lambda x: SCHWEREN.index(x.schwere)):
            zeilen.append(f"[{f.schwere.upper()}] {f.titel}")
            if f.detail:
                zeilen.append(f"  Detail: {f.detail}")
            if f.empfehlung:
                zeilen.append(f"  Empfehlung: {f.empfehlung}")
            zeilen.append("")
        return "\n".join(zeilen).strip()
