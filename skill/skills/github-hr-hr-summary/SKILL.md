---
name: github-hr-hr-summary
description: >
  Generate HR-friendly summaries for developers in the talent pool.
  Invoked via: claude -p "/github-hr hr-summary <TASK_ID>" --model haiku
  No API key needed — Claude Code handles everything.
---

# Generate HR Summaries

Generate 1-2 sentence non-technical profile summaries in Italian for recruiters.
This skill is meant to be run with `--model haiku` for cost efficiency.

## Usage

```bash
claude -p "/github-hr hr-summary <TASK_ID> [--dry-run]" --model haiku
```

## Process

### Step 1: Load developers for the task

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
python -c "
from skill.scripts.convex_client import get_task_leaderboard
import json
devs = get_task_leaderboard('<TASK_ID>')
print(json.dumps(devs, indent=2))
"
```

### Step 2: Generate summaries

For EACH developer in the leaderboard:

1. Read their profile data: `name`, `login`, `location`, `topLanguages`, `scoreComment`
2. Generate a 1-2 sentence summary following these rules:
   - Written in **professional Italian**
   - **No technical jargon** — a non-technical HR recruiter must understand it
   - **No scores or numbers** — describe qualities, not metrics
   - Describe what kind of developer they are and what they excel at
   - Example: "Sviluppatore backend con forte esperienza in sistemi distribuiti e architetture cloud. Dimostra un approccio metodico alla qualità del codice e alla documentazione."

3. Determine `poolCategory` from their `topLanguages`:
   - backend: Java, Python, Go, Rust, C#, PHP, Ruby, Scala, Kotlin, C++, C
   - frontend: JavaScript, TypeScript, Vue, Svelte, CSS, HTML, SCSS
   - fullstack: has BOTH backend AND frontend languages
   - data: Jupyter Notebook, MATLAB, Julia, R
   - devops: Shell, Dockerfile, Nix, HCL
   - mobile: Kotlin, Dart, Swift

### Step 3: Patch each developer

For each developer, patch the two fields to Convex:

```bash
python -c "
from skill.scripts.convex_client import patch_developer
patch_developer('<LOGIN>', {
    'hrSummary': '<generated summary>',
    'poolCategory': '<category>'
})
print('Patched <LOGIN>')
"
```

If `--dry-run` is passed, print the summary but do NOT patch.

### Step 4: Log completion

```
HR Summaries generated: N developers processed for task <TASK_ID>
```

## Output

No file output. Patches are written directly to Convex via HTTP API.
