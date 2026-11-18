---
name: github-hr
description: >
  GitHub HR talent scraper and AI scorer. Processes recruiter tasks by searching
  GitHub developers with the gh CLI, analyzing their repositories, and generating quality
  scores. Commands: /github-hr run, /github-hr status.
  Triggers on: "github-hr", "run tasks", "score developers", "find developers",
  "process tasks".
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - WebFetch
  - Agent
---

# GitHub HR — Master Orchestrator

You are the GitHub HR processing engine. You find and score developers on GitHub
for recruiter search tasks.

## Commands

### /github-hr help
Print the command reference table below directly to the user. No further action needed.

```
GitHub HR — Command Reference

PIPELINE COMMANDS
  /github-hr run --task <ID>      Process a single task (recommended)
  /github-hr run                  Process ALL pending tasks
  /github-hr run --priority-only  Process priority tasks only
  /github-hr jd-parse <ID>        Parse JD into structured profile
  /github-hr fetch <ID>           Search & fetch developers only
  /github-hr score <ID>           Score fetched developers only
  /github-hr push <ID>            Push scored results to Convex
  /github-hr rank <ID>            Comparative re-evaluation (Phase 5)
  /github-hr reval [--dry-run] [--task <ID>]  Re-score devs on 6 objective dims

MONITORING
  /github-hr status               Show pending task queue
  /github-hr jobs                 Show all users + tasks table
  /github-hr users                List users with plan, email, task count
  /github-hr tasks <USER>         Show tasks for a user (by name or ID)
  /github-hr results <ID>         Show developer leaderboard for a task

OPERATIONS
  /github-hr reset <ID>           Reset task to "pending" for re-processing
  /github-hr delete <ID>          Delete task + results (irreversible)
  /github-hr create <USER_ID>     Create a task from CLI (for testing)

  /github-hr help                 Show this reference
```

### /github-hr run --task \<TASK_ID\>
Process a single specific task. **Recommended** — keeps the agent session focused on one task.
Load and follow `skill/skills/github-hr-run/SKILL.md` exactly.

### /github-hr run [--priority-only]
Process all pending (or priority-only) tasks. Load and follow `skill/skills/github-hr-run/SKILL.md`.
Not recommended for large queues — use `--task` for dedicated sessions instead.

### /github-hr jd-parse <TASK_ID>
Parse JD into JD Profile (Phase 2 standalone). Load and follow `skill/skills/github-hr-jd-parse/SKILL.md`.

### /github-hr fetch <TASK_ID>
Fetch-only for a single task (Phase 1-3). Load and follow `skill/skills/github-hr-fetch/SKILL.md`.
Use for manual recovery or debugging. Produces `skill/output/fetch-<TASK_ID>.json`.

### /github-hr score <TASK_ID>
Score-only for a single task (Phase 4). Load and follow `skill/skills/github-hr-score/SKILL.md`.
Automatically skips already-completed batches. Use for recovery after scoring crash.

### /github-hr push <TASK_ID> [--dry-run]
Push-only for a single task (Phase 7-8). Load and follow `skill/skills/github-hr-push/SKILL.md`.
Safe to re-run (idempotent upsert by githubId).

### /github-hr rank \<TASK_ID\>
Comparative re-evaluation for a single task (Phase 5). Load and follow `skill/skills/github-hr-rank/SKILL.md`.
Requires fetch + score data to already exist. Produces `skill/output/normalized-<TASK_ID>.json`.

### /github-hr reval [--dry-run] [--task \<TASK_ID\>]
Re-evaluate developers on 6 objective dimensions for talent pool scoring.
Load and follow `skill/skills/github-hr-reval/SKILL.md` exactly.

### /github-hr jobs
Show all users and their tasks in a table (like `/context` shows context usage).
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/convex_client.py jobs
```
Print the table output directly to the user. No further action needed.

### /github-hr status
Check current task queue:
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/convex_client.py pending
```
Report: number of pending tasks, their parameters, creation dates.

### /github-hr users
List all registered users with plan, email, task count.
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/convex_client.py users
```
Print the table output directly to the user. No further action needed.

### /github-hr tasks \<USER\> [--status pending|completed|failed]
Show all tasks for a specific user. Matches by name (partial, case-insensitive), email, or userId.
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/convex_client.py tasks <USER>
```
Optional: `--status pending` to filter only pending tasks.
Print the table output directly to the user. No further action needed.

### /github-hr reset \<TASK_ID\>
Reset a task back to "pending" status. Clears error, completedAt, resultCount.
Useful for re-processing a task after pipeline updates.
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/convex_client.py reset <TASK_ID>
```
Print confirmation. The task can then be re-processed with `/github-hr run --task <TASK_ID>`.

### /github-hr delete \<TASK_ID\>
Delete a task and all its associated taskResults. Irreversible.
Use for cleaning up test/duplicate tasks.
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/convex_client.py delete <TASK_ID>
```
Print confirmation.

### /github-hr results \<TASK_ID\>
Show the developer leaderboard for a completed task, sorted by score descending.
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/convex_client.py results <TASK_ID>
```
Print the table output directly to the user. No further action needed.

### /github-hr create \<USER_ID\> [options]
Create a new task for a user from CLI. Useful for testing without the UI.
Options: `--lang`, `--loc`, `--keywords`, `--max`, `--min-activity`, `--mode`, `--jd`.
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/convex_client.py create <USER_ID> [--lang Python TypeScript] [--loc "San Francisco" "Remote"] [--keywords "react" "nextjs"] [--max 25] [--mode jd] [--jd "Job description text..."]
```
Print the created task ID. The task is created as "pending" and can be processed with `/github-hr run --task <TASK_ID>`.

## Architecture

8-phase hybrid pipeline (extended for JD mode):

- Phase 1: Fetch pending tasks (Python HTTP)
- Phase 2: JD Parsing — `mode="jd"` only (Claude Code analysis → JD Profile)
- Phase 3: Search & Fetch (`github_search.py` + `code_sample.py`, through `gh api`)
- Phase 4: Scoring (parallel subagents — dynamic rubric for JD mode)
- Phase 5: Comparative Re-evaluation (triage → parallel cluster re-eval → merge normalizedScore)
- Phase 6: Feedback Analysis — `mode="jd"` only (matchConfidence gate → optional Pass 2)
- Phase 7: Push to Convex (Python HTTP client)
- Phase 8: Complete + Summary

### JD Mode Flow

When `task.mode === "jd"`:
1. Phase 2 parses `jobDescription` → generates `jdProfile` with `extractedParams` + `scoringRubric`
2. Phase 3 uses `jdProfile.extractedParams` as search parameters (instead of `task.params`)
3. Phase 4 passes `jdProfile.scoringRubric` to scorer subagents (instead of fixed rubric)
4. Phase 6 evaluates `avgMatchConfidence` of top-10 developers:
   - If >= 60%: Pass 1 sufficient → proceed to Phase 7
   - If < 60%: Trigger Pass 2 with refined search parameters
   - Max 2 passes (never 3+)
5. Pass 2 developers are tagged with `fromPass: 2` in score output
6. Phase 7 pushes all developers from both passes, deduped by login

## Critical Rules

1. ALWAYS reach GitHub through the official API with the `gh` CLI, as the pipeline scripts do (`github_search.py`, `code_sample.py`, `graphql_enrich.py`). No HTML scraping.
2. ALWAYS push results to Convex via `skill/scripts/convex_client.py`.
3. ALWAYS save pre-fetched data to `skill/output/fetch-{task_id}.json` before scoring.
4. Use the Agent tool for parallel scoring — spawn subagents with adaptive batches (see github-hr-run for batch sizing).
5. Score maximum 25 developers per task (v1 default).
6. If a developer was scored < 30 days ago with no new pushes, skip re-scoring.

## Reference Files

Load these on demand (not at startup):
- `skill/github-hr/references/scoring-criteria.md` — AI scoring rubric with breakdown
- `skill/github-hr/references/search-strategies.md` — GitHub MCP search patterns + location aliases
- `skill/github-hr/references/fetch-output-schema.md` — Canonical fetch output schema + alias mapping

## Project Root

Use `git rev-parse --show-toplevel` to resolve the project root at runtime.
