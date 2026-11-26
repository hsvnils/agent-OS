# Roadmap: OFC Ticketversand -- Wallet + PDF, Zahlungsbitte per Mail, Tickets nach Zahlung

- Status: geplant
- Stand: 2026-11-26
- Arbeitsbranch: `ai/ofc-ticketversand`
- Basiscommit: `81ee7f0`
- Naechster Schritt: Roadmap liegt dem CEO vor; Entscheidungen E1-E7 beantworten, dann Go fuer TV0 (Analyse der HSV-Mails auf Wallet-Links, nur lesend).
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
| E1 | Von welcher Adresse gehen die Mails? | **moin@hsvinside.de** (Fanclub-Postfach, Antworten landen dort). Braucht SMTP-Freigabe (CISO), das Passwort ist schon in der NAS-`.env`. |
| E2 | Wie sieht der Verwendungszweck aus? | **`<Gegner> <TT.MM.> <Vorname Nachname> K<Kurzcode>`**, z. B. „FCB 13.12. Anna Muster K4152“. Das Spiel und die Person sind lesbar, der Kurzcode (aus der Ticketnummer) macht die Zuordnung auch bei Tippfehlern sicher. Mehrere Karten einer Person fuer ein Spiel = **eine** Zahlung mit einem Code. |
| E3 | Wie wird bezahlt? | PayPal wie bisher (E-K5). Die Mail nennt die PayPal-Adresse des Fanclubs und, falls vorhanden, einen **PayPal.me-Link mit Betrag**. Den PayPal.me-Namen traegst du in der `.env` ein (nicht im Repo). |
| E4 | Woher kommt die Adresse je Person? | **Vorschlag aus der Mitgliederliste, Bestaetigung durch dich einmal je Person**; danach merkt LUNA sich die Zuordnung (im Fanclub-Speicher auf der NAS, nicht im Git). Gaeste traegst du von Hand ein. Ohne bestaetigte Adresse kein Versand. |
| E5 | Ticketversand nach Zahlung automatisch? | **Ja, aber nur wenn alles eindeutig ist:** Verwendungszweck mit gueltigem Kurzcode **und** Betrag genau gleich **und** bestaetigte Adresse **und** PDF + Wallet-Link vorhanden **und** noch nicht gesendet. Sonst Vorschlag mit Knopf „Tickets senden“. Abschaltbar (`OFC_AUTO_TICKETVERSAND=0`); an erst nach der Abnahme von TV4. |
| E6 | Zahlungsbitte gesammelt oder je Spiel? | **Je Person und Spiel eine Mail** (passt zu einem Verwendungszweck). Knopf je Spiel „Zahlungsbitten an alle offenen senden“ mit Vorschau der Liste. |
| E7 | Kopie an dich? | **Ja:** Jede gesendete Mail liegt in „Gesendet“ von moin@, und das Versandprotokoll steht im Spiel (wer, wann, was; ohne Mailtext). |

## Etappen

### Etappe TV0: Analyse der HSV-Mails (nur lesend)

- Status: geplant
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

- Status: geplant
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

- Status: geplant
- Ziel / Scope:
  - Je Ticketname schlaegt LUNA die Adresse aus der Mitgliederliste vor (eindeutiger Namenstreffer).
  - Der CEO bestaetigt einmal je Person oder traegt die Adresse von Hand ein (Gaeste). Das wird als Ereignis `ofc_kontakt`
    im Fanclub-Speicher gemerkt; die Tabelle bleibt unveraendert.
  - Anzeige je Ticket: „✉️ anna@… bestaetigt“ / „Adresse fehlt“.
- Gate: Test-Gate mit Gegenproben (zwei gleiche Namen -> kein Vorschlag; ohne Bestaetigung kein Versand moeglich).
- Abhaengig von: nichts (parallel zu TV1). Aufwand: klein.

### Etappe TV3: Zahlungsbitte per Knopf (Senden ueber moin@)

- Status: geplant
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

### Etappe TV4: Zahlung zuordnen und Tickets senden

- Status: geplant
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
