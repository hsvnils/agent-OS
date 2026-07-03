# Skill-/Charta-Standard — portables Skill-Format + gepruefter Import (Phase 24)

> **Lebendes Steuerungsdokument.** `AGENTS.md` bleibt kanonisch und uebergeordnet — bei Widerspruch gilt
> `AGENTS.md`. Dieses Dokument definiert **verbindlich** das Skill-Format, auf das die Agenten-Charten
> (`agents/*.md`) gehoben werden, und die **Sicherheits-Pipeline** fuer den Import fremder Skills.
> Angelehnt an den offenen „Agent Skills"-Standard (NVIDIA/skills) — uebernommen wird **nur das Format**,
> nicht die (fuer uns irrelevanten) Inhalte. Siehe `docs/entscheidungs-register.md`.

---

## 1 Warum

Unsere Faehigkeiten (Charten, wiederkehrende Workflows) sollen **portabel, versionierbar und pruefbar** sein
— statt ad hoc in Markdown. Ein einheitliches Format macht Skills vergleichbar (Erfolgsmetriken), erlaubt
Versionierung und oeffnet — **kontrolliert** — die Tuer fuer den Import erprobter Community-Skills. Weil
importierte Skills mit Skripten rund **2x haeufiger verwundbar** sind (SkillSpector), laeuft **jeder**
Fremd-Skill zuerst durch das Security-Gate aus Phase 22.

## 2 Skill-Aufbau

Ein Skill ist ein **Ordner** mit mindestens einer `SKILL.md`:

```
mein-skill/
  SKILL.md          # Pflicht: skill-card (Frontmatter) + Instruktion (Body)
  eval/             # optional: Testset/Beispiele (Eingabe -> erwartetes Ergebnis)
  BENCHMARK.md      # optional: Erfolgsmetriken/Messungen
  scripts/          # optional: Hilfsskripte (werden vom Gate statisch geprueft, NIE ausgefuehrt)
  SIGNATURE         # optional: Signatur/Herkunftsnachweis
```

### 2.1 `SKILL.md` — skill-card + Instruktion

Die `SKILL.md` beginnt mit einem **skill-card**-Frontmatter (flaches `key: value`, zwischen zwei `---`),
gefolgt von der eigentlichen Instruktion (Markdown-Body):

```markdown
---
name: mein-skill
version: 1.0.0
beschreibung: Ein Satz, was der Skill leistet.
lizenz: intern
autor: Head of Agents
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Mein Skill
<Instruktion / Workflow in Schritten>
```

**skill-card-Felder:**

| Feld           | Pflicht | Bedeutung                                                        |
|----------------|:-------:|------------------------------------------------------------------|
| `name`         |   ja    | Slug in **kebab-case** (`[a-z0-9]` mit Bindestrich).             |
| `version`      |   ja    | **semver-artig** `MAJOR.MINOR[.PATCH]` (z. B. `1.0` / `1.0.0`).  |
| `beschreibung` |   ja    | Ein Satz Zweck.                                                  |
| `lizenz`       |   ja    | SPDX-Kuerzel oder `intern`.                                      |
| `autor`        | empf.   | Urheber/Quelle.                                                  |
| `governance`   | empf.   | `intern` \| `extern-geprueft` (Import-Herkunft).                |
| `modell`       | empf.   | Modell-Richtwert (modell-agnostisch, nur Empfehlung).           |

Die Konformitaet prueft `orchestrator/core/skill_format.py` (`validiere` / `ist_konform`) — **dependency-frei**
(bewusst **kein** `yaml.load` auf Fremd-Cards, das flaggt unser eigenes Gate zu Recht).

### 2.2 Charten als Skills

Die `agents/*.md`-Charten werden schrittweise auf dieses Format gehoben (skill-card-Kopf) und um
**Erfolgsmetriken/Deliverables** ergaenzt (Baustein b, siehe `agents/_TEMPLATE.md`). **Wichtig:** Charta-
Aenderungen nimmt **nur der Head of Agents auf ausdrueckliche CEO-Anweisung mit Diff** vor (AGENTS.md 3.3).

## 3 Import-Pipeline mit Security-Gate (Pflicht fuer Fremd-Skills)

**Jeder** externe Skill durchlaeuft vor der Uebernahme das statische Gate `orchestrator/core/skill_gate.py`
(`pruefe_skill`) — es **fuehrt den Skill NIE aus**:

1. **Instruktion (`SKILL.md`)** → Prompt-Injection-/PII-Scan (`input_guard.pruefe`, Phase 23).
2. **Python-Skripte** → AST-Scan riskanter Aufrufe (Reuse Phase 22: `os.system`, `eval`/`exec`,
   `subprocess(shell=True)`, `pickle`, `yaml.load` ohne Loader, `__import__`).
3. **Shell-Skripte** → Heuristik (`curl|bash`, `rm -rf`, `eval`, `sudo`).
4. **Format** → `skill_format.validiere` (skill-card vollstaendig/gueltig).

**Verdikt** (mit Risiko-Score 0–100 und Exit-Code fuer CI):

| Verdikt      | Exit | Bedeutung                                                      |
|--------------|:----:|----------------------------------------------------------------|
| `bestanden`  |  0   | Keine Befunde — technisch unbedenklich.                        |
| `pruefen`    |  1   | Nur `mittel`/`niedrig` (z. B. Format, `sudo`) — manuell sichten.|
| `abgelehnt`  |  2   | Mind. ein `hoch`-Fund — **Import blockiert**.                  |

Ergebnisse sind als **SARIF-2.1.0** exportierbar (`GateErgebnis.sarif`) und ueber das HoA-Tool
`skill_pruefen(pfad, sarif?)` abrufbar.

## 4 Governance / GATE

- **Fremd-Skill = CEO-Tor** (AGENTS.md 5.4): Das Gate ist die **technische Vorpruefung**, **nicht** die
  Freigabe. Ein `bestanden` bedeutet „technisch unbedenklich", nicht „uebernommen" — die Uebernahme
  entscheidet der CEO ueber den Head of Agents.
- **`abgelehnt` ist hart:** Ein Skill mit `hoch`-Fund wird nicht vorgelegt, sondern zurueckgewiesen.
- **Charta-Aenderungen:** nur Head of Agents auf CEO-Anweisung mit Diff (AGENTS.md 3.3).
- **Changelog-Pflicht** fuer jede Aufnahme/Aenderung eines Skills (AGENTS.md 3.2).
