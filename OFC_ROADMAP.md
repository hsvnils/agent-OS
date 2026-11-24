# Roadmap: OFC -- Tickets und Zahlungen des Fanclubs HSVInside

- Status: in Umsetzung
- Stand: 2026-11-24
- Arbeitsbranch: `ai/ofc-zuordnung`
- Basiscommit: `734b284`
- Naechster Schritt: O5-Nachbesserung Fassung 3 (Branch `ai/ofc-zuordnung`) pushen, mergen, deployen; danach auf der NAS pruefen (erwartet nach dem naechsten Lauf: ca. 24 Eingaenge automatisch, 2 kein Ticket, 16 offen). Offen: Gesamtabnahme durch den CEO -- To-do A-212c2ea6, faellig 27.11.2026; danach Status „abgeschlossen“.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Anlass (CEO 2026-11-24)

Der CEO kauft ueber den Offiziellen Fanclub (OFC) HSVInside Karten fuer Spiele und gibt sie an Mitglieder weiter.
Probleme heute: Zahlungen der Mitglieder den Tickets/Spielen zuordnen, die eigenen PayPal-Abbuchungen dem Spiel
zuordnen, viel Handarbeit. Wunsch:

- eigener Reiter **„OFC“** in LUNA-OS;
- Postfach **moin@hsvinside.de** (All-Inkl) auslesen: eingehende PayPal-Zahlungen der Mitglieder, eigene Zahlungen
  (Summe, Referenzen), Mails von Eventim und HSV -- kommen fast gleichzeitig mit derselben Summe;
- Ordner auf der NAS `HSVInside_Shared/Fanclub HSVInside/Tickets 26-27` (Unterordner je Spiel; fertige Spiele in
  `Abgeschlossen` = alle Tickets bezahlt **und** Spieltag vorbei);
- HSV-Rechnungsnummern usw. mitfuehren;
- **nicht** in die normale Buchhaltung;
- je Spiel sichtbar, wie viele Karten es gibt (aus den Mail-Anhaengen); Namen je Ticket eintragen und jederzeit
  aendern; LUNA benennt die Ticket-Datei auf der NAS danach um.

## Analyse (read-only, mit Belegen, 2026-11-24)

- **Ordner auf der NAS:** `/volume1/HSVInside_Shared/Fanclub HSVInside/Tickets 26-27` mit 4 offenen Spielordnern
  (`HSV vs S04`, `HSVvsFCB`, `HSVvsSGE - DFB-Pokal`, `SVWvsHSV`) und 8 Spielen unter `Abgeschlossen`; 95 PDFs (ohne
  Synology-Metadaten `@eaDir`). Je Spiel: `Rechnung.pdf` (HSV), meist `ATGB_Ticketing_260630.pdf` (AGB) und die Tickets.
- **Dateinamen der Tickets:** ueberwiegend `<Rechnungsnr>-<Pos>-<Name>.pdf` (z. B. Muster `<N>-<N>-<Name>.pdf`);
  Abweichungen: ohne Namen (`<N>-<N>.pdf`, z. B. `Abgeschlossen/HSVvsVFB` alle 8), mit Zusatz (`…-<N>A-<Name>`,
  `…-<N>B-<Name>` beim DFB-Pokal), Name mit Ziffer. Namen der Mitglieder stehen also heute schon im Dateinamen.
- **HSV-Rechnung (Beispiel `HSVvsFCB/Rechnung.pdf`, Text per `pypdf` lesbar):** Rechnungsnr (12 Ziffern), Auftrags-Nr,
  Kunden-Nr, Datum, Spiel mit Datum/Uhrzeit/Ort („26-27 Hamburger SV - FC Bayern Muenchen / 28.11.2026 / 15:30“), je
  Ticket Position, Ticketnummer `<Rechnungsnr>-<Pos>`, Block, Preisgruppe, Reihe, Sitz, Preis; Gesamtsumme, Anzahl,
  **Zahlart: PayPal**.
- **Ticket-PDF:** enthaelt Kundennummer, Rechnungsnummer und **Ticketnummer `<Rechnungsnr>-<Pos>`** -> jede Datei laesst
  sich eindeutig einer Rechnungsposition zuordnen, auch ohne Dateinamen.
- **Container:** `luna-os` sieht heute nur `/volume1/docker/ki-unternehmen` und (nur lesend) einen Clip-Ordner
  (`deploy/docker-compose.yml` Zeile 33-38) -- die Freigabe `HSVInside_Shared` ist **nicht** eingehaengt.
- **Postfach moin@hsvinside.de:** keine Zugangsdaten in der NAS-`.env` (Namen geprueft: kein `HSVINSIDE_*`). Die Adresse
  steht in LUNAs Liste der CEO-eigenen Adressen (`orchestrator/core/eingangsbelege.py` Zeile 1698) -- Mails von dort
  zaehlen nie als Kunde. **Mail-Formate (PayPal, Eventim, HSV) sind noch unbekannt** -> O0 analysiert sie lesend.
- **Register:** keine Vorentscheidung zu Fanclub/OFC/hsvinside (`docs/entscheidungs-register.md` geprueft).
- **Wiederverwendbar:** IMAP nur lesend + Filter wie K5 (`NilsMail`, Server-Suche, `BODY.PEEK`), PDF-Text (`pypdf`),
  LUNA-OS-Bereiche (`BEREICHE` in `static/app-v2.js` Zeile 135), Rollen/Module fuer Sichtbarkeit nur CEO.

## Grundsaetze

- **Getrennt von der Buchhaltung:** eigener Speicher `fanclub/` auf der NAS (nicht im Git), eigene Ereignisse; nichts in
  `buchhaltung/log.jsonl`, EUeR, Kostenstatistik oder Firmenakte. Kein Bezug zu Hanserautisch-Kunden.
- **Keine KI fuer Mitgliederdaten:** Auslesen und Zuordnen regelbasiert (feste Mail-/PDF-Formate, Betrag, Zeit,
  Verwendungszweck); was nicht eindeutig ist, landet in „Zuordnen“ mit Vorschlaegen -- der CEO klickt.
- **Nur CEO sieht OFC** (Team-Nutzer nicht); Namen und Zahlungen der Mitglieder sind personenbezogene Daten.
- **Keine Mails/Nachrichten an Mitglieder** durch LUNA (Oeffentlichkeit = CEO-Tor); hoechstens Text zum Kopieren.
- **Dateien:** nur umbenennen/ablegen/verschieben in der Fanclub-Freigabe, nie loeschen; jede Aenderung protokolliert und
  rueckgaengig machbar.

## Entscheidungen des CEO (2026-11-24)

- **E1 Zugang moin@hsvinside.de** -- **BESCHLOSSEN wie empfohlen.** neuer Zugang = CISO-Freigabe (AGENTS.md 5.7). **Empfehlung:** wie K5: nur lesend,
  Server-Suche nur nach Absendern von PayPal, Eventim und HSV (Liste in O0 festgelegt), andere Mails nie laden; nichts
  verschieben/loeschen; Zugangsdaten `HSVINSIDE_MAIL_USER`/`HSVINSIDE_MAIL_PASSWORT` traegt der CEO selbst ein.
- **E2 Freigabe einhaengen** -- **BESCHLOSSEN wie empfohlen.** `HSVInside_Shared/Fanclub HSVInside` in den Container `luna-os` (nicht `luna-telegram`).
  **Empfehlung:** nur dieser Unterordner, **schreibend** (Umbenennen/Ablegen/Verschieben), Aenderung in
  `deploy/docker-compose.yml`; der CEO fuehrt `docker compose up -d` aus (Container wird neu erstellt).
- **E3 Saison-Ordner** -- **BESCHLOSSEN (CEO):** Saison-Ordner in LUNA einstellbar (heute `Tickets 26-27`); neue Spielordner
  heissen bei Heimspielen `HSV vs <Gegner>`, bei Auswaertsspielen `<Gegner> vs HSV`. Bestehende Ordner bleiben, wie sie sind.
- **E4 Bestand** -- **BESCHLOSSEN wie empfohlen.** **Empfehlung:** alle Spiele der Saison 26-27 inkl. `Abgeschlossen` uebernehmen (Rechnung + Tickets +
  Namen aus den Dateinamen); PayPal-Zahlungen rueckwirkend, soweit sie im Postfach liegen, sonst per PayPal-CSV-Export
  (Upload in LUNA-OS).
- **E5 Mitgliederliste** -- **BESCHLOSSEN (CEO): direkt die Mitgliederliste nehmen.** Sie liegt in Google Forms (Antworten =
  eine Tabelle); dieselbe Liste enthaelt Anfragen und Mitglieder -- Mitglied ist, wer eine Mitgliedsnummer hat. **Vorschlag
  Anbindung (offen, E5b):** der CEO teilt die Antwort-Tabelle **nur lesend** mit LUNAs Google-Konto; LUNA liest sie ueber den
  vorhandenen Sheets-Zugang (`google_workspace`, kein neuer Zugangstyp), nie schreibend. Alternative: Excel-Export per Upload
  (veraltet aber sofort). Umsetzung in Etappe OM.
- **E6 Zahlung -> Ticket** -- **BESCHLOSSEN wie empfohlen.** **Empfehlung:** eindeutig = automatisch (Betrag passt zu offenen Tickets eines Spiels **und**
  Name oder Verwendungszweck passt); sonst Vorschlag mit einem Klick. Eine Zahlung darf mehrere Tickets/Spiele abdecken
  (aufteilen), Ueber-/Unterzahlung wird als Saldo je Person gefuehrt.
- **E7 Abschliessen** -- **BESCHLOSSEN wie empfohlen.** **Empfehlung:** LUNA meldet „abschliessbar“ (alle bezahlt + Spieltag vorbei), der CEO klickt
  „Abschliessen“ -> Ordner wandert nach `Abgeschlossen`. Kein automatisches Verschieben.
- **E8 Meldungen** -- **BESCHLOSSEN (CEO): keine Telegram-Nachrichten.** Hinweise (neue Bestellung, „bitte zuordnen“,
  Spiel bald ohne Namen/Zahlung) erscheinen nur im Reiter OFC (Zaehler/Markierung).

## Etappen

### Etappe O0: Zugang und Analyse (nur lesend)

- Status: umgesetzt (2026-11-24; `HsvInsideMail` nur lesend/Absenderfilter, `core/ofc.py` Rechnung/Ticket/Ordner-/Postfach-Analyse, Endpunkte `/api/ofc/...` nur CEO, Mount `:ro`, CISO in `governance/zugriffs-policy.md`; `test_ofc.py`. Probelauf Ordner (Kopie, 2026-11-24): 12 Spiele, 11 Rechnungen erkannt (inkl. Auswaerts/DFB-Pokal/Freundschaft, Heim/Auswaerts), 70 Karten, 77 Ticket-Dateien; SVWvsHSV ohne Rechnung, HSVvsFCB mit 2. Bestellung ohne Rechnung, HSVvsVFB ohne Namen. Deployt 2026-11-24. Verbindung moin@ ok. **Postfach-Analyse live (120 Tage, 108 Mails):** PayPal „erhalten“ 40 (34 mit Mitteilung, alle mit Transaktionscode); PayPal „gesendet“ 21 -- die Zahlungen an **CTS EVENTIM** (HSV-Ticketshop) mit Bestellnummer, Positionszeile „Tickets HSV …: <Anzahl>“, Gesamtbetrag, Transaktionscode; PayPal sonstiges 29 (u. a. **„Spaeter bezahlen“ in 30 Tagen** bei CTS EVENTIM, Abbuchungen, Ueberweisungen aufs Bankkonto); HSV 18 (`hsv.de`, `service.hsv.de` mit „Kopie der Rechnung <Nr> vom <Datum>“, Ticket-PDFs `<Rechnungsnr>-<Pos>.pdf` und `Rechnung.pdf`; `news.hsv.de` = Newsletter). **Eigene Eventim-Mails gibt es nicht** -- „Eventim“ = PayPal-Beleg an CTS EVENTIM. Ordner-Analyse auf der NAS nach BF-101 (DSM-Berechtigung) ok: 12 Spiele, 11 erkannt, 70 Karten, 77 Dateien -- **verifiziert**.)
- Ziel / Scope / Nicht-Scope: Zugang moin@ nach E1 (Klasse wie `NilsMail`, Absenderfilter), Mount nach E2 (erst nur
  lesend). Dry-Run-Bericht in LUNA-OS bzw. als Skript: Mails je Absender der letzten 90 Tage, erkannte Felder je Typ
  (PayPal erhalten / PayPal gesendet / Eventim / HSV-Rechnung) **ohne** Namen/Betraege ins Log; Ordner-Scan wie oben.
  Ergebnis: feste Erkennungsregeln je Mailtyp + Beispiel-Fixtures (anonymisiert) fuer die Tests. Nicht-Scope: speichern.
- Gate: CISO-Pruefung in `governance/zugriffs-policy.md`; Tests: nur gefilterte Mails werden geladen (Gegenprobe), Mount
  nur der Fanclub-Ordner; Verbindungspruefung ohne Lesen.
- Verifikation: Dry-Run auf der NAS listet je Mailtyp Anzahl + erkannte Felder; Stichprobe mit dem CEO (3 Mails je Typ).
- Dry-Run: ist die Etappe selbst.
- Risiko / Rueckweg: Zugang eng; Entfernen der `.env`-Zeilen bzw. der Mount-Zeile.
- Abhaengig von / Aufwand / Risiko: E1, E2 / mittel / mittel (neuer Zugang).

### Etappe O1: Spiele, Tickets und Bestand (Reiter OFC, lesen)

- Status: umgesetzt (2026-11-24; Speicher `fanclub/log.jsonl`, `core/ofc_store.py` Import mit Vorschau (wiederholbar, Namen aus Dateinamen nur beim ersten Erfassen, Spiel-ID = Ordnername), Reiter „OFC“ nur CEO (Spiele, Karten, Namen, Status, Hinweise; Spiel-Detail mit Tickets und Rechnung, PDFs oeffnen); Probelauf auf Kopie der echten Saison: 12 Spiele, 77 Tickets, 68 mit Namen, zweiter Lauf ohne Aenderung; Sichtpruefung headless Rechner/iPad/iPhone ok; `test_ofc_store.py`. Gemergt und deployt 2026-11-24; erster Import auf der NAS durch den CEO: 12 Spiele, 77 Karten, 4 offen, erneute Vorschau ohne Aenderung; offen: Abgleich und Sichtabnahme durch den CEO)
- Ziel / Scope / Nicht-Scope: Speicher `fanclub/log.jsonl` (Spiele, Rechnungen, Tickets, Personen, Zahlungen als
  Ereignisse). Import des Bestands (E4): `Rechnung.pdf` lesen (Rechnungsnr, Auftrags-/Kunden-Nr, Spiel, Datum, Tickets
  mit Block/Reihe/Sitz/Preis), Ticket-Dateien ueber die Ticketnummer im PDF zuordnen, Namen aus den Dateinamen
  vorbelegen. Neuer Bereich **„OFC“** in LUNA-OS (nur CEO): Spiele der Saison mit Datum, Karten gesamt/mit Namen/bezahlt,
  Status (offen, abschliessbar, abgeschlossen); Spiel-Detail mit Rechnung und Ticketliste. Nicht-Scope: Aendern.
- Gate: Tests mit Beispiel-Rechnung/-Tickets (Fixtures ohne echte Namen); Import-Dry-Run zeigt alle 12 Spiele und die
  Ticketzahlen; Sichtpruefung Rechner/iPad/iPhone.
- Verifikation: Zahlen im Reiter = Ordner auf der NAS (z. B. HSVvsFCB: 4 Karten, Rechnung 140,00 EUR).
- Dry-Run: Import zeigt erst, was angelegt wuerde.
- Risiko / Rueckweg: nur lesend auf der Freigabe; Speicher loeschbar ohne Folgen.
- Abhaengig von / Aufwand / Risiko: O0 / mittel / gering.

### Etappe OM: Mitgliederliste (CEO 2026-11-24)

- Status: umgesetzt (2026-11-24; `core/ofc_mitglieder.py`, `GET /api/ofc/mitglieder`, Ansicht „👥 Mitglieder“ im Reiter OFC mit Suche, Reitern Mitglieder/Anfragen und Detail mit allen Spalten. CEO-Entscheidung: nur Blatt „Formularantworten 1“, alle Spalten. Probelauf gegen die echte Tabelle: 119 Mitglieder, 11 Anfragen, 18 von 18 Spalten erkannt, Hinweise 2 Nummern und 3 Namen mehrfach. Nur `files.list`/`values.get` (Gegenprobe-Test), nichts gespeichert, keine KI; `test_ofc_mitglieder.py`; Sichtpruefung headless Rechner/iPad/iPhone ok; gemergt und deployt 2026-11-24, auf der NAS geprueft (119/11, 18 Spalten); offen: Stichprobe CEO)
- Ziel / Scope / Nicht-Scope: Mitgliederliste aus der Google-Forms-Antworttabelle lesen (E5/E5b): Name, Mitgliedsnummer,
  Kontaktfelder nach Bedarf; ohne Mitgliedsnummer = Anfrage. Nutzung: Namensvorschlaege fuer Tickets (O2), Zuordnung der
  PayPal-Zahlungen ueber Name/PayPal-Mail (O5), Statistik je Mitglied (O6). Anzeige im Reiter OFC (Mitglieder/Anfragen).
  Nicht-Scope: in die Tabelle schreiben, Mitgliedsnummern vergeben, Beitraege (eigene Roadmap).
- Gate: Tests (Spalten erkennen, Anfrage vs. Mitglied, Namensdubletten); Lesezugriff nur lesend (Gegenprobe: kein
  Schreibaufruf); Datenfluss + Datenschutz-Hinweis dokumentiert.
- Verifikation: Zahl der Mitglieder/Anfragen im Reiter = Tabelle (Stichprobe CEO).
- Dry-Run: Probelauf zeigt erkannte Spalten und Anzahl, ohne zu speichern.
- Risiko / Rueckweg: Freigabe der Tabelle fuer LUNA zuruecknehmen.
- Abhaengig von / Aufwand / Risiko: E5b, O1 / klein / gering.

### Etappe O2: Namen zuweisen und Dateien umbenennen

- Status: umgesetzt (2026-11-24; `core/ofc_store.py` `namen_plan`/`namen_setzen`/`rueckgaengig`/`namen_vorschlaege`, Ereignis `ofc_name` (Protokoll alt -> neu), Endpunkte Vorschau/Speichern/Rueckgaengig/Namen; im Spiel-Detail ✏️ je Ticket mit Vorschlaegen aus der Mitgliederliste, Vorschau „aus X wird Y“, „Rueckgaengig“. Dateiname `<Rechnungsnr>-<Pos>[A|B]-<Name>.pdf` (Zusatz A/B bleibt, Name dateisicher, Umlaute bleiben), Kollision auch bei Gross/Klein abgelehnt, nie loeschen/ueberschreiben, Datei fehlt -> nur Name in LUNA, Datei verschoben -> Hinweis „Ordner einlesen“; Mount schreibend in `deploy/docker-compose.yml`; `test_ofc_namen.py`; Sichtpruefung headless Rechner/iPhone ok; Abnahme CEO am Ende der Roadmap)
- Ziel / Scope / Nicht-Scope: Je Ticket Name eintragen/aendern (Vorschlaege aus der Personenliste, E5). Nach dem Speichern
  benennt LUNA die Datei nach dem Muster `<Rechnungsnr>-<Pos>-<Name>.pdf` um (Name dateisicher, Umlaute bleiben, keine
  Schraegstriche); Vorschau vor dem Umbenennen, Protokoll alt -> neu, „Rueckgaengig“. Nicht-Scope: Loeschen.
- Gate: Tests (Umbenennen, Namenswechsel, Kollision, Sonderzeichen, Datei fehlt/ist offen); Gegenprobe; Mount schreibend
  (E2) erst ab hier.
- Verifikation: Name im Reiter aendern -> auf der NAS (Finder/Drive) neuer Dateiname, alte Datei nicht mehr vorhanden.
- Dry-Run: Vorschau „aus X wird Y“ vor dem Klick.
- Risiko / Rueckweg: falscher Name -> neu benennen oder Rueckgaengig; Dateien werden nie geloescht.
- Abhaengig von / Aufwand / Risiko: O1 / klein / gering.

### Etappe O3: Neue Bestellungen automatisch (HSV/Eventim)

- Status: umgesetzt (2026-11-24; `core/ofc_post.py`: HSV-Mails mit PDF -> Rechnung/Tickets je Rechnungsnummer; bekanntes Spiel (Rechnungsnr oder Spieltag + Paarung) wird ergaenzt, neues Spiel bekommt Ordner nach E3 (`HSV vs <Gegner>` / `<Gegner> vs HSV`, bei Namensgleichheit mit Datum), Tickets ohne Rechnung bleiben „wartet“, per O2 umbenannte Tickets werden nicht erneut abgelegt; Dateien nur neu, nie ueberschreiben/loeschen; danach Import O1. Automatisch alle 15 Minuten in `luna-os` (erster Lauf 10 Minuten nach Start, `OFC_AUTO_POST=0` schaltet ab), Knopf „📬 Postfach“ mit Vorschau, Status unter der Spieleliste, „Spiel verwerfen“ (Ereignis, Ordner bleibt). Postfach-Abruf auf `hsv.de` eingeschraenkt (`posteingang(nur=...)`). Befund O0: Eventim schickt keine eigenen Mails -- Eventim-Kaeufe kommen nur als PayPal-Beleg und laufen ueber O4. `test_ofc_post.py`; Sichtpruefung headless Rechner/iPhone ok)
- Ziel / Scope / Nicht-Scope: Im Bot-Poll HSV-Rechnungsmail und Eventim-Mail erkennen (Regeln aus O0), zu einer Bestellung
  zusammenfuehren (gleiche Summe, kurzer Zeitabstand, Rechnungs-/Auftragsnummer), Spiel anlegen, Spielordner anlegen,
  Rechnung und Tickets dort ablegen (Namensmuster), Hinweis im Reiter OFC (E8: keine Telegram-Nachricht). Nicht-Scope: Zahlungen.
- Gate: Tests mit Fixtures aus O0 (Paar erkannt, Dublette nicht doppelt, nur Eventim ohne HSV bleibt „wartet“).
- Verifikation: naechste echte Bestellung erscheint im Reiter und als Ordner mit allen Tickets.
- Dry-Run: Probelauf zeigt, welche Bestellungen angelegt wuerden.
- Risiko / Rueckweg: Fehlerkennung -> Spiel im Reiter verwerfen (Ereignis, Ordner bleibt).
- Abhaengig von / Aufwand / Risiko: O0, O1 / mittel / mittel.

### Etappe O4: Eigene PayPal-Zahlungen dem Spiel zuordnen

- Status: umgesetzt (2026-11-24; `core/ofc_zahlung.py`: PayPal-Belege an Eventim/HSV erkennen -- gesendet, „Spaeter bezahlen“ (Faelligkeit +30 Tage, Abbuchung erfolgreich/fehlgeschlagen), Erstattung; Mitgliederzahlungen (O5) und andere Haendler ignoriert; Zuordnung per Punkte: Rechnungs-/Auftrags-/Bestellnummer im Beleg (sicher), Betrag = Rechnung, Datum nahe Rechnung, Gegner im Beleg; eindeutig -> automatisch, sonst Vorschlaege + „Zuordnen“/„Kein Ticketkauf“/„loesen“; Dubletten ueber Transaktionscode; Ereignis `ofc_zahlung` ohne Mailtext; Ansicht „💳 Zahlungen“, im Spiel „Eigene Zahlung“ mit Bezahlt/Rechnung, Hinweise „Eigene Zahlung nicht zugeordnet“ und „Abbuchung fehlgeschlagen“; automatisch im 15-Minuten-Takt. `test_ofc_zahlung.py`; Sichtpruefung headless Rechner/iPhone ok. Grenze: Eventim-Kaeufe ohne HSV-Rechnung haben keine gemeinsame Nummer -> meist Zuordnen per Klick. **Nachbesserung 2026-11-24 nach Probelauf mit echten Mails** (12 Zahlungen, 4 automatisch -- alle richtig): nur Haendler Eventim/HSV (Dropbox raus), „Spaeter bezahlen“ Kauf- + Erinnerungsmail = ein Kauf mit Kaufdatum, bereits bezahlte Rechnung zaehlt nicht erneut ueber den Betrag, alte automatische Eintraege werden neu bewertet (Klicks bleiben); Erkenntnis: auch HSV-Heimspiele laufen ueber „CTS EVENTIM Sports GmbH“)
- Ziel / Scope / Nicht-Scope: PayPal-Mail „Zahlung gesendet“ (an Eventim/HSV) erkennen; Zuordnung zur Bestellung ueber
  Betrag + Zeitfenster + Empfaenger; Referenzen (PayPal-Transaktionscode, Rechnungsnr, Auftrags-Nr, Kunden-Nr) am Spiel.
  Uneindeutig -> „Zuordnen“. Nicht-Scope: Mitgliederzahlungen.
- Gate: Tests (gleiche Summe zweimal am Tag, Teilerstattung/Rueckzahlung, Gebuehren).
- Verifikation: bestehende Spiele zeigen ihre PayPal-Abbuchung mit Transaktionscode (Stichprobe mit PayPal-Konto).
- Dry-Run: Probelauf ueber die letzten 90 Tage.
- Risiko / Rueckweg: falsche Zuordnung per Klick loesen.
- Abhaengig von / Aufwand / Risiko: O0, O1 / klein / gering.

### Etappe O5: Zahlungseingaenge der Mitglieder

- Status: umgesetzt (2026-11-24; `core/ofc_eingang.py`: PayPal „Zahlung erhalten“ -> Name, Betrag, Mitteilung, Transaktionscode, Datum; Rueckzahlung an ein Mitglied negativ; E6: automatisch, wenn der Betrag genau zu offenen Tickets auf den Namen des Zahlers (oder Alias) passt -- bei mehreren Spielen entscheidet der Gegner in der Mitteilung, Sammelzahlung fuer mehrere Spiele moeglich; sonst „Zuordnen“ mit Vorschlaegen oder „Tickets waehlen“ (auch Teil-/Ueberzahlung), „Kein Ticket“ (z. B. Beitrag), loesen; Alias wird beim Klick gelernt; Ticketstatus bezahlt/teilweise im Spiel, „x/y bezahlt“ in der Liste, Saldo je Zahler; Ansicht „💶 Eingaenge“; automatisch im 15-Minuten-Takt; `test_ofc_eingang.py`; Sichtpruefung headless Rechner/iPhone ok. PayPal-CSV-Import zurueckgestellt. **Fassung 3 (2026-11-24 abends, CEO: ohne Handabgleich):** Ticketnamen robust (zusammengeschrieben, Blockkuerzel, Ziffern, Akzente); Spiel aus der Mitteilung inkl. Spitznamen, Pokal, Heim/Auswaerts -- dort auch freie Karten und aufgerundete Betraege bis 5 €; sonst „Tickets waehlen“ mit vorgewaehltem Spiel; Teilzahlungen binnen 3 Tagen zusammen; Bankueberweisung/Trikot -> „kein Ticket“; offene Eingaenge bei jedem Lauf neu bewertet, Klicks nie. Probe auf echten Daten: 24 statt 10 automatisch)
- Ziel / Scope / Nicht-Scope: PayPal-Mail „Geld erhalten“ erkennen (Name, Betrag, Mitteilung, Transaktionscode); Vorschlag
  Spiel + Ticket(s) ueber Name/Personenliste, Verwendungszweck (Gegner, Datum, Anzahl) und Betrag (E6); eindeutige Faelle
  automatisch, sonst Liste „Zuordnen“; Aufteilen auf mehrere Tickets/Spiele; Saldo je Person; Ticketstatus bezahlt/offen.
  Optional Import PayPal-CSV fuer alte Zahlungen (E4). Nicht-Scope: Mahnungen an Mitglieder.
- Gate: Tests (Teilzahlung, Sammelzahlung fuer 2 Spiele, falscher Betrag, unbekannter Name, Rueckzahlung, Dublette aus Mail
  und CSV); Gegenproben.
- Verifikation: echte Zahlung eines Mitglieds -> Ticket „bezahlt“ im Reiter.
- Dry-Run: Probelauf zeigt Vorschlaege ohne zu speichern.
- Risiko / Rueckweg: Zuordnung loesbar; nichts verlaesst das Haus.
- Abhaengig von / Aufwand / Risiko: O1, (O4) / mittel / mittel (Datenqualitaet der Verwendungszwecke).

### Etappe O6: Abschluss, offene Posten, Saisonuebersicht

- Status: umgesetzt (2026-11-24; `core/ofc_saison.py`: Status „abschliessbar“ (Spieltag vorbei + alle Karten bezahlt), im Spiel „Abschliessen“/„Wieder oeffnen“ mit Vorschau (Ordner nach/aus `Abgeschlossen/`, Kollision auch Gross/Klein abgelehnt, nie loeschen), „trotzdem“ nur nach zweiter Rueckfrage; Hinweis 3 Tage vor dem Spiel (ohne Namen/unbezahlt) nur im Reiter; Ansicht „📊 Saison“: eingekauft/eingenommen/offen/Differenz, offene Posten je Kartenname mit 📋-Text zum Kopieren (inkl. abgeschlossene auf Wunsch), Statistik je Mitglied (Karten, Spiele, je Wettbewerb), Export CSV und PDF A4 hochkant; `test_ofc_saison.py`; Sichtpruefung headless Rechner/iPhone + PDF ok. Dazu Nachbesserung O4 („Spaeter bezahlen“: Erinnerung = „Sie bezahlen in N Tagen“) und O5 (abgeschlossene Spiele zaehlen mit, Mitteilung mit anderem Spiel verhindert Automatik) nach Probelauf mit echten Mails)
- Ziel / Scope / Nicht-Scope: „abschliessbar“-Hinweis und Knopf „Abschliessen“ (E7: Ordner nach `Abgeschlossen`);
  offene Posten je Person (wer schuldet was, fuer welches Spiel) mit Text zum Kopieren (z. B. fuer WhatsApp); Saison-
  uebersicht: Summe eingekauft / eingenommen / offen / Differenz; Export als CSV und PDF (A4 hochkant). Hinweis im Reiter 3 Tage
  vor dem Spiel (E8, keine Telegram-Nachricht). **Statistik je Mitglied** (CEO 2026-11-24): wer hat wie oft Karten
  bekommen (je Saison, je Wettbewerb), als Grundlage fuer eine faire Vergabe. Nicht-Scope: Versand an Mitglieder.
- Gate: Tests (Abschluss nur wenn bezahlt + Datum vorbei; Verschieben mit Kollision); Sichtpruefung.
- Verifikation: ein echtes, vollstaendig bezahltes vergangenes Spiel per Klick abschliessen -> Ordner liegt in
  `Abgeschlossen`, Reiter zeigt „abgeschlossen“.
- Dry-Run: Vorschau „verschiebe X nach Abgeschlossen/X“.
- Risiko / Rueckweg: Ordner zurueckschieben (Knopf „wieder oeffnen“).
- Abhaengig von / Aufwand / Risiko: O1-O5 / klein / gering.

## Folgethemen (CEO 2026-11-24, eigene Roadmap)

- **Mitgliedsbeitraege und Fanclub-Kasse** -- Beitraege und Kasse laufen ueber PayPal; eigene Roadmap nach OFC (nutzt
  Mitgliederliste OM und PayPal-Erkennung O5) -> geplant in `OFC_KASSE_ROADMAP.md` (2026-11-24).

## Ideen (nicht im Scope, auf Wunsch)

- Ticket-PDF direkt aus dem Reiter teilen (Datei-Link wie `/teilen/*` mit Ablauf) statt per Hand verschicken -- Oeffentlichkeit,
  braucht eigenes Go + CISO.
- Warteliste je Spiel (wer will Karten, wenn welche frei werden).
- Sitzplan-Ansicht (Block/Reihe/Sitz) fuer Gruppen, die zusammen sitzen wollen.

## Dokumentation bei der Umsetzung

`projekt_changelog.md`, Etappen-Status hier, `ROADMAP.md`, `docs/entscheidungs-register.md` (E1-E8),
`docs/datenfluesse.md` (Postfach moin@, Freigabe-Mount, Speicher `fanclub/`), `governance/zugriffs-policy.md` (CISO),
`docs/datenschutz-ki-nutzung.md` (Hinweis: keine KI fuer Mitgliederdaten), `AGENTS.md` Abschnitt 7 (`fanclub/`),
`docs/bekannte-fehler.md` (Test-Baseline), Backup-Umfang (`fanclub/` in die Sicherung).

## Definition of Done

Neue Bestellungen erscheinen ohne Handarbeit als Spiel mit Rechnung und Tickets; Namen sind je Ticket gepflegt und die
Dateien heissen danach; eigene PayPal-Zahlungen und Zahlungen der Mitglieder sind den Spielen/Tickets zugeordnet (Rest in
„Zuordnen“); fertige Spiele lassen sich per Klick abschliessen. Der CEO nimmt jede Etappe ab und setzt die Roadmap auf
abgeschlossen.
