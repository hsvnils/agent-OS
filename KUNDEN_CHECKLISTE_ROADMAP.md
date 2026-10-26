# Roadmap: Kunden-Checkliste fuer Content-Konzept und Skripte

- Status: geplant
- Stand: 2026-10-26
- Arbeitsbranch: `ai/plan-checkliste-zahlungserinnerung` (Plan); Umsetzung auf eigenem Branch
- Basiscommit: `30ccdb8`
- Naechster Schritt: CEO prueft den Fragenkatalog (unten) und entscheidet Q0 (Form); danach Go fuer C1.
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

- Status: geplant
- Ziel / Scope / Nicht-Scope: Katalog (nach CEO-Pruefung) als `vorlagen/Kunden-Checkliste.pdf` (A4 hochkant) und
  `.docx`, nur Kopf; Ankreuzfelder und Platz fuer Antworten; zusaetzlich Download in LUNA-OS (Konzept-Mappe). Nicht-Scope:
  Online-Formular fuer Kunden.
- Gate: CEO-Abnahme des Dokuments (Inhalt und Look), PDF hochkant.
- Verifikation: PDF und Word oeffnen -> erwartet: alle Fragen, Kopf, keine Firmenzeile unten.
- Dry-Run: Entwurf als Datei an den CEO vor Ablage.
- Risiko / Rueckweg: reine Vorlage.
- Abhaengig von / Aufwand / Risiko: Q0 / klein / niedrig.

## Etappe C2: Checkliste in der Konzept-Mappe

- Status: geplant
- Ziel / Scope / Nicht-Scope: Bereich „Checkliste“ je Vorgang in LUNA-OS (V2, ganzseitig, Desktop/iPad/iPhone):
  Fragen abhaken, Antworten eintragen (Hash-Kette wie die Mappe), Uebernahme in die Briefing-Felder per Klick,
  Fortschritt „8 von 10 Bloecken“, Hinweis bei fehlenden Pflichtfragen; Checkliste im Konzept-PDF optional.
- Gate: Tests (Speichern, Uebernahme ins Briefing, Pflichtfragen, Rechte Modul), Gegenprobe; Darstellung Desktop, iPad
  (820 px), iPhone (402 px) geprueft; Suite und Doku-Check gruen.
- Verifikation: an einem echten Vorgang Checkliste ausfuellen -> erwartet: Briefing vorbefuellt, PDF zeigt die Antworten.
- Dry-Run: Uebernahme zeigt vorher, welche Briefing-Felder ueberschrieben wuerden.
- Risiko / Rueckweg: Bereich per Schalter ausblendbar; Briefing-Felder bleiben unveraendert, bis der CEO uebernimmt.
- Abhaengig von / Aufwand / Risiko: C1 / mittel / niedrig.

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
