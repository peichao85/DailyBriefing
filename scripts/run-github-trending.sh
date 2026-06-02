#!/bin/bash --login
set -euo pipefail
#
# GitHub Trending briefing: query the GitHub API for hot/rising repos, generate
# Chinese summaries, write the web data file, then commit & push. Best-effort —
# independent of the AI pipeline.

source "$(cd "$(dirname "$0")" && pwd)/briefing-common.sh"

verify_tools claude python3 timeout
init_log research_results/GitHub/logs

run_stage "GitHub Trending Builder" \
  "Run the github_trending_builder skill for today ($DATE)" 3 || exit 1

commit_and_push "Daily GitHub trending: ${DATE}" web/GitHub research_results/GitHub || exit 1
