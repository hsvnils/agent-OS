# Cutter-Umbau + Manueller Cutter — Plan (zurueckgestellt bis MACO470)

> **UPDATE 2026-07-14: Der MACO470 ist da.** Die Umsetzung laeuft jetzt nach **`docs/maco470-roadmap.md`**.
> Abweichung: Der Punkt „Automatik einfalten" (Nightly-Reel als Queue-Job, Umsetzungsschritt 5) **entfaellt**
> — die naechtliche Automatik bleibt dauerhaft auf der NAS (Begruendung: Trainingslager-Betrieb, siehe
> Roadmap-Entscheidung E1). Der Rest dieses Plans (Queue-Worker, manueller Cutter, Min 15 s) gilt weiter.

> **Status: ZURUECKGESTELLT (CEO-Entscheidung 2026-07-09).** Wird **final gebaut, sobald der MACO470
> eingetroffen ist** — dann laeuft die ganze Videoverarbeitung ohnehin auf dem MACO470 statt auf der NAS.
> Bis dahin bleibt alles wie es ist (kein manueller Cutter, Automatik-Reel unveraendert per Nightly).
>
> Ein erster Wurf wurde am 2026-07-09 gebaut und **wieder revertiert** (nicht deployt): commits `5001c61`
> (Feature) und `57b4065` (NAS-Variante) — als Referenz in der Git-Historie. Beim finalen Bau bitte diesen
> Plan umsetzen (Worker-Architektur), nicht 1:1 die reverteten Commits.

## Ziel

1. **Manueller Cutter** in der Weboberflaeche: gezielt Reels anfordern mit
   - **Thema** (heute schon getaggt: Torjubel, Tore & Highlights, Beste Momente, Fan-Stimmung, Emotionen pur;
     **Pyro + Fangesang spaeter** — brauchen neues KI-Tag-Vokabular `pyro`/`gesang` + einmaliges Re-Tagging;
     Fangesang ist audio-lastig, Video-KI erkennt es schlechter),
   - **Einzelspiel ODER ueber alle Spiele** (Overall, nur mit Qualitaetskriterien),
   - **Min-/Max-Laenge** (global Mindestlaenge **15 s**).
2. **Ablehnen -> „neues erstellen?"**: nach Ablehnung eines Reels Rueckfrage; bei Ja direkt ein neues (gleiches
   Spiel/Thema) bauen.
3. **Mindestlaenge 15 s** global erzwingen (zu kurze Reels werden nicht eingereicht).
4. **Eigener Cutter-Worker**: schweres Schneiden (ffmpeg/whisper/Gemini) **raus aus dem interaktiven
   OS-/Web-Container** — sonst wird die Oberflaeche waehrend eines Baus traege. Das gilt fuer den **manuellen
   UND** den **automatischen naechtlichen** Reel.

## Architektur (Queue-basierter Worker)

Die Warteschlange existiert bereits: `luna_cutter_jobs` (Supabase) + `GET /api/cutter/queue` +
`POST /api/cutter/report`. Der heutige Mac-`cutter.watch` ist im Prinzip schon so ein Worker.

```
Weboberflaeche (luna-os)         Cutter-Worker (eigener Prozess/Container)
  - reiht Job NUR ein     --->     - pollt /api/cutter/queue
    (Thema/Spiel/Laenge)           - baut Reel (reel_daily.lauf) / schneidet Ordner
  - zeigt Status/Reels             - reicht Reel zur Freigabe ein (reel_store / API)
                                   - meldet Status via /api/cutter/report
```

- **Web reiht nur ein** (schnell, kein Bauen im Web-Prozess). Reel-Parameter als JSON im `note`-Feld des Jobs
  (typ=="reel", thema, spiel, alle_spiele, min_dauer, max_dauer) — so bleibt das feste Job-Schema unangetastet.
- **Automatik einfalten**: der Nacht-Reel wird nicht mehr per `docker exec luna-os …` gebaut, sondern
  **um 03:30 als Job eingereiht** (durch den OS-Scheduler oder einen Mini-Cron) und vom Worker abgearbeitet.
  Damit ist ALLES Schneiden an einer Stelle.
- **Ein Worker, kein Doppel-Bau**: nur EIN Worker darf die Queue abarbeiten (sonst greifen zwei denselben Job).
  Falls uebergangsweise zwei laufen -> simples „Job-Claiming" (Status queued -> claimed(worker_id) -> done).

## MACO470-Migration (der eigentliche Grund fuers Zurueckstellen)

Weil die Queue ueber die LUNA-OS-API entkoppelt ist, ist der Worker **ortsunabhaengig**:
- **Heute (bliebe NAS):** Worker als Container auf der Synology (gleiches Image, hat ffmpeg; + `/reelsrc`-Mount).
- **Ab MACO470:** derselbe Worker laeuft auf dem MACO470; NAS-Worker aus. **Web unveraendert.**

-> Deshalb **jetzt nicht bauen**: der Worker wuerde direkt auf dem MACO470 aufgesetzt, nicht erst auf der NAS.
**Es gibt keinen Mac-Cutter-Bedarf im alten Sinn** (CEO: „Ich brauche keinen MAC Cutter") — gemeint ist der
neue MACO470-Worker, nicht der bisherige Mac-`cutter.watch`.

## Umsetzungsschritte (fuer den finalen Bau)

1. **reel_select.py**: Thema „Torjubel" (Tags `tor`,`jubel`) + `thema_by_name()` + `MANUELLE_THEMEN`.
2. **reel_daily.lauf(...)**: Parameter `thema_name`, `alle_spiele` (Index ueber ALLE Spiele), `min_dauer=15`
   (zu kurz -> nicht einreichen). CLI-Args `--thema/--alle-spiele/--min-dauer`.
3. **Worker** (`cutter/worker.py` o. ä., basierend auf `cutter.watch`): pollt Queue, erkennt Reel-Jobs
   (note-JSON `typ==reel`), baut via `reel_daily.lauf`, reicht ein, meldet Status. Laeuft auf dem MACO470.
4. **Web**: `POST /api/cutter/reel` legt NUR einen `queued`-Job an (kein Bauen im Web!). UI: „Manueller
   Reel-Auftrag" (Thema-Dropdown, Einzelspiel/Overall, Min/Max) in der Cutter-App. Ablehnen fragt
   „neues erstellen?" -> `POST /api/reel/{id}/ablehnen {neu:true}` reiht neuen Job ein.
5. **Automatik**: Nacht-Job auf „Enqueue statt docker exec" umstellen; Worker baut.
6. **Spaeter**: Pyro/Fangesang — Tag-Vokabular in `gemini_video.TAG_VOKABULAR` erweitern + Clips neu taggen
   (`reel_tag`), dann Themen ergaenzen.

## Wichtig

- **Kein Bauen im Web-Prozess** (das war der erste, verworfene Ansatz). Web = nur einreihen.
- **Posten bleibt CEO-Tor.** Der Worker reicht nur zur **Freigabe** ein.
