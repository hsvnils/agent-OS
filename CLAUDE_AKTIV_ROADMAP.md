# Roadmap: Claude wieder aktiv, Gemini abloesen

- Status: in Umsetzung
- Stand: 2026-10-26
- Arbeitsbranch: `ai/claude-aktiv`
- Basiscommit: `88708b5`
- Naechster Schritt: CEO-Go fuer C3 (Gemini-Wege umstellen, dabei Fachagenten direkt ueber die API statt Kommandozeile).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-23)

LUNAs Chat und die Fachagenten laufen wieder ueber die Claude-API -- „nicht mit dem staerksten Modell fuer den Chat“ --, der
Netz-Agent ebenfalls ueber Claude; auf Gemini wird verzichtet. Budget laut CEO: 100 USD API-Guthaben im Monat (laut CEO
seit Oktober im Claude-Max-Abo enthalten -- vom Agenten nicht pruefbar, der Live-Test in C2 zeigt es).

## Ausgangslage (read-only, 2026-10-23)

- Der Anthropic-Schluessel in LUNAs `.env` (NAS und MACO470) ist ungueltig (HTTP 401, BF-18). Chat laeuft seitdem lokal bzw.
  ueber Gemini (Register „Gemini-Gratis-Tier als Standard fuer den Chat“).
- `config.toml` nennt veraltete Modelle: `claude-sonnet-5` (Chat, Fachagenten, Execution) und `claude-haiku-4-5` (Routing,
  zehnmal teurer als Haiku 5.5). Die Preistabelle `core/kosten.py` kennt Sonnet 5.5 und Haiku 5.5 nicht.
- `WEB_RESEARCH_ANTHROPIC=1` (NAS): mit gueltigem Schluessel wuerde Anthropics eigene Websuche wieder aktiv -- freies Surfen
  an `NETZ_AGENT_ROADMAP.md` vorbei.
- Kein Code sendet `temperature`/`top_p`/`top_k` (seit 21.10. von der API abgelehnt) -- geprueft.
- **Gemini wird heute ausserdem genutzt** (`docs/datenschutz-ki-nutzung.md`): Backoffice-Gegenlesen, Kennzahlen-Screenshots
  auslesen, CLO-Pruefung der Vertragsvorlagen, Videograf-Vorschlaege, Bildschirm sehen, Cutter (Video-KI/Tagging),
  Routing-Probelauf; Beleg-Foto-Auslesen (`GEMINI_API_KEY` im Bot).
- **Netz-Agent:** neuer Schluessel liegt in `netz_agent/.env` (Rechte 600). Er ist gueltig, aber **an keinen Workspace
  gebunden**: die API antwortet mit 400 „must include the anthropic-workspace-id header“. Empfehlung: Schluessel im
  Workspace „luna-netz“ (mit Monatslimit) neu anlegen und ersetzen.

## Entscheidungen (CEO, 2026-10-23)

- Chat und Fachagenten: **Claude Sonnet 5.5** (`claude-sonnet-5-5`, 2 / 10 USD je Mio. Token).
- Internes Routing und Netz-Agent: **Claude Haiku 5.5** (`claude-haiku-5-5`, 0,10 / 0,50 USD).
- **Zwei Schluessel** aus demselben Konto (LUNA, Netz-Agent), je eigener Workspace mit Monatslimit -- nicht wegen Prompt
  Injection (die haengt am gelesenen Inhalt und den Werkzeugen, nicht am Konto), sondern damit sich die Budgets nicht
  gegenseitig aufbrauchen und ein kompromittierter Netz-Container nur seinen eigenen Schluessel kostet.
- Websuche-Eskalation von Anthropic **aus**; freie Websuche nur noch ueber den Netz-Agenten.
- Gemini zunaechst als Notfall-Ersatz behalten, nach einer stabilen Woche abschalten.

## Etappe C1: Vorbereitung ohne Schluessel

- Status: umgesetzt 2026-10-26 (Modellnamen `claude-sonnet-5-5`/`claude-haiku-5-5` in `config.toml` und Code-Standardwerten, Chat-Aufwand `low`; Router: fuer immer mitdenkende Modelle `thinking: adaptive` + `drop_block` bei veraenderten Verlaeufen (Beta-Header `thinking-binding-controls-2026-08-01`) und mind. 8.000 Token; Reihenfolge Claude -> lokal -> Gemini -> OpenAI; Preistabelle inkl. 5.5-Modelle, Opus 4.8 korrigiert; Anthropic-Websuche im Code fest aus; Dienste-Register; Datenschutz-Nachtrag; Tests `test_claude_aktiv.py` mit 3 Gegenproben, echtes SDK 0.111 mit abgefangener Verbindung geprueft), Deploy offen
- Ziel / Scope / Nicht-Scope: Modellnamen in `config.toml` und Code-Standardwerten auf `claude-sonnet-5-5` / `claude-haiku-5-5`;
  Preistabelle `core/kosten.py` (Sonnet 5.5, Haiku 5.5, Opus 5.5, Fable 5.1); Reihenfolge im Modell-Router pruefen und
  festlegen (Claude zuerst, dann lokal, dann Gemini); `WEB_RESEARCH_ANTHROPIC` im Code standardmaessig aus und auf der NAS
  auf 0 (CEO); Nachtrag in `docs/datenschutz-ki-nutzung.md` (Chat-Inhalte inkl. Werkzeug-Ergebnisse gehen an Anthropic;
  Bedingungen zu Training/Aufbewahrung beim Umstieg nachlesen und eintragen); Abo-Kennzahlen bleiben ohne Chat-Werkzeug.
  Nicht-Scope: Schluessel, Abschalten von Gemini.
- Gate: Tests (Router-Reihenfolge, Kostenrechnung mit neuen Preisen, keine Websuche-Eskalation ohne Schalter), Suite und
  Doku-Check gruen.
- Verifikation: `python -c` Router mit Attrappen-Schluesseln -> erwartet: erster Anbieter Claude mit `claude-sonnet-5-5`;
  `kosten.preis("claude-haiku-5-5")` -> (0.10, 0.50).
- Dry-Run: solange der Schluessel ungueltig ist, faellt der Router wie heute auf lokal/Gemini -- Betrieb unveraendert.
- Risiko / Rueckweg: Modellname falsch -> 404 beim ersten Aufruf, Router faellt zurueck; Commit zuruecknehmen.
- Abhaengig von / Aufwand / Risiko: nichts / klein / niedrig.

## Etappe C2: Schluessel eintragen und live pruefen

- Status: verifiziert 2026-10-26 (Netz-Agent: Workspace „luna-netz“, Limit 20 USD, `claude-haiku-5-5` antwortet. LUNA: Workspace „luna“, Limit 80 USD, Schluessel HTTP 200; Chat ueber LUNA-OS mit `claude-sonnet-5-5` in 4 s, ~0,02 EUR je Antwort; CTO-Fachagent nach Neu-Erstellen der Container ueber `claude-sonnet-5-5`, ~0,06 EUR je Anfrage (Kommandozeile mit grossem System-Prompt); BF-74: `compose restart` laedt die .env nicht neu. Offen nebenbei: Schluessel in der MACO470-.env fuer Tests tauschen)
- Ziel / Scope / Nicht-Scope: CEO legt zwei workspace-gebundene Schluessel an (Workspace „luna“ und „luna-netz“, je mit
  Monatslimit) und traegt sie ein: LUNA in `orchestrator/.env` (NAS; MACO470 fuer Tests), Netz-Agent in `netz_agent/.env`
  (ersetzt den heutigen, nicht workspace-gebundenen). Agent prueft nur Status und eine echte Antwort. Danach Neustart der
  Container (CEO).
- Gate: beide Schluessel HTTP 200 (`/v1/models`, Wert nie angezeigt); eine Chat-Nachricht per Telegram wird von Claude
  beantwortet (am Empfaenger geprueft), Kostenlog zeigt `claude-sonnet-5-5` mit Betrag > 0.
- Verifikation: `curl -s -o /dev/null -w "%{http_code}" https://api.anthropic.com/v1/models ...` -> erwartet: 200 (beide);
  `finance/kosten-log.jsonl` letzter Eintrag -> erwartet: Modell `claude-sonnet-5-5`, Kosten > 0.
- Dry-Run: Status-Pruefung vor dem Neustart.
- Risiko / Rueckweg: Kein Guthaben / Limit erreicht -> Router faellt auf lokal/Gemini (C1), Meldung; Schluessel entfernen.
- Abhaengig von / Aufwand / Risiko: C1 / klein / niedrig.

## Etappe C3: Gemini-Wege umstellen

- Status: geplant
- Ziel / Scope / Nicht-Scope: **Fachagenten direkt ueber die API** (wie der Chat) statt ueber die Claude-Kommandozeile -- gemessen 2026-10-26: ~0,06 EUR je CTO-Anfrage ueber die Kommandozeile gegen ~0,02 EUR je Chat-Antwort direkt; dazu jeden Gemini-Weg aus dem Datenschutz-Check auf Claude (Haiku 5.5 fuer Auslesen/Gegenlesen,
  Sonnet 5.5 fuer Pruefungen/Vorschlaege) oder lokal umstellen: Backoffice-Gegenlesen, Kennzahlen-Screenshots, Beleg-Fotos,
  CLO-Pruefung, Videograf, Bildschirm sehen, Cutter-Video-KI/Tagging, Routing-Probelauf. Je Weg einzeln, mit Schalter.
  Nicht-Scope: neue Funktionen.
- Gate: Tests je Weg, Gegenprobe; Wachtest: kein Modul ruft Gemini ausser dem Notfall-Ersatz im Router.
- Verifikation: eine Woche Betrieb -> erwartet: Kostenlog ohne Gemini-Eintraege ausser Notfall, Datenschutz-Check aktuell.
- Dry-Run: je Weg zuerst parallel (Gemini wirkt, Claude-Ergebnis nur protokolliert), dann umschalten.
- Risiko / Rueckweg: schlechtere Ergebnisse (z. B. Video) -> Weg per Schalter zurueck.
- Abhaengig von / Aufwand / Risiko: C2 / mittel / mittel (Cutter-Video).

## Etappe C4: Gemini abschalten

- Status: geplant
- Ziel / Scope / Nicht-Scope: nach einer stabilen Woche Gemini aus dem Router nehmen, `GEMINI_API_KEY` aus den `.env`
  entfernen (CEO), Dienste-Register und Datenschutz-Check fortschreiben; Notfall-Ersatz ist dann das lokale Modell.
- Gate: Suite gruen, Wachtest; eine Woche ohne Ausfall.
- Verifikation: `grep -c GEMINI_API_KEY orchestrator/.env` (NAS) -> erwartet: 0; Chat antwortet weiter.
- Dry-Run: Gemini im Router per Schalter aus, Schluessel erst nach 3 Tagen ohne Bedarf entfernen.
- Risiko / Rueckweg: Claude faellt aus -> lokales Modell antwortet; Schluessel wieder eintragen.
- Abhaengig von / Aufwand / Risiko: C3 / klein / niedrig.

## Kosten (Schaetzung, ungemessen)

Chat ~30 Nachrichten/Tag mit Sonnet 5.5: ~20-25 USD/Monat (mit Prompt-Caching weniger); Netz-Agent ~100 Auftraege/Tag mit
Haiku 5.5: ~10 USD/Monat; Routing/Auslesen mit Haiku 5.5: wenige USD. Messung ueber `finance/kosten-log.jsonl` und die
Kostenstatistik (CFO). Neue laufende Kosten = CEO-Tor (entschieden 2026-10-23).

## Nicht-Scope

Kein Opus/Fable im Betrieb; keine Werkzeuge, die Abo-Kennzahlen an ein Modell geben; keine Websuche ausserhalb des
Netz-Agenten.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md` (Gemini-Standard revidiert),
`docs/datenschutz-ki-nutzung.md`, `docs/datenfluesse.md`, Dienste-Register, `orchestrator/config.toml`,
`docs/bekannte-fehler.md` (BF-18 schliessen), `finance/kosten-statistik.md` (CFO).

## Definition of Done

Chat, Fachagenten, Routing und Netz-Agent laufen ueber Claude (Sonnet 5.5 / Haiku 5.5) mit zwei begrenzten Schluesseln;
Gemini ist abgeschaltet; Datenschutz-Check und Kostenerfassung stimmen; freie Websuche nur ueber den Netz-Agenten.
Abschluss setzt der Agent nach CEO-Abnahme.
