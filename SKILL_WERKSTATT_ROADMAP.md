# Roadmap: Skill-Werkstatt -- eigene Skills beobachten, bauen, pruefen und verbessern

- Status: geplant
- Stand: 2026-10-16
- Arbeitsbranch: `ai/skill-werkstatt`
- Basiscommit: `eac473f`
- Naechster Schritt: CEO-Entscheidungen (Bedeutung „trainieren“, kein Import fremder Skills) und Go fuer S1-S4 abwarten.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-16)

„Ich wuerde gern wissen und zukuenftig auf dem Laufenden bleiben, welche SKILLS fuer Agenten so genutzt werden. Ich will
keine Skills aus dem Internet nutzen, sondern diese am liebsten selbst trainieren und aufbauen.“

## Analyse (read-only, 2026-10-16)

- **Wir haben schon eigene Skills:** 54 Skills in `skills/<abteilung>/<name>/SKILL.md` (z. B. CLO 7, CRO 6, Videograf 5,
  CCO/CFO je 4), Format `governance/skill-standard.md` (`core/skill_format.py`), geladen je Fachagent ueber
  `core/dept_skills.py` -- jeder Skill geht vorher durch das Security-Gate `core/skill_gate.py` (SkillSpector-Muster).
  Alle sind selbst geschrieben (`lizenz: intern`).
- **Fremde Skills:** Register 2026-07-03 -- „VoltAgent/awesome-agent-skills“ = SPAETER (nur ueber das Gate),
  NVIDIA-Skills-Inhalt verworfen, Format teilweise uebernommen. Mit der CEO-Vorgabe wird daraus: **kein Import**, fremde
  Sammlungen hoechstens als Ideenquelle (nur Name, Zweck, Kategorie -- nie Text oder Code uebernehmen).
- **Es fehlt:** (1) ein Blick nach aussen, welche Skill-Arten verbreitet sind; (2) ein geordneter Weg, aus unserer eigenen
  Arbeit neue Skills abzuleiten; (3) Pruefung, ob ein Skill wirklich hilft; (4) Verbesserung aus Rueckmeldungen.
- **„Trainieren“:** Ein eigenes Modell feinzutunen braucht viel Rechenleistung und Beispieldaten (lokal ist schon das
  30B-Modell zu gross, siehe Uebergabe 2026-09-26) und waere an ein Modell gebunden (AGENTS.md: modell-agnostisch).
  **Empfehlung:** Skills „trainieren“ = Anleitung + Beispiele + Pruffaelle, die aus unseren Ergebnissen und deinen
  Korrekturen laufend besser werden -- funktioniert mit jedem Modell und ist kostenlos.
- Vorhandene Bausteine: Fachagenten-Nutzung (`agenten_nutzung/`, ohne Inhalte), Erfahrungsspeicher (`erfahrung_merken`,
  Trajektorien), lokales Modell auf dem MACO470 (kostenlose Probelaeufe), Modell-Radar (Quellen-/Abruf-Technik).

## Etappe S1: Skill-Radar (Researcher, nur Ideen)

- Status: geplant
- Ziel / Scope: monatlich ein Ueberblick, welche Skill-Arten fuer Agenten verbreitet sind. Quellen nur oeffentliche
  **Uebersichten**: Hersteller-Dokus/Neuigkeiten zu Agent-Skills (aus dem Modell-Radar), GitHub-Themen (`agent-skills`,
  `claude-skills` u. ae., ueber die vorhandene GitHub-Abfrage: Name, Kurzbeschreibung, Sterne). Regelbasiert in Kategorien
  sortiert und **unseren Abteilungen zugeordnet**: „haben wir schon (eigener Skill …)“ oder „Luecke -> Idee“.
  Es wird **nichts heruntergeladen oder uebernommen** -- nur die Idee landet auf der Liste.
- Gate: Tests mit aufgezeichneten Antworten; Pruefung, dass kein fremder Text gespeichert wird; Gegenprobe.
- Aufwand: klein bis mittel.

## Etappe S2: Skill-Luecken aus unserer eigenen Arbeit

- Status: geplant
- Ziel / Scope: LUNA erkennt, wo ein Skill fehlt -- haeufige Fachagent-Anfragen ohne passenden Skill, wiederkehrende
  Ablaeufe im Erfahrungsspeicher, deine Korrekturen im Chat („nein, so …“), Fehlversuche. Daraus Vorschlag „Neuer Skill X
  fuer Abteilung Y“ mit Begruendung als Antrag (Kategorie `skill`). Zusammen mit den Ideen aus S1 eine Liste in LUNA-OS.
- Gate: Tests (Erkennung, keine Doppel-Vorschlaege); Gegenprobe.
- Aufwand: mittel.

## Etappe S3: Skill-Werkstatt -- bauen und pruefen

- Status: geplant
- Ziel / Scope: Aus einem freigegebenen Vorschlag schreibt LUNA einen **eigenen** Skill-Entwurf (Format wie bisher,
  `lizenz: intern`) mit 3-5 **Pruffaellen** (Eingabe + woran ein gutes Ergebnis erkennbar ist). Probelauf auf dem lokalen
  Modell (kostenlos): Aufgabe **mit und ohne** Skill, Bewertung nach den Pruffaellen. Erst wenn der Skill besser ist, legt
  LUNA ihn dir zur Freigabe vor; danach aktiv mit Version. LUNA-OS: Skills je Abteilung mit Version, Nutzung und Pruf-Ergebnis.
- Nicht-Scope: Skills mit Skripten/Code (bleiben gesperrt, Gate), Aenderungen an Charten (nur HoA auf CEO-Anweisung).
- Gate: Tests (Entwurf erfuellt das Format, Gate bestanden, Probelauf mit/ohne, Freigabe Pflicht); Browsertest.
- Aufwand: mittel bis gross.

## Etappe S4: Skills lernen aus Rueckmeldungen

- Status: geplant
- Ziel / Scope: 👍/👎 und kurze Korrektur zu Fachagent-Antworten (Telegram-Knoepfe, LUNA-OS) werden je Skill gesammelt.
  Monatlich (oder ab 3 Rueckmeldungen) schlaegt LUNA eine **verbesserte Version** vor (Aenderung sichtbar als Vorher/Nachher),
  die alten und neuen Pruffaelle muessen bestehen; Freigabe durch dich, jederzeit zurueck auf die alte Version.
- Gate: Tests (Version, Rueckweg, Pruffaelle); Gegenprobe.
- Aufwand: mittel.

## Nicht-Scope

Kein Import fremder Skills (auch nicht ueber das Gate), kein Modell-Feintuning, keine Skills mit ausfuehrbarem Code,
keine automatische Aktivierung ohne Freigabe.

## Entscheidungen fuer den CEO

1. **„Trainieren“** = Skills aus Anleitung, Beispielen, Pruffaellen und deinen Rueckmeldungen laufend verbessern (Empfehlung)
   -- statt ein Modell feinzutunen?
2. **Kein Import fremder Skills:** Register-Eintrag „awesome-agent-skills“ von SPAETER auf **VERWORFEN (nur Ideenquelle)**
   aendern?
3. Reihenfolge: S1 + S2 zuerst (Ueberblick und Luecken), dann S3 + S4?

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/entscheidungs-register.md`, `governance/skill-standard.md`
(Pruffaelle, Versionen), `docs/datenfluesse.md` (neue Abfragen/Speicher).

## Definition of Done

LUNA zeigt, welche Skill-Arten draussen verbreitet sind und wo wir Luecken haben, baut daraus eigene Skills mit
Pruffaellen, beweist ihren Nutzen im Probelauf und verbessert sie aus deinen Rueckmeldungen -- ohne fremde Skills zu uebernehmen.
