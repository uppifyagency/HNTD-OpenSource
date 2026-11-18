---
name: github-hr-objective-score
description: >
  Score developers on intrinsic code quality using the fixed 6-dimension rubric.
  Invoked via: claude -p "/github-hr objective-score <TASK_ID>" --model haiku
  No API key needed — Claude Code handles everything.
---

# Objective Score — Intrinsic Code Quality

Evaluate developers' repositories on 6 fixed dimensions to produce an `objectiveScore`
independent of any job description. This is a FALLBACK for developers whose scorer
subagent didn't produce `objectiveScore`.

This skill is meant to be run with `--model haiku` for cost efficiency.

## Usage

```bash
claude -p "/github-hr objective-score <TASK_ID> [--limit N] [--dry-run]" --model haiku
```

## Process

### Step 1: Load developers needing scoring

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python -c "
from skill.scripts.convex_client import get_developers_for_objective_scoring
import json
devs = get_developers_for_objective_scoring('<TASK_ID>')
print(json.dumps(devs, indent=2))
"
```

This returns developers from the task that have `objectiveScore === undefined` and have `repoRawData`.

If `--limit N` is passed, process only the first N developers.

### Step 2: Score each developer

For EACH developer, analyze their `repoRawData` and score on the fixed 6-dimension rubric:

| Dimension | Max | Criteria |
|---|---|---|
| codeQuality | 20 | 0-5: messy; 6-10: basic; 11-15: clean; 16-20: professional |
| architecture | 20 | 0-5: flat files; 6-10: organized; 11-15: well-structured; 16-20: exemplary |
| testing | 15 | 0-3: none visible; 4-7: some tests; 8-11: good coverage; 12-15: comprehensive |
| documentation | 15 | 0-3: none; 4-7: basic README; 8-11: good docs; 12-15: excellent |
| complexity | 15 | 0-3: trivial scripts; 4-7: simple apps; 8-11: medium systems; 12-15: complex |
| consistency | 15 | 0-3: sporadic; 4-7: semi-regular; 8-11: regular; 12-15: very active |

**Rules:**
- Score ONLY based on evidence in the repository data provided
- Do not infer skills from profile text alone
- If no source code is available for a repo, lower codeQuality proportionally
- `objectiveScore` = sum of all 6 dimension scores (max 100)

### Step 3: Patch each developer

For each scored developer:

```bash
python -c "
from skill.scripts.convex_client import patch_developer
patch_developer('<LOGIN>', {
    'scoreBreakdown': {
        'codeQuality': <int>,
        'architecture': <int>,
        'testing': <int>,
        'documentation': <int>,
        'complexity': <int>,
        'consistency': <int>
    },
    'objectiveScore': <int>
})
print('Patched <LOGIN>: objectiveScore=<int>')
"
```

If `--dry-run` is passed, print the scores but do NOT patch.

### Step 4: Log completion

```
Objective scoring complete: N developers scored for task <TASK_ID>
  Scored: N
  Skipped (already scored): M
  Errors: E
```

## Output

No file output. Patches are written directly to Convex via HTTP API.
