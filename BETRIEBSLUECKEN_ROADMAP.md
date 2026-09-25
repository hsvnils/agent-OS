# Roadmap: Betriebsluecken schliessen (BF-01, BF-03, BF-04, BF-08)

- Status: in Umsetzung
- Stand: 2026-09-25
- Arbeitsbranch: `ai/betriebsluecken`
- Basiscommit: `ba77909`
- Naechster Schritt: Probelauf Etappe 3 bestanden -> CEO-Go fuer den Merge nach `main` (ab dann naechtlich live),
  danach am Morgen den Timer-Lauf pruefen (Verifikation 3).
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel

Vier Befunde aus der Doku-Pruefung vom 2026-09-25 (`docs/bekannte-fehler.md`) beheben: die 4 roten Tests,
den fehlenden Deploy-Schutz, die Backup-Luecke und das Gedaechtnis-Log im oeffentlichen Repo.

## Analyse (Belege, read-only erhoben am 2026-09-25)

- **BF-01:** Nur zwei Stellen haben das feste Datum, das „neu" sein soll: `orchestrator/governance/github_watch.py:98`
  (`MockGitHubWatch`, `erstellt="2026-06-01..."`) und `orchestrator/tests/test_watch.py:31`. `flag_fast_growers`
  rechnet `neu_tage=60` gegen `datetime.now()` -> seit 2026-07-31 nicht mehr neu. Andere Tests mit
  `2026-06-01` (`test_ig_inbox`, `test_investment_*`) haengen nicht vom heutigen Datum ab und sind gruen.
- **BF-03:** `deploy/sync-to-nas.sh` Zeilen 47-90 schliessen `crm`, `content_ops`, `nutzung` nicht aus. Auf der NAS
  existieren sie live: `crm/log.jsonl` (7 Zeilen), `content_ops/` (104 KB), `nutzung/log.jsonl` (17 Zeilen).
  Lokal auf dem MACO470 gibt es sie nicht (Dry-Run 2026-09-25: nicht im Paket).
- **BF-04:** `deploy/backup-from-nas.sh` sichert 10 Dateien. Auf der NAS vorhanden, aber nicht gesichert:
  `crm/log.jsonl` (7), `ig_inbox/log.jsonl` (1032), `reel_freigabe/log.jsonl` (59), `approvals/log.jsonl` (91),
  `investment/features.jsonl` (27.962, 14 MB), `trajektorien/log.jsonl` (1), `nutzung/log.jsonl` (17) — zusammen
  **29.169 Zeilen**, komprimiert unter 1 MB je Stand. Nicht vorhanden: `social/log.jsonl`,
  `entwicklung/roadmap.jsonl`, `crm/sync_cursor.txt` (das Skript ueberspringt fehlende Dateien).
  Ausserdem: `reel_freigabe/*.mp4` = 1,3 GB, `orchestrator/state/instagram_token.json` (Secret).
  Das Skript prueft „Historie geschrumpft" ueber die **Summe aller JSONL-Zeilen** -> nur **append-only**
  Stores duerfen hinein. Beleg: keiner der sieben Stores wird im Code neu geschrieben (`grep` nach
  `open(...,"w")`/`write_text`/`os.replace` findet nur Content-Caches, Herzschlag, Token, Roadmap-Markdown).
  Platz auf dem MACO470: 952 GB frei.
  **Wichtig:** Der Timer ruft `/home/luna/ki-unternehmen/deploy/backup-from-nas.sh` direkt aus dem
  Arbeitsordner auf (`systemctl cat luna-backup.service`) -> **was dort ausgecheckt ist, laeuft um 03:20.**
- **BF-08:** `orchestrator/memory/log.jsonl` ist seit `618c8ae` versioniert (2 Testeintraege vom 2026-06-23),
  `.gitignore` Zeile 27 sagt ausdruecklich „kanonischer log.jsonl bleibt versioniert". Ebenfalls nicht ignoriert:
  `nutzung/`, `cutter_ops/`. Das Repo ist oeffentlich (`git ls-remote` anonym moeglich).

## Scope

BF-01, BF-03, BF-04 (nur append-only Stores + Hinweis-Logik im Doku-Check), BF-08 (Index + `.gitignore`).

## Nicht-Scope

- Deploy auf die NAS, Container-Neustarts (nichts davon ist noetig: alle Aenderungen wirken auf dem MACO470
  oder nur in Git)
- Umschreiben der Git-Historie (Inhalt harmlos; ein History-Rewrite eines oeffentlichen Repos waere
  unverhaeltnismaessig)
- Sicherung der Reel-Videos (1,3 GB) und des Instagram-Tokens (Secret) — CEO-Entscheidung 2026-09-25: **nein**
- BF-02 (unbeaufsichtigter Neustart, CEO-Aufgabe), alle anderen Eintraege aus `docs/bekannte-fehler.md`
- Schutzbereiche laut `governance/roadmap-workflow.md` B4

## Etappen

### Etappe 1: Test-Zeitbombe entschaerfen (BF-01)

- Status: verifiziert (2026-09-25, auf dem Arbeitsbranch; Merge offen) — `orchestrator/tests`: 723 passed,
  0 failed, 4 skipped; `cutter/tests`: 74 passed. Gegenprobe mit festem Datum: 4 failed, wie erwartet.
- Ziel / Scope: Mock-Datum relativ zu heute setzen (heute minus 10 Tage) in `MockGitHubWatch` und
  `test_watch.py:31`. Nicht-Scope: Produktionslogik von `flag_fast_growers`.
- Gate: beide Suiten, **0 rote Tests**; Doku-Check ok.
- Verifikation: `.venv/bin/python -m pytest orchestrator/tests -q` -> erwartet: `0 failed`, 4 skipped
  (Phase 17); `.venv/bin/python -m pytest cutter/tests -q` -> erwartet: `74 passed`.
  Gegenprobe: Datum testweise wieder auf `2026-06-01` -> die 4 Tests werden rot.
- Dry-Run: entfaellt (keine produktive Mutation).
- Risiko / Rueckweg: praktisch keins; `git revert`.
- Abhaengig von: – · Aufwand: klein · Risiko: niedrig
- Doku: Test-Baseline und BF-01 -> Archiv in `docs/bekannte-fehler.md`.

### Etappe 2: Deploy-Schutz vervollstaendigen (BF-03)

- Status: verifiziert (2026-09-25, auf dem Arbeitsbranch; Merge offen) — Probedateien im Dry-Run vorher `3`,
  nachher `0`; Doku-Check `Deploy-Schutz fehlt` = `0`. Probedateien geloescht. Kein Deploy noetig (Skript laeuft
  auf dem MACO470).
- Ziel / Scope: `--exclude='./crm'`, `--exclude='./content_ops'`, `--exclude='./nutzung'` in
  `deploy/sync-to-nas.sh`.
- Gate: Dry-Run-Probe unten wie erwartet; Doku-Check ohne Hinweis „Deploy-Schutz fehlt"; Tests gruen.
- Verifikation: Probedateien `crm/_probe.jsonl`, `content_ops/_probe.jsonl`, `nutzung/_probe.jsonl` lokal
  anlegen, `deploy/sync-to-nas.sh --dry-run | grep -c _probe` -> erwartet: `0` (vor der Aenderung: `3`);
  Probedateien danach loeschen. `python3 scripts/doku_check.py | grep -c 'Deploy-Schutz fehlt'` -> erwartet `0`.
- Dry-Run: ist die Verifikation selbst; die NAS wird nicht angefasst.
- Risiko / Rueckweg: keins fuer Live-Daten (es wird nur weniger uebertragen); `git revert`.
- Abhaengig von: – · Aufwand: klein · Risiko: niedrig
- Doku: `docs/datenfluesse.md` Abschnitt 3 (Spalte Deploy-Schutz), BF-03 -> Archiv.

### Etappe 3: Backup vervollstaendigen (BF-04)

- Status: umgesetzt (2026-09-25, Branch, im Worktree `.worktrees/betriebsluecken`) — 9 Eintraege in `FILES`,
  Doku-Check prueft Deploy-Schutz/Backup jetzt blockierend (Ausnahmen: Block `ohne-backup`); Tests 798 passed.
  Probelauf 2026-09-25 12:52: **17 Stores, 81.088 Events, Exit 0; alle 17 Dateien zeilengleich mit der NAS**;
  `~/LUNA-Backups` unberuehrt, Wegwerf-Kopie geloescht. Offen: Merge (Go), dann Timer-Lauf 03:20 pruefen.
- Ziel / Scope: `FILES` in `deploy/backup-from-nas.sh` um die sieben append-only Stores erweitern
  (`crm/log.jsonl`, `ig_inbox/log.jsonl`, `reel_freigabe/log.jsonl`, `approvals/log.jsonl`,
  `investment/features.jsonl`, `trajektorien/log.jsonl`, `nutzung/log.jsonl`) plus die heute fehlenden, aber
  im Code vorgesehenen `social/log.jsonl` und `entwicklung/roadmap.jsonl`. Im Doku-Check einen Block
  `doku-check:ohne-backup` in `docs/datenfluesse.md` einfuehren, der bewusst ungesicherte Speicher (Caches,
  Herzschlag) als Absicht markiert, damit nur echte Luecken als Hinweis erscheinen.
- Gate: Probelauf in ein Wegwerf-Verzeichnis wie erwartet; Tests + Doku-Check gruen; am naechsten Morgen
  der echte Timer-Lauf wie erwartet.
- Verifikation:
  1. Probelauf (liest nur von der NAS): `BACKUP_DIR=<scratch> BACKUP_MELDEN=0 bash deploy/backup-from-nas.sh`
     -> erwartet: `17 Stores` gesichert, Exit 0.
  2. Je Datei Zeilenzahl NAS gegen Probe-Backup vergleichen (`ssh luna-nas wc -l <datei>` vs. `wc -l`) ->
     erwartet: **alle 17 gleich** (zum Zeitpunkt des Laufs).
  3. Nach dem Timer-Lauf 03:20: `journalctl -u luna-backup.service --since today | grep Stores` -> erwartet:
     `17 Stores`, kein `FEHLER`; neuer Ordner in `~/LUNA-Backups`.
- Dry-Run: Probelauf 1 schreibt nur ins Wegwerf-Verzeichnis, nicht nach `~/LUNA-Backups`, rotiert nichts.
- Risiko / Rueckweg: (a) Ein Store ist doch nicht append-only -> falscher Alarm „Historie geschrumpft",
  Backup rotiert dann nicht (sicherer Ausfall, Telegram-Meldung) -> Datei wieder aus `FILES` nehmen.
  (b) **Der Timer nimmt den ausgecheckten Stand** -> Etappe wird erst durch den Merge nach `main` live;
  vor 03:20 muss `main` ausgecheckt sein. Rueckweg: `git revert` + `main` auschecken.
- Abhaengig von: – (unabhaengig von Etappe 2) · Aufwand: klein · Risiko: mittel (laeuft naechtlich)
- Doku: `docs/datenfluesse.md` Abschnitt 3 (Spalte Backup), `docs/bekannte-fehler.md` BF-04 -> Archiv.
- Freigaben: Go fuer die Etappe **plus** Go fuer den Probelauf (liest Live-Daten) **plus** Go fuer den Merge
  nach `main` (ab dann naechtlich live).

### Etappe 4: Git-Hygiene (BF-08)

- Status: geplant
- Ziel / Scope: `git rm --cached orchestrator/memory/log.jsonl`; `.gitignore`: die Datei sowie `nutzung/` und
  `cutter_ops/` aufnehmen, den Kommentar in Zeile 27 berichtigen.
- Gate: `git ls-files orchestrator/memory/log.jsonl` leer; `git check-ignore` greift fuer alle drei; Tests
  gruen; die lokale Datei ist noch da.
- Verifikation: `git ls-files orchestrator/memory/log.jsonl | wc -l` -> erwartet `0`;
  `git check-ignore orchestrator/memory/log.jsonl nutzung/x cutter_ops/x | wc -l` -> erwartet `3`;
  `test -f orchestrator/memory/log.jsonl && echo da` -> erwartet `da`.
- Dry-Run: `git rm --cached -n orchestrator/memory/log.jsonl` -> erwartet genau diese eine Datei.
- Risiko / Rueckweg: Auf einem anderen Klon (z. B. **MacBook**) loescht ein spaeteres `git pull` die lokale
  Datei — dort schreibt der Sprachkanal sein Gedaechtnis hinein. Vor einem Pull am MacBook die Datei sichern.
  NAS unbetroffen (kein Git, Datei vom Deploy ausgenommen). Die 2 Testeintraege bleiben in der Historie.
  Rueckweg: `git revert`.
- Abhaengig von: – · Aufwand: klein · Risiko: niedrig
- Doku: BF-08 -> Archiv; `docs/datenfluesse.md` Abschnitt 3.

## Reihenfolge

1 -> 2 -> 3 -> 4 empfohlen (1 macht das Test-Gate fuer alle weiteren Etappen scharf: danach bedeutet jeder rote
Test einen echten Fehler). Die Etappen sind technisch unabhaengig und einzeln abnehmbar.

## Fragen an den CEO (entschieden 2026-09-25: beide NEIN, wie empfohlen)

1. **Reel-Videos (1,3 GB) mitsichern?** Vorschlag: nein — gepostete Reels liegen bei Facebook, Rohmaterial im
   NAS-Clip-Archiv.
2. **Instagram-Token (Secret) mitsichern?** Vorschlag: nein — er erneuert sich selbst und laesst sich aus der
   `.env` neu seeden (BF-14); ein Secret mehr auf dem Sicherungsziel ist eine CISO-Frage.

## Dokumentationspflichten

`projekt_changelog.md` (jede Etappe), Etappen-Status + `Naechster Schritt` hier, `docs/bekannte-fehler.md`
(Baseline, Archiv), `docs/datenfluesse.md` (Abschnitt 3), `ROADMAP.md` (Verzeichnis-Status).

## Definition of Done

Alle vier Etappen `verifiziert`; BF-01/03/04/08 im Archiv von `docs/bekannte-fehler.md`; Testsuite ohne
roten Test; `scripts/doku_check.py` ohne Hinweis „Deploy-Schutz fehlt" und nur noch bewusst markierte
Speicher ohne Backup. Abnahme durch den CEO, Status `abgeschlossen` traegt der ausfuehrende Agent ein.
