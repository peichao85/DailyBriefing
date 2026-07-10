#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up daily briefing cron jobs..."

# Only the AI briefing is scheduled daily (shared code lives in
# scripts/briefing-common.sh). GitHub trending (run-github-trending.sh) and
# US-stocks recap (run-us-stocks-briefing.sh) still exist and can be run
# manually, but are intentionally not scheduled here.
#
# Times are in the machine's local zone (Asia/Shanghai) UNLESS a CRON_TZ prefix
# overrides them for that line.

CRON_ENTRIES=""

# AI briefing — daily at 06:58 Asia/Shanghai.
CRON_ENTRIES+="58 06 * * * ${SCRIPT_DIR}/run-ai-briefing.sh"
echo "  [+] AI briefing:      daily 06:58 Asia/Shanghai"

# Preserve existing non-briefing cron entries; replace any briefing ones
# (matches the old run-briefing.sh and the new run-*-briefing/run-*-trending
# script names).
EXISTING=$(crontab -l 2>/dev/null \
  | grep -vE 'run-(ai-briefing|github-trending|us-stocks-briefing|briefing)\.sh' || true)

if [ -n "$EXISTING" ]; then
  NEW_CRONTAB="${EXISTING}"$'\n'"${CRON_ENTRIES}"
else
  NEW_CRONTAB="${CRON_ENTRIES}"
fi

echo "$NEW_CRONTAB" | crontab -

echo ""
echo "Cron jobs installed. Current crontab:"
crontab -l
