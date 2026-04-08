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

# Stage 2 & 3: PDF Builder and Web Builder run in parallel
log "PDF Builder & Web Builder started (parallel)"

run_stage "PDF Builder" "Run the ai_pdf_builder skill for today ($DATE)" &
PID_PDF=$!

run_stage "Web Builder" "Run the ai_web_builder skill for today ($DATE)" &
PID_WEB=$!

FAILED=0

if ! wait "$PID_PDF"; then
  echo "ERROR: PDF Builder failed." >> "$LOG"
  FAILED=1
fi

if ! wait "$PID_WEB"; then
  echo "ERROR: Web Builder failed." >> "$LOG"
  FAILED=1
fi

if [ "$FAILED" -ne 0 ]; then
  log "Aborting due to builder failure(s)"
  exit 1
fi

log "PDF Builder & Web Builder finished (parallel)"

# Commit and push web/ and pdf/ changes
log "Git commit & push started"
git add web/ pdf/
if git diff --cached --quiet; then
  echo "No changes to commit." >> "$LOG"
else
  if ! git commit -m "Daily AI briefing: ${DATE}" >> "$LOG" 2>&1; then
    log "Git commit FAILED"
    exit 1
  fi
  if ! git push >> "$LOG" 2>&1; then
    log "Git push FAILED"
    exit 1
  fi
fi
log "Git commit & push finished"
