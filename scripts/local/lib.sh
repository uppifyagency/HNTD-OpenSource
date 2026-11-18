# Shared by setup.sh and run.sh. Sourced from the repo root.
ENV_FILE=.env.local
SKILL_ENV=skill/scripts/.env

# These override .env.local in the convex CLI and can point it at a cloud deployment.
unset CONVEX_DEPLOY_KEY CONVEX_DEPLOYMENT CONVEX_SELF_HOSTED_URL CONVEX_SELF_HOSTED_ADMIN_KEY

CONVEX_PID=

env_get() { { grep "^$2=" "$1" 2>/dev/null || true; } | head -1 | cut -d= -f2-; }  # $1 = file, $2 = key

require_local_env() {
  if [ -f "$ENV_FILE" ] && ! grep -q '^NEXT_PUBLIC_HNTD_MODE=local$' "$ENV_FILE"; then
    echo "refusing: $ENV_FILE exists and is not a local-mode file (it may point at a cloud deployment)."
    echo "Move it away, then rerun scripts/local/setup.sh."
    exit 1
  fi
}

# The pipeline client must never fall back to a cloud deployment.
require_local_skill_env() {
  if [ -f "$SKILL_ENV" ] && ! grep -q '^CONVEX_SITE_URL=http://127\.0\.0\.1:' "$SKILL_ENV"; then
    echo "refusing: $SKILL_ENV exists and does not point at 127.0.0.1. Move it away, then rerun."
    exit 1
  fi
}

write_skill_env() {  # $1 = API secret
  local site; site=$(env_get "$ENV_FILE" NEXT_PUBLIC_CONVEX_SITE_URL)
  case "$site" in http://127.0.0.1:*) ;; *) echo "refusing: Convex site URL '$site' is not local"; exit 1;; esac
  printf 'CONVEX_SITE_URL=%s\nAPI_SECRET=%s\n' "$site" "$1" > "$SKILL_ENV"
  chmod 600 "$SKILL_ENV"
}

# Kill a pid and every descendant (npx -> node -> convex local backend).
killtree() {
  local pid=$1 child
  for child in $(pgrep -P "$pid" 2>/dev/null); do killtree "$child"; done
  kill "$pid" 2>/dev/null || true
}

# Start `convex dev` in the background; sets CONVEX_PID. $1 = log file.
start_convex() {
  npx convex dev --tail-logs disable > "$1" 2>&1 < /dev/null &
  CONVEX_PID=$!
  disown "$CONVEX_PID"  # no "Terminated" job notice when we stop it
  for _ in $(seq 180); do
    local url; url=$(env_get "$ENV_FILE" NEXT_PUBLIC_CONVEX_URL)
    if grep -q '^CONVEX_DEPLOYMENT=anonymous:' "$ENV_FILE" && [ -n "$url" ] && curl -sf -m 2 "$url/version" >/dev/null; then
      return 0
    fi
    kill -0 "$CONVEX_PID" 2>/dev/null || { echo "convex dev exited early; log:"; tail -20 "$1"; exit 1; }
    sleep 1
  done
  echo "convex dev did not come up in 180s; log:"; tail -20 "$1"; exit 1
}

# Stop the backend start_convex started, if any, and wait until it is gone. Safe to call twice.
stop_convex() {
  [ -n "$CONVEX_PID" ] || return 0
  killtree "$CONVEX_PID"
  for _ in $(seq 20); do kill -0 "$CONVEX_PID" 2>/dev/null || break; sleep 1; done
  CONVEX_PID=
}
