# Roadmap: LUNA live am Rechner (Jarvis Paket D = Phase 17, MACO470) -- Mischform lokal + Cloud auf Ansage

- Status: geplant
- Stand: 2026-10-29
- Arbeitsbranch: `ai/rechner-steuerung-plan`
- Basiscommit: `969acf3`
- Naechster Schritt: CEO beantwortet die offenen Fragen (Abschnitt „Noch offen“) und gibt Go fuer die Probe L1 (Ohr, Kopf, Mund lokal -- nichts bedienen).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Anforderung (CEO, 2026-10-29)

> „Wie mit ChatGPT Sprache eine Unterhaltung mit LUNA auf meinem Rechner fuehren und gemeinsam mit ihr arbeiten
> koennen, und zwar an allem. Waehrend ich spreche, muss sie weiter zuhoeren und schnell reagieren koennen.
> Ausserdem soll sie schnell und praezise Aufgaben ausfuehren koennen. Ich will meinen Rechner hands-free mit ihr
> benutzen. Sie muss verstehen, was gerade auf dem Bildschirm ist, und es auch umsetzen koennen.“
> **Das Wichtigste: das Bedienen und Beauftragen von Aufgaben per Sprache.**
> **Loesung lokal und kostenlos -- als Mischform** (Cloud nur auf ausdrueckliche Ansage fuer einzelne schwere Schritte).

## Entscheidungen des CEO (2026-10-29)

| Frage | Entscheidung |
|---|---|
| Rechner | MACO470 (Windows 11), direkt oder per **Windows App** vom MacBook (Mikrofon-Umleitung) |
| Zuhoeren | Aktivierungswort „LUNA“, dann offene Sitzung bis „Danke LUNA“ oder 2 Min. Ruhe; mit Headset |
| Bild und Ton | **bleiben lokal** -- keine dauerhafte Uebertragung an Google/OpenAI (Live-APIs verworfen) |
| Kosten | kostenlos im Normalbetrieb; Cloud nur auf Ansage (Mischform) |
| Stimme | Hoerprobe Pflicht, dann Entscheidung; notfalls die, die geht, „solange der Rest klappt“ |
| Bestaetigen per Sprache | harmlos direkt; Senden/Loeschen nur nach „Ja, senden/loeschen“ mit Wiederholung; Geld/Vertraege/Posten nie per Sprache |
| Browser | ansehen/vorlesen ja; Handgriffe nur auf direkte Ansage; Webtext nie als Befehl (Ausnahme zu AGENTS.md 5.7, CISO-Eintrag bei Umsetzung) |
| Wichtigste Aufgabe | Bedienen und Beauftragen per Sprache |

## Mischform -- was wo laeuft

| Teil | Lokal auf dem MACO470 (Standard, kostenlos) | Cloud -- nur auf deine Ansage |
|---|---|---|
| **Ohr** | Spracherkennung Whisper (lokal), Sprechpausen-Erkennung, Aktivierungswort, Unterbrechen | -- |
| **Mund** | lokale Stimme (Kandidaten nach Hoerprobe) | -- |
| **Kopf fuer Bedienen** | lokales Modell (`qwen3:30b-a3b` oder `qwen3:14b`, Ollama) entscheidet Handgriffe | „Frag Claude“: ein schwerer Schritt geht an Claude |
| **Augen** | Windows-Bedienschnittstelle liest Fenster, Knoepfe, Felder und Texte **ohne Bildmodell** (schnell); Bildmodell `gemma3:27b` bei Bedarf (ca. 10-15 s) | „Schau genau hin“: ein Bildschirmfoto an Claude |
| **Haende** | Windows-Bedienschnittstelle (Knopf/Feld per Name), Tastatur, Dateien | -- |
| **Auftraege an LUNA** (To-dos, Termine, Mail-Entwuerfe, Kunden, Rechnungen, Gedaechtnis) | Sprache wird lokal zu Text | der **Text** geht wie heute aus Telegram an LUNA (Chat-Modell Claude, bestehender Datenfluss) -- siehe „Noch offen“ Nr. 1 |

Cloud-Schritte kuendigt LUNA an („Dafuer frage ich Claude, ein Bildschirmausschnitt geht raus – okay?“) und fuehrt
sie erst nach deinem „ja“ aus. Fenster aus der Augen-aus-Liste (Banking, Passwort-Manager …) sieht sie nie.

## Endbild -- so fuehlt es sich am Ende an

- „LUNA?“ -- sie ist da. Du redest normal, unterbrichst sie, sie hoert sofort auf und hoert zu.
- **Beauftragen:** „Leg ein To-do an: Angebot Kiez Alm bis Freitag“, „Was steht morgen an?“, „Schreib Anna einen
  Entwurf, dass Dienstag passt“, „Was hat CR Container gebucht?“ -- erledigt wie in Telegram, Antwort gesprochen.
- **Bedienen:** „Oeffne Outlook“, „Neue Mail an Anna, Betreff Dreh“, „Scroll runter“, „Klick auf Senden“ (-> „Ja, senden?“),
  „Leg den Ordner Kiez Alm in Dokumente an und schieb die zwei PDFs rein“.
- **Bildschirm verstehen:** „Was steht in der offenen Mail?“, „Welche Dateien liegen hier?“ -- sofort aus der
  Bedienschnittstelle; „Was ist auf dem Bild?“ -- Bildmodell (langsamer) oder auf Ansage Claude.
- **Laengere Aufgaben:** „Exportier die Praesentation als PDF in den Kundenordner“ -- Schritt fuer Schritt, sie sagt an,
  was sie tut, und haelt bei Unsicherheit an.
- „Stopp.“ -- alles haelt sofort an.

**Ehrlich zu erwarten (lokal):** Antworten setzen eher nach **ca. 1,5-3 s** ein (ChatGPT Voice: unter 1 s); das lokale
Modell versteht einfache, klare Ansagen gut, bei verschachtelten Aufgaben hilft „frag Claude“. Die Stimme haengt an der
Hoerprobe. Genaue Werte misst L1. Spaeterer Ausbau ohne Planaenderung: eine Grafikkarte macht alles deutlich schneller
(CEO-Tor, nicht geplant).

## Bestand und Recherche (2026-10-29)

| Thema | Befund | Folgerung |
|---|---|---|
| OpenJarvis | lokaler Agenten-Rahmen ohne Echtzeit-Gespraech/Bildschirm/Rechnersteuerung | nicht geeignet (Register) |
| Gemini Live / OpenAI Realtime | koennen alles live, aber Bild + Ton dauerhaft an den Anbieter, kostet | **verworfen** (CEO: lokal) |
| Microsoft UFO² (MIT) | Windows-Agent mit Bedienschnittstelle + Bilderkennung | Vorlage fuer Haende (L4), Uebernahme nach Pruefung |
| Lokales Bildmodell `gemma3:27b` | liest Testbildschirm richtig, Klick-Position falsch, ca. 13 s | Augen ueber Bedienschnittstelle, Bild nur ergaenzend |
| Lokale Stimmen | Stimme C (Qwen3-TTS 0.6B) ca. 7x langsamer als Echtzeit; Kokoro/Piper echtzeitfaehig, in J2b verworfen | Hoerprobe L1 entscheidet (inkl. Versuch, Stimme C zu beschleunigen) |
| MACO470 | Windows-Python 3.12, Sitzung „nils“ aktiv seit 15.10., kein Auto-Login, 30 GB RAM, Radeon 890M | App laeuft in deiner angemeldeten Sitzung |
| Repo | Steuer-Schleife (`runner/computer_use.py`), XMind (`runner/xmind.py`), Sandbox-Policy (Phase 25), Bruecken-Muster (`sprachdienst/`), Injection-Schutz, LUNA-Werkzeuge | wird wiederverwendet |

## Etappen

### L1: Probe „Ohr, Kopf, Mund“ -- lokal, ohne Bildschirm, ohne Handgriffe

- Ziel / Scope: kleines Probe-Programm unter Windows: Aktivierungswort, Whisper-Erkennung, lokales Modell, lokale
  Stimme, Unterbrechen. **Messen statt schaetzen:** Ende deines Satzes -> erstes Wort von LUNA; Unterbrechen -> Stille;
  Erkennung deutscher Saetze (inkl. Firmennamen); `qwen3:30b-a3b` gegen `qwen3:14b` (Tempo, Werkzeug-Treffsicherheit);
  **Hoerprobe** der echtzeitfaehigen Stimmen + Versuch, Stimme C zu beschleunigen; alles auch ueber die Windows App
  vom MacBook.
- Gate: Antwortbeginn im Mittel **unter 3 s** (Ziel 2 s); Unterbrechen **unter 0,5 s**; Erkennung **mind. 9 von 10**
  Testsaetzen woertlich richtig; Hoerprobe entschieden (CEO). Werte in dieser Datei.
- Aufwand: mittel. Kosten: keine. Rueckweg: Programm schliessen; nur Python-Pakete und Modelle installiert (CEO-Info
  vorab, Groesse ca. 1-3 GB).
- Stopp-Kriterium: Wird das Gate klar verfehlt, legen wir dir vor dem Weiterbau die Optionen vor (z. B. Grafikkarte,
  mehr Cloud) -- kein Weiterbau auf Verdacht.

### L2: LUNA-Desktop + Beauftragen per Sprache (wichtigste Aufgabe zuerst)

- Ziel / Scope: daraus die App: startet mit deiner Anmeldung, kleines Symbol, Aktivierungswort, „Stopp“ +
  Tastenkuerzel, Protokoll jeder Sitzung (ohne Tonaufnahme). **Auftraege an LUNA:** gesprochener Auftrag -> LUNA (wie
  Telegram, mit Gespraechsverlauf) -> Antwort gesprochen; Freigaben per „Ja, …“ nach Wiederholung. Neues
  Maschinenkonto fuer die LUNA-OS-API (CISO).
- Gate: 10 typische Auftraege (To-do, Termin, Mail-Entwurf, Kunden-/Rechnungsfrage, Gedaechtnis, Wochenplan) per
  Sprache richtig; „Stopp“ unter 0,5 s; 3 Arbeitstage ohne Absturz.

### L3: Augen -- Bildschirm verstehen

- Ziel / Scope: „Was ist offen / was steht da?“ aus der Bedienschnittstelle (Fenster, Inhalte, markiertes Element);
  Bildmodell auf Wunsch; **Mischform:** „schau genau hin“ -> Ausschnitt an Claude nach deinem „ja“. Augen-aus-Liste.
  Bildschirmtext ist Fremdtext (Injection-Schutz).
- Gate: 10 Bildschirmfragen in deinen Apps, mind. 9 richtig, Antwort aus der Bedienschnittstelle unter 2 s; Augen-aus
  greift (Test mit Gegenprobe); Cloud-Blick nie ohne „ja“ (Test).
- CEO-Tor: Cloud-Blick = Bildschirmausschnitt an Anthropic (Datenschutz-Eintrag, nur auf Ansage).

### L4: Haende -- Bedienen per Sprache

- Ziel / Scope: App oeffnen/wechseln, tippen/diktieren, Tastenkuerzel, Knopf/Feld/Menue per Name, scrollen,
  markieren, Dateien kopieren/verschieben/umbenennen; Sandbox-Policy (Apps/Ordner) und Bestaetigungsstufen.
- Gate: 20 Handgriffe in deinen Alltags-Apps, **mind. 95 % richtig, je unter 3 s**; „Ja, senden/loeschen“ ohne
  Wiederholung nie ausgefuehrt (Test).

### L5: Laengere Aufgaben

- Ziel / Scope: Ziel -> Kette von Handgriffen (vorhandene Steuer-Schleife), lokal; bei schweren Schritten „frag Claude“
  (nach „ja“); Ansagen waehrend der Arbeit, du kannst weiterreden oder „Stopp“ sagen.
- Gate: 5 Mehrschritt-Aufgaben, Erfolgsquote dokumentiert; Abbruch mitten in der Kette (Test).

### L6: Feinschliff im Alltag

- Ziel / Scope: deine haeufigsten Ansagen schneller/sicherer machen (App-Kenntnisse, Kuerzel, eigene Woerter),
  Cloud-Kosten im CFO-Bericht, Verhalten bei MACO470-Neustart/Fernzugriff.
- Gate: 2 Wochen Alltag, CEO-Abnahme.

## Reihenfolge und Aufwand

| Etappe | Aufwand | Kosten | Abhaengigkeit |
|---|---|---|---|
| L1 Probe Ohr/Kopf/Mund | mittel | keine | Go |
| L2 Desktop + Beauftragen | mittel | keine (Text an LUNA wie Telegram) | L1 bestanden, CISO-Konto |
| L3 Augen | mittel | Cloud-Blick nur auf Ansage (Cent-Betraege) | L2 |
| L4 Haende | mittel-gross | keine | L3 |
| L5 Laengere Aufgaben | gross | „frag Claude“ nur auf Ansage | L4 |
| L6 Feinschliff | mittel | -- | L5 |

Nach **L2** ist deine wichtigste Aufgabe (Beauftragen per Sprache) im Alltag nutzbar, nach **L4** das Bedienen.

## Noch offen (Fragen an den CEO)

1. **Auftraege an LUNA:** Der **Text** deiner Auftraege geht wie heute bei Telegram an LUNAs Chat-Modell (Claude) --
   Ton und Bildschirm bleiben lokal. Passt das? Oder soll LUNA auch dafuer lokal denken (langsamer, weniger klug;
   heute als Ausweich vorhanden)?
2. **Headset** vorhanden (am MACO470 bzw. am MacBook fuer die Windows App)? Ohne Headset hoert LUNA sich selbst und
   Videos mit -- Unterbrechen klappt dann schlecht.
3. **„Frag Claude“ / „schau genau hin“:** jedes Mal kurz nachfragen (Vorschlag) oder pro Sitzung einmal erlauben?
4. **Augen-aus-Liste:** welche Apps/Fenster nie? Vorschlag: Banking, PayPal, Passwort-Manager, Windows-Sicherheit,
   alles mit „Passwort“ im Fenstertitel.
5. **Installation auf dem MACO470:** fuer L1 kommen Python-Pakete und Modelle unter Windows dazu (kostenlos, ca. 1-3 GB,
   ohne Einfluss auf Cutter/Backup). Einverstanden?

## Nicht-Scope

Dauerhafte Uebertragung von Bild/Ton an Cloud-Anbieter; Zahlungen, Vertragsabschluesse, Posten (nur Entwuerfe);
Systemeinstellungen, Installationen durch LUNA, Passwort-Manager, `.env`/Schluessel; Tonaufnahmen speichern; der
Telegram-Bot (bleibt auf der NAS); `cutter-worker`/Backup/Keepalive; MacBook als eigener Steuer-Rechner;
Grafikkarten-Kauf (eigene Entscheidung); Charta-Aenderungen.

## Dokumentationspflicht bei Umsetzung

`projekt_changelog.md`, Etappen-Status hier, `ROADMAP.md` (Phase 17 + Verzeichnis), `JARVIS_ALLTAG_ROADMAP.md`
Paket D, `docs/entscheidungs-register.md`, `docs/datenfluesse.md` (Desktop-App, API-Bruecke, Cloud-Blick),
`docs/datenschutz-ki-nutzung.md`, `finance/kosten-statistik.md` (Cloud-Schritte), `governance/sandbox-policy.*`,
`AGENTS.md` 5.7 (Browser-Ausnahme, CISO) und Abschnitt 7 (Ordner der Desktop-App), `docs/bekannte-fehler.md`.

## Definition of Done

L1-L6 verifiziert, CEO-Abnahme im Alltag; der CEO setzt den Status auf abgeschlossen.
