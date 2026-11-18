#!/bin/bash
# github-hr-cron.sh — Automated daily task processing
LOG_DIR="$HOME/github-hr-logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date +%F).log"

# Prevent concurrent execution by re-running ourselves under lockf, which holds the lock
# on an open descriptor -- so the kernel releases it even if this run is kill -9'd, and a
# stale lock cannot wedge every future run. (flock lived here before and does NOT exist
# on macOS: it exited 127, the `|| exit 0` branch fired, and the job did nothing at all,
# every time, logging the same "Already running" line a real conflict would. shlock, the
# other candidate, is deprecated and did not actually reclaim a dead PID's lock.)
LOCK="$HOME/.github-hr/cron.lock"
mkdir -p "$(dirname "$LOCK")"
if [ -z "${GITHUB_HR_CRON_LOCKED:-}" ]; then
  export GITHUB_HR_CRON_LOCKED=1
  /usr/bin/lockf -t 0 "$LOCK" "$0" "$@"
  status=$?
  if [ "$status" -eq 75 ]; then          # EX_TEMPFAIL: another run holds the lock
    echo "Already running, skipping" >> "$LOG_FILE"
    exit 0
  fi
  exit "$status"
fi

echo "=== GitHub HR Run — $(date) ===" >> "$LOG_FILE"

# Claude Code uses the current working directory as the project root.
# The CLI has no --project flag (verified on 2.1.144); cd into the project instead.
# The repo root, two levels above this script (skill/cron/).
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

# launchd starts with an empty environment, so the stale-recovery curl below used to
# POST to "/api/recover-stale-tasks" with no host and no token, and log the failure
# where nobody reads it. Same credentials the Python scripts load via dotenv.
set -a
. "$PROJECT_DIR/skill/scripts/.env"
set +a

# Locate claude binary — check common install paths
CLAUDE_BIN="$(which claude 2>/dev/null)"
if [ -z "$CLAUDE_BIN" ]; then
  for candidate in "$HOME/.npm/bin/claude" "$HOME/.local/bin/claude" "/opt/homebrew/bin/claude" "/usr/local/bin/claude"; do
    if [ -x "$candidate" ]; then
      CLAUDE_BIN="$candidate"
      break
    fi
  done
fi
if [ -z "$CLAUDE_BIN" ]; then
  echo "ERROR: claude not found in PATH or known locations" >> "$LOG_FILE"
  exit 1
fi

echo "--- Stale task recovery ---" >> "$LOG_FILE"
curl -s -H "Authorization: Bearer $API_SECRET" \
  -X POST "$CONVEX_SITE_URL/api/recover-stale-tasks" \
  -H "Content-Type: application/json" \
  -d '{"thresholdMinutes": 30}' >> "$LOG_FILE" 2>&1
echo "" >> "$LOG_FILE"

cd "$PROJECT_DIR" || { echo "ERROR: cannot cd to $PROJECT_DIR" >> "$LOG_FILE"; exit 1; }

# Weekly activity refresh (Mondays): re-read lastPushAt / followers / publicRepos
# from GitHub for every indexed dev, so the dossier's "Last active Nd ago" stays true.
# Runs before the pipeline: ~50 GraphQL calls, patches only what moved.
if [ "$(date +%u)" = "1" ]; then
  echo "--- Weekly activity refresh ---" >> "$LOG_FILE"
  (cd "$PROJECT_DIR/skill/scripts" && .venv/bin/python refresh_activity.py) >> "$LOG_FILE" 2>&1
fi

"$CLAUDE_BIN" -p "/github-hr run" >> "$LOG_FILE" 2>&1

echo "=== Completed — $(date) ===" >> "$LOG_FILE"
