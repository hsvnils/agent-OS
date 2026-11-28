# Roadmap: OFC Ticketversand -- Wallet + PDF, Zahlungsbitte per Mail, Tickets nach Zahlung

- Status: in Umsetzung
- Stand: 2026-11-28
- Arbeitsbranch: `ai/ofc-ticketversand`
- Basiscommit: `81ee7f0`
- Naechster Schritt: Erweiterung Handsteuerung (TV6, TV7) geplant 2026-11-28, wartet auf CEO-Go und die Entscheidungen E7-E10. TV5 (Test mit Leverkusen, dann Automatik an) bleibt offen.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Auftrag (CEO 2026-11-26)

1. In den HSV-Mails mit den Ticket-PDFs stehen zusaetzlich **Wallet-Links**. LUNA soll je Ticket **PDF und Wallet-Link
   zusammen** anzeigen, damit der CEO beides weitergeben kann.
2. Per **Knopfdruck eine Mail an die Person** mit der Bitte um Zahlung: Betrag, Spiel, **Verwendungszweck** (Spiel + Person),
   damit die PayPal-Zahlung zugeordnet werden kann.
3. Kommt die PayPal-Mail „Zahlung erhalten“ und LUNA kann sie zuordnen, darf LUNA **automatisch PDF-Ticket und Wallet-Link**
   an die Person senden.

Gehoert fachlich zu OFC (`OFC_ROADMAP.md`) und OFC-Kasse (`OFC_KASSE_ROADMAP.md`); eigene Roadmap, weil hier zum ersten
Mal Mails an Mitglieder gehen.

## Analyse (read-only, Belege)

- **HSV-Mails heute:** `core/ofc.py` `mail_pdfs` (Zeile 48) liest aus HSV-Mails nur Kopf und **PDF-Anhaenge**; der Mailtext
  und damit Links werden **nicht** ausgewertet. `core/ofc_post.py` (O3) gruppiert die PDFs nach Rechnungsnummer und legt sie im
  Fanclub-Ordner ab; das Mailfenster betraegt 60 Tage (`TAGE = 60`).
- **Wallet-Links: Aufbau unbekannt.** Ob es je Ticket einen eigenen Link gibt oder einen fuer die ganze Bestellung, wie er dem
  Ticket zuzuordnen ist (Ticketnummer, Position, Reihenfolge) und auf welchen Host er zeigt, ist im Code nicht belegt. Die
  Zugangsdaten zum Postfach liegen nur auf der NAS. Deshalb klaert das **TV0** mit einer nur lesenden, maskierten Analyse,
  bevor etwas gebaut wird.
- **Tickets:** `ofc_ticket` hat `spiel`, `rechnungsnr`, `pos`, `block`, `reihe`, `sitz`, `preis_cent`, `datei` und den Namen
  aus dem Dateinamen (O2) (`core/ofc_store.py:29`). Das reicht fuer Betrag und Spiel in der Zahlungsbitte.
- **E-Mail-Adressen:** Die Mitgliederliste (OM, Google-Tabelle, nur lesend) hat eine Spalte „E-Mail-Adresse“
  (`core/ofc_mitglieder.py:35/98`). Ticketnamen werden heute per Name mit der Liste abgeglichen (Namensvorschlaege
  `ofc_store.py:401`). Gaeste ohne Mitgliedschaft haben keine Adresse.
- **Senden:** Das Fanclub-Postfach `moin@hsvinside.de` ist laut CISO-Freigabe vom 2026-11-24 **nur lesend**.
  `HsvInsideMail.mail_senden` lehnt ab (`governance/allinkl_mail.py:341`). Senden waere ein **neuer Zugang** und braucht
  die CISO-Freigabe; der Weg ist derselbe wie bei luna@ und nils@ (All-Inkl-SMTP, Kopie per IMAP in „Gesendet“).
- **Zahlungseingang:** `core/ofc_eingang.py` (O5) liest aus PayPal-Mails Name, Betrag, **Mitteilung**, Transaktionscode und
  Datum. Es ordnet heute ueber Name + Betrag und den Gegner in der Mitteilung zu (Regeln ab Zeile 277). Ein eindeutiger
  Verwendungszweck macht das sicherer.
- **Fruehere Entscheidungen, die sich aendern:**
  - `OFC_ROADMAP.md:57`: „Keine Mails/Nachrichten an Mitglieder durch LUNA (Oeffentlichkeit = CEO-Tor); hoechstens Text zum
    Kopieren“. Dieser Auftrag **revidiert** das ausdruecklich (CEO). Das kommt mit Datum ins Entscheidungs-Register.
  - E8 (kein Telegram) bleibt; Hinweise stehen im OFC-Reiter.
  - Keine KI fuer Mitgliederdaten bleibt; die Mailtexte sind feste Vorlagen.

## Befund TV0 (NAS, 2026-11-26, 180 Tage, nur Zaehlungen)

- **Mails:** 21 HSV-Mails, davon 3 mit Ticket-PDFs (10 Tickets). Aeltere Spiele kamen ueber den Fanclub-Ordner (O1), nicht
  per Mail; fuer sie gibt es im Postfach keine Wallet-Links mehr. Wallet gibt es also vor allem fuer **neue Bestellungen**.
- **Wallet-Links:**
  - 6 Links, alle auf `www.eventimsports.de/wallet/<…>/<…>`.
  - 2 von 3 Mails haben **genau einen Link je Ticket**, und **die Ticketnummer steckt im Link** (6 von 6). Damit laesst
    sich jeder Link sicher seinem Ticket zuordnen, unabhaengig von der Reihenfolge.
  - Keine `.pkpass`-Anhaenge.
  - Linktext maskiert „##-## … - …“ (vermutlich Saison und Paarung).
- **Eine Bestellung (4 Tickets) hat gar keinen Link** in der Mail. Entweder kam das Wallet getrennt, oder es gab dafuer
  keins. Klaert der CEO.
- **Spieltag-Nummer:** steht weder in Rechnung noch Ticket (0 von 3) -> der CEO traegt sie je Spiel ein (E2).
- **Adressen:** Von 36 Ticketnamen hat **keiner** einen genauen Namenstreffer in der Mitgliederliste (119 Mitglieder, alle
  mit E-Mail). Die Namen auf den Tickets sind offenbar anders geschrieben (z. B. nur Vorname, Spitzname, andere
  Reihenfolge). Die Namen selbst wurden nicht angesehen (keine Mitgliederdaten an ein Modell). TV2 braucht deshalb eine
  Zuordnung per Auswahl durch den CEO statt eines automatischen Treffers.

**CEO-Hinweise 2026-11-26:** Auf den Tickets steht kein Name (die Namen traegt der CEO in LUNA ein, mit Mitglied aus der Liste); die Mitgliedsnummer gehoert ans Ticket, damit beim Mitglied Tickets und offene Betraege sichtbar sind; der Spielplan wird einmal geholt und bestimmt den Spieltag. Eine Beispiel-Mail vom 23.11. (Wallet) wird vom 15-Minuten-Lauf erfasst, weil Wallet-Links jetzt aus allen HSV-Mails gelesen werden.

**Anpassungen:**
- **TV1:** Wallet-Links werden aus **allen** HSV-Mails gelesen, nicht nur aus Mails mit PDFs, und ueber die Ticketnummer im
  Link dem Ticket zugeordnet. Ohne Link steht „Wallet fehlt“; der CEO kann einen Link von Hand eintragen.
- **TV2:** Die Zuordnung Ticketname -> Mitglied laeuft ueber eine Auswahlliste der Mitglieder (Suche nach Name oder
  Nummer, Vorschlaege nach Nachname/Vorname). Gemerkt wird je Ticketname einmal, auch die Mitgliedsnummer fuer den
  Verwendungszweck (E2).

## Scope

Wallet-Links aus HSV-Mails je Ticket speichern und neben dem PDF zeigen; Empfaenger-Adresse je Ticketname (aus der
Mitgliederliste vorgeschlagen, vom CEO bestaetigt, Gaeste von Hand); Zahlungsbitte per Knopf mit Vorschau; Zuordnung des
Zahlungseingangs ueber den Verwendungszweck; Ticketversand (PDF + Wallet) nach Zahlung, auf Knopf oder automatisch nach E5;
Versandprotokoll; Ansicht auf Rechner, iPad und iPhone.

## Nicht-Scope

- Mahnungen und Erinnerungen bei Nichtzahlung (spaeter eigene Etappe; heute weiter Text zum Kopieren).
- WhatsApp oder SMS (`docs/entscheidungs-register.md`, WhatsApp-Bewertung 2026-09-29).
- KI-Texte oder KI-Zuordnung (Mitgliederdaten an kein Modell).
- Schreiben in die Google-Tabelle der Mitglieder (bleibt nur lesend).
- Loeschen von Dateien oder Mails.
- Telegram-Meldungen zu OFC (E8).
- Schutzbereiche nach `governance/roadmap-workflow.md` B4: Zugangsdaten traegt der CEO ein, Neustart macht der CEO.

## Offene Entscheidungen (CEO)

| Nr | Frage | Empfehlung |
|---|---|---|
| E1 (wie empfohlen) | Von welcher Adresse gehen die Mails? | **moin@hsvinside.de** (Fanclub-Postfach, Antworten landen dort). Braucht SMTP-Freigabe (CISO), das Passwort ist schon in der NAS-`.env`. |
| E2 (CEO 2026-11-26, **geaendert**) | Wie sieht der Verwendungszweck aus? | **`<Spieltag>-<Mitgliedsnummer>`**, z. B. „12-1004“ (12. Spieltag Bundesliga, Mitglied 1004) -- kurz und leicht zu tippen. Fuer Spiele ohne Bundesliga-Spieltag ein Buchstabe davor: Pokal `P<Runde>` (z. B. „P2-1004“), sonstige Spiele `S<laufende Nr. in der Saison>`. Gaeste zahlen unter der Nummer des Mitglieds, das sie mitbringt; ohne Mitglied vergibt LUNA `G<Nr>`. Mehrere Karten einer Person fuer ein Spiel = eine Zahlung. Die Spieltag-Nummer liest LUNA aus Rechnung/Ticket, falls sie dort steht (TV0 prueft das); sonst traegst du sie je Spiel einmal ein. |
| E3 (wie empfohlen) | Wie wird bezahlt? | PayPal wie bisher (E-K5). Die Mail nennt die PayPal-Adresse des Fanclubs und, falls vorhanden, einen **PayPal.me-Link mit Betrag**. Den PayPal.me-Namen traegst du in der `.env` ein (nicht im Repo). |
| E4 (wie empfohlen) | Woher kommt die Adresse je Person? | **Vorschlag aus der Mitgliederliste, Bestaetigung durch dich einmal je Person**; danach merkt LUNA sich die Zuordnung (im Fanclub-Speicher auf der NAS, nicht im Git). Gaeste traegst du von Hand ein. Ohne bestaetigte Adresse kein Versand. |
| E5 (wie empfohlen) | Ticketversand nach Zahlung automatisch? | **Ja, aber nur wenn alles eindeutig ist:** Verwendungszweck mit gueltigem Kurzcode **und** Betrag genau gleich **und** bestaetigte Adresse **und** PDF + Wallet-Link vorhanden **und** noch nicht gesendet. Sonst Vorschlag mit Knopf „Tickets senden“. Abschaltbar (`OFC_AUTO_TICKETVERSAND=0`); an erst nach der Abnahme von TV4. |
| E6 (wie empfohlen) | Zahlungsbitte gesammelt oder je Spiel? | **Je Person und Spiel eine Mail** (passt zu einem Verwendungszweck). Knopf je Spiel „Zahlungsbitten an alle offenen senden“ mit Vorschau der Liste. |
| E7 (wie empfohlen) | Kopie an dich? | **Ja:** Jede gesendete Mail liegt in „Gesendet“ von moin@, und das Versandprotokoll steht im Spiel (wer, wann, was; ohne Mailtext). |

## Etappen

### Etappe TV0: Analyse der HSV-Mails (nur lesend)

- Status: umgesetzt 2026-11-26 (`orchestrator/core/ofc_wallet.py`, `GET /api/ofc/analyse/wallet`, Tests `test_ofc_wallet.py` mit Gegenprobe Maskierung); prueft zusaetzlich, ob die Spieltag-Nummer in Rechnung oder Ticket steht (E2)
- Ziel / Scope: Ein Dry-Run-Endpunkt nur fuer den CEO, `GET /api/ofc/analyse/wallet`. Er liest die HSV-Mails (60 Tage, nur
  lesend) und meldet **maskiert**:
  - je Mail die Zahl der PDFs und der Wallet-Links;
  - den Link-Host (z. B. Apple/Google Wallet oder ein Dienst des HSV);
  - ob ein Link pro Ticket oder pro Bestellung kommt;
  - woran sich Link und Ticket zuordnen lassen (Ticketnummer im Link oder Linktext, Reihenfolge).
  
  Links selbst gibt der Bericht nicht aus. Dazu kommt die Abdeckung der Adressen: wie viele Ticketnamen einen eindeutigen
  Treffer mit E-Mail in der Mitgliederliste haben (nur Zahlen).
- Nicht-Scope: Speichern, Anzeigen, Senden.
- Gate: Bericht auf der NAS; der CEO sieht ihn. Ergebnis entscheidet, ob TV1 Links je Ticket zuordnen kann. Gibt es nur einen
  Link je Bestellung, wird TV1 angepasst und dir vorgelegt.
- Verifikation: `GET /api/ofc/analyse/wallet` -> erwartet: `ok: true`, Zahl der Mails mit Tickets > 0, je Mail
  `wallet_links` und `pdfs` als Zahlen, keine URL und kein Name im Text (Test mit Gegenprobe).
- Risiko / Rueckweg: nur lesend; Rueckweg ist keiner noetig.
- Aufwand: klein.

### Etappe TV1: Wallet-Links speichern und neben dem PDF anzeigen

- Status: umgesetzt 2026-11-26 (`core/ofc_wallet.py` `wallet_links`/`wallet_anwenden`/`wallet_von_hand`, im 15-Minuten-Lauf `ofc_post.lauf` mit denselben Mails, Knopf „📱 Wallet-Links holen“ bis 365 Tage, je Ticket 📄/📱/📋 bzw. 📱＋; Tests `test_ofc_ticketversand.py` mit Gegenproben)
- Ziel / Scope:
  - **Speichern:** Der 15-Minuten-Lauf (O3) liest kuenftig auch den Mailtext der HSV-Mails und speichert je Ticket den
    Wallet-Link (Ereignis `ofc_wallet` mit Ticketnummer und Link, Quelle Message-ID) im Fanclub-Speicher auf der NAS.
  - **Nachholen:** einmal fuer die vorhandenen Spiele, so weit die Mails im Postfach noch da sind (Fenster fuer diesen
    Lauf bis Saisonbeginn erweitert).
  - **Anzeige:** In der Spielansicht je Ticket „📄 PDF · 📱 Wallet“ nebeneinander, mit Knopf „Link kopieren“. Fehlt ein
    Link, steht dort „Wallet fehlt“.
  - **Schutz:** Wallet-Links sind wie Eintrittskarten. Sie sind nur fuer den CEO sichtbar, stehen nie in Log, Fehlertext
    oder Git und gehen an kein Modell.
- Gate: Test-Gate mit Gegenproben (Link landet beim richtigen Ticket; fremde Domain wird nicht als Wallet-Link genommen; Link
  erscheint nicht im Log); headless auf Rechner/iPad/iPhone.
- Verifikation (NAS, nur Zaehlungen): `GET /api/ofc/uebersicht` -> erwartet: je offenem Spiel „Tickets mit Wallet“ =
  Zahl der Tickets laut TV0.
- Risiko / Rueckweg: additiv (neues Ereignis), Anzeige ausblendbar.
- Abhaengig von: TV0. Aufwand: mittel.

### Etappe TV2: Empfaenger je Person

- Status: umgesetzt 2026-11-26 (CEO: Tickets tragen keinen Namen, der CEO traegt ihn ein: Auswahl „Name (Nr. …)“ merkt die Mitgliedsnummer am Ticket, Ereignis `ofc_mitglied`; beim Mitglied Tickets, Spiele und offener Betrag; **Spielplan** 2026/27 als feste Datei `core/ofc_spielplan.py` (OpenLigaDB, einmal geholt), Spieltag je Spiel aus dem Datum oder von Hand)
- Ziel / Scope:
  - Je Ticketname schlaegt LUNA die Adresse aus der Mitgliederliste vor (eindeutiger Namenstreffer).
  - Der CEO bestaetigt einmal je Person oder traegt die Adresse von Hand ein (Gaeste). Das wird als Ereignis `ofc_kontakt`
    im Fanclub-Speicher gemerkt; die Tabelle bleibt unveraendert.
  - Anzeige je Ticket: „✉️ anna@… bestaetigt“ / „Adresse fehlt“.
- Gate: Test-Gate mit Gegenproben (zwei gleiche Namen -> kein Vorschlag; ohne Bestaetigung kein Versand moeglich).
- Abhaengig von: nichts (parallel zu TV1). Aufwand: klein.

### Etappe TV3: Zahlungsbitte per Knopf (Senden ueber moin@)

- Status: umgesetzt 2026-11-26 (`core/ofc_versand.py`, `HsvInsideMail.mail_senden` mit Auflagen, Abschnitt „✉️ Zahlungsbitten“ im Spiel mit Mail-Vorschau, Senden, Testmail an moin@, „an alle bereiten“; Adresse aus der Mitgliederliste ueber die Nummer am Ticket; Tests `test_ofc_versand.py` mit Gegenproben)
- Ziel / Scope:
  - **Senden aus moin@:** freigeschaltet nach E1 und CISO-Auflagen:
    - nur aus der OFC-Ansicht;
    - nur an bestaetigte Adressen;
    - nur nach CEO-Klick mit Vorschau;
    - Kopie in „Gesendet“;
    - hoechstens 30 Mails je Stunde;
    - Posteingang weiter nur lesend wie bisher.
  - **Zahlungsbitte** je Person und Spiel (E6), als feste Vorlage, ohne KI: Spiel, Datum, Karten (Block/Reihe/Sitz), Betrag,
    Verwendungszweck nach E2, Zahlweg nach E3, Absender HSVInside.
  - **Knoepfe:** „Zahlungsbitte senden“ je Person und „an alle offenen dieses Spiels“ mit Liste zur Kontrolle.
  - **Schutz:** Ohne Klick auf „erneut senden“ geht keine Mail doppelt raus.
  - **Protokoll:** Ereignis `ofc_mail` mit Art, Tickets, Zeit und maskierter Adresse, ohne Mailtext.
  - **Doku:** Zugriffs-Policy, `docs/datenfluesse.md`, Datenschutz-Nachtrag.
- Gate: Test-Gate mit Gegenproben (ohne Bestaetigung kein Versand; doppelter Klick sendet nicht doppelt; ohne bestaetigte
  Adresse abgelehnt; Posteingang bleibt nur lesend). **Erste echte Mail an dich selbst** (Testmodus: Empfaenger = CEO).
- Verifikation: Die Testmail kommt bei dir an (Empfaenger, nicht Absender), die Kopie liegt in „Gesendet“ von moin@, und das
  Protokoll zeigt `gesendet`.
- Risiko / Rueckweg: Eine falsche Mail kann nicht zurueckgeholt werden; daher Vorschau, Bestaetigung, Testmodus und Limit.
  Schalter `OFC_MAILVERSAND=0` sperrt alles.
- Abhaengig von: TV2. Aufwand: mittel.

### Etappe TV3b: Person am Ticket (Mitglied oder extern), Textkorrektur, klarere Knoepfe

- Status: umgesetzt 2026-11-26 (CEO-Go)
- Ziel / Scope:
  - **Dialog ✏️ „Person“:** „Mitglied oder bekannte Person suchen“ fuellt Vorname, Nachname und E-Mail; ein Mitglied wird
    ueber die Nummer gemerkt (Daten aus der Liste, Felder gesperrt, „✕ loesen“).
  - **Externe Personen** (CEO: Karten gehen auch ausserhalb weiter) mit Vorname, Nachname und E-Mail bekommen eine eigene
    Nummer `G<n>` (Ereignis `ofc_person` im Fanclub-Speicher, gleiche E-Mail = gleiche Person) und erscheinen in der Suche
    wieder. Verwendungszweck dann z. B. „11-G3“.
  - **Beim Oeffnen** bleibt der Name auf dem Ticket; der Name der Person greift nur bei aktiver Auswahl.
  - **Mailtext:** „über deinen Fanclub HSVInside“.
  - **Knoepfe** auf dem Rechner mit Wort („Person“, „PDF“, „Wallet“, „Link“), auf dem iPhone nur Symbol, mit Hinweis beim
    Darueberfahren.
- Gate: Tests `test_ofc_versand.py` (`TestExtern`, API mit `extern`), headless Rechner/iPhone.

### Etappe TV3c: Karten von Hand als bezahlt markieren

- Status: umgesetzt 2026-11-26 (CEO-Go)
- Ziel / Scope:
  - **Knopf „💶 bezahlt“ je Karte** und **„💶 alle bezahlt“** je Person in den Zahlungsbitten. Ein Fenster fragt Zahlart
    (Bar, Ueberweisung, PayPal, Sonstiges), Datum und Notiz ab.
  - **„↩︎ bezahlt“** nimmt die Markierung zurueck.
  - **Protokoll:** Ereignis `ofc_bezahlt` (nichts geloescht).
  - **Wirkung:** `bezahlt_stand` zaehlt die Karte als bezahlt. Damit gibt es keine Zahlungsbitte mehr, beim Mitglied ist
    nichts offen, und das Spiel kann „abschliessbar“ werden.
  - **Kasse (= PayPal-Konto) unberuehrt:** Bar und Ueberweisung buchen nichts.
- Gate: Tests `test_ofc_versand.py` (`TestHandBezahlt`, API) mit Gegenprobe; headless Rechner/iPhone (Knoepfe brechen unter
  den Text um).

### Etappe TV4: Zahlung zuordnen und Tickets senden

- Status: umgesetzt 2026-11-26 (CEO-Go). Umsetzung:
  - **Zuordnung:** `ofc_eingang.zweck_treffer` erkennt „11-1004“, „11 1004“, „11/1004“, „P2-0001“, „11-G3“ (fuehrende Nullen egal) und greift nur bei genau passendem Betrag der offenen Karten dieser Person in diesem Spiel; sonst gelten die bisherigen Regeln.
  - **Ticketmail** (`ofc_versand.tickets_*`): PDF-Tickets als Anhang, Wallet-Links im Text, feste Vorlage; Abschnitt „🎟 Ticketversand“ im Spiel mit Vorschau, Senden, Testmail an moin@, nie doppelt ohne „erneut“.
  - **Automatik** `auto_lauf` im 15-Minuten-Lauf: nur Zahlungen der letzten 14 Tage, die per Verwendungszweck zugeordnet wurden, nur mit Adresse, PDF und Wallet fuer alle Karten, nur einmal; Schalter `OFC_AUTO_TICKETVERSAND=1` (Standard aus).
  - **Tests** `test_ofc_tv4.py` mit Gegenproben.
- Ziel / Scope:
  - **Zuordnung:** `ofc_eingang` erkennt zuerst den Kurzcode aus dem Verwendungszweck. Passt der Betrag genau, sind die
    Tickets bezahlt; sonst greifen die bisherigen Regeln (Name + Betrag + Gegner).
  - **Ticketmail:** Danach bietet LUNA „Tickets senden“ an. Die Mail enthaelt die PDF-Tickets als Anhang, die Wallet-Links
    und Spiel, Datum und Platz.
  - **Automatik (E5):** ist alles eindeutig, sendet LUNA im 15-Minuten-Lauf selbst, hoechstens einmal je Ticket.
  - **Sichtbarkeit:** Im Spiel steht je Ticket „bezahlt · Ticket gesendet am …“; im OFC-Reiter steht ein Hinweis, was
    automatisch rausging (kein Telegram, E8).
- Gate: Test-Gate mit Gegenproben:
  - falscher Betrag -> kein Auto-Versand;
  - unbekannter Code -> kein Auto-Versand;
  - schon gesendet -> nicht erneut;
  - Schalter aus -> nur Vorschlag;
  - PDF oder Wallet fehlt -> nur Vorschlag mit Hinweis.
  
  Echter Durchlauf mit dir als Empfaenger (Testmodus).
- Verifikation: Eine Testzahlung (z. B. 1 Euro mit Verwendungszweck) fuehrt zu „bezahlt“ und einer Ticketmail beim
  Empfaenger; das Protokoll zeigt den Versand genau einmal.
- Risiko / Rueckweg: Auto-Versand an die falsche Person. Dagegen stehen strenge Bedingungen, ein Limit und das Protokoll.
  Rueckweg: `OFC_AUTO_TICKETVERSAND=0`.
- Abhaengig von: TV1, TV3. Aufwand: mittel.

### Etappe TV5: Abnahme

- Gate:
  1. Fuer ein echtes Spiel stehen bei allen Tickets PDF und Wallet nebeneinander.
  2. Zahlungsbitten an echte Mitglieder sind angekommen.
  3. Eine echte Zahlung wurde zugeordnet und das Ticket automatisch versendet.
  
  Dazu kommt die Sichtabnahme auf Rechner, iPad und iPhone. Danach wird der Auto-Versand dauerhaft eingeschaltet (E5).
- Nach dem Deploy wird sofort ein datiertes To-do „Roadmap: OFC_TICKETVERSAND_ROADMAP.md“ angelegt (F4).

## Erweiterung Handsteuerung (CEO 2026-11-28, Plan)

Auftrag nach der Sichtabnahme der Mitglieder:
1. Eine Karte **von Hand als „nicht bezahlt“** markieren koennen -- nur mit **Grund**, genau wie beim Anhaken „bezahlt“.
2. **Je Person von Hand** die **Ticketmail** und die **Zahlungsbitte** anstossen koennen.
3. Ticketversand **vor** einer abgehakten Zahlung nur mit **Kommentar**.

Bestand (read-only geprueft):
- „💶 bezahlt“ (TV3c) fragt Zahlart und Datum ab; die Notiz ist bisher **freiwillig**. „↩︎ bezahlt“ nimmt nur eine
  Hand-Markierung zurueck; eine von LUNA zugeordnete PayPal-Zahlung laesst sich bisher **nicht** ueberstimmen.
- Zahlungsbitte je Person gibt es schon (Spiel oeffnen -> „✉️ Zahlungsbitten“ -> „👁 Mail“ -> Senden/Erneut senden).
- Ticketversand je Person gibt es nur fuer **bezahlte** Karten; unbezahlte Karten erscheinen dort gar nicht.

### Offene Entscheidungen (CEO)

| Nr. | Frage | Empfehlung |
|---|---|---|
| E7 | Grund Pflicht auch beim Anhaken „bezahlt“ und beim Zuruecknehmen? | **Ja, bei jeder Hand-Aenderung** (mind. 3 Zeichen), steht im Verlauf der Karte. |
| E8 | Was bewirkt „nicht bezahlt“? | **Ueberstimmt alles**, auch eine zugeordnete PayPal-Zahlung (z. B. Rueckbuchung, falsch zugeordnet). Die Karte ist wieder offen (Zahlungsbitte moeglich, beim Mitglied offen), die Automatik sendet dafuer nie. Die Zuordnung des Eingangs und die Kasse bleiben unveraendert; ein Hinweis zeigt „PayPal-Eingang zugeordnet, von Hand nicht bezahlt“. Zuruecknehmen geht jederzeit (mit Grund). |
| E9 | Text der Ticketmail vor Zahlung? | **Ohne** „danke fuer deine Zahlung“, dafuer mit offenem Betrag, Verwendungszweck und PayPal-Adresse moin@hsvinside.de. |
| E10 | Wo die Knoepfe? | **Im Spiel** (Ticketversand zeigt alle Personen mit Karten, unbezahlte mit „🎟 Vor Zahlung senden“) **und** in der Mitgliederansicht je Spiel „✉️ Zahlungsbitte“ und „🎟 Tickets senden“ -- beide oeffnen dieselbe Vorschau. |

Bleibt unveraendert: Gekuendigte und Personen ohne E-Mail bleiben gesperrt; jede Mail mit Vorschau, Rueckfrage und
Testmail an moin@; hoechstens 30 Mails je Stunde; die Automatik (TV4) sendet nie vor einer Zahlung.

### Etappe TV6: Bezahlt / nicht bezahlt von Hand mit Grund

- Status: geplant
- Inhalt:
  - Neue Markierung „nicht bezahlt“ (Ereignis `ofc_bezahlt` mit `nicht_bezahlt`) mit Pflicht-Grund; sie gilt in
    `bezahlt_stand` vor der PayPal-Zuordnung (E8).
  - Grund Pflicht bei jeder Hand-Aenderung (E7); serverseitig geprueft, nicht nur im Dialog.
  - Am Ticket: „❌ nicht bezahlt“ (bei bezahlten Karten) und „↩︎ Markierung zuruecknehmen“; Abzeichen mit Grund beim
    Darueberfahren; Verlauf der Hand-Markierungen im Spiel.
  - Wirkung ueberall gleich: Spieluebersicht, Zahlungsbitten, Ticketversand, Mitgliederansicht, Automatik.
- Tests mit Gegenproben: ohne Grund abgelehnt; „nicht bezahlt“ schlaegt PayPal-Zuordnung; Automatik sendet nicht;
  Zahlungsbitte wieder moeglich; Zuruecknehmen stellt den alten Stand her; Kasse unveraendert.
- Gate: am Testspiel eine per PayPal bezahlte Karte auf „nicht bezahlt“ setzen und zuruecknehmen.

### Etappe TV7: Versand je Person von Hand

- Status: geplant
- Inhalt:
  - Ticketversand listet **alle** Personen mit Karten des Spiels; unbezahlte mit „🎟 Vor Zahlung senden“ -> Vorschau mit
    Text nach E9 und **Pflicht-Kommentar**; der Kommentar steht im Mail-Protokoll.
  - In der Mitgliederansicht je Spiel „✉️ Zahlungsbitte“ und „🎟 Tickets senden“ (E10).
  - Server prueft: vor Zahlung nur mit Kommentar und nur von Hand (nie Automatik).
- Tests mit Gegenproben: ohne Kommentar abgelehnt; Automatik sendet unbezahlt nie; Text ohne Dank; Gekuendigte gesperrt.
- Gate: Testmail an moin@ fuer eine unbezahlte Karte, danach Sichtabnahme auf Rechner, iPad, iPhone.

Reihenfolge: TV6 -> TV7, nach Go am Stueck gebaut, ein Deploy (nur `luna-os`). Danach weiter mit TV5.

## Reihenfolge, Aufwand, Deploy

TV0 (eigener kleiner Deploy, weil das Ergebnis TV1 bestimmt) -> TV1 + TV2 -> TV3 -> TV4, nach Go am Stueck gebaut, dann ein
Deploy. Neustart von `luna-os` durch den CEO; die neuen Schalter (`OFC_MAILVERSAND`, `OFC_AUTO_TICKETVERSAND`, PayPal.me-Name)
traegt der CEO in die NAS-`.env` ein, danach braucht es `docker compose up -d --force-recreate luna-os`. Gesamtaufwand rund
2 Arbeitstage.

## Dokumentationspflichten

`projekt_changelog.md`, Etappen-Status hier, `ROADMAP.md`, `docs/entscheidungs-register.md` (Revision „keine Mails an
Mitglieder“, E1-E7), `governance/zugriffs-policy.md` (`hsvinside_mail` Senden), `docs/datenfluesse.md`,
`docs/datenschutz-ki-nutzung.md`, `docs/bekannte-fehler.md`, `OFC_ROADMAP.md` (Verweis), Dienste-Register (neue Schluessel).

## Definition of Done

TV5 bestanden und Sichtabnahme durch den CEO; Auto-Versand laeuft; Status „abgeschlossen“ traegt Claude Code ein.
