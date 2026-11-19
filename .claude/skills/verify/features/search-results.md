# Search results

When the pipeline completes a search, the recruiter sees a ranked shortlist, can sort it,
export it, open a candidate's dossier, and delete the search with its results.

## Sub-features

- `results-list` shows `Sviluppatori trovati: N` and one numbered row per candidate.
- `results-sort` sorts by `Match`, `Objective` or `Calibrated`, and flips direction on a second click.
- `results-export` downloads the shortlist as CSV and as PDF.
- `results-dossier` opens a candidate's dossier with scores, assessment and repositories.
- `results-delete` deletes the search and its results after a confirmation dialog.
- `results-missing` shows `Task non trovato.` for a search that no longer exists.

## How to get to it (user POV)

- Choose a search row in `your searches` on the overview at `/dashboard`.
- Open `/dashboard/tasks/<TASK_ID>` directly.
- Open `/dashboard/developer/<DEVELOPER_ID>` directly for the dossier.

## Driving it with hntd-verify

Preconditions:

- The baseline in [README.md](./README.md) holds.
- A search titled `python — italy, Verifyville` exists, made with [Create a search](./create-search.md).
- `hntd-verify seed-results <TASK_ID>` ended with `Task completed: {'ok': True}`.

- **Open the shortlist.** Run `hntd-verify browser --out <dir> goto /dashboard/tasks/<TASK_ID> expect 'role=heading[name="Sviluppatori trovati: 4"]' aria completed shot completed`. The badge reads `completed` and row `001` is `Alice Developer` with `82.4/100 calibrated`.
- **Read the first row.** Add `text 'main a[href^="/dashboard/developer/"] >> nth=0'`. It prints `001 Alice Developer 82.4/100 calibrated Milan, Italy · JavaScript · TypeScript 88% match`.
- **Sort by match.** Add `click 'role=button[name="Match"]' expect 'role=button[name=/^Match ▼/]'`. Row `001` stays `Alice Developer` and now shows `88/100 match`.
- **Flip the direction.** Add `click 'role=button[name=/^Match/]'` and read the first row again. The button reads `Match ▲` and row `001` is `Carol Junior` with `8/100 match`.
- **Export.** Add `download 'role=button[name="CSV"]' shortlist.csv download 'role=button[name="PDF"]' shortlist.pdf`. The CSV has a header starting `Name,Login,Location` and four rows in the order on screen. The PDF is a one-page PDF.
- **Open a dossier.** Add `click 'text="Alice Developer"' url '/dashboard/developer/' expect 'role=heading[name="Alice Developer"]' aria dossier shot dossier`. The dossier shows `78/100` as objective score, the six assessment lines, and the repositories table.
- **Second view.** Run `hntd-verify client results <TASK_ID>`. It lists the same four logins, `alice-fullstack` first with score 82, and ends with `Total: 4 developers`.
- **Cancel a delete.** Run `hntd-verify browser --out <dir> goto /dashboard/tasks/<TASK_ID> click 'role=button[name="[ elimina task ]"]' expect 'role=dialog[name="Eliminare il task?"]' click 'role=button[name="Annulla"]' absent 'role=dialog'`. The search is still there.
- **Delete.** Add `click 'role=button[name="[ elimina task ]"]' click 'role=button[name="Elimina"]' url '/dashboard$' absent 'role=link[name="python — italy, Verifyville"]'`. The overview no longer lists the search.
- **Confirm it is gone.** Add `goto /dashboard/tasks/<TASK_ID> expect 'text="Task non trovato."'`, then run `hntd-verify client jobs`. The task ID is absent.

## Gotchas

- Rows show the candidate's name, not the login. The login is the image's alt text.
- `seed-results` runs only the push. A green run here says nothing about search, fetch or scoring.
- `Calibrated` is the default sort and the first click on `Match` keeps Alice first. Click twice to see the order change.
- Candidate avatars load from GitHub over the network. A broken image is not an app failure.
- Deleting a search while a pipeline run works on it costs that run: its push ends with `Search <ID> was deleted while the pipeline ran` and stores nothing.
