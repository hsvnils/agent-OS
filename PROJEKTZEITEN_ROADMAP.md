# Roadmap: Projektzeiten als Stundenzettel und optional in der Rechnung
- Status: in Umsetzung
- Stand: 2026-10-02
- Arbeitsbranch: `ai/plan-zeit-bericht` (Plan); Umsetzung je Etappe auf eigenem Branch
- Basiscommit: `6d66942`
- Naechster Schritt: CEO-Go 2026-10-02 fuer alle Etappen am Stueck (zusammen mit PROJEKTBERICHT); Bau auf `ai/projekt-etappen`.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-02)

„Beim Zeit-Tracking immer den Tag und die Einstempel-/Ausstempelzeiten mit tracken. Jedes Tracking haette dann seine
eigenen Daten und Summen -- wie Positionen. Cool waere, wenn ich spaeter in einer moeglichen Rechnung auswaehlen kann,
ob die Projektzeiten mitgerechnet werden.“

## Analyse (read-only, 2026-10-02)

- Die Daten sind schon da: jeder Eintrag (`zeit_start`/`zeit_stopp` bzw. `zeit_eintrag`, `core/zeiterfassung.py`)
  speichert **Start und Ende mit Datum und Uhrzeit**, Minuten, kalkulatorische Kosten und Fahrten. Es fehlt die
  Darstellung als Stundenzettel (Zeile je Eintrag mit Summen), eine Korrektur (heute nur Stornieren + neu) und eine
  Taetigkeit je Eintrag.
- Rechnungen entstehen aus dem Auftrag (`/api/finanzen/rechnungen/aus-auftrag/<nr>`) nur mit dessen Positionen.
- Der hinterlegte Stundensatz (29,20 EUR) ist **kalkulatorisch** (Brutto-Lohn Hauptjob) -- er ist ein Kostensatz, kein
  Verkaufspreis. Fuer eine Abrechnung braucht es einen eigenen **Verkaufs-Stundensatz**.
- CEO-Regel 2026-09-30: Stunden sind intern, nie beim Kunden. Diese Roadmap macht sie **nur auf ausdruecklichen Wunsch
  je Rechnung/Bericht** sichtbar (Standard bleibt intern) -- Register-Eintrag bei Umsetzung.

## Etappe Z1: Stundenzettel je Auftrag

- Status: umgesetzt (2026-10-02) -- Ereignisse `zeit_details`/`zeit_korrigiert`, Pause mindert die Dauer, `stundenzettel()`,
  Endpunkte `/api/finanzen/zeit/<id>/details|korrigieren`, Tabelle im Auftrag (Handy: kompakte Karten), Taetigkeit + Pause
  nach dem Stoppen (Fenster und Telegram-Knoepfe). Tests `test_projektzeiten.py` mit Gegenprobe; Browsertest 1300/820/390 px.
- Ziel / Scope: Im Auftrag (und im Zeit-Fenster) eine Tabelle wie Positionen: **Datum · Ein · Aus · Pause · Dauer ·
  Taetigkeit · km · Quelle**, Summen je Tag und gesamt (Stunden, km, interne Kosten). Beim Stoppen und beim Nachtrag
  kurz die **Taetigkeit** (z. B. Dreh, Schnitt, Abstimmung; Vorschlaege merken). **Korrigieren** statt nur stornieren
  (Ein/Aus/Pause aendern, Verlauf bleibt). Pause optional in Minuten. Telegram „Bin wieder zuhause“ fragt kurz nach
  der Taetigkeit (Knoepfe mit den letzten drei).
- Gate: Tests -- Summen je Tag/gesamt, Korrektur mit Verlauf, Pause mindert die Dauer, ueber Mitternacht; Browsertest
  Desktop + iPhone 390 px + iPad 820 px.
- Aufwand: klein bis mittel.

## Etappe Z2: Projektzeiten optional in der Rechnung

- Status: geplant
- Ziel / Scope: Beim Rechnungsentwurf aus einem Auftrag der Schalter **„Projektzeiten abrechnen“** (Standard aus).
  Darunter der Stundenzettel mit Haken je Eintrag (vorausgewaehlt: noch nicht abgerechnete). Darstellung waehlbar:
  **einzeln** (je Eintrag eine Position „Arbeitszeit 05.10.2026, 09:00–12:30 (3,5 h)“) oder **zusammengefasst**
  („Projektzeit 12,5 h“, Stundenzettel als Anlage zum PDF). Preis = **Verkaufs-Stundensatz** (Katalog-Artikel
  „Projektstunde“, je Auftrag aenderbar). Abgerechnete Eintraege sind markiert (keine Doppelabrechnung); ein
  Rechnungs-Storno gibt sie wieder frei. Ebenso per Haken Fahrten (km x Verkaufs-km-Satz, CEO-Entscheidung 2026-10-02).
- Gate: Tests -- Auswahl, beide Darstellungen, Summe = Stunden x Satz, Doppelabrechnung verhindert, Storno gibt frei,
  EUeR bucht nur die echte Einnahme (kalkulatorische Kosten bleiben getrennt); PDF-Pruefung; Browsertest Desktop +
  Mobil.
- Aufwand: mittel.

## Etappe Z3 (eigener Vorschlag): Zeiten auswerten

- Status: geplant (Vorschlag Claude Code)
- Ziel / Scope: Wochen-/Monatsuebersicht ueber alle Auftraege (Stunden je Kunde/Taetigkeit), CSV-Export; Zeit
  optional einer **Auftragsposition** zuordnen (z. B. „Reel 2“) -> Nachkalkulation je Leistung zeigt, welche Formate
  sich lohnen und wo Preise im Katalog zu niedrig sind.
- Aufwand: klein bis mittel.

## CEO-Entscheidungen (2026-10-02)

1. Verkaufs-Stundensatz: Katalog-Artikel „Projektstunde“, je Auftrag aenderbar.
2. Darstellung auf der Rechnung: je Rechnung waehlbar einzeln/zusammengefasst, **Standard zusammengefasst** +
   Stundenzettel als Anlage.
3. **Stunden und km per Haken** abrechen- und zeigbar (Standard aus). Dem Kunden berechnete km sind echte Einnahmen
   (Verkaufs-km-Satz, eigener Katalog-Artikel); die kalkulatorischen Fahrtkosten bleiben getrennt.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (neue Ereignisse/Endpunkte),
`docs/entscheidungs-register.md` (Stunden optional sichtbar, Verkaufs-Stundensatz), `docs/verfahrensdokumentation-
buchhaltung.md` (abgerechnete Zeit = echte Einnahme, kalkulatorische Kosten unveraendert getrennt).

## Definition of Done

Z1 und Z2 verifiziert und vom CEO abgenommen (Desktop und Mobil); Z3 nach eigenem Go.
