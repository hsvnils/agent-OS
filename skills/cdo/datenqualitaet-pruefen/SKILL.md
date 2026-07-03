---
name: datenqualitaet-pruefen
version: 1.0.0
beschreibung: Prueft Daten/Zahlen anhand der 6 Datenqualitaets-Dimensionen, bevor sie an andere Agenten gehen.
lizenz: intern
autor: Head of Agents
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Datenqualitaet pruefen (CDO)

Bevor der CDO Zahlen an andere Agenten liefert (CFO-Kosten, Social-Insights, Umsatz, App-Analytics), pruefen
diese die **Datenqualitaet** -- damit niemand mit falschen/widerspruechlichen Zahlen arbeitet.

## Die 6 Dimensionen (Wang/Strong)
1. **Genauigkeit** -- spiegeln die Werte die Realitaet? (Ausreisser/Tippfehler/falsche Einheiten?)
2. **Vollstaendigkeit** -- fehlt etwas? (leere Felder, fehlende Zeitraeume/Quellen?)
3. **Konsistenz** -- widerspricht sich nichts ueber Quellen/Systeme? (dieselbe Kennzahl 2x verschieden?)
4. **Aktualitaet** -- ist der Stand aktuell genug fuer die Entscheidung? (Datum/Stand angeben!)
5. **Gueltigkeit** -- passen Format/Wertebereich? (Prozente 0-100, plausible Groessenordnung?)
6. **Eindeutigkeit** -- keine Doubletten/Doppelzaehlungen?

## Vorgehen
- Jede gelieferte Kennzahl/Datei kurz gegen die 6 Dimensionen checken.
- **Quelle + Stand (Datum)** immer mitgeben.
- **Fehler-/Luecken-Quote** grob beziffern, wenn moeglich.
- Bei Widerspruch: NICHT weitergeben, sondern klaeren/kennzeichnen.

## Output (an den Head of Agents / Abnehmer)
1. **Ampel:** gruen (verlaesslich) / gelb (mit Vorbehalt -- welchem?) / rot (nicht nutzbar).
2. **Befunde** je verletzter Dimension (was + Auswirkung).
3. **Bereinigte Zahl / Empfehlung** + Quelle/Stand.

## Grenzen
Liefert **Grundlage, keinen Beschluss** (keine Eigeninterpretation als Entscheidung). Personenbezogene Daten
nur nach **DSGVO-Pruefung durch den CISO**.
