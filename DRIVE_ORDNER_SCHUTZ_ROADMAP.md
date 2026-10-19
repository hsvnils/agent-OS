# Roadmap: Drive-Fix, Kundenordner mit Freigabe-Link, Prompt-Injection-Schutz (Sammel-Roadmap)

- Status: in Umsetzung
- Stand: 2026-10-19
- Arbeitsbranch: `ai/kundenordner-injektion`
- Basiscommit: `d816b1d`
- Naechster Schritt: F1-F3 bauen, dann Deploy des Blocks. Go CEO 2026-10-19 fuer alle acht Etappen, Weg A, Empfehlungen angenommen.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-19)

Eine Roadmap fuer drei Punkte: (1) Upload-Problem in Google Drive beheben, (2) Kundenordner auf der NAS mit Freigabe-Link
per Mail, (3) Schutz gegen Prompt Injection ausbauen und verfeinern. **Nach jedem erledigten Punkt zeigt Claude eine
Tabelle mit erledigten und offenen Punkten** (CEO-Arbeitsanweisung, gilt generell).

Diese Datei legt **Reihenfolge und Stand** fest. Die Einzelheiten je Etappe (Analyse, Scope, Gate) stehen in:
- `docs/bekannte-fehler.md` BF-72 (Drive),
- `KUNDENORDNER_FREIGABE_ROADMAP.md` (F1-F3),
- `PROMPT_INJECTION_SCHUTZ_ROADMAP.md` (I1-I4).

## Reihenfolge (Empfehlung) und Stand

Der Schutz kommt **vor** dem oeffentlichen Freigabe-Link: Sobald ein Pfad ohne Anmeldung erreichbar ist und LUNA Mails mit
Links verschickt, sollen Fremdtexte schon markiert und Handlungen nach einem Verdacht gesperrt sein.

| Nr. | Etappe | Inhalt | Aufwand | Status |
|---|---|---|---|---|
| 1 | D1 | Drive-Upload: Mails (.eml) mit neutralem Dateityp hochladen, 3 haengende Belege werden nachgeholt (BF-72) | klein | ✅ live (bad49d5) |
| 2 | I1 | Jeder Fremdtext (Mail, Drive, Tabellen, Belege, Kundenantworten, Content-Feed) wird geprueft und markiert | mittel | ✅ live (d2bd03e) |
| 3 | I2 | Feinere Erkennung (Tarnungen, versteckter Text, Rollenmarken, Datenabfluss ueber Links) + Testkorpus | mittel | ✅ live (d2bd03e) |
| 4 | I3 | Handlungs-Sperre nach Verdacht (Senden, Termine, Schreiben, Loeschen, Freigaben nur nach Rueckfrage) | mittel | ✅ live (d2bd03e) |
| 5 | F1 | Kundenordner je Kunde/Projekt auf der NAS (anlegen, hochladen, Lieferungen uebernehmen) | mittel | ⬜ offen |
| 6 | F2 | Freigabe-Link mit Ablauf, optional Passwort, widerrufbar, Abruf-Protokoll | mittel | ⬜ offen (Weg A entschieden) |
| 7 | F3 | Link per Mail (Versanddialog, Textbaustein „Dateifreigabe“, nur per Klick) | klein | ⬜ offen |
| 8 | I4 | Ueberwachung (CISO-Bericht, Leistungsbericht) + Angriffs-Testreihe in der Testsuite | klein bis mittel | ⬜ offen |

Deploy: nach D1 sofort (kleiner Fix, stoppt die taeglichen Fehlermeldungen); danach je Block (I1-I3, F1-F3, I4) ein Deploy,
oder auf Wunsch alles am Stueck.

## Entscheidungen fuer den CEO

1. Reihenfolge wie oben (Schutz vor Freigabe-Link)?
2. Freigabe-Link: Weg A (eigener LUNA-OS-Link, Empfehlung) oder B (Synology-Freigabe)? Standard 30 Tage, Passwort optional?
3. Go fuer alle acht Etappen (am Stueck mit Deploys je Block) oder einzeln?

## Doku

`projekt_changelog.md`, Status-Tabelle hier und in `ROADMAP.md`, Einzel-Roadmaps, `docs/bekannte-fehler.md`,
`docs/entscheidungs-register.md`, `docs/datenfluesse.md`.

## Definition of Done

Alle acht Zeilen der Tabelle stehen auf ✅ -- Drive-Sicherung ohne Fehler, Kundenordner mit sicherem Link per Mail, und
Fremdtexte koennen LUNA nicht mehr unbemerkt zu Handlungen bringen.
