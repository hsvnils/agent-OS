---
name: mobil-check
version: 1.0.0
beschreibung: Prueft Oberflaechen auf Bedienbarkeit am iPhone 17 Pro (Web-App, Safe Areas), iPad und Rechner.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Mobil- und Safe-Area-Check (CXO)

## Wann anwenden
Vor jedem Abschluss einer UI-Aenderung und wenn der CEO meldet, dass etwas am Handy schlecht aussieht.

## Pruefgeraete (Pflicht)
Rechner (ca. 1300 px), iPad (820 px), **iPhone 17 Pro als Web-App aus Safari (402 x 874 px, Dynamic Island oben
59 px, Home-Balken unten 34 px)**.

## Checkliste
1. Nichts ragt aus dem Bild, kein seitliches Scrollen der Seite.
2. Raender links/rechts symmetrisch; Fenster am iPhone volle Breite.
3. Nichts Bedienbares unter der Dynamic Island oder im Home-Balken; feste Leisten mit Safe-Area-Abstand.
4. Tippflaechen mindestens 44 px hoch; Eingabefelder 16 px Schrift (kein Safari-Zoom).
5. Texte nicht abgeschnitten; lange Woerter/Nummern umbrechen.
6. Ende eines Fensters erreichbar (nicht von Leisten verdeckt); Dunkel/Hell lesbar.

## Ausgabe
Je Geraet: ok/Befund mit Element und Mass (px), Vorschlag fuer die Korrektur. Erst nach allen drei Geraeten „fertig“.
