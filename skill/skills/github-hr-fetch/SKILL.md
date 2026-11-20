---
name: github-hr-fetch
description: >
  Fetch-only command for a single task. Runs Phase 0-1 (search + fetch + activity ranking + save).
  Use for manual recovery or debugging. Produces skill/output/fetch-<TASK_ID>.json.
---

# /github-hr fetch <TASK_ID>

Standalone fetch command. Runs Phase 0-1 from the main pipeline for a single task.

## Arguments

- `<TASK_ID>`: Required. The Convex task ID to process.

## Prerequisites

- GitHub CLI signed in (`gh auth status`)
- `skill/scripts/.env` must have valid CONVEX_SITE_URL and API_SECRET
- Python venv active

## Execution

### Step 1: Load task parameters

```bash
source skill/scripts/.venv/bin/activate
python -c "
from skill.scripts.convex_client import get_pending_tasks
import json
tasks = get_pending_tasks()
task = next((t for t in tasks if t['_id'] == '<TASK_ID>'), None)
if task: print(json.dumps(task, indent=2))
else: print('Task not found or not pending')
"
```

If the task is not found in pending, it is not claimable. A task left in `processing` by a
crashed run needs `/github-hr reset <TASK_ID>` first, and only if no other run is working on it.

### Step 2: Claim the task

```bash
python skill/scripts/convex_client.py claim <TASK_ID>
```
- Exit 0: this run holds the task. Go on.
- Any other exit: another run holds the task, or it is not pending, or it is gone. Do NOT work
  on it and do NOT mark it failed. Print the command's output and stop.

A write that reports the claim lost: follow the **Lost claim** rule in `skill/skills/github-hr-run/SKILL.md`.

### Step 3: Check if fetch already exists

```bash
ls skill/output/fetch-<TASK_ID>.json 2>/dev/null
```

If the file already exists and is valid JSON with developer data, **SKIP the fetch** and print:
```
[fetch] fetch-<TASK_ID>.json already exists with N developers. Skipping.
```

### Step 4: Execute Phase 1 (1.2 through 1.5)

Follow the exact same steps as Phase 1 in `skill/skills/github-hr-run/SKILL.md`:
- 1.2: Build search queries
- 1.3: Search developers with `github_search.py` (`gh api`)
- 1.4.0: Fetch profilo completo (OBBLIGATORIO)
- 1.4.1: Get top repos and data
- 1.4.2: Activity-weighted ranking
- 1.5: Save pre-fetch data to `skill/output/fetch-<TASK_ID>.json`

### Step 5: Report

Print summary:
```
[fetch] Completed. N developers saved to skill/output/fetch-<TASK_ID>.json
```

Do NOT proceed to scoring or pushing. This command only fetches.
