# Pipeline terminal

The pipeline is the second user surface. In Claude Code, `/github-hr` commands list the queue,
process searches, and reset or delete them. Each command wraps
`skill/scripts/convex_client.py`, which talks to the same database as the dashboard.

## Sub-features

- `term-status` lists pending searches as JSON (`/github-hr status`).
- `term-jobs` prints every search with user, status, mode and result count (`/github-hr jobs`).
- `term-results` prints the ranked shortlist of one search (`/github-hr results <ID>`).
- `term-create` creates a search without the dashboard (`/github-hr create <USER_ID>`).
- `term-claim` takes a queued search for one run and refuses every other run (`convex_client.py claim <ID>`).
- `term-reset` puts a search back in the queue and deletes its results (`/github-hr reset <ID>`).
- `term-delete` deletes a search and its results (`/github-hr delete <ID>`).
- `term-push` pushes scored candidates and completes the search (`/github-hr push <ID>`).
- `term-run` runs the whole pipeline on a search (`/github-hr run --task <ID>`). In local mode
  the worker started by `npm run local` does this for every queued search.

## How to get to it (user POV)

- Start Claude Code in the repository and type a `/github-hr` command.
- Run `skill/scripts/.venv/bin/python skill/scripts/convex_client.py <command>` in a terminal.

## Driving it with hntd-verify

Preconditions:

- The baseline in [README.md](./README.md) holds.
- A queued search exists, made with [Create a search](./create-search.md).

- **Jobs.** Run `hntd-verify client jobs`. One row per search: `Local user`, a status such as `○ pending`, the mode, the result count and the task ID.
- **Status.** Run `hntd-verify client pending`. A JSON array of the pending searches with their `params`.
- **Create.** Read the user ID with `hntd-verify api GET /api/users-dashboard`, then run `hntd-verify client create <USER_ID> --lang Python --loc italy --max 20`. It prints `Task created: <TASK_ID>` and the dashboard overview lists a new `Python — italy` row.
- **Push.** Run `hntd-verify seed-results <TASK_ID>`. It ends with `Pushed 4 developers` and `Task completed: {'ok': True}`, and `client jobs` shows `● completed` with 4 results.
- **Results.** Run `hntd-verify client results <TASK_ID>`. Four rows, `alice-fullstack` first, then `Total: 4 developers`.
- **Claim.** Run `skill/scripts/.venv/bin/python skill/scripts/convex_client.py claim <TASK_ID>` twice on a queued search. The first prints `claimed: pending -> processing` and exits 0. The second prints `not claimed: it is processing` with the reset hint and exits 3.
- **Fail, then reset.** Run `hntd-verify api POST /api/update-task-status '{"taskId":"<TASK_ID>","status":"failed","error":"verify: forced failure"}'`. `client jobs` shows `◐ failed` and the dashboard page shows the error text. Then run `hntd-verify client reset <TASK_ID>`. It prints `reset to pending`, and `client results <TASK_ID>` prints `No results found for this task.`
- **Delete.** Run `hntd-verify client delete <TASK_ID>`. It prints `deleted (with results)` and `client jobs` no longer lists the ID.

## Gotchas

- `term-run` and the worker were not driven. A run needs a GitHub token, `claude` signed in, the network, several minutes and Claude tokens. Confirm with the user before you launch with `HNTD_VERIFY_WORKER=1`.
- `client create` needs the Convex user ID, not the name. The local user row exists only after a browser has opened `/dashboard` once. Before that, `client users` prints `No users found.` `launch` makes that first visit through the printed link.
- `client` reads `skill/scripts/.env`. `run.sh` rewrites that file on every start, because the backend port can change. The file can hold a `GH_TOKEN`. Never print it.
- `term-push` proves the push step alone when it runs through `seed-results`.
- `update-task-status` sets only `pending` and `failed`. `processing` and `completed` answer HTTP 400: only `claim-task` starts a search (from `pending`, once) and only `complete-task` completes it, together with its result list. A completed search refuses the other three with HTTP 409 (`code: "invalid_transition"`), so only a reset or a delete takes it out of `completed`. See [the statechart](../statechart/README.md).
- Run pipeline tests with `skill/scripts/run-tests.sh`, never with a bare `pytest`.
