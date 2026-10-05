---
name: kampagnen-auswertung
version: 1.0.0
beschreibung: Wertet Kundenkampagnen aus (Reichweite, Impressionen, Engagement, TKP) und vergleicht sie mit Zielen und frueheren Kampagnen.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A2, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Kampagnen-Auswertung (CDO)

## Wann anwenden
Fuer den Projektbericht an den Kunden, fuer die Nachkalkulation des CFO und fuer die Folgeauftrag-Planung des CRO.

## Daten (von LUNA)
Ist-Kennzahlen je Posting (Reichweite, Impressionen, Aufrufe, Likes, Kommentare, Shares, Saves, Profilbesuche,
Link-Klicks; aus Insights-Screenshots oder manueller Eingabe), Zeitpunkt der Erhebung, Preis des Auftrags,
Ziele aus Briefing/Angebot.

## Kennzahlen (Definitionen festhalten)
- **Engagement-Rate** = Interaktionen / Reichweite (bei fehlender Reichweite: / Impressionen, kennzeichnen).
- **TKP** = Preis / Impressionen x 1.000 (gesamt und je Posting).
- **Kosten je Interaktion** = Preis / Interaktionen.
- Messzeitpunkt angeben (z. B. 7 Tage nach Posting); Kennzahlen nur vergleichen, wenn der Zeitpunkt passt.

## Vorgehen
1. Datenqualitaet pruefen (Skill `datenqualitaet-pruefen`): fehlende Werte, Ausreisser, Erhebungszeitpunkt.
2. Kennzahlen je Posting und gesamt berechnen.
3. Vergleich: Ziel vs. Ist, frueheres Projekt desselben Kunden, Durchschnitt eigener Kampagnen.
4. Erkenntnisse: bestes Posting und warum, Empfehlung fuer die Fortsetzung.

## Ausgabe
Tabelle je Posting + Gesamt, drei Kernaussagen in Kundensprache, interne Notiz (Nachkalkulation, Upsell-Ansatz).
Keine geschoenten Zahlen: Luecken offen benennen. Versand des Berichts nur nach CEO-Freigabe.
