# Roadmap: Kontakte -- Visitenkarte per Telegram und Mail aus LUNA-OS

- Status: geplant
- Stand: 2026-11-19
- Arbeitsbranch: `ai/kontakte-roadmap`
- Basiscommit: `c0af13f`
- Naechster Schritt: CEO entscheidet E1-E4 (unten) und gibt das Go fuer Etappe K1.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Anlass (CEO 2026-11-19)

1. „Wenn ich per Telegram ein Foto einer Visitenkarte sende, soll Luna bitte die Firma und den Kontakt auch anlegen. Falls ich
   ein To-do dazu schreibe, soll auch das direkt dort angelegt werden und mit dem Kunden/Ansprechpartner verknuepft sein.“
2. „Im System einen Ansprechpartner anwaehlen und dort eine Mail schreiben -- dann geht die Mail per LUNA raus und die
   Antworten kommen da auch rein.“ Absender waehlbar: `luna@hanserautisch.de` **oder** `nils@hanserautisch.de`.

## Analyse (read-only, mit Belegen)

- **Fotos in Telegram:** Jedes Foto geht heute in den Kennzahlen-Ablauf der Postings (`orchestrator/channels/telegram/bot.py`
  Zeile 2849 -> `_po_foto`, Zeile 1042). Eine Bildunterschrift wird nicht gelesen; wartet kein Posting, antwortet LUNA
  „gerade wartet kein Posting auf Kennzahlen“. Eine Visitenkarte wuerde also heute abgewiesen.
- **Auslesen vorhanden:** OCR mit `tesseract` (deu+eng) im NAS-Image (`orchestrator/core/eingangsbelege.py` `_ocr_bild`,
  Zeile 202); Kennzahlen-Screenshots liest Claude Haiku (Bild geht an Anthropic, `docs/datenschutz-ki-nutzung.md` C3).
- **Anlegen vorhanden:** `firma_anlegen` (Vorschau -> CEO-Ja -> anlegen, Dubletten-Pruefung `KundenStore.finde`),
  `KundenStore.ansprechpartner_anlegen` (`orchestrator/core/kunden.py` Zeile 298), `todo_anlegen`.
- **To-do-Verknuepfung:** `AufgabenStore.anlegen` kennt `kunde`, aber **keinen Ansprechpartner**
  (`orchestrator/core/aufgaben.py` Zeile 182) -> Feld fehlt.
- **Mailversand vorhanden:** `governance/allinkl_mail.py` (SMTP/IMAP fuer **luna@hanserautisch.de**, Message-ID
  `<luna-…@hanserautisch.de>`, Kopie in „Gesendet“). Antworten erkennt `core/mail_antworten.py` -- aber **nur zu Belegen**
  (Angebot, AB, Rechnung, Mahnung); eine freie Mail an einen Ansprechpartner hat keinen Beleg und wuerde nicht zugeordnet.
- **nils@hanserautisch.de:** In der NAS-`.env` gibt es nur Zugangsdaten fuer das LUNA-Postfach (`ALLINKL_MAIL_USER`,
  `ALLINKL_MAIL_PASSWORT`, `ALLINKL_ABSENDER`; nur Namen geprueft). Fuer nils@ fehlen SMTP- und IMAP-Zugang. Antworten auf eine
  Mail von nils@ landen im Postfach von nils@ -- LUNA sieht sie nur mit Lesezugang dorthin.
- **Ansprechpartner in LUNA-OS:** Liste in der Firmen-Ansicht mit „Bearbeiten“ (`static/app-v2.js` Zeile 1230); keine
  Mail-Funktion.
- **Register:** keine Vorentscheidung zu Visitenkarten oder freiem Mailversand (`docs/entscheidungs-register.md` geprueft).
  Bekannt: BF-99 (Mail-Ablage, 2026-11-19 behoben) -- dieselbe Akte nimmt kuenftig auch die Antworten auf.

## Entscheidungen fuer den CEO (vor K1 bzw. K4)

| # | Frage | Empfehlung |
|---|---|---|
| E1 | Wer liest die Visitenkarte? (a) Claude Haiku (Bild geht an Anthropic, wie die Kennzahlen-Screenshots), (b) nur lokal `tesseract` + Regeln | **(a)** mit (b) als Rueckfall: Visitenkarten sind Geschaeftskontaktdaten, die die Person selbst uebergeben hat; Tesseract erkennt Namen und Firma oft schlecht. Nachtrag in `docs/datenschutz-ki-nutzung.md` |
| E2 | Woran erkennt LUNA, dass ein Foto eine Visitenkarte ist? | Wartet ein Posting auf einen Screenshot, bleibt alles wie heute. Sonst liest Haiku das Bild und unterscheidet Visitenkarte / Screenshot; bei Zweifel zwei Knoepfe |
| E3 | Foto der Visitenkarte aufheben? | Ja, in der Firmenakte (Art „Sonstiges“, Titel „Visitenkarte <Name>“) |
| E4 | Absender nils@hanserautisch.de: neuer Zugang (SMTP zum Senden, IMAP **nur lesend** fuer Antworten) | Ja, aber eigene Etappe K5 mit **CISO-Freigabe**; Zugangsdaten traegt der CEO selbst in die `.env` ein. LUNA liest dort nur Mails, die eine Antwort auf eine von LUNA versendete Mail sind (Message-ID), nichts anderes |

## Scope

- Visitenkarte per Telegram -> Vorschau -> nach CEO-Knopf Firma + Ansprechpartner (oder Ansprechpartner an bestehender Firma).
- Bildunterschrift mit Aufgabe -> To-do mit Firma **und** Ansprechpartner verknuepft.
- Mail aus LUNA-OS am Ansprechpartner, Absender waehlbar (luna@ ab K4, nils@ ab K5), Kopie in die Akte, Antworten in die Akte
  mit Telegram-Meldung.

## Nicht-Scope

- `.env`-Dateien und Zugaenge: traegt der CEO ein (K5); kein Zugang ohne CISO-Freigabe.
- Telegram-Bot: kein zusaetzlicher Poller; Neustarts macht der CEO.
- Serienmails/Newsletter, automatische Mails ohne Klick des CEO, Mails von LUNA im Namen des CEO ohne Senden-Knopf.
- Gmail-Konto von LUNA (bleibt fuer Weiterleitungen/Belege), Instagram/Meta.
- Loeschen oder Umhaengen bestehender Akten-Eintraege.

## Etappen

### Etappe K1: Visitenkarte lesen und anlegen (Telegram)

- Status: geplant
- Ziel / Scope / Nicht-Scope: Foto ohne wartendes Posting -> Visitenkarte erkennen (E2) -> Felder auslesen (Firma, Vorname,
  Nachname, Rolle, Mail, Telefon, Website, Ort) -> Vorschau in Telegram mit Knoepfen „✅ Anlegen“, „✏️ In LUNA-OS
  aendern“, „❌ Verwerfen“. Gibt es die Firma schon (Domain/Name, `KundenStore.finde`), wird nur der Ansprechpartner
  angelegt; gibt es den Ansprechpartner schon (gleiche Mail), nichts doppelt. Foto in die Akte (E3). Nicht-Scope: To-do (K2).
- Gate: Tests mit drei Beispielkarten (neue Firma, bekannte Firma, bekannter Kontakt) + Gegenproben (kein Anlegen ohne Knopf,
  Kennzahlen-Screenshot bei wartendem Posting laeuft weiter wie bisher); Suite gruen, Doku-Check ok.
- Verifikation: CEO schickt eine echte Visitenkarte -> `GET /api/crm/kunden?suche=<Firma>` -> erwartet: genau eine Firma mit
  einem Ansprechpartner, Akte enthaelt „Visitenkarte <Name>“.
- Dry-Run: Vorschau in Telegram ist der Dry-Run; geschrieben wird erst nach „✅ Anlegen“.
- Risiko / Rueckweg: falsch gelesene Felder -> Vorschau zeigt alles vor dem Anlegen; Schalter `VISITENKARTE=0` schaltet den Weg
  ab (Fotos gehen dann wieder nur an die Postings).
- Abhaengig von / Aufwand / Risiko: E1-E3 / mittel / gering.

### Etappe K2: To-do aus der Bildunterschrift, verknuepft

- Status: geplant
- Ziel / Scope / Nicht-Scope: Bildunterschrift („Nachfassen in 7 Tagen“, „Angebot bis Freitag“) wird nach dem Anlegen als
  To-do angelegt -- mit `kunde` = Firma und neuem Feld `ansprechpartner` (AP-Nummer). LUNA-OS zeigt den Ansprechpartner am
  To-do und die offenen To-dos am Ansprechpartner. Gilt auch fuer `todo_anlegen` im Chat (optional Ansprechpartner).
- Gate: Tests (Faelligkeit „in 7 Tagen“, Verknuepfung beidseitig sichtbar; Gegenprobe: ohne Bildunterschrift kein To-do);
  Sichtpruefung Rechner/iPad 820 px/iPhone 402 px headless.
- Verifikation: echte Karte mit Bildunterschrift -> `GET /api/aufgaben` -> erwartet: To-do mit `kunde` und `ansprechpartner`
  der neuen Firma, Erinnerung am Faelligkeitstag in Telegram.
- Dry-Run: To-do erscheint in der Vorschau aus K1 und wird mit demselben Knopf angelegt.
- Risiko / Rueckweg: neues Feld ist optional (alte To-dos unveraendert).
- Abhaengig von / Aufwand / Risiko: K1 / klein / gering.

### Etappe K3: Antworten auf freie Mails erkennen (Grundlage fuer K4)

- Status: geplant
- Ziel / Scope / Nicht-Scope: `core/mail_antworten.py` ordnet Antworten nicht nur Belegen, sondern auch freien Mails an
  Ansprechpartner zu (Message-ID der versendeten Mail -> Firma/Ansprechpartner) und legt sie in die Firmenakte; Telegram-
  Meldung „Antwort von <Name> (<Firma>)“. Nicht-Scope: Versand (K4).
- Gate: Tests mit Antwort per `In-Reply-To` und per `References`; Gegenprobe: fremde Mail ohne Bezug bleibt unberuehrt.
- Verifikation: siehe K4 (echte Antwort).
- Dry-Run: Testlauf gegen das Postfach im Lesemodus -> Liste, was zugeordnet wuerde.
- Risiko / Rueckweg: Postfach wird weiterhin nur gelesen.
- Abhaengig von / Aufwand / Risiko: -- / klein / gering.

### Etappe K4: Mail schreiben am Ansprechpartner (Absender luna@)

- Status: geplant
- Ziel / Scope / Nicht-Scope: In LUNA-OS am Ansprechpartner (und in der Firmen-Ansicht) Knopf „✉️ Mail schreiben“: Betreff,
  Text, optional Anhang aus der Akte, Absender-Auswahl (vorerst nur luna@, nils@ ausgegraut bis K5). Versand erst nach
  „Senden“ des CEO (Oeffentlichkeit = CEO-Tor, der Klick ist die Freigabe); LUNA formuliert auf Wunsch einen Entwurf, sendet
  aber nie selbst. Kopie (.eml + PDF-Ansicht) in die Firmenakte, Verlauf am Ansprechpartner.
- Gate: Tests (Versand mit Fake-SMTP, Akte, Kennung); Sichtpruefung Rechner/iPad/iPhone; Testmail an den CEO selbst.
- Verifikation: Testmail an eine Adresse des CEO -> kommt an (Empfaenger prueft), Antwort darauf -> erscheint in der Akte und
  in Telegram (Wirkung beim Empfaenger, nicht nur „gesendet“).
- Dry-Run: Vorschau der fertigen Mail (Absender, Empfaenger, Betreff) vor dem Senden.
- Risiko / Rueckweg: Fehlversand -> nur mit Senden-Knopf, Empfaenger aus den Stammdaten; Schalter `KONTAKT_MAIL=0` blendet
  den Knopf aus.
- Abhaengig von / Aufwand / Risiko: K3 / mittel / mittel (Aussenwirkung).

### Etappe K5: Absender nils@hanserautisch.de

- Status: geplant
- Ziel / Scope / Nicht-Scope: zweiter Zugang (SMTP senden, IMAP **nur lesend**) fuer nils@; Absender-Auswahl in K4 wird
  freigeschaltet. LUNA liest im Postfach von nils@ **nur** Antworten auf von LUNA versendete Mails (Message-ID-Treffer),
  nichts sonst; Kopie der gesendeten Mail in „Gesendet“ von nils@, damit der CEO sie im eigenen Programm sieht.
  Nicht-Scope: alles Weitere im Postfach von nils@.
- Gate: **CISO-Freigabe** (neuer Zugang, AGENTS.md 5.7) + CEO traegt `NILS_MAIL_USER`/`NILS_MAIL_PASSWORT` selbst in die
  NAS-`.env` ein; Tests mit Gegenprobe (andere Mails im Postfach bleiben ungelesen); Testmail + Antwort wie K4.
- Verifikation: Testmail von nils@ -> beim Empfaenger Absender nils@, in „Gesendet“ von nils@ sichtbar; Antwort -> Akte +
  Telegram; `docs/datenfluesse.md` ergaenzt.
- Dry-Run: Verbindungspruefung ohne Versand (`verbindung_pruefen`, wie bei luna@).
- Risiko / Rueckweg: Zugang eng begrenzt; Entfernen der zwei `.env`-Zeilen schaltet nils@ ab.
- Abhaengig von / Aufwand / Risiko: K4, E4 / klein / mittel (Zugang).

## Dokumentationspflichten

`projekt_changelog.md`, Etappen-Status hier, `ROADMAP.md`, `docs/entscheidungs-register.md` (E1-E4),
`docs/datenfluesse.md` (Haiku-Bild bei K1, IMAP/SMTP nils@ bei K5), `docs/datenschutz-ki-nutzung.md` (K1),
`docs/bekannte-fehler.md` (Funde), Testbaseline.

## Definition of Done

Der CEO hat eine echte Visitenkarte (mit To-do) angelegt und eine echte Mail aus LUNA-OS mit beiden Absendern verschickt, und
die Antworten sind in der Akte angekommen. Danach Sichtabnahme; der CEO nimmt ab, Claude traegt „abgeschlossen“ ein.
