# Roadmap: To-dos in LUNA-OS und per Telegram (mit Kalender-Erinnerung)

- Status: abgeschlossen
- Stand: 2026-10-27
- Arbeitsbranch: `ai/todos`
- Basiscommit: `78b35b0`
- Naechster Schritt: keiner -- abgeschlossen 2026-10-27 (CEO hakt ab, Test im laufenden Betrieb). Beim ersten To-do mit Erinnerung pruefen: Kalendertermin, Telegram-Erinnerung, „✓ Erledigt“ loescht den Termin; Auffaelligkeiten nach `docs/bekannte-fehler.md`.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-27, dringend)

„Wir brauchen dringend einen To-Do-Bereich im LUNA-OS, und ich brauche die Moeglichkeit, LUNA per Telegram eine Nachricht
zu senden, damit sie ein To-Do mit Erinnerung im Kalender anlegt.“

## Ist-Stand (Nachweis)

- Kachel **„Zu erledigen“** auf der Hauptseite (`core/todos.py`, `GET /api/todos`): wird nur **aus den Daten abgeleitet**
  (Belege, Rechnungen, Angebote, Auftraege, CRM, Reels) und verschwindet mit der erledigten Arbeit -- eigene, frei
  formulierte Aufgaben gibt es nicht (Register 2026-09-28).
- CRM-To-dos (`crm_store.todo`, `POST /api/crm/todo/<id>/erledigen`) nur fuer Collab-Kontakte.
- Kalender: Werkzeug `termin_anlegen` im Chat -- ohne `bestaetigt=true` nur Vorschau (Google-Sicherheitsmodell 2026-06-25);
  Ausnahme fuer LUNAs **eigene, protokollierte** Erinnerungen (`core/erinnerungen.py`, CEO 2026-09-28).
- Telegram-Chat laeuft ueber LUNA (Claude Sonnet 5.5) mit Werkzeugen; Bot-Zeitplaene pruefen alle 5 min.

## Entscheidungen fuer den CEO (Q0) -- **entschieden 2026-10-27: alle Empfehlungen angenommen**

1. **Ablage:** eigener Speicher `todos/log.jsonl` (Ereignisse, nichts geht verloren), nur NAS + Backup, nicht im Git.
   Felder: Titel, Notiz, faellig (Datum, optional Uhrzeit), Erinnerung (Zeitpunkt), optional Kunde, Quelle
   (LUNA-OS/Telegram), Status offen/erledigt.
2. **Telegram ohne Rueckfrage:** Deine Nachricht ist der Auftrag -- LUNA legt das To-do und den Kalendertermin **direkt**
   an und antwortet mit einer Zusammenfassung und einem Knopf **„↶ Rueckgaengig“**. (Sonst muesstest du jedes To-do
   noch einmal bestaetigen.) Erkannt wird freie Sprache, z. B. „To-do: Kiez Alm wegen Dreh anrufen, Freitag 10 Uhr“
   oder „Erinnere mich morgen um 9 an die Steuer“ -- LUNA waehlt das Werkzeug selbst (Routing durch LUNA).
3. **Erinnerung:** Kalendertermin in LUNAs Kalender mit dir als Gast (wie bisher) **plus** eine Telegram-Nachricht zum
   Erinnerungszeitpunkt (spaetestens 5 min danach) mit Knoepfen **„✓ Erledigt“ / „⏰ +1 Std.“ / „⏰ morgen“**. Ohne
   Uhrzeit: Erinnerung um 09:00 am Faelligkeitstag.
4. **Erledigt:** in LUNA-OS oder per Telegram-Knopf; ein kuenftiger Kalendertermin des To-dos wird dann geloescht (nur
   LUNAs eigener, protokollierter Termin).
5. **Anzeige:** neuer Bereich **„✅ To-dos“** in der Navigation (ueberfaellig / heute / demnaechst / ohne Datum /
   erledigt), dazu erscheinen faellige eigene To-dos auch in der Kachel „Zu erledigen“ auf der Hauptseite.

## Etappe T1: To-do-Speicher und Bereich in LUNA-OS

- Status: gebaut 2026-10-27 (`core/aufgaben.py`, `/api/aufgaben*` nur Modul administration, Bereich „✅ To-dos“ als eigener Navigationspunkt mit Schnell-Eingabe, Gruppen, Abhaken, Bearbeiten/Loeschen; faellige To-dos in „Zu erledigen“ mit „✓ Erledigt“; Speicher `todos/log.jsonl` nur NAS + Backup, vom Deploy ausgenommen). Deployt 2026-10-27 (4ce6308; live: `/api/aufgaben` antwortet, App „aufgaben“ fuer den CEO freigeschaltet, Kalender verbunden, Oberflaeche v142). **Abgehakt vom CEO 2026-10-27 -- Abnahme im laufenden Betrieb** (Anlegen per Telegram vom CEO bestaetigt)
- Ziel / Scope / Nicht-Scope: `core/aufgaben.py` (anlegen, aendern, erledigen/wieder oeffnen, loeschen = als geloescht
  markieren), Endpunkte `/api/aufgaben*`; Bereich „✅ To-dos“ (Liste nach Faelligkeit, Schnell-Eingabe oben, Bearbeiten,
  Abhaken, optional Kunde), Desktop/iPad/iPhone; Eintraege in „Zu erledigen“. Nicht-Scope: Teilen mit Team, Wiederholungen.
- Gate: Tests (Anlegen, Faelligkeit/Sortierung, Erledigen, Rechte), Gegenprobe; Darstellung Desktop, iPad (820 px),
  iPhone (402 px); Suite und Doku-Check gruen.
- Verifikation: in LUNA-OS ein To-do mit Datum anlegen, abhaken -> erwartet: erscheint/verschwindet in Liste und Kachel.
- Dry-Run: nicht noetig (neuer Speicher, keine Altdaten).
- Risiko / Rueckweg: Bereich per Schalter ausblendbar; Speicher append-only.
- Abhaengig von / Aufwand / Risiko: Q0 / mittel / niedrig.

## Etappe T2: Kalender-Erinnerung und Telegram-Erinnerung

- Status: gebaut 2026-10-27 (Kalendertermin 15 min in LUNAs Kalender, Titel „✅ …“, anlegen/verschieben/loeschen ohne Rueckfrage nur fuer eigene To-do-Termine; Bot-Thread prueft jede Minute, Telegram mit „✓ Erledigt / ⏰ +1 Std. / ⏰ morgen“, gilt erst als erinnert, wenn Telegram den Versand bestaetigt; Schalter `AUFGABEN_ERINNERUNG=0`). Deployt 2026-10-27 (4ce6308; live: `/api/aufgaben` antwortet, App „aufgaben“ fuer den CEO freigeschaltet, Kalender verbunden, Oberflaeche v142). **Abgehakt vom CEO 2026-10-27 -- Abnahme im laufenden Betrieb** (Anlegen per Telegram vom CEO bestaetigt)
- Ziel / Scope / Nicht-Scope: beim Anlegen mit Erinnerung Kalendertermin (LUNAs Kalender, CEO als Gast, Popup-Erinnerung),
  Termin-ID am To-do; Bot prueft alle 5 min faellige Erinnerungen und schickt sie per Telegram mit Knoepfen (Erledigt,
  +1 Std., morgen); Erledigen/Verschieben passt den Kalendertermin an bzw. loescht ihn. Nicht-Scope: fremde Termine.
- Gate: Tests (Termin angelegt/verschoben/geloescht, Telegram-Erinnerung genau einmal, Knoepfe), Gegenprobe.
- Verifikation: To-do mit Erinnerung in 10 min -> erwartet: Termin im Kalender auf dem iPhone, Telegram-Nachricht kommt
  an (Empfang beim CEO geprueft), „✓ Erledigt“ loescht den Termin.
- Dry-Run: Erinnerungslauf mit `--dry-run` (zeigt, was er schicken wuerde).
- Risiko / Rueckweg: Schalter `AUFGABEN_ERINNERUNG=0`; Kalender nur fuer eigene Termine.
- Abhaengig von / Aufwand / Risiko: T1 / mittel / niedrig.

## Etappe T3: To-do per Telegram-Nachricht

- Status: gebaut 2026-10-27 (Werkzeuge `todo_anlegen`, `todos_zeigen`, `todo_erledigen`, eigene Gruppe in der Werkzeugauswahl mit Stichwoertern To-do/Aufgabe/Erinner…; Erinnerung in der Vergangenheit abgewiesen; `todo_anlegen`/`todo_erledigen` sind Aktions-Werkzeuge -> nach Fremdtext mit Verdacht gesperrt; Antwort mit Knopf „↶ Rueckgaengig“ unter der Telegram-Antwort). Deployt 2026-10-27 (4ce6308; live: `/api/aufgaben` antwortet, App „aufgaben“ fuer den CEO freigeschaltet, Kalender verbunden, Oberflaeche v142). **Abgehakt vom CEO 2026-10-27 -- Abnahme im laufenden Betrieb** (Anlegen per Telegram vom CEO bestaetigt)
- Ziel / Scope / Nicht-Scope: Werkzeug `todo_anlegen` (und `todos_zeigen`, `todo_erledigen`) fuer LUNA: Titel, Faelligkeit,
  Erinnerung, optional Kunde aus freier Sprache (Datum relativ zu heute, Europe/Berlin); legt direkt an (Q0 Nr. 2), Antwort
  mit Zusammenfassung und „↶ Rueckgaengig“. Auch im LUNA-OS-Chat nutzbar. Nicht-Scope: Sprachnachrichten (folgen dem
  bestehenden Weg, falls Transkription vorhanden).
- Gate: Tests (Werkzeug mit festen Beispielen: „morgen 9 Uhr“, „Freitag“, „am 3.11. um 14:30“, ohne Datum; Rueckgaengig),
  Gegenprobe; Kosten je Nachricht im Kostenlog (Chat ~0,015 EUR).
- Verifikation: Telegram „To-do: Testaufgabe, heute in 15 Minuten erinnern“ -> erwartet: Antwort mit Zusammenfassung,
  To-do in LUNA-OS, Kalendertermin, Erinnerung nach 15 min.
- Dry-Run: Werkzeug ohne Speichern (Vorschau) in den Tests.
- Risiko / Rueckweg: falsch verstandenes Datum -> Zusammenfassung zeigt es sofort, „↶ Rueckgaengig“ bzw. in LUNA-OS aendern.
- Abhaengig von / Aufwand / Risiko: T1, T2 / klein bis mittel / niedrig.

## Dokumentationspflicht

`projekt_changelog.md`, `docs/datenfluesse.md` (neuer Speicher, Kalender, Telegram-Zeitplan), Backup-Liste,
`docs/entscheidungs-register.md` (Q0), `governance/zugriffs-policy.md` (Kalender-Schreiben ohne Rueckfrage fuer eigene
To-do-Termine).
