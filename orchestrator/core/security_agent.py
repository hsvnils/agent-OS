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

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

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
                 run: Callable[[list], str] | None = None, notify=None, antraege=None, changelog=None):
        self.root = Path(repo_root)
        self.env = env or {}
        self.secrets = secrets or []
        self.run = run                 # injizierbarer Kommando-Runner (git ls-files, pip-audit) -> stdout
        self.notify = notify
        self.antraege = antraege
        self.changelog = changelog

    # -- Audit --

    def audit(self) -> list[Finding]:
        return (self._check_secret_hygiene() + self._check_hardening() + self._check_dependencies())

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

    # -- Loop --

    def lauf(self, *, als_antrag: bool = False) -> dict:
        findings = self.audit()
        luecken = [f for f in findings if f.schwere != "ok"]
        hoch = [f for f in luecken if f.schwere == "hoch"]
        if luecken and self.notify:
            detail = "\n".join(
                f"- [{f.schwere}] {f.titel}: "
                + " | ".join(t for t in (f.detail, f.empfehlung) if t)
                for f in luecken)
            try:
                self.notify(f"Sicherheits-Audit: {len(luecken)} Befund(e)"
                            + (f", davon {len(hoch)} hoch" if hoch else "") + ".",
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
        return {"ok": True, "befunde": len(luecken), "hoch": len(hoch), "antrag_id": antrag_id,
                "findings": [f.__dict__ for f in findings]}

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
