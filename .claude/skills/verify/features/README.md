# HNTD verification map

This directory is the maintained source for verifying the user-facing behavior of HNTD in
local mode. Read this index before you drive the app, then use the matching feature file as
the recipe.

## Baseline preconditions

- `hntd-verify` means `.claude/skills/verify/scripts/hntd-verify`, run from the repo root.
- `hntd-verify launch` printed `READY` and `hntd-verify doctor` exits 0.
- The pipeline worker is off, so a search a recipe creates stays `pending` until the recipe
  changes it. The dashboard shows the banner `Pipeline locale non attiva` on every page.
- The instance is the one this run launched. Never drive the user's own `npm run local`.
- The database is a copy of the user's local database, so it can hold their searches and
  candidates. A recipe never assumes an empty list. It finds its own records by name.
- Pick one run folder and reuse it: `test-results/verify/<run>/`.

## Driving conventions

- Every search a recipe creates uses the city `Verifyville`, so its title is
  `python — italy, Verifyville` and no real search has that name.
- `seed-results` candidates are `Alice Developer`, `Dave DevOps`, `Bob Backend` and
  `Carol Junior`, with logins `alice-fullstack`, `dave-devops`, `bob-backend`, `carol-junior`.
- Treat every command as literal. Keep quotes, brackets and arrows unchanged. The interface
  text is Italian and English mixed, and the brackets in `[ avvia ricerca ]` are part of it.
- One `hntd-verify browser` call is one page session. Put the steps of one journey in one call.
- The task ID is the last part of the URL `/dashboard/tasks/<TASK_ID>`. `steps.log` records it,
  and `hntd-verify client jobs` lists it.
- `hntd-verify stop` restores the database. Do not hand-delete records to clean up.

## Proof and skip reporting

- Capture the action (`steps.log`) and the resulting state (`aria` and `shot` after it).
- A mutation proof adds a second view: `hntd-verify client jobs`, `client pending` or
  `client results <TASK_ID>`, saved in the same folder.
- A proof that uses `seed-results` says that search, fetch and scoring did not run.
- Report an entry point you could not reach with the command you tried and the reason.
- Do not report a skipped entry point as verified through another one.
- A recipe step that fails because of a known defect stays in the recipe. The defect is listed
  in that file's `Gotchas`. Report the failure. Do not route around it.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph on the user-visible behavior.
It then has exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with hntd-verify` starts with `Preconditions:` and pairs each user action with
   an exact command and an observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

Keep implementation details out of the map. Name only user paths, stable handles, required
state, commands and observable proof.

## Features

Every recipe below ran green on 2026-11-19 at commit `eb9d2b0`, except the steps its
`Gotchas` names.

- [Create a search](./create-search.md) covers the JD form, the quick form, validation, the
  overview row and the queued search page.
- [Search results](./search-results.md) covers the ranked shortlist, sorting, CSV and PDF
  export, the candidate dossier and deleting a search.
- [Candidate pipeline](./candidate-pipeline.md) covers saving a candidate, moving the card
  through the four columns and removing it.
- [Talent pool](./talent-pool.md) covers browsing pre-analysed developers and the AI search box.
- [Pipeline terminal](./pipeline-terminal.md) covers the queue, results, reset and delete
  commands of the pipeline client, and what a full `/github-hr run` needs.

The state map of one search, with the rules it breaks and how to replay each break, is in
[`../statechart/README.md`](../statechart/README.md).
