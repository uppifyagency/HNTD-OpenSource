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
- **Move through the columns.** In the same browser call, with no `goto` between moves, add:
  - `click 'role=button[name="→ contacted"]' url '/dashboard/pipeline$' expect '.kcol:has(.kcol__head:has-text("contacted")) >> text="Alice Developer"'`
  - `click 'role=button[name="→ interview"]' url '/dashboard/pipeline$' expect '.kcol:has(.kcol__head:has-text("in interview")) >> text="Alice Developer"'`
  - `click 'role=button[name="→ pass"]' url '/dashboard/pipeline$' expect '.kcol:has(.kcol__head:has-text("pass")) >> text="Alice Developer"'`. The heading reads `Pipeline. 0 attivi.`.
  - `click 'role=button[name="→ saved"]' url '/dashboard/pipeline$' expect '.kcol:has(.kcol__head:has-text("saved")) >> text="Alice Developer"'`

  Each move keeps the page on the pipeline.
- **Open the dossier from the card.** Add `click 'role=link[name="Alice Developer"]' url '/dashboard/developer/'`. Only the candidate's name is a link. Then `goto /dashboard/pipeline` to come back.
- **Remove.** Add `click 'role=button[name="✕"]' url '/dashboard/pipeline$' expect 'text="Pipeline vuota."' aria emptied`.

## Gotchas

- A column header and its count are separate elements. `text=/contacted 1/` never matches. Use the `.kcol:has(...)` selector.
- A card in `pass` does not count as active, so the heading can read `0 attivi` with one card on the board.
- CSV and PDF export here were not driven. Use `download` as in [Search results](./search-results.md).
