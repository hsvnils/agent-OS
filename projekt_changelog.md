# Projekt-Changelog

> **Changelog-Pflicht:** Keine Aufgabe gilt als abgeschlossen, bevor ein Eintrag hier geschrieben wurde.
> Jede Erstellung, Änderung oder Löschung von Dateien sowie jede Struktur- oder Mandatsänderung MUSS hier
> protokolliert werden — von jedem Tool und jedem Agenten. Neueste Einträge stehen **oben**.

Eintragsformat:

```
## [JJJJ-MM-TT HH:MM] — <Akteur, z. B. Claude Code / Codex / Head of Agents>
- **Was:** <kurz, was geändert wurde>
- **Warum:** <Grund/Anweisung>
- **Betroffen:** <Dateien/Agenten>
```

---

## Einträge

## [2026-06-22 15:35] — Claude Code
- **Was:** Kanonische Orchestrierungslogik als `docs/orchestrierung.md` festgehalten (Grundprinzip,
  Auftrags-Lebenszyklus, Delegations-/Ergebnisformat, Eskalation & Request-Protokoll, Kosten & Budget,
  CEO-Tore, Inter-Agenten-Zusammenarbeit, Konfliktlösung, Status & Gedächtnis, erste aktive Welle).
  Verweise ergänzt: `AGENTS.md` (Org-Prinzip + Dateiübersicht), `README.md` und `docs/README.md`. Die vom
  CEO abgelegte Visualisierung `docs/orchestrierung.xmind` aufgenommen und mitcommittet.
- **Warum:** CEO-Anweisung „Orchestrierungslogik festhalten" — verbindliche Ablaufbeschreibung dokumentieren
  und XMind-Map einbinden. Noch keine Implementierung/kein Laufzeit-Code (folgt nach Framework-Entscheidung).
- **Betroffen:** `docs/orchestrierung.md` (neu), `docs/orchestrierung.xmind` (neu, vom CEO), `AGENTS.md`,
  `README.md`, `docs/README.md`.

## [2026-06-22 11:20] — Claude Code
- **Was:** XMind-Organigramm `agents/Organigramm.xmind` angelegt (Top-Down-Org-Chart: CEO → Head of Agents →
  14 Abteilungs-Agenten, mit Status-Labels „aktiv"/„Entwurf", Kurznotizen je Rolle und Hanserautisch-Farben).
  Querverweis dazu in `agents/REGISTRY.md` ergänzt.
- **Warum:** CEO-Anweisung: Organigramm zusätzlich als XMind-Map ablegen.
- **Betroffen:** `agents/Organigramm.xmind` (neu), `agents/REGISTRY.md`.

## [2026-06-22 11:05] — Claude Code
- **Was:** Governance-Modell in zwei Schritten erweitert. **(Teil 1 — Autonomie-Prinzip:** `AGENTS.md`
  Abschnitt 5 ein übergeordnetes Autonomie-Prinzip vorangestellt (eigenständige Lösung ist Standard,
  Eskalation die Ausnahme; Request-Protokoll greift nur im Eskalationsfall, IT-Regel als Spezialfall);
  Standard-Eskalationszeile „Zuerst eigenständig … nur eskalieren, wenn nicht selbst lösbar …" in
  `agents/_TEMPLATE.md` und allen 15 Charten im Feld „Eskalation" ergänzt. **(Teil 2 — Kosten & Budget:**
  `AGENTS.md` um Abschnitt 5.9 „Kosten & Budget" ergänzt (laufende Kostenüberwachung/-statistik durch CFO,
  Kostenvoranschlag bei neuen Modellen/Diensten/Abos, CEO-Monatsbudget als einzige Quelle
  `finance/budget.md`, Budgetverwaltung durch HoA, Entscheidungslogik, CEO-Tor bleibt); `03_cfo.md` und
  `00_head-of-agents.md` im Auftrag entsprechend erweitert; `finance/budget.md` (Platzhalter-Budget +
  Änderungshistorie) und `finance/kosten-statistik.md` (monatlich, mit Historie) angelegt; Dateiübersicht in
  `AGENTS.md` um `finance/` und `docs/` ergänzt.
- **Warum:** CEO-Anweisung „Governance-Modell in zwei zusammenhängenden Schritten erweitern" — Autonomie als
  Leitprinzip verankern und eine nachvollziehbare Kosten-/Budget-Governance einführen.
- **Betroffen:** `AGENTS.md`, `agents/_TEMPLATE.md`, `agents/00_head-of-agents.md` … `agents/14_cko.md`
  (alle 15 Charten), `finance/budget.md`, `finance/kosten-statistik.md`.

## [2026-06-22 10:48] — Claude Code
- **Was:** (1) `AGENTS.md` um Abschnitt 5 „Request-/Freigabe-Protokoll" erweitert — Grundsatz, Anfrageformat,
  Entscheidungsbaum, CEO-Tor-Kategorien, Routing nach Bedarfstyp (technischer Bedarf → CTO/IT), proaktive
  Bedarfsermittlung durch die IT und Zugriffs-Governance (CISO autorisiert, CTO setzt um); Folgeabschnitte
  zu 6./7. umnummeriert. (2) Alle 14 Abteilungs-Charten mit recherchierten Verantwortlichkeiten,
  Modell-Richtwerten und der Standard-Eskalationszeile (Request-Protokoll) befüllt; HoA-Charta um Verweis
  auf das Request-Protokoll ergänzt. (3) `05_ciso.md` (Zugriffs-Autorisierung/Policy) und `08_cto.md`
  (zentrale Anlaufstelle für technischen Bedarf + proaktive Bedarfsermittlung) entsprechend angepasst.
  (4) `agents/REGISTRY.md` aktualisiert: Welle 1 (HoA, CFO, CBO, CTO, CCO) = aktiv, übrige = Entwurf.
- **Warum:** CEO-autorisierte Setup-Aufgabe „Agenten-Verantwortlichkeiten + Request-Protokoll": Charten mit
  echten C-Level-abgeleiteten Mandaten füllen und das universelle Request-/Freigabe- sowie
  Bedarfs-Routing-Protokoll verankern. Weiterhin keine Orchestrierungslogik/kein Laufzeit-Verhalten.
- **Betroffen:** `AGENTS.md`, `agents/REGISTRY.md`, `agents/00_head-of-agents.md` …
  `agents/14_cko.md` (alle 14 Abteilungs-Charten).

## [2026-06-22 10:32] — Claude Code
- **Was:** Ausgangs-Prompt nach `docs/bootstrap-prompt.md` verschoben (per `git mv`, Historie erhalten) und
  `docs/`-Ordner für Projektdokumente angelegt; `docs/README.md` mit Zweck des Ordners (Historie/Provenienz)
  ergänzt.
- **Warum:** CEO-Anweisung: Ausgangs-Prompt nicht löschen, sondern als Herkunftsnachweis dokumentieren;
  `docs/` als Ablage für Briefs, Bootstrap- und spätere Build-Prompts etablieren.
- **Betroffen:** `docs/bootstrap-prompt.md` (vormals `Claude_Code_Bootstrap_Prompt_Agenten.md`),
  `docs/README.md`.

## [2026-06-22 10:24] — Claude Code
- **Was:** Projekt initialisiert — Governance, Charta-System und 14 Agenten-Entwürfe angelegt.
- **Warum:** Bootstrap-Anweisung des CEO (Datei `Claude_Code_Bootstrap_Prompt_Agenten.md`): Fundament des
  Hanserautisch Agenten-Unternehmens errichten (Struktur + Governance + Charta-Vorlagen, noch ohne
  Agenten-Verhalten).
- **Betroffen:** `AGENTS.md`, `CLAUDE.md`, `README.md`, `projekt_changelog.md`, `agents/_TEMPLATE.md`,
  `agents/REGISTRY.md`, `agents/00_head-of-agents.md`, `agents/01_unternehmensberater.md`,
  `agents/02_cao.md`, `agents/03_cfo.md`, `agents/04_cro.md`, `agents/05_ciso.md`, `agents/06_cbo.md`,
  `agents/07_cpo.md`, `agents/08_cto.md`, `agents/09_cxo.md`, `agents/10_cco-content.md`,
  `agents/11_cdo.md`, `agents/12_chro.md`, `agents/13_clo.md`, `agents/14_cko.md`.
