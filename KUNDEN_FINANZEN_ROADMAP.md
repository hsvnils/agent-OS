# Roadmap: Kunden, Angebote, Rechnungen und Finanzen in LUNA-OS

- Status: in Umsetzung
- Stand: 2026-09-29
- Arbeitsbranch: `ai/kunden-finanzen`
- Basiscommit: `649a974`
- Naechster Schritt: Etappe 14 deployen (Go), dann live `stammdaten/zuordnen` (erst Probe) und Erstbefuellung der
  Lieferanten aus den Belegen; Etappe 13: CEO-Abnahme beim Buchen, erste echte Auto-Weiterleitung pruefen.
  Abnahme Etappen 9-11 (Export/PDF, Verfahrensdokumentation freigeben, Mahnung durchspielen, eine
  gemischte Rechnung aufteilen); Deploy + Abnahme Etappe 12 (Barter-Deal einmal von Angebot bis Ware-Eingang
  durchspielen). Etappe 3c wartet auf Meta-Exporte. Offen aus Etappe 6: Live-Probe der OCR mit einem fotografierten Beleg.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-09-27)

Ein durchgehender, detaillierter Geschaeftsprozess **in LUNA-OS im Web** (nicht primaer ueber Telegram):

**Kunde (CRM) -> Angebot -> Beauftragung -> Rechnung -> Zahlung -> Finanzen/EUeR.**

- **CRM** fuer Kooperationspartner **und** weitere Kunden sowie Lieferanten. **Jede Firma hat eine Firmenkundennummer,
  jeder Ansprechpartner eine eigene Ansprechpartner-Nummer.**
- **Angebote** erstellen, ablegen, nachfassen (Kalender-Erinnerungen); aus einem angenommenen Angebot wird eine
  **Beauftragung** (Auftragsbestaetigung), daraus die **Rechnung** — alles verknuepft mit Kunde und Ansprechpartner.
- **Rechnungen** mit fortlaufender Rechnungsnummer, abgelegt und sortiert; **Eingangsrechnungen** fuer Einkaeufe der Firma.
- **Finanzen:** das Jahr ueber die wichtigsten Zahlen sehen; am Jahresende direkt die **EUeR** machen (lassen).
- Steuerlich: **Kleinunternehmer nach § 19 UStG**, Gewinnermittlung per EUeR. **Eigenbau**, keine Fremdsoftware.

## Register und bekannte Fehler (B3)

- Register: „CRM als File-Store (JSONL), kanalagnostisch" (BESCHLOSSEN 2026-07-01) — wird hier erweitert, nicht ersetzt.
  Zu Buchhaltungssoftware, Rechnungen, Angeboten gibt es **keine** Vorentscheidung.
- Bekannte Fehler: keine direkt betroffen; zu beachten: Doku-Check-Pflichten fuer neue Speicher (BF-03/BF-04-Lehre),
  Deploy-Schutz, Backup.

## Analyse (Belege, 2026-09-27)

### Bestand im Code

- **CRM** (`orchestrator/core/crm.py`): append-only JSONL `crm/log.jsonl`, Write-through nach Supabase `crm_companies`,
  `crm_messages`, `crm_todos`. **Kein eigenes Firmen-Objekt:** Identitaet ist nur der Anzeigename (`_key = name.lower()`),
  keine Nummer, keine Adresse, keine Ansprechpartner, keine Aliase (Instagram-Handle und Mail-Absender derselben Firma
  bleiben getrennt). Pipeline-Stufen `neu|in_gespraech|angebot|vereinbart|abgelehnt` sind kooperationsspezifisch.
  Oberflaeche: LUNA-OS V2 `renderCrm` (Pipeline/Timeline), Schreib-API nur fuer Status und To-dos.
- **Finanzen heute:** nur KI-Kosten (`core/kosten.py`, `finance/kosten-log.jsonl`) und Monatsbudget. Keine Einnahmen,
  Ausgaben, Belege. Investment-Depot (`investment/store.py`) ist ein gutes **Vorbild fuer ein Hauptbuch**: Buchungen als
  Ereignisse, Korrektur nur per Storno-Ereignis mit Bezug, Bestand per Faltung.
- **Keine PDF-Bibliothek** (Docker-Image und `.venv`), kein PDF-Code. **Mail-Anhaenge** gehen nicht (`google_workspace._mime`
  nur Text). Kalender: `termin_anlegen` ohne Erinnerungs-/Ganztags-Option. Drive: nur Textdateien.
- **Backup** sichert nur einzeln gelistete JSONL-Dateien, keine Beleg-Ordner. `finance/` ist vom Deploy nur teilweise
  ausgenommen -> neues Verzeichnis `buchhaltung/` statt `finance/`.
- **LUNA-OS:** neue App = Eintrag in `SECTIONS` + `RENDER.<id>` (`static/app-v2.js`); Rechte ueber Module
  (`core/team_auth.py`) — ein neues Modul `finanzen` darf standardmaessig nur der Owner sehen.
- **Mandate:** CRO = Umsatz, Vertrieb, Angebots-Entwurf („Lead -> Angebot -> CEO-Freigabe"); CFO = Kosten, Budget,
  Finanzberichte, ausdruecklich **keine Buchungen autonom**; CLO = Vertragsentwuerfe. Buchhaltung/EUeR stehen in keinem
  Mandat -> Charta-Erweiterung CFO (nur HoA auf CEO-Anweisung, mit Diff).

### Rechtsrahmen (Recherche 2026-09-27, Quellen im Changelog-Eintrag; [?] = vor Umsetzung gegenpruefen)

- **§ 19 UStG ab 2025:** Grenzen 25.000 EUR Vorjahr / **100.000 EUR laufendes Jahr — bei Ueberschreiten endet der Status
  sofort**. Umsatzsteuer darf **nie** ausgewiesen werden (sonst geschuldet nach § 14c). Pflicht-Hinweis auf die
  Steuerbefreiung (UStAE 14.7a).
- **Rechnung:** vereinfachte Rechnung nach **§ 34a UStDV** (Name/Anschrift beider Seiten, Steuernummer oder USt-IdNr.,
  Ausstellungsdatum, Menge/Art der Leistung, Entgelt + Befreiungshinweis). Rechnungsnummer und Leistungsdatum sind dort nicht
  Pflicht — **wir fuehren sie trotzdem** (GoBD-Nachvollziehbarkeit, sofortiger Wechsel bei Grenzueberschreitung).
- **E-Rechnung:** Kleinunternehmer duerfen **dauerhaft PDF** ausstellen (§ 34a S. 2 UStDV, BMF 15.10.2025), muessen aber seit
  2025 **E-Rechnungen empfangen** koennen (XRechnung/ZUGFeRD ab Profil EN16931 [?]); XML im Original aufbewahren.
- **GoBD** (BMF 28.11.2019, 2. Aenderung 14.07.2025): Unveraenderbarkeit ab Erfassung, Korrekturen protokolliert und
  erkennbar, Verfahrensdokumentation Pflicht, Datenzugriff der Finanzverwaltung (§ 147 Abs. 6 AO). Eigenbau zulaessig,
  Verantwortung beim Steuerpflichtigen.
- **Aufbewahrung** (BEG IV): Belege **8 Jahre**, Aufzeichnungen/Journal 10 Jahre, Geschaeftsbriefe (angenommene Angebote,
  Auftragsbestaetigungen) 6 Jahre; Frist ab Ende des Kalenderjahres.
- **EUeR:** Zufluss-/Abflussprinzip (Zahlungsdatum), 10-Tage-Regel fuer wiederkehrende Zahlungen um den Jahreswechsel [?],
  GWG bis 800 EUR (beim Kleinunternehmer Brutto-Anschaffungskosten gegen die Netto-Grenze pruefen), Sammelposten 250-1.000
  EUR, AfA, Anlageverzeichnis; Abgabe elektronisch ueber ELSTER (Zeilennummern jaehrlich aus der Anleitung [?]).

## Scope

LUNA-OS-Apps **Kunden** (CRM-Stammdaten), **Angebote & Auftraege**, **Rechnungen**, **Belege/Eingangsrechnungen**,
**Finanzen** (Cockpit + EUeR); GoBD-faehiger Buchhaltungs-Speicher; PDF-Erzeugung; Ablage/Backup; Kalender-Erinnerungen;
Mail-Entwurf mit Anhang; Export fuer Steuerberater/ELSTER.

## Nicht-Scope

- Automatischer Versand ohne CEO-Freigabe, Zahlungen ausloesen, Bankzugang per API (spaeter hoechstens eigenes CEO-Tor)
- Direkte ELSTER-Uebermittlung (ERiC) — Export als Eingabehilfe/CSV
- Regelbesteuerung/Umsatzsteuer-Voranmeldung (erst wenn die Kleinunternehmer-Grenze reisst — dann eigene Roadmap)
- LUNA-Chat-/Telegram-Werkzeuge (CEO: zuerst LUNA-OS im Web; spaeter optional)
- Schutzbereiche laut `governance/roadmap-workflow.md` B4

## Grundsaetze (gelten fuer alle Etappen)

- **Nummern:** Firmen `K-00001` (Firmenkundennummer, fortlaufend, nie wiederverwendet), Ansprechpartner `AP-00001`,
  Lieferanten ebenfalls mit Firmennummer (Typ „Lieferant"), Angebote `AN-2026-0001`, Auftraege `AB-2026-0001`, Rechnungen
  `RE-2026-0001`, Eingangsbelege `ER-2026-0001` (Nummernkreise je Jahr, lueckenlos, atomar vergeben). Format = CEO-Entscheidung.
- **Unveraenderbarkeit:** Buchhaltungs-Speicher append-only mit **Hash-Kette** (jeder Eintrag enthaelt den Hash des
  vorigen); Belege (PDF/XML) mit SHA-256 im Eintrag; **Festschreiben** einer Rechnung vergibt die Nummer und friert
  PDF + Daten ein; Korrektur nur per Storno-/Korrekturrechnung. Taegliche Pruefung der Kette (Manipulationsalarm).
- **Entwurf vs. festgeschrieben:** LUNA-OS erlaubt Entwuerfe frei zu bearbeiten; Festschreiben, Versand (Mail) und
  Loeschen sind Aktionen des CEO (Recht/Geld/Oeffentlichkeit).
- **Rechte:** neues Team-Modul `finanzen` (nur Owner/ausdruecklich freigegeben); Kunden/Angebote im Modul `crm`.
- **Kleinunternehmer-Waechter:** laufender Jahresumsatz gegen 100.000 EUR (Warnung ab 80 %), Vorjahr gegen 25.000 EUR.

## Entscheidungen (CEO, 2026-09-27)

1. **Nummernformate:** wie vorgeschlagen (`K-00001`, `AP-00001`, `AN-/AB-/RE-/ER-JJJJ-NNNN`).
2. **Firma fuer den Briefkopf:** Krueger Onlinehandel und Media, c/o Hanserautisch, Arthur-Soltau-Weg 7c, 22889 Tangstedt.
   Bankverbindung am 2026-09-27 geliefert und in `buchhaltung/firmendaten.json` auf der NAS abgelegt (nicht im Git).
   Steuernummer (Pflichtangabe § 34a UStDV) am 2026-09-28 geliefert und in `buchhaltung/firmendaten.json` auf der NAS
   eingetragen (nicht im Git); erscheint in der Fusszeile aller Dokumente (live geprueft).
3. **Zahlungseingaenge:** zum Start von Hand in LUNA-OS als bezahlt markieren; Kontoauszug-Import spaeter.
4. **PDF:** `fpdf2` ins Docker-Image (einmaliger Neubau).
5. **Kein Steuerberater:** einfache Gewinnermittlung aus den Einnahmen und Ausgaben des CEO -> Etappen 7 und 9 **schlank**
   (AfA/Anlageverzeichnis nur bei Bedarf, kurze Verfahrensdokumentation).
6. **Charta-Erweiterungen CFO/CRO:** ja — Diff wird vorgelegt, Anwendung erst nach Bestaetigung (AGENTS.md 3.3).

## Entscheidungen (Vorschlaege, Stand der Planung)

1. **Nummernformate** (Vorschlag oben) — so uebernehmen oder anpassen?
2. **Firmendaten fuer den Briefkopf:** Name, Anschrift, Steuernummer, Bankverbindung, Kontakt (liefert der CEO).
3. **Zahlungseingaenge:** in LUNA-OS von Hand als bezahlt markieren (Start) — oder Kontoauszug-CSV-Import (spaetere Etappe)?
4. **PDF-Bibliothek** `fpdf2` (reines Python, frei, klein) ins Docker-Image aufnehmen (Neubau des Images) — ok?
5. **Steuerberater-Pruefung** der Verfahrensdokumentation und der EUeR-Zuordnung (empfohlen, kostet Beratung = CEO-Tor):
   vor Echtbetrieb oder spaeter?
6. **Charta-Erweiterungen** (CFO: Buchhaltungsentwuerfe/EUeR-Vorbereitung; CRO: Angebote/Auftraege) — Diff wird vorgelegt.

## Etappen

Jede Etappe: eigener Branch, Tests + Gegenproben, Probelauf, CEO-Go, Deploy, Verifikation in LUNA-OS durch den CEO.

### Etappe 1: Fundament — Buchhaltungs-Speicher, Nummernkreise, Ablage, Backup

- Status: live (deployt 2026-09-27, Container-Neustart durch den CEO bestaetigt)
- Ergebnis: `orchestrator/core/buchhaltung.py` (Hash-Kette, `vergebe_nummer` unter Dateisperre, `beleg_ablegen`,
  `pruefe_kette`/`pruefe_belege`, `tagespruefung`), Bot-Loop 05:00 mit Alarm, Deploy-Schutz, Backup (Log + Beleg-Ordner +
  Schrumpf-Check), `.gitignore`, Doku, Team-Modul `finanzen` (nur owner oder ausdruecklich zugeteilt). Tests: 12 neue,
  Suite 815 gruen. Gegenproben rot wie erwartet: Hash-Pruefung aus -> Manipulation unerkannt; Sperre aus -> doppelte
  Nummern; Backup mit weniger Belegen als der Vorstand -> Abbruch mit Exit 1. Backup-Probelauf gegen die echte NAS:
  18 Stores, 0 Belege (auf der NAS gibt es noch keine Buchhaltung; Log + Belege werden ab der ersten Aufzeichnung
  gesichert). Bekannte Grenze: das Abschneiden der **letzten** Zeile erkennt die Kette allein nicht -- das faengt der
  Schrumpf-Check des Backups ab.
- Ziel / Scope: `buchhaltung/log.jsonl` (append-only, Hash-Kette, Ereignistypen, Faltung wie Investment-Depot),
  Nummernkreis-Dienst (atomar, lueckenlos, je Jahr), Belegablage `buchhaltung/belege/<jahr>/` mit SHA-256, Ketten-Pruefung
  (taeglich + Alarm), Aufbewahrungsklassen; Deploy-Schutz, Backup inkl. Beleg-Ordner (+ Dateizaehlung im Schrumpf-Check),
  `.gitignore`, `docs/datenfluesse.md`; Team-Modul `finanzen`.
- Gate: Tests gruen; Gegenprobe: eine manipulierte Zeile wird erkannt; zwei gleichzeitige Nummernvergaben ergeben keine
  Doppelung/Luecke; Backup-Probelauf sichert Log + Belege.
- Aufwand: mittel · Risiko: niedrig (noch keine Oberflaeche, keine echten Daten)

### Etappe 2: Kunden (CRM-Stammdaten) in LUNA-OS

- Status: abgeschlossen -- live, vom CEO abgenommen (2026-09-27); Zeitzonen-Korrektur (BF-32) deployt (`05454bd`)
- Ergebnis: `orchestrator/core/kunden.py` (Firmen `K-`, Ansprechpartner `AP-`, Aenderungen als Eintraege in der
  Hash-Kette, Verlauf je Feld, Dubletten-Warnung, Collab-Zuordnung eindeutig), API `/api/crm/kunden*` +
  `/api/crm/ansprechpartner/*` (Modul crm), LUNA-OS **V2** Sektion „Kunden" (Liste + Suche, Detail mit Stammdaten,
  Ansprechpartnern, Collab-Verknuepfung und Verlauf, Formulare). Nur V2 (CEO 2026-09-27: „Ich nutze nur V2, V1 koennen wir
  entfernen" -> Entfernen von V1 als eigener Vorschlag). Tests: 10 neue, Suite 825 gruen; Gegenproben rot wie erwartet
  (Dubletten-/Existenzpruefung aus; Dubletten-Rueckfrage in der Oberflaeche aus). Oberflaeche im Headless-Chrome mit
  Beispieldaten durchgeklickt: Liste, Collab-Tab, Anlegen mit Dublette + Rueckfrage, Detail, Speichern, Ansprechpartner.
- Abnahme 2026-09-27 (CEO): Firma `K-00001` und Ansprechpartner `AP-00001` in LUNA-OS V2 angelegt; auf der NAS geprueft:
  Kette intakt, Akteur `LUNA-OS:ceo`. Dabei gefunden: Zeitstempel in UTC (BF-32) -> Buchhaltung schreibt jetzt deutsche Zeit
  mit Zeitzone (deployt `05454bd`).
- Abweichung vom Plan: **keine Supabase-Projektion** -- die Kunden-App liest direkt aus der Kette auf der NAS; eine
  Kopie in Supabase braucht derzeit niemand (spart eine Migration). Nachruestbar, falls ein anderer Dienst die Daten braucht.
- Hinweis Rechte: Kunden liegen im Modul crm -> auch Team-Nutzer mit crm-Modul sehen und bearbeiten Stammdaten
  (so im Plan vorgesehen). Loeschen gibt es nicht (Aufbewahrung), nur „inaktiv".
- Ziel / Scope: Firmen mit **Firmenkundennummer** `K-…`, Typ (Kunde/Lieferant/Partner), Rechnungsanschrift,
  Steuernummer/USt-IdNr., Rechnungs-Mail, Zahlungsziel; **Ansprechpartner mit eigener Nummer** `AP-…` (Name, Rolle, Mail,
  Telefon), mehrere je Firma; Zuordnung/Zusammenfuehren bestehender Collab-Firmen (Instagram-Handle, Mail) zu einer Nummer;
  LUNA-OS-App „Kunden": Liste, Suche, Detail, Formular Anlegen/Bearbeiten (Aenderungen als Ereignisse mit Verlauf);
  Supabase-Projektion erweitern.
- Gate: CEO legt in LUNA-OS eine Firma mit zwei Ansprechpartnern an, Nummern fortlaufend; bestehende Collab-Firmen bleiben
  sichtbar und zuordenbar.
- Aufwand: mittel · Risiko: niedrig-mittel (Migration des bestehenden CRM)

### Etappe 3: Angebote

- Status: abgeschlossen -- vom CEO abgenommen 2026-09-28 mit dem ersten echten Angebot AN-2026-0001 (CR Container
  Trading GmbH): angelegt, PDF, als versendet markiert, Kalender-Erinnerungen (nach BF-33 nachgeholt) erscheinen auch im
  Apple-Kalender des CEO. **Noch nicht live erprobt:** Gmail-Entwurf mit Anhang (Google war beim Test ausgefallen) --
  beim naechsten Angebot pruefen.
- Ergebnis: `orchestrator/core/angebote.py` (AN-Nummer aus dem Angebotsjahr, Positionen in Cent, Status entwurf ->
  versendet -> angenommen/abgelehnt, „abgelaufen" abgeleitet, Inhalt nach „versendet" eingefroren), `core/beleg_pdf.py`
  (PDF nach DIN 5008 mit Briefkopf, § 19-Hinweis, Bank in der Fusszeile, Tabellenkopf auf Folgeseiten; wiederverwendbar
  fuer Rechnungen), Gmail-Entwurf **mit PDF-Anhang** (`google_workspace.mail_entwurf(anhaenge=)`), Kalender-Erinnerungen
  09:00 (Nachfassen nach N Tagen, Tag vor Ablauf), CRM-Stufe „angebot" fuer verknuepfte Collab-Firmen, PDF-Ablage als
  Geschaeftsbrief (6 Jahre) mit Inhalts-Hash. LUNA-OS V2: Sektion „📄 Angebote" (Offen/Alle, Editor mit Positionen und
  Live-Summe, Detail mit Aktionen) + Knopf im Kunden-Detail. Tests: 11 neue, Suite 838 gruen; Gegenprobe (Einfrieren
  aus) rot; PDF ein- und zweiseitig gesichtet; Oberflaeche im Headless-Chrome durchgeklickt.
- Nicht umgesetzt (bewusst): Textbausteine-Verwaltung (Einleitung/Schluss sind je Angebot frei, sonst Standardtext).
- Ziel / Scope: Angebot zu Firma + Ansprechpartner, Positionen (Menge, Einheit, Einzelpreis, Summe), Gueltigkeit,
  Bedingungen/Textbausteine, Kleinunternehmer-Hinweis; Status (Entwurf, versendet, angenommen, abgelehnt, abgelaufen);
  PDF; Versand als **Gmail-Entwurf mit Anhang** (Senden = CEO); Kalender-Erinnerung zum Nachfassen und vor Ablauf; CRM-Stufe
  „angebot" automatisch; Ablage + Aufbewahrung (angenommene Angebote 6 Jahre).
- Gate: Angebot anlegen -> PDF pruefen (CEO) -> Mail-Entwurf mit Anhang in Gmail -> Erinnerung im Kalender.

### Etappe 3b: Leistungskatalog + Hanserautisch-Angebot (aus dem Preislisten-Generator)

- Status: abgeschlossen -- live, CEO nutzt Katalog + Hanserautisch-Layout (AN-2026-0001, 2026-09-28); Editor/Detail
  ganzseitig, Firmensuche mit Vorschlaegen
- Ergebnis: `core/katalog.py` (18 Eintraege = 15 Formate + 3 Pakete, 6 Zuschlaege, Texte 1:1 aus dem Generator;
  `buchhaltung/katalog.json` nur NAS, Aenderungen als `katalog_geaendert` in der Kette, Speichern nur Modul finanzen),
  Angebote mit Katalog-Positionen, Zuschlaegen (Prozent auf die Summe aller Formate) und Paketrabatt (auf die
  Zwischensumme), Cent-genau und beim Anlegen eingefroren (Preise + Textbausteine); Standard 14 Tage, „Tangstedt, den";
  `beleg_pdf.hanserautisch_pdf` (Logo `buchhaltung/logo.jpg`, Farbbalken, „Moin"-Anrede, „So kalkulieren wir",
  Kennzahlen, Gruppen, Summenblock, Fusstext) + Preisliste (`/api/crm/katalog/preisliste.pdf`); schlichtes Layout
  bleibt waehlbar. LUNA-OS V2: Editor „Aus Katalog", Zuschlaege/Rabatt mit Live-Summe, Layout-Schalter; Tabs „Katalog"
  (Preise/Texte pflegen, Formate ergaenzen) und „Preisliste". Befund: „1.600" wurde als 1,60 € gelesen -> deutscher
  Tausenderpunkt wird jetzt erkannt (Server + Browser). Tests: 11 neue, Suite 849 gruen; Gegenprobe (Rabatt auf
  Formate statt Zwischensumme) rot; PDFs gesichtet; Oberflaeche im Headless-Chrome durchgeklickt.
- Herkunft: Preislisten-Generator des CEO (Claude-Chat-Artefakt, JSX; 17 Formate + 3 Pakete, 6 Zuschlaege, Rabatt,
  Hanserautisch-Layout). CEO-Entscheidungen 2026-09-27: mit den Angeboten verbinden; **Hanserautisch-Look**;
  Zuschlaege **wie im Generator** (Prozent auf die Summe aller Formate); Standard **Tangstedt, 14 Tage**.
- Ziel / Scope: Leistungskatalog (Formate, Pakete, Zuschlaege, Textbausteine) nur auf der NAS, in LUNA-OS pflegbar,
  Aenderungen protokolliert; Angebots-Editor „Aus Katalog hinzufuegen", Zuschlaege + Paketrabatt als eigene Zeilen
  (Cent-genau, beim Anlegen eingefroren); PDF im Hanserautisch-Look (Logo, Blau/Rot-Balken, „Moin"-Anrede,
  „So kalkulieren wir", Kennzahlen, Fusstext) mit Angebotsnummer, Kundennummer und Bank; **Preisliste** als eigenes PDF
  (ohne Nummer, ohne Buchhaltungseintrag).
- Gate: CEO erstellt ein Angebot aus dem Katalog mit Zuschlag + Rabatt, prueft PDF und Preisliste.

### Etappe 3c: Social-Media-Kennzahlen speichern und nutzen

- Status: geplant (CEO-Wunsch 2026-09-27) -- wartet auf die Meta-Business-Suite-Exporte des CEO
- Ziel / Scope: Meta-Exporte (Instagram/Facebook/Stories, CSV) in LUNA-OS hochladen, dauerhaft speichern (NAS, Backup);
  Auswertung (Median 90 Tage je Format, Follower, Aufrufe, Interaktionen, Verlauf); Werte fliessen in Katalog-Basis
  („Ø 37.000 Aufrufe je Reel") und die Kennzahlen im Angebot/Preisliste statt fester Zahlen.
- Gate: Export hochladen -> Auswertung in LUNA-OS stimmt mit der Meta Business Suite ueberein -> Angebot zeigt die Werte.

### Etappe 4: Beauftragung (Auftragsbestaetigung)

- Status: abgeschlossen -- live, vom CEO abgenommen 2026-09-28 („Auftragsbestaetigung sieht top aus“)
- Ergebnis: `core/beauftragung.py` (`AuftragBuch`): Auftrag `AB-JJJJ-NNNN` nur aus **angenommenem** Angebot, genau einer je
  Angebot (Pruefung unter der Sperre, Inhalt per Funktion an `mit_nummer` -- neu in `buchhaltung.py`), uebernimmt
  Positionen/Zuschlaege/Rabatt/Texte eingefroren + Leistungszeitraum/Notiz; Status beauftragt -> erledigt/storniert;
  Verknuepfung in beide Richtungen (Angebot zeigt `auftrag`); CRM-Stufe „vereinbart"; PDF „Auftragsbestaetigung"
  (Hanserautisch/schlicht; lange Titel schrumpfen automatisch) + Senden aus LUNAs Konto (nur CEO, Mail als .eml
  archiviert). LUNA-OS V2: Bereich „Angebote & Auftraege", Tab „Auftraege", Knopf „Auftrag anlegen" bzw.
  „Angenommen + Auftrag anlegen", ganzseitiges Auftrags-Detail. Tests + Gegenprobe (ein Auftrag je Angebot); Headless-
  Chrome-Klicktest; Test-Basisklasse `ApiBasis` (keine doppelten Testlaeufe).
- Ziel / Scope: angenommenes Angebot -> Auftrag `AB-…` (uebernimmt Positionen, Leistungszeitraum), optional PDF
  Auftragsbestaetigung, CRM-Stufe „vereinbart", Verknuepfung Angebot <-> Auftrag.
- Gate: durchgaengige Verknuepfung sichtbar in LUNA-OS.

### Etappe 5: Ausgangsrechnungen

- Status: abgeschlossen -- live, vom CEO abgenommen 2026-09-28 („Rechnung getestet, sieht alles gut aus“)
- Ergebnis: `core/rechnungen.py` (`RechnungStore`): Entwurf **ohne Nummer** (frei oder aus Auftrag, aenderbar/verwerfbar)
  -> **Festschreiben** ueber neues `Buchhaltung.festschreiben` (Nummer `RE-JJJJ-NNNN` + PDF + Eintrag in EINEM gesperrten
  Schritt; Fehlversuche verbrauchen keine Nummer, lueckenlos auch parallel) -> Senden (genau das archivierte PDF, nur
  Modul finanzen) -> Zahlung von Hand (Teil-/Restzahlung). **Storno** = Stornorechnung mit eigener Nummer (negativ,
  Bezug + Grund), optional Korrektur-Entwurf; bezahlte Rechnungen nicht stornierbar. Pflicht: Steuernummer +
  Leistungsdatum, kein USt-Feld. **Kleinunternehmer-Waechter** blockiert > 100.000 € Jahresumsatz bzw. Vorjahr > 25.000 €,
  Warnung ab 80 %. Faelligkeits-Erinnerung in LUNAs Kalender, taeglich 05:00 Meldung ueberfaelliger Rechnungen.
  LUNA-OS V2: Bereich „🧾 Rechnungen" (Modul finanzen, Offen/Alle/Entwuerfe, Umsatz-Balken), ganzseitiger Editor +
  Detail, Knopf „🧾 Rechnung erstellen" im Auftrag. Tests (11) + Gegenprobe (Nummer vor der Pruefung -> 5 rot); PDFs
  gesichtet; Headless-Chrome-Klicktest. Abweichung: Versand direkt aus LUNAs Konto statt Mail-Entwurf (CEO-Entscheidung
  LUNA-Google-Konto).
- Ziel / Scope: Rechnung aus Auftrag (oder frei), Pflichtangaben § 34a UStDV + Nummer + Leistungsdatum + fester
  Befreiungshinweis, **kein USt-Feld** (Schutz vor § 14c); Festschreiben (Nummer, eingefrorenes PDF, Hash); Storno- und
  Korrekturrechnung; Versand als Mail-Entwurf mit Anhang; Zahlungsziel, offene Posten, Erinnerung bei Faelligkeit;
  Ablage nach Jahr/Kunde; Kleinunternehmer-Waechter.
- Gate: Rechnung festschreiben -> nicht mehr aenderbar (Gegenprobe) -> Storno erzeugt Gegenbeleg; Nummern lueckenlos;
  Steuerberater-Muster (Entscheidung 5).

### Etappe 6: Eingangsrechnungen und Belege

- Status: abgeschlossen -- live (Image neu gebaut), vom CEO abgenommen 2026-09-28 mit der ersten echten Eingangsrechnung
  ER-2026-0001 (Calumet, per Mail an LUNA weitergeleitet, gebucht, bezahlt). Dabei BF-36 behoben (Apple-Mail-Anhaenge
  inline/verschachtelt) und der Regel-Vorschlag geschaerft. Zusatz (CEO): erledigte Kalender-Erinnerungen von Angeboten
  und Rechnungen loescht LUNA selbststaendig (`core/erinnerungen.py`). OCR-Live-Probe mit Foto steht noch aus.
  Zusatz (CEO 2026-09-29): erledigte Beleg-Mails legt LUNA in Gmail-Ordnern `LUNA/<Rechnungen|Gutschriften|Doppelt>/
  <Jahr>` ab (gelesen; alles andere bleibt im Posteingang; `eingangsbelege.mails_ablegen`, Recht `gmail.modify`,
  Neu-Anmeldung bei Google durch den CEO noetig, BF-39).
- Ergebnis: `core/eingangsbelege.py`: Aufnahme mit Beleg-Nr. `ER-JJJJ-NNNN` + Original (8 Jahre) atomar
  (`Buchhaltung.festschreiben`), doppelte Dateien erkannt; Auslesen lokal: XRechnung UBL/CII + ZUGFeRD-XML im PDF
  (defusedxml, exakt), PDF-Text (`pypdf`), OCR (`tesseract`/`pdftoppm`); Sofort-Vorschlag nach Regeln + genauerer
  Vorschlag ueber das Backoffice-Modell (MACO470, `roh`-Auftrag, stumm, beim Lesen uebernommen); CEO bucht (Lieferant,
  Nr., Datum, Faelligkeit, Betrag brutto, EUeR-Kategorie aus 14, Leistung, Notiz; Korrektur = neuer Eintrag; doppelte
  Rechnungsnummer je Lieferant erkannt), Lieferant im Kundenstamm (Typ Lieferant), bezahlt, verwerfen (Datei bleibt).
  Mail-Eingang: an luna.hanserautisch@gmail.com weitergeleitete Anhaenge werden im 15-min-Poll uebernommen (nur eigene
  Absender, doppelt geprueft). LUNA-OS V2: Bereich „📥 Belege" (Ziehen, Auswahl, Kamera; grosse Fotos im Browser
  verkleinert; ganzseitige Pruefansicht Original | Formular). Tests (13) + Gegenproben (XML-Bombe, Doppelt, Absender);
  Headless-Chrome-Klicktest. OCR selbst erst im neuen Image pruefbar (lokal kein tesseract).
- Ziel / Scope: Upload in LUNA-OS (PDF/Foto), **E-Rechnungen (XRechnung/ZUGFeRD) einlesen und lesbar anzeigen**, Original
  unveraendert archivieren; Lieferant, Datum, Betrag, Kategorie (EUeR-Zuordnung), Zahlungsdatum; optional Eingang aus
  Gmail-Anhaengen.
- **PDF-Scan (CEO-Wunsch 2026-09-28):** CEO laedt Rechnungen/Belege (PDF, Scan, Handyfoto) in LUNA-OS hoch; LUNA
  **digitalisiert** sie (Text/Werte auslesen: Lieferant, Rechnungsnummer, Datum, Betrag, Leistung), **sortiert** sie weg
  (Ablage je Jahr mit ER-Nummer, Lieferant im Kundenstamm als Typ „Lieferant“) und **verarbeitet** sie (Vorschlag fuer
  EUeR-Kategorie und Zahlungsdatum). Erkannte Werte sind **Vorschlaege** -- der CEO bestaetigt vor dem Buchen. Auslesen
  bevorzugt lokal (Backoffice-LLM/OCR auf dem MACO470), Cloud nur mit Freigabe (Belege enthalten Geschaeftsdaten);
  Mehrfach-Upload moeglich. Oberflaeche ganzseitig (siehe UI.md 11).
- Gate: je ein PDF-, Foto- und XRechnungs-Beleg korrekt erfasst und archiviert (Hash); ein gescanntes Papier-PDF wird
  richtig ausgelesen und nach Bestaetigung abgelegt.

### Etappe 7: Zahlungen und EUeR-Journal

- Status: abgeschlossen -- live, vom CEO abgenommen 2026-09-28 („sieht gut aus“); offene Praxisprobe: Meta-Euro-Betrag per Telegram
- Ergebnis: `core/finanzen.py` (Journal nach Zahlungsdatum, EUeR je Position, Anlageverzeichnis mit AfA, Uebersicht),
  `core/eigenbelege.py` (Eigenbelege `EB-JJJJ-NNNN` fuer Zahlungen ohne eigene Rechnung, Storno mit Grund, 10-Tage-Regel),
  Teilzahlungen + Zahlungs-Storno fuer Rechnungen und Belege, GWG-Grenze 800 €, Anlagegut mit Nutzungsdauer,
  Kleinunternehmer-Waechter zaehlt Eigenbeleg-Einnahmen mit. LUNA-OS V2 „💶 Finanzen“: Uebersicht (Kennzahlen mit
  Vorjahr, Monatsverlauf, KU-Grenze, Pipeline Angebot -> Geld, offene Posten, To-dos, Kategorien, Top-Kunden, letzte
  Zahlungen), Journal (+ CSV), EUeR, Anlagen; Jahreswahl. Probejahr von Hand nachgerechnet (Tests + Gegenproben);
  Headless-Chrome-Klicktest mit echten API-Daten. Amtliche EUeR-Zeilennummern bewusst erst in Etappe 9.
  Nachtrag (CEO, Facebook-Monetarisierung): Belegart „Einnahme (Gutschrift)“, Meta-Zahlungsavis (englisch, USD)
  erkannt, Fremdwaehrung -> Euro-Betrag vom Kontoauszug (Kalender-Erinnerung RG-Datum + 7 Tage); Beleg-Mails auch aus dem Spam mit DKIM/DMARC-Pruefung (BF-37).
- Ziel / Scope: Zahlungen erfassen (Rechnung bezahlt / Beleg bezahlt, Teilzahlungen), Journal nach Zahlungsdatum,
  10-Tage-Regel, Kategorien -> Zeilen der Anlage EUeR, Anlageverzeichnis mit AfA/GWG/Sammelposten; (optional spaeter:
  Kontoauszug-CSV-Import, Entscheidung 3).
- Gate: Probejahr mit Testdaten ergibt nachvollziehbare EUeR-Summen (Abgleich von Hand).

### Etappe 8: Finanz-Cockpit in LUNA-OS

- Status: abgeschlossen -- live, vom CEO abgenommen 2026-09-28 („Neustart erledigt, sieht gut aus, weiter mit Etappe 9“)
- Ergebnis: Zeitraum-Wahl (Jahr, Q1-Q4, Monat) mit Vorjahreszeitraum; jede Kennzahl, jeder Monat, jedes Quartal, jede
  Kategorie und jeder Kunde per Klick als Buchungsliste (Drill-down, `GET /api/finanzen/posten`; Summe = Kachel);
  Quartalstabelle mit Vorjahr + Veraenderung; Monatsverlauf mit Vorjahr (blass); Abschreibung monatsgenau (Monate/
  Quartale addieren sich exakt zum Jahr; im laufenden Jahr nur bis zum aktuellen Monat); Hochrechnung Jahresumsatz fuer
  die KU-Grenze; KI-Kosten (Verbrauch geschaetzt je Monat/Anbieter gegen das Monatsbudget, bewusst nicht in der EUeR --
  die Anbieter-Rechnung ist der Beleg). Tests (Kennzahl = Summe ihrer Posten fuer Jahr/Quartal/Monat) + Gegenprobe;
  Headless-Chrome-Test mit echten API-Daten.
- Ziel / Scope: Einnahmen, Ausgaben, Gewinn (Monat/Quartal/Jahr, Vorjahresvergleich), offene Posten, Top-Kunden,
  Ausgaben je Kategorie, Kleinunternehmer-Grenze als Balken, KI-Kosten eingebunden; detaillierte Drill-downs.
- Gate: CEO-Abnahme der Zahlen gegen die Rohdaten.

### Etappe 9: Jahresabschluss und Export

- Status: umgesetzt (CEO-Go 2026-09-28 „weiter mit Etappe 9“), Deploy + Abnahme offen (inkl. Verfahrensdokumentation)
- Ergebnis: `core/jahresabschluss.py` + `core/euer_zeilen.py`: Abschluss-Pruefung (Kette/Belege, Monatsabgleich, Belege
  gebucht, Entwuerfe, offene Posten), EUeR je **Zeile und ELSTER-Kennzahl** der Anlage EUeR (2024/2025 und 2026 aus den
  BMF-Vordrucken belegt; 2026 ab Zeile 27 verschoben; Summen/Gewinn rechnet ELSTER), EUeR als PDF, **Export-ZIP**
  (Tabellen als CSV + `index.xml` nach dem Beschreibungsstandard mit DTD, vollstaendige Hash-Kette + Pruefergebnis,
  alle Belege des Jahres im Original, EUeR-PDF, LIESMICH). LUNA-OS: Reiter „Jahresabschluss“. Verfahrensdokumentation
  `docs/verfahrensdokumentation-buchhaltung.md` (Entwurf, Abnahme durch den CEO offen). Monatsabgleich beginnt jetzt
  beim fruehesten Beleg-/Zahlungsdatum (nachgetragene Belege). Tests (Export vollstaendig: Stichprobe Journal = EUeR,
  Hashes der Belege, index.xml passt zu den CSV-Koepfen) + Gegenproben; Browser-Test + PDF gesichtet.
- Ziel / Scope: EUeR-Uebersicht je Zeile (Eingabehilfe fuer ELSTER), Export aller Journal-/Stammdaten maschinenlesbar
  (Datenzugriff § 147 Abs. 6 AO) + Belege, Steuerberater-Paket, **Verfahrensdokumentation**
  (`docs/verfahrensdokumentation-buchhaltung.md`).
- Gate: Export vollstaendig (Stichprobe), Verfahrensdokumentation vom CEO (ggf. Steuerberater) abgenommen.

### Etappe 10: Mahnwesen

- Status: umgesetzt (CEO-Wunsch 2026-09-28 mit Entscheidungen, s. u.), Deploy + Abnahme offen
- Entscheidungen (CEO 2026-09-28): 1. Mahnung stoesst der CEO an (Frist waehlbar); 2. und 3. Mahnung bereitet LUNA nach
  Fristablauf vor und fragt per Telegram (✅ Senden / ❌ Nicht senden) -- **kein autonomer Versand** (AGENTS.md 4);
  Firmen: **40 EUR Verzugspauschale** einmal je Rechnung (§ 288 Abs. 5 BGB) statt 15 EUR je Mahnung (rechtlich
  angreifbar), Privatkunden: 2,50 EUR tatsaechliche Kosten je Mahnung; **Verzugszinsen ab Faelligkeit**, Basiszinssatz +
  9 (Firma) bzw. 5 (Privat) Prozentpunkte, taggenau je Halbjahr.
- Ergebnis: `core/mahnungen.py` (Nummern `MA-JJJJ-NNNN`, PDF als Geschaeftsbrief, Basiszinssaetze 2023-2026 von der
  Bundesbank belegt, act/act), Kundenfeld „Privatperson (Verbraucher)“, Zahlung mit zusaetzlichen Zinsen/Kosten
  (Journal als eigene Einnahme; EUeR Zeile 12 inkl., nachrichtlich Zeile 13/Kz 119; zaehlt nicht zum § 19-Umsatz),
  LUNA-OS: Mahnung in der Rechnungsansicht (Vorschau mit Frist -> festschreiben -> senden), To-dos zeigen den
  naechsten Schritt, CFO-Finanzcheck erinnert an fehlenden Basiszinssatz (naechster: 01.01.2027). Tests (Zinsen von Hand,
  Stufen, Verbraucher, Zahlung, Telegram-Versand) + Gegenprobe.

### Etappe 11: Positionen erkennen und Belege aufteilen

- Status: umgesetzt (CEO-Wunsch 2026-09-28: „Belege beim Scannen so anlegen, dass die Positionen auch erkannt und
  einzeln aufgefuehrt werden“, Anlass: gemischte Amazon-Rechnungen mit privaten Artikeln), Deploy + Abnahme offen
- Ergebnis: Positionen aus E-Rechnungen (UBL/CII, netto + Steuersatz -> brutto), aus PDF-/OCR-Text (Zeilenregel) und
  ueber das Backoffice-Modell (je Position mit Kategorie); Buchungsmaske „In Positionen aufteilen“ mit Kategorie je
  Position inkl. **„privat – nicht absetzbar“** (§ 12 EStG), Summenkontrolle, „Differenz als Position“ (Versand/Rabatt);
  GWG-Grenze und Anlagegut (Nutzungsdauer) je Position; Zahlungen anteilig je Position (centgenau), Privatanteil im
  Journal sichtbar, zaehlt nicht in EUeR/Cockpit/AfA; Export-Spalte „Aufteilung“. Tests + Gegenprobe; Browser-Test.

### Etappe 12: Barter-Deals (Leistung gegen Ware)

- Status: umgesetzt (CEO-Go 2026-09-28 „Go für Etappe 12“; kein Steuerberater -> Zweifelsfaelle als Hinweis in LUNA-OS),
  Deploy + Abnahme offen
- Ergebnis: Feld „Gegenleistung in Ware“ (Text + Wert) in Angebot, Auftragsbestaetigung (uebernommen) und Rechnung
  (Editor, Detail, PDF: „Gegenleistung: X in Ware ... und Y in Geld“ bzw. Rechnung mit beziffertem Entgelt
  „davon Sachleistung (tauschaehnlicher Umsatz) ... in Geld zu zahlen“); Rechnung: Geldteil und Warenteil getrennt,
  „bezahlt“ erst mit Geld **und** Ware; „📦 Ware erhalten“ (Wert laut Marke + eigener Nachweis, der Nachweis zaehlt;
  Verwendung Content = Einnahme + gleiche Anschaffung GWG/Anlage/Verbrauch, privat = nur Einnahme, Leihgabe = nichts;
  Nachweis-Dateien als Beleg; Storno); Mahnung nur Geldteil; To-do „Ware zu RE erhalten?“; Journal/EUeR (Einnahme
  „Sachleistungen (Barter)“ in Zeile 12, Anlagegut aus Barter mit AfA), KU-Grenze mit vollem Rechnungswert; spaetere
  Privatnutzung/Verkauf als Eigenbeleg „Verkauf oder private Weiternutzung“ -> EUeR Zeile 19/Kz 102, nicht zur KU-Grenze;
  Export-Spalten Warenwert/Ware erhalten. Tests (Roadmap-Verifikation) + Gegenprobe; Browser-Test.
- Hintergrund (Recherche 2026-09-28, amtliche Quellen; [?] = nur Schlussfolgerung, Steuerberater-Frage):
  - **Einnahme:** Behaltene Produkte sind Betriebseinnahmen, anzusetzen mit dem **ueblichen Endpreis am Abgabeort
    abzueglich ueblicher Preisnachlaesse** (§ 8 Abs. 2 EStG; Leitfaden Hessen 06/2026 S. 2-3, FAQ Bayern S. 3/8,
    Steuerguide BW 2025, finanzamt.nrw.de/influencer); Zufluss bei Erhalt bzw. wenn sie behalten werden duerfen
    (§ 11 EStG). **Leihgabe/Rueckgabe = keine Einnahme** (Hessen: nur „wenn Sie das Produkt ... behalten duerfen“).
  - **Umsatzsteuer/§ 19:** tauschaehnlicher Umsatz (§ 3 Abs. 12 UStG), Wert der Gegenleistung als Entgelt (§ 10 Abs. 2
    UStG, UStAE 10.5: Aufwand der Marke, sonst Schaetzung) -> **zaehlt zum Gesamtumsatz der Kleinunternehmer-Grenze**
    (§ 19 Abs. 1/2 UStG). Default: derselbe Wert wie oben; optional abweichender „USt-Wert“ [?].
  - **EUeR:** Zeile 12 / Kz 111 (alle Einnahmen des Kleinunternehmers, Anleitung 2026).
  - **Danach:** betriebliche Nutzung -> Anschaffung in gleicher Hoehe als GWG (Zeile 37) bzw. AfA (Hessen S. 3:
    „Wertverzehr ... als Betriebsausgabe“; gleiche Hoehe [?]); spaetere Privatnutzung -> **Entnahme zum Teilwert**,
    einnahmeerhoehend (Hessen S. 3, § 6 Abs. 1 Nr. 4 EStG; Zeile 19/Kz 102 bzw. 21/Kz 108); sofort privat -> Einnahme,
    keine Ausgabe [?]; Verkauf -> Erloes Zeile 19 (Anlagevermoegen) bzw. 12.
  - **Rechnung:** Pflicht bei Unternehmer-Kunden binnen 6 Monaten (§ 14 Abs. 2 Satz 2 Nr. 1 UStG), Pflichtangaben
    § 34a UStDV mit beziffertem Entgelt (Sachwert + Geld) und § 19-Hinweis; keine Sonderformel vorgeschrieben.
  - **Keine Bagatell-Ausnahme** fuer Barter: § 37b-Pauschalierung der Marke gilt nur fuer Zusatzgeschenke, nicht fuer
    die vereinbarte Gegenleistung; fuer echte Zusatzgeschenke Feld „Marke hat pauschal versteuert (§ 37b)“.
  - **Nachweis:** Vertrag/Mail, Lieferschein bzw. Wertangabe der Marke, datierter Shop-Screenshot, Eingangsdatum,
    Link zum Post, ggf. Rueckversandbeleg.
- Ziel / Scope:
  - **Angebot und Auftragsbestaetigung:** je Position oder fuer den ganzen Deal eine Gegenleistung „in Ware“ mit
    Warenbezeichnung und Warenwert; Mischformen (Geld + Ware); das PDF zeigt klar „Gegenleistung: Produkte im Wert
    von X EUR (Sachleistung)“ und den Geldteil getrennt.
  - **Rechnung:** weist den vollen Wert aus (Geld- und Sachteil), zahlbar ist nur der Geldteil; Hinweis, dass der
    Sachteil durch Lieferung der Ware ausgeglichen wird; Pflichtangaben § 34a UStDV / § 19-Hinweis wie gehabt [?].
  - **„Zahlung“ in Ware:** neuer Vorgang „Ware erhalten“ (Datum, Bezeichnung, Wert, Nachweis wie Foto/Screenshot
    des Shop-Preises/Lieferschein als Beleg) -> Einnahme im Journal (Kategorie Barter/Sachleistung), zaehlt zur
    Kleinunternehmer-Grenze; offene Sachleistung erscheint unter „bekommen wir“ und in den To-dos.
  - **Verwendung der Ware:** beim Erhalt „betrieblich fuer Content“ (Standard, CEO) / „privat“ / „Leihgabe, geht
    zurueck“ -> automatische Gegenbuchung (GWG/Anlage) bzw. keine; spaeter „privat weiter genutzt“ (Entnahme zum
    Teilwert) oder „verkauft“ (Erloes) als eigener Vorgang; Korrektur per Storno.
  - **Mahnwesen:** gemahnt wird nur der Geldteil; ausbleibende Ware als To-do „Ware nachfordern“ (kein Zins).
  - **Cockpit/EUeR/Export:** Barter-Einnahmen und -Ausgaben sichtbar getrennt, Drill-down, Export-Spalten; EUeR-Zeile
    fuer Kleinunternehmer vermutlich Zeile 12 [?].
  - **Collab-CRM:** Deals mit Marken sind oft Barter -> Kennzeichnung am Kunden/Deal [?].
- Entscheidungen (CEO 2026-09-28): (1) Warenwert = **Preisangabe der Marke UND eigener Nachweis** (Shop-Screenshot/
  Lieferschein als Beleg); (2) Standard-Verwendung der Ware = **betrieblich fuer Content**; (3) **Rechnung auch bei
  reinem Barter: ja**.
- Gate: ein Probe-Deal (Geld + Ware) laeuft von Angebot bis EUeR durch; Summen je Belegart von Hand nachgerechnet;
  Wert der Ware zaehlt in Journal, EUeR und Kleinunternehmer-Grenze; privat behaltene Ware erzeugt keine Ausgabe;
  Tests + Gegenprobe; CEO-Abnahme der PDFs.
- Verifikation (vorab): `pytest -q orchestrator` gruen; Probe-Deal 500 EUR Geld + Ware 300 EUR: Rechnung 800 EUR,
  offen 500 EUR; nach Geldeingang + „Ware erhalten (betrieblich, GWG)“: Einnahmen 800 EUR, Ausgaben 300 EUR,
  KU-Umsatz +800 EUR; Variante „privat“: Einnahmen 800 EUR, Ausgaben 0 EUR.
- Risiko: steuerliche Einordnung -> vorab recherchieren, Zweifelsfaelle als Steuerberater-Frage markieren;
  bestehende Belege bleiben unveraendert (neue Felder sind optional, additive Ereignisse).
- Dokumentation: Changelog, Roadmap-Status, `ROADMAP.md`, Entscheidungs-Register (Wertermittlung, Verwendung),
  `docs/datenfluesse.md`, Verfahrensdokumentation (Tauschgeschaefte).

### Etappe 13: Abo-Belege aus Mails (ohne PDF) und automatische Weiterleitungen

- Status: umgesetzt (CEO 2026-09-29: „Alle Mails die ich eben geschickt habe, muessen auch erkannt werden ... Kuemmere
  dich bitte drum“), Deploy + Abnahme offen. Probelauf mit den 13 echten Mails (lokal): 11 Mailtext-Rechnungen mit
  richtigem Lieferant/Datum/Betrag, Anthropic/Supabase je ein Beleg mit Quittung als Zahlungsnachweis, Apple-Developer-
  Mail als Dublette von ER-2026-0003 erkannt. Abo-Kennzeichnung je Lieferant wandert in Etappe 14 (braucht L-Nummern).
- Ergebnis: `core/eingangsbelege.py`: `mail_text` (Text-/HTML-Teil ohne Links), `weiterleitung` (Original-Absender,
  -Betreff, -Datum aus dem Weiterleitungskopf), `mail_ist_beleg` (Beleg-Wort + Betrag), `vorschlag_mail` (Haendler statt
  PayPal, hoechster Euro-Betrag = brutto, Datum ersatzweise aus dem Kopf), `mail_pdf` (lesbare Ansicht) + `.eml` als
  unveraendertes Original am selben Beleg; `auto_weitergeleitet` (DKIM/DMARC des Original-Absenders + an/ueber eigene
  Adresse); `_gleicher_beleg` (Dublette per Rechnungsnummer + Betrag -> `LUNA/Doppelt`); Quittung neben Rechnung ->
  `datei_anhaengen` (Rolle Zahlungsnachweis); `als_nachweis` + `POST /api/finanzen/belege/<nr>/als-nachweis` fuer
  Altfaelle; Regeln: Stripe-Nummer, englische/deutsche ausgeschriebene Daten, Lieferant nicht „Page 1 of 1“/„Invoice“,
  Bestell-/Dokument-/Transaktionsnummer, Zweifelsfall-Hinweise (Versicherung, Mobilfunk, Streaming, PayPal-Beleg,
  Kundenportal). LUNA-OS: weitere Dateien am Beleg, Hinweise, „🧾 Ist Zahlungsnachweis zu …“ (app v60). Tests
  `test_mail_belege.py` (9) + 8 Gegenproben; Browser-Test.
- Befund 2026-09-29 (13 Weiterleitungen von moin@, alle DKIM-geprueft echt): nur **2 mit PDF** (Anthropic, Supabase --
  je **Rechnung + Zahlungsquittung** als zwei PDFs); **11 ohne Anhang**, die Rechnung steht im Mailtext (Apple iCloud+/
  AppleCare x4, PayPal-Belege Microsoft x2/DAZN/Grover/Dropbox, Canva, DR.SIM). Der Mail-Eingang sucht bisher nur
  `has:attachment` -> diese 11 sieht LUNA gar nicht.
- Ziel / Scope:
  - **Mail als Beleg:** eigene, echte Weiterleitung ohne PDF, deren Text wie eine Rechnung/Quittung aussieht (Wort
    Rechnung/Beleg/Receipt/Invoice + Betrag) -> Beleg `ER-...`; Original = die **.eml unveraendert** (GoBD: bei
    Mail-Rechnungen ist die Mail das Original), dazu eine lesbare PDF-Ansicht (Absender, Datum, Betreff, Text) fuer
    LUNA-OS und Auslesen. Vorschlag aus dem weitergeleiteten Teil (Originalabsender, Rechnungsdatum, Nummer, Betrag,
    MwSt). Mails ohne Rechnungsmerkmale bleiben im Posteingang.
  - **Rechnung + Quittung in einer Mail:** Quittung/Receipt/Zahlungsbestaetigung wird **Zahlungsnachweis am selben
    Beleg**, kein zweiter Beleg (sonst doppelte Ausgabe); Zahlungsdatum daraus als Vorschlag „bezahlt“.
  - **Automatische Weiterleitungen:** Viele Anbieter/Postfaecher leiten mit dem **Original-Absender** weiter (z. B.
    `no_reply@email.apple.com`) -- dann greift die Absenderliste nicht. Zulassen, wenn (a) die Absenderdomain per
    DKIM/DMARC echt ist **und** als Rechnungs-Absender eines Lieferanten in den Stammdaten steht (Etappe 14), oder
    (b) die Mail nachweislich ueber eines der eigenen Postfaecher kam (ARC-/Weiterleitungs-Kopf). Erste echte
    Auto-Weiterleitung wird vorher untersucht, wie sie ankommt.
  - **Abos erkennen:** Lieferant + aehnlicher Betrag monatlich -> Kennzeichen „Abo“ (Kostenstatistik, CFO-Hinweis
    „Abo-Beleg fehlt diesen Monat“ auf Lieferantenbasis statt Kategorie).
  - **Zweifelsfaelle als Hinweis** beim Buchen (kein Steuerberater): Mobilfunk (privater Anteil), Streaming (DAZN),
    Versicherungen/AppleCare (nur fuer betriebliche Geraete), Cloud-Speicher; Steuer-Hinweis „Versicherungssteuer,
    keine MwSt“ bei AppleCare.
- Gate: die 11 Mails ohne PDF werden (nach Deploy) als 11 Belege mit richtigem Lieferant/Datum/Betrag vorgeschlagen
  (Abweichungen von Hand gezaehlt); Anthropic/Supabase ergeben je **einen** Beleg mit Zahlungsnachweis; eine Mail ohne
  Rechnungsmerkmale bleibt im Posteingang; eine gefaelschte Mail (DKIM fail) wird nie Beleg; Tests + Gegenprobe.
- Verifikation (vorab): `pytest -q orchestrator backoffice` gruen; Testmails aus den echten Mustern (anonymisiert):
  Apple 9,99 EUR (MwSt 1,59), PayPal/DAZN 44,99 EUR, Canva 12,00 EUR -> Vorschlag korrekt; Readback im Live-Kassenbuch.
- Risiko: falsche Beleg-Erkennung (Werbemail als Rechnung) -> nur eigene/verifizierte Absender, CEO bucht immer selbst;
  zurueck per „verwerfen“. Bereits aufgenommene Quittungs-PDFs (Anthropic/Supabase, falls vorher gepollt) werden
  verworfen bzw. als Nachweis umgehaengt.
- Aufwand: mittel (1 Sitzung). Abhaengigkeit: (a) der Auto-Weiterleitung nutzt Etappe 14.
- Dokumentation: Changelog, Roadmap, `docs/datenfluesse.md`, Register, Verfahrensdokumentation (Mail als Original).

### Etappe 14: Lieferanten-, Partner- und Dienstleister-Stammdaten mit Nummern

- Status: umgesetzt (CEO-Go 2026-09-29 „Go fuer etappe 14“), Deploy + Nachzuordnung live + Erstbefuellung + Abnahme offen
- Ergebnis: Kreise `K-`/`L-`/`P-` (`buchhaltung.KREISE_OHNE_JAHR`, `kunden.KREIS`); alte Lieferanten behalten ihren
  K-Schluessel und bekommen eine L-Nummer (`rollennummer_sichern`, Ereignis `firma_nummer_ergaenzt`, jede Nummer findet die
  Firma, angezeigt wird die Rollennummer); neue Felder `kundennummer_bei`, `zahlungsweg`, `rechnungs_absender`,
  `vertraege` [{bezeichnung, nummer, notiz}], Lueckenanzeige (Adresse/Land/USt-ID, im Ausland ohne PLZ); `finde` (Absender >
  Name > erstes Namenswort; Zahlungsdienste wie PayPal nie) und `zuordnen` (finden oder anlegen, Absender lernen). Buchen
  eines Belegs setzt **immer** eine Nummer (gewaehlt, gefunden oder neu: Lieferant bei Ausgaben, Partner bei Einnahmen);
  Eigenbelege brauchen eine Gegenpartei (Nummer); Altbelege per `POST /api/finanzen/stammdaten/zuordnen` (mit `probe`);
  Journal mit Nummer + Filter `?firma=`, CSV-Spalte „Nr.“, Export-Spalten Partner_Nr/Lieferant_Nr + erweiterte
  `kunden.csv`, alle Dateien eines Belegs im Export; Firmen-Detail mit Belegen, Summen je Jahr, Abo-Erkennung; CFO-Hinweis
  „wiederkehrend fehlt“ je Nummer. LUNA-OS: Reiter Kunden/Lieferanten/Partner, Vertraege-Editor, Stammdaten-Auswahl beim
  Buchen und bei Eigenbelegen (app v61). Tests `test_stammdaten.py` (7) + 8 Gegenproben, Browser-Test; Probelauf an einer
  Kopie des Live-Kassenbuchs: L-00001..L-00005 fuer die bisherigen Lieferanten, TeamClash/Fiverr/Elgato L-00006..8, Meta
  P-00001, Kette intakt. „Etwas anderes“ bei den Angaben war ein Versehen (CEO 2026-09-29) -- keine weiteren Felder.
- Bestand: Firmen-Stammdaten gibt es (`core/kunden.py`, Typ kunde/lieferant/partner), aber **eine** Nummernfolge
  `K-00001` fuer alle; Lieferanten entstehen beim Buchen nur mit Namen (live: K-00003..K-00007). Eigenbelege haben nur
  Freitext „Gegenpartei“.
- Ziel / Scope:
  - **Eigene Nummer je Rolle** (Vorschlag): Kunden `K-`, Lieferanten/Dienstleister `L-`, Partner `P-`; bestehende
    Lieferanten bekommen ihre L-Nummer als Ergaenzung (K-Nummer bleibt als Verweis gueltig, Hash-Kette unveraendert).
  - **Adresse und Nummern** je Lieferant: Anschrift, Land, USt-ID/Steuernummer, **unsere Kundennummer beim Lieferanten**,
    Vertrags-/Abo-/Versicherungsnummern, Rechnungs-Absenderadressen (fuer Etappe 13), Zahlungsweg, Website, Notiz.
  - **Jeder Beleg haengt an einer Nummer:** Eingangsbelege Pflichtfeld Lieferant (Auswahl/Neuanlage mit Vorschlag aus
    dem Beleg: Name, Anschrift, USt-ID, Kundennummer), Eigenbelege und Barter ebenfalls; Altbelege nachtraeglich
    verknuepfen (additives Ereignis).
  - **Lieferanten-Ansicht** in LUNA-OS: Stammdaten, alle Belege/Zahlungen, Summe je Jahr, Abos; Filter im Journal und
    Export-Spalte Lieferantennummer.
  - **Erstbefuellung durch LUNA:** alle bisherigen Lieferanten/Partner aus den Belegen (Calumet, Amazon, J. Fuehr,
    Adlerfokus, Apple, Meta (Partner), Fiverr, Elgato, TeamClash) plus die neuen Abo-Anbieter (Anthropic, Supabase,
    Microsoft, DAZN, Grover, Dropbox, Canva, DR.SIM) mit den Adressen/Nummern, die auf den Belegen stehen; fehlende
    Angaben als Luecke markiert, nichts erfunden.
- Entscheidungen (CEO 2026-09-29): (1) **eigene Nummernkreise** K-/L-/P- (bestehende Lieferanten K-00003..K-00007
  erhalten zusaetzlich eine L-Nummer); (2) je Lieferant **Adresse + USt-ID, unsere Kundennummer, Vertrags-/Abo-/
  Versicherungsnummern, Zahlungsweg** (weitere Angabe: Versehen, CEO 2026-09-29); (3) **erst nur planen**:
  CEO liest die Roadmap, Go fuer 13/14 steht aus.
- Gate: jeder gebuchte Beleg und Eigenbeleg hat eine Lieferanten-/Partnernummer; Lieferanten-Ansicht zeigt fuer Amazon
  alle Amazon-Belege mit Summe = Summe im Journal; Tests + Gegenprobe; CEO-Abnahme der Ansicht.
- Verifikation (vorab): `pytest` gruen; Readback live: Anzahl Belege ohne Lieferantennummer = 0.
- Risiko: Dubletten (Amazon.de vs. Amazon EU S.a.r.l.) -> Dublettenpruefung + Zusammenfuehren; Nummern sind additiv,
  nichts wird umgeschrieben.
- Aufwand: mittel bis gross (1-2 Sitzungen). Reihenfolge: **14 vor 13(a)**, 13 ohne (a) sofort moeglich.
- Dokumentation: Changelog, Roadmap, `docs/datenfluesse.md`, Register, Verfahrensdokumentation (Stammdaten).

## Reihenfolge

1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11 -> 12 -> 13 (ohne Auto-Weiterleitung) -> 14 -> 13 (Auto-Weiterleitung). Etappe 6 (Belege) kann nach Etappe 2 vorgezogen werden, falls Einkaeufe zuerst
erfasst werden sollen. Jede Etappe ist fuer sich nutzbar.

## Kosten

Software 0 EUR (Eigenbau, freie Bibliotheken). Optional: Steuerberater-Pruefung (CEO-Tor).

## Dokumentationspflichten

`projekt_changelog.md`, Etappen-Status hier, `ROADMAP.md`, `docs/datenfluesse.md` (neue Speicher, Tabellen, Endpunkte),
`docs/entscheidungs-register.md`, `docs/bekannte-fehler.md`, `AGENTS.md` 7 (neue Dateien), Verfahrensdokumentation,
Charten (nur ueber HoA auf CEO-Anweisung).

## Definition of Done

Der CEO fuehrt in LUNA-OS einen kompletten Fall durch — Firma + Ansprechpartner anlegen, Angebot, Beauftragung, Rechnung,
Zahlung — erfasst Eingangsrechnungen, sieht die Kennzahlen live und erhaelt zum Jahresende eine EUeR-Uebersicht samt
Export; Verfahrensdokumentation liegt vor. Abnahme durch den CEO.
