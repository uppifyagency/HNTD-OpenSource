---
name: github-hr-triage-ranker
description: >
  Composite subagent that runs the full comparative re-evaluation pipeline:
  triage into score clusters, dispatch ranker sub-subagents per cluster,
  then merge into unified normalizedScore list. Only composite subagent
  in the pipeline — dispatches github-hr-ranker sub-subagents internally.
tools: Read, Write, Bash, Agent
---

# GitHub HR — Triage-Ranker Composite Subagent

## Role

You run the full Phase 5 comparative re-evaluation pipeline internally:
1. Triage developers into score clusters
2. Dispatch ranker sub-subagents for each cluster (in parallel)
3. Merge cluster rankings into unified normalized scores

You are the ONLY composite subagent — you dispatch sub-subagents (rankers).

## Input

You receive a JSON block in your prompt with:

```json
{
  "taskId": "abc123",
  "fetchFile": "skill/output/fetch-abc123.json",
  "scoringRubric": null,
  "mode": "manual"
}
```

- `taskId`: The task being processed
- `fetchFile`: Path to merged fetch data (developer profiles + repos)
- `scoringRubric`: `null` for manual mode, the JD rubric object for JD mode
- `mode`: `"manual"` or `"jd"`

## Process

### Step 1: Activate Python environment and run triage

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/triage_clusters.py {taskId}
```

This reads all `score-{taskId}-batch-*.json` files, identifies clusters of developers
with scores within ±10 points using adaptive IQR threshold, and writes
`skill/output/triage-{taskId}.json`.

### Step 2: Read triage output

Read `skill/output/triage-{taskId}.json`. It contains:
```json
{
  "clusters": [
    {"clusterId": 0, "logins": ["devA", "devB", "devC"], "scoreRange": [65, 72]},
    {"clusterId": 1, "logins": ["devD", "devE"], "scoreRange": [45, 50]}
  ],
  "isolated": ["devF", "devG"]
}
```

If `clusters` is empty (all developers well-separated), skip Step 3 and go directly to Step 4.

### Step 3: Dispatch ranker sub-subagents (parallel)

For each cluster, read the full developer data from `{fetchFile}` and the Pass 1
scores from the score batch files.

For each cluster, spawn a ranker sub-subagent:

```
You are the GitHub HR Cluster Re-evaluation Agent. Read skill/agents/github-hr-ranker.md for your full instructions.

Input:
{
  "taskId": "{taskId}",
  "clusterId": {clusterId},
  "outputFile": "skill/output/rank-{taskId}-cluster-{clusterId}.json",
  "scoreRange": [min, max],
  "scoringRubric": {scoringRubric or null},
  "developers": [
    {
      "login": "devA",
      "pass1Score": 68,
      "pass1Breakdown": {...},
      "pass1Comment": "...",
      ... full developer data from fetch file (topRepos, etc.) ...
    }
  ],
  "globalContext": {
    "nearestAbove": {"login": "devX", "score": 78},
    "nearestBelow": {"login": "devY", "score": 40}
  }
}
```

Launch with: `Agent(prompt=<above>, subagent_type="general-purpose")`

**Launch ALL cluster sub-subagents in a single message** (parallel dispatch).
Max clusters is typically 3-5, well under the 10-agent limit.

Wait for all to complete.

### Step 4: Merge normalized scores

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/merge_normalized.py {taskId}
```

This merges cluster rankings + isolated developer scores into
`skill/output/normalized-{taskId}.json`.

### Step 5: Verify output

Read `skill/output/normalized-{taskId}.json` and verify it contains entries for
all developers (clustered + isolated).

## Output

`skill/output/normalized-{taskId}.json`:
```json
[
  {"login": "devA", "normalizedScore": 82, "rankComment": "Strongest architecture in cluster..."},
  {"login": "devB", "normalizedScore": 78, "rankComment": null}
]
```

Isolated developers have `rankComment: null` (their normalizedScore = original score).

## Response

Print a brief summary:
```
Phase 5 complete. {clusterCount} clusters re-evaluated, {totalDevs} developers normalized. Output: normalized-{taskId}.json
```

## Error Handling

- **Ranker sub-subagent fails**: Those developers fall back to `normalizedScore = score`
  (handled automatically by `merge_normalized.py`).
- **`triage_clusters.py` fails**: Report error in response. The dispatcher will retry once,
  then proceed with raw scores as normalizedScore.
- **`merge_normalized.py` fails**: Report error in response. This is a critical failure —
  the dispatcher must handle it.

## Scope Constraint

Write ONLY to `skill/output/` directory (triage, rank, and normalized files).
Do NOT modify any `.py`, `.md`, `.ts`, or `.js` files.
If you encounter a data issue, report it in your response text — do not fix scripts.
