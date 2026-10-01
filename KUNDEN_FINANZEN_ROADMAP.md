# Roadmap: Kunden, Angebote, Rechnungen und Finanzen in LUNA-OS

- Status: in Umsetzung
- Stand: 2026-09-30
- Arbeitsbranch: `ai/kunden-finanzen` (geschlossen 2026-09-29, alles auf main; naechste Etappe auf neuem Branch)
- Basiscommit: `649a974`
- Naechster Schritt: Etappe 27 (Plattform-Auszahlungen) live, Nachtrag gebucht -- CEO-Abnahme offen; Etappe 26 (kalkulatorische Kosten zuschaltbar) live -- CEO-Abnahme offen; Etappe 19 live (Hands of God/Kiezalm uebernommen 2026-09-30), Etappe 20 live, Etappe 23 live, Etappen 21, 22 live; 24 (Firmenakte) und 25 (Zeiterfassung) umgesetzt -- gemeinsamer Deploy offen; 21 Kalkulation + Lager, 22 Firmendaten-Recherche. Etappe 18 (Zahlungsbedingungen/Vorkasse) umgesetzt -- Deploy + CEO-Abnahme (ein Angebot mit Vorkasse bis zur Schlussrechnung durchspielen). Etappen 15/16 sind live (2026-09-29) -- CEO-Abnahme (erstes Abo anlegen, ein Angebot mit
  Community-Fit + OMR-Vergleich als PDF ansehen). CEO-Abnahme Etappen 13/14 beim Buchen der offenen Belege (ER-0033/-0035: Lieferant aus der Liste
  waehlen, Vorschlag stammt noch von vor dem Update); Luecken (Adressen) fuellen, sobald Belege sie zeigen; erste echte
  Auto-Weiterleitung pruefen.
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
- Erweiterung (Antrags-Durchsicht 2026-09-29, Antrag „datengetriebener Content-Feedback-Loop“, CCO): die Auswertung
  speist auch die **TKP-Kontakte** im Katalog (Etappe 16: Median 90 Tage statt Handwert) und zeigt je Format/Thema, was
  funktioniert (Top-/Flop-Reels) -> Hinweis an Content-Feed/Ideen. Weiter wartend auf die Meta-Exporte.

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

- Nachtrag 2026-09-30 (CEO: Jahresordner statt Eigenbelege): Upload in LUNA-OS nimmt auch gespeicherte Mails (`.eml`) und
  Postfaecher (`.mbox`) an -- gleiche Erkennung wie Mails an LUNA, idempotent ueber die Message-ID, Dubletten erkannt
  (`eingangsbelege.datei_importieren`); Lesefehler aus dem echten Ordner behoben (BF-43).

### Etappe 14: Lieferanten-, Partner- und Dienstleister-Stammdaten mit Nummern

- Status: deployt + live befuellt (main 774de97, 2026-09-29), CEO-Abnahme offen. Nachzuordnung live: L-00001..05
  (Calumet, Amazon, J. Fuehr, Adlerfokus, Apple), L-00006..08 (TeamClash, Fiverr, Elgato), P-00001 (Meta); Erstbefuellung aus
  den Belegen + neue Abo-Anbieter L-00009..16 (Anthropic, Supabase, Canva, DR.SIM, Microsoft, DAZN, Grover, Dropbox); Kette intakt
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

### Etappe 15: Wiederkehrende Zahlungen / Abos (manuelle Belege)

- Status: umgesetzt (CEO-Go 2026-09-29 „Du hast dann das Go fuer beide Etappen“), Deploy + Abnahme offen
- Entscheidung (CEO 2026-09-29): **automatisch buchen als Option** -- Haken beim Anlegen/Bearbeiten; ohne Haken To-do mit
  „✓ Buchen“; mit „Beleg kommt per Mail“ bucht LUNA nie selbst.
- Ergebnis: `core/abos.py` (Kreis `ABO-`, Turnus woechentlich bis jaehrlich, Monatsende-sicher, Faelligkeit genau einmal
  erledigt: gebucht/Beleg/uebersprungen, Abgleich mit gebuchten Belegen derselben Stammdaten-Nummer ±25 %, taeglicher Lauf
  05:00 im Bot), To-dos auf der Hauptseite („faellig – buchen?“, „Beleg fehlt“ nach 10 Tagen, „kuendigen bis …“ 14 Tage
  vorher; die Kuendigungs-Erinnerung laeuft als To-do statt Kalendertermin), CFO-Hinweis „wiederkehrend fehlt“ schweigt fuer
  Firmen mit Abo; API `/api/finanzen/abos*`; LUNA-OS Reiter Finanzen -> Abos (Liste, Kosten je Monat/Jahr, Formular, Detail
  mit Buchen/Ueberspringen/Beenden) und „Als Abo anlegen“ bei erkannten Abos. Tests `test_abos.py` (6) + 9 Gegenproben.
- Bestand: Eigenbelege `EB-` (einzeln), Stammdaten mit Vertraegen (Etappe 14), Abo-Erkennung aus Belegen, CFO-Hinweis
  „wiederkehrend fehlt“. Es gibt keine Vorlage, die regelmaessig faellig wird.
- Ziel / Scope:
  - **Abo-Vorlage** `ABO-00001` (eigener Kreis, `AB-` ist die Auftragsbestaetigung): Bezeichnung, Stammdaten-Nummer
    (L-/P-), Ausgabe/Einnahme, Betrag, Kategorie, **Turnus** (woechentlich, monatlich, alle 2 Monate, vierteljaehrlich,
    halbjaehrlich, jaehrlich), erste Faelligkeit, optional Ende/Kuendigungsdatum und Kuendigungsfrist, Zahlungsweg,
    Vertragsnummer, „Beleg kommt per Mail“ ja/nein, pausieren/beenden (nichts wird geloescht).
  - **Bei Faelligkeit** (CFO-Lauf 05:00): To-do „Abo X faellig – buchen?“ auf der Hauptseite (+ optional Telegram ✅/❌);
    ✅ erzeugt einen Eigenbeleg mit Verweis auf das Abo (Datum = Faelligkeit, aenderbar). Kommt fuer das Abo schon ein
    Mail-Beleg derselben Firma mit aehnlichem Betrag (±25 %) im Zeitraum, wird das Abo automatisch als erfuellt markiert
    und nichts doppelt gebucht.
  - **Abo-Uebersicht** im Finanzbereich: alle aktiven Abos, Kosten je Monat (jaehrlich / 12) und je Jahr, naechste
    Faelligkeit, Kuendigungstermine; Kalender-Erinnerung X Tage vor Ablauf der Kuendigungsfrist.
  - **Aus erkannten Abos anlegen:** Firma mit „🔁 Abo erkannt“ (Etappe 14) bekommt „Als Abo anlegen“ mit Vorbelegung.
- Nicht enthalten: wiederkehrende **Ausgangsrechnungen** an Kunden (z. B. Saison-Sponsoring monatlich) -- spaeter als
  eigene Etappe moeglich.
- Gate: Monats- und Jahresabo laufen ueber einen Jahreswechsel korrekt (Faelligkeiten nachgerechnet); ✅ bucht genau einen
  Eigenbeleg; ein passender Mail-Beleg verhindert die Doppelbuchung; Kuendigung stoppt kuenftige Faelligkeiten; Tests +
  Gegenprobe; Browser-Test; CEO-Abnahme.
- Verifikation (vorab): `pytest` gruen; Beispiel iCloud 9,99 EUR monatlich ab 22.07.: Faelligkeiten 22.08., 22.09., ...;
  Developer-Programm 99 EUR jaehrlich ab 23.05.2026 -> 23.05.2027; 31.01. monatlich -> 28./29.02., 31.03.
- Risiko: Doppelbuchung (Abo-Eigenbeleg + Mail-Beleg) -> Abgleich wie oben + Hinweis beim ✅; Buchung nie ohne CEO-Klick.
- Aufwand: mittel (1 Sitzung).
- Dokumentation: Changelog, Roadmap, Register, `docs/datenfluesse.md`, Verfahrensdokumentation (Dauervorgaenge).

### Etappe 16: TKP-Kalkulation in Preisliste und Angeboten

- Status: umgesetzt (CEO-Go 2026-09-29), Deploy + Abnahme offen
- Entscheidungen (CEO 2026-09-29): (1) OMR-Vorschlaege im System anzeigen und im Angebot per Haken als Vergleich **mit Link**
  zeigen; (2) Spannen/Produktion „erstmal deine Rechnung“; (3) Rechnung Kontakte x TKP im Angebot an-/abwaehlbar.
- Ergebnis: `core/katalog.py` (`OMR`, `TKP_STANDARD`, `tkp_preis`, `kalkulation_texte`; Kataloge von vorher bekommen die
  Startwerte: Post 52.000 Kontakte, TKP 20–30, 260 EUR Produktion; Story 34.000, 20–30, 100 EUR; Reel Standalone 37.000, 30–40,
  490 EUR; Reel-Integration 37.000, 25–35, 125 EUR -- heutige Preise bleiben beim Minimum, nur Story 600 -> 780 EUR), Angebots-
  Positionen mit TKP (Preis rechnet der Server nach, eingefroren), Schalter `tkp_zeigen`/`omr_zeigen`, PDF-Block mit Rechnung je
  Format, OMR-Vergleich und klickbarem Quellen-Link, Preisliste mit Spanne 20–40 EUR + OMR; LUNA-OS: Katalog-Editor mit
  TKP-Zeile je Format (Kontakte, TKP min/max, Produktion, OMR-Vergleich, Preisspanne), Angebots-Editor mit TKP je Position,
  „Community-Fit“ (Standard/Mitte/oben) und zwei Haken. Tests `test_tkp.py` (5) + 8 Gegenproben, Browser-Test, PDF gesichtet.
- Abgleich (Live-Katalog 2026-09-29 vs. OMR „Influencer Preisliste 2026“, Stand 08.05.2026 -- Instagram-Post 20–30 EUR,
  Story 20–50 EUR, Reel/TikTok 25–50 EUR, YouTube-Video 60–100 EUR TKP; Preis steigt u. a. mit Nische/Zielgruppen-Fit,
  Engagement, Content-Qualitaet, Nutzungsrechten, Exklusivitaet, Saison):
  | Format | Kontakte | Preis | TKP heute (ohne Produktion) | OMR |
  |---|---|---|---|---|
  | Feed-Post | 52.000 | 1.300 EUR | ca. 20 EUR (bei ca. 260 EUR Produktion) | 20–30 EUR |
  | Reel Standalone | 37.000 | 1.600 EUR | ca. 31 EUR (450 EUR Produktion) | 25–50 EUR |
  | Reel-Integration | 37.000 | 1.050 EUR | 16–28 EUR (Produktionsanteil offen) | 25–50 EUR |
  | Story-Serie | 34.000 | 600 EUR | ca. 15 EUR | 20–50 EUR (**heute darunter**) |
  Der Preislisten-Text („je nach Format 12–30 EUR ... am unteren Rand“) stimmt fuer Story nicht mehr.
- Ziel / Scope:
  - **Katalog rechnet statt fester Preise** (fuer Reichweiten-Formate): Kontakte (Median 90 Tage) x TKP / 1.000 +
    Produktionspauschale, gerundet (z. B. auf 10 EUR). Je Format **TKP-Spanne** (Standard/Minimum und Maximum) und
    Produktionspauschale; Formate ohne verlaessliche Reichweite (X, App, Stadion, Kanaele im Aufbau) bleiben Festpreise.
  - **Im Angebot:** Regler „Community-Fit“ je Angebot (und je Position abweichend) -- TKP zwischen Minimum und Maximum,
    Standard = Minimum; Vorschau des Preises je Stufe; der gewaehlte TKP wird mit dem Angebot festgeschrieben (spaetere
    Katalogaenderung aendert nichts). PDF zeigt den Preis; Kalkulation (Kontakte x TKP) optional sichtbar.
  - **Preisliste:** Kalkulationstext und Beispielrechnung werden aus den Werten erzeugt (keine veralteten Zahlen mehr);
    Zuschlaege (Nutzungsrechte, Whitelisting, Exklusivitaet ...) bleiben wie sie sind.
  - **Kontakte** vorerst von Hand im Katalog; spaeter automatisch aus den Meta-Exporten (Etappe 3c).
- Gate: Beispielrechnungen je Format von Hand nachgerechnet (TKP 20/25/30); bestehende Angebote unveraendert; Angebot mit
  TKP 28 fuer einen passenden Kunden -> Preis im PDF korrekt; Tests + Gegenprobe; CEO-Abnahme von Editor und PDF.
- Verifikation (vorab): Feed-Post 52.000 Kontakte, Produktion 260 EUR: TKP 20 -> 1.300 EUR, TKP 25 -> 1.560 EUR, TKP 30 ->
  1.820 EUR; Story 34.000 Kontakte, Produktion 100 EUR: TKP 20 -> 780 EUR, TKP 30 -> 1.120 EUR.
- Risiko: Preisaenderung fuer Kunden -> nur neue Angebote; Rundung nachvollziehbar; Preisliste nur mit CEO-Freigabe
  veroeffentlichen (Oeffentlichkeit = CEO-Tor).
- Aufwand: mittel (1 Sitzung). Unabhaengig von Etappe 15.
- Dokumentation: Changelog, Roadmap, Register (TKP-Spannen, Quelle OMR), `docs/datenfluesse.md`.

### Etappe 17: Aus einer Collab-Anfrage ein Angebotsentwurf

- Status: **verworfen** (CEO 2026-09-29: „brauchen wir so nicht, ich lege das manuell an“ -- Unternehmen schreiben nicht an
  LUNAs Adresse, sie bekommen sie nur beim Angebotsversand; die Anbindung an das Meta-Postfach ist verworfen). Nicht bauen.
- Urspruenglich: geplant (Antrags-Durchsicht 2026-09-29, Antrag „Collab-CRM um KI-gestuetzte Lead-Qualifizierung und
  Angebotsentwuerfe erweitern“, CRO; Eigenbau statt der geschaetzten 2.500–5.000 EUR)
- Ziel / Scope: im Collab-CRM (Firma/Nachricht) ein Knopf „Angebot entwerfen“: legt -- falls noetig -- die Firma mit
  K-Nummer an, schlaegt passende Katalog-Formate vor (aus dem Anfragetext, regelbasiert, optional lokales Backoffice-
  Modell), setzt TKP-Stufe Standard und oeffnet den Angebots-Editor als Entwurf. Kein Versand ohne CEO (Oeffentlichkeit).
- Gate: echte Beispiel-DM -> Entwurf mit plausiblen Formaten; nichts wird versendet; Tests + Gegenprobe.
- Aufwand: mittel. Abhaengig von Etappe 16 (TKP) -- erfuellt.

### Etappe 18: Zahlungsbedingungen und Vorkasse mit Payment-Check im Kalender

- Status: umgesetzt (CEO-Go 2026-09-30), Deploy + Abnahme offen
- Ergebnis: `core/zahlungsbedingungen.py` (pruefen/Vorkasse-Betrag/Frist/Texte); Angebot-Feld `zahlung` (leeres
  Zahlungsziel = Kundendaten, sonst 14), Satz in Angebots- und AB-PDF; Auftrag friert `vorkasse_cent`/`vorkasse_faellig`
  ein (Vorkasse vom Geldanteil, Barter-Ware bleibt der Schlussrechnung); `RechnungStore.entwurf_aus_auftrag(vorkasse=True)`
  -> Vorkasse-Rechnung `art="anzahlung"` (Leistungsdatum optional: „folgt gemaess Auftrag“), Schlussrechnung mit
  `abzuege` nach Zuschlaegen/Rabatt (PDF-Titel „Schlussrechnung“, Zeilen „Auftragssumme“ + „abzgl. Vorkasse RE-...“),
  Sperren unter der Buchhaltungs-Sperre (keine zweite Vorkasse, keine Vorkasse nach der Rechnung, abgezogene Vorkasse
  nicht stornierbar, 100 % Vorkasse -> keine Schlussrechnung noetig). Kalender: „💶 Payment-Check: Vorkasse|Rechnung
  RE-... (Betrag) – Firma“ am Faelligkeitstag 09:00; das Loeschen bei Zahlung/Storno gab es schon (`core/erinnerungen.py`,
  die Ausgangslage oben war insoweit falsch). To-do „Vorkasse-Rechnung erstellen“; Vorkasse zaehlt nicht als
  „berechnet“. LUNA-OS: Block „💶 Zahlungsbedingungen“ im Angebots-Editor mit Vorschau Vorkasse/Rest, Auftrag zeigt
  Bedingungen, Vorkasse, Rechnungen und Knopf „💶 Vorkasse-Rechnung erstellen“, Rechnungen mit Art. Nebenbei (CEO):
  Titel in „Zu erledigen“ klickbar (auch Enter). Tests `test_zahlungsbedingungen.py` (8) + 8 Gegenproben, Suite 1017
  gruen, Headless-Chrome-Test, PDFs gesichtet.
- Entscheidungen (CEO 2026-09-30): (1) Vorkasse als eigene Vorkasse-Rechnung, Schlussrechnung zieht ab; (2) Standard-Frist
  7 Tage nach Auftragsbestaetigung, im Angebot aenderbar; (3) Payment-Check auch fuer normale Rechnungen, Termin wird bei
  Zahlung geloescht; (4) Vorkasse wird **pro Angebot** entschieden -- keine Standard-Vorkasse je Kunde.
- Ausgangslage (Code-Stand 2026-09-30): Zahlungsziel gibt es nur als Tage je Kunde (`kunden.zahlungsziel_tage`) und je
  Rechnung (0-120 Tage, Standard 14). **Angebot und Auftragsbestaetigung nennen keine Zahlungsbedingungen.** Je Auftrag
  ist genau **eine** Rechnung moeglich -- Vorkasse/Anzahlung geht heute nicht. Beim Festschreiben einer Rechnung legt LUNA
  einen Termin „Rechnung ... faellig“ an; bei Zahlungseingang bleibt der Termin stehen.
- Ziel / Scope:
  - **Zahlungsbedingungen im Angebot einstellbar** (werden in Auftrag und Rechnung uebernommen, eingefroren wie Positionen):
    Zahlungsziel in Tagen (Vorschlag aus dem Kunden, sonst 14) und optional **Vorkasse** als **Prozent des Auftrags** oder
    **fester Euro-Betrag**, faellig **N Tage nach Auftragsbestaetigung** (Standard 7) oder zu einem festen Datum.
    Optionaler Zusatztext. Vorschau im Editor: „Vorkasse 50 % = 1.300,00 EUR, Rest 1.300,00 EUR 14 Tage nach Rechnung“.
  - **PDF-Text** in Angebot, Auftragsbestaetigung und Rechnung, z. B. „Zahlungsbedingungen: 50 % Vorkasse (1.300,00 EUR)
    bis 7 Tage nach Auftragsbestaetigung, Rest zahlbar innerhalb von 14 Tagen nach Rechnungsstellung ohne Abzug.“
  - **Vorkasse-Rechnung** (Vorschlag, Entscheidung 1): Knopf „Vorkasse-Rechnung erstellen“ im Auftrag -> eigene Rechnung
    `RE-` ueber den Vorkasse-Betrag (Art „Anzahlung“, Faelligkeit = Vorkasse-Frist). Zahlungseingang, Ueberfaellig-Meldung
    und Mahnwesen funktionieren damit wie bei jeder Rechnung. Die **Schlussrechnung** aus dem Auftrag zieht die Anzahlung
    ab („abzgl. Anzahlung RE-... vom ...“) und nennt nur den Rest; der Kleinunternehmer-Waechter und das Journal zaehlen
    den Umsatz nicht doppelt.
  - **Payment-Check im Kalender:** Sobald ein Auftrag mit Vorkasse entsteht bzw. die Vorkasse-Rechnung festgeschrieben
    wird, legt LUNA in ihrem Kalender einen Termin „💶 Payment-Check: Vorkasse AB-... (1.300,00 EUR) -- Firma“ am
    Faelligkeitstag 09:00 an (CEO eingeladen, wie bei den Angebots-Erinnerungen). **Wird die Zahlung vorher erfasst, loescht
    LUNA den Termin** -- das gilt dann auch fuer die bestehenden „Rechnung ... faellig“-Termine. Ohne Zahlung bis zum Termin
    zusaetzlich Hinweis in „Zu erledigen“ (wie ueberfaellige Rechnungen).
- Nicht im Scope: Standard-Vorkasse je Kunde (CEO: pro Angebot), Skonto, Ratenplaene mit mehr als zwei Teilen, automatischer Zahlungsabgleich mit dem Konto.
- Gate: Angebot mit 50 % Vorkasse -> Auftrag -> Vorkasse-Rechnung (Betrag, Frist, PDF-Text korrekt) -> Termin im Kalender ->
  Zahlung erfassen -> Termin weg -> Schlussrechnung mit Abzug, Rest korrekt; Umsatz nur einmal gezaehlt; Angebot ohne
  Vorkasse unveraendert (alte Angebote/Auftraege/Rechnungen unveraendert); Tests + Gegenproben; CEO-Abnahme von Editor
  und PDFs.
- Risiko: Rundung bei Prozent (auf volle Cent, Rest = Summe - Vorkasse, damit nichts verloren geht); festgeschriebene
  Belege duerfen sich nicht aendern (neue Felder nur fuer neue Belege); Kalender-Zugang faellt aus -> Hinweis wie bisher.
- Aufwand: mittel bis gross (1-2 Sitzungen).
- Dokumentation: Changelog, Roadmap, Register (Entscheidungen), `docs/datenfluesse.md` (Kalender-Termine, neue Felder),
  Verfahrensdokumentation (Anzahlungs- und Schlussrechnung).

### Etappe 19: Altrechnungen uebernehmen (vor LUNA geschrieben) inkl. Zahlung und Mahnstufe

- Status: live (CEO-Go 2026-09-30: „neue Rechnungen anlegen, aber die alten Nummern nutzen“); uebernommen 2026-09-30:
  RG-18032026 und RG-20092026 (Hands of God, bezahlt), RG-11052026 (Kiez Alm, offen -- Mahnstufen setzt der CEO)
- Ergebnis: `RechnungStore.alt_erfassen` -- Originalnummer (nicht aus LUNAs Kreisen, eindeutig) + Original-PDF
  unveraendert, Datensatz wie eine festgeschriebene Rechnung (`alt: true`, Faelligkeit leer = sofort), kein `RE-`-
  Eintrag, zaehlt zum Umsatz; `MahnStore.alt_erfassen` -- schon verschickte Mahnung als naechste Stufe
  (`<Rechnung>-M<Stufe>`, kein `MA-`-Kreis, optional PDF, als versendet markiert), danach Mahnwesen wie gewohnt (nach
  Stufe 3: „Mahnbescheid oder Inkasso pruefen“). Endpunkte `POST /api/finanzen/rechnungen/alt`,
  `/api/finanzen/rechnungen/<nr>/altmahnung`; LUNA-OS: „+ Altrechnung erfassen“ in Rechnungen, „📨 Mahnung vor LUNA
  erfassen …“ im Rechnungs-Detail. Tests `test_altrechnungen.py` (4) + 8 Gegenproben, Browser-Test.
- Anlass: Kundenrechnungen, die der CEO vor LUNA selbst geschrieben hat (eigene Nummern `RG-TTMMJJJJ`): Hands of God
  GmbH K-00008 (RG-18032026 385,12 EUR, RG-20092026 186,31 EUR, beide ueberwiesen) und Kiez Alm Gastro GmbH K-00009
  (RG-11052026 4.000,00 EUR, offen, 1.-3. Mahnung bis 31.08.2026). Eine neue `RE-`-Rechnung darueber waere eine zweite
  Rechnung fuer dieselbe Leistung -- das darf nicht sein.
- Ziel / Scope: „Altrechnung erfassen“: Original-PDF hochladen, Originalnummer, Datum, Kunde, Betrag, Faelligkeit ->
  unveraenderlicher Rechnungs-Datensatz ohne `RE-`-Nummer (der eigene Nummernkreis bleibt lueckenlos), zaehlt zum Umsatz
  (Kleinunternehmer-Waechter, EUeR, Export). Zahlung erfassen wie bei jeder Rechnung. Bereits verschickte Mahnungen als
  Dokumente mit Datum anhaengen und die erreichte Mahnstufe setzen; das Mahnwesen (Etappe 10) macht von dort weiter
  (nach der letzten Mahnung: To-do „Mahnbescheid oder Inkasso pruefen“).
- Danach: Hands of God als bezahlt durchbuchen (Zahlungsdatum laut EUeR-Liste), Kiezalm nur anlegen (CEO bucht und
  setzt die Mahnstufe selbst).
- Gate: Altrechnung erscheint in Rechnungen/Umsatz/Export mit Originalnummer, `RE-`-Kreis unberuehrt; Zahlung und
  Mahnstufe funktionieren; Tests + Gegenproben.
- Aufwand: klein bis mittel.

### Etappe 20: EZB-Kurs fuer Fremdwaehrungs-Belege automatisch

- Status: umgesetzt (CEO 2026-09-30: „EZB-Kurs bei Dollar nehmen“, „Sehr gut“), Deploy + Abnahme offen
- Ergebnis: `core/wechselkurse.py` (`EzbKurse` mit Zwischenspeicher `buchhaltung/wechselkurse.json`, Wochenende/
  Feiertag = letzter Kurs davor, eine Luecke gilt als gesichert, sobald ein spaeterer Kurs bekannt ist; `euro_vorschlag`,
  `kurse_ergaenzen`), laeuft nach jedem Upload in LUNA-OS und im 15-Minuten-Abruf des Bots; der Termin „Euro-Betrag
  eintragen“ entfaellt bei vorhandenem Kurs; Beleg-Detail zeigt Kurs, Rechnung und vorbelegte Notiz. Nie automatisch
  gebucht. Tests `test_wechselkurse.py` (3) + 5 Gegenproben; `orchestrator/tests/conftest.py` schaltet EZB-Abrufe in
  Tests ab (`LUNA_EZB_OFFLINE`).
- Ziel / Scope: Belege in Fremdwaehrung (USD usw.) bekommen beim Eingang den Euro-Betrag vorgeschlagen: EZB-
  Referenzkurs des Rechnungstags (Wochenende/Feiertag: letzter Kurs davor) von `data-api.ecb.europa.eu`, Kurs und Datum
  in der Notiz (wie bei der Nachbuchung vom 30.09.). Der Kalender-Termin „Euro-Betrag eintragen“ entfaellt, wenn der Kurs
  da ist; ohne Netz bleibt es beim heutigen Weg. Kurse werden lokal zwischengespeichert.
- Gate: Beispiel-USD-Beleg ergibt den Euro-Betrag wie von Hand gerechnet; Ausfall der EZB-Schnittstelle bricht nichts;
  Tests + Gegenprobe; `docs/datenfluesse.md` (neue externe Verbindung).
- Aufwand: klein.

### Etappe 21: Artikel-Kalkulation (Einkauf, Kosten, Marge) und Lagerbestand im Leistungskatalog

- Status: umgesetzt (CEO-Go 2026-09-30: „die fehlenden einbauen und fuer physische Ware schon mal einen moeglichen
  Lagerbestand als Funktion“ -- aktuell keine physische Ware, Funktion fuer die Zukunft), Deploy offen
- Ergebnis: Katalog-Artikel mit internen Kosten (`kosten`: Einkauf, Fremdleistung, Material, Reise, Sonstiges) ->
  `katalog.kalkulation` (Kosten, Deckungsbeitrag, Marge, Warnung unter `mindestmarge_prozent`, Standard 30 %); Angebots-
  Editor zeigt „🔒 Intern“ Kosten/DB/Marge (nie im PDF, Test). Lager: `physisch`, `mindestbestand`, `lager_start`;
  `core/lager.py` -- Bestand = Zugaenge/Korrekturen (Ereignis `lager_bewegung`) minus Verkaeufe laut festgeschriebenen
  Rechnungen ab Lager-Start, Storno bucht zurueck; To-do „Lagerbestand niedrig“; Endpunkte `GET /api/finanzen/lager`,
  `POST /api/finanzen/lager/<id>/bewegung`; LUNA-OS: Katalog „Kalkulation & Lager“ je Artikel, Mindestmarge, Kachel
  „📦 Lager“ mit Bewegungs-Formular. Tests `test_kalkulation_lager.py` (5) + 8 Gegenproben, Browser-Test.
- Zusatz Lager: Artikel optional als „physische Ware“ mit Bestand, Mindestbestand, Einkaufspreis; Zugang (Einkauf,
  optional mit Eingangsbeleg) und Abgang (Rechnung/Angebot angenommen) als Ereignisse; Warnung unter Mindestbestand.
- Ausgangslage: Eigene Artikel anlegen geht schon -- LUNA-OS „Angebote & Auftraege“ -> Katalog (Name, Preis, Einheit,
  Gruppe, bei Reichweiten-Formaten TKP-Rechnung); sie erscheinen im Angebots-Dropdown. Einkaufspreise, Kosten und
  Marge gibt es noch nicht; eine Warenwirtschaft mit Lager gibt es nicht.
- Ziel / Scope: je Artikel interne Kosten (Einkaufspreis, Produktion, Fremdleistung/Freelancer, Material, Reisen) ->
  Deckungsbeitrag und Marge in EUR/% neben dem Verkaufspreis, Warnung unter Mindestmarge; im Angebot (nur intern, nie im
  PDF) Summe Kosten, Deckungsbeitrag, Marge. Optional spaeter: Lagerbestand fuer physische Ware (nur wenn benoetigt).
- Gate: Kalkulation je Artikel und im Angebot stimmt mit Handrechnung; nichts davon im Kunden-PDF (Gegenprobe).
- Aufwand: mittel.

### Etappe 22: Firmendaten recherchieren und auf Knopfdruck uebernehmen

- Status: umgesetzt (CEO 2026-09-30: „Mach das“), Deploy offen
- Ergebnis: `core/firmendaten.py` -- Website (hinterlegt oder Brave „<Name> Impressum“, Portale wie North Data/LinkedIn
  ausgeschlossen) -> Impressum (uebliche Pfade, sonst Impressums-Link der Startseite, nur dieselbe Website) -> Muster fuer
  Strasse/PLZ/Ort, USt-ID, Handelsregister, Telefon, Rechnungs-Mail (nur rechnung@/billing@ ...); Vorschlaege nur fuer
  leere Felder, mit Quelle (Ereignis `firma_recherche`), Uebernehmen einzeln/alle oder Verwerfen (`firma_vorschlag_erledigt`,
  ueberschreibt nie von Hand Eingetragenes); keine Privatpersonen, nie die eigene Firma. Neues Stammdatenfeld
  `handelsregister`. Wochenlauf im Bot (Sonntag ab 06:00, bis 8 Firmen, Pause 30 Tage, Hinweis im Morgen-Briefing).
  Endpunkte `POST /api/crm/kunden/<nr>/recherche`, `/vorschlaege`; Kunden-Detail zeigt Vorschlaege + „🔎 Fehlende Daten im
  Netz suchen“. Echter Probelauf (nur lesend): Kiez Alm, Hands of God, Grover vollstaendig; Calumet, Canva nichts
  (auslaendisch/anderes Format). Tests `test_firmendaten.py` (6) + 9 Gegenproben, Browser-Test.
- Ziel / Scope: Fuer Kunden, Lieferanten und Partner mit Luecken (Adresse, USt-ID, Website, Handelsregister, Rechnungs-
  Mail) sucht LUNA oeffentliche Angaben (Web-Suche ueber Brave, Impressum der Firmen-Website) und zeigt je Feld einen
  Vorschlag mit Quelle; „Uebernehmen“ je Feld oder alle. Regelmaessig (z. B. woechentlich) prueft ein Agent die Luecken
  und legt Vorschlaege ab -- uebernommen wird nie automatisch. Nur oeffentliche Firmendaten, keine Privatpersonen.
- Gate: Vorschlag fuer eine bekannte Firma mit korrekter Quelle; nichts ohne Klick uebernommen; Kosten im Rahmen
  (Brave-Kontingent); Tests + Gegenprobe; `docs/datenfluesse.md`.
- Aufwand: mittel.

### Etappe 23: Provisionsmodell (Affiliate) in Angebot, Auftrag und Abrechnung

- Status: umgesetzt (CEO 2026-09-30: „im Angebot mit einem Preis ausstatten, z. B. 5 Euro pro verkauftem Artikel oder
  10 % ... um nach der Collab abrechnen zu koennen; auf der Rechnung steht dann ein richtiger Euro-Wert“), Deploy offen
- Ergebnis: Position mit `provision` (`stueck`: Satz in Cent, `prozent`: Satz in %); ohne Abrechnung Betrag 0 und
  „nach Abrechnung“ (Angebot, Auftrag, PDFs, Detail), mit Abrechnung (verkaufte Stueck bzw. vermittelter Umsatz) rechnet
  der Server den Euro-Betrag (kaufmaennisch gerundet). Summen: Provision ohne Zuschlag/Rabatt, danach addiert; Vorkasse
  nur vom Festpreis-Anteil. Festschreiben einer Rechnung mit offener Provision gesperrt. Katalog: Standard-Preismodell je
  Artikel (`provision_art`/`provision_wert`, Editor „Preismodell“), Preisliste zeigt den Satz statt 0,00 EUR. LUNA-OS:
  Provisionsfelder in der Positionszeile, im Rechnungs-Editor Feld „Abrechnung“. Tests `test_provision.py` (6) +
  8 Gegenproben, Suite gruen, Headless-Chrome-Test, PDF gesichtet.
- Ziel / Scope: Katalog-Artikel „Affiliate-Partnerschaft“ (live seit 2026-09-30, Gruppe „Partnerschaften“) bekommt ein
  Provisionsmodell: **fester Betrag je verkauftem Artikel** (z. B. 5,00 EUR) oder **Prozent vom Umsatz** (z. B. 10 %).
  Im Angebot/Auftrag steht das Modell statt einer Summe („5,00 EUR je verkauftem Artikel“), die Angebotssumme weist die
  Provision als „nach Abrechnung“ aus. Nach der Collab: Abrechnung im Auftrag -- verkaufte Stueck bzw. vermittelter
  Umsatz eintragen -> LUNA rechnet den Euro-Betrag aus und legt die Rechnung mit echtem Betrag an (Grundlage der
  Rechnung: Menge x Satz bzw. Umsatz x %).
- Gate: Angebot mit Provisionsposition zeigt das Modell, keine Phantasiesumme; Abrechnung ergibt den handgerechneten
  Betrag; Tests + Gegenproben.
- Aufwand: mittel.

### Etappe 24: Firmenakte -- Dokumente und Mailverlauf je Firma

- Status: umgesetzt (CEO-Go 2026-09-30), Deploy offen
- Ergebnis: `core/firmenakte.py` -- Upload je Firma (Art, Titel, Datum, Bezug z. B. RG-11052026; Geschaeftsbrief 6 Jahre),
  Mails im 15-min-Poll des Bots: vom CEO weitergeleitete Nicht-Beleg-Mails (Original-Absender, DKIM-geprueft, Text
  darueber = Notiz) und Mails mit LUNA in CC/BCC oder vom CEO -> `.eml` + PDF-Ansicht in der Akte; Zuordnung ueber
  exakte Adressen (Rechnungs-Mail, Rechnungs-Absender, Ansprechpartner) oder Domain (nie Freemail); keine/mehrere Firmen
  -> To-do „Mail zuordnen“. Endpunkte `/api/crm/kunden/<nr>/akte` (GET/POST), `/api/crm/akte/<id>/datei`,
  `/api/crm/akte/offen`, `/api/crm/akte/<id>/zuordnen`; Rechnungs-Detail zeigt Dokumente mit Bezug. LUNA-OS: „📁 Akte“ in der
  Kunden-Detailansicht, Zuordnen-Fenster. Beim Testen gefunden und behoben: `firmen()` liefert keine Ansprechpartner.
  Tests `test_firmenakte.py` (7) + 8 Gegenproben, Browser-Test.
- Ausgangslage: Dokumente gibt es nur an Belegen/Rechnungen/Angeboten; Mails werden nur fuer Angebote (Antworten) und im
  Collab-CRM (Phase 19, Instagram-Firmen) mitgeschrieben -- nicht an den Stammdaten-Firmen (K-/L-/P-).
- Ziel / Scope:
  - **Dokumente je Firma:** Upload in der Kunden-Detailansicht (PDF, Bild, Office) mit Titel, Datum, Art (z. B.
    Anwaltsschreiben, Vertrag, Korrespondenz) und optional Bezug (Rechnung/Auftrag); unveraendert abgelegt mit Hash und
    Aufbewahrung (Geschaeftsbrief 6 Jahre). In der Rechnung sichtbar, wenn Bezug gesetzt (z. B. Kiezalm RG-11052026).
  - **Mail an LUNA weiterleiten:** ist die weitergeleitete Mail kein Beleg, ordnet LUNA sie ueber den Original-Absender
    (Mail/Domain aus Stammdaten, Ansprechpartner, Website) der Firma zu und legt sie als `.eml` + Lesefassung in der Akte ab;
    dein Text darueber wird Notiz. Ohne eindeutige Firma: Liste „Mail zuordnen“ in LUNA-OS.
  - **LUNA in CC/BCC:** Mails, in denen LUNAs Adresse in CC/BCC steht, landen genauso in der Akte der Firma (Absender bzw.
    Empfaenger). Nur Lesen/Ablegen, LUNA antwortet nie selbst.
  - Akte zeigt Dokumente + Mails chronologisch (Timeline), Suche im Titel.
- Gate: Anwaltsschreiben hochgeladen und an RG-11052026 sichtbar; weitergeleitete Mail der Anwaeltin landet bei
  K-00009; CC-Mail an einen Kunden landet in dessen Akte; unklare Mail in „zuordnen“; Tests + Gegenproben.
- Aufwand: mittel.

### Etappe 25: Zeiterfassung und Nachkalkulation je Auftrag

- Status: umgesetzt (CEO-Go 2026-09-30), Deploy offen
- Entscheidungen (CEO 2026-09-30): Stundensatz = Brutto-Monatslohn des Arbeitgebers (5.061,21 EUR, 40 h/Woche ->
  29,20 EUR/h, nur kalkulatorisch); Fahrzeit zaehlt; Kilometer erfassen, **Adresse eingeben und LUNA rechnet** (Start =
  Firmenadresse, Hin + Rueck); Stunden **nur intern** -- nie im PDF, nie beim Kunden, **kein Kostenpunkt in der EUeR**.
  **Revidiert 2026-09-30:** auch die Kilometer sind nur kalkulatorisch (Firmenwagen des Hauptarbeitgebers, real keine
  Kosten; Ziel: wissen, was es als Selbststaendiger kosten wuerde) -- **kein Eigenbeleg, keine Buchung**.
- Ergebnis: `core/zeiterfassung.py` (Einstellung, Start/Stopp, manuell inkl. ueber Mitternacht, Zuordnen, Storno,
  Fahrt kalkulatorisch 0,30 EUR/km (korrigierbar, letzter Wert gilt), Nachkalkulation: Auftragssumme - Arbeitszeit -
  Fahrtkosten (beides kalkulatorisch) = Deckungsbeitrag, effektiver Stundenlohn), `core/routen.py` (OpenStreetMap: Nominatim + OSRM, kostenlos,
  Zwischenspeicher; Google Maps waere kostenpflichtig = CEO-Tor, nicht angebunden). Telegram: „Bin auf dem Weg zu <Firma>“
  (Auftrag automatisch, bei mehreren Knoepfe; ohne Auftrag -> To-do „Zeit zuordnen“), „Bin wieder zuhause“/„Fahre nach
  Hause“ stoppt und schlaegt km vor (✅/✏️ andere km oder Adresse/🚫), Erinnerung nach 10 h. LUNA-OS: Auftrags-Detail
  „⏱ Zeiten & Nachkalkulation“ (🔒 intern). Test beweist: EUeR vor/nach Zeiterfassung gleich. Tests
  `test_zeiterfassung.py` (8) + Gegenproben, Browser-/Telegram-Probe.
- Ziel / Scope:
  - **Stundensatz (intern):** Einstellung „kalkulatorischer Stundensatz“ (Empfehlung: Brutto-Stundenlohn des Arbeitgebers,
    siehe Entscheidung), nur fuer Kalkulation -- keine Buchung, keine Betriebsausgabe (Unternehmerlohn ist in der EUeR nicht
    abziehbar).
  - **Telegram:** „Bin auf dem Weg zu CR Container“ -> LUNA erkennt die Firma, waehlt den offenen Auftrag (bei mehreren:
    Knoepfe zur Auswahl) und startet die Zeit; „Bin wieder zuhause“ / „fertig“ stoppt sie und meldet Dauer + Kosten.
    Vergessener Stopp: Nachfrage nach 10 Stunden. Manuelle Eintraege (Datum, von-bis oder Dauer, Notiz) in LUNA-OS am Auftrag.
  - **Nachkalkulation am Auftrag:** Auftragssumme vs. Kosten (Stunden x Satz + dem Auftrag zugeordnete Belege, z. B.
    Material) -> Deckungsbeitrag und effektiver Stundenlohn; auch im Angebot als Planwert (Stunden schaetzen).
  - Optional: gefahrene Kilometer je Termin -> Fahrtkosten als echte Betriebsausgabe (0,30 EUR/km Pauschale) als Eigenbeleg.
- Gate: Start/Stopp per Telegram am richtigen Auftrag; manueller Eintrag; Nachkalkulation stimmt mit Handrechnung;
  Tests + Gegenproben.
- Aufwand: mittel.

### Etappe 26: Kalkulatorische Kosten in Finanzauswertung und Export (zuschaltbar)

- Status: live (deployt 2026-09-30, `911e8b1`, Neustart durch den CEO, live geprueft) -- CEO-Abnahme offen (CEO-Wunsch 2026-09-30: „fiktive Kosten auch
  anzeigen, aber abwaehlbar ... bei Exporten auswaehlen, ob sie mitgerechnet werden“)
- Ziel / Scope:
  - **Finanz-Uebersicht (LUNA-OS):** Schalter „Kalkulatorische Kosten zeigen“ (Standard: an, Wahl merkt sich der Browser).
    Eigener, klar markierter Block „Kalkulatorisch (nicht steuerlich)“: eigene Arbeitszeit (Stunden x Satz) und Fahrten
    (km x 0,30 EUR) je Monat und Jahr, dazu „Ergebnis inkl. kalkulatorischer Kosten“ **neben** dem echten Gewinn. Die
    echten Zahlen (Einnahmen, Ausgaben, Gewinn, EUeR) aendern sich dadurch nie.
  - **Exporte:** Haken „Kalkulatorische Kosten beilegen“ (Standard: aus). Journal-CSV: zusaetzliche Zeilen mit Art
    „kalkulatorisch“ (eigene Spalte, nicht in den Summen der echten Buchungen). Jahresabschluss-ZIP: zusaetzliche Datei
    `kalkulatorisch.csv` + Abschnitt in der Uebersicht, gekennzeichnet „keine Betriebsausgaben“. **EUeR-PDF, EUeR-Zahlen
    und GoBD-Index bleiben immer ohne kalkulatorische Kosten** -- fuer Steuerberater und Finanzamt nie vermischt.
- Gate: Ansicht mit/ohne Schalter; Export mit/ohne Haken; EUeR-Summen in allen Faellen identisch (Test + Gegenprobe).
- Aufwand: klein bis mittel.
- Ergebnis: `core/zeiterfassung.kalkulatorisch()` wertet die Zeit-Ereignisse je Jahr/Zeitraum aus (Arbeitszeit, Fahrten,
  je Monat); `Finanzen.uebersicht()` liefert sie als Zusatz `kalkulatorisch` mit `gewinn_inkl_cent`, Kennzahlen/EUeR
  unberuehrt. LUNA-OS V2: Kachel „Kalkulatorisch (nicht steuerlich)“ mit Schalter (Browser merkt sich die Wahl, Standard
  an), folgt dem gewaehlten Zeitraum. Exporte: Haken „Kalkulatorische Kosten beilegen“ (Standard aus) an Journal-CSV
  (eigener Block unter den echten Buchungen, Ueberschrift „KEINE Betriebsausgaben“ -- statt Zusatzspalte, damit die
  Buchungszeilen unveraendert bleiben) und Jahresabschluss-ZIP (`zusatz/kalkulatorisch.csv` + Hinweis in `LIESMICH.txt`,
  nicht im `index.xml`). Test `test_kalkulatorisch.py`: `euer.csv`, `journal.csv`, `index.xml` mit/ohne Haken
  byte-gleich, EUeR mit Zeiten = EUeR ohne Zeiten; Browsertest Schalter + beide Haken.

### Etappe 27: Plattform-Auszahlungen mit Erzielt-Zeitraum (Facebook-Monetarisierung)

- Status: live (deployt 2026-09-30, `b2aca93`, Neustart CEO); Nachtrag Jan/Maer/Jun gebucht (ER-2026-0131..0133) --
  CEO-Abnahme offen
- Analyse: 4 Facebook-Auszahlungen 2026 (23.01. 146,16 USD, 20.03. 191,74 USD, 22.06. 135,01 USD, 25.09. 282,37 USD).
  Erfasst ist nur 25.09. als `ER-2026-0002` (Einnahme 246,38 EUR = echter Bankeingang, EZB-Kurs haette 247,63 EUR
  ergeben). Das Meta-„Remittance“-PDF nennt je Posten Payout-Referenz, Zeitraum und Betrag; die Meta-Oberflaeche
  weicht davon ab (Juni-Auszahlung Posten 135,03 statt 135,01; Juli-Posten 70,23 statt 69,96) -> **PDF ist massgeblich**.
- Ziel / Scope:
  - Einnahme-Belege bekommen optional **Posten mit Erzielt-Zeitraum** (von/bis, Betrag in Originalwaehrung,
    Payout-Referenz) und die Zahlungs-ID. Beim Mail-/Datei-Import liest LUNA das Meta-Remittance-PDF selbst aus.
  - Finanzen: Kachel „Plattform-Einnahmen“ -- **erzielt je Monat** (nach Zeitraum) neben **ausgezahlt** (Zufluss),
    in USD und anteilig in EUR (Verhaeltnis Bankeingang/USD je Auszahlung).
  - **EUeR bleibt beim Zuflussprinzip** (§ 11 EStG): gezaehlt wird der Bankeingang am Zahlungstag; die Januar-
    Auszahlung (erzielt Nov./Dez. 2025) gehoert damit in 2026. Der Erzielt-Zeitraum ist reine Information.
  - Nachtrag der drei fehlenden Auszahlungen 23.01./20.03./22.06. als Einnahme-Belege (produktiver Datenwrite ->
    eigenes CEO-Go): Beleg = Remittance-PDF (CEO leitet die Meta-Mails an LUNA weiter), Betrag = Bankeingang laut
    Kontoauszug; ohne Kontoauszug EZB-Referenzkurs des Zahlungstags (CEO-Regel fuer USD) mit Hinweis.
  - `ER-2026-0002` bekommt die vier Posten aus seinem PDF nachgetragen.
- Gate: Test Parser (PDF-Text aus ER-2026-0002 -> 4 Posten, Summe = 282,37); EUeR mit/ohne Posten identisch;
  Kachel-Summe erzielt = Summe der Posten; Browsertest.
- Aufwand: mittel.
- Ergebnis: `core/plattform.py` (`remittance_lesen`, `posten_aus_text`, `auswertung`), Ereignis `eingang_posten` (nur
  von Hand, aendert keine Buchung), `GET /api/finanzen/plattform`, `POST /api/finanzen/belege/<nr>/posten`; Belege mit
  Meta-PDF brauchen keinen Nachtrag (Posten werden aus dem gespeicherten Text gelesen, ER-2026-0002 also sofort).
  Beleg-Ansicht „Erzielt-Zeitraeume“ (Tabelle + Eingabe von Hand), Finanz-Kachel „Plattform-Einnahmen“ (erzielt je
  Monat, Auszahlungen). Vorschlag beim Import nennt den Zeitraum. Tests `test_plattform.py` (EUeR mit/ohne Posten
  identisch), Browsertest. Nachtrag ohne Meta-Mails: Screenshot der Auszahlungsdetails als Beleg + Betrag laut
  Kontoauszug, Zeitraeume von Hand.

### Etappe 28: Mahnstufen und Mahnverfahren, Anwalts-Post in die Akte, Selgros-Positionen

- Status: live (deployt 2026-10-01, `0afc429`, Neustart CEO, live geprueft) -- CEO-Abnahme offen
- Ziel / Scope:
  - **Begriffe (CEO):** unsere Mahnungen heissen in LUNA **„Mahnstufe 1/2/3“** (Status, Listen, Handlungsbedarf,
    Telegram); die Ueberschrift auf dem Brief an den Kunden bleibt „1./2./3. Mahnung“ wie in den CEO-PDFs (bisher druckt
    LUNA bei Stufe 3 „Letzte Mahnung“).
  - **Status „Mahnverfahren“:** an einer offenen Rechnung eintragbar (Datum eingeleitet, durch wen, Notiz, Bezug auf ein
    Akte-Dokument), z. B. RG-11052026 seit 29.09.2026 durch RAin Marquardt (digital beim Gericht). Rechnung bleibt
    offen; Handlungsbedarf zeigt statt „dringend: Mahnbescheid/Inkasso pruefen“ den ruhigen Punkt „Mahnverfahren laeuft
    seit … – auf Zahlung oder Nachricht der Anwaeltin warten“ (Stufe „wenn Zeit ist“). Zahlung beendet es wie bisher.
  - **BF-49:** Mails, die eine eigene Ausgangsrechnung nennen (auch „Rechnung Nr. 11052026“ ohne Praefix) oder von einer
    in der Akte hinterlegten Kanzlei kommen, gehen in die Firmenakte statt in die Belege.
  - **BF-50:** Leser fuer Selgros/Transgourmet-Rechnungen: 24 Positionen mit GTIN, mehrzeilige Namen, **brutto je
    MwSt-Satz** (Kleinunternehmer), Summen-/Infozeilen ignorieren, Lieferant „Transgourmet Deutschland GmbH & Co. OHG
    (Selgros …)“; Kartenzahlungsbeleg mit gleicher Belegnummer automatisch als Zahlungsnachweis. Allgemein: zwei PDFs
    einer Mail mit derselben Belegnummer = Rechnung + Nachweis.
- Gate: Tests mit nachgebauten Texten (keine echten Kundendaten): Selgros 24 Positionen, Summe exakt; Anwalts-Mail ->
  Akte; Mahnverfahren-Status im Handlungsbedarf; Brief-Ueberschrift „3. Mahnung“; Suite + Doku-Check gruen.
- Aufwand: mittel.
- Ergebnis: `core/mahnungen.py` `STUFEN` (Status „Mahnstufe 1-3“) getrennt von `BRIEF` („1./2./3. Mahnung“ fuer PDF,
  Betreff, Telegram-Frage), Ereignis `rechnung_mahnverfahren` + `MahnStore.mahnverfahren_setzen`,
  `POST /api/finanzen/rechnungen/<nr>/mahnverfahren`, Rechnungsansicht mit Anzeige + Formular, Handlungsbedarf
  „Mahnverfahren laeuft seit …“ (nicht dringend). BF-49: `firmenakte.eigene_forderung` (volle Nummer, „Rechnung Nr.
  11052026“, Forderungs-/Anwaltsvokabular + Firmenname; Kosten-/Honorarnote an uns bleibt Beleg) -- Beleg-Eingang
  ueberspringt, Akte nimmt auf (auch Anhangtext). BF-50: `selgros_lesen` (Positionen brutto, Rundung je MwSt-Satz an die
  Summenzeile), Kartenzahlungsbeleg per Inhalt als Zahlungsnachweis. Tests `test_mahnverfahren.py`,
  `test_geschaeftspost.py` mit Gegenprobe, Browsertest.

### Etappe 29: Zeit-Tracker auf der Startseite

- Status: umgesetzt (CEO-Go 2026-10-01) -- Deploy offen. Kachel „⏱ Zeit“ neben dem Handlungsbedarf, Fenster mit
  Auftragswahl, Knopf wechselt sofort (vor der Serverantwort), Timer in Fenster/Kachel/Kopfzeilen-Chip/Seitenmenue,
  km nach dem Stoppen; Startzeit zusaetzlich als `start_ms` (Timer stimmt in jeder Geraete-Zeitzone; im Browsertest
  gefunden).
- Analyse: Start/Stopp gibt es schon (`POST /api/finanzen/zeit/start|stopp`, `core/zeiterfassung.py`), erreichbar aber nur
  im Auftrag und per Telegram.
- Ziel / Scope: Eigene Kachel „⏱ Zeit“ auf der Startseite (und im Seitenmenue). Klick oeffnet ein Fenster:
  laufenden Auftrag waehlen (nur Status „beauftragt“, zuletzt genutzter vorbelegt) -> „▶ Zeit starten“. Laeuft eine
  Zeit, wird der Knopf **sofort** zu „■ Zeit stoppen“ und ein Timer zaehlt sichtbar mit (hh:mm:ss) -- im Fenster, auf
  der Kachel und als kleine Anzeige oben in der Kopfzeile (auf jeder Seite, auch am iPhone). Nach dem Stoppen
  optional Fahrt-km (wie heute im Auftrag). Eine per Telegram gestartete Zeit erscheint genauso (gleiche Quelle).
- Gate: Browsertest Start -> Knopf/Timer wechseln ohne Neuladen -> Stopp; Kopfzeilen-Anzeige auf einer anderen Seite;
  Test: Start nur fuer beauftragte Auftraege.
- Aufwand: klein.

### Etappe 30: Auftrag „geliefert“ mit Lieferungen (Videos, Bilder, Links)

- Status: umgesetzt (CEO-Go 2026-10-01) -- Deploy offen. `core/lieferungen.py` (Ereignisse `lieferung_angelegt/_datei/
  _entfernt`, Ablage `lieferungen/<Auftrag>/`, Upload in 8-MB-Stuecken per `PUT`, kein Multipart), Status „Geliefert“
  mit Lieferdatum + „Wieder oeffnen“ (Grund Pflicht), Zeitsperre in `zeiterfassung._ziel`, Lieferungen im Auftrag und in
  der Firmenakte, `lieferungen/` aus Git und Deploy-Sync ausgenommen. Tests `test_lieferungen.py` mit Gegenprobe.
  Noch nicht: LUNA legt Lieferungen automatisch aus Mails/Reels ab (Funktion `datei_ablegen` steht bereit; Folgeschritt).
- Analyse: Auftrags-Status heute `beauftragt/erledigt/storniert`; „erledigt“ bedeutet bereits „fertig, bereit fuer die
  Rechnung“ (Handlungsbedarf „Rechnung schreiben“). Die Zeiterfassung sperrt nur stornierte Auftraege. Belege-Ablage
  (`buchhaltung/belege/`) ist ungeeignet fuer Videos: alles dort wird nach Google Drive kopiert (15 GB) und ist Teil des
  Kassenbuchs. Der NAS-Proxy hat keine Groessengrenze, lange Uploads am Stueck sind am Handy aber anfaellig.
- Ziel / Scope:
  - „Erledigt“ heisst in der Oberflaeche **„Geliefert“** (intern bleibt der Schluessel, Daten unveraendert) mit
    Lieferdatum. Knopf „📦 Als geliefert markieren“ im Auftrag.
  - **Lieferungen** je Auftrag: Dateien (Videos, Bilder, PDFs) **oder Links** (z. B. Instagram-Post, Drive, WeTransfer)
    mit Titel und Datum. Upload in Stuecken (je 8 MB, auch grosse Videos vom iPhone), Ablage auf der NAS unter
    `lieferungen/<Auftrag>/` (nicht im Git, nicht im Kassenbuch, nicht nach Drive). Ansicht mit Vorschau im Auftrag
    und in der Firmenakte („was haben wir wann wohin geliefert“). LUNA kann Lieferungen auch selbst ablegen (z. B. aus
    weitergeleiteten Mails oder fertigen Reels).
  - Geliefert = keine Zeit mehr buchbar (Start, Nachtrag und Telegram verweigern mit Hinweis). „Wieder oeffnen“ fuer
    Nachlieferungen (mit Verlauf) gibt die Zeiterfassung wieder frei.
- Gate: Tests -- Statuswechsel + Verlauf, Zeitsperre (Start/Eintrag/Telegram), Upload in Stuecken (Reihenfolge,
  Abbruch, Groesse), Links, Dateien nicht in `belege/`; Browsertest Auftrag + Firmenakte; Suite + Doku-Check gruen.
- CEO-Entscheidungen 2026-10-01: Lieferungs-Dateien **nur auf der NAS, kein zusaetzliches Backup** (die Liste der
  Lieferungen steht in der gesicherten Hash-Kette); eine Lieferung kann **Dateien und Links zugleich** haben;
  „Erledigt“ heisst **„Geliefert“**; **Wieder oeffnen** erlaubt (mit Verlauf, Zeit danach wieder buchbar).
- Aufwand: mittel.

### Etappe 31: Auftrag ohne Angebot (manuell anlegen)

- Status: geplant (CEO 2026-10-02: „Nicht jeder Auftrag braucht ein Angebot. Ich muss Auftraege auch manuell anlegen
  koennen.“), umgesetzt (CEO-Go 2026-10-02) -- Deploy offen. `AuftragBuch.anlegen` (gleiche Pruefregeln wie das
  Angebot), `POST /api/crm/auftraege`, Angebots-Editor im Auftragsmodus, Knopf „+ Neuer Auftrag (ohne Angebot)“,
  Bestaetigung (PDF beide Vorlagen, Mail) ohne Angebotsbezug. Tests `test_auftrag_manuell.py` mit Gegenprobe.
- Analyse: Auftraege entstehen heute nur aus einem angenommenen Angebot (`AuftragBuch.aus_angebot`, uebernimmt Firma,
  Ansprechpartner, Titel, Positionen, Zuschlaege/Rabatt, Zahlungsbedingungen inkl. Vorkasse, Ware/Barter). Ein Weg ohne
  Angebot fehlt in Code und Oberflaeche.
- Ziel / Scope:
  - Knopf „+ Neuer Auftrag“ in der Auftragsliste (und auf der Bereichsseite Geschaeft). Formular wie der
    Angebots-Editor: Firma (Suche/Anlegen), Ansprechpartner, Titel, Positionen aus dem Katalog oder frei (mit
    Provision/TKP wie bisher), Zuschlaege/Rabatt, Zahlungsbedingungen inkl. Vorkasse, Leistungszeitraum, Notiz.
  - Speichern legt direkt einen Auftrag `AB-JJJJ-NNNN` an (Nummernkreis wie bisher, Feld „Angebot“ leer). Danach gilt
    alles wie heute: Auftragsbestaetigung (PDF ohne Angebotsbezug), Vorkasse-/Schlussrechnung, Zeiterfassung, Geliefert.
- Gate: Tests -- Anlegen ohne Angebot (Pflichtfelder, Summen, Vorkasse), PDF ohne „Angebot“-Zeile, Rechnung aus dem
  manuellen Auftrag, Zeit buchbar; Browsertest Formular -> Auftrag; Suite + Doku-Check gruen.
- Aufwand: mittel.

## Reihenfolge

1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11 -> 12 -> 13 (ohne Auto-Weiterleitung) -> 14 -> 13 (Auto-Weiterleitung) -> 15/16 (unabhaengig, nach CEO-Go). Etappe 6 (Belege) kann nach Etappe 2 vorgezogen werden, falls Einkaeufe zuerst
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
