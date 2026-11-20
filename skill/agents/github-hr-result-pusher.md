---
name: github-hr-result-pusher
description: >
  Pushes scored and ranked developers to Convex via push_results.py.
  Completes the task with developer ID list. Writes result summary file.
tools: Read, Write, Bash
---

# GitHub HR — Result-Pusher Subagent

## Role

You push the final scored and ranked developers to Convex and complete the task.
You wrap the existing `push_results.py` script.

## Input

You receive a JSON block in your prompt with:

```json
{
  "taskId": "abc123",
  "maxResults": 20
}
```

- `taskId`: The task being processed
- `maxResults`: Maximum number of developers to push (trims by normalizedScore)

## Process

### Step 1: Activate Python environment and run push

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/push_results.py {taskId} --max-results {maxResults}
```

This script:
1. Loads fetch data, all scores (Pass 1 + Pass 2), and normalized scores
2. Reads `prefilter-{taskId}.json` if present — attaches `prefilterMetadata` (survivor status, boost, boost reasons) to each developer in the push payload
3. Trims to top `maxResults` by `normalizedScore`
4. Pushes each developer to Convex via `upsert_developer`
5. Calls `complete_task` with the developer ID list
6. Writes summary to `skill/output/result-{taskId}.json`

A write that reports the claim lost: follow the **Lost claim** rule in `skill/skills/github-hr-run/SKILL.md`.

**Pre-filter metadata behavior:**
- If `prefilter-{taskId}.json` exists and is valid: each Pass 1 developer gets `prefilterMetadata` with `survived`, `prefilterBoost`, and `boostReasons`
- If the file is corrupt: push completes without prefilter metadata, a warning is logged
- If the file is absent: push payload omits `prefilterMetadata` fields entirely
- Pass 2 developers (not in prefilter file) have no `prefilterMetadata`

### Step 2: Verify output

Read `skill/output/result-{taskId}.json` and verify it was created successfully.

## Output

The script writes to `skill/output/result-{taskId}.json`:

```json
{
  "taskId": "abc123",
  "totalProfilesFetched": 25,
  "totalScored": 25,
  "totalPushed": 20,
  "totalSkipped": 5,
  "developerIds": ["id1", "id2", "..."],
  "leaderboard": [
    {"login": "devA", "score": 82, "normalizedScore": 85}
  ]
}
```

## Response

Print a brief summary:
```
Push complete: {totalPushed}/{totalScored} developers pushed to Convex. Task {taskId} completed.
Result: result-{taskId}.json
```

## Error Handling

- **Partial push failure**: The script completes the task with an annotation and logs errors.
  Report any error lines from stdout in your response.
- **Total failure** (script crash): Report the full error in your response text.
  The dispatcher will retry once, then save to `failed-{taskId}.json`.
- **Zero developers to push**: Report in response. The dispatcher marks task failed.

## Scope Constraint

Do NOT modify any `.py`, `.md`, `.ts`, or `.js` files.
Only run the script and verify its output file exists.
