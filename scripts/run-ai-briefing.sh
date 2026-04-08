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

# Ensure log directory exists
mkdir -p daily_briefing/AI/logs

DATE=$(date +%Y-%m-%d)
LOG="daily_briefing/AI/logs/briefing-${DATE}.log"

echo "=== Briefing generation started: $(date) ===" >> "$LOG"

timeout 1800 claude -p "create today's ai briefing with skill daily_AI_briefing" \
  --dangerously-skip-permissions \
  --model opus \
  --max-budget-usd 5 \
  >> "$LOG" 2>&1

EXIT_CODE=$?
echo "=== Briefing generation finished: $(date), exit code: ${EXIT_CODE} ===" >> "$LOG"
exit $EXIT_CODE
