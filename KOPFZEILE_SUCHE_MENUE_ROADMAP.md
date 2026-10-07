# Roadmap: Suchleiste mit Vorschlaegen in der Kopfzeile und Aufklapp-Menues

- Status: geplant
- Stand: 2026-10-07
- Arbeitsbranch: `ai/kopfzeile-suche-menue`
- Basiscommit: `c5299b2`
- Naechster Schritt: Go des CEO fuer K1-K3.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-07)

„Die Suche als Suchleiste zwischen ‚LUNA & System‘ und ‚LUNA fragen‘ statt des kleinen Suchen-Knopfs. Eine Art
Autovervollstaendigung: bei ‚HAMBURG‘ tauchen der Hamburger SV, derbe Hamburg usw. auf. Ausserdem bei Maus-Over ueber
Geschaeft und Co. ein Menue mit den naechsten Punkten (ausser man ist schon in dem Bereich).“

## Analyse (read-only)

- Die globale Suche (GLOBALE_SUCHE G1, `/api/suche`) findet schon Wortteile („hamburg“ trifft „Hamburger SV“), ueber alle
  Kategorien und mit Rechten je App. Heute oeffnet der Knopf 🔎 bzw. die Taste „/“ ein eigenes Suchfenster.
- Die Kopfzeile hat links die 4 Bereiche, rechts „LUNA fragen“, Glocke, Theme, Avatar. Auf dem iPhone ist kein Platz fuer
  eine Leiste (dort Burger-Menue).

## Etappe K1: Suchleiste in der Kopfzeile

- Status: geplant
- Ziel / Scope: Eingabefeld „Suchen …“ zwischen den Bereichen und „LUNA fragen“ (Rechner und iPad quer), passt sich der
  Breite an; Taste „/“ springt hinein. iPhone/iPad hoch: weiter der Knopf 🔎 (zu wenig Platz).
- Gate: Browsertest Rechner 1300/1920, iPad 820/1180, iPhone 17 Pro.

## Etappe K2: Vorschlaege beim Tippen (Autovervollstaendigung)

- Status: geplant
- Ziel / Scope: ab 2 Zeichen klappt unter der Leiste eine Liste auf (kurze Verzoegerung beim Tippen), bis zu 8 Treffer
  gemischt nach Kategorie mit Symbol (🏢 Hamburger SV · Kunde, 📄 AN-… „Derbe Hamburg“ …), Suchwort hervorgehoben; Pfeiltasten
  + Enter oeffnen den Treffer, Enter ohne Auswahl bzw. „Alle Ergebnisse“ oeffnet die volle Ergebnisliste; Esc schliesst.
  Gleiche Rechte wie heute (nur erlaubte Apps). Bestehende Suche serverseitig wiederverwendet, nur ein schlanker
  Vorschlags-Modus (weniger Felder).
- Gate: Tests (Vorschlags-Endpunkt, Rechte, leere/kurze Eingabe), Browsertest mit Tastatur.

## Etappe K3: Aufklapp-Menue bei Maus-Over

- Status: geplant
- Ziel / Scope: Maus ueber „Geschaeft“, „Content & Collabs“, „Investment“, „LUNA & System“ -> kleines Menue mit den
  Unterpunkten (z. B. Kunden, Angebote, Auftraege …), Klick oeffnet direkt; nicht fuer den Bereich, in dem man gerade ist;
  kurze Verzoegerung gegen versehentliches Aufklappen. Nur mit Maus (Touch-Geraete unveraendert: Tippen oeffnet den Bereich).
- Gate: Browsertest Rechner (Hover), iPad/iPhone unveraendert.

## Nicht-Scope

Keine neue Suchtechnik (kein Index, kein Dienst), keine neuen Suchquellen.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/bekannte-fehler.md`.

## Definition of Done

Suchleiste mit Vorschlaegen in der Kopfzeile, Aufklapp-Menues bei Maus-Over -- Rechner, iPad, iPhone geprueft.
