# Create a search

A recruiter describes a role, either by pasting a job description or by picking languages and
a country, and gets a queued search that the pipeline will process.

## Sub-features

- `create-jd` creates a search from a pasted job description of 50 characters or more.
- `create-quick` creates a search from search terms, a country, an optional city and a
  minimum activity.
- `create-validate` keeps the submit button disabled until the active form is valid.
- `create-listed` shows the new search first in the overview, with its mode and date.
- `create-queued` shows the queued search page with `Task in coda.` and the line about the
  local pipeline.

## How to get to it (user POV)

- Choose `match` in the top navigation.
- Choose `+ new search`, `[ crea ricerca ]` or `New Search` on the overview at `/dashboard`.
- Open `/dashboard/new-task` directly.

## Driving it with hntd-verify

Preconditions:

- The baseline in [README.md](./README.md) holds.
- No search is titled `python — italy, Verifyville`.

- **Open the form.** Run `hntd-verify browser --out <dir> goto /dashboard/new-task expect 'text="New search."'`. The heading `New search.` shows, the `Da Job Description` card is active and `[ avvia ricerca ]` is disabled.
- **Quick mode.** Add `click 'text="Ricerca rapida"'`. The fields `search terms *`, `country *`, `city / region (opzionale)` and `min activity (mesi)` appear and `max results` drops to 20.
- **Add a term.** Add `type 'form input >> nth=0' python press Enter expect 'text="Python"'`. A `Python` tag with an `x` button appears.
- **Fill the rest.** Add `select 'form select >> nth=0' italy fill 'input[placeholder^="es. Vercelli"]' Verifyville expect 'button[type=submit]:not([disabled])'`. The submit button becomes enabled only now.
- **Submit.** Add `click 'button[type=submit]' url '/dashboard$' expect 'role=link[name="python — italy, Verifyville"]' aria overview shot overview`. The overview opens and its first row reads `python — italy, Verifyville · Quick search`.
- **Open the queued search.** Add `click 'role=link[name="python — italy, Verifyville"]' url '/dashboard/tasks/' expect 'text="Task in coda."' aria queued shot queued`. The page shows the badge `pending`, `Task in coda.` and `La pipeline locale la avvia appena è libera, una ricerca alla volta.`
- **Second view.** Run `hntd-verify client pending`. The JSON holds one task with `"city": "Verifyville"`, `"languages": ["python"]`, `"mode": "manual"` and `"status": "pending"`.
- **JD mode.** Run `hntd-verify browser --out <dir> goto /dashboard/new-task fill 'textarea' 'Senior backend engineer in Milan. Python and PostgreSQL, five years of experience, REST APIs, Docker.' expect 'button[type=submit]:not([disabled])' click 'button[type=submit]' url '/dashboard$' expect 'main table a' aria overview-jd`. The first row reads `JD Search · JD mode`, and `hntd-verify client jobs` shows a `pending` row with mode `jd`.

## Gotchas

- The term box loses its placeholder after the first tag. Address it as `form input >> nth=0`.
- `fill` does not add a tag. The box reacts to the Enter and comma keys, so use `type` then `press Enter`.
- Every JD search is titled `JD Search` until the pipeline parses it. Tell two apart by task ID.
- A job description shorter than 50 characters leaves the button disabled with no message.
- With the worker on, a queued search starts within seconds and the page moves to `processing`. The harness keeps the worker off, so here it stays `pending`.
- `[ elabora ora ]` and the cron sentence exist only in cloud mode. This harness cannot reach them.
