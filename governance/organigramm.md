# Organigramm — Hierarchie des Agenten-Unternehmens

> **Lebendes Dokument.** Es aendert sich, sobald Abteilungen **Unter-Agenten** bekommen.
> **Quelle der Wahrheit fuer Agenten, Status und Charta-Dateien ist [`agents/REGISTRY.md`](../agents/REGISTRY.md).**
> Dieses Dokument ist die **visuelle Hierarchie-Darstellung** und verweist auf die Registry — Status- und
> Bestandsangaben werden **dort** gepflegt, nicht hier doppelt. Visuelle Map: [`organigramm.xmind`](organigramm.xmind).
> `AGENTS.md` bleibt uebergeordnet; bei Widerspruch gilt `AGENTS.md`.

---

## Hierarchie-Ebenen

```
CEO (Nils)
   │  einziger menschlicher Auftraggeber
   ▼
Head of Agents (00)
   │  Supervisor — zerlegt, delegiert, buendelt, eskaliert
   ▼
Abteilungsleiter (C-Rollen / Berater, 01–14)
   │  je Abteilung ein verantwortlicher Leit-Agent
   ▼
Unter-Agenten je Abteilung (geplant)
   │  spezialisierte Sub-Agenten, vom jeweiligen Abteilungsleiter gefuehrt
   ├─ 10 CCO → Research · Konzept/Strategie · Copywriter/Caption (je Plattform) · Video-Cutter · Reviewer
   ├─ 08 CTO → Backend · Frontend/iOS · DevOps/Infra
   └─ uebrige Abteilungen → Unter-Agenten bei Bedarf
```

- **Ebene 1 — CEO (Nils):** spricht ausschliesslich mit dem Head of Agents.
- **Ebene 2 — Head of Agents (00):** einziger Gespraechspartner des CEO; Supervisor aller Abteilungen.
- **Ebene 3 — Abteilungsleiter (01–14):** die C-Rollen bzw. der Berater; sprechen nur mit dem HoA.
- **Ebene 4 — Unter-Agenten (geplant):** **jede Abteilung kann kuenftig Unter-Agenten erhalten**
  (spezialisierte Sub-Agenten). Sie werden vom jeweiligen Abteilungsleiter gefuehrt und sprechen nicht
  direkt mit dem HoA oder CEO. Anlage neuer (Unter-)Agenten erfolgt als Charta ueber den HoA (CEO-Tor).
  Derzeit sind sie nur **skizziert (Status: geplant)** — noch keine eigenen Dateien, nicht aktiviert.
  **CCO und CTO** sind die ersten Abteilungen mit explizit geplanten Unter-Agenten (zuerst real beim CCO).

## Abteilungen und ihre (moeglichen) Unter-Agenten

Alle Unter-Agenten sind **Status: geplant** (Skizze; keine eigenen Dateien, nicht aktiviert). Details je
Abteilung stehen im Abschnitt „Unter-Agenten (geplant)" der jeweiligen Charta. Aktueller Bestand/Status der
**aktiven** Agenten: siehe [`agents/REGISTRY.md`](../agents/REGISTRY.md) (Quelle der Wahrheit).

| Abteilungsleiter | Geplante Unter-Agenten (Status: geplant) |
|------------------|-------------------------------------------|
| 00 · Head of Agents | Supervisor — keine eigene Unter-Ebene |
| 01 · Unternehmensberater | Unter-Agenten bei Bedarf |
| 02 · CAO | Unter-Agenten bei Bedarf |
| 03 · CFO | bei Bedarf — z. B. Kosten-Sammler |
| 04 · CRO | bei Bedarf — z. B. Sponsoring-Outreach |
| 05 · CISO | Unter-Agenten bei Bedarf |
| 06 · CBO | Unter-Agenten bei Bedarf |
| 07 · CPO | bei Bedarf — z. B. Feedback-Analyse |
| **08 · CTO** | **Backend, Frontend/iOS, DevOps/Infra** (explizit geplant) |
| 09 · CXO | Unter-Agenten bei Bedarf |
| **10 · CCO** | **Research, Konzept/Strategie, Copywriter/Caption (je Plattform), Video-Cutter, Reviewer** (explizit geplant; zuerst real gebaut) |
| 11 · CDO | bei Bedarf — z. B. Daten-Ingest-Agent |
| 12 · CHRO | Unter-Agenten bei Bedarf |
| 13 · CLO | Unter-Agenten bei Bedarf |
| 14 · CKO | Unter-Agenten bei Bedarf |

> Hinweis: Der **Video-Cutter-Agent** (vom CCO gesteuert) ist das erste konkret vorgesehene Unter-Agenten-
> Beispiel; **CCO** ist die Abteilung, in der Unter-Agenten zuerst real gebaut werden. Sobald ein
> Unter-Agent real existiert (Charta/Registry-Eintrag), wird er in `agents/REGISTRY.md` gefuehrt.

## Rollenverteilung gegenueber der Registry

- **`agents/REGISTRY.md`** = **textbasierte Quelle der Wahrheit**: welche Agenten existieren, ihr **Status**
  (`aktiv`/`Entwurf`) und die zugehoerige **Charta-Datei**.
- **`governance/organigramm.md`** (dieses Dokument) = **visuelle Hierarchie-Darstellung**; verweist auf die
  Registry und bildet die Ebenen/Ausbaupfade ab.
- **Keine doppelte Pflege widerspruechlicher Inhalte:** Status- und Bestandsaenderungen passieren in der
  Registry; dieses Dokument zeigt nur die Struktur und verlinkt.
