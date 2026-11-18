---
name: github-hr-rank
description: >
  Rank-only command for a single task. Runs Phase 2.7 (comparative re-evaluation).
  Use for manual recovery or to re-rank after scoring is complete.
---

# /github-hr rank <TASK_ID>

Standalone comparative re-evaluation. Runs Phase 2.7 from the main pipeline.

## Arguments

- `<TASK_ID>`: Required. The Convex task ID to rank.

## Prerequisites

- `skill/output/fetch-<TASK_ID>.json` must exist
- At least one `skill/output/score-<TASK_ID>-batch-*.json` must exist
- Python venv active

## Execution

### Step 1: Triage

```bash
source skill/scripts/.venv/bin/activate
python skill/scripts/triage_clusters.py <TASK_ID>
```

If 0 clusters found, log "All developers well-separated. No re-evaluation needed." and exit.

### Step 2: Load context

Read `skill/output/triage-<TASK_ID>.json`. For each cluster:

1. Extract full developer data from `skill/output/fetch-<TASK_ID>.json` for logins in cluster
2. Extract Pass 1 scores from score batch files for those logins
3. If a task file exists and `mode === "jd"`, include the scoringRubric
4. Note the nearest isolated developer scores above and below the cluster

### Step 3: Spawn cluster subagents

Read `skill/agents/github-hr-ranker.md` for the ranker prompt.

For each cluster, spawn a subagent (Agent tool, subagent_type "general-purpose"):
- Provide: ranker prompt + developer data + Pass 1 scores + rubric + global context
- Output target: `skill/output/rank-<TASK_ID>-cluster-<N>.json`

Launch ALL subagents **in parallel**.

### Step 4: Merge

```bash
python skill/scripts/merge_normalized.py <TASK_ID>
```

### Step 5: Summary

Print the normalized leaderboard:
```
[rank] Comparative re-evaluation complete.
  1. devC: normalizedScore=79 (raw=75) — "Best architecture in cluster..."
  2. devA: normalizedScore=76 (raw=78) — "Excellent code quality..."
  ...
```
