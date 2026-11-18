<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/hero-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset=".github/assets/hero-light.svg">
    <img alt="HNTD: hire from the code, not the CV" src=".github/assets/hero-light.svg" width="100%">
  </picture>
</p>

<h3 align="center">Hire from the code, not the CV.</h3>

<p align="center">
  <a href="LICENSE"><img alt="License: AGPL-3.0" src="https://img.shields.io/badge/license-AGPL--3.0-blue"></a>
  <img alt="Self-hosted" src="https://img.shields.io/badge/self--hosted-yes-2ea44f">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-16-black">
  <img alt="Convex" src="https://img.shields.io/badge/Convex-local-orange">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-bring%20your%20own-d97757">
</p>

HNTD finds developers on GitHub and ranks them by the code they actually wrote. You describe the
role. HNTD searches public GitHub profiles, reads their repositories with your own Claude, scores
each one, and shows a ranked shortlist in a live dashboard. This repository runs the whole thing on
your machine. A hosted version runs at [hntd.it](https://hntd.it).

## Why

- **Code is the evidence.** A CV says what someone claims. Their repositories show how they work.
- **The best people are often invisible.** Many strong engineers have no LinkedIn presence, but
  their work is public on GitHub.
- **Your data stays yours.** Searches, shortlists and scores live in a database on your machine.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/flow-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset=".github/assets/flow-light.svg">
    <img alt="Describe, search, score, rank" src=".github/assets/flow-light.svg" width="100%">
  </picture>
</p>

## Quickstart

You need Node.js 20 or later, npm, git, openssl and Python 3. To run searches you also need the
[GitHub CLI](https://cli.github.com) (`gh`) and [Claude Code](https://claude.com/claude-code)
(`claude`), both signed in.

```bash
git clone https://github.com/uppifyagency/HNTD-OpenSource.git
cd HNTD-OpenSource
npm ci
scripts/local/setup.sh
npm run local
```

Open <http://127.0.0.1:3000/dashboard>. To use another port, run `PORT=3001 npm run local`.

`scripts/local/setup.sh` is safe to rerun. It creates `.env.local`, a signing key for the local
session, a local Convex database, `skill/scripts/.env` for the pipeline, and a Python virtual
environment in `skill/scripts/.venv`. It refuses to overwrite an `.env.local` that is not a
local-mode file, or a `skill/scripts/.env` that points off this machine. `npm run local` starts the database and the app, and
binds the app to `127.0.0.1` only. Press Ctrl-C to stop both.

### Run a search (beta)

> [!WARNING]
> The search pipeline is in beta. It runs in production on the hosted version, but nobody has
> run it end to end in local mode yet. Expect rough edges. If a step fails, please
> [open an issue](https://github.com/uppifyagency/HNTD-OpenSource/issues) with the command you ran
> and its output.

1. In the dashboard, create a search: languages and location, or a pasted job description.
2. Sign in to GitHub once with `gh auth login`.
3. Start Claude Code in the repository folder and run `/github-hr run`.

Claude Code then works through the pipeline in `skill/`: it searches GitHub with `gh`, fetches
profiles and repositories, scores each candidate, and pushes the results to your local database.
The dashboard shows the shortlist as soon as the results are pushed. `/github-hr help` lists every command.

## Bring your own AI

HNTD has no AI account of its own. It uses the Claude Code CLI you already have installed, signed
in with your own account.

- **Your account, your machine.** HNTD starts the `claude` command as your user, on your machine,
  the same way you would in a terminal. Local mode serves one user: you.
- **Credentials are never read.** HNTD does not open, copy or store your Claude login. The `claude`
  CLI handles its own authentication.
- **Locked-down calls.** When the app asks Claude to read a search query, it runs `claude -p` with
  no tools, no MCP servers, and none of your personal Claude Code settings or plugins.
- **API key alternative.** Set `ANTHROPIC_API_KEY` in `.env.local` and the app calls the Anthropic
  API directly instead of the CLI. Claude Code itself also accepts an API key for the pipeline.
- **Codex is not supported yet.** Running the pipeline on the OpenAI Codex CLI is on the roadmap.

## What leaves your machine

| Data | Goes to | Why |
|---|---|---|
| Search queries, profile and repository reads | GitHub API, through `gh` | To find and fetch candidates |
| Repository content, profile text, job description | Anthropic, through your Claude Code | To score candidates |
| Searches, shortlists, scores | Nowhere. A local Convex database in `.convex/` | |

Installing and building also download npm packages, the Convex local backend binary, and the web
fonts the app uses (through `next/font/google`).

## Architecture

| Layer | Technology | In local mode |
|---|---|---|
| Web app | Next.js 16 (App Router), React 19, Tailwind CSS | `next dev` on 127.0.0.1 |
| Database and API | [Convex](https://convex.dev) | Local backend started by `npx convex dev` |
| Sign-in | Session seam in `src/lib/session/` | One local user, signed with a key `setup.sh` generates. No accounts. |
| Pipeline | Claude Code skill in `skill/`, Python scripts in `skill/scripts/` | Runs in your Claude Code |
| GitHub data | Official GitHub API through `gh`. No HTML scraping. | Your `gh` login |

The same code also runs as a hosted, multi-user service with Clerk sign-in and Stripe billing. Local
mode switches those off: no Clerk, no Stripe, no paywall.

## Roadmap

- Codex CLI as an alternative to Claude Code.
- A fully English interface. Much of the interface text is in Italian today.
- A one-command start for the pipeline from the dashboard.

## Contributing

Issues and pull requests are welcome. Before you open a pull request, run the checks:

```bash
npm test                 # frontend and Convex unit tests (vitest)
npm run build            # type-check and build
python3 -m venv skill/scripts/.venv
skill/scripts/.venv/bin/pip install -r skill/scripts/requirements-dev.txt
skill/scripts/run-tests.sh   # pipeline tests
```

`npm run lint` reports errors that already exist in the code. Fixing them is a good first
contribution. `AGENTS.md` has notes for working on the code with an AI coding agent.

## License

Copyright (C) 2026 the HNTD authors.

HNTD is free software under the [GNU Affero General Public License v3.0](LICENSE). If you run a
modified version as a network service, the AGPL requires you to offer its source code to the users
of that service.
