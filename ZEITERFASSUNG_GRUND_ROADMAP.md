# Roadmap: Grund der Arbeitszeit und Zeiten nachtragen

- Status: geplant
- Stand: 2026-10-09
- Arbeitsbranch: `ai/zeitgrund-partnerliste`
- Basiscommit: `a680e53`
- Naechster Schritt: CEO-Go fuer Z1 und Z2 abwarten (Gruende bestaetigen).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-09)

„Grund fuer Zeiterfassung mit aufnehmen (Dreharbeiten, Postproduktion und Schnitt). Manuelles Nachbuchen von Zeiten im
System ermoeglichen.“

## Analyse (read-only, 2026-10-09)

- `core/zeiterfassung.py`: Feld `taetigkeit` gibt es schon, aber als **Freitext** (max. Laenge, Vorschlaege = die drei
  zuletzt benutzten). Telegram fragt nach dem Stopp „Was hast du gemacht?“ mit Knoepfen aus diesen Vorschlaegen
  (Standard „Dreh“, „Schnitt“, „Abstimmung“, `channels/telegram/bot.py` `_zeit_taet_frage`).
- Von Hand eintragen geht heute **nur im Auftrag** (aufgeklappter Bereich „+ Zeit von Hand eintragen“ unter
  „Zeiten & Nachkalkulation“, Endpunkt `POST /api/finanzen/zeit/eintrag`). Das zentrale Fenster „⏱ Zeiterfassung“
  (Start/Stopp/Auswertung) hat **kein** Nachtragen; Telegram auch nicht.
- Live (NAS, 2026-10-09): 1 Zeiteintrag in 2026 (6:31 h), ohne Taetigkeit -> keine Altdaten-Umstellung noetig.
- Auswertung gruppiert schon „je Taetigkeit“ -> feste Gruende machen sie sofort aussagekraeftig.

## Etappe Z1: Feste Gruende statt Freitext

- Status: geplant
- Ziel / Scope: Auswahl **Grund** mit festen Werten (Empfehlung): **Dreharbeiten**, **Postproduktion & Schnitt**,
  **Konzept & Abstimmung**, **Sonstiges** (bei Sonstiges kurzer Text). Pflicht beim Nachtragen und Korrigieren; beim
  Stoppen fragt LUNA (OS und Telegram-Knoepfe mit genau diesen Gruenden). Alte Freitexte bleiben lesbar und werden in der
  Auswertung als „Sonstiges: …“ gezeigt. Liste der Gruende zentral im Code (spaeter in den Einstellungen erweiterbar).
- Nicht-Scope: Stundensaetze je Grund; Anzeige beim Kunden (Zeiten bleiben intern, nie im PDF).
- Gate: Tests (Pflicht, Telegram-Knoepfe, Auswertung je Grund, alte Freitexte, Gegenprobe rot); Browser Rechner/iPad/iPhone.
- Risiko / Rueckweg: nur Eingabe und Anzeige; Ereignisse bleiben additiv (`taetigkeit` + neues Feld `grund`).
- Aufwand: klein.

## Etappe Z2: Zeiten nachtragen ueberall

- Status: geplant
- Ziel / Scope: Im Fenster „⏱ Zeiterfassung“ Knopf **„+ Zeit nachtragen“** (Auftrag waehlen, Datum, von-bis oder Dauer,
  Pause, Grund, optional km); im Auftrag den Bereich sichtbarer machen (Knopf statt eingeklapptem Text). Telegram:
  „Gestern 3 Stunden Schnitt fuer CR Container“ bzw. „09.10. 10-14 Uhr Dreh AB-2026-0001“ -> LUNA zeigt die erkannte Zeit
  mit Knopf „✅ Eintragen“ (nichts ohne Bestaetigung). Nachgetragene Zeiten sind als „von Hand“ markiert (wie heute).
- Nicht-Scope: Zeiten fuer bereits abgerechnete Projektzeiten aendern (bleibt gesperrt).
- Gate: Tests (Erkennung der Telegram-Saetze, Bestaetigung Pflicht, Gegenprobe); Browsertest.
- Risiko / Rueckweg: Telegram-Erkennung regelbasiert (kein LLM noetig); Rueckweg = Commit zuruecknehmen.
- Aufwand: klein bis mittel.

## Nicht-Scope

Keine Buchung, keine EUeR-Wirkung (Zeiten bleiben kalkulatorisch); keine Zeiten in Kunden-PDFs.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md`, `docs/datenfluesse.md` (Z2 Telegram).

## Definition of Done

Jede Zeit hat einen Grund aus der festen Liste, die Auswertung zeigt Stunden je Grund, und Zeiten lassen sich im
Zeiterfassungs-Fenster, im Auftrag und per Telegram nachtragen.
