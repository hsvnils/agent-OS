---
name: clip-suche
version: 1.0.0
beschreibung: Findet passende Clips im Video-Archiv (Spielordner, Clip-Gedaechtnis) zu einem Thema, Moment oder Reel-Skript.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Clip-Suche (CKO, mit dem CCO)

## Wann anwenden
Wenn fuer ein Reel, ein Konzept oder eine Kundenanfrage vorhandenes Material gesucht wird.

## Archiv (Ist-Stand)
NAS-Archiv mit Spielordnern (Rohclips), gemountet auf dem MACO470; der Video-Cutter waehlt je Spiel Clips aus
(Transkript per Whisper). Plan fuer ein durchsuchbares Clip-Gedaechtnis: `docs/video-brain-plan.md`.

## Vorgehen
1. Suche praezisieren: Spiel/Datum, Gegner, Moment (Tor, Choreo, Anreise), Personen, Stimmung, Format (9:16).
2. Kandidaten nennen mit Ordner/Datei und Zeitbereich, wenn bekannt; sonst die wahrscheinlichsten Spielordner.
3. Rechte pruefen: Personen erkennbar? Vereinslogos/Fremdmaterial? (CLO-Skills `club-und-markenrechte`, KUG).
4. Luecken melden: Was fehlt und muss neu gedreht werden?

## Ausgabe
Liste der Kandidaten (Quelle, Zeit, Inhalt, Eignung), Rechte-Hinweise, Drehbedarf. Nichts erfinden: nicht gefundene
Clips als „nicht im Archiv gefunden“ markieren.
