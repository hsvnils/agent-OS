#!/usr/bin/env bash
# Off-NAS-Backup der LIVE-Datenstores (Investment-Historie u. a.) vom NAS auf den Mac.
#
# Die Stores (investment/, antraege/, research/, notifications/, agenda/, aktivitaet/, watch/, brain/,
# finance/kosten-log, orchestrator/memory) sind bewusst gitignored + vom Code-Sync ausgeschlossen, damit ein
# Deploy sie nie ueberschreibt -> die "Wahrheit" liegt nur im NAS-Docker-Volume. Dieses Skript zieht eine
# zeitgestempelte Kopie auf den Mac (zweite, unabhaengige Kopie der append-only-Historie).
#
# WICHTIG: Ziel liegt **ausserhalb** von ~/Documents/~Desktop/~Downloads, damit der launchd-Automatismus
# ohne "Full Disk Access" laeuft (macOS-TCC blockt sonst den Zugriff). Default: ~/LUNA-Backups.
#
# Nutzung:  bash backup-from-nas.sh           (manuell)
#           BACKUP_DIR=/pfad bash backup-from-nas.sh
# Automatisch: via launchd (com.hanserautisch.investment-backup) taeglich 03:00.
set -uo pipefail

NAS_SSH="luna-nas"
NAS_PATH="/volume1/docker/ki-unternehmen"
DEST_BASE="${BACKUP_DIR:-$HOME/LUNA-Backups}"
STAMP="$(date +%Y-%m-%d_%H%M)"
DEST="${DEST_BASE}/${STAMP}"

FILES=(
  investment/log.jsonl
  antraege/log.jsonl
  research/log.jsonl
  notifications/log.jsonl
  agenda/log.jsonl
  aktivitaet/log.jsonl
  watch/log.jsonl
  brain/log.jsonl
  finance/kosten-log.jsonl
  orchestrator/memory/log.jsonl
)

mkdir -p "$DEST"
echo ">> [$(date '+%Y-%m-%d %H:%M:%S')] Backup ${NAS_SSH}:${NAS_PATH}  ->  ${DEST}"

REMOTE_LIST=""
for f in "${FILES[@]}"; do REMOTE_LIST="${REMOTE_LIST} ${f}"; done
ssh -o BatchMode=yes "$NAS_SSH" "cd ${NAS_PATH} && tar czf - \$(for f in ${REMOTE_LIST}; do [ -f \"\$f\" ] && echo \"\$f\"; done) 2>/dev/null" \
  | tar xzf - -C "$DEST" 2>/dev/null || true

FILES_OK=$(find "$DEST" -type f -name '*.jsonl' 2>/dev/null | wc -l | tr -d ' ')
LINES=$(find "$DEST" -type f -name '*.jsonl' -exec cat {} + 2>/dev/null | wc -l | tr -d ' ')
echo ">> ${FILES_OK} Stores, ${LINES} Events gesichert."

# Aufbewahrung: die NEUESTE Kopie enthaelt die KOMPLETTE append-only-Historie -> aeltere Snapshots sind
# redundant. Wir behalten die letzten KEEP Backups (kein Datenverlust, kein unbegrenztes Wachstum).
KEEP="${BACKUP_KEEP:-30}"
cd "$DEST_BASE" || exit 0
COUNT=$(ls -1d */ 2>/dev/null | wc -l | tr -d ' ')
if [ "$COUNT" -gt "$KEEP" ]; then
  ls -1d */ | sort | head -n "$((COUNT - KEEP))" | xargs rm -rf
  echo ">> Aufbewahrung: aelteste $((COUNT - KEEP)) Backups entfernt (behalten: ${KEEP}; neuestes hat die volle Historie)."
fi
