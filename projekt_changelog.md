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

## [2026-06-23 19:38] — Claude Code
- **Was:** Schritt B implementiert (GATE C freigegeben): dateibasiertes Agenten-Gedaechtnis. Neu
  `orchestrator/core/memory.py` (`Memory` mit append-only JSONL, `recall` = letzte N + stichwort-relevante
  aeltere ohne Embeddings, `render_context`, Leck-Schutz via `redact`; `MemoryRecord` mit Feldern
  ts/session_id/instruction/delegated_to/status/result_digest/eskalationen/tags). `core/hoa.py` verdrahtet:
  Recall wird vor der Delegation als „Gedaechtnis-Kontext" dem Subagenten-Auftrag vorangestellt (Tor/Routing
  nutzen den Original-Auftrag), nach dem Buendeln ein Eintrag (Status ok|mit_fehler|eskalation). `run.py`
  erzeugt den Store (Dry-Run -> `memory/log_dryrun.jsonl`, gitignored; Live -> `memory/log.jsonl`).
  `config.toml [memory]` (enabled/path/recall_limit), `.gitignore` um Dry-Run-Store ergaenzt.
  Doku: `orchestrator/memory/README.md`, `governance/gedaechtnis.md` (Policy: Abgrenzung zum Changelog,
  Isolation vom persoenlichen Claude-Code-Memory, Leck-Schutz, Retention). Sechs neue Self-Checks
  (`tests/test_memory.py`): Round-Trip, Relevanz, Leck-Schutz, HoA-Integration, Dry-Run-Trennung, Isolation.
  Gesamt **18/18 OK**. Dry-Run-Smoke bestaetigt: zweiter Auftrag sieht den Kontext des ersten; kanonischer
  Store bleibt sauber. Offline, ohne Kosten.
- **Warum:** CEO-Freigabe GATE C; Umfang schlank/dateibasiert gemaess `MEMORY_PLAN.md`. Offene Ausbaustufen
  (Abschalten des CLI-Auto-Memory in Live-Subagenten, semantische Suche, Supabase) bleiben spaeteren GATES
  vorbehalten.
- **Betroffen:** `orchestrator/core/memory.py` (neu), `orchestrator/core/hoa.py`, `orchestrator/run.py`,
  `orchestrator/config.toml`, `.gitignore`, `orchestrator/memory/README.md` (neu),
  `governance/gedaechtnis.md` (neu), `orchestrator/tests/test_memory.py` (neu).

## [2026-06-23 19:31] — Claude Code
- **Was:** `MEMORY_PLAN.md` (Plan-Dokument) fuer Schritt B angelegt: schlankes, dateibasiertes,
  git-versioniertes Agenten-Gedaechtnis (`orchestrator/memory/log.jsonl`, append-only), abgegrenzt vom
  Changelog, mit Lese-Pfad (`recall` vor Delegation) und Schreib-Pfad (`append` nach Buendeln), Leck-Schutz,
  Dry-Run-Trennung und Isolation vom persoenlichen Claude-Code-Memory (inkl. Abschalten des CLI-Auto-Memory in
  Subagenten). Sechs neue Self-Checks geplant (Ziel >= 18/18). Kein externer Dienst -> kein CEO-Tor, keine
  Kosten. GATE C = Freigabe dieses Plans; danach Offline-Implementierung. Noch KEIN Memory-Laufzeit-Code.
- **Warum:** CEO-Entscheidung: mit B (Kontext & Gedaechtnis) weitermachen, Umfang schlank/dateibasiert,
  Vorgehen Plan-erst (GATE).
- **Betroffen:** `MEMORY_PLAN.md` (neu).

## [2026-06-23 16:12] — Claude Code
- **Was:** GATE B **bestanden**: der echte Mini-Lauf laeuft nach Guthaben-Aufladung vollstaendig durch
  (CEO -> HoA -> echte Opus-Aufrufe an CTO und Berater -> eine konsolidierte Antwort; HoA-Auto-Changelog
  16:05/16:08). Vorher trat `Reached maximum number of turns (1)` auf, weil die gebundelte CLI vollen
  Projekt-/Skill-Kontext laedt und das Modell den einzigen Turn fuer Tool-Versuche verbraucht. Fix in
  `core/backends.py`: Subagenten laufen jetzt schlank -- `setting_sources=[]` (kein Projekt-CLAUDE.md/Skills),
  `mcp_servers={}` + `strict_mcp_config=True` (keine externen MCP), `max_turns` konfigurierbar
  (`config.toml [run] max_turns`, Default 4; in `run.py` durchgereicht). Senkt zugleich den Kontext-Overhead.
  Self-Checks weiterhin **12/12 OK**. `dry_run` wieder auf `true` gesetzt (sicherer Default; fuer Live-Lauf
  diese eine Zeile auf false). Ausserdem drei Changelog-Kopfzeilen (14:40, 15:06, 15:29) wiederhergestellt,
  die durch fehlerhaft formulierte vorherige Edits (Anker-Header im Ersatztext nicht erneut eingefuegt)
  verloren gegangen waren -- Format gemaess AGENTS.md 3.2 wieder vollstaendig.
- **Warum:** CEO-Freigabe fuer GATE B; Guthaben aufgeladen. Live-Pfad sollte vor dem naechsten Schritt
  (Agenten-Gedaechtnis) verifiziert und stabil sein.
- **Betroffen:** `orchestrator/core/backends.py`, `orchestrator/run.py`, `orchestrator/config.toml`,
  `projekt_changelog.md` (Kopfzeilen-Reparatur).

## [2026-06-23 16:08] — Head of Agents
- **Was:** Auftrag erfolgreich bearbeitet: Skizziere kurz, wie wir die Beobachtbarkeit des Orchestrators technisch verbessern (Logging, Infrastruktur) und welcher strategische Nutzen fuer unsere Prozesse und Effizienz daraus entsteht. Der CTO liefert die technische Sicht, der Unternehmensberater die strategische -- buendle beides zu EINER Empfehlung.
- **Warum:** CEO-Anweisung ueber Kanal-Adapter
- **Betroffen:** Subagenten: berater, cto

## [2026-06-23 16:05] — Head of Agents
- **Was:** Auftrag mit Fehler(n) bearbeitet: Skizziere kurz, wie wir die Beobachtbarkeit des Orchestrators technisch verbessern (Logging, Infrastruktur) und welcher strategische Nutzen fuer unsere Prozesse und Effizienz daraus entsteht. Der CTO liefert die technische Sicht, der Unternehmensberater die strategische -- buendle beides zu EINER Empfehlung.
- **Warum:** CEO-Anweisung ueber Kanal-Adapter
- **Betroffen:** Subagenten: berater, cto

## [2026-06-23 15:52] — Claude Code
- **Was:** Robustheit des Live-Pfads: SDK-/CLI-/API-Fehler werden nicht mehr als Traceback durchgereicht.
  Neue Ausnahme `BackendError` in `core/backends.py`; `AgentSdkBackend` faengt SDK-Ausnahmen und erzeugt eine
  umlautfreie, CEO-taugliche Meldung (`_readable_error`, mit Hinweis bei erkennbarem Guthaben-/Auth-/Modell-
  Problem -- da das SDK den konkreten API-Grund verwirft, sonst Auflistung der haeufigen Ursachen). `core/hoa.py`
  faengt `BackendError` je Delegation ab, schreibt das Ergebnis als `FEHLER: ...` in die konsolidierte Antwort,
  startet bei echten Fehlern keinen CTO-Workaround und kennzeichnet den Changelog wahrheitsgemaess
  („erfolgreich" vs. „mit Fehler(n)"). Zwei neue Self-Checks (`tests/test_backend_fehler.py`). Self-Checks
  jetzt **12/12 OK** (vorher 10/10; MockBackend-Verhalten unveraendert).
- **Warum:** Beim GATE-B-Mini-Lauf brach der Orchestrator bei „Credit balance is too low" mit Traceback ab;
  CEO-Anweisung: saubere Meldung statt Traceback. Robustheit fuer den naechsten Live-Lauf nach Guthaben-Aufladung.
- **Betroffen:** `orchestrator/core/backends.py`, `orchestrator/core/hoa.py`,
  `orchestrator/tests/test_backend_fehler.py` (neu).

## [2026-06-23 15:29] — Claude Code
- **Was:** GATE-B-Mini-Lauf vorbereitet und erstmals real versucht. `claude-agent-sdk` (0.2.107) im venv
  installiert; Claude-CLI lokalisiert (`~/.npm-global/bin/claude`, 2.1.186; das SDK nutzt jedoch seine
  mitgelieferte gebundelte CLI gleicher Version). `orchestrator/.env` aus der Vorlage angelegt und
  `ANTHROPIC_API_KEY` eingetragen (gitignored, nie committet). GitHub-Remote `origin`
  (https://github.com/hsvnils/agent-OS.git) angebunden, Token sicher in der macOS-Keychain (nicht in
  `.git/config`), `main` gepusht. Live-Lauf (dry_run voruebergehend false): (1) Erste Test-Anweisung mit dem
  Wort „Kostenschaetzung" wurde korrekt vom CEO-Tor (Kategorie geld) **vor** jeder Delegation blockiert und in
  eine Freigabe-Anfrage verwandelt -- Governance greift real, kein Modellaufruf. (2) Zweite, tor-freie
  Anweisung erreichte den echten SDK-Pfad; die Anthropic-API antwortete mit HTTP 400 „Credit balance is too
  low". Wiring (Auth via API-Key, Modell, CLI, SDK, Delegation) ist damit verifiziert; einziger Blocker ist
  das **zu niedrige Guthaben des Anthropic-API-Kontos**. `config.toml` wieder auf `dry_run = true`
  zurueckgesetzt (sicherer Default; fuer den Live-Lauf nach Guthaben-Aufladung nur diese eine Zeile auf false).
- **Warum:** CEO-Freigabe fuer GATE B und Repo-Anbindung erteilt. Beobachtung fuer CFO/Budget: jeder
  CLI-basierte Agent-Turn laedt den vollen Claude-Code-Kontext (Skills/Memory, ~10k Cache-Tokens) -> grob
  ~0,12 USD Overhead pro Aufruf; spaeter optimierbar (minimaler System-Prompt, Skills/MCP in der SDK-Session
  abschalten oder fuer Subagenten die `anthropic`-API direkt nutzen).
- **Betroffen:** `orchestrator/config.toml` (netto unveraendert), `orchestrator/.env` (neu, nicht versioniert),
  Git-Remote `origin` (neu), Keychain (Token). Kein Quellcode geaendert.

## [2026-06-23 15:06] — Claude Code
- **Was:** Git-Hygiene: `.gitattributes` neu angelegt (`* text=auto eol=lf` zur Zeilenenden-Normalisierung,
  `*.xmind binary`). `.gitignore` um macOS-`.DS_Store` (auch `**/.DS_Store`) ergaenzt; die ungetrackten
  `.DS_Store` und `orchestrator/.DS_Store` aus dem Arbeitsbaum entfernt. `git add --renormalize .` ausgefuehrt
  — alle getrackten Textdateien sind bereits LF, keine Inhaltsaenderung noetig.
- **Warum:** Wechsel von Windows auf macOS; Zeilenenden plattformneutral fixieren und OS-Cruft vom Repo
  fernhalten, bevor GATE B beginnt.
- **Betroffen:** `.gitattributes` (neu), `.gitignore`.

## [2026-06-23 14:40] — Claude Code
- **Was:** GATE-B-Vorbereitung: `AgentSdkBackend` echt implementiert, gebaut gegen die verifizierten Bindings
  des Claude Agent SDK (`query`, `ClaudeAgentOptions`, `HookMatcher`, `AssistantMessage`/`TextBlock`;
  PreToolUse-Hook mit `permissionDecision: deny` fuer CEO-Tor). Lazy import, damit die Offline-Self-Checks
  ohne SDK gruen bleiben (weiterhin 10/10 OK). `run.py` verdrahtet das Backend inkl. CEO-Tor-Hook;
  `orchestrator/README.md` um GATE-B-Voraussetzungen ergaenzt (claude-agent-sdk, Claude CLI,
  ANTHROPIC_API_KEY; Live-Lauf ist billbar).
- **Warum:** SDK-Bindings waren nach kurzer Nichtverfuegbarkeit des Klassifizierers per WebFetch verifizierbar;
  damit kann der echte Mini-Lauf am GATE B ohne geratene API-Namen erfolgen. Ausfuehrung erst nach
  CEO-Freigabe (Key + billbarer Lauf).
- **Betroffen:** `orchestrator/core/backends.py`, `orchestrator/run.py`, `orchestrator/README.md`.

## [2026-06-23 14:30] — Claude Code
- **Was:** Orchestrator Phase 2-4 (lauffaehiger, offline getesteter Kern) umgesetzt: `core/charter_loader.py`
  (Charta -> System-Prompt, Single Source of Truth), `core/subagents.py` (CTO+Berater aus Charten),
  `core/routing.py` (Delegation + CEO-Tor-Erkennung), `core/backends.py` (MockBackend jetzt; AgentSdkBackend
  als markierter Stub bis GATE B), `core/hoa.py` (kanal-agnostischer Kern: Auftrag -> delegieren -> EINE
  Antwort, mit CEO-Tor-Vorpruefung, Eskalation an CTO, Changelog, Leck-Schutz), Kanal-Adapter
  (`channels/base.py`, `terminal.py`, `mock.py`), Governance (`governance/ceo_gate_hook.py`,
  `changelog_tool.py` umlautfrei, `capability.py` Fall A/B, `leak_guard.py`), Beobachtbarkeit
  (`observability/logging.py`), Einstieg `run.py`. Sechs Self-Checks (`orchestrator/tests/`, unittest)
  **real ausgefuehrt: 10/10 OK** (Durchstich, Kanal-Abstraktion, Autonomie, Eskalation, Secret-Governance,
  Changelog). Dry-Run schreibt in separates `orchestrator/logs/changelog_dryrun.md` (gitignored), damit das
  kanonische Changelog sauber bleibt.
- **Warum:** GATE A freigegeben; Python 3.12.10 nun verfuegbar, daher ausfuehrbare Umsetzung + reale
  Self-Checks. Offline/Mock ohne Kosten; echtes Agent-SDK-Backend erst ab GATE B.
- **Betroffen:** `orchestrator/core/*.py`, `orchestrator/channels/*.py`, `orchestrator/governance/*.py`,
  `orchestrator/observability/*.py`, `orchestrator/tests/*.py`, `orchestrator/run.py`,
  `orchestrator/__init__.py` (Paketgeruest).

## [2026-06-23 10:55] — Claude Code
- **Was:** Orchestrator Phase 1 (Foundation, ohne Laufzeit-Code): Ordner `orchestrator/` mit `.env.example`,
  `config.toml` (dry_run-Default, Modelle/effort/Flags), `README.md` angelegt; `.gitignore` ergaenzt
  (schliesst `orchestrator/.env` aus). Governance-Dokumente `governance/schnittstellen.md` (kanal-agnostischer
  Kern + Adapter-Roadmap: Terminal jetzt, Live-Voice/Telegram geplant) und `governance/zugriffs-policy.md`
  (Least-Privilege, grant_capability Fall A/B) neu. `agents/REGISTRY.md` um Spalte „Orchestrator"
  (verdrahtet: HoA, CTO, Berater) erweitert; `agents/01_unternehmensberater.md` Status `Entwurf` -> `aktiv`.
  `governance/orchestrierung.md` Status-/Verweis-Hinweis aktualisiert (Bootstrap begonnen, Verweis auf
  schnittstellen.md).
- **Warum:** GATE A freigegeben; Start der phasenweisen Umsetzung. Foundation ohne Python-Laufzeit, da auf
  diesem Rechner kein Python-Interpreter installiert ist (nur Store-Platzhalter) — die ausfuehrbaren
  Python-Module + Offline-Self-Checks folgen, sobald Python verfuegbar ist (Self-Check-Pflicht).
- **Betroffen:** `.gitignore`, `orchestrator/.env.example`, `orchestrator/config.toml`,
  `orchestrator/README.md`, `governance/schnittstellen.md`, `governance/zugriffs-policy.md`,
  `agents/REGISTRY.md`, `agents/01_unternehmensberater.md`, `governance/orchestrierung.md`.

## [2026-06-23 10:30] — Claude Code
- **Was:** `ORCHESTRATOR_PLAN.md` (Plan-Dokument) fuer den Bootstrap-Orchestrator angelegt — Dreiergruppe
  Head of Agents + CTO + Unternehmensberater auf Basis des Claude Agent SDK (Python), mit kanal-agnostischem
  Kern (Adapter-Pattern, Terminal-Adapter jetzt; Live-Voice/Telegram nur architektonisch vorgesehen),
  Governance-Durchsetzung (Changelog-Hook, CEO-Tor-PreToolUse-Hook), Secret-/Capability-Mechanik
  (orchestrator/.env, grant_capability Fall A/B, Leck-Schutz-Hook, zugriffs-policy.md), Beobachtbarkeit,
  Self-Checks und GATES. Noch KEIN Laufzeit-Code.
- **Warum:** CEO-Anweisung „Bootstrap-Orchestrator": erst Plan, dann GATE A (Freigabe), erst danach
  Implementierung. Scope strikt auf die Dreiergruppe begrenzt.
- **Betroffen:** `ORCHESTRATOR_PLAN.md` (neu).

## [2026-06-23 09:45] — Claude Code
- **Was:** `governance/organigramm.xmind` passend zur erweiterten `governance/organigramm.md` neu aufgebaut.
  Vier Ebenen: CEO -> Head of Agents -> Abteilungsleiter (14 C-Rollen/Berater) -> geplante Unter-Agenten.
  CCO (Research, Konzept/Strategie, Copywriter/Caption je Plattform, Video-Cutter eingehaengt, Reviewer) und
  CTO (Backend, Frontend/iOS, DevOps/Infra) explizit als „geplant"; alle uebrigen Abteilungen mit einem
  Knoten „Unter-Agenten bei Bedarf". Status-Labels aktiv/Entwurf je Abteilungsleiter, geplant je
  Unter-Agent. Datei als gueltiger XMind-ZIP-Container (content.json/metadata.json/manifest.json) erzeugt
  und verifiziert.
- **Warum:** CEO-Anweisung: XMind-Map an die erweiterte Organigramm-Struktur angleichen. Map ist nur
  Visualisierung; `agents/REGISTRY.md` bleibt Quelle der Wahrheit.
- **Betroffen:** `governance/organigramm.xmind`.

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
