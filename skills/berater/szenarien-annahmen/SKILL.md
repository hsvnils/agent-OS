---
name: szenarien-annahmen
version: 1.0.0
beschreibung: Rechnet Plaene in drei Szenarien ueber benannte Treiber, fuehrt ein Annahmen-Register und macht ein Pre-Mortem vor grossen Entscheidungen.
lizenz: intern
autor: Head of Agents
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Szenarien, Annahmen-Register und Pre-Mortem (Unternehmensberater)

Planzahlen sind Annahmen. Dieser Skill macht sie sichtbar, testbar und rechnet, was passiert, wenn sie nicht
eintreten.

## Wann anwenden
Bei jedem Plan mit Zahlen, vor grossen Entscheidungen (App-Start, Merch-Investition, Teilzeit/Kuendigung).

## Drei Szenarien ueber Treiber
Nie Pauschalwerte („10.000 EUR Sponsoring"), sondern Treiber: Follower/Reichweite, Konversion, Preis, Anzahl
Deals, Churn. Je Treiber drei Werte:
- **Konservativ:** Reichweite minus 30 %, ein Sponsor faellt weg, Konversion am unteren Benchmark.
- **Basis:** beste ehrliche Schaetzung, belegt durch eigene Daten.
- **Optimistisch:** oberer Benchmark, nur mit Begruendung.
Geplant wird mit **Basis**, Entscheidungen muessen **konservativ** verkraftbar sein.

## Annahmen-Register (eine Zeile je Annahme)
Annahme · Wert · Evidenz (gemessen / Benchmark / geschaetzt) · Zuversicht · Auswirkung falls falsch · Test ·
Pruefdatum · verantwortlich · Status. Riskanteste Annahme (hohe Auswirkung, wenig Evidenz) zuerst klein testen
(Umfrage, Warteliste, Vorbestellung, ein Pilot-Sponsor).

## Pre-Mortem (vor grossen Schritten)
1. „Es ist ein Jahr spaeter, das Vorhaben ist gescheitert. Warum?" -- jeder schreibt still Gruende auf.
2. Sammeln, clustern, je Ursache Gegenmassnahme, Person, Pruefzeitpunkt.
3. Jede Ursache wird eine Annahme im Register.
Typische Ursachen bei Fan-Medien: Plattform drosselt Reichweite, Verein mahnt Marken- oder Bildrechte ab,
Saisonpause, Zeitmangel neben dem Job, App-Store-Ablehnung, Kleinunternehmergrenze ueberraschend ueberschritten.

## Ausgabe
Szenario-Tabelle (konservativ / Basis / optimistisch) je Quelle und gesamt, Top-5-Annahmen mit Test und Datum,
Pre-Mortem-Liste mit Gegenmassnahmen.

## Grenzen
Analyse, keine Entscheidung. Benchmarks aus Anbieter-Blogs als unsicher kennzeichnen.
