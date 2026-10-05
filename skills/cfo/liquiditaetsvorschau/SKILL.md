---
name: liquiditaetsvorschau
version: 1.0.0
beschreibung: Liquiditaetsvorschau fuer die naechsten 4-12 Wochen aus offenen Rechnungen, Mahnstufen, Abos und geplanten Auftraegen.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A2, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Liquiditaetsvorschau (CFO)

## Wann anwenden
Wenn der CEO fragt „Wie viel Geld kommt rein/geht raus?“, vor groesseren Ausgaben, monatlich im Finanzcheck.

## Daten (liefert LUNA aus LUNA-OS)
Kontostand (falls genannt), offene Ausgangsrechnungen mit Faelligkeit und Mahnstufe, angenommene Angebote und
Auftragsbestaetigungen ohne Rechnung, Abos und wiederkehrende Kosten, bekannte Einmalausgaben, Monatsbudget
(`finance/budget.md`).

## Vorgehen
1. Zeitachse in Wochen (Standard 8 Wochen, auf Wunsch 4 oder 12).
2. **Einzahlungen** je Woche: offene Rechnungen zur Faelligkeit; Mahnfaelle mit Abschlag/Verzoegerung (konservativ
   in die Folgewochen schieben, Annahme nennen); Auftraege ohne Rechnung erst nach realistischem Rechnungsdatum.
3. **Auszahlungen** je Woche: Abos zum Abbuchungstag, bekannte Rechnungen, Ruecklage fuer Steuern (Einkommensteuer-
   Vorauszahlungen, wenn bekannt).
4. Drei Szenarien: **erwartet**, **vorsichtig** (Mahnfaelle zahlen nicht, Auftraege +2 Wochen), **gut**.
5. Tiefster Stand und Woche markieren; Warnung, wenn er unter eine vom CEO genannte Untergrenze faellt.

## Ausgabe
Wochentabelle (Woche · Ein · Aus · Saldo kumuliert) je Szenario, groesste Risiken (welcher Kunde, welche Rechnung),
konkrete Massnahmen (nachfassen, Mahnstufe, Ausgabe schieben) als **Entwurf**. Keine Zahlungen ausloesen (CEO-Tor Geld).
