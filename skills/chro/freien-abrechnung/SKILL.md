---
name: freien-abrechnung
version: 1.0.0
beschreibung: Prueft Rechnungen freier Mitarbeitender gegen Vereinbarung und Projektzeiten und ordnet die Kosten dem Auftrag zu.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Freien-Abrechnung (CHRO, mit dem CFO)

## Wann anwenden
Wenn eine Rechnung einer freien Person eingeht oder ein Auftrag nachkalkuliert wird.

## Checkliste
1. Rechnung gegen Vereinbarung: Satz, Tage/Stunden, Fahrtkosten, Zusatzleistungen.
2. Leistung erbracht und geliefert (Rohdaten/Schnitt angekommen, Freigabe)?
3. Pflichtangaben der Rechnung (CFO-Skill `beleg-gobd-pruefung`); Umsatzsteuer nur, wenn die Person sie ausweisen darf
   -- als Kleinunternehmer kann Hanserautisch sie **nicht** als Vorsteuer abziehen (Kosten = Brutto).
4. Zuordnung zum Auftrag (Eingangsbeleg mit Auftragsnummer) fuer die Nachkalkulation.
5. Zahlungsziel und Zahlung (CEO-Tor Geld).

## Ausgabe
Pruefergebnis (ok/Abweichung mit Betrag), Buchungsvorschlag (Kategorie, Auftrag), Rueckfragen an die Person als
Entwurf. Keine Zahlung ausloesen.
