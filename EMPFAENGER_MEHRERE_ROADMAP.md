# Roadmap: Mehrere Empfaenger beim Versand von Belegen

- Status: in Umsetzung
- Stand: 2026-10-13
- Arbeitsbranch: `ai/mehrere-empfaenger`
- Basiscommit: `6a6a87e`
- Naechster Schritt: Deploy, dann Abnahme durch den CEO (eine echte Mail mit CC/BCC an eigene Adressen) und Roadmap abschliessen.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-13)

„Beim Versenden von Belegen aus dem System: Kann ich mehrere Mailadressen des Kunden angeben und auch manuell eine
eintragen? Falls nicht, muessen wir das einrichten.“

## Analyse (read-only, 2026-10-13)

- Acht Versanddialoge haben je **ein** Feld „An“ (`app-v2.js`): Angebot (`as-an`), Auftragsbestaetigung (`abs-an`),
  Rechnung (`res-an`), Mahnung (`mas-an`), Projektbericht (`ber-an`), Konzept (`kzs-an`), Einwilligungs-Kopie
  (`ews-an`), Vorstellungs-Mail (`vs-an`). Vorbelegt ist **eine** Adresse (Ansprechpartner bzw. Rechnungs-Mail);
  ueberschreiben (= manuell eintragen) geht schon.
- Server: die Senden-Endpunkte pruefen nur „enthaelt ein @“ (`channels/web/app.py`); Versand ueber All-Inkl
  (`governance/allinkl_mail.py` `nachricht`: `To` = der Text) bzw. Gmail. Mehrere Adressen mit Komma wuerden technisch
  vermutlich rausgehen, sind aber **weder geprueft noch vorgesehen** (keine Pruefung je Adresse, kein CC, in der Kette als
  ein Text).
- Antworten erkennt LUNA ueber die Kennung der Mail (Message-ID), nicht ueber die Empfaengeradresse -> mehrere Empfaenger
  stoeren die Antwort-Erkennung nicht.

## Etappe M1: Empfaenger-Baustein fuer Angebot, Auftrag, Rechnung, Mahnung

- Status: umgesetzt
- Ziel / Scope: Ein gemeinsamer Baustein statt des einzelnen Felds:
  - **Vorschlaege zum Anhaken:** alle Mailadressen der Firma (Ansprechpartner mit Mail + Rechnungs-Mail), die bisherige
    Vorbelegung ist angehakt.
  - **Weitere Adressen von Hand:** Eingabefeld, mehrere mit Komma oder Enter, jede als entfernbarer Chip.
  - **CC (optional, Empfehlung):** z. B. die Buchhaltung des Kunden in Kopie.
  - Pruefung je Adresse (gueltig, keine Doppelten, hoechstens 10), Fehler zeigt die falsche Adresse.
  - Server: `an` als Liste (alter Text-Wert bleibt erlaubt), Versand mit allen Empfaengern in `To`/`Cc`; in der Kette die
    Liste; Anzeige im Verlauf „gesendet an a@…, b@… (CC c@…)“.
- Nicht-Scope: BCC, Adressbuch ausserhalb der Firma, Massenversand.
- Gate: Tests (mehrere An/CC, ungueltige Adresse, Doppelte, alte Einzel-Adresse weiter gueltig, All-Inkl-Nachricht hat
  To/Cc, Gegenprobe rot); Browser Rechner/iPad/iPhone.
- Aufwand: mittel.

## Etappe M2: Uebrige Versanddialoge

- Status: umgesetzt
- Ziel / Scope: derselbe Baustein fuer Projektbericht, Konzept, Einwilligungs-Kopie (Vorschlag = Mail der Person) und
  Vorstellungs-Mail (Vorschlaege nur bei vorhandener Firma); „Im Mail-Programm oeffnen“ uebernimmt alle Adressen.
- Gate: wie M1.
- Aufwand: klein bis mittel.

## Umsetzung (2026-10-13, Go CEO fuer M1 und M2, zusaetzlich BCC)

- `core/empfaenger.py`: `pruefen` (je Adresse, Doppelte raus, An vor CC vor BCC, hoechstens 10, mindestens ein An, auch
  „Name <a@b.de>“), `anzeige`/`zerlegen` (ein Text „a, b · CC: c · BCC: d“ fuer Kette und Verlauf), `aus_body`, `kopf`
  (To/Cc/Bcc fuer den Versandweg; einzelne alte Adressen bleiben unveraendert), `vorschlaege` (Ansprechpartner + Rechnungs-Mail).
- Versand: All-Inkl setzt To/Cc, BCC nur im SMTP-Umschlag (nie im Kopf, auch nicht in der Kopie in „Gesendet“ und der .eml in
  der Firmenakte); Gmail mit Bcc-Kopf (Gmail entfernt ihn beim Zustellen); .eml fuers eigene Mail-Programm mit To/Cc/Bcc.
- Alle Senden-Endpunkte (Angebot inkl. Gmail-Entwurf, Auftrag, Rechnung, Mahnung, Projektbericht, Konzept, Einwilligungs-Kopie,
  Vorstellungs-Mail, Mail-Programm) pruefen ueber `_an()`; Testmail an den CEO bleibt eine Adresse. Alle acht Vorschauen
  liefern `adressen`.
- Oberflaeche: Baustein `empfBaustein` in allen acht Dialogen -- Adressen der Firma anhaken, weitere von Hand (Komma),
  „+ CC / BCC“, Hinweis auf ungueltige Adressen; „📋 Adresse kopieren“ kopiert die An-Adressen und nennt CC/BCC.
- Tests `test_empfaenger.py` (4, Gegenproben rot); Browser Rechner/iPad/iPhone.

## Nicht-Scope

Keine automatische Versendung (Senden bleibt Klick + Bestaetigung), keine Aenderung an Belegen oder der Antwort-Erkennung.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (Versand-Ereignisse mit Empfaengerliste).

## Definition of Done

In jedem Versanddialog lassen sich mehrere Adressen der Firma anhaken, weitere von Hand eintragen und optional Kopien (CC)
setzen; alle Empfaenger erhalten die Mail, und der Verlauf zeigt, an wen sie ging.
