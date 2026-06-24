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

## Hinweise
- **Nur der Telegram-Kanal** laeuft hier. Der Voice-Browser von aussen braucht zusaetzlich HTTPS +
  Reverse-Proxy + WebRTC/TURN (spaeterer Schritt).
- **Execution (Phase 7)** auf der NAS arbeitet auf dem **NAS-Repo-Klon** (eigene Branches); Merges nach
  `main` dort bzw. via Git synchronisieren. Der Mac-Klon und der NAS-Klon sind getrennte Arbeitskopien.
- **Auto-Start:** `restart: unless-stopped` startet den Bot nach NAS-Neustart automatisch wieder.
- **Secrets:** `orchestrator/.env` bleibt privat (nie ins Git). Nur auf der NAS ablegen.
