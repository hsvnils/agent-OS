# Roadmap: Kunden-Checkliste fuer Content-Konzept und Skripte

- Status: in Umsetzung
- Stand: 2026-10-26
- Arbeitsbranch: `ai/kunden-leitfaden`
- Basiscommit: `30ccdb8`
- Naechster Schritt: C2 gebaut -- Merge/Deploy (CEO), dann Abnahme in einem (Probe-)Gespraech auf Rechner, iPad und iPhone; C3 nach eigenem Go.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-26)

Eine **Checkliste mit Fragen, die wir mit Kunden klaeren muessen**, um daraus Content-Konzept und Skripte machen zu
koennen.

## Ist-Stand (Nachweis)

- Konzept-Mappe je Vorgang (`orchestrator/core/konzept.py`, KONZEPT_MAPPE_ROADMAP): Briefing-Felder Ziel, Zielgruppe,
  Kernbotschaft, Tonalitaet, Do's, Don'ts, Pflichtangaben, Freigaben durch, Notizen (Zeile 21); danach Ideen, Skript
  (Hook, Text, Einblendungen, Musik, CTA, Laenge), Szenen, Drehplan, Kunden-Freigabe; PDF-Export.
- Konzept-Vorlage (Blanko + Muster) als PDF/Word in `vorlagen/` (nur lokal, nicht im Git).
- Einwilligungen (Personen vor der Kamera) gibt es als eigenes Modul.
- Register: Konzept-Mappe 2026-10-05 beschlossen; keine Checkliste.

## Entwurf Fragenkatalog (zur Pruefung durch den CEO)

**A. Unternehmen & Angebot** -- Was macht ihr in einem Satz? Welches Produkt/Angebot steht im Mittelpunkt? Was
unterscheidet euch von anderen (USP)? Gibt es Aktionen, Termine oder Saisons, die wir treffen muessen?
**B. Ziel** -- Was soll der Content erreichen (Bekanntheit, Besucher, Anfragen, Verkauf, Bewerber)? Woran messen wir
Erfolg (Reichweite, Klicks, Reservierungen, Anfragen)? Gibt es ein konkretes Ziel bis wann?
**C. Zielgruppe** -- Wen wollt ihr erreichen (Alter, Ort, Interessen)? Wer sind eure besten Kunden heute? Was ist deren
groesstes Problem oder Wunsch?
**D. Kernbotschaft & Ton** -- Was soll man nach dem Video ueber euch denken? Wie sprecht ihr (du/Sie, locker/serioes,
Humor ja/nein)? Gibt es Woerter oder Themen, die tabu sind?
**E. Marke & Pflichtangaben** -- Logo, Farben, Schrift, Claim? Pflichtangaben (Impressum, Werbekennzeichnung,
Rechtliches, Preise, Allergene, Gewinnspielbedingungen)? Markennamen/Partner, die genannt oder nicht genannt werden
duerfen?
**F. Inhalte & Formate** -- Plattformen (Instagram, Facebook, TikTok, LinkedIn)? Formate (Reel, Story, Karussell,
Foto)? Wie viele Postings, in welchem Zeitraum? Beispiele, die euch gefallen (und welche nicht)? Gibt es vorhandenes
Material (Fotos, Videos, Texte)?
**G. Personen & Rechte** -- Wer darf/soll vor die Kamera? Sind Einwilligungen vorhanden (sonst ueber unser
Einwilligungs-Modul)? Gaeste/Mitarbeitende im Bild ok? Musik: eigene Rechte oder Plattform-Musik?
**H. Dreh & Organisation** -- Drehorte und Zeiten (Oeffnungszeiten, ruhige Phasen)? Ansprechpartner vor Ort?
Requisiten/Produkte, die bereitstehen muessen? Parken, Strom, Zugang?
**I. Freigabe & Zusammenarbeit** -- Wer gibt Skripte und Videos frei (Name, Kontakt)? Wie schnell kommt eine Freigabe
(Frist)? Ueber welchen Kanal (Mail, WhatsApp, Kundenordner-Link)? Wer postet (wir oder ihr), auf welchem Konto?
**J. Call to Action** -- Was soll der Zuschauer am Ende tun (folgen, reservieren, Link, anrufen, vorbeikommen)? Gibt es
einen Link, Rabattcode oder eine Aktion?

## Entscheidungen fuer den CEO (Q0) -- **entschieden 2026-10-26: alle Empfehlungen angenommen**

1. **Form:** Empfehlung **beides**: (a) Checkliste als Dokument (PDF hochkant + Word, nur mit Kopf wie die
   Konzept-Vorlage) zum Mitnehmen ins Kundengespraech oder zum Vorab-Schicken; (b) in LUNA-OS in der Konzept-Mappe
   abhakbar mit Antwortfeldern -- Antworten fuellen das Briefing (Ziel, Zielgruppe, Botschaft, Ton, Do's/Don'ts,
   Pflichtangaben, Freigabe) automatisch vor. Spaeter optional (c): Kunde fuellt online selbst aus (oeffentlicher
   Link wie Kundenordner-Freigabe -> eigene CISO-Pruefung, eigenes Go).
2. **Pflichtfragen:** Empfehlung: B, C, D, I und J sind Pflicht, bevor LUNA Ideen/Skripte vorschlaegt; LUNA zeigt
   „Briefing unvollstaendig: noch offen ...“.
3. **Skript-Hilfe:** Empfehlung: aus dem ausgefuellten Briefing schlaegt LUNA 3 Ideen und je ein Skript-Geruest (Hook,
   Text, CTA) vor -- nur als Entwurf in der Mappe (Modell: Claude, ohne Kundendaten ausser Briefing-Inhalten;
   Datenschutz-Check `docs/datenschutz-ki-nutzung.md` beachten).

## Etappe C1: Fragenkatalog als Dokument

- Status: Dokument erstellt 2026-10-26 (`scripts/kunden_checkliste_dokument.py` -> `vorlagen/Kunden-Checkliste.pdf` A4 hochkant, 4 Seiten, und `.docx`; Kopf wie Konzept-Vorlage, Kopffelder Kunde/Gespraechspartner/Datum/Projekt, Bloecke A-J mit Ankreuzkaestchen und zwei Antwortzeilen je Frage, ★ Pflicht bei B, C, D, I, J, Notizen). Download in LUNA-OS verschoben nach C2. **Abgenommen vom CEO 2026-10-26**
- Ziel / Scope / Nicht-Scope: Katalog (nach CEO-Pruefung) als `vorlagen/Kunden-Checkliste.pdf` (A4 hochkant) und
  `.docx`, nur Kopf; Ankreuzfelder und Platz fuer Antworten; zusaetzlich Download in LUNA-OS (Konzept-Mappe). Nicht-Scope:
  Online-Formular fuer Kunden.
- Gate: CEO-Abnahme des Dokuments (Inhalt und Look), PDF hochkant.
- Verifikation: PDF und Word oeffnen -> erwartet: alle Fragen, Kopf, keine Firmenzeile unten.
- Dry-Run: Entwurf als Datei an den CEO vor Ablage.
- Risiko / Rueckweg: reine Vorlage.
- Abhaengig von / Aufwand / Risiko: Q0 / klein / niedrig.

## Etappe C2: Gespraechsleitfaden am Kunden (neu zugeschnitten, CEO 2026-10-26)

CEO: „Die Checkliste soll man im System oeffnen und befuellen koennen, und daraus soll eine am Kunden speicherbare Datei
werden -- ein Gespraechsleitfaden, den man waehrend eines Telefonats/Meetings ausfuellt, um danach ein Konzept vorlegen zu
koennen.“

- Status: gebaut 2026-10-26 (`orchestrator/core/leitfaden.py` als einzige Fragenquelle fuer Dokument und Leitfaden; Kundenansicht „📋 Gespraechsleitfaden“ mit Liste, Start, Download leere Checkliste PDF/Word; ganzseitiger Leitfaden mit Kopf, Bloecken A-J, Haken + Antwort je Frage, Notizen, Speichern nach 0,7 s bzw. beim Verlassen eines Feldes, Fortschritt/Pflicht offen; Abschluss -> PDF in der Firmenakte als Fassung; Uebernahme ins Briefing mit Vorschau alt/neu und Feldauswahl; Tests mit Gegenproben). Deploy und Abnahme offen
- Ziel / Scope / Nicht-Scope:
  - **Ort:** am **Kunden** (Kundenansicht/Firmenakte, Knopf „📋 Gespraechsleitfaden“), auch **ohne** Angebot/Auftrag --
    gerade fuer das erste Gespraech. Mehrere Leitfaeden je Kunde moeglich (z. B. je Kampagne), jeweils mit Titel.
  - **Ausfuellen waehrend des Gespraechs:** ganzseitig auf Rechner, iPad und iPhone; Block fuer Block (A-J) mit
    Fortschritt, Ankreuzen je Frage, kurzes Antwortfeld, freies Notizfeld; **speichert laufend** (kein Datenverlust, wenn
    das Gespraech unterbrochen wird oder das Geraet wechselt); Pflichtbloecke markiert, „noch offen: ...“.
  - **Abschliessen:** erzeugt ein **PDF** im Look der Checkliste (Kopf, Fragen mit Antworten, Notizen, Datum, Gespraechs-
    partner) und legt es in der **Firmenakte** des Kunden ab (Art `leitfaden`); spaeteres Weiterbearbeiten erzeugt eine
    neue Fassung, alte bleiben erhalten.
  - **Weiter zum Konzept:** gibt es einen Vorgang (Angebot/Auftrag), uebernimmt ein Klick die passenden Antworten ins
    Briefing der Konzept-Mappe (Ziel, Zielgruppe, Botschaft, Ton, Do's/Don'ts, Pflichtangaben, Freigabe), mit Vorschau,
    welche Felder sich aendern.
  - Download der leeren Checkliste (PDF/Word) in LUNA-OS.
  - Nicht-Scope: Ausfuellen durch den Kunden selbst (oeffentlicher Link), Versand per Mail (geht ueber die Firmenakte
    bzw. spaeter), Modell-Vorschlaege (C3).
- Gate: Tests (Anlegen ohne Vorgang, laufendes Speichern, Abschluss -> PDF in der Firmenakte mit Fassung, Uebernahme ins
  Briefing nur mit Bestaetigung, Rechte), Gegenprobe; Darstellung Desktop, iPad (820 px) und iPhone (402 px) geprueft;
  Suite und Doku-Check gruen.
- Verifikation: an einem echten Kunden waehrend eines (Probe-)Telefonats ausfuellen -> erwartet: Antworten nach Neuladen
  noch da, PDF in der Firmenakte, Briefing vorbefuellt.
- Dry-Run: Uebernahme ins Briefing zeigt vorher die Aenderungen.
- Risiko / Rueckweg: Knopf per Schalter ausblendbar; Daten in der Hash-Kette (nichts geht verloren).
- Abhaengig von / Aufwand / Risiko: C1 / mittel bis gross / niedrig.

## Etappe C3: Ideen- und Skript-Vorschlaege aus dem Briefing (optional)

- Status: geplant
- Ziel / Scope / Nicht-Scope: Knopf „Ideen vorschlagen“ -> 3 Ideen + Skript-Geruest als Entwurf in der Mappe; nur
  Briefing-Inhalte ans Modell (keine Kontaktdaten), Kosten im Kostenlog. Nicht-Scope: Freigabe/Versand.
- Gate: Tests mit Modell-Attrappe (nur Briefing im Prompt, Entwurfsstatus), Kostenmessung je Vorschlag.
- Verifikation: echter Vorgang -> erwartet: 3 Ideen als Entwurf, Kosten < 0,05 EUR.
- Dry-Run: Prompt-Vorschau ohne Aufruf.
- Risiko / Rueckweg: Schalter aus.
- Abhaengig von / Aufwand / Risiko: C2 / mittel / niedrig.

## Dokumentationspflicht

`projekt_changelog.md`, `docs/datenfluesse.md` (neue Ereignisse/Endpunkte, C3: Modellaufruf),
`docs/entscheidungs-register.md` (Q0), `KONZEPT_MAPPE_ROADMAP.md` (Verweis).
