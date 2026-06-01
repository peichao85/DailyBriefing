#!/bin/bash --login
set -euo pipefail

# --login flag makes bash read ~/.profile, loading the full PATH
# (needed because cron only has /usr/bin:/bin)

# Resolve project root (scripts/ is one level under project root)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Verify required tools are available
for cmd in claude node npm timeout; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' not found in PATH." >&2
    echo "  Current PATH: $PATH" >&2
    echo "  If running from cron, ensure your shell profile (~/.profile or ~/.bash_profile)" >&2
    echo "  adds the directory containing '$cmd' to PATH." >&2
    exit 1
  fi
done

# Extend per-command bash timeout (default 2min is too short for some steps)
export BASH_DEFAULT_TIMEOUT_MS=600000   # 10 min
export BASH_MAX_TIMEOUT_MS=900000       # 15 min

# Set NODE_PATH so globally installed npm packages are found
export NODE_PATH="$(npm root -g 2>/dev/null || true)"

cd "$PROJECT_ROOT"

DATE=$(date +%Y-%m-%d)
mkdir -p research_results/AI/logs
mkdir -p research_results/GitHub/logs
mkdir -p research_results/USStocks/logs

LOG="research_results/AI/logs/briefing-${DATE}.log"

log() { echo "=== $1: $(date) ===" >> "$LOG"; }

run_stage() {
  local name="$1" prompt="$2" budget="${3:-5}"
  log "$name started"
  if timeout 1800 claude -p "$prompt" \
    --dangerously-skip-permissions \
    --model opus \
    --max-budget-usd "$budget" \
    >> "$LOG" 2>&1; then
    log "$name finished successfully"
  else
    local code=$?
    log "$name FAILED (exit code: $code)"
    echo "ERROR: $name failed with exit code $code. Aborting." >> "$LOG"
    return $code
  fi
}

# Stage 1: Research (must complete before builders)
run_stage "Research" "Run the ai_research skill for today ($DATE)" 20 || exit 1

# Stages 2-5: PDF Builder, Web Builder, GitHub Trending, and US Stocks recap run in parallel.
# GitHub Trending and US Stocks are best-effort — they must not block the AI pipeline if
# their external data sources (GitHub API / market data feeds) hiccup.
log "PDF Builder, Web Builder, GitHub Trending & US Stocks started (parallel)"

run_stage "PDF Builder" "Run the ai_pdf_builder skill for today ($DATE)" 7 &
PID_PDF=$!

run_stage "Web Builder" "Run the ai_web_builder skill for today ($DATE)" &
PID_WEB=$!

run_stage "GitHub Trending Builder" "Run the github_trending_builder skill for today ($DATE)" 3 &
PID_GH=$!

run_stage "US Stocks Briefing" "Run the us_stocks_briefing skill for today ($DATE)" 15 &
PID_US=$!

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

if ! wait "$PID_GH"; then
  # Non-fatal: GitHub Trending is best-effort. Log a warning but do NOT set FAILED.
  echo "WARNING: GitHub Trending Builder failed (non-fatal)." >> "$LOG"
  log "GitHub Trending Builder FAILED (non-fatal)"
fi

if ! wait "$PID_US"; then
  # Non-fatal: US Stocks recap is best-effort. Log a warning but do NOT set FAILED.
  echo "WARNING: US Stocks Briefing failed (non-fatal)." >> "$LOG"
  log "US Stocks Briefing FAILED (non-fatal)"
fi

if [ "$FAILED" -ne 0 ]; then
  log "Aborting due to builder failure(s)"
  exit 1
fi

log "Parallel builders finished"

# Rebuild the web manifest from disk. Doing this post-builders avoids any race
# that would exist if the two web-writing skills each updated manifest.json
# independently. Only web/manifest.json is touched by this step.
log "Manifest rebuild started"
if ! python3 scripts/rebuild_manifest.py >> "$LOG" 2>&1; then
  log "Manifest rebuild FAILED"
  exit 1
fi
log "Manifest rebuild finished"

# Commit and push web/ and pdf/ changes
log "Git commit & push started"
git add web/ pdf/ research_results/
# Unstage log files so they are never pushed to remote
git reset HEAD research_results/AI/logs/ research_results/GitHub/logs/ research_results/USStocks/logs/ >/dev/null 2>&1 || true
if git diff --cached --quiet; then
  echo "No changes to commit." >> "$LOG"
else
  if ! git commit -m "Daily AI briefing: ${DATE}" >> "$LOG" 2>&1; then
    log "Git commit FAILED"
    exit 1
  fi
  # Pull first to avoid "rejected: fetch first" when remote has new commits
  if ! git pull --rebase origin main >> "$LOG" 2>&1; then
    log "Git pull --rebase FAILED"
    # If rebase left the repo in an intermediate state, abort to keep it clean
    if [ -d "$(git rev-parse --git-path rebase-merge)" ] || [ -d "$(git rev-parse --git-path rebase-apply)" ]; then
      echo "Rebase in progress, aborting..." >> "$LOG"
      git rebase --abort >> "$LOG" 2>&1 || true
    fi
    log "Git push skipped due to rebase failure"
    exit 1
  fi
  if ! git push >> "$LOG" 2>&1; then
    log "Git push FAILED"
    exit 1
  fi
fi
log "Git commit & push finished"
