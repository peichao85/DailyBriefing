#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up daily briefing cron jobs..."

# Collect cron entries
CRON_ENTRIES=""

# Daily AI briefing at 7:00 AM
CRON_ENTRIES+="01 00 * * * ${SCRIPT_DIR}/run-ai-briefing.sh"
echo "  [+] AI briefing: daily at 7:00 AM"

# Future: add more briefing cron jobs here
# CRON_ENTRIES+=$'\n'"0 9 * * * ${SCRIPT_DIR}/run-xxx-briefing.sh"

# Preserve existing non-briefing cron entries, replace briefing ones
# Remove any existing briefing entries (old or new paths)
EXISTING=$(crontab -l 2>/dev/null | grep -v "run-.*briefing.sh" || true)

if [ -n "$EXISTING" ]; then
  NEW_CRONTAB="${EXISTING}"$'\n'"${CRON_ENTRIES}"
else
  NEW_CRONTAB="${CRON_ENTRIES}"
fi

echo "$NEW_CRONTAB" | crontab -

echo ""
echo "Cron jobs installed. Current crontab:"
crontab -l
