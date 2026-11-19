---
name: verify
description: >
  Drive HNTD local mode the way a user does and capture proof: the Next.js dashboard in a real
  browser, and the pipeline's terminal client against the local Convex database. Use it to
  verify a change to src/, convex/ or skill/scripts/ on the running app, before you call the
  change done.
---

# Verify HNTD

HNTD has two user surfaces. The primary one is the dashboard at `/dashboard` (Next.js, local
mode). The second is the terminal: the `/github-hr` pipeline and its client
`skill/scripts/convex_client.py`. Both read and write one local Convex database.

`hntd-verify` below means `.claude/skills/verify/scripts/hntd-verify`. Run it from the repo root.
[`features/README.md`](features/README.md) is the feature map: one recipe per user-facing
feature. [`statechart/README.md`](statechart/README.md) is the state map of a search and the
rules it breaks.

## Launch

```bash
scripts/local/setup.sh    # once per checkout, and again after a schema or auth change
hntd-verify launch        # prints READY http://127.0.0.1:3100/dashboard
```

`launch` copies the local database to `.convex/verify/db-before`, starts `scripts/local/run.sh`
on port 3100 (`HNTD_VERIFY_PORT` picks another), and waits until three things answer: the app
signs a local session for the browser key, `/dashboard` compiles, and the pipeline API accepts
the secret in `skill/scripts/.env`. It then opens the link `npm run local` prints
(`/api/local-session?key=...`) once in a browser, as a user does. That stores the browser key
and lands on `/dashboard`, and the first visit creates the local user row.
`HNTD_VERIFY_SKIP_FIRST_VISIT=1` skips that visit, to test a database with no user row.

**The pipeline worker stays off.** `run.sh` also starts `scripts/local/worker.py`, which runs
every pending search with Claude Code and a GitHub token. A recipe that creates a search would
start a real run that costs tokens. `launch` therefore takes `.convex/worker.lock` first, and
the worker exits at once with `another HNTD worker is already running`. The dashboard then shows
the banner `Pipeline locale non attiva`. `HNTD_VERIFY_WORKER=1 hntd-verify launch` leaves the
worker on. Use it only to verify the worker itself, and only with the user's go when
`skill/scripts/.env` holds a `GH_TOKEN`.

One instance per checkout. The Convex backend takes the first free port from 3210 and the
database is one folder, so two instances of the same checkout cannot run side by side. `launch`
refuses when a Convex backend already answers and the harness did not start it. That backend
is the user's own `npm run local`. Never drive it and never stop it. Ask the user to stop it,
or work in another checkout.

A checkout with no `.env.local` needs `npm ci` and `scripts/local/setup.sh` first. Setup
downloads the Convex backend binary, so it needs the network once.

## Doctor

```bash
hntd-verify doctor
```

Read-only. It checks that the `run.sh` this harness started is alive, that the app port belongs
to that process tree, that the app signs a session for the browser key, that the pipeline
worker is held off, that Convex answers, that the pipeline API accepts the secret, that the
local user row exists, and that Playwright can open a Chromium. It prints the commit the dev
server is serving. Exit code 0 means the instance is worth driving. Run it first whenever a
step fails for a reason you do not understand.

## Drive

Browser, one invocation per journey. The steps run in order in one page:

```bash
hntd-verify browser --out test-results/verify/<run>/<feature> \
  goto /dashboard/new-task \
  click 'text="Ricerca rapida"' \
  type 'form input >> nth=0' python  press Enter \
  select 'form select >> nth=0' italy \
  click 'button[type=submit]'  url '/dashboard$' \
  aria overview  shot overview
```

Steps: `goto PATH`, `click SEL`, `fill SEL VALUE`, `type SEL VALUE`, `press KEY`,
`select SEL VALUE`, `expect SEL`, `absent SEL`, `url REGEX`, `text SEL`,
`download SEL NAME`, `aria NAME`, `shot NAME`. `SEL` is a Playwright selector. The header of
[`scripts/browser.mjs`](scripts/browser.mjs) documents each step. Page state does not carry from
one invocation to the next. The database does. Every invocation starts with the browser key
cookie already set, so a journey can open any page first.

Terminal, the pipeline's view of the same database:

```bash
hntd-verify client jobs                 # every search with status and result count
hntd-verify client pending              # the queue as JSON
hntd-verify client results <TASK_ID>    # the shortlist of one search
hntd-verify api GET /api/users-dashboard
hntd-verify seed-results <TASK_ID>      # give a search a shortlist of four fixture candidates
```

`seed-results` stands in for pipeline phases 1 to 6, which need GitHub, Claude and several
minutes. It copies the contract-tested fixtures from `skill/scripts/tests/jd_pipeline/fixtures/`
into `skill/output/` and runs the real `push_results.py`. Phase 7 (push and complete) is
therefore real. Search, fetch and scoring are not exercised. Say so in the proof.

Selectors are in the feature files. The app has few ARIA labels: prefer visible text and
roles, and `form input >> nth=0` style positions only where the feature file gives them.

## Evidence

Write every artifact under `test-results/verify/<run>/<feature>/`. The folder is gitignored.
Pick one `<run>` name per verification, for example the date and the branch.

A proof holds, in this order:

1. The user action: `steps.log`, which `browser` appends to on every step.
2. The resulting screen: an `aria` snapshot and a `shot` screenshot taken after the action.
3. A second view of the stored value, read another way: `hntd-verify client jobs`,
   `client pending` or `client results`, saved to a file in the same folder.

Rules:

- Drive the real path. Create a search through the form, not through `client create`, when the
  form is what you changed.
- A redirect or a toast is not proof. Reopen the record from the overview.
- `console.log` in the evidence folder holds browser console errors. Read it. An empty folder
  entry means none.
- State what `seed-results` skipped whenever a proof uses it.

## Cleanup

```bash
hntd-verify stop
```

`stop` sends TERM to the `run.sh` it started, waits for the app and the Convex backend to go,
releases the worker lock, puts the database snapshot back, and deletes the files `seed-results`
wrote to `skill/output/`.
It never kills by process name. The database the run left moves to `.convex/verify/last-run-db`
and stays there until the next run ends. Everything under `test-results/verify/` survives.

Run `stop` after a failed attempt too. While `.convex/verify/db-before` exists, `launch`
refuses to start, because starting would snapshot the run's data as if it were the user's.

## Helpers

- [`scripts/hntd-verify`](scripts/hntd-verify) is the harness: `launch`, `doctor`, `stop`,
  `browser`, `client`, `api`, `seed-results`. Run it with no argument for the usage text.
- [`scripts/browser.mjs`](scripts/browser.mjs) is the browser driver. It uses the Playwright in
  `node_modules` with the installed Google Chrome, and falls back to Playwright's Chromium
  (`npx playwright install chromium`).

## Keeping it honest

`/pstack:maintain-verification-skill` re-reads the code behind each feature file, drives every
recipe in one session, and proposes corrections.
