# Candidate pipeline

A recruiter saves candidates to a personal pipeline and moves each card through four columns:
saved, contacted, in interview and pass.

## Sub-features

- `pipeline-save` saves a candidate from the dossier, and the button turns into `♥ In pipeline`.
- `pipeline-board` shows the card in the `saved` column with a count of active candidates.
- `pipeline-move` moves the card with `→ contacted`, `→ interview`, `→ pass` and `→ saved`.
- `pipeline-remove` removes the card with `✕`.
- `pipeline-empty` shows `Pipeline vuota.` when no card is left.
- `pipeline-export` downloads the board as CSV and as PDF.

## How to get to it (user POV)

- Choose `♡ Save to pipeline` on a candidate's dossier.
- Choose `pipeline` in the top navigation, or `Your Pipeline` on the overview.
- Open `/dashboard/pipeline` directly.

## Driving it with hntd-verify

Preconditions:

- The baseline in [README.md](./README.md) holds.
- A completed search with seeded results exists. See [Search results](./search-results.md).
- `Alice Developer` is not in the pipeline.

- **Save.** Run `hntd-verify browser --out <dir> goto /dashboard/tasks/<TASK_ID> click 'text="Alice Developer"' url '/dashboard/developer/' click 'role=button[name=/Save to pipeline/]' expect 'role=button[name=/In pipeline/]'`. The button reads `♥ In pipeline`.
- **See the card.** Add `goto /dashboard/pipeline expect '.kcol:has(.kcol__head:has-text("saved")) >> text="Alice Developer"' aria saved shot saved`. The heading reads `Pipeline. 1 attivi.` and the card offers `→ contacted`, `→ interview`, `✉` and `✕`.
- **Move to contacted.** Add `click 'role=button[name="→ contacted"]' url '/dashboard/pipeline$' expect '.kcol:has(.kcol__head:has-text("contacted")) >> text="Alice Developer"'`. The card sits in `contacted` and the page is still the pipeline. The `url` step fails today. See `Gotchas`.
- **Move to interview.** `goto /dashboard/pipeline`, then `click 'role=button[name="→ interview"]'`, `goto /dashboard/pipeline` and `expect '.kcol:has(.kcol__head:has-text("in interview")) >> text="Alice Developer"'`.
- **Move to pass.** `click 'role=button[name="→ pass"]'`, `goto /dashboard/pipeline` and `expect '.kcol:has(.kcol__head:has-text("pass")) >> text="Alice Developer"'`. The heading reads `Pipeline. 0 attivi.`.
- **Move back.** `click 'role=button[name="→ saved"]'`, `goto /dashboard/pipeline` and expect the card under `saved`.
- **Remove.** `click 'role=button[name="✕"]'`, `goto /dashboard/pipeline` and `expect 'text="Pipeline vuota."' aria emptied`.

## Gotchas

- Known defect: every button on a card also opens the candidate's dossier. The whole card is a link and the buttons sit inside it, so the click moves the card and then leaves the page. The move is saved. Until this is fixed, `goto /dashboard/pipeline` after each click to see the result, and report the failed `url` step.
- The same nesting puts the `✉` link inside the card link. The browser console logs a hydration error for it on every load.
- A column header and its count are separate elements. `text=/contacted 1/` never matches. Use the `.kcol:has(...)` selector.
- A card in `pass` does not count as active, so the heading can read `0 attivi` with one card on the board.
- CSV and PDF export here were not driven. Use `download` as in [Search results](./search-results.md).
