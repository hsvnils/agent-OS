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
| **Gemini „Omni"** (Video-Verstaendnis fuer den Cutter) | 2026-07-03 | **OPT-IN-PILOT GEBAUT** (Aktivieren = CEO-Tor) | Cutter Phase 15 (`--video-ki`) |
| **NVIDIA Nemotron 3 Ultra** (550B-MoE, offene Gewichte) | 2026-07-03 | **SPAETER/OPTIONAL** (technisch machbar; kein Bedarf jetzt) | Multi-Provider-Fallback-Kandidat -- CEO-Tor |
| **CFO Token-Erfassung je Agent** (aus Repo-Report) | 2026-07-03 | **UEBERNEHMEN** (Idee, home-grown) | Finance Stufe 2.5 -- `model_router` usage -> KostenStore |
| **langfuse** (LLM-Observability, self-hosted) | 2026-07-03 | **SPAETER/OPTIONAL** (schwer f. NAS) | nur falls Trace-UI gewuenscht |
| **PySceneDetect** (Szenen-/Highlight-Erkennung) | 2026-07-03 | **UMGESETZT via ffmpeg** (Lib selbst VERWORFEN: OpenCV-Dep) | Cutter szenenbewusster B-Roll-Ausschnitt |
| **mem0** (+Supabase pgvector, Memory-Layer) | 2026-07-03 | **SPAETER** (Konflikt Phase 26: BM25 bewusst gewaehlt) | erst bei echtem Vektor-Recall-Bedarf |
| **Instagram Private-API** (instagrapi/trypeggy) | 2026-07-03 | **VERWORFEN** (ToS-/Sperr-Risiko) | offizielle Graph-API bleibt |
| **moviepy / captacity** (Video) | 2026-07-03 | **VERWORFEN** (unterbesetzt/ungewartet) | wir nutzen ffmpeg direkt |
| **awesome-mcp-servers / best-of-mcp-servers** | 2026-07-03 | **REFERENZ** (Tool-Discovery) | Import nur via Security-Gate + CEO-Tor |
| **Creator-Monetarisierung/Pricing-Benchmarks 2026** (CRO) | 2026-07-04 | **UEBERNEHMEN** (in CRO-Skills) | `skills/cro/` pricing-struktur + umsatz-diversifizierung |
| **Brand-Voice-Framework (4 Dimensionen) + Konsistenz** (CBO) | 2026-07-04 | **UEBERNEHMEN** (in CBO-Skills) | `skills/cbo/` markenstimme + markenkonformitaet-pruefen |
| **6 Datenqualitaets-Dimensionen + North-Star/Vanity** (CDO) | 2026-07-04 | **UEBERNEHMEN** (in CDO-Skills) | `skills/cdo/` datenqualitaet-pruefen + kennzahlen-definieren |
| **MBB-Beratungsframeworks** (MECE/Issue-Tree/Hypothesen/Pyramid/Porter/BCG/Ansoff/BMC) (UB) | 2026-07-04 | **TEILWEISE UEBERNEHMEN** (Prinzipien, nicht Ballast) | `skills/berater/` (3 Skills) |
| **safishamsi/graphify** (Code/Docs -> Knowledge-Graph fuer Coding-Assistenten) | 2026-07-04 | **REFERENZ / OPTIONAL** (kein Laufzeit-Bedarf; ggf. Ad-hoc-CLI) | Dev-Codebasis-Uebersicht, nicht in LUNA |
| **3D-Avatar: GLB (Ready Player Me) + TalkingHead-Ansatz** (selbst gehostet) | 2026-07-05 | **VERWORFEN (revidiert)** -- zunaechst umgesetzt, dann verworfen: RPM/Selfie-GLBs treffen das stilisierte KI-Kunstbild des CEO nicht; kein Sprachmodell (auch Fable 5 nicht) macht aus einem Bild einen gerigten 3D-Kopf | ersetzt durch 2D-Living-Portrait (Zeile unten); Three.js/GLB entfernt |
| **2D-Living-Portrait** (Kunstbild direkt + Canvas-Glow/Scanline/Augen/Mund-Bloom, kein 3D/WebGL) | 2026-07-05 | **UMGESETZT** -- bildtreu (nutzt DAS Kunstbild), gratis, kein externes Tool, kein CDN | `static/luna-avatar.js`; Bild unter `static/luna-portrait.png`; gleiche `setState/setEnergy`-API |
| **3D-Avatar: HeyGen LiveAvatar** (fotorealistischer Cloud-Streaming-Avatar) | 2026-07-05 | **VERWORFEN** | Cloud + ~$0,10/Min laufend (CEO-Tor); Optik = realer Mensch, nicht Hologramm |
| **Foto->3D-Avatar-Dienste: Avaturn / Ready Player Me** (Selfie -> GLB mit ARKit-Blendshapes/Visemes) | 2026-07-05 | **VERWORFEN** | erzeugen realistische Menschen aus einem echten Gesicht -> treffen das stilisierte KI-Kunstbild nicht; CEO will genau sein Bild |
| **DeepMotion (SayMotion / Animate 3D)** | 2026-07-05 | **VERWORFEN (falscher Zweck)** | liefert Koerper-Animation/Motion-Capture, keinen Gesichts-Avatar mit Visemes -- passt nicht zum Lip-Sync-Bedarf |
| **Bild->3D-Mesh (Meshy / Tripo) + Talking-Portrait (LivePortrait, lokal)** | 2026-07-05 | **NICHT GEWAEHLT** (Alternativen) | Meshy/Tripo: statisches Mesh ohne Gesichts-Rig (Lip-Sync fehlt); LivePortrait: gratis/bildtreu, aber Vorab-Render statt Live + Einrichtungsaufwand -- CEO waehlte 2D-Living-Portrait |

---

## Eintraege (neueste oben)

### 2026-07-04 — safishamsi/graphify (CEO-Frage: hilft uns das?)

**Was:** Python/MIT-Dev-Tool (CLI + MCP-Server + IDE-Skill), das Codebasis/Docs/Medien in einen abfragbaren
**Knowledge-Graph** verwandelt, damit **KI-Coding-Assistenten** ein Projekt semantisch verstehen (Tree-sitter-
AST + LLM-Backends + Community-Detection/Leiden; optional Neo4j/Postgres). Aktiv (v0.9.5, Juli 2026).

**Bewertung durch unsere Brille:** Zielt auf **Code-Verstaendnis fuer Coding-Assistenten** -- **nicht** auf
unser Geschaeft (Content/Reels/CRM/Social/Abteilungen). Einzige plausible Nische: unsere wachsende LUNA-
Codebasis als Architektur-Graph (Dev-Hilfe / besserer Kontext fuer Execution/Self-Dev). Aber: Claude Code
navigiert die Codebasis bereits via grep/read; das Tool ist **schwer** (Tree-sitter/uv/optional Neo4j) und
**token-kostend** (LLM-Analyse) -> gegen „dependency-arm/token-frugal/local-first"; MCP/Import waere zudem
Security-Gate + CEO-Tor.

**Entscheidung:** **REFERENZ / OPTIONAL** -- **kein Laufzeit-Einbau in LUNA**. Falls je noetig: **gelegentlich
als CLI** (`graphify extract`) fuer eine einmalige Codebasis-/Architektur-Uebersicht. Aktuell **kein Bedarf**.

**Quelle:** github.com/safishamsi/graphify (README).

### 2026-07-04 — UB-Recherche: MBB-Beratungsframeworks (CEO-Auftrag „richtig wertvoll machen")

**Kontext:** Unternehmensberater (Agent 01) soll deutlich wertvoller werden. Ist-Stand: konsultierbar (starker
Pfad Sonnet 5/high), Innovations-Pipeline (`innovation_scouting`), Self-Dev-Ideengeber, Routing -- aber ohne
feste Methodik.

**Befund (Top-Frameworks McKinsey/BCG/Bain):**
- **Problemloesen:** MECE, Issue Trees, hypothesengetrieben, 7-Schritte-Prozess. **Kommunikation:** Pyramid
  Principle (Antwort zuerst). **Strategie:** SWOT, Porter's Five Forces, BCG-Matrix, Ansoff, Business Model
  Canvas, Wertkette.

**Entscheidung:** **TEILWEISE UEBERNEHMEN -- Prinzipien, nicht Ballast** (keine Interview-Framework-Sammlung
1:1). 3 Skills gebaut: `strukturiertes-problemloesen` (MECE/Issue-Tree/Hypothesen/7-Schritte + Pyramid-Output),
`strategie-framework-toolkit` (das *richtige* Framework waehlen, 1-2 statt alle), `effizienz-prozess-review`
(Engpass-/Prozessanalyse des Agenten-Unternehmens mit Impact/Aufwand). Lokal, kein CEO-Tor; Entscheidung
bleibt CEO.

**Quellen:** StrategyU / High Bridge / Slideworks / Hacking-the-Case (MBB-Frameworks + 7-Schritte-Prozess).

### 2026-07-04 — CDO-Recherche: Datenqualitaets-Dimensionen + North-Star/Vanity (CEO-Auftrag)

**Kontext:** CDO-Ausbau -- online nach nuetzlichen Daten-/KPI-Frameworks gesucht.

**Befund:**
- **6 Datenqualitaets-Dimensionen** (Wang/Strong 1996): Genauigkeit, Vollstaendigkeit, Konsistenz,
  Aktualitaet, Gueltigkeit, Eindeutigkeit -- Standard-Raster zur Pruefung, bevor Zahlen weitergegeben werden.
- **North-Star-Metrik + actionable vs. vanity:** eine Leitmetrik (beantwortet „So what?"), wenige actionable
  KPIs (Engagement-Rate, Conversion, CAC/CLV, Umsatz/wiederkehrend), Vanity (Follower/Likes/Views) nur als
  Kontext. **Vanity-Test:** „steigt die Zahl auch, wenn's schlechter wird?" -> dann Vanity.

**Entscheidung:** **UEBERNEHMEN in CDO-Skills** (lokal): `skills/cdo/datenqualitaet-pruefen` (6-Dim-Raster
-> Ampel) und `skills/cdo/kennzahlen-definieren` (North Star + actionable, Vanity kennzeichnen). North-Star-
Wahl = CEO-Bestaetigung; CDO liefert Grundlage, keinen Beschluss; PII -> CISO/DSGVO.

**Quellen:** iceDQ / IBM / Collibra / dbt (Datenqualitaets-Dimensionen); Neal Schaffer / Amplitude / Mixpanel
(North-Star-/Vanity-Metriken).

### 2026-07-04 — CBO-Recherche: Brand-Voice-Framework + Markenkonsistenz (CEO-Auftrag)

**Kontext:** CBO-Ausbau -- online nach nuetzlichen Marken-Frameworks gesucht.

**Befund:**
- **Tonalitaet -- 4 Dimensionen** (Nielsen Norman): Humorvoll↔Ernst, Locker↔Foermlich, Respektvoll↔Frech,
  Enthusiastisch↔Sachlich -- als **Prozente** verorten (nimmt das Raten raus, konsistent ueber Kanaele).
- **Markenkonsistenz** zahlt messbar (Vertrauen; Umsatz-Uplift bis ~33% in Studien); haeufiger Fehler: alles
  gleichzeitig aendern statt schrittweise. Brand-Voice-Chart ist 2026 auch **Prompt-Grundlage** (Agenten).

**Entscheidung:** **UEBERNEHMEN in CBO-Skills** (lokal): `skills/cbo/markenstimme` (4-Dim-Verortung +
Do/Don't + Anwendung als Prompt) und `skills/cbo/markenkonformitaet-pruefen` (Review-Raster -> Ampel +
Nachbesserung). Konkrete Marken-Verortung = CEO/CBO-Bestaetigung; Veroeffentlichung = CEO-Tor.

**Quellen:** Nielsen Norman Group (Tone-Dimensionen), InfluenceFlow / Bigeye / Inkbot (Brand-Voice-Guides 2026).

### 2026-07-04 — CRO-Recherche: Creator-Monetarisierung + Pricing-Benchmarks (CEO-Auftrag)

**Kontext:** Beim CRO-Ausbau nach online Nuetzlichem fuer die Abteilung gesucht.

**Befund (Benchmarks 2026):**
- **Sponsored-Post-Preise je Tier:** Nano (<10k) ~100-500 USD; **Micro (10k-100k) ~500-5.000 USD**; Mid
  (100k-1M) ~5.000-25.000 USD je Feed-Post. Faustregel-Startwert ~10 USD/1.000 Follower, dann anpassen.
- **Preis-Treiber:** Engagement (>5% -> +40-60%), Format (Reel 1,5-3x Feed, Story guenstiger), Publikum
  (DACH/westlich +20-40%).
- **Umsatz-Mix/Trend:** Brand-Deals dominant (~69-82%), aber Verschiebung zu **owned + wiederkehrend**
  (digitale Produkte ~67% der monetarisierenden Creator, Abos/Memberships, Affiliate, UGC-Lizenzierung).
  Diversifizierung senkt Volatilitaet.

**Entscheidung:** **UEBERNEHMEN in CRO-Skills** (lokal, kein externes Tool/Kosten): Benchmarks als *Referenz*
in `skills/cro/pricing-struktur` (verbindlicher Preis bleibt CEO-Entscheidung); neuer Skill
`skills/cro/umsatz-diversifizierung` fuer den Einnahmen-Mix. Keine Fixpreise erfunden -- alles Entwurf/
Referenz, Geld/Recht = CEO-Tor.

**Quellen:** Influencer Marketing Hub, Later, Shopify, Hootsuite (Influencer-Rates 2026); Circle / Influencer
Marketing Factory (Creator-Economy-Statistiken 2026).

### 2026-07-03 — Repo-Recherche „GitHub-Bausteine fuer LUNA-OS" (CEO-Report)

**Kontext:** CEO lieferte einen Recherche-Report (24 Repos, 9 Kategorien) und fragte, was/wie/warum wir
davon uebernehmen. Bewertung durch unsere Brille: **das meiste haben wir bereits selbst gebaut** (Report ist
greenfield gedacht). Nur wenige Teile sind echt additiv.

**Bereits vorhanden -> VALIDIERT (nichts zu tun):** Orchestrierung/Supervisor (Claude Agent SDK + governance/
orchestrierung.md), Second Brain + Trajektorien (Phase 26, BM25), Voice (Pipecat), Telegram-Bot, Cutter
(ffmpeg + whisper.cpp/faster-whisper + Gemini), CIO-Advisory + Risk-Checker, Instagram via offizielle
Graph-API. LangGraph-Frameworks (langgraph-supervisor) wuerden unseren SDK-Kern neu schreiben -> **VERWORFEN**.

**Echt additiv (2 Kandidaten, prinzipien-konform):**
1. **CFO Token-/Kosten-Erfassung je Agent** (Idee, nicht das Tool). Fuellt unsere bekannte Luecke „Finance
   Stufe 2.5" (Subagenten liefern keine Tokenzahl). Umsetzung **home-grown**: `usage`-Feld der Anthropic/
   OpenAI-Antworten im `model_router` je Agent in den `KostenStore` schreiben -- dependency-frei, local.
   **langfuse** = maechtige Alternative (self-hosted Trace-UI, Kosten je Session), aber **schwer** (TS/
   ClickHouse-Docker-Stack auf der schwachen NAS) -> nur wenn wir echte Trace-UI wollen. `ccusage` misst die
   Claude-*Code*-Kosten des CEO, nicht LUNAs Laufzeit -> marginal. `agentops` = SaaS-Ausleitung -> gegen
   unser Prinzip. **Entscheidung: Idee UEBERNEHMEN (home-grown), langfuse = SPAETER/OPTIONAL.**
2. **Cutter lokal intelligenter** (Backlog „Cutter intelligenter machen"). **PySceneDetect** (BSD, Python,
   CPU) = Szenen-/Highlight-Erkennung fuer bessere Ausschnitt-/Segmentwahl; Stille-Trimmen via unser
   vorhandenes **ffmpeg silencedetect** (statt Dependency **auto-editor**). Alles lokal/gratis, passt zum
   Stil-Profil-Backlog. **Entscheidung/Umsetzung (2026-07-03): UMGESETZT via ffmpeg** (`select='gt(scene,..)'`,
   `ffmpeg_ops.szenen_zeiten`) statt der PySceneDetect-Lib -- „technisch besser fuer uns": kein OpenCV, gleiche
   Umgebung, ausreichend fuer B-Roll-Ausschnittwahl (Lib selbst VERWORFEN wegen OpenCV-Dep). Szenenbewusster
   B-Roll-Start live, Default AN, abschaltbar (`CUTTER_SZENEN=0` / `--ohne-szenen`); lokal auf Mac verifiziert.

**Bewusst ABGELEHNT / schon entschieden:**
- **mem0 (+Supabase pgvector)** — Report-Top-Pick, aber **Konflikt mit Phase 26**: wir haben Vektor-Recall
  bewusst zugunsten dependency-freiem BM25 zurueckgestellt (token-frugal, keine Ausleitung, Zero-LLM-Writes;
  MemPalace VALIDIERT unseren Ansatz). mem0 macht LLM-Writes (Token-Kosten) + Vektor-DB-/Embedding-Abhaengigkeit.
  **SPAETER** -- erst wenn Volumen waechst und semantischer Recall wirklich noetig wird (= die geparkte
  Phase-26-Vektor-Option).
- **Instagram Private-API** (instagrapi, trypeggy/instagram_dm_mcp) — **VERWORFEN** (ToS-/Sperr-Risiko; wir
  nutzen korrekt die offizielle Graph-API, wie der Report selbst empfiehlt).
- **moviepy** (unterbesetzt), **captacity** (ungewartet) — **VERWORFEN** (wir nutzen ffmpeg direkt).
- **father-bot/livekit/langgraph** etc. — **VERWORFEN** (wuerden vorhandene, integrierte Bausteine ersetzen).

**Referenz/Watchlist (kein Import):** `punkpeye/awesome-mcp-servers` + `best-of-mcp-servers` als Tool-
Discovery-Quelle; `ai-hedge-fund`/`TradingAgents` als Investment-Muster (LangGraph -> nur Ideen); `sec-edgar-mcp`
(Form-4-Insider) als moegliches spaeteres Daten-Tool fuer den Insider/CIO -- **jeder** MCP-/Fremd-Import
zuerst durch das Security-Gate (Phase 22/24) + CEO-Tor.

**Quelle:** CEO-Report `compass_artifact_...md` (Downloads), Juli 2026.

### 2026-07-03 — NVIDIA Nemotron 3 Ultra als Modell fuer LUNA (CEO-Frage)

**Kontext:** CEO fragte, ob wir NVIDIA Nemotron 3 Ultra nutzen koennen.

**Befund:**
- **Was:** 550B-Mixture-of-Experts (55B aktiv), Hybrid Mamba-2/Transformer, **1M-Kontext**, **offene Gewichte**
  (NVIDIA Open Model License, kommerzielle Nutzung erlaubt). Auf „Long-running Agents" ausgerichtet, ~300 Tok/s.
- **Verfuegbar** ueber HuggingFace, **OpenRouter**, ModelScope, **NVIDIA NIM / build.nvidia.com**, Perplexity.
  OpenRouter-Preis **$0.50 Input / $2.20 Output pro 1M**; zusaetzlich eine **kostenlose** OpenRouter-Variante.
- **Integration:** **Trivial** -- unser `model_router.py` unterstuetzt beliebige **OpenAI-kompatible** Fallbacks
  (`{name,key,base_url,model}`). build.nvidia.com und OpenRouter sind OpenAI-kompatibel -> als zusaetzlicher
  Fallback in Minuten einbindbar, KEIN Umbau. **Self-Hosting der 550B-Gewichte scheidet auf unserer Hardware
  aus** (NAS ohne GPU, Mac zu klein) -> nur der API-Weg ist realistisch.
- **Bedarf:** Wir haben bereits einen funktionierenden Multi-Provider-Fallback (Anthropic primaer + Gemini +
  OpenAI). Nemotron waere ein **zusaetzlicher** Fallback / Kosten-Experiment, **kein** Lueckenfueller.
- **Risiken:** Qualitaet fuer UNSERE Agenten unbewiesen (laut Analysten Top-US-Open-Model, aber hinter den
  geschlossenen Frontier-Modellen); **Datenschutz** der Free-Endpoints pruefen (Free-Tiers loggen/trainieren
  oft); ein weiterer Key/Provider zu verwalten.

**Entscheidung:** **SPAETER/OPTIONAL.** Technisch problemlos nutzbar (OpenAI-kompatibler Fallback via
build.nvidia.com/OpenRouter), aber **kein akuter Bedarf**. Sinnvollster Einsatz: **zusaetzlicher, guenstiger
Fallback-Provider** (nicht als Primaer-Ersatz fuer Claude). Einbindung = **CEO-Tor** (neuer Provider/Modell)
+ kurzer CFO-Blick; noch **kein** Code geaendert.

**Quellen:** developer.nvidia.com/blog (Nemotron 3 Ultra), artificialanalysis.ai (Launch), openrouter.ai/nvidia/
nemotron-3-ultra-550b-a55b (Preise + :free-Variante), vllm.ai (Day-0-Support).

### 2026-07-03 — Gemini „Omni" (Video-Verstaendnis) fuer den Cutter (CEO-Wunsch, Prio zeitnah)

**Kontext:** CEO fragte, ob Googles multimodales „Omni"-Modell den Cutter (Phase 15) verbessert (Szenen-/
Highlight-Verstaendnis, bessere Reihenfolge, „bester Ausschnitt", Untertitel).

**Befund:**
- **Kein Produkt namens „Gemini Omni".** Gemeint sind die **multimodalen Gemini-Modelle mit Video-Input**
  (Files-API: Clip hochladen, Modell verarbeitet Frames @1 fps + Audio).
- **Ist-Zustand Cutter:** nutzt `gemini-2.5-flash` **nur mit Text** (Transkript + Dateiname) fuer die
  Reihenfolge -- es **sieht die Clips nicht**. Transkription laeuft lokal (whisper.cpp). Video verlaesst den
  Mac heute NICHT (nur kurze Transkript-Schnipsel gehen an Google, Free-Tier).
- **Kosten (CFO-Voranschlag):** Video = **258 Token/s** (+ Audio ~32/s). Typischer Lauf ~3-5 Min Rohmaterial
  ~= 60-90k Input-Token. Mit **Gemini 2.5 Flash-Lite** ($0.10/1M) ~**<1 Cent/Lauf**, mit 2.5 Flash ($0.30/1M)
  ~2-3 Cent/Lauf. 30 Laeufe/Monat < 1 USD. **Kein Kostenblocker.**
- **Datenschutz (Kernpunkt):** **Free-Tier -> Daten werden fuers Training genutzt.** **Paid-Tier -> NICHT.**
  Fuer echtes Video-Verstaendnis muessten die Rohclips zu Google -> nur auf **Paid-Tier** (Billing an)
  datenschutz-vertretbar. Heute ist die Pipeline fast vollstaendig lokal.
- **Mehrwert:** echtes visuelles Highlight-/Best-Cut-/Hook-Verstaendnis (heute „blind" auf Basis des
  Transkripts). Nutzen v. a. bei **visuellem** Material (B-Roll/Action/Szenerie); bei reinem Talking-Head
  gering. Nachteil: harte Google-/Netz-Abhaengigkeit, Upload-Latenz, Datenschutz-Verschiebung.

**Entscheidung:** **OPT-IN-PILOT GEBAUT** (CEO-freigegeben 2026-07-03). `cutter/gemini_video.py` +
`--video-ki`/`CUTTER_VIDEO_KI=1` (Default AUS, Paid-Tier `gemini-2.5-flash-lite`, Fallback Text->Dateiname,
Bericht-Feld `reihenfolge`). **Aktivieren bleibt CEO-Tor** (Clips zu Google, Billing an) -- der Code ist
inert, bis der CEO das Flag setzt + einen Paid-Key hinterlegt. A/B-Vergleich gegen die Text-Reihenfolge moeglich.

**Quellen:** ai.google.dev/gemini-api/docs/pricing (258 Token/s Video; Flash-Lite $0.10 / Flash $0.30 pro 1M;
Free-Tier „used to improve products" = ja, Paid = nein).

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
