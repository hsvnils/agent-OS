---
name: preis-margen-analyse
version: 1.0.0
beschreibung: Nachkalkulation von Auftraegen (Projektzeiten, Fahrtkosten, Fremdkosten) und Preisvergleich ueber TKP und Stundensatz.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A2, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Preis- und Margen-Analyse (CFO, mit CRO)

## Wann anwenden
Nach Abschluss eines Auftrags (Nachkalkulation), vor einem neuen Angebot (Preis plausibel?) oder wenn der CEO fragt,
welche Leistungen sich lohnen.

## Daten (liefert LUNA aus LUNA-OS)
Angebot/Auftragsbestaetigung (Positionen, Paketpreis), Rechnung(en) mit **Projektzeiten** (Stunden, Kilometer),
Eingangsbelege des Auftrags (Fremdkosten, z. B. Freie, Requisiten), Ist-Kennzahlen aus dem Projektbericht
(Reichweite/Impressionen).

## Kennzahlen
- **Effektiver Stundensatz** = (Netto-Erloes minus Fremdkosten minus Fahrtkosten) / Projektstunden. Vergleich mit dem
  internen Satz (Projektstunde 65 €, km 0,50 € laut CEO-Vorgabe -- aktuelle Werte aus LUNA-OS nehmen, wenn mitgeliefert).
- **Deckungsbeitrag** je Auftrag und je Leistungsart (Reel, Post, Story, Paket).
- **TKP** (Tausender-Kontakt-Preis) = Preis / Impressionen x 1.000; Vergleich zwischen Auftraegen und mit
  Marktbenchmarks (nur als Einordnung, Quelle nennen).
- **Abweichung Plan/Ist**: geplanter Aufwand (Angebot) vs. tatsaechlicher (Projektzeiten).

## Vorgehen
1. Erloes, Kosten, Zeiten je Auftrag tabellieren.
2. Kennzahlen berechnen; jede Zahl mit Herkunft.
3. Ausreisser erklaeren (Mehraufwand, Zusatzleistungen, Rabatt).
4. Empfehlung: Preis halten/anheben, Paket anpassen, Zusatzleistung abrechnen.

## Ausgabe
Tabelle (Auftrag · Erloes · Kosten · Stunden · eff. Stundensatz · TKP · Abweichung) + drei Saetze Fazit + Empfehlung als
**Entwurf**. Preisentscheidungen trifft der CEO (CEO-Tor Geld).
