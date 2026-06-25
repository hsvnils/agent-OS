# LUNA 24/7 auf der Synology DS923+ (Telegram-Bot)

Ziel: LUNA von ueberall per Telegram erreichbar, unabhaengig vom Mac. Der Telegram-Bot braucht **nur
ausgehendes Internet** -- keine Portfreigabe, keine Domain, kein HTTPS-Zertifikat.

## Voraussetzungen
- DS923+ mit **Container Manager** (Docker) installiert (Paket-Zentrum).
- Empfehlung: **8 GB+ RAM** (Basis 4 GB reicht fuer den Bot meist, mehr ist ruhiger).
- Ausgehender Internetzugang (Telegram, Anthropic, Deepgram).

## Schritt 1 -- Repo auf die NAS legen
Repo z. B. nach `/volume1/docker/ki-unternehmen` kopieren (inkl. `.git/` und `orchestrator/.env`).
Optionen: per Git klonen/pullen (privates Repo: https://github.com/hsvnils/agent-OS.git) oder per
File Station / rsync. Wichtig: `orchestrator/.env` (mit den Keys + TELEGRAM_*) muss dabei sein -- sie ist
gitignored, also separat uebertragen.

## Schritt 2 -- Container bauen + starten
**Variante A (SSH, am schnellsten):**
```sh
cd /volume1/docker/ki-unternehmen/deploy
sudo docker compose up -d --build
sudo docker logs -f luna-telegram     # "Telegram-Bot bereit." erwarten
```
> Wird das Image auf einem Apple-Silicon-Mac gebaut: `--platform linux/amd64` nutzen. Am besten direkt auf
> der NAS bauen (ist x86-64).

**Variante B (Container Manager GUI):** Projekt anlegen -> Ordner `deploy/` mit `docker-compose.yml`
auswaehlen -> Build/Start. Volume-Pfad in der compose ggf. an deinen Ablageort anpassen.

## Schritt 3 -- Testen
LUNA auf Telegram schreiben (@luna_headofagents_bot). Sie antwortet -- jetzt 24/7, auch wenn der Mac aus ist.

## Code-Updates: Mac -> NAS syncen
Wenn am Mac weiterentwickelt wird, bringt das Skript `deploy/sync-to-nas.sh` den **Code** auf die NAS und
startet den Container neu. Es ueberschreibt **bewusst keine NAS-Live-Daten** (LUNA schreibt auf der NAS live
Changelog/Antraege/Memory/Budget -- die NAS ist die Produktions-Datenquelle): die Live-Dateien sind aus dem
Transfer ausgeschlossen, und es wird nichts geloescht.

```sh
deploy/sync-to-nas.sh             # Code syncen + Container restart (fragt NAS-sudo-Passwort)
deploy/sync-to-nas.sh --build     # zusaetzlich Image neu bauen (bei Dep-Aenderung, z. B. neue Python-Pakete)
deploy/sync-to-nas.sh --no-restart# nur Code syncen
deploy/sync-to-nas.sh --dry-run   # nur anzeigen, welche Dateien uebertragen wuerden (NAS unberuehrt)
```

Technik: **tar-over-ssh** (macOS „openrsync" nutzt -e/Key nicht zuverlaessig). Voraussetzung ist ein Eintrag in
`~/.ssh/config` (`Host luna-nas` -> NAS-IP + `IdentityFile ~/.ssh/luna_nas`), damit ssh den Key automatisch
nutzt. Das NAS-sudo-Passwort wird zur Laufzeit abgefragt (oder via `NAS_SUDO_PW`) und steht nie im Repo.
Geschuetzte Live-Daten: `orchestrator/.env`, `finance/budget.md`, `orchestrator/memory/log.jsonl`,
`antraege/log.jsonl`, `projekt_changelog.md` (+ `.git/`, `.venv/`, `.worktrees/`, Caches).

## Hinweise
- **Nur der Telegram-Kanal** laeuft hier. Der Voice-Browser von aussen braucht zusaetzlich HTTPS +
  Reverse-Proxy + WebRTC/TURN (spaeterer Schritt).
- **Execution (Phase 7)** auf der NAS arbeitet auf dem **NAS-Repo-Klon** (eigene Branches); Merges nach
  `main` dort bzw. via Git synchronisieren. Der Mac-Klon und der NAS-Klon sind getrennte Arbeitskopien.
- **Auto-Start:** `restart: unless-stopped` startet den Bot nach NAS-Neustart automatisch wieder.
- **Secrets:** `orchestrator/.env` bleibt privat (nie ins Git). Nur auf der NAS ablegen.
