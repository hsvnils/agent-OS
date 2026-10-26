# Roadmap: Zahlungserinnerung vor der 1. Mahnung

- Status: in Umsetzung
- Stand: 2026-10-26
- Arbeitsbranch: `ai/z2-c3`
- Basiscommit: `30ccdb8`
- Naechster Schritt: Z1 live (Abnahme CEO offen); Z2 gebaut -- Merge/Deploy (CEO, Neustart luna-telegram), dann erste Vorschlaege per Telegram pruefen.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-26)

Vor den Mahnungen soll es moeglich sein, einen Beleg **„Zahlungserinnerung“** zu versenden -- freundlich, ohne Druck,
z. B.: „Moin zusammen, im taeglichen Stress gehen manchmal Dinge unter. Daher moechten wir euch gern an die Zahlung zu
unserer Rechnung XYZ erinnern.“

## Ist-Stand (Nachweis)

- Mahnwesen `orchestrator/core/mahnungen.py` (KUNDEN_FINANZEN Etappe 10): Stufen 1-3 (`STUFEN`, Zeile 43), Nummern
  `MA-JJJJ-NNNN`, je Mahnung Verzugszinsen + 40-EUR-Pauschale (Unternehmer) bzw. 2,50 EUR (Verbraucher), PDF als
  Geschaeftsbrief, Hash-Kette; Folgemahnungen schlaegt LUNA per Telegram vor (✅/❌), gesendet wird nur nach CEO-Tipp.
- Zu-erledigen-Liste `core/todos.py` Zeile 297: ueberfaellige Rechnung ohne Mahnung -> „Mahnstufe 1 erstellen oder
  Zahlung erfassen“.
- Mail-Vorlagen in `core/textbausteine.py` (Art `mahnung` mit Betreff/Text, im LUNA-OS bearbeitbar).
- Register: kein frueherer Eintrag zu „Zahlungserinnerung“.

## Entscheidungen fuer den CEO (Q0) -- **entschieden 2026-10-26: alle Empfehlungen angenommen**

1. **Eigener Beleg mit eigener Nummer?** Empfehlung: ja, `ZE-JJJJ-NNNN`, PDF als Geschaeftsbrief (6 Jahre), in der
   Hash-Kette und in der Belegverfolgung der Rechnung. Alternative: nur Mail ohne Beleg (dann fehlt der Nachweis).
2. **Inhalt:** Empfehlung: **keine** Zinsen, **keine** Pauschale, keine Mahnkosten -- nur offener Betrag, Rechnungsnummer,
   urspruengliche Faelligkeit, neue Zahlungsfrist, Bankverbindung, Rechnung als Anhang. Ton per Du/„Moin“ wie in der
   Kundenansprache (`anrede_moin`), Text als Textbaustein „zahlungserinnerung“ im LUNA-OS aenderbar.
   Hinweis (CLO, kein Rechtsrat): rechtlich ist auch eine freundliche Zahlungserinnerung bereits eine Mahnung im Sinne
   von § 286 BGB; das schadet nicht -- Verzugszinsen rechnet die 1. Mahnung ohnehin ab Faelligkeit.
3. **Frist:** Empfehlung 7 Tage (wie die Mahnstufen, `FRIST_TAGE`), beim Erstellen aenderbar.
4. **Ablauf / Vorschlag:** Empfehlung: Ist eine Rechnung **3 Tage** ueberfaellig und noch nichts verschickt, schlaegt
   LUNA per Telegram die Zahlungserinnerung vor (✅ Senden / ✏️ in LUNA-OS ansehen / ❌ Nicht senden). Laeuft deren Frist
   ab, schlaegt LUNA wie bisher die **1. Mahnung** vor. Versand **nie autonom** (Geld/Recht/Aussenwirkung, AGENTS.md 4).
   Die Zahlungserinnerung bleibt **optional**: der CEO kann weiter direkt die 1. Mahnung erstellen.
5. **Status-Bezeichnung in LUNA:** Empfehlung „Zahlungserinnerung“ (vor „Mahnstufe 1“) in Rechnungsliste, Belegverfolgung,
   Zu erledigen und CFO-Tagesmeldung.

## Etappe Z1: Beleg, PDF und Versand aus LUNA-OS

- Status: gebaut 2026-10-26 (als Stufe 0 im Mahnwesen: gleiche Ereignisse, Nummernkreis `ZE`, PDF/Mail ohne Zinsen/Kosten, Wortlaut nach CEO-Vorgabe, Rechnung als zweiter Anhang beim Versand aus LUNA; Knopf „💬 Zahlungserinnerung erstellen …“ in der Rechnungsansicht, Zu erledigen, Belegverfolgung, Nummern-Erkennung in Firmenakte/Mail-Antworten; 1. Mahnung nimmt Bezug auf die Erinnerung. Nebenwirkung: nach Ablauf der Erinnerungsfrist fragt LUNA per Telegram nach der 1. Mahnung (vorhandener Folgemahnungs-Weg, nur nach ✅). Einschraenkung: der Weg „Mail-Programm (.eml)“ haengt nur die Zahlungserinnerung an). Deploy und Abnahme offen
- Ziel / Scope / Nicht-Scope: Zahlungserinnerung in `MahnStore` als Stufe 0 bzw. eigene Art (Nummernkreis `ZE`),
  Ereignisse in der Hash-Kette (`zahlungserinnerung_erstellt/_versendet`), PDF hochkant (A4) im Belegstil, Mail-Vorlage
  als Textbaustein, Versand mit Vorschau nur nach CEO-Klick (Kundenversand wie bei Mahnungen, All-Inkl), Ablage in der
  Firmenakte; Knopf „Zahlungserinnerung“ in der Rechnungs-Detailansicht (V2, ganzseitig) vor „1. Mahnung“; Zu erledigen
  nennt zuerst die Zahlungserinnerung. Nicht-Scope: automatischer Versand, Gebuehren.
- Gate: Tests (Nummer, keine Zinsen/Pauschale, PDF-Inhalt, Ereignisse, Versand nur mit Bestaetigung, Belegverfolgung),
  Gegenprobe; Suite und Doku-Check gruen; Darstellung Desktop, iPad (820 px) und iPhone (402 px) geprueft.
- Verifikation: an einer Testrechnung in LUNA-OS Zahlungserinnerung erstellen -> erwartet: PDF mit Betrag, Frist, ohne
  Zinsen; Versandvorschau an die eigene Adresse; Mail kommt im eigenen Postfach an (Empfaenger-Pruefung).
- Dry-Run: Versandvorschau zeigt Empfaenger, Betreff, Text und Anhang, bevor etwas rausgeht.
- Risiko / Rueckweg: falscher Text/Betrag -> Vorschau verhindert Versand; Knopf per Schalter ausblendbar.
- Abhaengig von / Aufwand / Risiko: -- / mittel / niedrig.

## Etappe Z2: Vorschlag per Telegram und Uebergang zur 1. Mahnung

- Status: gebaut 2026-10-26 (`MahnStore.faellige_folgemahnungen(erinnerung=True)` liefert Rechnungen ab 3 Tagen ueberfaellig ohne Erinnerung/Mahnung/Mahnverfahren und nicht ausgesetzt; Bot fragt im vorhandenen Folgemahnungs-Lauf 08-20 Uhr **einmal je Rechnung** (Merker ohne Datum), eigener Telegram-Text ohne Zinsen; ✅ sendet ueber `folgemahnung_senden` mit Stufe 0 (Rechnung als 2. Anhang, Textbaustein), ❌ setzt aus; Schalter `ZAHLUNGSERINNERUNG_VORSCHLAG=0` in `orchestrator/.env` schaltet ab (Standard an); 1. Mahnung nach Fristablauf wie in Z1). Deploy offen
- Ziel / Scope / Nicht-Scope: im 15-min-Poll: Rechnung X Tage ueberfaellig, nichts verschickt -> Telegram-Vorschlag
  (✅/✏️/❌, einmal je Rechnung, 09-21 Uhr); ❌ setzt die Erinnerung fuer diese Rechnung aus; nach Ablauf der
  Erinnerungsfrist ohne Zahlung schlaegt LUNA die 1. Mahnung vor (vorhandener Weg). CFO-Tagesmeldung angepasst.
- Gate: Tests (Zeitpunkt, nur einmal, Aussetzen, Folgevorschlag Mahnung, Zahlung erfasst -> kein Vorschlag), Gegenprobe.
- Verifikation: Testrechnung mit Faelligkeit vor 3 Tagen -> erwartet: genau eine Telegram-Nachricht beim CEO; ✅
  verschickt die Erinnerung (Empfang im eigenen Postfach geprueft).
- Dry-Run: Vorschlagsliste ohne Versand anzeigen (`--dry-run` des Laufs).
- Risiko / Rueckweg: zu viele Vorschlaege -> Schalter `ZAHLUNGSERINNERUNG_VORSCHLAG=0`.
- Abhaengig von / Aufwand / Risiko: Z1 / klein / niedrig.

## Dokumentationspflicht

`projekt_changelog.md`, `docs/datenfluesse.md` (neue Ereignisse/Endpunkte), `docs/entscheidungs-register.md` (Q0),
`docs/verfahrensdokumentation-buchhaltung.md` (neuer Belegtyp), `KUNDEN_FINANZEN_ROADMAP.md` (Verweis).
