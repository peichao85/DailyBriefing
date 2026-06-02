#!/bin/bash --login
set -euo pipefail
#
# US-stocks (美股复盘) recap: pull the latest completed US session and publish a
# Chinese closing recap, then commit & push. Best-effort, independent of the AI
# pipeline.
#
# Scheduling note: this must run late enough that the data provider has posted
# the just-closed session's end-of-day bar (observed available ~6h after the
# 16:00 ET close). The cron runs it ~7h after the close (>=1h margin): 11:00
# Asia/Shanghai Apr–Oct and 12:00 Nov–Mar, a month split that follows US
# daylight saving because this cron ignores CRON_TZ for scheduling. See
# scripts/setup-cron.sh.
#
# The pre-flight --check-only guard skips the (paid) recap when the market is
# closed and the latest completed session is already published — weekends,
# holidays, or a same-day re-run. It exits 3 in that case; any other result
# (new session, or an inconclusive check) falls through and runs the stage.

source "$(cd "$(dirname "$0")" && pwd)/briefing-common.sh"

verify_tools claude python3 timeout
init_log research_results/USStocks/logs

check_rc=0
python3 skills/us_stocks_briefing/scripts/fetch_market_data.py \
  --date "$DATE" --check-only >> "$LOG" 2>&1 || check_rc=$?
if [ "$check_rc" -eq 3 ]; then
  log "US Stocks Briefing skipped (market closed / latest session already published)"
  exit 0
fi

run_stage "US Stocks Briefing" \
  "Run the us_stocks_briefing skill for today ($DATE)" 15 || exit 1

commit_and_push "Daily US stocks recap: ${DATE}" web/USStocks research_results/USStocks || exit 1
