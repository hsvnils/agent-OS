# Projekt-Changelog

> **Changelog-Pflicht:** Keine Aufgabe gilt als abgeschlossen, bevor ein Eintrag hier geschrieben wurde.
> Jede Erstellung, Aenderung oder Loeschung von Dateien sowie jede Struktur- oder Mandatsaenderung MUSS hier
> protokolliert werden — von jedem Tool und jedem Agenten. Neueste Eintraege stehen **oben**.

Eintragsformat:

```
## [JJJJ-MM-TT HH:MM] — <Akteur, z. B. Claude Code / Codex / Head of Agents>
- **Was:** <kurz, was geändert wurde>
- **Warum:** <Grund/Anweisung>
- **Betroffen:** <Dateien/Agenten>
```

---

## Eintraege

## [2026-06-23 09:30] — Claude Code
- **Was:** Alle 15 Charten unter `agents/` um die Abschnitte „Aufgabenkatalog (wiederkehrende To-dos)",
  „Workflows" und „Unter-Agenten (geplant)" erweitert (hinten angehaengt, vor der Aenderungsregel-Fussnote).
  `agents/_TEMPLATE.md` um dieselben Abschnitte ergaenzt, damit kuenftige Charten die Struktur erben.
  Unter-Agenten nur als Skizze (Name + Einzeiler-Zweck + Status: geplant); wo kein Mehrwert: „vorerst keine
  Unter-Agenten noetig". `governance/organigramm.md` um die geplante Unter-Agenten-Ebene erweitert (CCO und
  CTO explizit, uebrige Abteilungen „bei Bedarf"); Diagrammblock ASCII-bereinigt.
- **Warum:** CEO-Anweisung „Charten anreichern: Aufgabenkataloge, Workflows, Unter-Agenten (Skizze)".
  Leitprinzip nicht ueberbauen — Unter-Agenten nur skizziert, kein Laufzeit-Verhalten, keine separaten
  Unter-Agenten-Dateien, keine Orchestrierungs-Implementierung.
- **Betroffen:** `agents/_TEMPLATE.md`, `agents/00_head-of-agents.md` … `agents/14_cko.md` (alle 15 Charten),
  `governance/organigramm.md`.

## [2026-06-22 16:20] — Claude Code
- **Was:** Neue Konvention eingefuehrt und umgesetzt: In .md-Dateien werden keine Umlaute und kein scharfes
  S mehr verwendet (ASCII-Transliteration ae/oe/ue/ss, gross Ae/Oe/Ue). Regel in `AGENTS.md` (Abschnitt 6
  Konventionen) festgehalten. Lesbarer Text in ALLEN 28 .md-Dateien des Repos transliteriert; Code-Bloecke,
  Inline-Code, URLs und Dateipfade blieben unveraendert. Verifikation: 0 Vorkommen von Umlauten/scharfem S
  ausserhalb von Code/Inline-Code; verbleibende 16 Zeilen mit Umlauten liegen ausschliesslich innerhalb von
  Code-Bloecken (bewusst bewahrt, z. B. Changelog-Format-Vorlage, Anfrageformat, ASCII-Diagramme).
- **Warum:** CEO-Anweisung: ASCII-only fuer Markdown, um Umlaut-/Encoding-Probleme zu vermeiden; gilt ab
  sofort auch fuer kuenftige .md-Dateien. Gilt nicht fuer Nicht-.md-Dateien.
- **Betroffen:** alle .md-Dateien des Repos (`AGENTS.md`, `CLAUDE.md`, `README.md`, `projekt_changelog.md`,
  `agents/*.md`, `governance/*.md`, `finance/*.md`, `docs/*.md`).

## [2026-06-22 15:52] — Claude Code
- **Was:** Ordner `governance/` fuer lebende, autoritative Steuerungsdokumente (AGENTS.md untergeordnet)
  angelegt. Per `git mv` verschoben: `docs/orchestrierung.md` → `governance/orchestrierung.md`,
  `docs/orchestrierung.xmind` → `governance/orchestrierung.xmind`, `agents/Organigramm.xmind` →
  `governance/organigramm.xmind` (Dateiname vereinheitlicht). Neu: `governance/organigramm.md` (visuelle
  Hierarchie CEO → HoA → Abteilungsleiter → optionale Unter-Agenten, verweist auf `agents/REGISTRY.md` als
  Quelle der Wahrheit) und `governance/README.md`. `docs/README.md` bereinigt (nur noch Provenienz/Historie).
  Verweise aktualisiert in `AGENTS.md`, `README.md` und `agents/REGISTRY.md`.
- **Warum:** CEO-Anweisung: lebende Steuerungsdokumente von der eingefrorenen Provenienz in `docs/` trennen;
  Organigramm als eigenstaendiges, erweiterbares Dokument mit Unter-Agenten-Ebene fuehren; keine doppelte
  Pflege widerspruechlicher Inhalte (Registry = Quelle der Wahrheit, Organigramm = Visualisierung).
- **Betroffen:** `governance/orchestrierung.md`, `governance/orchestrierung.xmind`,
  `governance/organigramm.md` (neu), `governance/organigramm.xmind`, `governance/README.md` (neu),
  `docs/README.md`, `AGENTS.md`, `README.md`, `agents/REGISTRY.md`.

## [2026-06-22 15:35] — Claude Code
- **Was:** Kanonische Orchestrierungslogik als `docs/orchestrierung.md` festgehalten (Grundprinzip,
  Auftrags-Lebenszyklus, Delegations-/Ergebnisformat, Eskalation & Request-Protokoll, Kosten & Budget,
  CEO-Tore, Inter-Agenten-Zusammenarbeit, Konfliktloesung, Status & Gedaechtnis, erste aktive Welle).
  Verweise ergaenzt: `AGENTS.md` (Org-Prinzip + Dateiuebersicht), `README.md` und `docs/README.md`. Die vom
  CEO abgelegte Visualisierung `docs/orchestrierung.xmind` aufgenommen und mitcommittet.
- **Warum:** CEO-Anweisung „Orchestrierungslogik festhalten" — verbindliche Ablaufbeschreibung dokumentieren
  und XMind-Map einbinden. Noch keine Implementierung/kein Laufzeit-Code (folgt nach Framework-Entscheidung).
- **Betroffen:** `docs/orchestrierung.md` (neu), `docs/orchestrierung.xmind` (neu, vom CEO), `AGENTS.md`,
  `README.md`, `docs/README.md`.

## [2026-06-22 11:20] — Claude Code
- **Was:** XMind-Organigramm `agents/Organigramm.xmind` angelegt (Top-Down-Org-Chart: CEO → Head of Agents →
  14 Abteilungs-Agenten, mit Status-Labels „aktiv"/„Entwurf", Kurznotizen je Rolle und Hanserautisch-Farben).
  Querverweis dazu in `agents/REGISTRY.md` ergaenzt.
- **Warum:** CEO-Anweisung: Organigramm zusaetzlich als XMind-Map ablegen.
- **Betroffen:** `agents/Organigramm.xmind` (neu), `agents/REGISTRY.md`.

## [2026-06-22 11:05] — Claude Code
- **Was:** Governance-Modell in zwei Schritten erweitert. **(Teil 1 — Autonomie-Prinzip:** `AGENTS.md`
  Abschnitt 5 ein uebergeordnetes Autonomie-Prinzip vorangestellt (eigenstaendige Loesung ist Standard,
  Eskalation die Ausnahme; Request-Protokoll greift nur im Eskalationsfall, IT-Regel als Spezialfall);
  Standard-Eskalationszeile „Zuerst eigenstaendig … nur eskalieren, wenn nicht selbst loesbar …" in
  `agents/_TEMPLATE.md` und allen 15 Charten im Feld „Eskalation" ergaenzt. **(Teil 2 — Kosten & Budget:**
  `AGENTS.md` um Abschnitt 5.9 „Kosten & Budget" ergaenzt (laufende Kostenueberwachung/-statistik durch CFO,
  Kostenvoranschlag bei neuen Modellen/Diensten/Abos, CEO-Monatsbudget als einzige Quelle
  `finance/budget.md`, Budgetverwaltung durch HoA, Entscheidungslogik, CEO-Tor bleibt); `03_cfo.md` und
  `00_head-of-agents.md` im Auftrag entsprechend erweitert; `finance/budget.md` (Platzhalter-Budget +
  Aenderungshistorie) und `finance/kosten-statistik.md` (monatlich, mit Historie) angelegt; Dateiuebersicht in
  `AGENTS.md` um `finance/` und `docs/` ergaenzt.
- **Warum:** CEO-Anweisung „Governance-Modell in zwei zusammenhaengenden Schritten erweitern" — Autonomie als
  Leitprinzip verankern und eine nachvollziehbare Kosten-/Budget-Governance einfuehren.
- **Betroffen:** `AGENTS.md`, `agents/_TEMPLATE.md`, `agents/00_head-of-agents.md` … `agents/14_cko.md`
  (alle 15 Charten), `finance/budget.md`, `finance/kosten-statistik.md`.

## [2026-06-22 10:48] — Claude Code
- **Was:** (1) `AGENTS.md` um Abschnitt 5 „Request-/Freigabe-Protokoll" erweitert — Grundsatz, Anfrageformat,
  Entscheidungsbaum, CEO-Tor-Kategorien, Routing nach Bedarfstyp (technischer Bedarf → CTO/IT), proaktive
  Bedarfsermittlung durch die IT und Zugriffs-Governance (CISO autorisiert, CTO setzt um); Folgeabschnitte
  zu 6./7. umnummeriert. (2) Alle 14 Abteilungs-Charten mit recherchierten Verantwortlichkeiten,
  Modell-Richtwerten und der Standard-Eskalationszeile (Request-Protokoll) befuellt; HoA-Charta um Verweis
  auf das Request-Protokoll ergaenzt. (3) `05_ciso.md` (Zugriffs-Autorisierung/Policy) und `08_cto.md`
  (zentrale Anlaufstelle fuer technischen Bedarf + proaktive Bedarfsermittlung) entsprechend angepasst.
  (4) `agents/REGISTRY.md` aktualisiert: Welle 1 (HoA, CFO, CBO, CTO, CCO) = aktiv, uebrige = Entwurf.
- **Warum:** CEO-autorisierte Setup-Aufgabe „Agenten-Verantwortlichkeiten + Request-Protokoll": Charten mit
  echten C-Level-abgeleiteten Mandaten fuellen und das universelle Request-/Freigabe- sowie
  Bedarfs-Routing-Protokoll verankern. Weiterhin keine Orchestrierungslogik/kein Laufzeit-Verhalten.
- **Betroffen:** `AGENTS.md`, `agents/REGISTRY.md`, `agents/00_head-of-agents.md` …
  `agents/14_cko.md` (alle 14 Abteilungs-Charten).

## [2026-06-22 10:32] — Claude Code
- **Was:** Ausgangs-Prompt nach `docs/bootstrap-prompt.md` verschoben (per `git mv`, Historie erhalten) und
  `docs/`-Ordner fuer Projektdokumente angelegt; `docs/README.md` mit Zweck des Ordners (Historie/Provenienz)
  ergaenzt.
- **Warum:** CEO-Anweisung: Ausgangs-Prompt nicht loeschen, sondern als Herkunftsnachweis dokumentieren;
  `docs/` als Ablage fuer Briefs, Bootstrap- und spaetere Build-Prompts etablieren.
- **Betroffen:** `docs/bootstrap-prompt.md` (vormals `Claude_Code_Bootstrap_Prompt_Agenten.md`),
  `docs/README.md`.

## [2026-06-22 10:24] — Claude Code
- **Was:** Projekt initialisiert — Governance, Charta-System und 14 Agenten-Entwuerfe angelegt.
- **Warum:** Bootstrap-Anweisung des CEO (Datei `Claude_Code_Bootstrap_Prompt_Agenten.md`): Fundament des
  Hanserautisch Agenten-Unternehmens errichten (Struktur + Governance + Charta-Vorlagen, noch ohne
  Agenten-Verhalten).
- **Betroffen:** `AGENTS.md`, `CLAUDE.md`, `README.md`, `projekt_changelog.md`, `agents/_TEMPLATE.md`,
  `agents/REGISTRY.md`, `agents/00_head-of-agents.md`, `agents/01_unternehmensberater.md`,
  `agents/02_cao.md`, `agents/03_cfo.md`, `agents/04_cro.md`, `agents/05_ciso.md`, `agents/06_cbo.md`,
  `agents/07_cpo.md`, `agents/08_cto.md`, `agents/09_cxo.md`, `agents/10_cco-content.md`,
  `agents/11_cdo.md`, `agents/12_chro.md`, `agents/13_clo.md`, `agents/14_cko.md`.
