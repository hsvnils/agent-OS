# Roadmap: Textbausteine und Versand ueber das eigene Mail-Programm
- Status: abgeschlossen
- Stand: 2026-10-05
- Arbeitsbranch: `ai/erneut-senden`
- Basiscommit: `ed7fdcc`
- Naechster Schritt: keiner -- T1-T3 und T5 live; T4 (Geraete-Abnahme Mail-Programm) vom CEO gestrichen, weil der Versand aus LUNA-OS reicht (2026-10-05).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Textbausteine fuer Angebote und andere Belegarten. Ich will ausserdem an den Belegen einen Button, den ich druecken kann,
der dann eine Mail in Outlook oeffnet, mit dem Beleg als angehaengte PDF und die ausgewaehlte Textvorlage in der Mail als
Text und meine Signatur drunter.“

Entscheidungen des CEO (2026-10-05):
- Geraete: **iPhone = Apple Mail**, **MacBook = Apple Mail**, **MACO470 (Windows) = Outlook**.
- Belegarten: **Angebot, Auftragsbestaetigung, Rechnung (inkl. Vorkasse), Mahnung, Projektbericht, Konzept**.
- Signatur: **in LUNA-OS hinterlegt** (Text vom CEO genannt; liegt wegen Telefonnummer nur auf der NAS, nie im Git).
- Vorlagen gelten **ueberall** -- auch fuer den bisherigen Gmail-Versand („Senden …“), eine Quelle der Wahrheit.

## Analyse (read-only, 2026-10-05)

- Heute hat jede Belegart einen **fest eingebauten** Mailtext: `angebote.mail_text`, `beauftragung.auftrag_mail_text`,
  `rechnungen.rechnung_mail_text`, `mahnungen.mahnung_mail_text`, `projektbericht.mail_text`, `konzept.mail_text`.
  Versand ueber Gmail: Versandvorschau (`GET …/versandvorschau`) -> CEO passt Text an -> `POST …/senden` (PDF als Anhang,
  Ablage in der Firmenakte, Status „versendet“). Eine Signatur gibt es nirgends.
- **Technische Grenze:** Ein normaler Mail-Link (`mailto:`) kann **keine Anhaenge** mitgeben. Deshalb je Geraet ein Weg:
  - **iPhone/MacBook (Safari, Apple Mail):** Teilen-Menue des Browsers (Web Share mit Datei): PDF + Text gehen an Apple Mail
    als neue Mail. Grenze: Das Teilen-Menue kann **keinen Empfaenger** vorbelegen -> LUNA zeigt/kopiert die Adresse.
  - **MACO470 (Outlook):** LUNA erzeugt einen **Mail-Entwurf als .eml-Datei** (Empfaenger, Betreff, Text mit Signatur, PDF
    angehaengt, Kennung „ungesendet“); Outlook oeffnet ihn als neue Mail. Ob das „neue Outlook“ die Kennung beachtet, ist
    zu testen (T4); Rueckfall: Outlook im Browser bzw. Teilen-Menue von Windows.
- Ob eine Mail aus dem eigenen Programm wirklich verschickt wurde, sieht LUNA nicht -> danach Knopf „Als versendet
  markieren“ (gleiche Wirkung wie heute: Status, PDF-Ablage in der Firmenakte, Erinnerungen).

## Etappe T1: Textbausteine und Signatur

- Status: umgesetzt (2026-10-05) -- `core/textbausteine.py` (7 Vorlagen-Arten inkl. Stornorechnung, Platzhalter je Art,
  Pruefung, genau ein Standard, `buchhaltung/textbausteine.json`, Ereignis `textbausteine_geaendert`), Editor unter
  Einstellungen mit Platzhalter-Chips und Vorschau mit Beispielwerten; Standard = bisheriger Text (180 Faelle mit dem
  alten Code verglichen, identisch).
- Ziel / Scope: Vorlagen je Belegart (mehrere moeglich, eine als Standard), je Vorlage Name, Betreff und Text mit
  **Platzhaltern** (z. B. {anrede}, {vorname}, {firma}, {nummer}, {titel}, {betrag}, {gueltig_bis}, {faellig},
  {zahlungsziel}, {praesentation}, {mahnstufe}, {frist}); Standardvorlagen = die heutigen Texte (nichts aendert sich, bis
  der CEO etwas anpasst). Signatur einmal hinterlegt, wird automatisch unter jeden Text gesetzt. Ablage nur auf der NAS
  (`buchhaltung/`, wie Firmendaten), Aenderungen nachvollziehbar protokolliert. Editor in LUNA-OS unter **Einstellungen**
  („Textbausteine & Signatur“, CEO 2026-10-05) mit Vorschau an einem echten Beleg. **Wirkung:** Der Mailtext entsteht erst
  beim Versand aus der aktuellen Vorlage -- eine Aenderung gilt fuer jede Mail ab dann (auch fuer bestehende, noch nicht
  versendete Belege); bereits versendete Mails bleiben unveraendert in der Firmenakte. Vor jedem Versand ist der Text fuer
  diese eine Mail anpassbar, ohne die Vorlage zu aendern.
- Gate: Tests (Platzhalter, unbekannte Platzhalter abgelehnt, Standard = heutiger Text, Signatur angehaengt, nichts im
  Git); Browsertest Rechner/iPad/iPhone 17 Pro.
- Aufwand: mittel.

## Etappe T2: Vorlagen im Gmail-Versand

- Status: umgesetzt (2026-10-05) -- alle 6 Versandvorschauen mit `?vorlage=` und Auswahl im Dialog; Signatur ersetzt den
  frueheren Gruss; Folgemahnung per Telegram nutzt Standardvorlage + Signatur.
- Ziel / Scope: In jedem Versanddialog (6 Belegarten) Auswahl der Vorlage; Text bleibt vor dem Senden aenderbar; Signatur
  automatisch darunter. Bisherige Wirkung (PDF-Anhang, Firmenakte, Status) unveraendert.
- Gate: Tests je Belegart; Gegenprobe ohne Vorlagen = heutiger Text.
- Aufwand: klein bis mittel.

## Etappe T3: Knopf „✉️ Im Mail-Programm oeffnen“

- Status: umgesetzt (2026-10-05) -- Block in allen 6 Versanddialogen: Apple-Geraete Teilen-Menue (PDF vorab geladen,
  Teilen startet direkt im Tipp), sonst .eml-Entwurf (X-Unsent) fuer Outlook; „📋 Adresse kopieren“; „✓ Als versendet
  markieren“ ueber den bestehenden Senden-Ablauf mit `kanal: mail-programm` (kein Gmail, Kanal im Protokoll).
- Ziel / Scope: Knopf an allen 6 Belegarten (Detail/Beleg): Vorlage waehlen -> LUNA baut Betreff, Text + Signatur und PDF ->
  **iPhone/Mac:** Teilen-Menue mit PDF und Text (Adresse wird angezeigt und, wo moeglich, kopiert); **Windows:** .eml-Entwurf
  fuer Outlook (mit Empfaenger). Danach „✓ Als versendet markieren“ (Status, Firmenakte, Erinnerungen wie beim Gmail-Weg).
  Kein Versand durch LUNA; es entsteht kein neuer externer Dienst.
- Gate: Tests (.eml-Aufbau: Kopf „ungesendet“, Empfaenger, Betreff, Text, PDF-Anhang; Endpunkte je Belegart; Markieren
  wirkt wie Gmail-Versand); Browsertest der Knoepfe auf Rechner/iPad/iPhone 17 Pro.
- Aufwand: mittel.

## Etappe T4: Geraete-Abnahme mit dem CEO

- Status: verworfen (CEO 2026-10-05: „Aus dem LUNA-OS versenden reicht. Das ist ein guter Weg“ -- Kundenmails gehen ueber
  luna@hanserautisch.de aus LUNA-OS; der Knopf „Im Mail-Programm oeffnen“ bleibt als ungepruefte Ausweichmoeglichkeit)
- Ziel / Scope: echter Test auf **iPhone (Apple Mail)**, **MacBook (Apple Mail)** und **MACO470 (Outlook)**: Mail oeffnet
  sich mit Anhang, Text und Signatur. Was ein Geraet nicht kann (z. B. Empfaenger im Teilen-Menue), wird dokumentiert;
  falls Outlook die .eml nicht als Entwurf oeffnet, Rueckfall-Weg festlegen.
- Gate: CEO bestaetigt je Geraet; Befunde in `docs/bekannte-fehler.md`.
- Aufwand: klein.

## Etappe T5: Erneut senden / nachfassen, Versand ohne Google

- Status: umgesetzt (2026-10-05) -- CEO-Frage „Kann es sein, dass die Senden-Buttons verschwinden, sobald ein Beleg mal
  versendet wurde?“ (ja: bei Angebot und Mahnung). Neu: versendete Angebote („✉️ Erneut senden / nachfassen …“) und
  Mahnungen („✉️ Erneut senden …“) gehen mit dem **eingefrorenen PDF** erneut raus -- ueber Gmail oder das eigene
  Mail-Programm, mit waehlbarer Vorlage; Status, Stufe, Frist und Erinnerungen bleiben, die Mail steht im Verlauf
  (Ereignisse `angebot_erneut_gesendet`, `mahnung_erneut_gesendet`). „Senden …“ ist ohne Google-Verbindung nicht mehr
  gesperrt -- gesperrt ist nur „Jetzt senden“ (Gmail), der Mail-Programm-Weg geht immer.
- Gate: Tests (erneut nur nach Versand, normales Senden nicht doppelt, gleiches PDF, keine neuen Erinnerungen,
  Gegenprobe rot); Browsertest Rechner/iPad/iPhone 17 Pro.

## Nicht-Scope

Kein automatischer Versand aus dem eigenen Mail-Programm; keine Anbindung an das Microsoft- oder Apple-Konto (waere ein
neuer Zugang = CEO-Tor); keine HTML-Signatur mit Logos in T1 (reiner Text, Erweiterung spaeter moeglich).

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (neue NAS-Datei, .eml-Download),
`docs/entscheidungs-register.md`, `docs/bekannte-fehler.md` (T4).

## Definition of Done

Alle 6 Belegarten haben waehlbare Textvorlagen mit Signatur -- im Gmail-Versand und ueber den Knopf im eigenen
Mail-Programm (Apple Mail auf iPhone/Mac, Outlook auf dem MACO470), vom CEO auf allen drei Geraeten bestaetigt.
