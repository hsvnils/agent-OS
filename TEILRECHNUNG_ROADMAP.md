# Roadmap: Teilrechnung -- Position spaeter gesondert abrechnen

- Status: in Umsetzung
- Stand: 2026-11-14
- Arbeitsbranch: `ai/teilrechnung`
- Basiscommit: `8500711`
- Naechster Schritt: T1 deployt und an der echten Rechnung verifiziert (RE-2026-0003, 2026-11-14). Am 31.12.2026 die
  Folgerechnung erstellen (To-do A-bef2420a erinnert); danach Abnahme durch den CEO und Roadmap abschliessen.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur aktuellen
  Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-11-14)

Eine Rechnung mit Festpreis-Position (800 EUR) und einer Affiliate-Position, die erst spaeter feststeht, soll jetzt
versendet werden koennen. Der Kunde sieht bei der zweiten Position: „Wird am 31.12.2026 gesondert abgerechnet (5,00 € je
verkauftem Artikel).“ (Wortlaut vom CEO bestaetigt). Alles soll sauber nachverfolgbar sein.

## Analyse (read-only)

- Festschreiben war gesperrt, solange eine Provision nicht abgerechnet ist (`orchestrator/core/rechnungen.py`, Etappe 23).
- Je Auftrag war nur eine Rechnung erlaubt (`entwurf_aus_auftrag`, `festschreiben`).
- Vorkasse (Etappe 18) rechnet Abschlaege auf einen Gesamtbetrag -- passt nicht fuer einzelne Positionen.

## Scope

Feld „Spaeter abrechnen am“ je Position (nur Rechnung), Teilrechnung (Summe ohne die spaeteren Positionen, Hinweis auf dem
PDF), Folgerechnung nur ueber die offenen Positionen (genau einmal, Bezug auf die Teilrechnung), Sperren gegen
Doppelabrechnung, Storno-Reihenfolge, To-do mit Telegram-Erinnerung am Termin, Belegverfolgung, Finanz-Cockpit.

## Nicht-Scope

Teilrechnungen ueber Vorkasse-Rechnungen; mehrere Folgerechnungen je Teilrechnung; automatisches Anfragen der
Verkaufszahlen beim Kunden (Mail = CEO-Tor).

## Etappen

### T1 Teilrechnung und Folgerechnung (mittel, Risiko niedrig) -- verifiziert 2026-11-14 (RE-2026-0003)
- **Stand:** Position mit `spaeter_am` (`angebote._positionen`), Summe ohne diese Positionen (`angebote.summen`, Feld
  `spaeter`), PDF-Hinweis (`spaeter_hinweis`), Rechnung mit `teil` {abrechnung_am, positionen}, Folgerechnung mit `folge_zu`
  (`RechnungStore.folgerechnung`, `POST /api/finanzen/rechnungen/<nr>/folgerechnung`), Ereignis `rechnung_teil_aufgabe`
  (To-do „Rest abrechnen“ in `todos/log.jsonl`, wird mit der Folgerechnung abgehakt), Belegverfolgung „Rest abgerechnet in“,
  Finanz-Cockpit-Stufe „Rest spaeter abrechnen“, Editor/Detail/Liste in LUNA-OS.
- **Gate:** `orchestrator/tests/test_teilrechnung.py` (7 Tests: Summe, Wortlaut im PDF, Gegenproben Vergangenheit/ohne
  Datum, genau eine Folgerechnung, Storno-Reihenfolge, To-do angelegt und abgehakt; zwei Mutationsproben rot), Suite ohne
  neue rote Tests, Doku-Check gruen, PDF in beiden Layouts gesichtet, Editor am Rechner und iPhone (402 px) geprueft.

## Dokumentationspflicht

`projekt_changelog.md`, Status hier, `ROADMAP.md`, `docs/datenfluesse.md`, `docs/entscheidungs-register.md`.

## Definition of Done

Die echte Rechnung an Fantastic Frames ist als Teilrechnung versendet, das To-do fuer den 31.12.2026 steht, und die
Folgerechnung laesst sich am Termin erstellen. Der CEO nimmt ab.
