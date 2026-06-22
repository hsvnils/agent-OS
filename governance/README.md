# governance/ — Aktiv gepflegte Steuerungs-/Governance-Dokumente

Dieser Ordner enthält die **lebenden, autoritativen Steuerungsdokumente** des Agenten-Unternehmens. Sie
werden **aktiv fortgeschrieben**, sobald sich Struktur oder Abläufe ändern.

> **Verhältnis zu `AGENTS.md`:** Alle Dokumente hier sind `AGENTS.md` **untergeordnet**. `AGENTS.md` bleibt
> die einzige kanonische Quelle aller Regeln — bei Widerspruch gilt `AGENTS.md`.
>
> **Abgrenzung zu `docs/`:** `docs/` enthält **eingefrorene Provenienz/Historie** (Briefs, Bootstrap-/
> Build-Prompts) — Dokumente, die festhalten, *wie* etwas entstanden ist. `governance/` enthält dagegen
> Dokumente, die den *aktuellen* Betrieb steuern und sich mit ihm verändern.

## Inhalt

| Datei | Bedeutung |
|-------|-----------|
| `orchestrierung.md` | Kanonische Orchestrierungslogik — wie der Head of Agents Aufträge durch das Unternehmen steuert (Auftrags-Lebenszyklus, Supervisor-Pattern). |
| `orchestrierung.xmind` | Visuelle Map (XMind) zur Orchestrierungslogik. |
| `organigramm.md` | Visuelle Hierarchie (CEO → HoA → Abteilungsleiter → optionale Unter-Agenten); verweist auf `agents/REGISTRY.md` als Quelle der Wahrheit. |
| `organigramm.xmind` | Visuelle Map (XMind) des Organigramms. |

## Quelle der Wahrheit

- **Regeln:** `AGENTS.md` (Repo-Root).
- **Agenten/Status/Charta-Dateien:** `agents/REGISTRY.md`.
- **Ablauflogik / Hierarchie-Visualisierung:** dieser Ordner (`governance/`).
