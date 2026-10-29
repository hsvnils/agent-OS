# Roadmap: LUNA als Jarvis im Alltag (Gesamtroadmap in Paketen)

- Status: in Umsetzung
- Stand: 2026-10-28
- Arbeitsbranch: `ai/jarvis-alltag`
- Basiscommit: `d4ae65d`
- Naechster Schritt: Reihenfolge seit 2026-10-29 (CEO): A -> C -> D -> B. Paket A live, J1 abgenommen; J2c/J3/J4 Abnahme im Alltag. Paket C live (J7-J9), Abnahme im Betrieb. Paket D geplant in `RECHNER_STEUERUNG_ROADMAP.md` -- CEO prueft Plan und beantwortet D0. Paket B (J5/J6) zurueckgestellt hinter C und D.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-28)

LUNA soll den CEO im Alltag mehr unterstuetzen -- „Jarvis“-Faehigkeiten nach Vorbild von OpenJarvis, Hermes Agent und
OpenClaw (Recherche 2026-10-28, `docs/entscheidungs-register.md`), aber mit eigenen Bausteinen und ohne fremde Skills.
Die Arbeit ist in **vier Pakete** sortiert, die nacheinander abgearbeitet werden; jedes Paket bekommt sein eigenes Go.

**Jarvis ist nicht ein einzelner Punkt**, sondern die Summe der Pakete: A (hoeren und sprechen), B (verstehen, was
reinkommt), C (mitdenken und lernen), D (Haende am Rechner). Paket D ist die schon geplante Phase 17 in `ROADMAP.md`
(Umbau auf Windows, W1-W7) -- sie wird hier nur eingeordnet, nicht doppelt geplant.

## Bestand (Analyse, read-only)

| Baustein | Stand | Nachweis |
|---|---|---|
| Sprachnachrichten in Telegram | werden schon in Text umgewandelt, **ueber Deepgram (Cloud)**; Schluessel auf der NAS gesetzt (2026-10-28 geprueft, ohne Wert) | `orchestrator/channels/telegram/bot.py:313-330`, `:2541`; `docs/datenfluesse.md` Zeile `api.deepgram.com` |
| Lokale Spracherkennung | **nicht installiert** (2026-10-28 geprueft: kein whisper.cpp, kein faster-whisper auf dem MACO470; der Cutter faellt auf Deepgram zurueck) -- Annahme der ersten Fassung war falsch | `cutter/transkription.py` |
| Sprachausgabe | ElevenLabs/Cartesia fuer LUNA-OS-Voice (`/api/tts`) | `docs/datenfluesse.md` Zeile `api.elevenlabs.io` |
| Briefings | Morgen/Abend per Telegram, Lagebild | `core/briefing.py`, `core/insights.py` |
| Routen | Adresse -> Koordinaten (Nominatim) -> Fahrstrecke (OSRM), **ohne Live-Verkehr** | `core/routen.py`, `docs/datenfluesse.md` |
| CRM-Zeitleiste | letzter Kontakt je Firma ableitbar | `core/crm.py:199` (`timeline`) |
| To-dos mit Erinnerung | live seit 2026-10-27 | `TODOS_ROADMAP.md`, `core/aufgaben.py` |
| Belege per Foto | Erkennung von Belegen vorhanden | `core/eingangsbelege.py` |
| Einwilligung fuer Aufnahmen | vorhanden | `core/einwilligungen.py`, `EINWILLIGUNG_AUFNAHMEN_ROADMAP.md` |
| Gedaechtnis | Wissensbasis mit Wortsuche (keine Bedeutungssuche) | `core/brain.py` |
| Rechner bedienen | geplant, nicht begonnen | `ROADMAP.md` Phase 17 |

## Paket A -- „Sofort im Alltag“ (klein, gratis oder fast gratis)

### J1: Sprachnachrichten an LUNA

- Status: abgenommen (2026-10-29) -- CEO-Live-Test: gemischte Sprachnachricht -> To-dos mit Termin in LUNAs Kalender
  (im iPhone sichtbar, nur mit Ladeverzoegerung). Umgesetzt 2026-10-28: Sprachnachrichten und Audio-Dateien -> Deepgram -> Text -> wie getippt (To-do,
  Zeiterfassung, Fragen); LUNA antwortet direkt auf den Inhalt (seit 2026-10-29 kein Echo des erkannten Texts mehr, CEO-Wunsch); Erkennungsfehler gehen nicht mehr als Text an LUNA
  (vorher „[Transkription fehlgeschlagen …]“ als Nachricht), sondern als klare Meldung. **Abweichung:** lokale
  Spracherkennung nicht umgesetzt, weil auf dem MACO470 keine installiert ist -- Installation (faster-whisper +
  Modell-Download) ist eine eigene CEO-Entscheidung und Voraussetzung fuer J6.

- Ziel / Scope: Sprachnachricht in Telegram -> Text -> LUNA handelt wie bei getippter Nachricht (To-do anlegen, Notiz,
  Frage beantworten). Erst Probe, ob es heute schon laeuft. Dann Umstellung auf **lokale Spracherkennung (whisper auf dem
  MACO470)** statt Deepgram (Datenschutz, keine Kosten); Deepgram nur noch als Ersatz, wenn der MACO470 aus ist. LUNA
  antwortet direkt auf den Inhalt (Echo „Verstanden: …“ am 2026-10-29 auf CEO-Wunsch entfernt). Live-Test 2026-10-29: gemischte Nachricht (2 To-dos + Frage) vollstaendig umgesetzt.
- Gate: Sprachnachricht „Erinner mich morgen um 10 an die Steuer“ ergibt ein To-do mit Termin (Empfang in Telegram
  geprueft); MACO470 aus -> Ersatzweg greift oder klare Meldung; Tests mit Gegenprobe.
- Risiko: MACO470 nicht erreichbar -> Ersatzweg. Aufwand: klein.

### J2: Briefing als Sprachnachricht

- Status: umgesetzt (2026-10-28) -- Einstellung „Morgen-Briefing vorlesen“ (Standard **aus**: Kosten + Daten an
  ElevenLabs); Sprechfassung regelbasiert (`core/alltag.sprechfassung`, ohne Emojis/Kennungen/Links, max. 2.400 Zeichen),
  Stimme wie LUNA-OS (Lola), Versand als Audio in Telegram, einmal am Tag. ElevenLabs-Aufruf liegt jetzt gemeinsam in
  `core/alltag.elevenlabs_tts` (auch fuer `/api/tts`). **Seit J2b lokale Stimme statt ElevenLabs** (siehe J2b).

- Ziel / Scope: Morgen-Briefing zusaetzlich als kurze Sprachnachricht (1-2 Min.) in Telegram, schaltbar. Text wie heute,
  Stimme ueber die vorhandene Sprachausgabe (lokal bevorzugt, falls brauchbar; sonst ElevenLabs mit Kostenvoranschlag).
- Gate: Sprachnachricht kommt an (Empfang geprueft), Kosten im Kostenlog sichtbar und unter dem Richtwert.
- CEO-Tor: nur falls dafuer laufende Kosten entstehen (Kostenvoranschlag CFO). Aufwand: klein.

### J2b: Lokale Sprachausgabe (Hoerprobe, dann Umstellung)

- Anlass (CEO 2026-10-28): Stimme deutsch, natuerlich, weiblich; auf Dauer lokal, damit die Kosten bei mehr Sprache nicht
  steigen (ElevenLabs-Kontingent 10.000 Credits/Monat, Jarvis-Sprachsteuerung waere 20-100 EUR/Monat).
- Ziel / Scope: auf dem MACO470 (nur zum Testen, Betrieb unveraendert) Kokoro-Deutsch „Victoria“, Qwen3-TTS (0.6B, CPU)
  und Piper „Ramona/Kerstin“ installieren, denselben Briefing-Text mit allen plus ElevenLabs „Lola“ als MP3 erzeugen,
  Tempo je Modell messen (Sekunden Rechenzeit je Minute Sprache). CEO hoert und waehlt. Danach Umstellung: Sprachdienst
  auf dem MACO470, LUNA (NAS) schickt Text im Heimnetz, ElevenLabs nur noch Ersatz.
- Gate: Hoerproben beim CEO angekommen, Tempo dokumentiert; Umstellung erst nach Wahl des CEO (neue Verbindung NAS ->
  MACO470 = CISO-Freigabe + `docs/datenfluesse.md`).
- Recht: nur Stimmen mit freier Lizenz; Klonen einer echten Stimme nur mit schriftlicher Einwilligung (CEO-Tor).
- Aufwand: klein (Probe), mittel (Umstellung).
- Hoerprobe erzeugt (2026-10-28, MACO470, nur Prozessor; Testumgebung `~/tts-probe/`, ausserhalb des Repos; Proben unter
  `vorlagen/Hoerprobe_Stimmen/`, nicht im Git). Gleicher Text (ca. 30 s Sprache), Rechenzeit je Sekunde Sprache:

  | Probe | Modell | Rechenfaktor | live tauglich |
  |---|---|---|---|
  | 1 | Kokoro-82M Deutsch „Victoria“ (kikiri-tts, Apache 2.0) -- erste Probe ohne Sprache (Ladefehler: Gewichte mit neuer weight_norm-Benennung wurden von `KModel` stillschweigend uebersprungen), korrigiert durch Umbenennen beim Laden | 0,19 (30 s Sprache in 5,6 s) | ja |
  | 2 | Qwen3-TTS 0.6B CustomVoice „Serena“, Sprache Deutsch (Apache 2.0) | 2,85 (30 s in 87 s) | nein, nur Briefing |
  | 2b | Qwen3-TTS 1.7B VoiceDesign, Stimme per Beschreibung (deutsche Frau Anfang 30, Hochdeutsch) | 8,05 (27 s in 214 s) | nein, nur Briefing |
  | 3a/3b | Piper „Ramona“ / „Kerstin“ (low) -- vom CEO verworfen („Muell“) | 0,07-0,08 | ja |
  | 4 | ElevenLabs „Lola“ (Referenz, ca. 220 Credits) | Cloud | ja |

  CEO-Urteil 2026-10-28: Victoria (erste Probe) ohne Stimme -> korrigiert und neu geschickt; Serena „okay, aber nicht
  optimal“; Piper verworfen. Danach: Victoria gefaellt nicht; **Qwen3-Stimmdesign (2b) gut** (Tempo, Aussprache „top“),
  aber etwas quietschig/euphorisch -> vier ruhigere Beschreibungen erzeugt (je ca. 3,5 Min. Rechenzeit, Seed 7), mittlere
  Tonhoehe gemessen: 2b 293 Hz, A 294 Hz, D 276 Hz, B 255 Hz, C 255 Hz (ElevenLabs Lola 219 Hz). **CEO-Wahl
  2026-10-28: Variante C („souveraen“: tiefe, samtige Stimme, Mitte 30, sachlich-freundlich) = LUNA-Stimme.**
  Stimme festgehalten (2026-10-28): Klon aus der C-Probe mit dem Qwen3-Basismodell, neuer Text (ca. 15 s), Seed 7 --
  0.6B: 94 s Rechenzeit (Faktor 6,3), 1.7B: 132 s (Faktor 8,6); Tonhoehe 224 bzw. 232 Hz (Original C 255 Hz, anderer
  Text). Proben `5_Stimme_C_festgehalten_*.mp3`. CEO: **0.6B „klingt gut“** -> wird genommen; **1.7B vorgemerkt**
  (umschaltbar ueber `SPRACHE_MODELL`).
- Umstellung (CEO-Go 2026-10-28) -- **umgesetzt, Abnahme offen:** `core/sprachauftraege.py` (Warteschlange, MP3 nach 30
  Tagen entfernt), `/api/sprache/naechster|ergebnis` (nur Modul administration), `sprachdienst/worker.py` + Dienst
  `deploy/sprachdienst.service` (eigene Umgebung `~/luna-sprache/.venv`, Stimmordner `~/luna-sprache/stimme_c`, offline).
  Abweichung vom Plan: der Briefing-Text entsteht erst um 08:00, deshalb wird er dann in Auftrag gegeben (nicht 07:30)
  -- die Sprachnachricht kommt ca. 10-16 Min. spaeter. Echte Probe mit dem fertigen Code: 1.519 Zeichen = 101 s Sprache
  in 595 s (Faktor 5,9), offline. Nicht fertig bis 10:00 -> einmal kurzer Hinweis, der Text gilt. ElevenLabs bleibt nur
  fuer die LUNA-OS-Stimme (`/api/tts`). Gate: am ersten Morgen mit Einstellung „Morgen-Briefing vorlesen“ kommt die
  Sprachnachricht in Telegram an (Empfang durch den CEO bestaetigt).
- Plan der Umstellung (wie vorgeschlagen): Sprach-Arbeiter auf dem MACO470 nach dem Muster des
  Cutter-Workers -- er holt Sprachauftraege ueber die LUNA-OS-Schnittstelle ab (kein neuer offener Port am MACO470),
  spricht sie mit der festgehaltenen Stimme C und laedt die MP3 zurueck. Der Bot stellt den Briefing-Text schon um
  07:30 als Auftrag ein (bei ca. 2.400 Zeichen = 2,5-3 Min. Sprache rund 15-25 Min. Rechenzeit) und schickt die
  Sprachnachricht, sobald sie fertig ist. Kommt bis 08:30 nichts (MACO470 aus), bleibt es beim Text -- kein
  ElevenLabs-Ersatz fuers Briefing (Kontingent). Vorher: CISO-Freigabe der Verbindung, `docs/datenfluesse.md`, Tests. Folge: Qwen3-Design taugt nur fuer vorbereitete Texte (Briefing), nicht live -- fuer Live-Sprache ist
  weiter offen, ob eine Grafikkarte oder eine Cloud-Stimme noetig ist.

### J2c: Sprach-Ergaenzung statt alles vorlesen

- Status: umgesetzt (2026-10-29), Abnahme offen.
- Anlass (CEO 2026-10-29): Das ganze Briefing vorzulesen ist „quatsch“, wenn viele Punkte (z. B. offene Antraege)
  darin stehen. Das Text-Briefing bleibt, wie es ist; die Sprachnachricht ist eine **kurze Ergaenzung (ca. 1 Min.)**.
- Inhalt, vier Bloecke (CEO-Go 2026-10-29): (1) Begruessung mit Wochentag und Datum; (2) der Tag: Anzahl Termine,
  der naechste mit Uhrzeit und Abfahrtszeit (wie J3, nur bei Ort); (3) wichtig heute: hoechstens 3 Punkte --
  ueberfaellige/heutige eigene To-dos, dann dringende Punkte aus „Zu erledigen“ (Belegnummern weg, Firma dazu),
  der Rest als Anzahl; (4) nur Zahlen: wartende Antraege, offene Research-Tickets, offene Agenda-Aufgaben.
- Regelbasiert (`core/alltag.sprach_ergaenzung`, `sprechpunkt`), kein Sprachmodell -- nichts wird dazuerfunden;
  Kalender nicht lesbar -> „Den Kalender konnte ich heute nicht lesen“ statt „nichts im Kalender“. Faellt das
  Zusammenstellen ganz aus, wird wie bisher die Sprechfassung des Briefings gesprochen. Die Daten werden nur einmal
  je Morgen gesammelt (beim Anlegen des Auftrags).
- Gate: am naechsten Morgen kommt die Ergaenzung (statt des ganzen Briefings) in Telegram an, CEO bestaetigt Inhalt
  und Laenge. Spaeter optional: freie Formulierung durch das lokale Modell (erst nach eigenem Go).

### J3: Abfahrts-Erinnerung

- Status: umgesetzt (2026-10-28) -- Bot prueft jede Minute die heutigen Termine mit Ort (ohne Online-Termine), Fahrzeit
  ab Firmenadresse (`Routen.fahrzeit_min`, OSRM), Abfahrt = Beginn - Fahrzeit - Puffer (15 %, mind. 10 Min.), Erinnerung
  10 Min. vorher mit Google-Maps-Link, je Termin einmal; Einstellung „Abfahrts-Erinnerung“ (Standard an).

- Ziel / Scope: Bei Kalenderterminen mit Ort rechnet LUNA die Fahrzeit (vorhandene Routen) und schickt rechtzeitig
  „In 20 Min. losfahren nach …“ mit Kartenlink. **Ohne Live-Verkehr** (OSRM kennt keinen Stau) -- daher Puffer
  (Standard +15 %, mind. 10 Min.). Live-Verkehr waere ein neuer Dienst (CEO-Tor) und ist hier nicht Scope.
- Gate: Testtermin mit Adresse -> Erinnerung zur richtigen Zeit genau einmal; Termin ohne Ort -> keine Erinnerung.
- Aufwand: klein.

### J4: Kundenpflege-Hinweise

- Status: umgesetzt (2026-10-28) -- „Zu erledigen“: „Lange nichts gehört“ (Kunden mit Auftrag, letzter Vorgang aelter als
  die Einstellung „Kundenpflege-Hinweis“, Standard 60 Tage, 0 = aus), „🎂 Geburtstag“ (neues Feld am Ansprechpartner,
  heute bis in 3 Tagen), „Vor einem Jahr: Kampagne …“ (+-3 Tage); Knopf „✓ Gemeldet“ zaehlt als Kontakt.
  Tests `test_alltag.py` (10) mit 8 Gegenproben, Suite gruen.

- Ziel / Scope: „Zu erledigen“ und Briefing melden: Kunde seit X Tagen ohne Kontakt (Standard 60), Geburtstag eines
  Ansprechpartners (neues optionales Feld), Jahrestag einer Kampagne („vor einem Jahr lief …“ -> Folgeangebot?).
- Gate: Tests (Schwelle, einmal je Anlass, erledigt -> weg); Browser-Pruefung des neuen Feldes durch den CEO.
- Aufwand: klein.

## Paket B -- „Verstehen, was reinkommt“

- Status: zurueckgestellt (CEO 2026-10-29) -- kommt erst nach Paket C und D.

### J5: Post abfotografieren

- Ziel / Scope: Brief/Bescheid/Vertrag als Foto an LUNA -> Absender, Betreff, **Frist** erkennen -> To-do mit Erinnerung
  vor der Frist, Dokument in die Firmenakte bzw. unter „Verwaltung“ ablegen. Erkannte Werte immer als Vorschlag mit
  „✅ Stimmt / ✏️ Korrigieren“ (wie Kennzahlen-Screenshots).
- Gate: Probe mit 3 echten Briefen (Trefferquote dokumentiert); nichts wird ohne Bestaetigung gespeichert.
- Datenschutz: Briefe koennen sensible Daten enthalten -> Auswertung lokal bevorzugt; sonst Eintrag in
  `docs/datenschutz-ki-nutzung.md` und CEO-Entscheidung. Aufwand: mittel.

### J6: Gespraechsnotizen beim Kunden

- Ziel / Scope: Gespraech (z. B. mit dem Gespraechsleitfaden) aufnehmen -> lokal in Text -> Zusammenfassung, To-dos,
  Vorschlaege fuer Briefing-Felder der Konzept-Mappe -> Ablage in der Firmenakte. Aufnahme nur mit Einwilligung
  (vorhandener Baustein); Audio wird nach der Auswertung geloescht (Frist festlegen).
- Gate: Probe-Gespraech -> Notiz und To-dos in der Akte; ohne Einwilligung keine Aufnahme (Gegenprobe).
- CEO-Tor: Recht (Aufnahme von Gespraechen). Aufwand: mittel.

## Paket C -- „Mitdenken und lernen“

### J7: LUNA lernt aus Korrekturen

- Status: umgesetzt (2026-10-29), Abnahme offen -- Werkzeug `regel_vorschlagen` (Gruppe „lernen“, geladen bei
  Korrektur-Woertern wie „falsch“, „heisst“, „merk dir“, „ab jetzt“) legt einen Vorschlag an; Knoepfe „✅ Als Regel
  merken / ❌ Nein“ unter LUNAs Antwort in Telegram, sonst in LUNA-OS -> Einstellungen -> „🧠 Feste Regeln fuer LUNA“
  (dort auch Loeschen). Bestaetigte Regeln stehen im System-Prompt jedes Gespraechs (hoechstens 30, je 200 Zeichen).
  Schutz: Regeltexte mit Injection-Muster werden abgewiesen, Werkzeug nach Fremdtext-Verdacht gesperrt. Speicher
  `regeln/log.jsonl` (`core/regeln.py`). Nebenbei: veralteter Satz zum Anthropic-Limit „bis 1. Juli“ aus dem Chat-Prompt
  entfernt (Platz fuer das Token-Budget der Werkzeugauswahl).

- Ziel / Scope: Korrigiert der CEO etwas (Schreibweise, Format, Vorgehen), schlaegt LUNA eine feste Regel vor
  („Kiez Alm, nie Kizalm – als Regel merken?“). Erst nach Bestaetigung gilt sie; Liste der Regeln in LUNA-OS, jederzeit
  loeschbar. Passt zur Regel „trainieren = Anleitung + Rueckmeldungen“ (kein Modell-Training).
- Gate: Korrektur -> Vorschlag -> bestaetigt -> wirkt im naechsten Gespraech; abgelehnt -> keine Regel.
- Aufwand: mittel.

### J8: Bessere Suche im Gedaechtnis

- Status: umgesetzt (2026-10-29), Abnahme offen -- `brain_suchen` durchsucht jetzt auch Firmen, Firmenakte, Angebote,
  Auftraege (mit Kennzahlen + Projektbericht), Rechnungen, Eingangsbelege (+ Zusammenfassung je Lieferant), eigene
  To-dos, Wissen, Research und offene/erledigte Antraege (abgelehnte/geloeschte nicht -- Rauschen). Wortsuche (BM25) +
  Bedeutungssuche (Suchmodell `qwen3-embedding:0.6b`, Apache 2.0, im Ollama auf dem MACO470, CEO-Go 2026-10-29), gemischt
  per Reciprocal Rank Fusion; MACO470 aus -> nur Wortsuche. Suchverzeichnis `gedaechtnis/vektoren.json` auf der NAS,
  stuendlich nachgezogen (Bot-Takt), Erstaufbau ca. 30 s. Code `core/gedaechtnis.py`.
- **Gate-Messung 2026-10-29** (Kopie des Backups vom 29.10., 488 Vorgaenge, Treffer = richtige Quelle unter den ersten 5):
  heutige Suche **0/10**, nur Wortsuche **6/10**, Wort + Bedeutung **9/10**. Verfehlt: „Wo haben wir Webhosting und unsere
  Domains?“ -- dass All-Inkl der Hoster ist, steht nirgends in den Daten (nur Kategorie „Software, Abos, Hosting“);
  abhilfe: Notiz an der Firma oder „merk dir“. Eine Suche dauert auf dem MACO470 ca. 1,4 s.

- Ziel / Scope: Fragen wie „Was hat Kiez Alm letztes Jahr gebucht und wie lief es?“ ueber Akte, Mails, Angebote,
  Berichte und Wissen hinweg -- mit Bedeutungssuche (lokal auf dem MACO470), Antwort mit Quellenangaben.
- Gate: 10 Pruef-Fragen mit bekannter Antwort, Trefferquote dokumentiert.
- Aufwand: mittel.

### J9: Wochenplanung mit Zeitbloecken

- Status: umgesetzt (2026-10-29), Abnahme offen -- `core/wochenplan.py`, regelbasiert (kein Modell, keine Kosten).
  **Montag** nach dem Morgen-Briefing (+15 min, bis 12 Uhr): offene eigene To-dos ohne feste Uhrzeit (ueberfaellig,
  faellig bis Sonntag, dann ohne Datum, aelteste zuerst; hoechstens 6) als 1-Stunden-Bloecke in freie Luecken Mo-Fr
  9-18 Uhr, Mittag 12-13 frei, 15 min Puffer um Termine, ganztaegige Termine sperren den Tag, nie nach der Faelligkeit.
  Knoepfe „✅ Eintragen / ❌ Nein“; nach ✅ wird der Kalender **frisch** geprueft, belegte Bloecke fallen weg, die
  uebrigen kommen als „🧱 …“ in LUNAs Kalender. Auch per Chat („Plan mir die Woche“, Werkzeug `wochenplan_vorschlagen`).
  **Freitag 16 Uhr** Wochenrueckblick: erledigte/offene To-dos, Rechnungen der Woche, offene Forderungen, Termine der
  naechsten Woche. Beides in den Einstellungen abschaltbar (`wochenplanung`, `wochenrueckblick`, Standard an).
  Speicher `wochenplan/log.jsonl`. Test: 8 Self-Checks inkl. Gate „kein Block ueberschneidet einen Termin“ mit Gegenproben.

- Ziel / Scope: Montags schlaegt LUNA vor, offene To-dos als Bloecke in freie Kalenderluecken zu legen (CEO bestaetigt
  per Knopf); freitags Wochenrueckblick (erledigt, offen, Umsatz, naechste Woche).
- Gate: Vorschlag ueberschneidet keinen Termin; nichts landet ohne Bestaetigung im Kalender.
- Aufwand: mittel.

## Paket D -- „Haende am Rechner“ (= Phase 17)

- Plan seit 2026-10-29 in `RECHNER_STEUERUNG_ROADMAP.md` (Etappen D1-D6, Fragen D0) -- wartet auf CEO-Pruefung.

- LUNA bedient den Rechner (MACO470/Windows) auf ausdrueckliche Anweisung -- Plan W1-W7 steht in `ROADMAP.md`
  (Phase 17), mit Not-Aus, Protokoll und CEO-Tor. Wird nach A-C oder auf ausdruecklichen Wunsch vorgezogen.
- Aufwand: gross.

## Reihenfolge und Aufwand

| Paket | Etappen | Aufwand | Kosten | Abhaengigkeit |
|---|---|---|---|---|
| A Sofort im Alltag | J1-J4 | klein | keine bis gering (J2 ggf. Sprachausgabe) | keine |
| C Mitdenken und lernen | J7-J9 | mittel | keine (lokal) | J8 nutzt MACO470 |
| D Haende am Rechner | Phase 17 W1-W7 | gross | offen | eigene Planung |
| B Verstehen, was reinkommt | J5-J6 | mittel | keine (lokal) | J1 (lokale Spracherkennung) fuer J6 |

Reihenfolge (CEO 2026-10-29): **A -> C -> D -> B** -- Paket B steht hinter C und D.

## Nicht-Scope

- Fremde Skills/Marktplaetze (ClawHub u. a.) -- Regel „nur eigene Skills“ bleibt.
- Smart Home (nur falls der CEO Geraete nennt; dann eigene Etappe).
- Live-Verkehrsdaten, neue kostenpflichtige Dienste ohne Kostenvoranschlag und CEO-Freigabe.
- Meta-/Instagram-Postfach (verworfen 2026-09-29).
- `.env`, Schluessel, laufende Dienste, Charta-Dateien -- nur mit eigener Freigabe.

## Dokumentationspflicht bei Umsetzung

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md`, `docs/datenfluesse.md` (J1
Spracherkennung lokal, J2 Sprachausgabe, J5/J6 Auswertung), `docs/datenschutz-ki-nutzung.md` (J5, J6),
`docs/bekannte-fehler.md` bei Funden.
