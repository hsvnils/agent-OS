# Execution-Sandbox-Policy (Phase 25) — deklarativ, maschinell pruefbar

> **Lebendes Steuerungsdokument.** `AGENTS.md` bleibt kanonisch und uebergeordnet — bei Widerspruch gilt
> `AGENTS.md`. Dieses Dokument definiert die **deklarative Sicherheits-Policy** fuer handelnde Agenten
> (Execution Phase 7, Computer-Use Phase 17). Sie formalisiert die bisher nur als Prompt-Text
> (`execution_live.EXECUTION_RULES`) vorhandenen Grenzen zu einer **pruefbaren** Policy und ergaenzt das
> bestehende „Branch + Tests + CEO-Merge, non-root". Blaupause aus `NVIDIA/openshell` (deklarative YAML-Policy,
> Defense-in-Depth) — siehe `docs/entscheidungs-register.md`.

---

## 1 Warum

Regeln, die nur als Prompt-Text existieren, sind nicht erzwingbar — ein Agent kann sie ignorieren oder
missverstehen. Phase 25 macht die Grenzen **maschinell pruefbar**: ein Enforcement-Punkt kann VOR jeder
Datei-/Netz-/Prozess-Aktion fragen „ist das erlaubt?" und im Zweifel abbrechen (Least Privilege, Not-Aus).

## 2 Umsetzung

- **Policy-Engine:** `orchestrator/core/sandbox_policy.py` (`SandboxPolicy`, `lade_policy`) — deterministisch,
  **dependency-frei**, kein LLM.
- **Policy-Datei:** `governance/sandbox-policy.json` — **JSON** (eine YAML-Teilmenge). Bewusst **kein**
  `yaml.load` (das flaggt unser eigenes Security-Gate zu Recht). Die Datei ueberschreibt die Code-Defaults
  feldweise; fehlt sie, gelten die Defaults.
- **Vorab-Pruefung (Tool):** `sandbox_check(art, ziel, modus?)` — fragt eine geplante Aktion ab, **fuehrt
  nichts aus**.

## 3 Schema

| Feld              | Modell        | Bedeutung                                                          |
|-------------------|---------------|-------------------------------------------------------------------|
| `fs_allow`        | allow-list    | Erlaubte Pfad-Praefixe (relativ zum Sandbox-Root). Default `["."]`.|
| `fs_deny`         | deny (Vorrang)| Immer verbotene Pfade — schlaegt `fs_allow`.                       |
| `net_allow_hosts` | allow-list    | Erlaubte Egress-Hosts (`*.domain` moeglich). Leer = **kein Netz**.|
| `proc_deny`       | deny-list     | Verbotene Kommando-Muster (Regex).                                 |
| `creds_env_only`  | Flag          | Credentials nur als Env-Variable, nie im Sandbox-Dateisystem.     |

**Enforcement-Modell (Least Privilege):**
- **Datei + Netz = default-deny** (allow-list): nur explizit Erlaubtes ist erlaubt; `fs_deny` hat Vorrang;
  Pfad-Traversal aus der Sandbox wird immer verweigert.
- **Prozess = default-allow mit deny-list**: Kommandos sind nicht vollstaendig enumerierbar; daher werden
  nur bekannte gefaehrliche Muster verboten.

## 4 Default-Policy (sicher)

- `fs_deny`: `agents/`, `AGENTS.md`, `CLAUDE.md` (Charten/Regeln — AGENTS.md 3.3), `.git/` (History),
  `.env` / `orchestrator/.env` (Secrets).
- `net_allow_hosts`: **leer** (kein Egress, bis explizit freigegeben).
- `proc_deny`: `rm -rf`/`rm -fr`, `sudo`, `curl|wget ... | bash`, `git push`, `git rebase`/`filter-branch`,
  `git reset --hard`, `mkfs`, `dd if=`, Fork-Bomb, `chmod 777`.
- `creds_env_only`: `true`.

## 5 Geplante Enforcement-Punkte (Blaupause)

Die Policy stellt die Pruefer bereit; **live erzwungen** wird sie erst dort, wo Aktionen entstehen:
1. **Phase 17 (Computer-Use):** vor jeder Datei-/Netz-/Prozess-Aktion des Rechner-bedienenden Agenten.
2. **Execution-Engine (Phase 7):** am Bash-/Datei-Pfad des Coding-Agenten (`execution_live.real_run_agent`).

Dieses Dokument + Modul ist die **Design-Freigabe-Stufe**; die Verdrahtung in die Live-Pfade erfolgt mit
Phase 17 (daran gekoppelt). Aenderungen an der Policy-Datei sind sicherheitsrelevant und laufen ueber den
CISO (Autorisierung) / CTO (Umsetzung), Changelog-Pflicht (AGENTS.md 3.2, 5.7).
