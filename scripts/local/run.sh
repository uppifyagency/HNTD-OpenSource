#!/usr/bin/env bash
# Start HNTD in local mode: local Convex backend + Next on 127.0.0.1. Ctrl-C stops both.
# PORT picks the app port (default 3000).
set -euo pipefail
cd "$(dirname "$0")/../.."
. scripts/local/lib.sh

[ -f "$ENV_FILE" ] || { echo "no $ENV_FILE yet: run scripts/local/setup.sh first"; exit 1; }
require_local_env
require_local_skill_env
PORT=${PORT:-3000}

mkdir -p .convex
NEXT_PID= WORKER_PID=
# Every child runs in the background so a signal reaches this trap at once instead of after
# a foreground child exits. Installed first so a failed start still stops the backend.
trap 'trap - EXIT INT TERM; for p in $NEXT_PID $WORKER_PID; do killtree "$p"; done; stop_convex' EXIT INT TERM
start_convex .convex/hntd-convex.log

# The backend picks the first free port from 3210, so keep the pipeline client in step with it.
API_SECRET=$(env_get "$SKILL_ENV" API_SECRET)
if [ -n "$API_SECRET" ]; then write_skill_env "$API_SECRET"; fi

# The worker runs the searches created in the dashboard (claude -p "/github-hr run --task <id>").
# HNTD_PIPELINE_MODEL picks its model (default: your Claude Code default).
skill/scripts/.venv/bin/python scripts/local/worker.py >> .convex/hntd-worker.log 2>&1 &
WORKER_PID=$!

# The link carries the browser key (src/lib/session/loopback.ts): open it once in each browser.
echo "HNTD local: http://127.0.0.1:$PORT/api/local-session?key=$(node scripts/local/keys.mjs browser-key)"
echo "  (open this link once in your browser; then http://127.0.0.1:$PORT/dashboard works. Convex: $(env_get "$ENV_FILE" NEXT_PUBLIC_CONVEX_URL))"
echo "Pipeline worker log: .convex/hntd-worker.log   (model: ${HNTD_PIPELINE_MODEL:-Claude Code default})"
npx next dev -H 127.0.0.1 -p "$PORT" &
NEXT_PID=$!
wait "$NEXT_PID"
