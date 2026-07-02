# Recherche- & Entscheidungs-Register

> **Zweck:** Ein dauerhaftes Gedaechtnis fuer **geprüfte externe Ideen, Tools, Repos, Modelle und Ansaetze**
> -- mit **Datum, Entscheidung und Begruendung**. Wenn der CEO spaeter erneut nach etwas fragt, wird hier
> zuerst geprueft: *Haben wir das schon bewertet? Was haben wir entschieden -- und warum?*
>
> **So wird es gepflegt:**
> - Jede substanzielle Bewertung (uebernehmen / teilweise / verworfen / spaeter) kommt als Eintrag hierher.
> - Zuerst die **Index-Tabelle** aktualisieren, dann den **Detail-Eintrag** ergaenzen (neueste oben).
> - Entscheidungs-Werte: **UEBERNEHMEN** · **TEILWEISE** (nur Teile/Muster) · **VERWORFEN** · **VALIDIERT**
>   (bestaetigt unseren Ist-Stand) · **SPAETER/OPTIONAL** · **REFERENZ** (nur als Vorbild).
> - ASCII-Konvention wie im ganzen Repo (ae/oe/ue/ss). Keine Secrets, kein Chat-Mitschnitt -- nur Sachstand.
> - Umsetzung bleibt IMMER eigener GATE/CEO-Tor; dieses Register ist Entscheidungs-Doku, keine Freigabe.

---

## Index (schnelles Nachschlagen)

| Quelle / Idee | Geprueft | Entscheidung | Ergebnis / wohin |
|---|---|---|---|
| NVIDIA **SkillSpector** (Security-Scanner fuer Agent-Skills) | 2026-07-03 | **UEBERNEHMEN** (Muster/Regeln) | Phase 22 |
| NVIDIA **Skills** -- *Format* (SKILL.md/skill-card/Benchmark) | 2026-07-03 | **TEILWEISE** | Phase 24 |
| NVIDIA **Skills** -- *Inhalt* (CUDA/Jetson/Robotik) | 2026-07-03 | **VERWORFEN** | -- (irrelevant fuer uns) |
| NVIDIA **OpenShell** (sichere Agenten-Sandbox, Rust) | 2026-07-03 | **TEILWEISE** (Blaupause) | Phase 25 |
| NVIDIA **NemoClaw** (24/7-Agenten-Referenzstack) | 2026-07-03 | **REFERENZ** | Phase 25 |
| **MemPalace** (Langzeit-Gedaechtnis, Method-of-Loci) | 2026-07-03 | **VALIDIERT** / optional | Phase 26 |
| **ruflo** (`ruvnet/ruflo`) -- *als Framework* | 2026-07-03 | **VERWORFEN** | -- (Overkill/TS) |
| **ruflo** -- *Einzelideen* (AIDefence, Trajektorien-Lernen) | 2026-07-03 | **TEILWEISE** (2 Ideen) | Phase 23 / Phase 26 |
| **agency-agents #525** („The Agency") | 2026-07-03 | **MINIMAL** (nur Metrik-Idee) | Phase 24 |
| **VoltAgent/awesome-agent-skills** (1000+ Skills) | 2026-07-03 | **SPAETER** (nur via Security-Gate) | Phase 24 |

---

## Eintraege (neueste oben)

### 2026-07-03 — Recherche „Agent-Oekosystem" (CEO-Auftrag)

**Kontext:** CEO bat um Pruefung, ob wir aus mehreren extern kursierenden Agenten-Projekten etwas 1:1 lernen
oder uebernehmen koennen. Ergebnis floss in `ROADMAP.md` (Phasen 22-26). Quellen unten.

- **NVIDIA SkillSpector — UEBERNEHMEN (Muster/Regeln).**
  *Was:* Python+LangGraph Security-Scanner fuer Agent-Skills; 68 Muster in 17 Kategorien (Prompt-Injection,
  Anti-Refusal, Data-Exfiltration, Privilege-Escalation, Supply-Chain via OSV.dev, Excessive-Agency,
  Memory-Poisoning, Rogue-Agent, AST-Checks `exec/eval/subprocess/os.system`, Taint-Tracking, YARA,
  MCP-Least-Privilege); Risiko-Score 0-100, SARIF/JSON, Exit-Code-Gate; fuehrt Skills nie aus.
  *Begruendung:* Gleicher Stack wie unser `security_agent.py` (Python, regelbasiert) -> Regeln direkt nachbaubar;
  fuellt genau die Luecken von Phase 21 (heute nur Secret-Hygiene/Hardening/pip-audit). Klarster Volltreffer.
  *Ergebnis:* **Phase 22** (HOCH). Vorbehalt: Lizenz vor Code-Copy pruefen (Regel-Nachbau unproblematisch).

- **NVIDIA Skills — TEILWEISE (Format ja, Inhalt nein).**
  *Was:* Katalog signierter Skills; Format `SKILL.md` + `skill-card` (Metadaten) + Signatur + Eval-Set +
  `BENCHMARK.md`; offener „Agent Skills"-Standard.
  *Begruendung:* Inhalte sind NVIDIA-Produkt-spezifisch (CUDA/Jetson/Robotik) -> fuer unser Business nutzlos
  (**VERWORFEN**). Das **Format/Standard** ist aber wertvoll, um unsere ad-hoc-Charten (`agents/*.md`) zu
  modularisieren, versionieren und portabel/importierbar zu machen.
  *Ergebnis:* Format -> **Phase 24**.

- **NVIDIA OpenShell + NemoClaw — TEILWEISE / REFERENZ.**
  *Was:* OpenShell = Rust-Runtime, sichere Agenten-Sandbox mit deklarativer YAML-Policy (Dateisystem/Netzwerk/
  Prozess/Inference), Credentials nur als Env; „agents propose, humans approve". NemoClaw = Referenzstack fuer
  always-on-Agenten darin.
  *Begruendung:* Wir machen die Philosophie schon (Docker non-root, Env-Secrets, Antrag->Freigabe->Build). Was
  fehlt, ist eine **formale, deklarative Policy-Schicht**. Rust + schwergewichtig -> nicht als Drop-in, nur als
  **Blaupause** fuer die Execution/Computer-Use-Sicherheit.
  *Ergebnis:* **Phase 25** (an Phase 17 gekoppelt). Voll-Adoption **VERWORFEN**.

- **MemPalace — VALIDIERT / optional.**
  *Was:* Langzeit-Gedaechtnis nach Method-of-Loci; „Closets" (komprimierte Summaries) + „Drawers" (verbatim
  Logs); ~170-Token-Wake-up; Schreiben ohne LLM (deterministisch, offline); ChromaDB+SQLite; LangGraph.
  *Begruendung:* Bestaetigt unseren Ansatz stark: `MEMORY.md`-Index ~ „Closets", Fakt-Dateien/JSONL-Stores ~
  „Drawers", Zero-LLM-Writes machen wir auch. Kein akuter Handlungsbedarf. Optionaler Zugewinn nur bei starkem
  Wachstum: **semantischer (Vektor-)Recall**.
  *Ergebnis:* **Phase 26** (NIEDRIG/optional). Vorbehalt: Provenienz/Hype -> Substanz+Lizenz pruefen, eher
  Konzepte als Tool.

- **ruflo (`ruvnet/ruflo`) — VERWORFEN als Framework, TEILWEISE einzelne Ideen.**
  *Was:* TS-Meta-Harness; 100+ Agenten, Swarm-Topologien mit Raft/Byzantine-Consensus, Foederation ueber
  Maschinen/Orgs (mTLS/ed25519), Vektor-Memory, Selbstlernen aus Trajektorien (SONA), AIDefence
  (Injection-Block+PII), GOAP-Planer.
  *Begruendung:* Foederation/Byzantine-Consensus = massiver Overkill fuer ein Ein-CEO-Unternehmen; TS-Stack
  passt nicht. Zwei uebernehmbare Konzepte: **(1) Input-Filter fuer externe Inhalte** (Injection/PII) ->
  Phase 23; **(2) Trajektorien-Lernen** -> Phase 26.
  *Ergebnis:* Framework **VERWORFEN**; zwei Ideen -> Phase 23 / Phase 26.

- **agency-agents #525 („The Agency") — MINIMAL.**
  *Was:* Sammlung persona-/rollenbasierter Spezialisten-Agenten, „deliverable-focused", mit Erfolgsmetriken.
  Kein konkreter Code im Issue.
  *Begruendung:* Wir haben schon 14 Charten. Einziger uebernehmenswerter Gedanke: **staerkerer Deliverable-/
  Ergebnis-Fokus + Erfolgsmetriken je Charta**.
  *Ergebnis:* Metrik-Idee -> **Phase 24**. Sonst nichts.

- **VoltAgent/awesome-agent-skills — SPAETER.**
  *Was:* Kuratierte Sammlung 1000+ Claude-Code-kompatibler Skills.
  *Begruendung:* Potenziell nuetzliche Generik-Skills, aber Import = Supply-Chain-Risiko (Skills mit Skripten
  2,12x haeufiger verwundbar). Erst sinnvoll, wenn das **Security-Gate (Phase 22)** + Import-Pipeline
  (Phase 24) stehen.
  *Ergebnis:* **SPAETER**, gated -> Phase 24.

**Quellen:** github.com/nvidia/skillspector · github.com/nvidia/skills · github.com/nvidia/openshell ·
github.com/NVIDIA/NemoClaw · github.com/ruvnet/ruflo · github.com/msitarzewski/agency-agents/issues/525 ·
github.com/VoltAgent/awesome-agent-skills · MemPalace (analyticsvidhya.com/blog/2026/05/mempalace-explained,
recca0120.github.io/en/2026/04/08/mempalace-ai-memory-system).
