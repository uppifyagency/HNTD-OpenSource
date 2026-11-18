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
NEXT_PID=
# Both servers run in the background so a signal reaches this trap at once instead of after
# a foreground child exits. Installed first so a failed start still stops the backend.
trap 'trap - EXIT INT TERM; [ -n "$NEXT_PID" ] && killtree "$NEXT_PID"; stop_convex' EXIT INT TERM
start_convex .convex/hntd-convex.log

# The backend picks the first free port from 3210, so keep the pipeline client in step with it.
API_SECRET=$(env_get "$SKILL_ENV" API_SECRET)
if [ -n "$API_SECRET" ]; then write_skill_env "$API_SECRET"; fi

echo "HNTD local: http://127.0.0.1:$PORT/dashboard   (Convex: $(env_get "$ENV_FILE" NEXT_PUBLIC_CONVEX_URL))"
npx next dev -H 127.0.0.1 -p "$PORT" &
NEXT_PID=$!
wait "$NEXT_PID"
