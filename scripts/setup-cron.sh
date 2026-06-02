#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up daily briefing cron jobs..."

# Each briefing now runs as its own cron job (shared code lives in
# scripts/briefing-common.sh):
#
#   - AI briefing      : research + PDF + web builders
#   - GitHub trending   : hot/rising repos
#   - US-stocks recap   : 美股复盘 closing recap
#
# Times are in the machine's local zone (Asia/Shanghai) UNLESS a CRON_TZ prefix
# overrides them for that line.

CRON_ENTRIES=""

# AI briefing — daily at 06:58 Asia/Shanghai.
CRON_ENTRIES+="58 06 * * * ${SCRIPT_DIR}/run-ai-briefing.sh"
echo "  [+] AI briefing:      daily 06:58 Asia/Shanghai"

# GitHub trending — daily at 08:30 Asia/Shanghai (after the AI run, so the two
# git pushes don't overlap; not time-sensitive otherwise).
CRON_ENTRIES+=$'\n'"30 08 * * * ${SCRIPT_DIR}/run-github-trending.sh"
echo "  [+] GitHub trending:  daily 08:30 Asia/Shanghai"

# US-stocks recap — must run after the just-closed US session's end-of-day bar
# is published (observed available ~6h after the 16:00 ET close). We want >=1h
# margin on top of that, i.e. >= ~7h after the close.
#
# This cron (Ubuntu vixie cron) ignores CRON_TZ/TZ for *scheduling* — jobs always
# fire in the machine zone (Asia/Shanghai). So we can't anchor to US Eastern;
# instead we split the year by month to follow US daylight saving, since the UTC
# time of the US close shifts by an hour across DST:
#
#   US summer (EDT, close 20:00 UTC) -> 11:00 SH (03:00 UTC) = +7h after close
#   US winter (EST, close 21:00 UTC) -> 12:00 SH (04:00 UTC) = +7h after close
#
# Month split (Apr–Oct summer / Nov–Mar winter) is deliberately conservative
# around the mid-March and early-Nov DST edges: every day still lands >=7h after
# the close (>=1h margin), with at most a harmless extra hour of wait. The
# --check-only guard fails safe anyway (skips weekends/holidays, and a still-late
# bar just retries the next day).
CRON_ENTRIES+=$'\n'"00 11 * 4-10 * ${SCRIPT_DIR}/run-us-stocks-briefing.sh"
CRON_ENTRIES+=$'\n'"00 12 * 1-3,11,12 * ${SCRIPT_DIR}/run-us-stocks-briefing.sh"
echo "  [+] US-stocks recap:  11:00 Asia/Shanghai (Apr–Oct) / 12:00 (Nov–Mar) — ~7h after US close"

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
