# governance/ — Aktiv gepflegte Steuerungs-/Governance-Dokumente

Dieser Ordner enthaelt die **lebenden, autoritativen Steuerungsdokumente** des Agenten-Unternehmens. Sie
werden **aktiv fortgeschrieben**, sobald sich Struktur oder Ablaeufe aendern.

> **Verhaeltnis zu `AGENTS.md`:** Alle Dokumente hier sind `AGENTS.md` **untergeordnet**. `AGENTS.md` bleibt
> die einzige kanonische Quelle aller Regeln — bei Widerspruch gilt `AGENTS.md`.
>
> **Abgrenzung zu `docs/`:** `docs/` enthaelt **eingefrorene Provenienz/Historie** (Briefs, Bootstrap-/
> Build-Prompts) — Dokumente, die festhalten, *wie* etwas entstanden ist. `governance/` enthaelt dagegen
> Dokumente, die den *aktuellen* Betrieb steuern und sich mit ihm veraendern.

## Inhalt

| Datei | Bedeutung |
|-------|-----------|
| `orchestrierung.md` | Kanonische Orchestrierungslogik — wie der Head of Agents Auftraege durch das Unternehmen steuert (Auftrags-Lebenszyklus, Supervisor-Pattern). |
| `orchestrierung.xmind` | Visuelle Map (XMind) zur Orchestrierungslogik. |
| `organigramm.md` | Visuelle Hierarchie (CEO → HoA → Abteilungsleiter → optionale Unter-Agenten); verweist auf `agents/REGISTRY.md` als Quelle der Wahrheit. |
| `organigramm.xmind` | Visuelle Map (XMind) des Organigramms. |
| `autonomie-stufen.md` | Entwurfsraster fuer autonome Schleifen (Loop Engineering): Autonomie-Treppe L1→L2→L3, Maker/Checker, Kosten je Schleife. Gilt fuer alle autonomen Loops. |

## Quelle der Wahrheit

- **Regeln:** `AGENTS.md` (Repo-Root).
- **Agenten/Status/Charta-Dateien:** `agents/REGISTRY.md`.
- **Ablauflogik / Hierarchie-Visualisierung:** dieser Ordner (`governance/`).
