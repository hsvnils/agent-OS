"""Phase 25 -- Deklarative Execution-Sandbox-Policy (Blaupause fuer Phase 7/17).

Formalisiert die bisher nur als Prompt-Text (`execution_live.EXECUTION_RULES`) vorhandenen Grenzen zu einer
**maschinell pruefbaren** Policy: Datei-Zugriffe (allow-list), Egress/Netz (allow-list), Prozess-/Kommando-
Muster (deny-list) und „Credentials nur als Env". Deterministisch, dependency-frei, kein LLM.

**Format:** JSON (eine YAML-Teilmenge) -- bewusst **kein** `yaml.load` auf die Policy (das flaggt unser
eigenes Security-Gate zu Recht). Default-Policy steckt im Code; `governance/sandbox-policy.json` ueberschreibt
sie optional.

**Enforcement-Modell (Least Privilege):**
- **Datei + Netz = default-deny** (allow-list): nur explizit Erlaubtes ist erlaubt.
- **Prozess = default-allow mit deny-list**: bekannte gefaehrliche Muster (rm -rf, curl|bash, git push,
  history-rewrite, sudo, fork-bomb) werden verboten -- alles andere ist erlaubt (Kommandos sind nicht
  vollstaendig enumerierbar).

**Status:** Blaupause. Die Enforcement-Punkte greifen erst mit Phase 17 (Computer-Use) bzw. am Bash-/Datei-
Pfad der Execution-Engine; dieses Modul stellt die Policy + Pruefer bereit, aendert aber noch keinen Live-Pfad.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Default-Deny-Liste fuer Prozesse (Regex, case-insensitive). Destruktiv / Exfiltration / History-Rewrite.
_PROC_DENY_DEFAULT: tuple[str, ...] = (
    r"\brm\s+-[a-z]*(?:rf|fr)[a-z]*\b",       # rm -rf / rm -fr
    r"\bsudo\b",
    r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba)?sh\b",   # curl ... | bash
    r"\bgit\s+push\b",
    r"\bgit\s+(?:\w+\s+)*(?:rebase|filter-branch)\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r":\s*\(\s*\)\s*\{",                      # Fork-Bomb :(){ ...
    r"\bchmod\s+777\b",
)

# Default-Deny fuer Dateipfade (relativ zum Sandbox-Root). Charten/Regeln (AGENTS.md 3.3), Git-Interna, Secrets.
_FS_DENY_DEFAULT: tuple[str, ...] = (
    "agents/", "AGENTS.md", "CLAUDE.md", ".git/", ".env", "orchestrator/.env",
)


@dataclass
class Entscheidung:
    erlaubt: bool
    grund: str
    regel: str = ""


@dataclass
class SandboxPolicy:
    fs_allow: list[str] = field(default_factory=lambda: ["."])            # Praefixe (default: Sandbox-Root)
    fs_deny: list[str] = field(default_factory=lambda: list(_FS_DENY_DEFAULT))
    net_allow_hosts: list[str] = field(default_factory=list)             # leer = KEIN Egress
    proc_deny: list[str] = field(default_factory=lambda: list(_PROC_DENY_DEFAULT))
    creds_env_only: bool = True                                          # Secrets nur als Env, nie im FS

    # -- Serialisierung --

    def als_dict(self) -> dict:
        return {"fs_allow": self.fs_allow, "fs_deny": self.fs_deny,
                "net_allow_hosts": self.net_allow_hosts, "proc_deny": self.proc_deny,
                "creds_env_only": self.creds_env_only}

    # -- Enforcement --

    def pruefe_datei(self, pfad: str, *, sandbox_root: str = ".", modus: str = "write") -> Entscheidung:
        """Datei-Zugriff pruefen (default-deny). Traversal ausserhalb der Sandbox -> verweigert."""
        root = Path(sandbox_root).resolve()
        ziel = Path(pfad)
        ziel = ziel.resolve() if ziel.is_absolute() else (root / ziel).resolve()
        if ziel != root and root not in ziel.parents:
            return Entscheidung(False, "Pfad ausserhalb der Sandbox", "traversal")
        rel = "" if ziel == root else ziel.relative_to(root).as_posix()
        for muster in self.fs_deny:
            if _pfad_match(rel, muster):
                return Entscheidung(False, f"verboten durch fs_deny: {muster}", muster)
        for prefix in self.fs_allow:
            if _pfad_unter(rel, prefix):
                return Entscheidung(True, f"erlaubt durch fs_allow ({modus})", prefix)
        return Entscheidung(False, "nicht in fs_allow (default-deny)", "default-deny")

    def pruefe_netz(self, host: str) -> Entscheidung:
        """Egress-Ziel pruefen (default-deny). Wildcard '*.example.com' wird unterstuetzt."""
        h = (host or "").strip().lower()
        if not h:
            return Entscheidung(False, "kein Host angegeben", "default-deny")
        for erlaubt in self.net_allow_hosts:
            e = erlaubt.strip().lower()
            if h == e or (e.startswith("*.") and (h == e[2:] or h.endswith(e[1:]))):
                return Entscheidung(True, "Host in net_allow_hosts", e)
        return Entscheidung(False, "Egress verweigert (Host nicht erlaubt)", "default-deny")

    def pruefe_prozess(self, cmd: str) -> Entscheidung:
        """Kommando gegen die Deny-Liste pruefen (default-allow, deny-list)."""
        c = " ".join((cmd or "").split())          # Whitespace normalisieren
        for muster in self.proc_deny:
            if re.search(muster, c, re.I):
                return Entscheidung(False, f"verboten durch proc_deny: {muster}", muster)
        return Entscheidung(True, "kein Deny-Muster getroffen", "")


def _pfad_match(rel: str, muster: str) -> bool:
    """True, wenn `rel` (relativer POSIX-Pfad) vom Deny-Muster erfasst wird."""
    if muster.endswith("/"):                       # Verzeichnis-Praefix
        m = muster.rstrip("/")
        return rel == m or rel.startswith(m + "/")
    return (rel == muster or rel.startswith(muster + "/")
            or rel.endswith("/" + muster) or rel.split("/")[-1] == muster)


def _pfad_unter(rel: str, prefix: str) -> bool:
    p = prefix.rstrip("/")
    if p in ("", "."):
        return True
    return rel == p or rel.startswith(p + "/")


def lade_policy(pfad: str | Path | None = None) -> SandboxPolicy:
    """Laedt die Policy aus einer JSON-Datei (ueberschreibt die Defaults feldweise). None/fehlend -> Defaults."""
    basis = SandboxPolicy()
    if pfad is None:
        return basis
    p = Path(pfad)
    if not p.exists():
        return basis
    try:
        daten = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return basis
    if not isinstance(daten, dict):
        return basis
    for feld in ("fs_allow", "fs_deny", "net_allow_hosts", "proc_deny"):
        if isinstance(daten.get(feld), list):
            setattr(basis, feld, [str(x) for x in daten[feld]])
    if isinstance(daten.get("creds_env_only"), bool):
        basis.creds_env_only = daten["creds_env_only"]
    return basis
