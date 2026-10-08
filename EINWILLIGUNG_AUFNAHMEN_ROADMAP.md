# Roadmap: Einwilligung in Video-/Bildaufnahmen -- Vorlage und Unterschrift am iPad

- Status: in Umsetzung
- Stand: 2026-10-08
- Arbeitsbranch: `ai/einwilligung-aufnahmen`
- Basiscommit: `cff22ad`
- Naechster Schritt: E1-E3 gebaut (2026-10-08) -- Deploy, Vorlage Version 1 im Vertragswerk anlegen, Probe am echten iPad durch den CEO, anwaltliche Pruefung vor dem ersten Einsatz.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-08)

„Wir brauchen eine Moeglichkeit, eine Erlaubnis zur Anfertigung von Videoaufnahmen von Personen einzuholen … Vertragsentwurf
anlegen … am iPad im System oeffnen, der Kunde unterschreibt mit dem Apple Pencil; gespeichert und am Auftrag als
unterschriebene PDF abgelegt; pro Auftrag mit verschiedenen Personen; Datum vorbelegt mit dem Tag, an dem ich es oeffne;
Personendaten per Tastatur, Unterschriftsfeld fuer den Apple Pencil.“

## Recherche (2026-10-08, Web; keine Rechtsberatung)

- Rechtsgrundlagen: Recht am eigenen Bild (§ 22 KUG) und Datenschutz (Art. 6 Abs. 1 lit. a, Art. 7 DSGVO); Einwilligung
  freiwillig, informiert, fuer einen **konkret benannten Zweck**, getrennt von anderen Erklaerungen, jederzeit fuer die
  Zukunft widerrufbar (Art. 7 Abs. 3 DSGVO), Widerruf so einfach wie die Erteilung; schon Veroeffentlichtes laesst sich
  im Netz oft nicht vollstaendig zurueckholen -- darauf hinweisen.
- Alternative „Model Release“ (Vertrag mit Rechteeinraeumung, ggf. gegen Verguetung): weniger frei widerrufbar, Grundlage
  Art. 6 Abs. 1 lit. b DSGVO -- sinnvoll bei bezahlten Darstellern. Fuer Gaeste/Mitarbeitende des Kunden: Einwilligung.
- Minderjaehrige: Erziehungsberechtigte unterschreiben (bei gemeinsamem Sorgerecht moeglichst beide), ab 14 zusaetzlich
  der/die Minderjaehrige; ab 16 je nach Quelle allein. Beschaeftigte des Kunden: Freiwilligkeit besonders beachten
  (§ 26 BDSG), Einwilligung schriftlich oder elektronisch.
- Form: Die DSGVO verlangt keine Schriftform; entscheidend ist der **Nachweis** (Art. 7 Abs. 1). Eine Unterschrift am
  Tablet mit Zeitstempel, Textfassung und Person ist ein brauchbarer Nachweis (einfache elektronische Signatur); eine
  qualifizierte Signatur braucht es nur bei gesetzlicher Schriftform (nicht hier).
- Typische Inhalte: Verantwortlicher + Kontakt, Person (Name, Anschrift, Geburtsdatum), Projekt/Auftraggeber, Ort/Datum,
  Zweck und Kanaele (eigene Social-Media-Kanaele, Kanaele des Auftraggebers, bezahlte Werbung, Website, Print), Umfang
  (Bild, Stimme, Namensnennung), Bearbeitung/Schnitt, Dauer bis Widerruf, Widerrufsweg und -wirkung, Verguetung (keine/
  Betrag), Datenschutzhinweise, Freiwilligkeit, Kopie fuer die Person.
- Quellen u. a.: WD 10 - 3000 - 038/18 (Bundestag), Mustererklaerungen Uni Luebeck/Bamberg, GF-Leitlinien,
  DLRG-Merkblatt, dr-datenschutz.de/versicherungsbote.de (Tablet-Unterschrift).

## Etappe E1: Vorlage „Einwilligung in Bild- und Videoaufnahmen“ im Vertragswerk

- Status: umgesetzt
- Ziel / Scope: neue Vorlagenart `einwilligung` im Vertragswerk (Version 1, Entwurf, anwaltliche Pruefung erforderlich)
  mit den Inhalten oben, ankreuzbaren Zwecken/Kanaelen, Abschnitt Minderjaehrige und Datenschutzhinweisen; optionaler
  Abschnitt Verguetung (Model Release). Kurz und auf einer Seite lesbar.
- Gate: Tests (Vorlage vorhanden, Versionierung wie die anderen), Doku.

## Etappe E2: Einwilligung am iPad aufnehmen und am Auftrag ablegen

- Status: umgesetzt
- Ziel / Scope: im Auftrag Knopf „✍️ Einwilligung aufnehmen“ -> ganzseitiges Formular (iPad quer/hoch und iPhone):
  Vorlagentext, Personendaten per Tastatur (Name, Anschrift, Geburtsdatum, optional Mail/Telefon), Zwecke vorbelegt aus
  dem Auftrag (anpassbar), Datum = Tag des Oeffnens, **Unterschriftsfeld fuer den Apple Pencil** (auch Finger/Maus,
  „Neu unterschreiben“), bei unter 16 Jahren zusaetzlich Erziehungsberechtigte(r) mit eigener Unterschrift.
  „Speichern“ erzeugt eine **PDF A4 hochkant** (Text der verwendeten Vorlagenversion, Daten, Unterschrift(en), Zeitstempel,
  Pruefsumme) und legt sie **am Auftrag** ab; beliebig viele Personen je Auftrag, Liste mit Datum/Name/PDF im Auftrag.
  Nachweis in der Kette (Ereignis `einwilligung_erteilt`, ohne Unterschriftsbild im Log).
- Gate: Tests (Pflichtfelder, Unterschrift noetig, PDF, Ablage, mehrere Personen, Rechte nur CEO/Team mit Modul),
  Browsertest mit Touch-Simulation; Probe am echten iPad durch den CEO.

## Etappe E3: Kopie fuer die Person und Widerruf

- Status: umgesetzt
- Ziel / Scope: Kopie der PDF per Mail an die Person (nur per Klick, aus luna@, Textbaustein „Einwilligung“);
  Widerruf vermerken (Datum, Weg) -> am Auftrag und bei den Postings sichtbar („Person X hat widerrufen – nicht mehr
  verwenden“), Erinnerung, betroffene Inhalte zu pruefen.
- Gate: Tests, Browsertest.

## Entscheidungen CEO (vor E2)

1. **Ablage:** Empfehlung -- nur auf der NAS (mit Backup), **nicht** in LUNAs Google Drive (personenbezogene Daten
   Dritter so wenig wie moeglich verteilen).
2. **Einsatz:** Das Formular ist ein Entwurf. Empfehlung -- vor dem ersten echten Einsatz von der Anwaeltin pruefen
   lassen (wie die anderen Vorlagen; CEO-Tor Recht).

## Umsetzung (2026-10-08, Go CEO, beide Empfehlungen angenommen)

- E1: Vorlagenart `einwilligung` im Vertragswerk; Entwurf (8 Paragraphen: Gegenstand, Zwecke, Umfang/Bearbeitung inkl.
  keine KI-Veraenderung ohne Zustimmung, Dauer/Widerruf, Verguetung, Freiwilligkeit, Minderjaehrige, Datenschutzhinweise)
  in `core/vertrag_entwuerfe.py`; Zwecke zum Ankreuzen in `core/einwilligungen.ZWECKE`.
- E2: `core/einwilligungen.py` (EinwilligungStore, PDF A4 hochkant mit Vorlagentext, Zwecken, Personendaten,
  Unterschrift(en), Nachweis-Fuss mit Vorlagenversion/Zeitstempel, SHA-256 im Log); Ablage `einwilligungen/` nur NAS
  (vom Deploy ausgenommen, im Backup: Log + PDFs), nicht Kette/Drive. Endpunkte `/api/crm/auftraege/<nr>/einwilligungen`
  (Liste/Anlegen, Modul crm), `/api/crm/einwilligungen/<id>/pdf`. Oberflaeche: Knopf „✍️ Einwilligung aufnehmen“ im
  Auftrag, ganzseitiges Formular mit Unterschriftsfeld (Pointer Events, Apple-Pencil-Druck, „Neu unterschreiben“),
  Erziehungsberechtigte ab Geburtsdatum unter 16 (unter 14 nur Eltern), Liste „Einwilligungen“ am Auftrag.
- E3: Kopie per Mail (Textbaustein „Einwilligung (Kopie)“, nur per Klick, Modul finanzen), Widerruf vermerken
  (Datum, Weg, Notiz) -> Liste durchgestrichen + rote Warnung im Reiter Postings.
- Tests `test_einwilligungen.py` (6, Gegenprobe Minderjaehrige rot), Browser iPad quer/hoch, iPhone, Rechner.
- Nachtrag (CEO 2026-10-08): Haken „✉️ Kopie an die Person senden“ im Formular (erscheint mit der Mailadresse, bei gueltiger
  Adresse vorbelegt) -> beim Speichern geht die Kopie mit dem Textbaustein direkt raus; Versandfehler blockieren das
  Speichern nie (Hinweis + spaeter „✉️ Kopie …“); nur mit Modul Finanzen.

## Nicht-Scope

Keine E-Signatur-Plattform (Register 2026-10-05), keine qualifizierte Signatur, keine Gesichtserkennung oder
automatische Zuordnung von Personen zu Clips.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md`, `docs/datenfluesse.md`,
`docs/datenschutz-ki-nutzung.md`, `docs/bekannte-fehler.md`.

## Definition of Done

Vor dem Dreh am iPad: Person traegt sich ein, unterschreibt mit dem Pencil; die unterschriebene PDF liegt am Auftrag,
fuer jede Person einzeln, mit Kopie und Widerrufs-Vermerk.
