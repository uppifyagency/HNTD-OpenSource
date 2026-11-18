#!/usr/bin/env bash
# One-time setup for local mode: HNTD on this machine, a local Convex database, no Clerk, no Stripe.
# Idempotent: rerun it any time. Then start the app with `npm run local`.
set -euo pipefail
cd "$(dirname "$0")/../.."
. scripts/local/lib.sh

require_local_env
require_local_skill_env
command -v node >/dev/null || { echo "Node.js 20+ is required"; exit 1; }
[ -d node_modules ] || npm ci

node scripts/local/keys.mjs init

# Reuse the pipeline secret across reruns so skill/scripts/.env and Convex agree.
API_SECRET=$(env_get "$SKILL_ENV" API_SECRET)
[ -n "$API_SECRET" ] || API_SECRET=$(openssl rand -hex 24)

mkdir -p .convex
LOG=.convex/hntd-setup.log
trap stop_convex EXIT
start_convex "$LOG"
# convex/auth.config.ts trusts only the local issuer when CLERK_JWT_ISSUER_DOMAIN is the local issuer.
# The backend validates each change against the deployed auth config: set the key before the switch.
npx convex env set LOCAL_AUTH_JWKS "$(node scripts/local/keys.mjs jwks)" >/dev/null
npx convex env set CLERK_JWT_ISSUER_DOMAIN https://local.hntd.invalid >/dev/null  # = LOCAL_ISSUER, convex/localAuth.ts
npx convex env set API_SECRET "$API_SECRET" >/dev/null
stop_convex

# Push once more so convex/auth.config.ts reads LOCAL_AUTH_JWKS.
npx convex dev --once --tail-logs disable > "$LOG" 2>&1 < /dev/null || { echo "convex push failed; log:"; tail -30 "$LOG"; exit 1; }

write_skill_env "$API_SECRET"

if [ -f skill/scripts/requirements.txt ] && [ ! -x skill/scripts/.venv/bin/python ] && command -v python3 >/dev/null; then
  python3 -m venv skill/scripts/.venv
  skill/scripts/.venv/bin/pip install -q -r skill/scripts/requirements.txt
fi

command -v claude >/dev/null || echo "note: Claude Code (claude) is not installed; the pipeline and AI search need it."
command -v gh >/dev/null || echo "note: GitHub CLI (gh) is not installed; the pipeline needs it (then run: gh auth login)."
echo "LOCAL SETUP DONE. Start the app with: npm run local"
