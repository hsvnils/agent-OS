---
name: fristen-uebersicht
version: 1.0.0
beschreibung: Fuehrt eine Uebersicht aller Fristen (Steuer, Vertraege, Abos, Versicherungen, Aufbewahrung) und warnt rechtzeitig.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Fristen-Uebersicht (CAO, mit CFO und CLO)

## Wann anwenden
Monatlich, bei neuen Vertraegen/Abos und wenn der CEO fragt „Was steht an?“.

## Fristen-Arten
- **Steuer** (Termine vom Steuerberater bzw. Finanzamt: Erklaerungen, Vorauszahlungen) -- nur nennen, was bekannt ist.
- **Vertraege/Abos:** Laufzeit, Kuendigungsfrist, Verlaengerung (Abo-Liste in LUNA-OS).
- **Versicherungen:** Ablauf, Beitragstermine.
- **Kunden:** Zahlungsziele, Mahnfristen, Liefertermine, Folgeauftrag-Nachfassen.
- **Aufbewahrung:** Belege 8 Jahre, Buecher/Abschluesse 10 Jahre, Geschaeftsbriefe 6 Jahre (AO § 147, CFO-Quellen).
- **System:** Pruefdaten der Rechtsquellen, Zertifikate, Token-Ablaeufe (mit dem CTO).

## Ausgabe
Tabelle (Datum · Frist · Was ist zu tun · Wer · Vorlauf), sortiert nach Datum, die naechsten 30 Tage hervorgehoben.
Unbekannte Daten als Luecke kennzeichnen statt zu schaetzen.
