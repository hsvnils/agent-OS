---
name: fehlersuche
version: 1.0.0
beschreibung: Systematische Fehlersuche entlang docs/bekannte-fehler.md -- erst bekannte Fehler pruefen, dann eingrenzen, Ursache belegen, Regressionstest.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A3/A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Fehlersuche (CTO)

## Wann anwenden
Wenn etwas nicht geht („geht nicht“ ist keine Endstation, `AGENTS.md` 2), bei roten Tests, Ausfaellen von Nachtlaeufen
oder Meldungen des CEO.

## Vorgehen
1. **Zuerst `docs/bekannte-fehler.md` lesen:** Ist das Symptom bekannt (Offen, Umgehung aktiv, Lehren)? Gilt eine
   Umgehung? Gehoert ein roter Test zur Baseline?
2. **Symptom genau fassen:** Was, wo (NAS-Container, MACO470, Werkbank, Browser/iPhone), seit wann, nach welchem Deploy?
3. **Eingrenzen:** letzter funktionierender Stand (git log), Logs, ein Schritt nach dem anderen; Wirkung bis zum
   Empfaenger pruefen (erzeugt ist nicht angekommen).
4. **Ursache belegen**, nicht raten: Fehlermeldung, reproduzierbarer Fall, Test, der vorher rot und nachher gruen ist
   (Gegenprobe).
5. **Beheben** mit kleinster Aenderung; bei Infrastruktur/Kosten/Zugang: Anfrage an den HoA (CEO-Tor).
6. **Festhalten:** neuer Eintrag in `docs/bekannte-fehler.md` (Symptom, Ursache, Status), Lehre, falls allgemein.

## Ausgabe
Symptom · vermutete und belegte Ursache · Loesung oder Umgehung · Test · Eintrag fuer bekannte-fehler (Entwurf).
Wenn keine Loesung: begruendet, mit Alternative, an den HoA.
