# Roadmap: Beleg in einer Ebene (Formular an der Stelle des Blatts, gesperrt nur lesen)

- Status: geplant
- Stand: 2026-10-05
- Arbeitsbranch: `ai/beleg-eine-ebene`
- Basiscommit: `5cdb129`
- Naechster Schritt: CEO-Go fuer E1 (Rechnung) abwarten.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Bekommen wir es sauber hin, dass die Seite, die sich oeffnet, wenn ich in einem Beleg auf Bearbeiten druecke, immer da
angezeigt wird, wo jetzt die PDF ist, man aber nichts aendern kann, solange der Beleg gesperrt ist? Quasi beide Ebenen
zusammenbringen.“ Entscheidungen: **Formular an der Stelle des Blatts + Umschalter „Vorschau“** fuer das Belegblatt;
gilt fuer **Angebot, Auftrag und Rechnung**.

## Analyse (read-only, 2026-10-05)

- Heute zwei Ebenen: die Detailansicht (`anDetail`, `abDetail`, Rechnungsdetail) zeigt das Belegblatt
  (`belegAnsicht` mit `haupt` = Blatt, `seite` = Status/Aktionen; DIGITALER_BELEG D1-D3); „✎ Bearbeiten“ oeffnet
  zusaetzlich ein eigenes ganzseitiges Fenster mit dem Formular (`anEditor`, `reEditor` per `openModal(…, true)`).
- Bearbeitbar ist heute nur der Entwurf: Angebot im Status `entwurf`, Rechnung als Entwurf (vor dem Festschreiben). Der
  Auftrag hat kein Bearbeiten-Formular (nur beim Anlegen ohne Angebot, `abEditorUmbauen`).
- Das Server-Gate bleibt unveraendert: Aenderungen an versendeten/festgeschriebenen Belegen lehnt der Server schon heute
  ab -- die Sperre in der Oberflaeche ist nur Darstellung, keine neue Schutzschicht.
- DIGITALER_BELEG hatte „kein neuer Editor“ als Nicht-Scope; diese Roadmap baut ebenfalls keinen neuen Editor, sondern
  bettet den vorhandenen in die Detailansicht ein.

## Grundsatz

- Ein Beleg = eine Seite: oben die Aktionen, links das Formular (Entwurf: aenderbar; gesperrt: alle Felder nur lesen,
  ohne Neue Position/Entfernen/Speichern), rechts die Seitenleiste wie heute (Status, Verfolgung, Versand).
- Umschalter **Formular | Vorschau** ueber dem Inhalt; Vorschau = das heutige Belegblatt. Die Wahl merkt sich das Geraet.
- Gesperrt-Hinweis im Formular: z. B. „🔒 Versendet am … – nur lesen“ / „🔒 Festgeschrieben – Korrektur ueber
  Stornorechnung“.
- Neu anlegen (Neues Angebot, Neue Rechnung, Auftrag ohne Angebot) bleibt das ganzseitige Fenster wie heute.

## Etappe E1: Rechnung

- Status: geplant
- Ziel / Scope: Formular-Baustein aus `reEditor` so umbauen, dass er in einen Container der Detailansicht rendert
  (statt eigenes Fenster) und einen Nur-lesen-Modus kennt; Rechnungsdetail zeigt Formular + Umschalter Vorschau; „✎
  Bearbeiten“ entfaellt; Speichern bleibt im Beleg (danach Ansicht aktualisiert, nicht geschlossen). Festgeschriebene,
  stornierte und Korrektur-Rechnungen: nur lesen. Preis-mit-Grund, TKP je Position, Neue Position wie heute.
- Nicht-Scope: keine Aenderung an Server, Nummern, PDF, Kette; Mahnung bleibt reines Blatt.
- Gate: Tests (Server-Sperre unveraendert, Gegenprobe); Browsertest Rechner 1300 / iPad 820 / iPhone 17 Pro (Entwurf und
  festgeschrieben, Umschalter, nichts ausserhalb des Bildschirms).
- Verifikation: Browser-Szenario „festgeschrieben“ -> erwartet: 0 bedienbare Eingabefelder, keine Speichern-/Positions-Knoepfe.
- Risiko / Rueckweg: Umbau der Editor-Funktion; Rueckweg = Commit zuruecknehmen (nur Oberflaeche).
- Aufwand: mittel.

## Etappe E2: Angebot und Auftrag

- Status: geplant
- Ziel / Scope: dasselbe fuer das Angebot (`anEditor`; Entwurf aenderbar, ab versendet nur lesen) und den Auftrag (immer
  nur lesen: Positionen/Konditionen der Auftragsbestaetigung als Formular, Reiter Konzept/Postings/Zeiten/Bericht bleiben).
- Gate/Verifikation wie E1.
- Aufwand: mittel.

## Etappe E3: Feinschliff

- Status: geplant
- Ziel / Scope: Umschalter-Gedaechtnis je Geraet, Tastatur/Fokus, iPhone-Feinschliff, Aufraeumen der alten
  Bearbeiten-Wege (Handlungsbedarf-/Verlinkungen, die noch das Fenster oeffnen).
- Gate: Browsertest aller drei Belegarten.
- Aufwand: klein.

## Nicht-Scope

Kein neuer Editor, keine neuen Felder, keine Aenderung an Server-Regeln, PDFs, Nummern oder Buchungen; Mahnungen,
Eingangs-/Eigenbelege bleiben wie sie sind.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md`, `docs/bekannte-fehler.md`.

## Definition of Done

Angebot, Auftrag und Rechnung haben nur noch eine Ansicht: Formular an der Stelle des Blatts, im Entwurf aenderbar,
gesperrt nur lesen, Vorschau per Umschalter -- auf Rechner, iPad und iPhone.
