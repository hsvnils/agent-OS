# Verfahrensdokumentation Buchhaltung (GoBD)

- Unternehmen: Krueger Onlinehandel und Media, c/o Hanserautisch, Arthur-Soltau-Weg 7c, 22889 Tangstedt
- Verantwortlich: Nils Krueger (Inhaber, im Projekt „CEO“)
- Steuerliche Einordnung: Kleinunternehmer nach § 19 UStG, Gewinnermittlung nach § 4 Abs. 3 EStG (EUeR)
- System: LUNA-OS (Eigenbau, Web-Oberflaeche auf der eigenen Synology-NAS), Bereich Kunden/Angebote/Rechnungen/Belege/Finanzen
- Stand: 2026-09-28, gueltig ab Beginn der Aufzeichnungen im September 2026
- Status: **Entwurf -- Abnahme durch den Inhaber offen** (ggf. Pruefung durch einen Steuerberater)

Diese Dokumentation beschreibt, wie Geschaeftsvorfaelle in LUNA-OS erfasst, verarbeitet, aufbewahrt und
ausgewertet werden (GoBD, BMF-Schreiben vom 28.11.2019 in der Fassung vom 14.07.2025, Rz. 151 ff.). Technische
Details stehen im Code; hier steht, *was* passiert und *wer* es tut.

## 1. Allgemeine Beschreibung

- **Umfang:** Kunden- und Lieferantenstamm, Angebote, Auftragsbestaetigungen, Ausgangsrechnungen, Eingangsbelege
  (Rechnungen, Gutschriften), Eigenbelege, Zahlungen, EUeR, Anlageverzeichnis, Jahresexport.
- **Nicht im System:** Bankkonto (kein Bankzugang; Zahlungen werden von Hand erfasst), Lohn, Kasse (keine Bargeldkasse).
- **Beteiligte:** Der Inhaber erfasst, prueft, bucht, schreibt fest und versendet. Die KI-Assistentin LUNA
  (inkl. „CFO“-Agent) liest Belege aus, macht Vorschlaege, erinnert an Offenes und legt Kalendertermine an --
  **sie bucht, versendet oder loescht keine Buchhaltungsdaten eigenstaendig**. Jede Buchung, jedes Festschreiben und
  jede Zahlung ist eine Handlung des Inhabers (Klick in LUNA-OS bzw. Bestaetigung per Telegram-Knopf).
- **Rechte:** Zugriff auf den Bereich „Finanzen“ nur fuer den Inhaber (Rollen-/Modulrechte in LUNA-OS,
  Anmeldung ueber HTTPS mit Passwort).

## 2. Anwenderdokumentation (Ablauf der Geschaeftsvorfaelle)

### 2.1 Stammdaten
Firmen erhalten eine fortlaufende Nummer `K-00001`, Ansprechpartner `AP-00001`. Aenderungen werden mit altem und
neuem Wert protokolliert; Nummern werden nie wiederverwendet.

### 2.2 Ausgangsseite
1. **Angebot** `AN-JJJJ-NNNN` -> Versand per Mail aus LUNAs Postfach nach Klick des Inhabers; Original-Mails (.eml)
   werden als Geschaeftsbrief abgelegt.
2. **Auftragsbestaetigung** `AB-JJJJ-NNNN` aus dem angenommenen Angebot.
3. **Rechnung**: zuerst Entwurf ohne Nummer (frei aenderbar), dann **Festschreiben**: Nummer `RE-JJJJ-NNNN`
   (lueckenlos), PDF und Eintrag entstehen in einem Schritt und sind danach unveraenderbar. Pflichtangaben nach
   § 34a UStDV inkl. Hinweis auf die Steuerbefreiung nach § 19 UStG; keine Umsatzsteuer.
   **Altrechnungen** (vor LUNA mit eigener Nummer geschrieben) werden mit Originalnummer und Original-PDF
   unveraendert uebernommen -- ohne neue Nummer und ohne zweite Rechnung; bereits verschickte Mahnungen werden mit Datum
   (und PDF) als erreichte Stufe erfasst.
   **Provisionen** (z. B. Affiliate): Angebot und Auftrag nennen nur das Modell (Euro je verkauftem Artikel bzw. Prozent
   vom vermittelten Umsatz); die Rechnung entsteht nach der Abrechnung (Stueckzahl bzw. Umsatz) mit ausgewiesener
   Berechnungsgrundlage; eine Rechnung mit nicht abgerechneter Provision kann nicht festgeschrieben werden.
4. **Korrektur** nur per **Stornorechnung** (eigene Nummer, negativer Betrag, Bezug auf das Original) und ggf.
   neuer Rechnung.
5. **Zahlungseingang** wird von Hand erfasst (Datum laut Kontoauszug, Teilzahlungen moeglich).
6. **Barter (Tausch Leistung gegen Ware)**: Angebot, Auftrag und Rechnung weisen die Gegenleistung in Ware mit Wert
   aus. Der Ware-Eingang wird mit Datum, Wert (eigener Nachweis, sonst Angabe der Marke) und Nachweis-Dateien gebucht;
   er ist eine Betriebseinnahme zum ueblichen Endpreis und zaehlt zur Kleinunternehmer-Grenze. Fuer Content genutzte
   Ware ist zugleich eine Anschaffung (GWG/Anlage), privat behaltene nur Einnahme, Leihgaben werden nur dokumentiert.
7. **Mahnwesen**: Die 1. Mahnung stoesst der Inhaber an; nach Fristablauf fragt LUNA per Telegram nach der 2. bzw.
   letzten Mahnung und versendet erst nach Bestaetigung. Verzugszinsen ab Faelligkeit (Basiszinssatz + 9 bzw. 5
   Prozentpunkte, taggenau), Verzugspauschale 40 EUR (Unternehmer) bzw. 2,50 EUR je Mahnung (Verbraucher). Mahnungen
   `MA-JJJJ-NNNN` werden wie Rechnungen unveraenderbar abgelegt.
8. **Zahlungsbedingungen und Vorkasse** (Etappe 18): Je Angebot werden Zahlungsziel und optional eine Vorkasse (Prozent
   des Geldanteils oder fester Betrag, Frist in Tagen nach Auftragsbestaetigung oder festes Datum) festgelegt und
   unveraendert in Auftrag und Rechnung uebernommen. Die Vorkasse wird als eigene **Vorkasse-Rechnung** `RE-JJJJ-NNNN`
   gestellt (Leistung „folgt gemaess Auftrag“, faellig zur vereinbarten Frist). Die **Schlussrechnung** zum Auftrag
   weist die Auftragssumme aus und zieht jede nicht stornierte Vorkasse-Rechnung mit Nummer und Datum ab; ihr Betrag ist
   nur der Rest, so zaehlt der Umsatz nur einmal. Eine abgezogene Vorkasse-Rechnung kann erst storniert werden, wenn die
   Schlussrechnung storniert ist. Zu jeder festgeschriebenen Rechnung legt LUNA einen Payment-Check-Termin am
   Faelligkeitstag an und loescht ihn, sobald die Zahlung erfasst ist.

### 2.3 Eingangsseite
1. **Belegeingang**: Upload in LUNA-OS (PDF, E-Rechnung XML, Foto, gespeicherte Mails `.eml`/`.mbox`) oder
   Weiterleitung an `luna.hanserautisch@gmail.com` (nur von den eigenen Adressen; Absender kryptografisch geprueft per
   DKIM/DMARC). **Zweck/Begruendung**: Was der Inhaber beim Weiterleiten ueber die Mail schreibt („wofuer gekauft“),
   speichert LUNA als Zweck am Beleg (betriebliche Veranlassung); er ist in LUNA-OS aenderbar (Aenderungen im Verlauf)
   und steht im Jahresexport (Spalte `Zweck`).
2. Das **Original** wird sofort unveraendert abgelegt (SHA-256 im Kassenbuch) und erhaelt die Nummer `ER-JJJJ-NNNN`.
   Doppelte Dateien werden erkannt.
   Wiederkehrende Zahlungen ohne eigenen Beleg (Abos, `ABO-`) werden je Faelligkeit genau einmal erledigt: als Eigenbeleg
   (per Klick oder -- nur wenn am Abo angehakt -- automatisch), durch einen passenden Beleg oder begruendet uebersprungen.
   Jeder Beleg haengt an einer Stammdaten-Nummer des Geschaeftspartners (Kunden `K-`, Lieferanten `L-`, Partner `P-`,
   fortlaufend, nie wiederverwendet); Adresse, USt-ID und Vertragsnummern werden aus den Belegen uebernommen.
   Steht die Rechnung nur im Mailtext (z. B. Apple, PayPal), ist die **Mail selbst das Original**: LUNA archiviert die
   `.eml` unveraendert und legt eine lesbare PDF-Ansicht dazu. Eine Zahlungsquittung neben der Rechnung wird als
   Zahlungsnachweis beim selben Beleg abgelegt (kein zweiter Beleg).
   Danach legt LUNA die Mail in ihrem Postfach unter `LUNA/Rechnungen/<Jahr>`, `LUNA/Gutschriften/<Jahr>` bzw.
   `LUNA/Doppelt/<Jahr>` ab (gelesen, nie geloescht); welche Mail zu welchem Beleg gehoert, steht im Kassenbuch
   (`eingang_mail_abgelegt`). Mails ohne erkannten Beleg bleiben im Posteingang.
3. LUNA liest den Beleg lokal aus (E-Rechnung exakt, PDF-Text, Texterkennung) und schlaegt Lieferant, Datum,
   Betrag, Kategorie vor. **Der Inhaber prueft und bucht**. Belegarten: Ausgabe (Eingangsrechnung) oder
   Einnahme (Gutschrift, z. B. Plattform-Verguetung).
4. **Fremdwaehrung**: Es zaehlt der Euro-Betrag laut Kontoauszug; der Fremdbetrag steht in der Notiz.
   **Gemischte Rechnungen** (z. B. Amazon mit privaten Artikeln) werden in Positionen aufgeteilt; private Positionen
   sind als „privat – nicht absetzbar“ gekennzeichnet und zaehlen nicht als Betriebsausgabe (§ 12 EStG). Die Summe der
   Positionen muss dem Rechnungsbetrag entsprechen; Zahlungen werden anteilig verteilt.
5. **Zahlung** (Abfluss/Zufluss) wird von Hand erfasst; falsch erfasste Zahlungen werden mit Grund storniert
   (bleiben sichtbar).
6. **Eigenbelege** `EB-JJJJ-NNNN` fuer Zahlungen ohne eigenen Beleg (z. B. Kontogebuehren, Plattform-Auszahlungen
   ohne Dokument) mit Pflichttext; Korrektur nur per Storno.

### 2.4 Gewinnermittlung (EUeR)
- Zufluss-/Abflussprinzip nach Zahlungsdatum; 10-Tage-Regel nur fuer regelmaessig wiederkehrende Zahlungen vom
  22.12. bis 10.01. per ausdruecklich gesetztem Zuordnungsjahr.
- Bruttobetraege (kein Vorsteuerabzug). Bewirtung zu 70 % abziehbar.
- Geringwertige Wirtschaftsgueter bis 800 EUR sofort; darueber Anlagegut mit linearer AfA, monatsgenau ab
  Anschaffung; Computer/Software mit Nutzungsdauer 1 Jahr (BMF 22.02.2022) im Anschaffungsjahr voll.
- Kein Sammelposten, keine Privatanteile (bei Bedarf manuell mit Steuerberater).
- Die EUeR wird aus dem Kassenbuch berechnet; LUNA-OS zeigt sie je Position mit der Zeile der Anlage EUeR als
  Eingabehilfe fuer ELSTER. Die Uebermittlung macht der Inhaber selbst.

## 3. Technische Systemdokumentation

- **Speicher:** `buchhaltung/log.jsonl` auf der NAS -- nur anhaengend (append-only). Jeder Eintrag enthaelt
  laufende Nummer, Zeitstempel (Europe/Berlin), Typ, Daten, Urheber und den **SHA-256-Hash des vorigen Eintrags**
  (Hash-Kette). Belegdateien liegen unter `buchhaltung/belege/<jahr>/`, Dateiname beginnt mit dem Hash.
- **Nummernkreise** werden unter einer Dateisperre vergeben; Nummer, Datei und Eintrag entstehen in einem Schritt
  (keine Nummer ohne Beleg, kein Beleg ohne Nummer).
- **Unveraenderbarkeit:** Es gibt keine Funktion zum Aendern oder Loeschen von Eintraegen. Korrekturen sind neue
  Eintraege mit Bezug (Storno, Korrekturbuchung). Jede nachtraegliche Aenderung der Datei bricht die Hash-Kette.
- **Programm:** Python (FastAPI) im Docker-Container auf der NAS; Quellcode in Git (`hsvnils/agent-OS`), jede
  Aenderung mit Commit und Eintrag in `projekt_changelog.md`.
- **Firmendaten** (Steuernummer, Bankverbindung) nur auf der NAS (`buchhaltung/firmendaten.json`), nie im Git.

## 4. Betriebsdokumentation

- **Taegliche Pruefung 05:00:** Hash-Kette und alle Belegdateien (vorhanden, Hash unveraendert); bei Befund sofortige
  Meldung an den Inhaber („nichts reparieren, Backup-Stand vergleichen“).
- **CFO-Finanzcheck** taeglich: Vollstaendigkeit (ungepruefte Belege, fehlende Zahlungen, Monatsabgleich mit dem
  Kontoauszug, fehlende wiederkehrende Posten, Kleinunternehmer-Grenze); Hinweise auf der Startseite und per Telegram.
- **Monatsabgleich:** Der Inhaber gleicht jeden Monat den Kontoauszug mit den erfassten Zahlungen ab und bestaetigt
  das in LUNA-OS („Abgeglichen“, protokolliert).
- **Datensicherung:** (1) NAS; (2) naechtliche Kopie auf den Rechner MACO470 (03:20) und das MacBook (03:00) mit
  Pruefung gegen Schrumpfen; (3) LUNAs Google-Drive: jede Belegdatei laufend, Kassenbuch-Stand taeglich
  (`LUNA-Buchhaltung/Stand/<datum>/`). Wiederherstellung = Kopie zurueckspielen, danach Kettenpruefung.
- **Aufbewahrung** (ab Ende des Kalenderjahres): Belege 8 Jahre, Aufzeichnungen/Journal 10 Jahre, Geschaeftsbriefe
  (angenommene Angebote, Auftragsbestaetigungen, Mails) 6 Jahre. Die Frist steht je Datei im Kassenbuch.
  Es wird nichts automatisch geloescht.
- **Datenzugriff der Finanzverwaltung (§ 147 Abs. 6 AO):** LUNA-OS -> Finanzen -> Jahresabschluss -> „Export (ZIP)“:
  Tabellen als CSV mit `index.xml` (Beschreibungsstandard), vollstaendiges Kassenbuch mit Pruefergebnis, alle Belege
  des Jahres im Original, EUeR als PDF.

## 5. Internes Kontrollsystem (Kurzfassung)

| Risiko | Kontrolle |
|---|---|
| Beleg geht verloren | Ablage sofort beim Eingang, dreifache Sicherung, taegliche Dateipruefung |
| Nachtraegliche Aenderung | Hash-Kette, taegliche Pruefung, keine Aenderungsfunktion |
| Beleg vergessen | Monatsabgleich mit dem Kontoauszug, Hinweis auf fehlende wiederkehrende Posten |
| Doppelte Erfassung | Datei-Hash und Rechnungsnummer je Lieferant werden geprueft |
| Falscher KI-Vorschlag | KI schlaegt nur vor; gebucht wird erst nach Pruefung durch den Inhaber |
| Gefaelschte Beleg-Mail | nur eigene Absender mit bestandener DKIM/DMARC-Pruefung |
| Kleinunternehmer-Grenze | Waechter mit Warnung ab 80 %, Festschreiben ueber 100.000 EUR gesperrt |

## 6. Aenderungen dieser Dokumentation

| Datum | Aenderung | Wer |
|---|---|---|
| 2026-09-28 | Erstfassung (KUNDEN_FINANZEN Etappe 9) | Claude Code, Abnahme durch den Inhaber offen |
| 2026-09-28 | Mahnwesen (Etappe 10) und Aufteilung gemischter Rechnungen (Etappe 11) ergaenzt | Claude Code |
| 2026-09-28 | Barter-Deals (Etappe 12) ergaenzt | Claude Code |
| 2026-09-30 | Zahlungsbedingungen, Vorkasse- und Schlussrechnung (Etappe 18) ergaenzt | Claude Code |
| 2026-09-30 | Beleg-Import aus gespeicherten Mails und Zweck/Begruendung am Beleg ergaenzt | Claude Code |
| 2026-09-30 | Altrechnungen und Mahnungen von vor LUNA (Etappe 19) ergaenzt | Claude Code |
| 2026-09-30 | Provisionen (Etappe 23) ergaenzt | Claude Code |
