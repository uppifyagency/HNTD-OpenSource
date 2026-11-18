#!/bin/bash
# poller.sh — Check for priority tasks every 5 minutes
set -e

# The repo root, two levels above this script (skill/scripts/).
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_DIR="$HOME/github-hr-logs"
mkdir -p "$LOG_DIR"

cd "$PROJECT_DIR"
source skill/scripts/.venv/bin/activate

PRIORITY=$(python skill/scripts/convex_client.py priority 2>/dev/null)

if [ "$PRIORITY" != "[]" ] && [ -n "$PRIORITY" ]; then
    LOG_FILE="$LOG_DIR/priority-$(date +%F-%H%M).log"
    echo "=== Priority Run — $(date) ===" >> "$LOG_FILE"
    echo "Tasks: $PRIORITY" >> "$LOG_FILE"

    claude -p "/github-hr run --priority-only" \
        --project "$PROJECT_DIR" \
        >> "$LOG_FILE" 2>&1

    echo "=== Completed — $(date) ===" >> "$LOG_FILE"
fi

deactivate
