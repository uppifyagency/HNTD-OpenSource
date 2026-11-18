#!/bin/sh
# npm "predev" hook. `npm run dev` is the cloud dev server: it starts no Convex backend and binds
# every interface. A local-mode checkout must use `npm run local` (loopback only, local Convex).
if grep -q '^NEXT_PUBLIC_HNTD_MODE=local$' .env.local 2>/dev/null; then
  echo "refusing: .env.local is a local-mode file. Start local mode with: npm run local"
  echo "(npm run dev is cloud-only.)"
  exit 1
fi
