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
   │  Supervisor — zerlegt, delegiert, bündelt, eskaliert
   ▼
Abteilungsleiter (C-Rollen / Berater, 01–14)
   │  je Abteilung ein verantwortlicher Leit-Agent
   ▼
Unter-Agenten je Abteilung (optional, künftig)
      spezialisierte Sub-Agenten, vom jeweiligen Abteilungsleiter geführt
```

- **Ebene 1 — CEO (Nils):** spricht ausschliesslich mit dem Head of Agents.
- **Ebene 2 — Head of Agents (00):** einziger Gespraechspartner des CEO; Supervisor aller Abteilungen.
- **Ebene 3 — Abteilungsleiter (01–14):** die C-Rollen bzw. der Berater; sprechen nur mit dem HoA.
- **Ebene 4 — Unter-Agenten (optional):** **jede Abteilung kann kuenftig Unter-Agenten erhalten**
  (spezialisierte Sub-Agenten). Sie werden vom jeweiligen Abteilungsleiter gefuehrt und sprechen nicht
  direkt mit dem HoA oder CEO. Anlage neuer (Unter-)Agenten erfolgt als Charta ueber den HoA (CEO-Tor).

## Abteilungen und ihre (moeglichen) Unter-Agenten

Aktueller Bestand und Status: siehe [`agents/REGISTRY.md`](../agents/REGISTRY.md). Die Spalte
„Unter-Agenten" zeigt den **Ausbaupfad** — heute noch leer, sofern nicht in der Registry anders vermerkt.

| Abteilungsleiter | Beispiele kuenftiger Unter-Agenten |
|------------------|-----------------------------------|
| 00 · Head of Agents | (Supervisor — keine eigene Unter-Ebene) |
| 01 · Unternehmensberater | Markt-Research, Wettbewerbsanalyse |
| 02 · CAO | Beschaffung, Termin-/Prozess-Assistenz |
| 03 · CFO | Kosten-Tracking, Forecasting |
| 04 · CRO | Sales-Outreach, Pricing-Analyse |
| 05 · CISO | Security-Monitoring, DSGVO-Pruefung |
| 06 · CBO | Visual-Design, Markenpruefung |
| 07 · CPO | Spec-Writing, Research |
| 08 · CTO | DevOps, Integrationen, Build/Test |
| 09 · CXO | Journey-Mapping, Usability-Tests |
| 10 · CCO | **Video-Cutter-Agent**, Copywriting, Redaktion je Kanal |
| 11 · CDO | ETL/Datenpflege, Dashboarding |
| 12 · CHRO | Recruiting/Eignung neuer Agenten |
| 13 · CLO | Vertrags-Review, Lizenz-Recherche |
| 14 · CKO | Wissensaufnahme, RAG-Indexierung |

> Hinweis: Der **Video-Cutter-Agent** (vom CCO gesteuert) ist das erste konkret vorgesehene Beispiel eines
> Unter-Agenten. Sobald er als Charta/Registry-Eintrag existiert, wird er hier und in der Registry gefuehrt.

## Rollenverteilung gegenueber der Registry

- **`agents/REGISTRY.md`** = **textbasierte Quelle der Wahrheit**: welche Agenten existieren, ihr **Status**
  (`aktiv`/`Entwurf`) und die zugehoerige **Charta-Datei**.
- **`governance/organigramm.md`** (dieses Dokument) = **visuelle Hierarchie-Darstellung**; verweist auf die
  Registry und bildet die Ebenen/Ausbaupfade ab.
- **Keine doppelte Pflege widerspruechlicher Inhalte:** Status- und Bestandsaenderungen passieren in der
  Registry; dieses Dokument zeigt nur die Struktur und verlinkt.
