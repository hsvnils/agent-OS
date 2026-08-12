# MACO470-Roadmap — Integration des AOOSTAR MACO470

> **Lebendes Dokument.** Status je Phase wird hier gepflegt. Uebersteuert Teile von
> `docs/cutter-worker-plan.md` (siehe Entscheidung E1). Angelegt 2026-07-14 nach CEO-Planungsrunde.
>
> **Trainingslager: erledigt/gestrichen (CEO, 2026-08-12).** Der urspruengliche „Camp-Sprint" hat seinen
> Zweck erfuellt — der MACO470 ist eingerichtet und der Worker laeuft. Der **Camp-Modus bleibt als Funktion
> erhalten** (lokale `~/CutterInbox` fuer Material, das nicht auf der NAS liegt — funktioniert auch ohne
> Internet). Neue Prioritaet: **SMB-Mount**, danach **Video-Brain (M5)** und **lokales LLM (M6)**.

## IST-Stand der Einrichtung (2026-08-10)

**Fertig:** Windows 11 Pro (Build 26200) mit Rechnername `maco470`, feste IP **192.168.178.184**
(FritzBox-Reservierung), Energie/Auto-Login/Update-Fenster gesetzt · **OpenSSH-Server aktiv**, Key-Login
vom MacBook (`ssh maco470`, Key `~/.ssh/maco470`, User `nils`, Windows-`administrators_authorized_keys`
mit icacls-Rechten) · **WSL2 + Ubuntu 24.04** installiert, Benutzer `luna` (Default, NOPASSWD-sudo),
**systemd aktiv** · Pakete: git 2.43, **Python 3.12.3**, **ffmpeg 6.1.1**, build-essential, cmake ·
Repo geklont (`~/ki-unternehmen`, https, public), `.venv` + pytest -> **62 Cutter-Tests gruen**.
**Bereits vom CEO installiert (Vorgriff auf M6):** **Ollama** auf Windows (Port 11434, im LAN erreichbar)
mit **qwen3:30b-a3b** (MoE, kann *tools*+*thinking* -> der Kandidat fuer LUNAs Gehirn) und **gemma3:27b**
(nur completion). Beide Q4_K_M, ~17-18 GB.

**Gemessen:** clip_brain-Analyse eines 30-s-1080p-Testclips = **0,92 s** auf dem MACO470 (MacBook zum
Vergleich 0,64 s beim identischen Clip). Direkter NAS-Vergleich mit demselben Clip steht aus (braucht
sudo); die frueheren NAS-Zahlen (100 echte, meist kuerzere Clips in ~7 min = ~4,2 s/Clip) legen aber
einen deutlichen Vorsprung nahe. WSL sieht 24 Threads und ~14 GB RAM (WSL-Default = halber Host-RAM;
per `.wslconfig` anpassbar, spaeter gegen das Windows-native LLM abwaegen).

**Worker (2026-08-10):** `cutter/worker.py` gebaut + auf dem MACO470 deployt (`deploy/sync-to-maco.sh`),
**71 Cutter-Tests dort gruen**. systemd-Dienst `cutter-worker` angelegt + `enable`d (noch nicht gestartet).
`.env` mit Platzhalter-Passwort angelegt. **Camp-Modus verifiziert:** 5 Clips in `~/CutterInbox/camptest`
-> fertiges 16-s-Reel in **14 s**; die Bridge-401 (Platzhalter-Passwort) hat den Lauf **nicht** gestoppt —
genau das gewuenschte Offline-Verhalten.

**LIVE seit 2026-08-12:** Maschinen-Konto `maco470-worker` (Rolle content, Modul content_ops) angelegt,
Passwort in der `.env`; Mac-Watcher auf `CUTTER_QUEUE_POLL=0` umgestellt (Log bestaetigt „Queue-Polling:
AUS (MACO470 uebernimmt)"); systemd-Dienst `cutter-worker` **gestartet und aktiv**.
**Ende-zu-Ende verifiziert:** Job ueber die LUNA-OS-API eingereiht -> der MACO470 hat ihn binnen 20 s
geholt, in **11 s** ein 12,8-s-Reel aus 4 Clips gebaut und den Status **`done`** samt Clips/Dauer/Groesse
zurueckgemeldet. Testdaten entfernt.

**Autostart erledigt (2026-08-12):** Windows-Aufgabe `LUNA-WSL-Autostart` (bei Anmeldung ->
`wsl.exe -d Ubuntu-24.04 --exec /bin/true`) startet die WSL-Instanz; systemd bringt `cutter-worker`
automatisch mit hoch. **Getestet:** `wsl --shutdown` -> Aufgabe ausgeloest -> Worker war ohne Zutun
wieder `active`. Passwort am 2026-08-12 durch ein starkes ersetzt.

**Offen:** **SMB-Mount** (drvfs) fuer Themen-Reels aus dem NAS-Archiv (51 Ordner unter
`/volume1/SocialMediaTeam/Dropbox-Medien/Dateianfragen`) — braucht einen DSM-Benutzer mit Nur-Lese-Recht.

## Hardware (aus `docs/maco470-specs.pdf`, abgelegt 2026-07-14)

**AOOSTAR MACO470 (Modell Maco-L):** AMD **Ryzen AI 9 HX 470** (12 Kerne / 24 Threads, bis 5,2 GHz, Zen-5-
Klasse mit Radeon-iGPU) · **32 GB LPDDR5X-8000, VERLOETET** (nie aufruestbar) · **kein NPU** laut Datenblatt ·
M.2 NVMe x3 (bis 4 TB) · **2x 2,5-GbE-LAN**, Wi-Fi 7 · USB4 x2 · **Oculink (PCIe 4.0 x4)** = spaetere
eGPU-Option · 120-W-Netzteil (DC 5525 — **fuers Camp einpacken!**).

**Einordnung:** Fuer den **Video-Worker exzellent** (12 schnelle Kerne: ffmpeg/Whisper deutlich flotter als
NAS und MacBook-Nebenlast). Fuer das **lokale LLM (M6)** setzt der verloetete 32-GB-Speicher die Grenze —
Details im M6-Gate unten; die 120B-Klasse aus der ROADMAP ist damit NICHT machbar, die 7-30B-Klasse gut.

## Zielbild

Der **AOOSTAR MACO470** wird:
1. der **einzige Queue-Consumer** fuer manuelle Cutter-/Reel-Jobs (der grosse, vertagte Cutter-Worker),
2. die Maschine fuer **schwere Video-Brain-Stufen** (Whisper-Transkripte, spaeter Gemini-Tagging),
3. in einer spaeten Phase **lokaler LLM-Host** (LUNAs Gehirn/Execution ohne Cloud-Guthaben).

```
MacBook (Dev, Voice, Runner)      NAS DS923+ (24/7, zuhause)           MACO470 (Ubuntu, faehrt mit)
  - Entwicklung + git push          - luna-telegram, luna-os (Web)       - cutter-worker (systemd)
  - cutter.watch: nur noch          - Nightly-Reel 03:30 (bleibt!)       - pollt /api/cutter/queue
    lokale Inbox, KEIN Queue-Poll   - clip_brain-Scan 01:00 (bleibt!)    - SMB-Mount NAS (read-only)
  - reel.daily / invest-backup      - Supabase-Queue via LUNA-OS-API     - lokale CutterInbox (Camp)
                                                                         - spaeter: whisper, Gemini, LLM
```

**Feste CEO-Entscheidungen (2026-07-14, OS-Punkt abends revidiert):** **Windows 11 Pro BLEIBT** — der
Worker laeuft im **WSL2-Ubuntu** (Begruendung: CEO hat sonst nur Apple-Geraete und gewinnt so einen
Windows-Rechner; WSL2 statt Hyper-V-VM wegen dynamischem RAM — die 32 GB sind verloetet und muessen
spaeter auch das lokale LLM tragen; kein USB-Stick noetig = schnellster Weg zum Camp) · lokales LLM ja,
als eigene spaete Phase (laeuft dann **Windows-nativ** mit Vulkan auf der iGPU) · Clip-Quelle per
**SMB** von der NAS (kein Dropbox-Client) · im Trainingslager schneidet der MACO470 **nur manuell
uebergebenes Vor-Ort-Material**, die NAS arbeitet zuhause normal weiter.
**Bekannte WSL2-Haken (akzeptiert):** Autostart braucht Windows-Auto-Login + geplante Aufgabe;
Windows-Update-Neustarts werden in ein Nachtfenster gelegt; SMB laeuft ueber den Windows-Umweg (drvfs).

---

## Architektur-Entscheidungen

### E1 — Naechtliche Automatik bleibt DAUERHAFT auf der NAS
Der Nightly-Reel (DSM-Task 03:30, `docker exec luna-os … cutter.reel_daily --einreichen --schnell-index`)
und der clip_brain-Nachtscan (01:00) **bleiben unveraendert auf der NAS**. Das uebersteuert die alte Idee
aus `docs/cutter-worker-plan.md` („Automatik einfalten": Nightly als Queue-Job) — Begruendung: Der MACO470
faehrt ins Camp; waere die Automatik in der Queue, stuende sie dort still oder braeuchte einen zweiten
Worker (Claiming-Komplexitaet). Die NAS liest die Clips ausserdem lokal (kein SMB) und der clip_brain-Index
liegt bei den Web-Daten (`/app/reel_work/state/`), wo die spaetere Clip-Archiv-App ihn braucht.

### E2 — MACO470 = einziger Queue-Consumer (manuelle Jobs + Camp-Inbox)
Der neue `cutter/worker.py` pollt `GET /api/cutter/queue` und bearbeitet (a) manuelle Themen-Reel-Jobs
(Parameter als JSON im `note`-Feld, `typ=="reel"`) und (b) die lokale `~/CutterInbox` (Camp-Modus).
Fuer Themen-Reels braucht er den clip_brain-Index **nicht**: `reel_daily.lauf` baut seinen eigenen
`clip_index.json` (`schnell_index` = nur ffprobe — auch ueber SMB schnell genug). Kein Claiming (YAGNI,
ein Worker); bei einem kuenftigen zweiten Worker: Claiming nach `cutter-worker-plan.md` nachruesten.

### E3 — Eigene Zugaenge (Least Privilege, CISO-Fall-B)
- **LUNA-OS-Team-User `maco470-worker`** (role member, Modul content_ops) statt CEO-Credentials —
  revozierbar ohne CEO-Lockout, sauberes Audit. Anlage via `orchestrator/core/team_auth.py`.
- **SMB-User `maco470`** auf der NAS, **nur lesen**, nur Freigabe mit dem Medien-Ordner.
- Beide Zugaenge in `governance/zugriffs-policy.md` (Capabilities + Vergabe-Log) eintragen. CEO-Freigabe
  fuer neue Zugaenge erteilt mit dieser Roadmap (2026-07-14); CISO-konforme Dokumentation bei Anlage.

### E4 — Mac-Watcher verliert das Queue-Polling per Schalter
Neuer Env-Schalter `CUTTER_QUEUE_POLL=0` (Mac-`orchestrator/.env`); `cutter/watch.py` ueberspringt dann
den `bridge.offene_jobs()`-Block, behaelt aber Bridge-Melden + lokale Mac-Inbox. **Reihenfolge zwingend:
erst Mac abschalten, dann MACO470-Worker starten** — nie zwei Queue-Poller gleichzeitig.

### E5 — Deploy auf den MACO470 per `git pull`
Repo ist public; der MACO470 hat (anders als die NAS) keine schuetzenswerten Live-Stores und `.env` ist
gitignored. Deploy-Weg: MacBook pusht, MACO470 zieht — Mini-Skript `deploy/sync-to-maco.sh`
(push -> `ssh maco470 'cd ~/ki-unternehmen && git pull'` -> `sudo systemctl restart cutter-worker`).
Konsequenz: **git push wird Teil des Deploys.** NAS-Deploy bleibt unveraendert tar-over-ssh.

---

## Camp-Sprint (Tag 1–4 vor Abreise)

### Tag 1 — Vorbereitung + Worker-Code — Status: OFFEN
1. ~~USB-Stick/ISO~~ **ENTFAELLT** (OS-Entscheidung: Windows bleibt + WSL2 — keine Installationsmedien noetig).
2. **Windows vorbereiten** *(CEO, mit Claude-Anleitung)*: Rechnername `maco470`; **OpenSSH-Server**
   aktivieren (Einstellungen -> System -> Optionale Features) fuer SSH vom MacBook; Energie: nie
   schlafen (Netzbetrieb); Windows-Update: Nutzungszeit so legen, dass Neustarts nachts ~04:30 passieren
   (nach dem NAS-Reel-Job waere egal — der laeuft ja auf der NAS); **Auto-Login** aktivieren (netplwiz)
   fuer den unbeaufsichtigten Autostart; FritzBox: DHCP-Reservierung (feste IP notieren).
3. **Worker-Code bauen** (auf dem MacBook, ohne MACO470 testbar): *(Claude)*
   - `cutter/reel_select.py`: Thema „Torjubel" (`tor`,`jubel`) + `thema_by_name()` + `MANUELLE_THEMEN`
   - `cutter/reel_daily.py`: `lauf(thema_name, alle_spiele, min_dauer=15)` + CLI (Logik der revertierten
     Referenz-Commits `5001c61`/`57b4065` neu umgesetzt, nicht cherry-picken)
   - **neu `cutter/worker.py`** (Muster `cutter/watch.py`): Queue-Zweig (note-JSON `typ=reel` -> sofort
     `melden(running)` = De-facto-Claim -> `reel_daily.lauf` -> `reel_einreichen` -> done/failed) +
     **Inbox-Zweig** (`~/CutterInbox`, offline-robust: Bridge schluckt Fehler, Reels bleiben in der Outbox)
   - `cutter/watch.py`: E4-Schalter
   - Web: `POST /api/cutter/reel` (legt NUR queued-Job an), Cutter-UI (Thema / Einzelspiel-Overall /
     Min-Max-Laenge), Reels-Ablehnen -> Rueckfrage „neues erstellen?" -> `{neu:true}`
   - `deploy/sync-to-maco.sh` · Tests · Changelog · Commit/Push

### Tag 2 — WSL2-Ubuntu + Zugriff — Status: OFFEN
1. **WSL2 installieren** (PowerShell als Administrator): `wsl --install -d Ubuntu-24.04` -> Neustart ->
   Ubuntu-User `luna` anlegen. Danach in der Ubuntu-Shell **systemd aktivieren**:
   `/etc/wsl.conf` mit `[boot]\nsystemd=true`, dann `wsl --shutdown` (einmalig) und neu oeffnen.
2. **BIOS: „Restore on AC Power Loss = Power On"** (Stromausfall-Recovery; AOOSTAR-BIOS via Entf beim Start).
3. **SSH vom MacBook**: Ziel ist der Windows-OpenSSH-Dienst (Tag 1), von dort per `wsl` in Ubuntu.
   MacBook: `ssh-keygen -t ed25519 -f ~/.ssh/maco470` + Key in Windows `authorized_keys`;
   `~/.ssh/config`-Eintrag `Host maco470` (HostName = feste IP).
4. Pakete im WSL-Ubuntu: `sudo apt update && sudo apt install -y git python3-venv python3-pip ffmpeg
   build-essential cmake`. (Kein avahi/cifs-utils noetig — mDNS macht Windows, SMB laeuft ueber drvfs.)
5. Repo klonen (`git clone https://github.com/hsvnils/agent-OS.git ~/ki-unternehmen`), `.venv` anlegen,
   `pytest cutter/tests` gruen.
6. **Minimal-`.env`** (`~/ki-unternehmen/orchestrator/.env`, NUR das Noetige — Least Privilege):
   `LUNA_OS_URL=https://os.hanserautisch.synology.me` · `LUNA_OS_USER=maco470-worker` + neues Passwort
   (Team-User vorher anlegen, E3) · `REEL_SOURCE=/mnt/nas-clips` · `REEL_OUTBOX`/`REEL_STATE` lokal (ext4,
   NICHT unter /mnt/c — Performance).
7. **Autostart-Kette**: Windows-Auto-Login (Tag 1) + geplante Aufgabe „Bei Anmeldung":
   `wsl -d Ubuntu-24.04 --exec /bin/true` haelt die Instanz mit systemd am Leben -> der
   cutter-worker-Service (Tag 3) startet darin automatisch.

### Tag 3 — Worker live + Ende-zu-Ende-Test — Status: OFFEN
1. systemd-Service `/etc/systemd/system/cutter-worker.service` (User luna, WorkingDir Repo,
   `ExecStart=.venv/bin/python -m cutter.worker`, `Restart=always`, `After/Wants=network-online.target`).
2. **E4-Reihenfolge:** Mac-`.env` `CUTTER_QUEUE_POLL=0` + watch neu laden -> DANN
   `sudo systemctl enable --now cutter-worker` auf dem MACO470.
3. **Camp-Test (Sprint-Erfolgskriterium):** Ordner mit Test-Clips per
   `scp -r <ordner> maco470:~/CutterInbox/test1/` -> Reel entsteht, Telegram-Meldung kommt, Reel erscheint
   in LUNA-OS zur Freigabe (Einreichen ueber die externe HTTPS-URL — funktioniert auch vom Camp-WLAN).
4. Web-Test manueller Themen-Reel (braucht SMB; sonst Tag 4 / nach dem Camp).
5. Falls Zeit — **SMB via drvfs**: DSM-User `maco470` (nur lesen, nur Medien-Freigabe) anlegen;
   Zugangsdaten in der Windows-Anmeldeinformationsverwaltung hinterlegen; im WSL-Ubuntu per fstab-Zeile
   `\\192.168.178.129\SocialMediaTeam\Dropbox-Medien\Dateianfragen /mnt/nas-clips drvfs ro,noatime,uid=1000,gid=1000,nofail 0 0`
   (nofail -> bootet im Camp ohne NAS sauber). Umlaut-Check der Spielordner!

### Tag 4 — Puffer + Abreise — Status: OFFEN
Reboot-Test ohne LAN-Kabel (nofail greift), `journalctl -u cutter-worker` sauber, Checkliste unten.

## Mobil-/Offline-Betrieb (frueher „Trainingslager-Checkliste")

Bleibt als **Funktion** erhalten, auch wenn das Camp durch ist — nuetzlich fuer jedes Material, das nicht
im NAS-Archiv liegt:
- MACO470 mitnehmen (Netzteil + LAN-Kabel), im fremden Netz per `maco470.local` erreichbar (Windows-mDNS);
  Auto-Login startet WSL + Worker selbsttaetig.
- Material uebergeben: `scp -r <ordner> maco470:~/CutterInbox/<name>/` (oder USB) -> der Worker schneidet
  automatisch, sobald der Ordner „ruhig" ist, und meldet per Telegram.
- **Mit** Internet: Queue + Einreichen laufen ueber die externe URL. **Ohne** Internet: der Schnitt laeuft
  trotzdem, fertige Reels bleiben in der Outbox (verifiziert 2026-08-10).
- Ohne NAS-Verbindung gibt es keine Themen-Reels aus dem Archiv (erwartet — dafuer braucht es den SMB-Mount).

## Weiterer Ausbau

- **M3-Rest — SMB finalisieren** (falls im Sprint nicht geschafft) -> manuelle Themen-Reels
  („Torjubel ueber alle Spiele") voll nutzbar.
- **M5 — Video-Brain-Schwerarbeit:** whisper.cpp aus Source (`cmake -B build && cmake --build build`),
  Modell `ggml-large-v3-turbo` nach `~/whisper-models` (Deutsch; `cutter/transkription.py` findet Binary im
  PATH + Modell via `WHISPER_CPP_MODEL`/`~/whisper-models`). Neues `cutter/transkript_batch.py` (resumable,
  Signatur-Cache — Muster `clip_brain.py`) per systemd-Timer nachts -> **Stufe 2**. Danach **Stufe 3**
  (Gemini: TAG_VOKABULAR + `pyro`,`gesang`,… + 1-2-Satz-Beschreibung) **hinter CEO-Tor** mit
  CFO-Kostenvoranschlag (~6–18 EUR einmalig). **Stufen 4/5** (Clip-Archiv-App mit Supabase-`clips`-Tabelle,
  Cutter fragt Archiv) nach `docs/video-brain-plan.md`; Index-Zusammenfuehrung ueber die LUNA-OS-API.
- **M6 — Lokales LLM (Gate am 2026-07-14 mit Specs aufgeloest):** 32 GB verloetet + kein NPU heisst
  **ehrlich**: Die in der ROADMAP anvisierte GPT-OSS-**120B**-Klasse ist auf DIESEM Geraet nicht machbar
  (braeuchte 64-128 GB). Realistisch und gut: **~7-14B komfortabel** (Q4, 4-9 GB), **~20-30B machbar**
  — Kandidaten: **gpt-oss-20b** (~13 GB), **Qwen3-Coder-30B-A3B** (MoE, nur ~3,3B aktiv -> flott, ~18 GB
  Q4, knapp aber realistisch), Mistral-Small-24B. Das reicht fuer LUNAs Gehirn (Chat/Routing/Fachagenten)
  und einfache Execution-Aufgaben; fuer die 120B-Klasse bleibt spaeter die **Oculink-eGPU** oder separate
  Hardware. Serving laeuft **Windows-nativ** (OS-Entscheidung: Windows+WSL2): Ollama-Windows oder
  LM Studio mit **Vulkan** auf der Radeon-iGPU (unter Windows gut unterstuetzt; WSL2 hat keinen
  brauchbaren iGPU-Zugriff) — mit kleinem Modell benchmarken, iGPU-Speicherzuteilung im BIOS beachten
  (teilt sich die 32 GB mit System und WSL — WSL-RAM-Cap via `.wslconfig` setzen, z. B. 8 GB). Anbindung Chat/Fachagenten trivial ueber den vorhandenen
  OpenAI-kompatiblen FallbackBackend (`base_url=http://maco470:11434/v1`); **Execution** braucht den
  Nicht-CLI-Ausfuehrungs-Agenten (separates Vorhaben, ROADMAP). Nur LAN binden, keine
  FritzBox-Portfreigabe (CISO-Notiz).

## Fallstricke (beim Bau beachten)

- `reel_daily._stage`: Symlinks liegen im lokalen tmp, ffmpeg liest ueber SMB — ok auf GbE. **OUTBOX/STATE
  muessen lokal bleiben**, nur SOURCE ist SMB.
- `/api/reel/einreichen` = base64-Upload (Timeout 180 s) — bei langen Reels Reverse-Proxy-Body-Limit pruefen.
- **Umlaute ueber CIFS (NFC/NFD)** beim Spielordner-Matching — ggf. `unicodedata.normalize("NFC", …)` in
  `reel_daily`/`reel_source`.
- **Nie zwei Queue-Poller** (E4-Reihenfolge einhalten).
- `.env` bleibt pro Maschine, nie syncen (gitignored; NAS-Sync excludiert sie ohnehin).

## Status-Uebersicht

| Phase | Inhalt | Status |
|---|---|---|
| M1 | Windows vorbereiten (Rechnername/SSH/Energie/Auto-Login/feste IP) | **ERLEDIGT 2026-08-10** |
| M2 | WSL2-Ubuntu + systemd + SSH-Kette + Repo + Tests | **ERLEDIGT 2026-08-10** |
| M4a | Worker-Code (`cutter/worker.py`, Themen-Reels, Web-UI, E4-Schalter) | **ERLEDIGT 2026-08-10** |
| M4b | Dienst + Offline-/Inbox-Modus verifiziert | **ERLEDIGT 2026-08-10** |
| M4c | Queue-Betrieb live (Maschinen-Konto, Mac-Poll aus, E2E-Test) | **ERLEDIGT 2026-08-12** |
| M4d | Autostart-Kette (Windows-Aufgabe -> WSL -> systemd) | **ERLEDIGT 2026-08-12** |
| **M3** | **SMB-Mount (drvfs) + Themen-Reels Ende-zu-Ende** | **NAECHSTER SCHRITT** (braucht DSM-Benutzer) |
| M5 | Video-Brain: Stufe 2 (Whisper) / 3 (Gemini, CEO-Tor) / 4-5 (Archiv-App) | OFFEN |
| M6 | Lokales LLM (Ollama laeuft bereits mit qwen3:30b-a3b — Anbindung offen) | OFFEN |
