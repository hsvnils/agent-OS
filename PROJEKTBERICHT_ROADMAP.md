# Roadmap: Social-Kennzahlen je Posting und Projektbericht zum Abschluss
- Status: geplant
- Stand: 2026-10-02
- Arbeitsbranch: `ai/plan-zeit-bericht` (Plan); Umsetzung je Etappe auf eigenem Branch
- Basiscommit: `6d66942`
- Naechster Schritt: CEO-Entscheidungen (Screenshot-Auslesen, Abschluss-Regel, Stunden im Bericht) und Go fuer Etappe P1
  abwarten.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-02)

„7 Tage nach Ausspielen eines Postings erinnert werden, die Social-Kennzahlen des jeweiligen Postings hochzuladen --
vielleicht per Screenshot an Lunas Telegram, pro Position (Bild-Postings, Reels usw.). Nach einem komplett
abgeschlossenen Projekt dem Kunden eine Auswertung inkl. Zahlen senden und auch die Stunden verdeutlichen. Ein Auftrag
waere erst dann wirklich abgeschlossen, wenn wir die Zusammenfassung erstellt und verschickt haben.“

## Analyse (read-only, 2026-10-02)

- Auftragspositionen tragen Menge, Einheit und oft eine Katalog-Herkunft (`katalog_id`, Formate wie Feed, Story,
  Reel mit **geplanten Kontakten und TKP**, KUNDEN_FINANZEN Etappe 16). Ein „Posting“ (einzelne Veroeffentlichung mit
  Datum und Link) gibt es nicht -- eine Position „2 x Reel“ sind zwei Postings mit eigenen Zahlen.
- Lieferungen (Etappe 30) halten Dateien und Links, aber kein Veroeffentlichungsdatum und keine Kennzahlen.
- Der Telegram-Bot nimmt **keine Fotos** an (kein Foto-Handler in `channels/telegram/bot.py`).
- Auslesen von Bildern: lokal ist `tesseract-ocr` (+deu) im NAS-Image vorhanden (Belege); das lokale Sprachmodell auf
  dem MACO470 liest nur Text. Gemini kann Bilder lesen, ist aber laut `docs/datenschutz-ki-nutzung.md` bisher nur fuer
  Chat/Bildschirm/Gegenlesen freigegeben -- Insights-Screenshots waeren ein neuer Datenfluss (CEO-Entscheidung).
- Meta-Postfach/API: vom CEO verworfen (Register 2026-09-29). **Etappe 3c** (Meta-Business-Suite-Exporte fuer
  Konto-Kennzahlen) ist geplant und ergaenzt diese Roadmap: Exporte = ganzes Konto; hier = je Kundenposting.
- Auftragsstatus heute: beauftragt -> geliefert -> (Rechnung). „Abgeschlossen“ gibt es noch nicht.

## Etappe P1: Postings je Position (veroeffentlicht am, Link, Format)

- Status: geplant
- Ziel / Scope: Je Auftragsposition so viele **Postings** wie die Menge (z. B. „Reel 1“, „Reel 2“), jeweils mit
  Format (aus dem Katalog: Feed-Bild, Karussell, Story, Reel), Plattform, **veroeffentlicht am**, Link und Bezug zur
  Lieferung. Erfassen im Auftrag („📣 Veroeffentlicht“) oder direkt beim Anlegen einer Lieferung mit Link.
- Gate: Tests (Postings aus Menge, Datum nicht in der Zukunft, Link-Pruefung); Browsertest Desktop + Mobil.
- Aufwand: klein bis mittel.

## Etappe P2: Kennzahlen-Erinnerung und Erfassung per Telegram-Screenshot

- Status: geplant
- Ziel / Scope:
  - **7 Tage nach „veroeffentlicht am“**: Telegram-Erinnerung je Posting („📊 Kennzahlen fuer Reel 2 · Kampagne Herbst
    (AB-2026-0003) faellig“) mit Knopf; dazu ein Punkt im Handlungsbedarf (Stufe „diese Woche“).
  - **Screenshot an LUNA**: Knopf antippen, dann Screenshot(s) schicken (mehrere je Posting moeglich, Insights haben
    oft 2-3 Seiten). LUNA legt die Bilder am Posting ab, liest die Zahlen aus und antwortet mit den erkannten Werten +
    Knoepfen „✅ Stimmt“ / „✏️ Korrigieren“ (fuehrt in das Formular in LUNA-OS). Ohne Antwort bleibt der Punkt offen.
  - **Felder je Format**: Reel -- Aufrufe, erreichte Konten, Likes, Kommentare, Geteilt, Gespeichert, Ø Wiedergabezeit;
    Feed/Karussell -- erreichte Konten, Impressionen, Likes, Kommentare, Geteilt, Gespeichert, Profilaufrufe; Story --
    Aufrufe/erreichte Konten, Antworten, Link-Klicks, Sticker-Taps, Weiter/Zurueck.
  - Formular in LUNA-OS je Posting (auch ohne Screenshot), Verlauf bei Korrekturen.
- Gate: Tests (Erinnerung genau am 7. Tag, eine je Posting, Zuordnung Foto -> Posting, Werte speichern/korrigieren,
  Handlungsbedarf verschwindet); OCR-Probe mit echten Insights-Screenshots des CEO (Trefferquote dokumentieren);
  Zustellung am Empfaenger pruefen (`typ: sent`); Browsertest Desktop + Mobil.
- Aufwand: mittel bis gross (Foto-Empfang im Bot ist neu).

## Etappe P3: Projektbericht und Status „abgeschlossen“

- Status: geplant
- Ziel / Scope:
  - **Bericht je Auftrag** (PDF im Hanserautisch-Layout): Kampagne, Zeitraum, Leistungen, je Posting Vorschau/Link +
    Kennzahlen, Summen (Gesamt-Reichweite, Interaktionen, Engagement-Rate), **Plan gegen Ist** (geplante Kontakte und
    TKP aus dem Angebot gegen tatsaechliche Reichweite -> **TKP-Ist**), optional **Stundenuebersicht** (aus
    PROJEKTZEITEN Z1, nur wenn angehakt), Fazit (LUNA schreibt einen Entwurf, du passt ihn an).
  - **Versand** wie beim Angebot: Vorschau -> Senden aus LUNAs Konto nur nach deinem Klick (Aussenkommunikation = CEO-Tor).
  - **Status „abgeschlossen“** = Bericht versendet. Handlungsbedarf fuehrt durch den Abschluss: „Kennzahlen fehlen (3
    von 5)“ -> „Bericht erstellen“ -> „Bericht senden“.
- Gate: Tests (Summen/TKP-Ist, Stunden nur mit Haken, Status erst nach Versand); PDF-Pruefung; Browsertest Desktop +
  Mobil; echter Versand nur nach CEO-Klick.
- Aufwand: mittel.

## Etappe P4 (eigene Vorschlaege): aus den Zahlen lernen

- Status: geplant (Vorschlag Claude Code)
- Ziel / Scope: Ist-Kennzahlen fliessen in die **Katalog-Kontakte** (zusammen mit Etappe 3c: Median statt Handwert)
  und in die **Firmenakte** (Kampagnen-Historie je Kunde); ein **zweiter Messpunkt nach 30 Tagen** (optional, fuer
  Reels mit langer Laufzeit); **14 Tage nach dem Bericht** Erinnerung „Folgeauftrag anfragen?“ (CRM) und auf Wunsch
  die Bitte um eine kurze Kundenstimme fuer Referenzen.
- Aufwand: klein bis mittel.

## Reihenfolge (zusammen mit PROJEKTZEITEN_ROADMAP)

Z1 -> P1 -> P2 -> Z2 -> P3 -> P4/Z3. Z1 zuerst, weil der Bericht die Stunden braucht; P1 vor P2, weil die Erinnerung
das Veroeffentlichungsdatum braucht.

## Offene CEO-Entscheidungen

1. Screenshots auslesen: **lokal** (Tesseract, alles bleibt im Haus, du bestaetigst die Werte) oder **Gemini** (liest
   Insights zuverlaessiger, neuer Datenfluss zu Google)? Empfehlung: lokal, Gemini nur als Ausweich nach Freigabe.
2. „Abgeschlossen“ allein durch den versendeten Bericht -- oder zusaetzlich erst, wenn die Rechnung bezahlt ist?
3. Stunden im Kundenbericht: je Bericht per Haken (Standard aus)?

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (Telegram-Fotos, Ablage, ggf.
Gemini), `docs/datenschutz-ki-nutzung.md` (falls Gemini), `docs/entscheidungs-register.md`, `docs/bekannte-fehler.md`.

## Definition of Done

P1-P3 verifiziert und vom CEO an einem echten Projekt abgenommen (Erinnerung, Screenshot, Bericht versendet,
Auftrag abgeschlossen), Desktop und Mobil; P4 nach eigenem Go.
