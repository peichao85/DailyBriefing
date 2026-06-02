#!/bin/bash --login
set -euo pipefail
#
# AI briefing pipeline: research -> (PDF builder + web builder in parallel) ->
# commit & push. The PDF and web builders both consume the research output, so
# research must finish first; the two builders are independent and run together.

source "$(cd "$(dirname "$0")" && pwd)/briefing-common.sh"

verify_tools claude node npm timeout python3
init_log research_results/AI/logs

# Stage 1: Research (must complete before the builders).
run_stage "Research" "Run the ai_research skill for today ($DATE)" 20 || exit 1

# Stage 2 + 3: PDF and web builders run in parallel.
log "PDF Builder & Web Builder started (parallel)"

run_stage "PDF Builder" "Run the ai_pdf_builder skill for today ($DATE)" 7 &
PID_PDF=$!

run_stage "Web Builder" "Run the ai_web_builder skill for today ($DATE)" &
PID_WEB=$!

FAILED=0

if ! wait "$PID_PDF"; then
  # The Claude session can exit non-zero (e.g. budget cap during final QA) after
  # the PDF artifact is already on disk. Treat that as success if the file is a
  # valid PDF; only mark FAILED when the artifact itself is missing or broken.
  PDF_ARTIFACT="pdf/AI/daily-tech-ai-briefing-${DATE}-cn.pdf"
  if [ -f "$PDF_ARTIFACT" ] && pdfinfo "$PDF_ARTIFACT" >/dev/null 2>&1; then
    echo "WARNING: PDF Builder exited non-zero but $PDF_ARTIFACT is a valid PDF; continuing." >> "$LOG"
    log "PDF Builder exited non-zero but artifact valid (treating as success)"
  else
    echo "ERROR: PDF Builder failed and artifact missing or invalid." >> "$LOG"
    FAILED=1
  fi
fi

if ! wait "$PID_WEB"; then
  echo "ERROR: Web Builder failed." >> "$LOG"
  FAILED=1
fi

if [ "$FAILED" -ne 0 ]; then
  log "Aborting due to builder failure(s)"
  exit 1
fi

log "Parallel builders finished"

commit_and_push "Daily AI briefing: ${DATE}" web/AI research_results/AI pdf/AI || exit 1
