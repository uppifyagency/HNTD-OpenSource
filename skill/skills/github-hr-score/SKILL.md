---
name: github-hr-score
description: >
  Score-only command for a single task. Runs Phase 2 (parallel scoring with batch skip logic).
  Use for manual recovery after a crash during scoring. Skips already-completed batches.
---

# /github-hr score <TASK_ID>

Standalone scoring command. Runs Phase 2 from the main pipeline with automatic skip for completed batches.

## Arguments

- `<TASK_ID>`: Required. The Convex task ID to score.

## Prerequisites

- `skill/output/fetch-<TASK_ID>.json` must exist. If not, error: "Run /github-hr fetch <TASK_ID> first"
- Python venv active

## Execution

### Step 1: Load fetch data

```bash
source skill/scripts/.venv/bin/activate
```

Read `skill/output/fetch-<TASK_ID>.json`. If the file does not exist, print an error and exit:
```
[score] ERROR: fetch-<TASK_ID>.json not found. Run /github-hr fetch <TASK_ID> first.
```

### Step 2: Calculate batches

Count developers in the fetch file. Choose batch size adaptively:

| Developers | Batch size |
|---|---|
| ≤ 30 | 3 |
| 31-40 | 4 |
| 41-50 | 5 |
| > 50 | 6 |

Calculate number of batches: `ceil(N / batch_size)`.

### Step 3: Score with skip logic

For each batch (0 to num_batches-1):

1. Check if `skill/output/score-<TASK_ID>-batch-<N>.json` exists
2. If it exists AND contains valid `scores` array with entries:
   - **SKIP** this batch
   - Log: `[score] Batch N already scored (K developers). Skipping.`
3. If it does NOT exist:
   - Read `skill/agents/github-hr-scorer.md` for the scorer prompt
   - Build the batch input JSON. If the task has `params.country`, include `"targetCountry": "<country>"` in the batch input JSON. Otherwise set it to `null`.
   - Spawn a subagent via Agent tool with the batch data
   - Tell the subagent to write results to `skill/output/score-<TASK_ID>-batch-<N>.json`

Launch all non-skipped subagents in parallel (up to 10 concurrent Agent calls).

### Step 4: Summary

After all batches complete, print:
```
[score] Completed. N scored, M skipped (already done), K failed.
```

Do NOT proceed to pushing. This command only scores.
