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
# Automatisch: MACO470 per systemd-Timer `luna-backup.timer` (seit 2026-09-25, 03:20);
#              MacBook zusaetzlich per launchd (com.hanserautisch.investment-backup) 03:00, solange es laeuft.
set -uo pipefail

NAS_SSH="${NAS_SSH:-luna-nas}"     # ueberschreibbar (Tests)
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
ssh -n -o BatchMode=yes "$NAS_SSH" "cd ${NAS_PATH} && tar czf - \$(for f in ${REMOTE_LIST}; do [ -f \"\$f\" ] && echo \"\$f\"; done) 2>/dev/null" \
  | tar xzf - -C "$DEST" 2>/dev/null || true

FILES_OK=$(find "$DEST" -type f -name '*.jsonl' 2>/dev/null | wc -l | tr -d ' ')
LINES=$(find "$DEST" -type f -name '*.jsonl' -exec cat {} + 2>/dev/null | wc -l | tr -d ' ')
echo ">> ${FILES_OK} Stores, ${LINES} Events gesichert."

# --- Fehlschlag laut machen (2026-09-25) ------------------------------------------------------------------
# Frueher: NAS nicht erreichbar -> leerer Ordner, Exit 0 -- und die Aufbewahrung unten loeschte TROTZDEM den
# aeltesten GUTEN Stand. Dreissig Naechte ohne NAS haetten jede echte Kopie still vernichtet.
# Jetzt: leerer Lauf ODER geschrumpfte Historie (die Stores sind append-only) -> nichts rotieren, melden, Exit 1.
melde() {
  echo ">> FEHLER: $1" >&2
  [ "${BACKUP_MELDEN:-1}" = "0" ] && return 0
  local envf tok chat
  envf="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)/orchestrator/.env"
  [ -f "$envf" ] || return 0
  tok=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$envf" | cut -d= -f2-)
  chat=$(grep -E '^TELEGRAM_ALLOWED_CHAT_ID=' "$envf" | cut -d= -f2-)
  { [ -n "$tok" ] && [ -n "$chat" ]; } || return 0
  curl -s -m 15 -o /dev/null "https://api.telegram.org/bot${tok}/sendMessage" \
    --data-urlencode "chat_id=${chat}" --data-urlencode "text=💾 NAS-Backup ($(hostname)): $1" || true
}
PREV=$(cd "$DEST_BASE" && ls -1d 20*/ 2>/dev/null | sort | grep -vx "${STAMP}/" | tail -1)
PREV_LINES=0
[ -n "$PREV" ] && PREV_LINES=$(find "$DEST_BASE/$PREV" -type f -name '*.jsonl' -exec cat {} + 2>/dev/null | wc -l | tr -d ' ')
if [ "$FILES_OK" -eq 0 ]; then
  rm -rf -- "${DEST_BASE:?}/${STAMP:?}"
  melde "kein einziger Store gesichert (NAS erreichbar?). Alte Backups bleiben unangetastet."
  exit 1
fi
if [ "$LINES" -lt "$PREV_LINES" ]; then
  melde "Historie geschrumpft (${LINES} statt ${PREV_LINES} Events) - append-only verletzt oder Abruf unvollstaendig. Nichts rotiert, alle Staende bleiben."
  exit 1
fi

# Aufbewahrung: die NEUESTE Kopie enthaelt die KOMPLETTE append-only-Historie -> aeltere Snapshots sind
# redundant. Wir behalten die letzten KEEP Backups (kein Datenverlust, kein unbegrenztes Wachstum).
KEEP="${BACKUP_KEEP:-30}"
cd "$DEST_BASE" || exit 0
COUNT=$(ls -1d */ 2>/dev/null | wc -l | tr -d ' ')
if [ "$COUNT" -gt "$KEEP" ]; then
  ls -1d */ | sort | head -n "$((COUNT - KEEP))" | xargs rm -rf
  echo ">> Aufbewahrung: aelteste $((COUNT - KEEP)) Backups entfernt (behalten: ${KEEP}; neuestes hat die volle Historie)."
fi
