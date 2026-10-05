---
name: quellenpflege
version: 1.0.0
beschreibung: Haelt die Wissensquellen aller Agenten aktuell (Stand- und Pruefdaten, Nachtabgleich, veraltete Skills).
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Quellenpflege (CKO)

## Wann anwenden
Monatlich, wenn der naechtliche Rechtsquellen-Abgleich eine Aenderung meldet, oder wenn ein Pruefdatum erreicht ist.

## Ist-Stand
Normen im Wortlaut liegen in `skills/<agent>/<skill>/quellen.md` (CLO, CFO, CISO, CHRO) mit „Stand“ und „Naechste
Pruefung“; der Nachtlauf 04:30 vergleicht sie mit gesetze-im-internet.de und meldet nur neue Aenderungen. Verweise
(DSGVO, GoBD, Leitfaeden, Urteile) werden nicht automatisch geprueft. Uebersicht je Agent: Agenten-Profil in LUNA-OS.

## Vorgehen
1. Liste: alle Quellen mit Stand, Pruefdatum, Art (Wortlaut/Verweis), letzte Meldung.
2. Faellig oder geaendert -> betroffene Skills benennen; Aenderung inhaltlich einordnen (betrifft sie die Checkliste?).
3. Verweise: neue Fassung bekannt (z. B. neues BMF-Schreiben)? -> Recherche ueber den Researcher.
4. Vorschlag zur Aktualisierung (Skill + quellen.md neu, Commit) -- die Aenderung macht nicht der Agent selbst.

## Ausgabe
Tabelle (Agent · Skill · Quelle · Stand · Pruefdatum · Status) und Aufgabenliste fuer die Aktualisierung.
