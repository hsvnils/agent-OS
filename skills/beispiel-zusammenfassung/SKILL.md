---
name: beispiel-zusammenfassung
version: 1.0.0
beschreibung: Fasst einen laengeren Text in wenigen Stichpunkten zusammen.
lizenz: intern
autor: Head of Agents
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Beispiel-Skill: Zusammenfassung

Referenz-Skill, der den Skill-/Charta-Standard (siehe `governance/skill-standard.md`) demonstriert und
zur Verifikation des Skill-Security-Gates (`skill_pruefen`) dient. Enthaelt bewusst **keine Skripte** und
keine riskanten Muster -> das Gate liefert das Verdikt `bestanden`.

## Aufgabe
Fasse den uebergebenen Text sachlich zusammen.

## Ablauf
1. Kernaussagen identifizieren.
2. In 3-5 knappe Stichpunkte buendeln.
3. Neutralen Ton halten, keine Wertung hinzufuegen.

## Output
- 3-5 Stichpunkte, je eine Zeile.
