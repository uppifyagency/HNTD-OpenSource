---
name: github-hr-reval
description: >
  Re-evaluate developers on 6 objective dimensions (codeQuality, architecture,
  testing, documentation, complexity, consistency) using original fetch data.
  Produces objectiveScore for talent pool ordering.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Agent
---

# GitHub HR Reval -- Objective Score Re-evaluation

Re-score developers who lack the 6 fixed-dimension scoreBreakdown using their
original fetch JSON data (source code, README, commits) and the fixed rubric.

## Execution Flow

### Phase 1: Identify and Quick Patch

Run the identify script. Pass --dry-run or --task flags through if the user specified them.

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/reval_scores.py [--dry-run] [--task <TASK_ID>]
```

This does two things:
1. Patches objectiveScore for devs that already have scoreBreakdown (no scoring needed)
2. Prepares scorer input batches in skill/output/score-input-reval-batch-*.json
3. Writes skill/output/reval-manifest.json with batch metadata

If --dry-run was passed, stop here and report counts to user.

### Phase 2: Score with Subagents

Read the manifest to know how many batches exist:

```bash
cat skill/output/reval-manifest.json
```

For each batch, spawn a scorer subagent using the Agent tool:
- Prompt must include: Score these developers using the FIXED 6-dimension rubric only.
  Read the scoring criteria from skill/github-hr/references/scoring-criteria.md.
  Read the input batch from skill/output/score-input-reval-batch-{N}.json.
  Write output to skill/output/score-reval-batch-{N}.json.
  Output format: {"scores": [{"login": "...", "score": N, "scoreBreakdown": {...6 fixed keys...}, "scoreComment": "...", "scoreModel": "claude-opus-4-6", "topRepo": "..."}]}
  IMPORTANT: Use ONLY the 6 fixed dimensions. Never use dynamic/JD dimension names.
- Batch size: Up to 5 devs per subagent (matches input batch size)
- Parallelism: Run up to 3 subagents in parallel

Wait for all subagents to complete.

### Phase 2.5: Validate Scores

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/validate_scores.py reval
```

This checks score == sum(scoreBreakdown) for all reval batches and auto-corrects.

### Phase 3: Push Results

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python skill/scripts/reval_scores.py --push
```

This reads score-reval-batch-*.json files and patches scoreBreakdown + objectiveScore for each dev.

### Summary

After all phases, report to the user:
- How many devs had objectiveScore computed from existing breakdown
- How many devs were re-scored from fetch data
- How many were skipped (no fetch JSON)
- Total devs now with objectiveScore
