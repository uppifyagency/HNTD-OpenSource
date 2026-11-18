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

# The pipeline reaches GitHub through gh with the token saved in skill/scripts/.env (gitignored,
# readable only by you), never with your gh login: it reads untrusted text, so a token that cannot
# write is the safe one. Ask once for one; the dashboard can also take it later.
GH_TOKEN_NEW=
GH_TOKEN_SAVED=$(env_get "$SKILL_ENV" GH_TOKEN)
if [ -n "$GH_TOKEN_SAVED" ] && login=$(github_login "$GH_TOKEN_SAVED"); then
  echo "GitHub: connected as $login with the token saved in $SKILL_ENV."
elif [ -t 0 ]; then
  if [ -n "$GH_TOKEN_SAVED" ]; then  # github_login printed why above
    echo "GitHub: the token saved in $SKILL_ENV was not confirmed. Paste a new one, or press Enter to keep it."
  else
    echo "GitHub is not connected. Paste a GitHub token here, or press Enter to do it later from the"
    echo "dashboard. Safest: a classic token with no boxes ticked, from https://github.com/settings/tokens/new"
  fi
  read -rs -p "GitHub token: " GH_TOKEN_NEW; echo
  if [ -n "$GH_TOKEN_NEW" ]; then
    if login=$(github_login "$GH_TOKEN_NEW"); then echo "GitHub: connected as $login."
    else echo "Token not saved; connect GitHub later from the dashboard."; GH_TOKEN_NEW=; fi
  fi
else
  echo "GitHub: not connected. Connect it from the dashboard."
fi
write_skill_env "$API_SECRET" "$GH_TOKEN_NEW"

if [ -f skill/scripts/requirements.txt ] && [ ! -x skill/scripts/.venv/bin/python ] && command -v python3 >/dev/null; then
  python3 -m venv skill/scripts/.venv
  skill/scripts/.venv/bin/pip install -q -r skill/scripts/requirements.txt
fi

command -v claude >/dev/null || echo "note: Claude Code (claude) is not installed; the pipeline and AI search need it."
command -v gh >/dev/null || echo "note: GitHub CLI (gh) is not installed; the pipeline needs it (a token is enough, no gh login)."
echo "LOCAL SETUP DONE. Start the app with: npm run local"
