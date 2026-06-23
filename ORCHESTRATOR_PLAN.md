# ORCHESTRATOR_PLAN.md — Bootstrap-Orchestrator (HoA + CTO + Berater)

> **Status: PLAN — wartet auf GATE A (CEO-Freigabe).** In diesem Lauf wird **kein Laufzeit-Code**
> geschrieben. Erst nach Freigabe dieses Plans beginnt die Implementierung.
> `AGENTS.md` bleibt kanonisch und uebergeordnet; dieser Plan ist ihr untergeordnet.

---

## 1. Zweck & Scope

Erster Schritt mit echtem Laufzeit-Verhalten: ein Orchestrator auf Basis des **Claude Agent SDK (Python)**,
der **genau drei** Agenten real verdrahtet — **Head of Agents (HoA)**, **CTO** und
**Unternehmensberater** — plus Governance-Durchsetzung, Secret-/Capability-Mechanik und eine
**kanal-agnostische** Schnittstelle mit einem **Terminal-Adapter**, ueber den der CEO mit dem HoA spricht.

**Ausdruecklich NICHT in diesem Build:** keine weiteren Agenten aktivieren; keine Live-Voice-/Telegram-
Adapter bauen (nur Architektur dafuer vorsehen); keine echten kostenpflichtigen/externen Aktionen ohne
GATE/CEO-Freigabe; keine Secrets committen.

---

## 2. Wiederverwendung (Bausteine aus GitHub)

Diese dienen als Fundament/Referenz — unsere Governance-Architektur (Charten, Request-Protokoll, CEO-Tore,
Changelog) bleibt der Rahmen; **kein fremdes Framework drueberstuelpen**.

| Quelle | Rolle in diesem Build |
|--------|------------------------|
| `anthropics/claude-agent-sdk-python` | Fundament (HoA-Hauptagent, Subagenten, Hooks, Tools). |
| `anthropics/claude-agent-sdk-demos` | Muster fuer Aufbau/Streaming/Tooldefinition. |
| `VoltAgent/awesome-claude-code-subagents` | Muster fuer Subagent-Definitionen (spaeter, zum Adaptieren). |
| `AgentOps` | Optionales, abschaltbares Kostentracking (speist spaeter den CFO). |
| `the-dev-squad`, `SelfClaude` | Referenz fuer das Supervisor-Pattern. |

> **Bindings-Hinweis:** Die exakten Klassen-/Funktionsnamen des Claude Agent SDK (z. B.
> `ClaudeSDKClient`, `ClaudeAgentOptions`, `AgentDefinition`, Hook-Typen `PreToolUse`/`PostToolUse`,
> Tool-Registrierung via `@tool` + In-Process-MCP-Server, `allowed_tools`/Permission-Modi) werden **vor dem
> Coding** gegen `anthropics/claude-agent-sdk-python` verifiziert (WebFetch), nicht aus dem Gedaechtnis
> angenommen. Der Plan beschreibt die Mechanik tool-neutral; Detailnamen folgen der Verifikation.

---

## 3. Technologie & Modelle

- **Sprache/Runtime:** Python 3.11+, virtuelle Umgebung unter `orchestrator/`.
- **Kern-Abhaengigkeit:** `claude-agent-sdk` (Agent SDK). Begleitend `anthropic` (API-SDK) nur falls noetig.
- **Modelle (konfigurierbar, Default Opus):**
  - HoA: starkes agentisches Modell, Default `claude-opus-4-8`, adaptives Thinking, `effort` konfigurierbar.
  - CTO: aus Charta (`claude-opus-4-8` + Claude Code-Stil) — Richtwert, ueberschreibbar per Config.
  - Berater: aus Charta (Reasoning-Modell) — Richtwert, ueberschreibbar.
  - Internes Routing/guenstige Schritte: optional kleineres Modell (z. B. `claude-haiku-4-5`), per Config.
- **Streaming:** durchgaengig (lange Ein-/Ausgaben), Antworten als Stream an den Adapter.
- **Konfiguration:** `orchestrator/config.toml` (Modelle, effort, Flags) + `orchestrator/.env` (Secrets).

---

## 4. Verzeichnis- und Dateistruktur (geplant)

```
orchestrator/
  __init__.py
  config.toml                 # Modelle, effort, Schalter (AgentOps an/aus, Dry-Run)
  .env                        # Secrets (NIE committen) -> via .gitignore
  .env.example                # Vorlage ohne echte Werte
  README.md                   # Start/Bedienung des Orchestrators
  core/
    charter_loader.py         # Charta -> System-Prompt (Single Source of Truth)
    hoa.py                    # HoA-Kern (kanal-agnostisch): Nachricht rein -> Antwort-Stream raus
    subagents.py              # CTO + Berater als Subagent-Definitionen aus Charten
    routing.py                # Autonomie-/Eskalations-Routing (Supervisor-Logik)
  channels/
    base.py                   # ChannelAdapter-Schnittstelle (Adapter-Pattern)
    terminal.py               # Terminal-Chat-Adapter (dieser Build)
    mock.py                   # Test-Adapter (fuer Self-Checks)
  governance/
    changelog_tool.py         # Tool/Hook: umlautfreier Changelog-Eintrag
    ceo_gate_hook.py          # PreToolUse-Hook: CEO-Tor-Kategorien blockieren -> Freigabe-Anfrage
    capability.py             # grant_capability(agent, capability) + Policy-Lesen/Schreiben
    leak_guard_hook.py        # Leck-Schutz: .env-Werte aus Ausgaben/Logs/Changelog redigieren
  observability/
    logging.py                # strukturiertes Logging aller Tool-Aufrufe + Token-/Kostenschaetzung
    agentops_optional.py      # optionale, per Schalter abschaltbare AgentOps-Anbindung
  tests/
    test_durchstich.py        # CEO -> HoA -> CTO/Berater -> EINE Antwort (Mock)
    test_kanal_abstraktion.py # Terminal- und Mock-Adapter, gleicher Kern, gleiches Ergebnis
    test_autonomie.py         # Subagent loest im Mandat ohne Eskalation
    test_eskalation.py        # Blockade -> HoA; CEO-Tor-Aktion blockiert -> Freigabe-Anfrage
    test_secret_governance.py # grant Fall A/B; .env-Wert taucht nirgends auf
    test_changelog.py         # nach Aktion umlautfreier Eintrag
  run.py                      # Einstieg: startet HoA-Kern + Terminal-Adapter

governance/
  schnittstellen.md           # NEU: kanal-agnostischer Kern + 3 Adapter (Terminal jetzt; Voice/Telegram geplant)
  zugriffs-policy.md          # NEU: Least-Privilege Capability -> erlaubte Agenten

.gitignore                    # NEU/erweitert: orchestrator/.env ausschliessen
```

Aenderungen an Bestand: `agents/REGISTRY.md` (Spalte „im Orchestrator verdrahtet"),
`governance/orchestrierung.md` (Verweis auf `schnittstellen.md`), `projekt_changelog.md` (Eintraege),
`agents/01_unternehmensberater.md` Status `Entwurf` -> `aktiv` (durch HoA, gemaess Schreibrechten).

---

## 5. Architektur

### 5.1 Kanal-agnostischer Kern (Adapter-Pattern) — Kernanforderung

Die **HoA-Logik** ist strikt von der **Ein-/Ausgabe** getrennt. Schnittstelle `ChannelAdapter` (in
`channels/base.py`):

- `send_to_core(message)` -> uebergibt Text (spaeter Audio) an den HoA-Kern.
- `receive_stream()` -> liefert die Antwort als **Stream** zurueck (Text; spaeter Audio/Stream).
- `session/context`-Verwaltung (Sitzungs-ID, Verlauf) liegt im Adapter-Vertrag, nicht in der Kernlogik.

Der HoA-Kern (`core/hoa.py`) kennt **nur** diese Schnittstelle: Nachricht rein -> Antwort-Stream raus,
voellig unabhaengig vom Kanal. So docken **Live-Voice** (Echtzeit-STT -> Kern -> TTS) und **Telegram**
(Text/Voice) spaeter **ohne Aenderung am Kern** an. In diesem Build wird **nur** `channels/terminal.py`
implementiert; `channels/mock.py` dient den Self-Checks.

### 5.2 HoA = Hauptagent (System-Prompt zur Laufzeit komponiert)

`core/hoa.py` baut einen `ClaudeSDKClient` (Agent SDK). Sein System-Prompt wird **zur Laufzeit
zusammengesetzt** aus:
1. `AGENTS.md` (kanonische Regeln),
2. `governance/orchestrierung.md` (Ablauf-Lebenszyklus, Supervisor-Pattern),
3. `agents/00_head-of-agents.md` (Charta).

`core/charter_loader.py` liest diese Dateien (UTF-8) und erzeugt deterministisch den Prompt — **Single
Source of Truth**, keine Dubletten. Reihenfolge/Trennung fest, damit Prompt-Caching stabil bleibt.

### 5.3 CTO + Berater = Subagenten (System-Prompts aus Charten generiert)

`core/subagents.py` erzeugt zwei Subagent-Definitionen **aus den Charten**:
- CTO aus `agents/08_cto.md`,
- Berater aus `agents/01_unternehmensberater.md`.

Je Charta werden generiert: Rolle/Auftrag/Grenzen -> Subagent-Prompt; empfohlenes Modell -> Subagent-Modell
(per Config ueberschreibbar); Tools & Zugaenge -> **Tool-Allowlist** des Subagenten. **Nicht** von Hand
duplizieren — immer aus der Charta ableiten.

### 5.4 Delegation & Routing (Supervisor)

`core/routing.py` setzt die Orchestrierungslogik aus `governance/orchestrierung.md` um:
- HoA delegiert ueber den Subagent-/Task-Mechanismus des SDK an CTO/Berater.
- Subagenten melden **nur an den HoA** zurueck, nie direkt an den CEO.
- **Autonomie zuerst:** Subagent loest im eigenen Mandat; Eskalation an HoA nur, wenn nicht selbst loesbar.
- **Technischer Bedarf** -> HoA leitet an CTO; **CEO-Tor** -> HoA holt Freigabe beim CEO (siehe 6).

---

## 6. Governance-Durchsetzung (Hooks/Tools)

Technische Durchsetzung der Regeln aus `AGENTS.md`:

- **Changelog-Tool/-Hook** (`governance/changelog_tool.py`): schreibt nach jeder abgeschlossenen Aktion
  einen **umlautfreien** Eintrag in `projekt_changelog.md` (Format aus `AGENTS.md` 3.2). Greift als
  PostToolUse-/Abschluss-Hook.
- **CEO-Tor-Durchsetzung** (`governance/ceo_gate_hook.py`): **PreToolUse-Hook**, der Aktionen/Tools blockt,
  die eine CEO-Tor-Kategorie beruehren (Geld/Kosten, Recht/Vertraege, Oeffentlichkeit, neue
  kostenpflichtige/externe Tools/Modelle/Zugaenge, Mandats-/Charta-Aenderungen, Loeschen von Daten), solange
  keine CEO-Freigabe vorliegt. Statt Ausfuehrung erzeugt der HoA eine **entscheidungsreife
  Freigabe-Anfrage** an den CEO. Charta-Dateien bleiben HoA-exklusiv.
- **Autonomie-Routing:** ergibt sich aus den Charten und wird durch `core/routing.py` umgesetzt (Eskalation
  nur im Bedarfsfall).

---

## 7. Secret-/Capability-Governance (bestaetigte Regeln)

- **Secrets nur in `orchestrator/.env`** (per `.gitignore` ausgeschlossen, **nie committen**). Kein Tool/
  Agent gibt je einen rohen Key aus.
- **Capability-Muster:** externe Integrationen sind **Tools**, die ihren Key intern aus `.env` lesen.
  Agenten erhalten **Faehigkeiten (Tools)**, nie den Key-Text.
- **Zugriffs-Policy** (`governance/zugriffs-policy.md`): Least-Privilege, Capability -> erlaubte Agenten.
  Owner spaeter CISO; bis dahin genehmigt der HoA Policy-Aenderungen (neue externe Zugaenge = CEO-Tor).
- **CTO-Tool `grant_capability(agent, capability)`** (`governance/capability.py`):
  - **Fall A** (vorhandene, bereits bezahlte Capability, im Budget): gewaehren (Agent in Policy aufnehmen),
    **CEO informieren** + Changelog. Autonom durch die IT auf HoA-Anforderung.
  - **Fall B** (neue Kosten / neuer externer Zugang / neuer Account): **nicht** gewaehren; CEO-Freigabe-
    Anfrage erzeugen + Changelog. Budget-Pruefung gegen `finance/budget.md`.
- **Leck-Schutz-Hook** (`governance/leak_guard_hook.py`): prueft Agenten-Ausgaben, Tool-Ergebnisse,
  Changelog und CEO-Nachrichten auf Werte aus `.env` und redigiert/blockiert sie — kein Key je im Klartext
  (auch nicht in Logs/Verlauf, auch nicht ueber spaetere Voice-/Telegram-Kanaele).

---

## 8. Beobachtbarkeit

- Strukturiertes Logging aller Tool-Aufrufe + **Token-/Kostenschaetzung** (`observability/logging.py`), in
  Datei (Default) oder spaeter Supabase — damit der CFO sie auswerten kann.
- **AgentOps-Anbindung optional** und **per Schalter abschaltbar** (`observability/agentops_optional.py`,
  Flag in `config.toml`). Standardmaessig aus, bis CEO-Freigabe fuer einen externen Dienst vorliegt
  (CEO-Tor).

---

## 9. Self-Checks (offline, ohne echte Kosten)

**Dry-Run-/Mock-Modus** (Modell-Antworten mockbar) ueber `channels/mock.py` + Config-Flag. Tests in
`orchestrator/tests/`:

1. **Durchstich:** CEO-Anweisung -> HoA zerlegt -> delegiert an CTO und/oder Berater -> buendelt -> **EINE**
   konsolidierte Antwort an den CEO.
2. **Kanal-Abstraktion:** dieselbe Anweisung laeuft ueber Terminal- **und** Mock-Adapter durch den
   **unveraenderten** HoA-Kern -> gleiches Ergebnis (beweist Andockbarkeit von Voice/Telegram).
3. **Autonomie:** ein Subagent loest eine Aufgabe im eigenen Mandat ohne Eskalation.
4. **Eskalation:** blockierte Aufgabe wird von CTO an HoA gemeldet; eine simulierte CEO-Tor-Aktion (z. B.
   „neues kostenpflichtiges Tool") wird **blockiert** und in eine CEO-Freigabe-Anfrage verwandelt.
5. **Secret-Governance:** `grant_capability` Fall A gewaehrt + informiert; Fall B blockiert + eskaliert; ein
   in `.env` gelegter Test-Secret-Wert taucht in **keiner** Ausgabe/Log/Changelog auf (Redaktion greift).
6. **Changelog:** nach jeder Aktion ein umlautfreier Eintrag.

---

## 10. Abhaengigkeiten zwischen Dateien

- `core/hoa.py` -> `core/charter_loader.py` (liest `AGENTS.md`, `governance/orchestrierung.md`,
  `agents/00_head-of-agents.md`).
- `core/subagents.py` -> `core/charter_loader.py` (liest `agents/08_cto.md`, `agents/01_*.md`).
- `core/hoa.py` -> `channels/base.py` (nur Schnittstelle; konkrete Adapter injiziert `run.py`).
- Governance-Hooks/Tools werden in `core/hoa.py` registriert (PreToolUse: CEO-Tor + Leck-Schutz;
  PostToolUse/Abschluss: Changelog; Leck-Schutz zusaetzlich auf Ausgaben).
- `governance/capability.py` -> `governance/zugriffs-policy.md` (lesen/schreiben) + `finance/budget.md`
  (Budget-Check, nur lesen).
- `observability/*` wird querschnittlich aus den Tool-Aufrufen gespeist.

---

## 11. Registry-Klarstellung

In `agents/REGISTRY.md` zwei Zustaende unterscheiden:
- **Charta aktiv** (Mandat steht) vs. **im Orchestrator verdrahtet** (laeuft real).
- Fuer diesen Build **verdrahtet:** HoA, CTO, Unternehmensberater.
- **Berater-Charta** `Status: Entwurf` -> `aktiv` setzen (durch HoA, gemaess Schreibrechten).
- Uebrige Agenten bleiben **unverdrahtet** (spaeter durch HoA + CTO (+ Berater) aufgebaut).

---

## 12. GATES

- **GATE A (jetzt):** Freigabe dieses `ORCHESTRATOR_PLAN.md`. Erst danach Implementierung.
- **GATE B:** `ANTHROPIC_API_KEY` (Betrieb des Orchestrators selbst) in `orchestrator/.env`. Danach ein
  echter **Mini-Lauf**: eine einfache CEO-Anweisung end-to-end durch HoA -> CTO/Berater -> Antwort ueber den
  Terminal-Adapter.
- Business-Keys fuer Integrationen kommen spaeter **ausschliesslich** ueber das Capability-Verfahren.

---

## 13. Annahmen & offene Punkte

- **Agent-SDK-Bindings** werden vor dem Coding gegen das offizielle Repo verifiziert (siehe 2).
- **Modell-Defaults** sind Richtwerte aus den Charten und per `config.toml` ueberschreibbar (modell-agnostisch).
- **Supabase/AgentOps** bleiben in diesem Build optional/aus (externe Dienste = CEO-Tor); Default-Logging in
  Datei.
- **Schnittstellen-Roadmap** (`governance/schnittstellen.md`) wird in der Implementierung angelegt und aus
  `governance/orchestrierung.md` referenziert: Terminal jetzt, Live-Voice (primaer) geplant, Telegram geplant.
- Phasenweises Vorgehen mit Self-Checks nach jeder Phase; an GATES anhalten.
