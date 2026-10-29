# Roadmap: LUNA Live am Rechner (Jarvis Paket D = Phase 17, MACO470)

- Status: geplant
- Stand: 2026-10-29
- Arbeitsbranch: `ai/rechner-steuerung-plan`
- Basiscommit: `969acf3`
- Naechster Schritt: CEO beantwortet die Fragen in L0 und gibt Go fuer die Machbarkeitsprobe L1 (nur Sprechen + Sehen, keine Handgriffe).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Anforderung (CEO, 2026-10-29, ersetzt den ersten Entwurf D0-D6)

> „Wie mit ChatGPT Sprache eine Unterhaltung mit LUNA auf meinem Rechner fuehren und gemeinsam mit ihr arbeiten
> koennen, und zwar an allem. Waehrend ich spreche, muss sie weiter zuhoeren und schnell reagieren koennen.
> Ausserdem soll sie schnell und praezise Aufgaben ausfuehren koennen. Ich will meinen Rechner hands-free mit ihr
> benutzen. Sie muss verstehen, was gerade auf dem Bildschirm ist, und es auch umsetzen koennen. Wie die
> Astra-Praesentation bzw. ein Jarvis.“

Rechner: **MACO470** (Windows 11). Der CEO arbeitet dort direkt **oder per Fernzugriff vom MacBook**.

Daraus folgen fuenf harte Eigenschaften:

| Eigenschaft | Bedeutet technisch |
|---|---|
| Gespraech wie ChatGPT Voice | Sprache rein und raus **direkt** (Speech-to-Speech), Antwortbeginn unter ca. 1 s |
| Zuhoeren waehrend sie spricht | **Unterbrechen** („barge-in“): LUNA verstummt, sobald du sprichst, und hoert weiter zu |
| Versteht den Bildschirm | laufend Bildschirmbilder (ca. 1 pro Sekunde) im selben Gespraech + Liste der Bedienelemente |
| Fuehrt schnell und praezise aus | Handgriffe ueber die Windows-Bedienschnittstelle (Knopf/Feld per Name statt Pixel), Tastatur, Dateien |
| Hands-free | Aktivierungswort bzw. offene Sitzung, Not-Aus per Sprache („Stopp“) und Tastenkuerzel |

## Endbild -- so fuehlt es sich am Ende an

- Du sagst „LUNA?“ -- sie ist da. Du redest normal, unterbrichst sie, sie hoert dich und reagiert sofort.
- „Was steht in der Mail, die gerade offen ist?“ -- sie liest vom Bildschirm vor und fasst zusammen.
- „Antworte Kiez Alm, dass der Dreh am Dienstag passt, Ton wie immer“ -- sie schreibt den Entwurf sichtbar ins
  Mail-Programm; du sagst „freundlicher, und erwaehn das Angebot“ -- sie aendert es live. **Senden machst du** (oder
  ausdrueckliches „Ja, senden“ -- siehe L0 Nr. 6).
- „Leg in XMind Aeste fuer Briefing, Dreh, Schnitt an“ -- die Knoten entstehen, waehrend du weiterredest.
- „Sortier die Downloads“ -- sie sagt, was sie vorhat, und tut es nach deinem „ja“.
- „Wie viel hat Kiez Alm noch offen?“ -- sie fragt LUNAs Geschaeftsdaten ab (Rechnungen, To-dos, Kalender,
  Gedaechtnis-Suche J8) und antwortet, ohne dass du etwas oeffnest.
- „Stopp.“ -- alles haelt sofort an.

## Bestand und Recherche (2026-10-29)

| Thema | Befund | Folgerung |
|---|---|---|
| **OpenJarvis** (`open-jarvis/openjarvis`, Apache 2.0, ca. 12k Sterne, Stanford) | lokal-zuerst Agenten-Rahmen (Ollama, Briefing mit Sprachausgabe, Skills, Windows-Installer); **kein Echtzeit-Gespraech, kein Unterbrechen, keine Bildschirm- oder Rechnersteuerung** laut README | hilft fuer dieses Paket **nicht** -- bleibt Ideenquelle (Register 2026-10-28) |
| **Gemini Live API** (Google, Technik hinter „Astra“) | Sprache rein/raus direkt, Unterbrechen, **Bild-/Video-Frames im selben Gespraech** (JPEG, ca. 1/s), Werkzeugaufrufe; aktuelles Modell `gemini-3.1-flash-live-preview` (Vorschau); Bezahlstufe: Daten **nicht** zum Training | **bester Kandidat** fuer Ohr, Mund und Augen |
| **OpenAI Realtime API** (`gpt-realtime`) | Sprache direkt, Unterbrechen, Bildeingabe, Werkzeuge | Alternative, nach eigener Einschaetzung teurer -- Vergleich in L1 |
| **Claude** (wieder aktiv, Sonnet 5.5) | stark im Planen und in Rechnersteuerung, aber **keine Echtzeit-Sprache** | als „Ausfuehrer“ fuer laengere Aufgaben hinter dem Gespraech (L4) |
| **Microsoft UFO²** (`microsoft/UFO`, MIT) | Windows-Agent: Bedienschnittstelle (UIA) + Bilderkennung, ueber 20 Windows-Apps getestet; ohne Sprache | Vorlage/Baustein fuer praezise Handgriffe (L3/L4), Uebernahme erst nach Pruefung |
| Lokal auf dem MACO470 | `gemma3:27b` liest einen Testbildschirm, Klick-Position grob falsch, ca. 13 s je Antwort; Sprach-Arbeiter-Stimme ca. 7x langsamer als Echtzeit | lokal ist **fuer Live zu langsam** -- bleibt fuer Hintergrund und Datenschutz-Faelle |
| Vorhanden im Repo | Steuer-Schleife mit Gefahr-Halt (`runner/computer_use.py`), XMind-Dateiformat (`runner/xmind.py`), Sandbox-Policy (Phase 25), Bruecken-Muster NAS<->MACO470 (`sprachdienst/`), Injection-Schutz (`core/input_guard.py`), Geschaeftsdaten-Werkzeuge (`core/hoa_tools.py`) | wird wiederverwendet |
| MACO470 | Windows-Python 3.12 vorhanden; Sitzung „nils“ an der Konsole seit 15.10.; kein Auto-Login | App laeuft in deiner angemeldeten Sitzung |

**Architektur-Vorschlag:**

```
Mikrofon/Lautsprecher (am MACO470 oder per Fernzugriff vom MacBook)
        │  Ton live, Bildschirm ~1 Bild/s
        ▼
LUNA-Desktop (neue App unter Windows, in deiner Sitzung)
   ├─ Gespraech: Live-Modell (Ohr + Mund + Augen, Unterbrechen)
   ├─ Haende: Windows-Bedienschnittstelle, Tastatur, Dateien  ── Sandbox-Policy, Not-Aus, Protokoll
   ├─ Ausfuehrer fuer laengere Aufgaben (Claude), Gespraech laeuft weiter
   └─ LUNA-Wissen: Kunden, Rechnungen, To-dos, Kalender, Gedaechtnis ── ueber LUNA-OS-API (NAS)
```

## L0 -- Fragen an den CEO (vor L1)

1. **Fernzugriff:** Womit waehlst du dich vom MacBook ein -- Microsoft Remote Desktop / „Windows App“, oder etwas
   anderes (AnyDesk, Parsec, Chrome Remote Desktop)? Ton und Mikrofon muessen durch die Verbindung; bei Remote
   Desktop geht das (Mikrofon-Umleitung einschalten).
2. **Hands-free -- wie soll LUNA zuhoeren?**
   (a) Aktivierungswort „LUNA“, danach offene Sitzung, bis du „Danke LUNA“ sagst oder 2 Min. Ruhe ist;
   (b) Sitzung per Tastenkuerzel an/aus und dann dauerhaft offen; (c) immer offen, wenn die App laeuft.
   Vorschlag: (a) -- mit Kopfhoerer/Headset, sonst hoert sie Videos und andere Stimmen mit.
3. **Cloud fuer Bild und Ton:** Live geht nur mit einem Cloud-Modell. Bildschirm und Sprache gehen dann waehrend der
   Sitzung an **Google** (Bezahlstufe, kein Training; Server ggf. ausserhalb der EU). Auf dem Bildschirm sind
   Kundendaten. Einverstanden? Gibt es Apps/Fenster, die LUNA **nie** sehen darf (z. B. Banking, Passwort-Manager)?
   -> dort schaltet sie die Augen automatisch aus.
4. **Kosten:** Gemini Live rechnet nach Minuten/Token ab. Grobe eigene Schaetzung: **ca. 1-3 EUR je Stunde
   Gespraech mit Bildschirm** (CFO-Kostenvoranschlag vor L1-Freigabe). Wie viele Stunden pro Tag ungefaehr? Soll es
   ein Monatslimit geben, bei dem LUNA warnt bzw. stoppt?
5. **Stimme:** Live spricht LUNA mit einer **Stimme des Anbieters** (deutsch, mehrere weibliche Stimmen zur Wahl),
   nicht mit der lokalen Stimme C -- die ist fuer Echtzeit zu langsam. In Ordnung? (Hoerprobe in L1.)
6. **Bestaetigen ohne Haende:** Was soll ein gesprochenes „Ja“ freigeben duerfen? Vorschlag:
   - harmlos (oeffnen, tippen, Entwurf, verschieben): direkt bzw. nach kurzem „ja“;
   - **Senden, Loeschen (Papierkorb), Kalender anderer:** nur nach ausdruecklichem „Ja, senden/loeschen“, LUNA
     wiederholt vorher genau, was passiert;
   - **Geld, Vertraege, Posten:** nie per Sprache -- nur Entwurf, Abschluss durch dich (AGENTS.md 4).
7. **„An allem“ -- auch der Browser?** Wenn LUNA Webseiten auf deinem Bildschirm liest und bedient, sieht das Modell
   fremde Webinhalte. Das widerspricht heute der Regel „freies Internet nur ueber den Netz-Agenten“ (AGENTS.md 5.7)
   und ist der Hauptweg fuer eingeschleuste Anweisungen. Vorschlag: Browser **ansehen und vorlesen ja**, Handgriffe
   im Browser nur auf deine direkte Ansage, Texte von Webseiten zaehlen als Fremdtext (keine Befehle daraus). Das
   ist eine **Regel-Ausnahme**, die du ausdruecklich entscheiden musst (CISO).
8. **Die wichtigsten 5 Alltagsaufgaben** am Rechner, an denen wir „schnell und praezise“ messen? (z. B. Mail
   beantworten, XMind, Ordner sortieren, LUNA-OS bedienen, Canva/Office …)

## Etappen

### L1: Machbarkeitsprobe „Sprechen + Sehen“ (keine Handgriffe)

- Ziel / Scope: kleines Probe-Programm unter Windows: Gespraech mit dem Live-Modell, Unterbrechen, Bildschirm
  ~1 Bild/s; LUNA beantwortet Fragen zum Bildschirm. **Kann nichts bedienen.** Vergleich Gemini Live gegen OpenAI
  Realtime (je 10 Minuten), auch **ueber den Fernzugriff vom MacBook**. Hoerprobe der Stimmen.
- Gate (gemessen, Werte in dieser Datei): Antwortbeginn im Mittel unter 1,5 s; Unterbrechen stoppt LUNA unter
  0,5 s; 10 von 10 Bildschirmfragen richtig (z. B. „welche Datei ist markiert?“); Deutsch ohne Aussetzer;
  Kosten je Minute gemessen.
- CEO-Tor: neues kostenpflichtiges Modell + Bildschirm an Anbieter (L0 Nr. 3/4); CFO-Kostenvoranschlag.
- Aufwand: klein-mittel. Rueckweg: Programm schliessen, nichts installiert ausser der Python-Umgebung.

### L2: LUNA-Desktop-App mit Sitzung, Not-Aus und LUNA-Wissen

- Ziel / Scope: daraus die App: startet mit deiner Anmeldung (Aufgabenplanung), kleines Symbol unten rechts,
  Aktivierungswort/Tastenkuerzel (L0 Nr. 2), „Stopp“ + Tastenkuerzel = sofort stumm und still, Protokoll jeder
  Sitzung (ohne Tonaufnahme). LUNAs Persoenlichkeit, Datum, **feste Regeln (J7)**. Lesende Werkzeuge ueber die
  LUNA-OS-API: To-dos, Kalender, Kunden, Rechnungen, Gedaechtnis-Suche (J8); To-do anlegen. Augen aus bei Apps aus
  L0 Nr. 3.
- Gate: 3 Arbeitstage im Alltag ohne Absturz; „Stopp“ wirkt unter 0,5 s (Test); Augen-aus-Liste greift (Test mit
  Gegenprobe).
- CISO: eigenes Maschinenkonto fuer die LUNA-OS-API (wie Sprach-Arbeiter).

### L3: Haende -- schnelle, praezise Handgriffe

- Ziel / Scope: App oeffnen/wechseln, tippen, Tastenkuerzel, Knopf/Feld/Menue per Name klicken
  (Bedienschnittstelle, Bild nur zur Kontrolle), scrollen, markieren, Dateien kopieren/verschieben/umbenennen. Jede
  Aktion durch Sandbox-Policy (Ordner-/App-Liste) und Bestaetigungsstufen (L0 Nr. 6). Bildschirmtext gilt als
  Fremdtext (Injection-Schutz).
- Gate: 20 Einzelhandgriffe in den 5 Alltags-Apps (L0 Nr. 8), Trefferquote und Zeit je Handgriff gemessen (Ziel:
  95 % richtig, unter 2 s); gefaehrlicher Handgriff ohne „Ja, …“ wird nicht ausgefuehrt (Test).

### L4: Laengere Aufgaben im Hintergrund, Gespraech laeuft weiter

- Ziel / Scope: „Exportier alle Praesentationen als PDF in die Kundenordner“ -> LUNA gibt es an den Ausfuehrer
  (Claude mit Rechnersteuerung oder UFO²-Baustein, nach Pruefung), sagt Zwischenstaende an, haelt bei Unsicherheit
  an und fragt. Du kannst waehrenddessen weiterreden.
- Gate: 5 Mehrschritt-Aufgaben, Erfolgsquote dokumentiert; Abbruch per „Stopp“ mitten in der Kette (Test).
- CEO-Tor: Kosten des Ausfuehrers (CFO).

### L5: Feinschliff im Alltag

- Ziel / Scope: die 5 Alltagsaufgaben gezielt schneller/sicherer machen (App-Kenntnisse, Kuerzel), Kosten im
  Kostenbericht des CFO, Ausfall-Verhalten (Cloud weg -> „Live gerade nicht verfuegbar“, Telegram geht weiter).
- Gate: 2 Wochen Alltag, deine Abnahme.

## Reihenfolge und Aufwand

| Etappe | Aufwand | Kosten | Abhaengigkeit |
|---|---|---|---|
| L1 Probe Sprechen + Sehen | klein-mittel | Probe-Minuten | L0 Nr. 1, 3, 4, 5 |
| L2 Desktop-App + Wissen | mittel | laufend je Gespraechsstunde | L1 bestanden, L0 Nr. 2 |
| L3 Haende | mittel-gross | wie L2 | L2, L0 Nr. 6-8 |
| L4 Hintergrund-Ausfuehrer | gross | zusaetzlich je Aufgabe | L3 |
| L5 Feinschliff | mittel | -- | L4 |

Nach **L1** weisst du, ob es sich wie ChatGPT Voice anfuehlt -- erst dann lohnt sich der Rest. Nach **L3** ist
das Ziel „hands-free am Rechner“ im Kern erreicht.

## Nicht-Scope

Zahlungen, Vertragsabschluesse, Posten (nur Entwuerfe); Systemeinstellungen, Installationen, Passwort-Manager,
`.env`/Schluessel; Daten anderer Personen aufzeichnen (keine Tonaufnahme gespeichert); der Telegram-Bot (bleibt auf
der NAS); `cutter-worker`/Backup/Keepalive; MacBook als eigener Steuer-Rechner (nur als Fernzugriff); Charta-
Aenderungen.

## Dokumentationspflicht bei Umsetzung

`projekt_changelog.md`, Etappen-Status hier, `ROADMAP.md` (Phase 17 + Verzeichnis), `JARVIS_ALLTAG_ROADMAP.md`
Paket D, `docs/entscheidungs-register.md` (L0-Entscheidungen, Modellwahl, UFO²), `docs/datenfluesse.md` (Live-
Modell, Bildschirm, API-Bruecke), `docs/datenschutz-ki-nutzung.md` (Bildschirm + Sprache an Anbieter),
`finance/kosten-statistik.md` (laufende Kosten), `governance/sandbox-policy.*`, `AGENTS.md` 5.7 (falls Browser-
Ausnahme) und Abschnitt 7 (neuer Ordner der Desktop-App), `docs/bekannte-fehler.md`.

## Definition of Done

L1-L5 verifiziert, CEO-Abnahme im Alltag; der CEO setzt den Status auf abgeschlossen.
