#!/usr/bin/env bash
# Deploy Mac -> MACO470 (Cutter-Worker).
#
# Anders als die NAS (tar-over-ssh, weil dort Live-Stores geschuetzt werden muessen) laeuft der MACO470
# ueber **git pull**: das Repo ist public, der Rechner haelt keine schuetzenswerten Live-Daten und
# `orchestrator/.env` ist gitignored (bleibt also pro Maschine unberuehrt).
#
# Ablauf:  lokal committen (macht der Mensch) -> push -> ssh maco470 -> git pull im WSL-Ubuntu
#          -> Cutter-Worker neu starten.
#
# Nutzung:  deploy/sync-to-maco.sh [--no-restart] [--no-push]
set -euo pipefail

SSH_HOST="${MACO_SSH_HOST:-maco470}"          # ~/.ssh/config-Alias
WSL_DISTRO="${MACO_WSL_DISTRO:-Ubuntu-24.04}"
REPO_PFAD="${MACO_REPO:-~/ki-unternehmen}"
SERVICE="${MACO_SERVICE:-cutter-worker}"

RESTART=1
PUSH=1
for arg in "$@"; do
  case "$arg" in
    --no-restart) RESTART=0 ;;
    --no-push)    PUSH=0 ;;
    *) echo "Unbekanntes Argument: $arg"; exit 2 ;;
  esac
done

wsl_run() {  # Befehl im WSL-Ubuntu des MACO470 ausfuehren
  ssh "$SSH_HOST" "wsl -d $WSL_DISTRO -- bash -lc \"$1\"" 2>/dev/null | tr -d '\0\r'
}

if [ "$PUSH" -eq 1 ]; then
  echo ">> push nach origin/main ..."
  git push origin main
fi

echo ">> git pull auf dem MACO470 ..."
wsl_run "cd $REPO_PFAD && git pull --ff-only 2>&1 | tail -3"

if [ "$RESTART" -eq 1 ]; then
  echo ">> Cutter-Worker neu starten ..."
  # systemctl im WSL braucht sudo (der Nutzer luna hat NOPASSWD).
  wsl_run "sudo systemctl restart $SERVICE 2>&1; sleep 2; systemctl is-active $SERVICE"
else
  echo ">> --no-restart: Dienst nicht angefasst."
fi

echo ">> fertig."
