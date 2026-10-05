---
name: beleg-gobd-pruefung
version: 1.0.0
beschreibung: Prueft Ausgangs- und Eingangsbelege auf Pflichtangaben (UStG, UStDV), Kleinunternehmer-Hinweis und GoBD-Konformitaet.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A2, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Beleg- und GoBD-Pruefung (CFO)

## Wann anwenden
Wenn LUNA einen Beleg (Rechnung, Gutschrift, Storno, Eingangsbeleg) oder einen Buchungsablauf in LUNA-OS pruefen laesst,
vor dem Festschreiben einer Rechnung, beim Monatsabschluss oder wenn der Steuerberater nachfragt.

## Grundlagen (Kurzfassung, Wortlaut in `quellen.md`)
- **UStDV § 34a**: Pflichtangaben der Kleinunternehmer-Rechnung -- Name/Anschrift beider Seiten, Steuernummer (oder
  USt-IdNr./Kleinunternehmer-IdNr.), Ausstellungsdatum, Menge/Art bzw. Umfang/Art der Leistung, Entgelt in einer Summe
  **mit Hinweis auf die Steuerbefreiung nach § 19 UStG**, bei Gutschrift die Angabe „Gutschrift“.
- **UStG § 14c**: wer Umsatzsteuer ausweist, schuldet sie -- als Kleinunternehmer **nie** Umsatzsteuer ausweisen.
- **UStG § 14**: Begriff der Rechnung, E-Rechnung; Kleinunternehmer duerfen nach § 34a Satz 3 UStDV immer eine
  „sonstige Rechnung“ (z. B. PDF) senden, muessen E-Rechnungen aber **empfangen** koennen.
- **AO § 146**: Buchungen vollstaendig, richtig, zeitgerecht, geordnet; Aenderungen nur so, dass der urspruengliche
  Inhalt feststellbar bleibt. **AO § 147**: Aufbewahrung -- Buecher/Abschluesse 10 Jahre, Buchungsbelege 8 Jahre,
  Handels-/Geschaeftsbriefe 6 Jahre.
- **GoBD** (BMF, Verweis): Unveraenderbarkeit, Nachvollziehbarkeit, Verfahrensdokumentation.

## Wie LUNA-OS das abbildet (zum Abgleich)
Hash-Kette `buchhaltung/log.jsonl` (jede Aenderung ist ein neues Ereignis), Festschreiben vergibt die Nummer,
Storno statt Loeschen, Korrektur verweist auf den Ursprungsbeleg, Belege als Datei in der Ablage,
Verfahrensdokumentation `docs/verfahrensdokumentation-buchhaltung.md`.

## Pruef-Checkliste
1. Alle Pflichtangaben nach § 34a UStDV vorhanden (inkl. fortlaufender Nummer und Leistungszeitraum/-datum).
2. § 19-Hinweis vorhanden, **kein** Steuerausweis, kein Steuersatz.
3. Summen stimmen (Positionen, Rabatte, Projektzeiten, Fahrtkosten), Faelligkeit plausibel.
4. Storno/Korrektur: verweist auf den Ursprungsbeleg, Ursprung bleibt erhalten.
5. Eingangsbeleg: Lieferant, Datum, Betrag, Zweck, Datei abgelegt, Kategorie/Konto plausibel.
6. Aufbewahrungsfrist und Ablageort klar.

## Ausgabe
Je Beleg: **Ampel** (gruen/gelb/rot), Befund, **Fundstelle** (Norm), konkrete Korrektur. Kopfzeile: „Entwurf -- der
Steuerberater zeichnet“. Quellen mit Stand nennen; nichts erfinden.

## Grenzen
Keine Buchung, kein Festschreiben, kein Versand -- nur Pruefung und Vorschlag. Steuerliche Endbeurteilung: Steuerberater.
