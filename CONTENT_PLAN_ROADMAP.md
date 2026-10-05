# Roadmap: Content-Plan (Kalender fuer Planung und Verwaltung)
- Status: geplant
- Stand: 2026-10-05
- Arbeitsbranch: `ai/plan-contentplan-allinkl`
- Basiscommit: `655f82a`
- Naechster Schritt: CEO-Go fuer C1-C3 abwarten (C4 Spielplan nach eigener Freigabe der Datenquelle).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Eigenen Content-Plan, wie in einem Kalender, anlegbar machen (als Planungs- und Verwaltungstool fuer unsere Firma).“
Entscheidungen: **eigene Postings planen**, **Kunden-Postings automatisch**, **Drehtermine**, **Spieltage und Anlaesse**;
Ansichten **Monat, Woche, Liste**.

## Analyse (read-only, 2026-10-05)

- Kunden-Postings gibt es je Auftragsposition (`core/postings.py`, IDs `<Auftrag>-P<Pos>-<Nr>`) -- aber nur mit
  **Veroeffentlichungsdatum** (nachdem es online ist), **kein geplantes Datum**.
- Drehtermine stehen im Drehplan der Konzept-Mappe (`core/konzept.py`, Feld `dreh`: Datum, Uhrzeit, Ort).
- Eigene Inhalte: Reel-Pipeline (Cutter, Freigabe), Content-Feed (Ideen/Entwuerfe in Supabase) -- ohne Kalender.
- CCO-Skill `content-kalender` beschreibt die Planungslogik (Kundentermine zuerst, Mix, Puffer).
- Spielplan: keine Datenquelle im System; Feiertage lassen sich ohne externen Dienst berechnen.

## Etappe C1: Eintraege und Kalender

- Status: geplant
- Ziel / Scope: eigene Plan-Eintraege (Datum, optional Uhrzeit, Kanal, Format, Thema/Titel, Status Idee -> Skript ->
  gedreht -> geschnitten -> geplant -> online, Notiz, optional Bezug Kunde/Auftrag) in der Buchhaltungs-Kette
  (Ereignisse `plan_*`, nachvollziehbar); neue Seite „🗓 Content-Plan“ unter Content & Collabs mit **Monat**, **Woche**
  und **Liste** (iPhone startet in der Liste), Eintrag per Tipp anlegen/aendern/verschieben, Filter nach Kanal/Status.
- Gate: Tests; Browsertest Rechner/iPad/iPhone 17 Pro.
- Aufwand: mittel bis gross.

## Etappe C2: Kunden-Postings und Drehtermine automatisch

- Status: geplant
- Ziel / Scope: Postings bekommen ein **geplantes Datum** (im Auftrag/Postings-Bereich setzbar); geplante und
  veroeffentlichte Kunden-Postings sowie Drehtermine aus der Konzept-Mappe erscheinen automatisch im Kalender (nur lesend,
  Klick oeffnet Auftrag/Konzept); ueberfaellige geplante Postings markiert.
- Gate: Tests (Quellen zusammengefuehrt, keine Doppelungen); Browsertest.
- Aufwand: mittel.

## Etappe C3: Anlaesse

- Status: geplant
- Ziel / Scope: gesetzliche Feiertage (Hamburg, lokal berechnet) und eigene Anlaesse/Kampagnen-Zeitraeume (von-bis) als
  Hintergrund im Kalender; LUNA kann auf Wunsch einen Wochenplan vorschlagen (CCO-Skill `content-kalender`, nur Entwurf).
- Gate: Tests; Browsertest.
- Aufwand: klein bis mittel.

## Etappe C4: Spieltage (eigene Freigabe der Datenquelle)

- Status: geplant
- Ziel / Scope: HSV-Spielplan automatisch (Datenquelle wird vorher bewertet und im Entscheidungs-Register festgehalten,
  z. B. eine freie Fussball-Daten-Schnittstelle oder ein Kalender-Abo); bis dahin Spieltage als Anlass von Hand.
- Gate: CEO-Freigabe der Quelle (neuer externer Dienst), Eintrag in `docs/datenfluesse.md`.
- Aufwand: klein.

## Nicht-Scope

Kein automatisches Posten (CEO-Tor Oeffentlichkeit); keine Synchronisation in fremde Kalender in dieser Roadmap
(spaeter moeglich, z. B. Google-Kalender von LUNA).

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md`, `docs/entscheidungs-register.md`.

## Definition of Done

Eigene und Kunden-Postings, Drehtermine und Anlaesse stehen in einem Kalender mit Monat/Woche/Liste, auf allen Geraeten
bedienbar.
