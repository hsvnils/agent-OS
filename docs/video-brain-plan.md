# Video-Second-Brain — durchsuchbares Clip-Gedaechtnis

> **Ziel:** Nicht mehr Ordner durchwuehlen. Jeder Clip bekommt eine **Clip-Karte** (Technik, Qualitaet,
> Gehoertes, Gesehenes). Dann findet man in Sekunden genau die Videos, die man gerade sucht — z. B.
> „Torjubel gegen St. Pauli, hochkant, mindestens 1080p, 4-8 Sekunden, gute Qualitaet".
>
> Der **manuelle Cutter** (siehe `docs/cutter-worker-plan.md`) wird dadurch nur noch ein **Konsument dieser
> Suche** — er sucht nicht mehr blind, sondern fragt das Archiv.

**Stand 2026-07-09:** **Stufe 1 ist gebaut** (`cutter/clip_brain.py`, gratis, kein LLM). Stufen 2-5 sind
geplant und laufen final auf dem **MACO470** (Batch-Schwerarbeit), passend zum zurueckgestellten Cutter-Worker.

---

## Die Clip-Karte (Zielbild)

| Feld | Inhalt | Stufe |
|---|---|---|
| `spiel`, `datei`, `pfad`, `sig` | Herkunft + Signatur-Cache | 1 |
| `breite`, `hoehe`, `format` | Aufloesung + **hoch / quer / quadrat** | 1 |
| `dauer`, `fps`, `codec`, `bitrate`, `hat_audio` | Technik | 1 |
| `lufs`, `stille_sek`, `schwarz_sek`, `schaerfe_yavg`, `szenen` | Qualitaets-Messungen | 1 |
| `qualitaet` (0-100) + `qualitaet_teil` | transparente Gesamtnote + Teilnoten | 1 |
| `transkript` | Gesagtes mit Zeitstempeln (whisper.cpp) | 2 |
| `tags`, `beschreibung`, `konfidenz` | Gesehenes **und Gehoertes** (Gemini Video) | 3 |
| `embedding` | fuer vage Fragen (optional) | 5 |

**Wichtige Erkenntnis:** Unser 360p-Proxy fuer Gemini behaelt den **Ton** (`-c:a aac` in
`gemini_video._downsample`). Gemini **hoert** die Clips also bereits. Pyro-Knall und Fangesang sind damit
grundsaetzlich erkennbar — der heutige Blocker ist nur das **8-Wort-Tag-Vokabular** und dass wir **keine
Beschreibung** speichern. Das loest Stufe 3.

---

## Stufen

### Stufe 1 — Technik + Qualitaet — **GEBAUT** (gratis, kein LLM, kein Upload)

`cutter/clip_brain.py`: persistenter, archivweiter Index ueber alle Spielordner.

- **Signatur-Cache** (mtime+groesse): jeder Clip wird genau **einmal** analysiert.
- **Resumable** (`--limit N`): nachts N neue Clips, bis das Archiv durch ist.
- **Graceful**: Metriken, die der ffmpeg-Build nicht kann, werden **uebersprungen** (Wert `None`), nicht geraten.
- Messungen: `ebur128` (Lautheit), `silencedetect` (Stille), `blackdetect` (Schwarzbild),
  `edgedetect`+`signalstats` (Schaerfe-Proxy). Szenen-Analyse ist **standardmaessig AUS**
  (`--mit-szenen` schaltet sie an) -- bei Fan-Einzelaufnahmen liefert sie fast immer 0 und ist der
  teuerste Schritt.
- **Ein Dekode je Clip**: alle Video-Messungen laufen in EINEM ffmpeg-Aufruf (`split` -> Schwarzbild +
  Schaerfe), Audio im selben Aufruf. Analyse-Fenster: die ersten **15 s** (`analyse_sek` steht in der Karte).
  Stille-/Schwarzbild-Anteile werden **auf dieses Fenster** normiert, nicht auf die volle Cliplaenge.
- **`ANALYSE_VERSION`**: aendert sich die Messung, werden alte Karten beim naechsten Lauf automatisch neu
  vermessen (inkrementell, resumable) -- der Index muss nicht weggeworfen werden.
- **Kein `-skip_frame nokey`**: geprueft und verworfen -- unser Material hat teils nur EINEN Keyframe je Clip
  (Schaerfe aus einem Einzelbild waere Zufall).
- **Qualitaets-Score 0-100**, gewichtet: Aufloesung .35, Schaerfe .25, Stille .15, Schwarzbild .15, Ton .10 —
  jede **Teilnote wird mitgespeichert**, damit man sieht, *warum* ein Clip schlecht bewertet ist.
- **Schaerfe wird RELATIV zum Archiv-Median bewertet** (Kantenenergie hat keinen universellen Massstab).
  Der Median steht im Index (`median_schaerfe`) und verfeinert sich, je mehr Clips indiziert sind. Objektive
  Maengel (Aufloesung, Stille, Schwarzbild, Ton) bleiben **absolut** bewertet -> Schrott bleibt Schrott.
  Nach jedem Lauf werden ALLE Noten neu gerechnet (billig, kein ffmpeg); `--nur-bewerten` macht das separat.

**An echtem Material geeicht (2026-07-09, erste 10 Clips des NAS-Archivs):** Schaerfe real ~9-38 (Median 18,7),
synthetische Testvideos nur ~0-6 -> die urspruengliche Absolut-Skala (2-8) saettigte und **spreizte nicht**
(alle Clips 89-100). Mit Relativ-Bewertung: **69-100**, Rangfolge plausibel (scharf+1080p oben, weich+720p unten).
Ein bewusst schlechter Testclip (320x240, stumm, schwarz) bleibt bei **12**.

Archiv-Stand: **1.185 Clips**. Auffaellig: **~80 % liegen quer (16:9)** -> fuer 9:16-Reels muss der Grossteil
beschnitten werden.

**Laufzeit (NAS, gemessen):** erster Lauf ~16-18 s je Clip (2 Video-Dekodes, 30-s-Fenster) -> 1.075 offene
Clips waeren ~5 h gewesen. Nach der Optimierung (1 Dekode + 15-s-Fenster, Werte identisch verifiziert):
**etwa halbe Zeit**, Richtung ~2,5 h fuers Restarchiv. Nachtlauf mit `--limit 300` -> in ~4 Naechten durch.

**Nachtlauf auf der NAS** (Code liegt per Mount schon im Container, **kein Neustart noetig**; `docker` braucht
auf der Synology `sudo`):

```
ssh -t luna-nas 'sudo /usr/local/bin/docker exec luna-os python -m cutter.clip_brain \
  --source /reelsrc --index /app/reel_work/state/clip_brain.json --limit 300'
```

### Stufe 2 — Transkript (gratis, CPU-hungrig)
`whisper.cpp` (haben wir, `cutter/transkription.py`) ueber alle Clips **mit Ton** -> `transkript` in die Karte.
Ergebnis: Volltextsuche ueber Gesagtes (Interviews, Rufe). **Auf der NAS langsam -> gehoert auf den MACO470.**

### Stufe 3 — KI-Inhalt (kostet -> CEO-Tor)
`gemini_video`: **Tag-Vokabular erweitern** (`pyro`, `gesang`, `torjubel`, `zweikampf`, `banner`, `nebel`, …)
**und zusaetzlich eine 1-2-Satz-Beschreibung + Konfidenz** je Clip speichern.
- Batchweise, nur ungetaggte, per Signatur gecacht -> jeder Clip kostet **einmal**.
- **Vorher CFO-Kostenvoranschlag** (Clip-Anzahl x Preis). Video an Gemini senden = externer Dienst (CEO-Tor).
- Ehrlich: 360p in 8er-Batches -> brauchbar, **nicht fehlerfrei**. Deshalb Konfidenz speichern und den CEO
  Tags korrigieren lassen (Feedback-Schleife: das Archiv wird mit der Nutzung besser).

### Stufe 4 — App „Clip-Archiv" (LUNA-OS)
Filterleiste (Spiel, Datum, Format, Min-Aufloesung, Dauer-Range, Qualitaet >= X, Tags) + Freitextsuche ueber
Beschreibung/Transkript/Tags + Vorschau. Tag-Korrektur durch den CEO.
Speicher-Ausbau: `clips`-Tabelle in Supabase statt JSON-Datei, sobald das Archiv gross ist.

### Stufe 5 — Cutter andocken + (optional) Embeddings
Der manuelle Cutter fragt das Archiv ab. Overall-Reels („alle Torjubel der Saison, nur Top-Qualitaet") werden
trivial. **Embeddings/pgvector** erst dann, wenn vage Fragen gebraucht werden — fuer harte Filter + Tags
unnoetig. Heute gibt es im Projekt **keine** Vektorsuche (`core/brain.py` sucht token-basiert).

---

## Grenzen (ehrlich)

- **Verwacklung wird nicht gemessen** — braucht `vidstabdetect`, in unserem ffmpeg-Build nicht vorhanden.
- Der Qualitaets-Score ist eine **Heuristik** (Gewichte oben), bewusst transparent und nachjustierbar.
- Schaerfe ist ein **Proxy** (Kantenenergie), kein echtes Schaerfemass.
- Stufe 2/3 sind rechen- bzw. kostenintensiv -> **MACO470**, nicht NAS.

## Governance

- Stufe 1/2: gratis, lokal, kein Upload.
- Stufe 3: **CEO-Tor** (Kosten + Upload an Gemini). CFO-Kostenvoranschlag vorab.
- Posten bleibt unveraendert CEO-Tor.
