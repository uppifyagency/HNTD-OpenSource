---
name: github-hr-push
description: >
  Push-only command for a single task. Runs Phase 3-4 (push results to Convex + complete task).
  Wrapper around push_results.py. Safe to re-run (idempotent upsert).
---

# /github-hr push <TASK_ID>

Standalone push command. Invokes `push_results.py` to merge fetch + score data and push to Convex.

## Arguments

- `<TASK_ID>`: Required. The Convex task ID to push.
- `--dry-run`: Optional. Print what would be pushed without actually pushing.

## Prerequisites

- `skill/output/fetch-<TASK_ID>.json` must exist
- At least one `skill/output/score-<TASK_ID>-batch-*.json` must exist
- `skill/scripts/.env` must have valid CONVEX_SITE_URL and API_SECRET
- Python venv active

## Execution

**ALWAYS pass `--max-results` (QT-16).** Without it `push_results.py` skips the
trim and publishes every scored developer, ignoring the recruiter's
`task.params.maxResults`. Read the value from the task first:

```bash
source skill/scripts/.venv/bin/activate
# Read task.params.maxResults
python skill/scripts/convex_client.py task <TASK_ID>
python skill/scripts/push_results.py <TASK_ID> --max-results <task.params.maxResults>
```

Or for dry-run:
```bash
python skill/scripts/push_results.py <TASK_ID> --dry-run --max-results <task.params.maxResults>
```

The script is idempotent — `upsert_developer` uses `githubId` as the unique key.
Re-running safely updates existing developers and adds any missing ones (e.g., from batch-0).
