# shellcheck shell=bash
#
# Shared helpers for the daily briefing entry scripts:
#   run-ai-briefing.sh, run-github-trending.sh, run-us-stocks-briefing.sh
#
# This file is meant to be *sourced*, not executed. The entry scripts own the
# `#!/bin/bash --login` shebang (so cron loads the full PATH from ~/.profile)
# and `set -euo pipefail`.

# Resolve project root from this library's own location (scripts/ is one level
# under the project root). Works regardless of the caller's CWD.
COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$COMMON_DIR/.." && pwd)"

DATE="$(date +%Y-%m-%d)"

# Extend the per-command bash timeout (Claude Code's 2min default is too short
# for some steps) and let Node find globally installed npm packages.
export BASH_DEFAULT_TIMEOUT_MS=600000   # 10 min
export BASH_MAX_TIMEOUT_MS=900000       # 15 min
export NODE_PATH="$(npm root -g 2>/dev/null || true)"

cd "$PROJECT_ROOT"

# LOG is set by init_log() before log() is used.
LOG=""

# verify_tools <cmd>...  — fail fast if a required command is missing from PATH.
verify_tools() {
  local cmd
  for cmd in "$@"; do
    if ! command -v "$cmd" &>/dev/null; then
      echo "ERROR: '$cmd' not found in PATH." >&2
      echo "  Current PATH: $PATH" >&2
      echo "  If running from cron, ensure your shell profile (~/.profile or ~/.bash_profile)" >&2
      echo "  adds the directory containing '$cmd' to PATH." >&2
      exit 1
    fi
  done
}

# init_log <logs-subdir>  — e.g. init_log research_results/AI/logs
# Creates the directory and points LOG at today's per-stage log file.
init_log() {
  local dir="$PROJECT_ROOT/$1"
  mkdir -p "$dir"
  LOG="$dir/briefing-${DATE}.log"
}

log() { echo "=== $1: $(date) ===" >> "$LOG"; }

# run_stage <name> <prompt> [budget]  — run one Claude Code skill stage.
# Returns the stage's exit code on failure so callers can decide fatality.
run_stage() {
  local name="$1" prompt="$2" budget="${3:-5}"
  log "$name started"
  if timeout 1800 claude -p "$prompt" \
    --dangerously-skip-permissions \
    --model claude-opus-4-8 \
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

# rebuild_manifest  — regenerate web/manifest.json from whatever is on disk.
# The manifest is a pure derived index, so regenerating always yields the
# correct merged result regardless of which stages have published.
rebuild_manifest() {
  python3 scripts/rebuild_manifest.py >> "$LOG" 2>&1
}

_rebase_in_progress() {
  [ -d "$(git rev-parse --git-path rebase-merge)" ] || \
  [ -d "$(git rev-parse --git-path rebase-apply)" ]
}

# commit_and_push <commit-message> <path>...
#
# Rebuilds the manifest, stages the manifest plus the given paths (never log
# files), commits, then pushes with rebase. Because the stages now run as
# independent cron jobs that each touch web/manifest.json, two pushes can race;
# the only shared file is the derived manifest, so a rebase conflict on it is
# resolved by simply regenerating it from disk and continuing. No-op when there
# is nothing to commit.
commit_and_push() {
  local msg="$1"; shift

  log "Manifest rebuild started"
  if ! rebuild_manifest; then
    log "Manifest rebuild FAILED"
    return 1
  fi
  log "Manifest rebuild finished"

  log "Git commit & push started"
  git add web/manifest.json "$@"
  # Logs live under research_results/<cat>/logs and must never be pushed.
  git reset -q HEAD \
    research_results/AI/logs \
    research_results/GitHub/logs \
    research_results/USStocks/logs >/dev/null 2>&1 || true

  if git diff --cached --quiet; then
    echo "No changes to commit." >> "$LOG"
    log "Git commit & push finished"
    return 0
  fi

  if ! git commit -m "$msg" >> "$LOG" 2>&1; then
    log "Git commit FAILED"
    return 1
  fi

  # Push, retrying on remote divergence. Resolve a manifest-only rebase
  # conflict by regenerating the manifest from disk.
  local attempt
  for attempt in 1 2 3; do
    if git pull --rebase origin main >> "$LOG" 2>&1; then
      if git push >> "$LOG" 2>&1; then
        log "Git commit & push finished"
        return 0
      fi
      echo "Push rejected (attempt $attempt); retrying." >> "$LOG"
      continue
    fi

    # pull --rebase failed: if it's a manifest conflict, regenerate & continue.
    if _rebase_in_progress; then
      echo "Rebase conflict; regenerating manifest from disk." >> "$LOG"
      rebuild_manifest || true
      git add web/manifest.json >> "$LOG" 2>&1 || true
      if git rebase --continue >> "$LOG" 2>&1; then
        if git push >> "$LOG" 2>&1; then
          log "Git commit & push finished"
          return 0
        fi
        echo "Push rejected after rebase (attempt $attempt); retrying." >> "$LOG"
        continue
      fi
      echo "Rebase --continue failed; aborting rebase." >> "$LOG"
      git rebase --abort >> "$LOG" 2>&1 || true
      log "Git push FAILED (unresolved rebase conflict)"
      return 1
    fi

    log "Git pull --rebase FAILED"
    return 1
  done

  log "Git push FAILED (exhausted retries)"
  return 1
}
