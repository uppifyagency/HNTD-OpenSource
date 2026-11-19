# Talent pool

The talent pool lists every developer the pipeline has analysed and summarised, across all
searches, and lets the recruiter find profiles by describing them.

## Sub-features

- `pool-browse` lists pre-analysed developers with a count and category filters.
- `pool-empty` shows `Nessuno sviluppatore in questa categoria.` when the pool is empty.
- `pool-search` ranks the pool against a free-text description, using Claude.
- `pool-clear` returns from search results to the full list with `pulisci ricerca`.
- `pool-save` saves a developer to the pipeline from the list.

## How to get to it (user POV)

- Choose `talent` in the top navigation, or `Browse Candidates` on the overview.
- Open `/dashboard/talent-pool` directly.
- Choose `[ sfoglia talent pool ]` on an empty pipeline.

## Driving it with hntd-verify

Preconditions:

- The baseline in [README.md](./README.md) holds.
- For `pool-empty`: the database has no developer with an HR summary. A fresh setup has none.
- For the other sub-features: at least one developer has an HR summary. See `Gotchas`.

- **Empty pool.** Run `hntd-verify browser --out <dir> goto /dashboard/talent-pool expect 'text=/0 sviluppatori pre-analizzati/' aria talent-empty shot talent-empty`. The page shows the search box `Descrivi il profilo che cerchi…`, a disabled `[ cerca ]`, the filter `all 0` and the empty message.
- **Search box.** Add `fill 'input[placeholder^="Descrivi il profilo"]' 'python backend' expect 'button:has-text("[ cerca ]"):not([disabled])'`. The button becomes enabled once the box has text.

## Gotchas

- Candidates pushed by a search do not appear here. The pool lists only developers with an HR summary, which a separate pipeline step writes (`skill/skills/github-hr-hr-summary`). After `seed-results` the pool still reads `0 sviluppatori pre-analizzati`.
- Nothing in this harness seeds an HR summary yet, so `pool-browse`, `pool-clear` and `pool-save` were not driven. Report them as not verified. Do not count the empty state as coverage for them.
- `pool-search` calls the `claude` CLI, or the Anthropic API when `ANTHROPIC_API_KEY` is set. It needs a signed-in Claude Code, costs tokens and takes seconds. It was not driven. Confirm with the user before you run it.
- Known defect: on a database with no user row, opening `/dashboard/talent-pool` as the very first page fails with `Unauthorized: user not found`. The page asks for the pool before the first visit has created the user. A reload fixes it. `launch` opens the printed link first, which lands on `/dashboard`, so a recipe does not hit this. To replay it on a database with no user row, run `HNTD_VERIFY_SKIP_FIRST_VISIT=1 hntd-verify launch`, then `hntd-verify browser --out <dir> goto /dashboard/talent-pool expect 'text=/sviluppatori pre-analizzati/'`. The step fails and `console.log` holds the error.
