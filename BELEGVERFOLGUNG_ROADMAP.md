# Roadmap: Belegverfolgung (Belegkette als Zeitstrahl in jeder Belegart)
- Status: in Umsetzung
- Stand: 2026-10-03
- Arbeitsbranch: `ai/belegverfolgung`
- Basiscommit: `fd77aa7`
- Naechster Schritt: B1+B2 gebaut (2026-10-03); Deploy + gemeinsamer Test mit PROJEKTZEITEN/PROJEKTBERICHT, Abnahme an AB-2026-0001.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-03)

„In jeder Belegart soll es den Punkt ‚Belegverfolgung‘ geben. Wenn man diese oeffnet, sieht man, welche Belege vor
dem Beleg existieren und welche danach -- miteinander verbunden, wie auf einem Zeitstrahl. Diese Belege sollen sich
darueber auch oeffnen lassen. So wird der Zusammenhang der Belege deutlicher.“

## Analyse (read-only, 2026-10-03)

- **Belegarten mit Nummer** (Hash-Kette, `bh.mit_nummer`/`bh.festschreiben`): Angebot `AN`, Auftrag `AB`, Rechnung
  `RE` (Arten Rechnung, Vorkasse, Schlussrechnung, Storno), Altrechnung `RG-…`, Mahnung `MA`, Eingangsbeleg `ER`,
  Eigenbeleg `EB`; dazu Rechnungsentwuerfe `E-…` (ohne Nummer).
- **Vorhandene Verknuepfungen** (alle schon gespeichert, nichts muss nachgetragen werden):
  - Auftrag -> Angebot (`angebot`), Rechnung -> Auftrag/Angebot (`auftrag`, `angebot`), Storno -> Original (`bezug`),
    Schlussrechnung -> Vorkasse (`abzuege`), Mahnung -> Rechnung (`rechnung`), Mahnverfahren -> Rechnung,
    Zahlungen an der Rechnung, Lieferungen und Projektbericht am Auftrag, Firmenakte-Dokumente mit `bezug`
    (z. B. Anwaltsschreiben zu `RG-11052026`), Abo-Faelligkeit -> Eigenbeleg (`beleg`).
  - **Luecke:** Ein Korrektur-Entwurf nach Storno weiss nicht, welche Rechnung er ersetzt -- nur ueber den gleichen
    Auftrag ableitbar (Altrechnungen ohne Auftrag: gar nicht). Neu: Feld `korrektur_zu` beim Anlegen.
- **Live-Umfang** (API, 2026-10-03): 2 Angebote, 2 Auftraege, 6 Rechnungen (3 Altrechnungen `RG`, eine echte Kette
  `AN-2026-0001 -> AB-2026-0001 -> RE-2026-0001 -> Storno RE-2026-0002 -> RE-2026-0003`), Mahnungen und Mahnverfahren
  zu `RG-11052026`.
- **Eingangsseite:** `ER`/`EB` haengen nicht an Kundenbelegen; verbunden sind dort nur Zahlungsnachweis/Quittung,
  Abo (gleiche Abo-Nummer) und Firmenakte-Dokumente.

## Etappe B1: Belegkette ermitteln (Kern + Schnittstelle)

- Status: umgesetzt (2026-10-03) -- `core/belegverfolgung.py`, Endpunkt `GET /api/crm/belege/<nummer>/verfolgung`,
  `korrektur_zu` an Korrektur-Entwurf und -Rechnung (Altfaelle abgeleitet), Reihenfolge am selben Tag nach der Kette.
  Tests `test_belegverfolgung.py` mit Gegenprobe.
- Ziel / Scope: `core/belegverfolgung.py` -- von einem beliebigen Beleg aus alle verbundenen Belege und Ereignisse
  sammeln (Graph ueber die Verknuepfungen oben), je Knoten Art, Nummer, Titel, Datum, Betrag, Status und wie er sich
  oeffnen laesst; Kanten mit Beschriftung („aus Angebot“, „Rechnung zu“, „storniert durch“, „ersetzt durch“, „Mahnung
  zu“, „Dokument zu“); nach Datum sortiert, Ausgangsbeleg markiert („vorher“/„nachher“). Endpunkt
  `GET /api/belege/<nummer>/verfolgung` (Rechte je Belegart wie heute: Rechnungen/Eingang nur Modul finanzen).
  Neu: `korrektur_zu` am Korrektur-Entwurf.
- Gate: Tests -- Kette AN -> AB -> Vorkasse -> Schlussrechnung; Storno -> Korrektur; Mahnstufen -> Mahnverfahren;
  Altrechnung mit Akte-Dokument; gleiche Kette von jedem Glied aus; keine fremden Belege
  (andere Firma); Rechte.
- Aufwand: mittel.

## Etappe B2: „🔗 Belegverfolgung“ in jeder Belegart (Zeitstrahl)

- Status: umgesetzt (2026-10-03) -- Knopf in Angebot, Auftrag, Rechnung (alle Arten, auch Entwurf) und je Mahnung;
  Zeitstrahl ab 900 px waagerecht (durchgehende Spur, aktueller Beleg in die Mitte gerollt), darunter senkrecht;
  Browsertest 1300/820/390 px.
- Ziel / Scope: Knopf in Angebot, Auftrag, Rechnung (auch Entwurf, Vorkasse, Storno, Altrechnung) und Mahnung.
  Fenster mit Zeitstrahl (Rechner waagerecht, iPad/iPhone senkrecht): „vorher“, hervorgehoben der aktuelle Beleg, „nachher“;
  Knoten mit Symbol, Nummer, Datum, Betrag, Status; Verbindungslinien mit Beschriftung; Klick oeffnet den Beleg
  (Rueckweg ueber die Belegverfolgung des neuen Belegs).
- Gate: Browsertest Desktop 1300 px, iPad 820 px, iPhone 390 px (kein Ueberlauf, Klick oeffnet); Tests aus B1 gruen.
- Aufwand: mittel.

## Nicht-Scope

Keine Aenderung bestehender Belege oder Nummern; keine neuen Verknuepfungen rueckwirkend erfinden (nur ableiten, was
gespeichert ist); Eingangsbelege werden nicht automatisch Kundenbelegen zugeordnet.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (neuer Endpunkt, Feld
`korrektur_zu`), `docs/entscheidungs-register.md` (Entscheidungen unten).

## CEO-Entscheidungen

1. **Umfang:** Belege mit Nummer als grosse Punkte **plus** Ereignisse (Zahlungen, Lieferung, Projektbericht,
   Mahnverfahren, Firmenakte-Dokumente) als kleine Punkte.
2. **Darstellung:** am Rechner **waagerecht** (links frueher, rechts spaeter; lange Ketten seitlich scrollbar, der
   aktuelle Beleg wird beim Oeffnen in die Mitte gerollt), auf iPad/iPhone senkrecht.
3. **Eingangs-/Eigenbelege:** keine Belegverfolgung -- der Knopf gibt es nur bei Kundenbelegen (Angebot, Auftrag,
   Rechnung inkl. Entwurf/Vorkasse/Storno/Altrechnung, Mahnung).

## Definition of Done

B1 und B2 verifiziert (Desktop und Mobil) und vom CEO an der echten Kette AB-2026-0001 abgenommen.
