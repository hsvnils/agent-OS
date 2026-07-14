# MACO470-Roadmap — Integration des AOOSTAR MACO470

> **Lebendes Dokument.** Status je Phase wird hier gepflegt. Uebersteuert Teile von
> `docs/cutter-worker-plan.md` (siehe Entscheidung E1). Angelegt 2026-07-14 nach CEO-Planungsrunde.
>
> **Zeitdruck:** In ~4 Tagen (ca. 2026-07-18) geht es ins **Trainingslager — der MACO470 faehrt mit** und
> muss dort Vor-Ort-Material schneiden koennen. Deshalb zuerst der Camp-Sprint, alles andere danach.

## Zielbild

Der **AOOSTAR MACO470** (AMD-Mini-PC; Specs-PDF folgt unter `docs/maco470-specs.pdf`) wird:
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

**Feste CEO-Entscheidungen (2026-07-14):** Ubuntu-Neuinstallation (Windows weg) · lokales LLM ja, als
eigene spaete Phase · Clip-Quelle per **SMB-Mount** von der NAS (kein Dropbox-Client) · im Trainingslager
schneidet der MACO470 **nur manuell uebergebenes Vor-Ort-Material**, die NAS arbeitet zuhause normal weiter.

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
1. **USB-Stick >= 8 GB besorgen** (~6 EUR, lokal kaufen; CEO-Tor Geld trivial, Changelog). *(CEO)*
2. Am MacBook: **Ubuntu Server 24.04 LTS ISO** laden (ubuntu.com/download/server, ~2,7 GB) +
   **balenaEtcher** (gratis, grafisch) -> Stick flashen („Flash from file" -> ISO -> Stick -> Flash). *(CEO)*
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

### Tag 2 — Ubuntu + Zugriff — Status: OFFEN
1. Ubuntu Server 24.04 installieren: Boot vom Stick (AOOSTAR: Boot-Menue **F7**/Entf), Tastatur German,
   LAN-Kabel, ganze Platte (Windows wird ueberschrieben — gewollt), User `luna`, Hostname `maco470`,
   **„Install OpenSSH server" ANHAKEN**. Danach Stick ziehen, Neustart.
2. **BIOS: „Restore on AC Power Loss = Power On"** (headless-Betrieb, Stromausfall-Recovery).
3. **FritzBox**: Heimnetz -> Netzwerk -> `maco470` -> „immer die gleiche IPv4-Adresse zuweisen". IP notieren.
4. Vom MacBook: `ssh-keygen -t ed25519 -f ~/.ssh/maco470` + `ssh-copy-id`, `~/.ssh/config`-Eintrag
   `Host maco470`; danach Haertung (`PasswordAuthentication no`, `PermitRootLogin no`).
5. Pakete: `sudo apt install -y git python3-venv python3-pip ffmpeg cifs-utils build-essential cmake
   avahi-daemon` (avahi -> im Camp als `maco470.local` findbar). Suspend maskieren
   (`systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target`).
6. Repo klonen (`git clone https://github.com/hsvnils/agent-OS.git ~/ki-unternehmen`), `.venv` anlegen,
   `pytest cutter/tests` gruen.
7. **Minimal-`.env`** (`~/ki-unternehmen/orchestrator/.env`, NUR das Noetige — Least Privilege):
   `LUNA_OS_URL=https://os.hanserautisch.synology.me` · `LUNA_OS_USER=maco470-worker` + neues Passwort
   (Team-User vorher anlegen, E3) · `REEL_SOURCE=/mnt/nas-clips` · `REEL_OUTBOX`/`REEL_STATE` lokal.

### Tag 3 — Worker live + Ende-zu-Ende-Test — Status: OFFEN
1. systemd-Service `/etc/systemd/system/cutter-worker.service` (User luna, WorkingDir Repo,
   `ExecStart=.venv/bin/python -m cutter.worker`, `Restart=always`, `After/Wants=network-online.target`).
2. **E4-Reihenfolge:** Mac-`.env` `CUTTER_QUEUE_POLL=0` + watch neu laden -> DANN
   `sudo systemctl enable --now cutter-worker` auf dem MACO470.
3. **Camp-Test (Sprint-Erfolgskriterium):** Ordner mit Test-Clips per
   `scp -r <ordner> maco470:~/CutterInbox/test1/` -> Reel entsteht, Telegram-Meldung kommt, Reel erscheint
   in LUNA-OS zur Freigabe (Einreichen ueber die externe HTTPS-URL — funktioniert auch vom Camp-WLAN).
4. Web-Test manueller Themen-Reel (braucht SMB; sonst Tag 4 / nach dem Camp).
5. Falls Zeit — **SMB-Mount**: DSM-User `maco470` (nur lesen, nur Medien-Freigabe); fstab-cifs mit
   `credentials=/etc/cifs/nas-clips.cred,ro,uid=1000,gid=1000,iocharset=utf8,vers=3.0,noserverino,soft,nofail,_netdev,x-systemd.automount,x-systemd.idle-timeout=60`
   -> bootet im Camp ohne NAS sauber, mountet zuhause automatisch. Umlaut-Check der Spielordner!

### Tag 4 — Puffer + Abreise — Status: OFFEN
Reboot-Test ohne LAN-Kabel (nofail greift), `journalctl -u cutter-worker` sauber, Checkliste unten.

## Trainingslager-Checkliste

**Abreise:** `sudo poweroff` · Netzteil + LAN-Kabel einpacken · Camp-Netz planen (MacBook-Hotspot reicht;
MACO470 + MacBook ins selbe Netz) · zuhause nichts umstellen (NAS-Automatik laeuft weiter, E1).
**Im Camp:** MACO470 booten, per `maco470.local` erreichbar (avahi) · Vor-Ort-Material: iPhone -> MacBook ->
`scp -r <ordner> maco470:~/CutterInbox/<name>/` (oder USB) -> Worker schneidet, meldet per Telegram ·
mit Internet funktionieren Queue + Einreichen ueber die externe URL; ohne Internet bleiben fertige Reels
in der Outbox liegen (erwartet) · SMB fehlt im Camp -> keine Themen-Reels aus dem Archiv (erwartet).
**Rueckkehr:** LAN-Kabel rein, booten, `ls /mnt/nas-clips` (Automount), `systemctl status cutter-worker`.

## Nach dem Camp

- **M3-Rest — SMB finalisieren** (falls im Sprint nicht geschafft) -> manuelle Themen-Reels
  („Torjubel ueber alle Spiele") voll nutzbar.
- **M5 — Video-Brain-Schwerarbeit:** whisper.cpp aus Source (`cmake -B build && cmake --build build`),
  Modell `ggml-large-v3-turbo` nach `~/whisper-models` (Deutsch; `cutter/transkription.py` findet Binary im
  PATH + Modell via `WHISPER_CPP_MODEL`/`~/whisper-models`). Neues `cutter/transkript_batch.py` (resumable,
  Signatur-Cache — Muster `clip_brain.py`) per systemd-Timer nachts -> **Stufe 2**. Danach **Stufe 3**
  (Gemini: TAG_VOKABULAR + `pyro`,`gesang`,… + 1-2-Satz-Beschreibung) **hinter CEO-Tor** mit
  CFO-Kostenvoranschlag (~6–18 EUR einmalig). **Stufen 4/5** (Clip-Archiv-App mit Supabase-`clips`-Tabelle,
  Cutter fragt Archiv) nach `docs/video-brain-plan.md`; Index-Zusammenfuehrung ueber die LUNA-OS-API.
- **M6 — Lokales LLM (Entscheidungs-Gate):** Specs-PDF auswerten (RAM -> Modellklasse: 32 GB ~7-20B ·
  64 GB ~30-70B · 96-128 GB unified -> GPT-OSS-120B-Klasse laut ROADMAP). Serving: Ollama (einfachster
  Betrieb) vs. llama.cpp-Server (AMD-iGPU: **Vulkan** oft robuster als ROCm) — am Gate benchmarken.
  Anbindung Chat/Fachagenten trivial ueber den vorhandenen OpenAI-kompatiblen FallbackBackend
  (`base_url=http://maco470:11434/v1`); **Execution** braucht den Nicht-CLI-Ausfuehrungs-Agenten
  (separates Vorhaben, ROADMAP). Nur LAN binden, keine FritzBox-Portfreigabe (CISO-Notiz).

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
| Tag 1 | Stick/ISO + Worker-Code | OFFEN |
| Tag 2 | Ubuntu + SSH + Repo | OFFEN |
| Tag 3 | Worker live + Camp-Test (+ SMB falls Zeit) | OFFEN |
| Tag 4 | Puffer + Abreise-Checkliste | OFFEN |
| M3-Rest | SMB finalisieren + Themen-Reels E2E | OFFEN (nach Camp) |
| M5 | Video-Brain Stufe 2 (Whisper) / 3 (Gemini, CEO-Tor) / 4-5 (Archiv-App) | OFFEN (nach Camp) |
| M6 | Lokales LLM (Gate: Specs-PDF) | OFFEN (nach Camp) |
