# Roadmap: OFC-Kasse -- Mitgliedsbeitraege und Fanclub-Kasse HSVInside

- Status: in Umsetzung
- Stand: 2026-11-24
- Arbeitsbranch: `main` (KA0 gemergt)
- Basiscommit: `fda2486`
- Naechster Schritt: KA0 live und auf der NAS geprueft (2026-11-25: 119 Mitglieder, 66 beitragspflichtig, Soll 2.640 € fuer 2026 und 2027, 9 mit Hinweis). Naechster Schritt: Go fuer KA1 (Beitragszahlungen erkennen). Fuer KA4 wird der PayPal-Aktivitaeten-Export (CSV) gebraucht.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Anlass (CEO 2026-11-24)

Folgethema aus `OFC_ROADMAP.md`: Die Mitgliedsbeitraege und die Kasse des Fanclubs laufen ueber PayPal. Der CEO
gleicht heute von Hand ab, wer seinen Beitrag bezahlt hat und wie viel Geld in der Kasse ist. Ziel: LUNA erkennt
Beitragszahlungen selbst, zeigt offene Beitraege je Mitglied und fuehrt ein Kassenbuch des Fanclubs mit Kassenstand
und Kassenbericht -- getrennt von der Buchhaltung von Hanserautisch.

## Analyse (read-only, mit Belegen, 2026-11-24)

- **Mitgliederliste (OM, `core/ofc_mitglieder.py`, Blatt „Formularantworten 1“, nur gezaehlt):** 119 Mitglieder,
  11 Anfragen. Spalten u. a. `Mitglied seit:`, `Beitrag`, `Nächste Zahlung`, `Welche Mitgliedschaft möchtest du anfragen?`.
  - Mitgliedschaft: Standard (kostenfrei) 52, Gold (jaehrliche Zahlung) 65 (zwei Schreibweisen „jaehrliche/Jaehrliche“),
    Foerdermitgliedschaft (Betrag frei, im Kommentarfeld) 1, Vorstand 1.
  - Spalte `Beitrag`: 67 x „40,00 €“, 10 x „0,00 €“, 42 leer. Erwarteter Jahresbeitrag Gold also ca. 65 x 40 € = 2.600 €.
  - Spalte `Nächste Zahlung`: 42 gefuellt (38 „2027…“, 4 „01.01.2…“), 77 leer -> Faelligkeit wird heute nur teilweise
    gepflegt.
- **PayPal-Eingaenge (O5, letzte 120 Tage):** 42 Eingaenge, Summe 2.511,50 €; keine Mitteilung nennt „Beitrag“ oder
  „Mitglied“ -- Beitraege kommen also eher ohne Text, zum Jahreswechsel, oder sind im Zeitraum nicht dabei.
  Einzelfaelle ohne Ticket: „Trikot“ (Merch), Ueberweisung an „Hamburger Sparkasse AG ••…“ (PayPal -> Bankkonto),
  Eingang ohne Mitteilung mit rundem Betrag (moeglicherweise Beitrag/Spende).
- **Eigene Ausgaben (O4):** PayPal-Zahlungen an Eventim/HSV fuer Tickets (`ofc_zahlung`), dazu Ruecklastschriften
  und Erstattungen. Andere Ausgaben (Gebuehren, Auslagen, Merch-Einkauf) sind bisher nicht erfasst.
- **Speicher:** `fanclub/log.jsonl` (Ereignisse `ofc_*`), nur CEO sichtbar, nicht in der Buchhaltung.
- **Register:** PayPal-CSV-Import am 2026-11-24 zurueckgestellt (`docs/entscheidungs-register.md`, OFC O5) -- wird hier
  fuer den Kassenabgleich wieder aufgegriffen. Kein Zugang zu PayPal-API oder Online-Banking vorhanden.
- **Geklaert (CEO 2026-11-24):** Der Fanclub nutzt ausschliesslich PayPal (E-K5). **Noch offen:** welcher Zeitraum das
  Geschaeftsjahr ist (E-K6), wie neue Mitglieder im laufenden Jahr zahlen (E-K3).

## Grundsaetze (wie OFC)

- **Getrennt von der Buchhaltung** (`fanclub/`, eigene Ereignisse; nichts in EUeR, Kostenstatistik, Firmenakte).
- **Keine KI fuer Mitgliederdaten:** Erkennung regelbasiert (Name, Betrag, Mitteilung, Datum); was nicht eindeutig
  ist, landet in „Zuordnen“ -- der CEO klickt.
- **Nur CEO sieht OFC.** LUNA **schreibt Mitgliedern nichts** (Erinnerungen nur als Text zum Kopieren) und schickt
  keine Telegram-Nachrichten (E8).
- **Google-Tabelle bleibt nur lesend:** LUNA traegt nichts in die Mitgliederliste ein (ein Schreibzugang waere ein
  neuer Zugang -> CISO + eigenes Go).
- **Kein Geld bewegen:** LUNA erfasst und zeigt nur; Zahlungen, Erstattungen und Ueberweisungen macht der CEO.
- **Nichts loeschen:** Korrekturen als neues Ereignis (Storno/Umbuchung), alles nachvollziehbar.

## Entscheidungen fuer den CEO (vor KA0)

| Nr | Frage | Empfehlung |
|---|---|---|
| E-K1 | Beitragsjahr und Faelligkeit | **Entschieden (CEO 2026-11-24): Kalenderjahr, faellig 01.01.** |
| E-K2 | Woher kommt der Soll-Beitrag? | **Entschieden (CEO 2026-11-24): Goldmitgliedschaft 40 € pro Jahr.** Empfehlung zur Quelle: aus der Google-Tabelle (Spalten `Beitrag` + Mitgliedschaft), nur lesend; fehlt `Beitrag` bei Gold: 40 €. Bezahlt-Status lebt nur in LUNA. |
| E-K3 | Neue Mitglieder im laufenden Jahr | **Entschieden (CEO 2026-11-24): anteilig ab dem Beitrittsmonat** (Monat mitgezaehlt, faellig am Beitrittstag). Zurzeit werden keine neuen Goldmitglieder aufgenommen. |
| E-K4 | Wann gilt ein Eingang automatisch als Beitrag? | **Entschieden (CEO 2026-11-24): wie empfohlen.** Name = Mitglied (oder gelernter Alias) **und** Betrag = Beitrag oder Vielfaches (mehrere Jahre/Mitglieder), **und** kein Ticket passt -- oder die Mitteilung nennt Beitrag/Mitgliedschaft/Gold. Sonst Vorschlag. |
| E-K5 | Was gehoert zur Kasse? | **Entschieden (CEO 2026-11-24): ausschliesslich PayPal.** Kasse = ein Konto (PayPal), kein Bargeld, kein Bankkonto. Anfangsbestand traegt der CEO zu einem Stichtag ein; Auszahlungen von PayPal auf ein Bankkonto zaehlen als Abgang (Kategorie „Auszahlung“). |
| E-K6 | Geschaeftsjahr fuer den Kassenbericht | **Entschieden (CEO 2026-11-24): wie empfohlen.** Kalenderjahr (passt zum Beitragsjahr); alternativ Saison Juli-Juni. |
| E-K7 | Abgleich mit PayPal | **Entschieden (CEO 2026-11-24): wie empfohlen.** CEO laedt den PayPal-Kontoauszug (CSV-Export) im Reiter hoch; kein API-Zugang (waere neuer Zugang, CISO). |
| E-K8 | Abgleich mit der Bank | **Entfaellt** (E-K5: nur PayPal). |
| E-K9 | Kategorien im Kassenbuch | **Entschieden (CEO 2026-11-24): wie empfohlen.** Tickets, Beitraege, Merch/Trikot, Spenden, Gebuehren, Auslagen, Auszahlung, Sonstiges -- im Reiter erweiterbar. |

## Etappen

### Etappe KA0: Beitragsdaten lesen und pruefen

- Status: umgesetzt (2026-11-24; `core/ofc_beitraege.py`: Mitgliedschaft vereinheitlicht (Gold/kostenfrei/Foerder/Vorstand/unklar), Soll je Kalenderjahr faellig 01.01., Gold 40 € (fehlt der Betrag: 40 € + Hinweis; abweichender Betrag gilt + Hinweis), Eintritt im Jahr anteilig ab Beitrittsmonat, spaeterer Eintritt = 0 €; Hinweise zur Datenqualitaet; `GET /api/ofc/beitraege?jahr=` nur CEO, nur lesend; Ansicht „🎫 Beitraege“ (Soll, Arten, Filter beitragspflichtig/mit Hinweis/alle, Jahr wechseln); `test_ofc_beitraege.py`; Probe auf echten Daten: 119 Mitglieder, 66 beitragspflichtig, Soll 2.640 €, 9 mit Hinweis (Dubletten + 1 x kostenfrei mit 40 €); Sichtpruefung headless Rechner/iPad/iPhone ok)
- Ziel / Scope / Nicht-Scope: Aus der Mitgliederliste je Mitglied Soll-Beitrag, Mitgliedschaftsart (Schreibweisen
  vereinheitlicht) und Faelligkeit ableiten (E-K1 bis E-K3); Datenqualitaets-Hinweise im Reiter (Gold ohne Beitrag,
  Gold ohne `Nächste Zahlung`, Foerdermitglied ohne Betrag, Betrag bei kostenfrei). Nicht-Scope: Zahlungen, Schreiben
  in die Tabelle.
- Gate: Tests (Schreibweisen, leere/fehlerhafte Felder, Foerderbetrag aus dem Kommentar nur als Hinweis); Gegenprobe:
  Summe Soll = Anzahl Gold x 40 € + Foerderbetraege.
- Verifikation: `GET /api/ofc/beitraege?jahr=2027` liefert 119 Mitglieder, Soll-Summe passt zur Zaehlung oben
  (ca. 2.600 € + Foerderbetrag), Hinweisliste nennt die 42 Faelle ohne Faelligkeit.
- Dry-Run: nur lesend, schreibt nichts.
- Risiko / Rueckweg: falsche Ableitung -> Regel anpassen; nichts gespeichert.
- Abhaengig von / Aufwand / Risiko: OM / klein / gering.

### Etappe KA1: Beitragszahlungen erkennen

- Status: geplant
- Ziel / Scope / Nicht-Scope: PayPal-Eingaenge (O5) bekommen neben „Ticket“ die Art **„Beitrag“** (Jahr + Mitglied);
  Regel E-K4 automatisch, sonst Vorschlag „Beitrag von X fuer 2027“; Mehrjahres- und Familienzahlung (ein Zahler fuer
  mehrere Mitglieder, Alias wie in O5); „Kein Ticket“ aus O5 wird zu waehlbarer Art (Beitrag, Merch, Spende,
  Sonstiges). Nicht-Scope: Mahnungen, Versand.
- Gate: Tests (Beitrag exakt, 80 € = 2 Jahre, Familie, Betrag passt auch zu einem Ticket -> Ticket/Mitteilung
  entscheidet, Name unbekannt, Rueckzahlung); bestehende O5-Tests bleiben gruen.
- Verifikation: echter Beitragseingang -> Mitglied „bezahlt 2027“ in der Beitragsliste; kein Ticket faelschlich als
  bezahlt.
- Dry-Run: Vorschau „Aus Postfach holen“ zeigt Beitrag/Ticket je Eingang, speichert nichts.
- Risiko / Rueckweg: falsche Art per Klick aendern; Klicks werden nie automatisch ueberschrieben.
- Abhaengig von / Aufwand / Risiko: KA0, O5 / mittel / mittel (Beitraege ohne Mitteilung).

### Etappe KA2: Beitragsuebersicht und offene Beitraege

- Status: geplant
- Ziel / Scope / Nicht-Scope: Ansicht „🎫 Beitraege“ je Jahr: Soll / bezahlt / offen je Mitglied, Filter (offen,
  Gold, neu), Summen; offene Beitraege mit **Text zum Kopieren** (wie O6); Hinweis im Reiter ab 4 Wochen nach
  Faelligkeit; Export CSV + PDF (A4 hochkant). Per Klick: „bezahlt (bar/Ueberweisung)“ fuer Zahlungen ausserhalb von
  PayPal, „erlassen“. Nicht-Scope: Versand an Mitglieder, Kuendigungen.
- Gate: Tests (Jahreswechsel, erlassen, bar bezahlt, Export hochkant); Sichtpruefung Rechner/iPad/iPhone.
- Verifikation: Liste 2027 zeigt alle Gold-Mitglieder; Summe offen = Soll - bezahlt.
- Dry-Run: Vorschau je Klick-Aktion.
- Risiko / Rueckweg: Klick-Aktionen loesbar (neues Ereignis).
- Abhaengig von / Aufwand / Risiko: KA1 / klein / gering.

### Etappe KA3: Kassenbuch

- Status: geplant
- Ziel / Scope / Nicht-Scope: Kassenbuch des Fanclubs aus allen vorhandenen Quellen: Einnahmen (Tickets O5, Beitraege
  KA1, Merch/Spenden), Ausgaben (eigene Ticketzahlungen O4, Erstattungen, Gebuehren, Auszahlungen auf ein Bankkonto);
  ein Konto PayPal (E-K5) mit Anfangsbestand; Kategorien E-K9; Buchung per Hand fuer Auslagen und Korrekturen (mit
  optionalem Beleg-Foto in `fanclub/`); Kassenstand. Nicht-Scope: Buchhaltung, Steuer.
- Gate: Tests (Auszahlung als Abgang, Storno statt Loeschen, Doppelte ueber Transaktionscode, Kassenstand =
  Anfangsbestand + Summe); Sichtpruefung.
- Verifikation: Kassenstand PayPal in LUNA = Guthaben laut PayPal-Konto des CEO (Stichtag, vom CEO abgelesen).
- Dry-Run: Vorschau jeder Handbuchung.
- Risiko / Rueckweg: Storno-Buchung; Anfangsbestand aenderbar mit Historie.
- Abhaengig von / Aufwand / Risiko: KA1, O4, O5 / mittel / mittel.

### Etappe KA4: Abgleich mit dem PayPal-Kontoauszug

- Status: geplant
- Ziel / Scope / Nicht-Scope: CSV-Upload im Reiter (PayPal-Aktivitaeten, E-K7; Bank entfaellt nach E-K5): Zeilen mit
  vorhandenen Buchungen abgleichen (Transaktionscode, Betrag, Datum), fehlende als Vorschlag uebernehmen (alte Zahlungen
  vor dem Postfach-Zeitraum, Gebuehren), Abweichungen anzeigen. Nicht-Scope: API-Zugaenge, automatischer Abruf.
- Gate: Tests (PayPal-CSV deutsch, Dubletten, Gebuehrenzeilen, Auszahlung auf ein Bankkonto); Gegenprobe mit
  erfundenen Dateien.
- Verifikation: echter PayPal-Export eines Monats -> 0 unerklaerte Abweichungen oder klare Liste.
- Dry-Run: Upload zeigt erst die Vorschau, uebernimmt nur nach Klick.
- Risiko / Rueckweg: Import-Lauf als Ganzes stornierbar; hochgeladene Datei bleibt nur in `fanclub/`.
- Abhaengig von / Aufwand / Risiko: KA3 / mittel / mittel (CSV-Formate).

### Etappe KA5: Kassenbericht

- Status: geplant
- Ziel / Scope / Nicht-Scope: Kassenbericht je Geschaeftsjahr (E-K6): Anfangsbestand, Einnahmen und Ausgaben nach
  Kategorie, Endbestand, Beitragsquote, offene Posten (Tickets + Beitraege); PDF A4 hochkant + CSV, z. B. fuer
  Kassenpruefung oder Mitgliederversammlung. Nicht-Scope: Veroeffentlichung (CEO-Tor), steuerliche Bewertung.
- Gate: Tests (Summen gehen auf, Jahresgrenze, leere Kategorien); Sichtpruefung PDF.
- Verifikation: Bericht fuer ein abgeschlossenes Testjahr stimmt mit dem Kassenbuch ueberein.
- Dry-Run: Vorschau im Reiter vor dem Export.
- Risiko / Rueckweg: reine Auswertung, schreibt nichts.
- Abhaengig von / Aufwand / Risiko: KA3 (KA4 empfohlen) / klein / gering.

## Reihenfolge

KA0 -> KA1 -> KA2 (Beitraege fertig, eigenstaendig nutzbar) -> KA3 -> KA4 -> KA5. Jede Etappe einzeln mit Go; nach
KA2 kann eine Pause sinnvoll sein (Beitraege laufen meist zum Jahreswechsel ein).

## Dokumentation bei der Umsetzung

`projekt_changelog.md`, Etappen-Status hier, `ROADMAP.md`, `docs/entscheidungs-register.md` (E-K1 bis E-K9),
`docs/datenfluesse.md` (CSV-Upload, Speicher `fanclub/`), `governance/zugriffs-policy.md` (falls neue Zugaenge),
`docs/datenschutz-ki-nutzung.md` (keine KI fuer Mitglieder- und Kassendaten), `docs/bekannte-fehler.md`
(Test-Baseline).
