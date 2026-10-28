# Roadmap: LUNA als Jarvis im Alltag (Gesamtroadmap in Paketen)

- Status: geplant
- Stand: 2026-10-28
- Arbeitsbranch: `ai/jarvis-alltag`
- Basiscommit: `d4ae65d`
- Naechster Schritt: CEO waehlt das erste Paket (Empfehlung: Paket A) und gibt das Go; bis dahin wird nichts umgesetzt.
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
| Sprachnachrichten in Telegram | werden schon in Text umgewandelt, **ueber Deepgram (Cloud)**, nur wenn ein Schluessel gesetzt ist; ob live aktiv: **unbekannt**, Probe noetig | `orchestrator/channels/telegram/bot.py:313-330`, `:2541`; `docs/datenfluesse.md` Zeile `api.deepgram.com` |
| Lokale Spracherkennung | whisper laeuft auf dem MACO470 fuer den Cutter | `cutter/transkription.py` |
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

- Ziel / Scope: Sprachnachricht in Telegram -> Text -> LUNA handelt wie bei getippter Nachricht (To-do anlegen, Notiz,
  Frage beantworten). Erst Probe, ob es heute schon laeuft. Dann Umstellung auf **lokale Spracherkennung (whisper auf dem
  MACO470)** statt Deepgram (Datenschutz, keine Kosten); Deepgram nur noch als Ersatz, wenn der MACO470 aus ist. LUNA
  antwortet mit „Verstanden: …“ und zeigt den erkannten Text.
- Gate: Sprachnachricht „Erinner mich morgen um 10 an die Steuer“ ergibt ein To-do mit Termin (Empfang in Telegram
  geprueft); MACO470 aus -> Ersatzweg greift oder klare Meldung; Tests mit Gegenprobe.
- Risiko: MACO470 nicht erreichbar -> Ersatzweg. Aufwand: klein.

### J2: Briefing als Sprachnachricht

- Ziel / Scope: Morgen-Briefing zusaetzlich als kurze Sprachnachricht (1-2 Min.) in Telegram, schaltbar. Text wie heute,
  Stimme ueber die vorhandene Sprachausgabe (lokal bevorzugt, falls brauchbar; sonst ElevenLabs mit Kostenvoranschlag).
- Gate: Sprachnachricht kommt an (Empfang geprueft), Kosten im Kostenlog sichtbar und unter dem Richtwert.
- CEO-Tor: nur falls dafuer laufende Kosten entstehen (Kostenvoranschlag CFO). Aufwand: klein.

### J3: Abfahrts-Erinnerung

- Ziel / Scope: Bei Kalenderterminen mit Ort rechnet LUNA die Fahrzeit (vorhandene Routen) und schickt rechtzeitig
  „In 20 Min. losfahren nach …“ mit Kartenlink. **Ohne Live-Verkehr** (OSRM kennt keinen Stau) -- daher Puffer
  (Standard +15 %, mind. 10 Min.). Live-Verkehr waere ein neuer Dienst (CEO-Tor) und ist hier nicht Scope.
- Gate: Testtermin mit Adresse -> Erinnerung zur richtigen Zeit genau einmal; Termin ohne Ort -> keine Erinnerung.
- Aufwand: klein.

### J4: Kundenpflege-Hinweise

- Ziel / Scope: „Zu erledigen“ und Briefing melden: Kunde seit X Tagen ohne Kontakt (Standard 60), Geburtstag eines
  Ansprechpartners (neues optionales Feld), Jahrestag einer Kampagne („vor einem Jahr lief …“ -> Folgeangebot?).
- Gate: Tests (Schwelle, einmal je Anlass, erledigt -> weg); Browser-Pruefung des neuen Feldes durch den CEO.
- Aufwand: klein.

## Paket B -- „Verstehen, was reinkommt“

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

- Ziel / Scope: Korrigiert der CEO etwas (Schreibweise, Format, Vorgehen), schlaegt LUNA eine feste Regel vor
  („Kiez Alm, nie Kizalm – als Regel merken?“). Erst nach Bestaetigung gilt sie; Liste der Regeln in LUNA-OS, jederzeit
  loeschbar. Passt zur Regel „trainieren = Anleitung + Rueckmeldungen“ (kein Modell-Training).
- Gate: Korrektur -> Vorschlag -> bestaetigt -> wirkt im naechsten Gespraech; abgelehnt -> keine Regel.
- Aufwand: mittel.

### J8: Bessere Suche im Gedaechtnis

- Ziel / Scope: Fragen wie „Was hat Kiez Alm letztes Jahr gebucht und wie lief es?“ ueber Akte, Mails, Angebote,
  Berichte und Wissen hinweg -- mit Bedeutungssuche (lokal auf dem MACO470), Antwort mit Quellenangaben.
- Gate: 10 Pruef-Fragen mit bekannter Antwort, Trefferquote dokumentiert.
- Aufwand: mittel.

### J9: Wochenplanung mit Zeitbloecken

- Ziel / Scope: Montags schlaegt LUNA vor, offene To-dos als Bloecke in freie Kalenderluecken zu legen (CEO bestaetigt
  per Knopf); freitags Wochenrueckblick (erledigt, offen, Umsatz, naechste Woche).
- Gate: Vorschlag ueberschneidet keinen Termin; nichts landet ohne Bestaetigung im Kalender.
- Aufwand: mittel.

## Paket D -- „Haende am Rechner“ (= Phase 17)

- LUNA bedient den Rechner (MACO470/Windows) auf ausdrueckliche Anweisung -- Plan W1-W7 steht in `ROADMAP.md`
  (Phase 17), mit Not-Aus, Protokoll und CEO-Tor. Wird nach A-C oder auf ausdruecklichen Wunsch vorgezogen.
- Aufwand: gross.

## Reihenfolge und Aufwand

| Paket | Etappen | Aufwand | Kosten | Abhaengigkeit |
|---|---|---|---|---|
| A Sofort im Alltag | J1-J4 | klein | keine bis gering (J2 ggf. Sprachausgabe) | keine |
| B Verstehen, was reinkommt | J5-J6 | mittel | keine (lokal) | J1 (lokale Spracherkennung) fuer J6 |
| C Mitdenken und lernen | J7-J9 | mittel | keine (lokal) | J8 nutzt MACO470 |
| D Haende am Rechner | Phase 17 W1-W7 | gross | offen | eigene Planung |

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
