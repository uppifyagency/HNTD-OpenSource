# Working on HNTD

Notes for contributors and AI coding agents. `README.md` covers what HNTD is and how to run it.

## Layout

- `src/` Next.js app. `src/lib/mode.ts` is the only reader of `NEXT_PUBLIC_HNTD_MODE` (`cloud` or
  `local`). Outside the cloud-only sign-in and billing pages, only `src/lib/session/` imports Clerk;
  use `useSessionUser()` or `useSession()` instead of Clerk hooks.
- `convex/` Convex functions and schema. Read `convex/_generated/ai/guidelines.md` before you change
  Convex code. `convex/http.ts` holds the HTTP API the pipeline calls.
- `skill/` the Claude Code pipeline: `skill/github-hr/SKILL.md` is the entry point,
  `skill/skills/*` are its phases, `skill/scripts/*.py` do the deterministic work.
- `scripts/local/` local mode: `setup.sh` once, `run.sh` (`npm run local`) every time.

## Checks

```bash
npm test                      # vitest
npm run build                 # type-check and build
skill/scripts/run-tests.sh    # pipeline tests; needs skill/scripts/requirements-dev.txt installed
```

Run Python tests through `run-tests.sh`, not a bare `pytest` in `skill/scripts`: collecting
`push_results.py` as a test module fails, and the acceptance suites collide when collected together.
`run-tests.sh` also points the pipeline client at a closed port, so no test can reach a database.

## Rules

- GitHub data comes from the official API through `gh`. No HTML scraping.
- `npm run dev` is the cloud dev server and refuses a local-mode `.env.local`. Use `npm run local`.
- Local mode must not need Clerk or Stripe keys. A change that breaks `npm run build` without them
  breaks local mode.
