# Roadmap: Kopfzeile aufraeumen -- Suchleiste mit Vorschlaegen, Aufklapp-Menues, Portrait

- Status: geplant
- Stand: 2026-10-07
- Arbeitsbranch: `ai/kopfzeile-suche-menue`
- Basiscommit: `c5299b2`
- Naechster Schritt: Go des CEO fuer K1-K5.
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

## Ergaenzung CEO (2026-10-07)

„Erscheinungsbild Hell/Dunkel/System kann in die Einstellungen. Die Sprachaktivierung von LUNA, zwischen der Glocke
und dem Erscheinungsbild, kann auch in die Einstellungen. Dann ist auf dem iPhone vielleicht Platz? Ausserdem den Mond
oben links vor ‚Geschaeft‘ durch Lunas Portrait ersetzen.“ -- Der Knopf zwischen Glocke und Erscheinungsbild ist der
Umschalter Orb/3D-Hologramm (LUNAs Darstellung); das Sprechen selbst laeuft ueber den LUNA-Knopf unten rechts (bleibt).

## Etappe K4: Erscheinungsbild und LUNA-Darstellung in die Einstellungen

- Status: geplant
- Ziel / Scope: Knoepfe ☀ (Hell/Dunkel) und ◐/🌙 (Orb/Hologramm) verlassen die Kopfzeile; in ⚙ Einstellungen neue Kachel
  „Darstellung“: Erscheinungsbild Hell / Dunkel / System (wie Geraet) und LUNA als Orb / 3D-Hologramm, beides sofort
  wirksam und geraeteuebergreifend gespeichert wie bisher. Auf dem iPhone ist damit Platz fuer ein kompaktes Suchfeld
  in der Kopfzeile (K1 wird dort ein schmales Feld statt nur 🔎; Vorschlaege als Liste unter der Kopfzeile).
- Gate: Browsertest Rechner/iPad/iPhone (Safe Areas), Umschalten wirkt sofort, Einstellung bleibt nach Neuladen.

## Etappe K5: LUNAs Portrait statt Mond

- Status: geplant
- Ziel / Scope: Logo oben links (vor „Geschaeft“) zeigt LUNAs Portrait (`static/luna-portrait.png`, runder Ausschnitt
  um das Gesicht, leichter Leuchtrand) statt des Mondes; Klick fuehrt wie bisher zum Start. Login-Seite und App-Symbol
  unveraendert (eigene Frage, falls gewuenscht).
- Gate: Browsertest hell/dunkel, Rechner/iPad/iPhone.

## Nicht-Scope

Keine neue Suchtechnik (kein Index, kein Dienst), keine neuen Suchquellen.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/bekannte-fehler.md`.

## Definition of Done

Aufgeraeumte Kopfzeile: Suchleiste mit Vorschlaegen (auch iPhone), Aufklapp-Menues bei Maus-Over, Darstellung in den Einstellungen, LUNAs Portrait oben links -- Rechner, iPad, iPhone geprueft.
