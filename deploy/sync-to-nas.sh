#!/usr/bin/env bash
#
# sync-to-nas.sh -- Code-Sync Mac -> Synology DS923+ (LUNA 24/7).
#
# Schiebt NUR den Code vom Mac auf die NAS (tar-over-ssh) und startet danach den
# Telegram-Container neu. Die LIVE-DATEN auf der NAS (Produktions-Datenquelle)
# werden bewusst NICHT angefasst: sie sind aus dem tar-Archiv ausgeschlossen, also
# nie im Transfer enthalten -> koennen nicht ueberschrieben werden. Es wird auch
# nichts geloescht (tar entpackt nur, loescht keine NAS-only-Dateien/Worktrees).
# LUNA schreibt auf der NAS live Changelog/Antraege/Memory/Budget; diese duerfen
# nie vom Mac ueberschrieben werden.
#
# Warum tar-over-ssh statt rsync? macOS liefert "openrsync", das die Remote-Shell
# (-e / RSYNC_RSH / ~/.ssh/config) nicht zuverlaessig fuer Key-Auth nutzt. tar-over-ssh
# nutzt das normale ssh (Key via ~/.ssh/config: Host luna-nas) und braucht keine
# Zusatz-Tools. Bei kleinem Repo (Code ohne .venv/.git) ist das schnell genug.
#
# Voraussetzungen:
#   - SSH-Key ~/.ssh/luna_nas + Eintrag in ~/.ssh/config (Host luna-nas -> NAS, IdentityFile)
#   - tar auf Mac (bsdtar) und NAS (GNU tar) vorhanden
#   - docker auf der NAS nur per sudo erreichbar (Daemon-Socket gehoert root)
#
# Nutzung:
#   deploy/sync-to-nas.sh                 # Code syncen + Container neu starten (restart)
#   deploy/sync-to-nas.sh --build         # Code syncen + Image neu bauen (bei Dep-Aenderung)
#   deploy/sync-to-nas.sh --no-restart    # nur Code syncen, Container nicht anfassen
#   deploy/sync-to-nas.sh --dry-run       # nur lokal anzeigen, welche Dateien ins tar kaemen
#
# Das NAS-sudo-Passwort wird zur Laufzeit abgefragt (read -s) oder aus der
# Umgebungsvariable NAS_SUDO_PW gelesen -- es steht NIE im Repo.
#
set -euo pipefail

# --- Konfiguration --------------------------------------------------------
NAS_SSH="luna-nas"                              # Alias aus ~/.ssh/config (Key + User + Host)
NAS_PATH="/volume1/docker/ki-unternehmen"
DOCKER="/usr/local/bin/docker"

# Repo-Root = Eltern-Ordner dieses Skripts (deploy/..).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --- Schutzliste: diese Pfade kommen NICHT ins tar-Archiv ------------------
# (Live-Daten der NAS-Produktion + lokale Artefakte/Secrets/Caches.)
TAR_EXCLUDES=(
  # --- NAS-Live-Daten (Produktions-Datenquelle, LUNA schreibt sie live) ---
  --exclude='./orchestrator/.env'
  --exclude='./.env'
  --exclude='./projekt_changelog.md'
  --exclude='./finance/budget.md'
  --exclude='./finance/kosten-log.jsonl'
  --exclude='./orchestrator/memory/log.jsonl'
  --exclude='./orchestrator/memory/log_dryrun.jsonl'
  --exclude='./antraege/log.jsonl'
  --exclude='./antraege/log_dryrun.jsonl'
  --exclude='./research/log.jsonl'
  --exclude='./watch/log.jsonl'
  --exclude='./notifications/log.jsonl'
  --exclude='./agenda/log.jsonl'
  --exclude='./aktivitaet/log.jsonl'
  --exclude='./brain/log.jsonl'
  --exclude='./trajektorien/log.jsonl'
  --exclude='./social/log.jsonl'
  --exclude='./investment/log.jsonl'
  --exclude='./investment/features.jsonl'
  --exclude='./orchestrator/channels/voice/selected_voice.json'
  # --- Git + virtuelle Umgebungen + Worktrees ---
  --exclude='./.git'
  --exclude='./.venv'
  --exclude='./venv'
  --exclude='./.worktrees'
  # --- Caches / Build / Logs / OS-Muell ---
  --exclude='*__pycache__*'
  --exclude='*.pyc'
  --exclude='*.egg-info'
  --exclude='./.pytest_cache'
  --exclude='./orchestrator/logs'
  --exclude='*.log'
  --exclude='./.xmind-build'
  --exclude='*.DS_Store'
)

# --- Argumente ------------------------------------------------------------
DO_BUILD=0
DO_RESTART=1
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --build)      DO_BUILD=1 ;;
    --no-restart) DO_RESTART=0 ;;
    --dry-run)    DRY_RUN=1 ;;
    -h|--help)    grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unbekanntes Argument: $arg" >&2; exit 2 ;;
  esac
done

# --- Dry-Run: nur lokal listen, was ins tar kaeme --------------------------
if [[ "$DRY_RUN" == "1" ]]; then
  echo ">> DRY-RUN -- Dateien, die uebertragen wuerden (NAS wird NICHT angefasst):"
  tar czf - --no-mac-metadata "${TAR_EXCLUDES[@]}" -C "$REPO_ROOT" . | tar tzf - | sort
  echo ">> DRY-RUN Ende."
  exit 0
fi

# --- Code-Sync per tar-over-ssh -------------------------------------------
echo ">> Code-Sync  ${REPO_ROOT}  ->  ${NAS_SSH}:${NAS_PATH}"
# tar entpackt auf der NAS NUR die im Archiv enthaltenen (Code-)Dateien; Live-Daten
# fehlen im Archiv -> bleiben unberuehrt. Nichts wird geloescht.
# --no-mac-metadata: keine macOS-xattrs ins Archiv (sonst harmlose tar-Warnungen auf der NAS).
tar czf - --no-mac-metadata "${TAR_EXCLUDES[@]}" -C "$REPO_ROOT" . \
  | ssh "$NAS_SSH" "tar xzf - -C ${NAS_PATH}"
echo ">> Code-Sync fertig."

if [[ "$DO_RESTART" == "0" ]]; then
  echo ">> --no-restart: Container nicht angefasst."
  exit 0
fi

# --- Container auf der NAS neu starten (braucht sudo) ----------------------
if [[ -n "${NAS_SUDO_PW:-}" ]]; then
  PW="$NAS_SUDO_PW"
else
  read -rs -p "NAS-sudo-Passwort (fuer Docker-Neustart): " PW; echo
fi

if [[ "$DO_BUILD" == "1" ]]; then
  echo ">> Image neu bauen + Container starten (docker compose up -d --build)..."
  REMOTE="cd ${NAS_PATH}/deploy && ${DOCKER} compose up -d --build"
else
  echo ">> Container neu starten (docker compose restart)..."
  REMOTE="cd ${NAS_PATH}/deploy && ${DOCKER} compose restart"
fi

# Passwort via stdin an sudo -S (nicht als Argument -> nicht in ps sichtbar).
printf '%s\n' "$PW" | ssh "$NAS_SSH" "sudo -S -p '' sh -c '${REMOTE}'"

echo ">> Status:"
printf '%s\n' "$PW" | ssh "$NAS_SSH" \
  "sudo -S -p '' ${DOCKER} ps --filter name=luna-telegram --format 'table {{.Names}}\t{{.Status}}'" 2>/dev/null || true
echo ">> Fertig."
