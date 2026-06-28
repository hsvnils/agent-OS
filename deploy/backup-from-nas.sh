#!/usr/bin/env bash
# Off-NAS-Backup der LIVE-Datenstores (Investment-Historie u. a.) vom NAS auf den Mac.
#
# Die Stores (investment/, antraege/, research/, notifications/, agenda/, aktivitaet/, watch/, brain/,
# finance/kosten-log) sind bewusst gitignored + vom Code-Sync ausgeschlossen, damit ein Deploy sie nie
# ueberschreibt. Damit liegt die "Wahrheit" aber NUR im NAS-Docker-Volume. Dieses Skript zieht eine
# zeitgestempelte Kopie auf den Mac -> zweite, unabhaengige Kopie (append-only-Historie, nichts geht verloren).
#
# Nutzung:  deploy/backup-from-nas.sh
# Ergebnis: backups/<JJJJ-MM-TT_HHMM>/...  (gitignored)
set -euo pipefail

NAS_SSH="luna-nas"
NAS_PATH="/volume1/docker/ki-unternehmen"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y-%m-%d_%H%M)"
DEST="${REPO_ROOT}/backups/${STAMP}"

# Live-Store-Dateien (relativ zum Repo-Root auf der NAS)
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
echo ">> Backup ${NAS_SSH}:${NAS_PATH}  ->  ${DEST}"

# tar nur die existierenden Store-Dateien (ignorierte fehlen ggf.) und entpacke lokal.
REMOTE_LIST=""
for f in "${FILES[@]}"; do REMOTE_LIST="${REMOTE_LIST} ${f}"; done
ssh "$NAS_SSH" "cd ${NAS_PATH} && tar czf - \$(for f in ${REMOTE_LIST}; do [ -f \"\$f\" ] && echo \"\$f\"; done) 2>/dev/null" \
  | tar xzf - -C "$DEST" 2>/dev/null || true

echo ">> Gesichert:"
find "$DEST" -type f -name '*.jsonl' | sed "s#${DEST}/##" | sort | sed 's/^/   - /'
LINES=$(find "$DEST" -type f -name '*.jsonl' -exec cat {} + 2>/dev/null | wc -l | tr -d ' ')
echo ">> ${LINES} Zeilen (Events) gesichert. Aelteste Backups bleiben erhalten (nichts wird geloescht)."
