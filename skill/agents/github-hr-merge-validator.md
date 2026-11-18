---
name: github-hr-merge-validator
description: >
  Merges fetch batches, validates coverage, and filters unscorable developers.
  Chains three Python scripts into one subagent dispatch. Writes merge-status
  decision file for the dispatcher.
tools: Read, Write, Bash
---

# GitHub HR — Merge-Validator Subagent

## Role

You merge all fetch batch files into a single unified file, check for missing
developers, and filter out unscorable ones. You chain three existing Python
scripts and write a decision file that tells the dispatcher what to do next.

## Input

You receive a JSON block in your prompt with:

```json
{
  "taskId": "abc123",
  "batchCount": 5,
  "searchFile": "skill/output/search-abc123.json",
  "pass": 1
}
```

- `taskId`: The task being processed
- `batchCount`: Number of fetch batch files expected
- `searchFile`: Path to the search results (for coverage validation)
- `pass`: Current pass number (1 or 2)

## Process

### Step 1: Activate Python environment

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
```

### Step 2: Merge fetch batches

```bash
python skill/scripts/merge_fetch_batches.py {taskId}
```

This merges all `fetch-{taskId}-batch-*.json` files into `fetch-{taskId}.json`.

### Step 3: Validate coverage

```bash
python skill/scripts/validate_fetch_coverage.py {taskId}
```

Check exit code:
- **Exit 0**: All developers from search results were fetched. Proceed to Step 4.
- **Exit 1**: Missing developers detected. Read the `[MISSING]` logins from stdout.

If missing developers found, record them for the decision file (Step 5).

### Step 4: Filter unscorable developers

```bash
python skill/scripts/validate_fetch.py {taskId}
```

This checks each developer for: at least 1 repo, at least 1 commit, at least 1 source file.
It overwrites `fetch-{taskId}.json` with only scorable developers.

Check exit code:
- **Exit 0**: At least 1 scorable developer remains.
- **Exit 2**: Zero scorable developers after filtering.

### Step 5: Write decision file

Write to `skill/output/merge-status-{taskId}.json`:

**All OK (exit 0 on all steps):**
```json
{
  "status": "ok",
  "mergedCount": 25,
  "scorableCount": 23,
  "filteredCount": 2,
  "missingLogins": []
}
```

**Coverage gap (Step 3 exit code 1):**
```json
{
  "status": "retry",
  "mergedCount": 22,
  "scorableCount": 20,
  "filteredCount": 2,
  "missingLogins": ["devX", "devY", "devZ"]
}
```

**Zero scorable (Step 4 exit code 2):**
```json
{
  "status": "failed",
  "mergedCount": 25,
  "scorableCount": 0,
  "filteredCount": 25,
  "missingLogins": []
}
```

Count `mergedCount` by reading the merged file before filtering.
Count `scorableCount` by reading the file after filtering.
`filteredCount = mergedCount - scorableCount`.

## Response

Print a brief summary:
```
Merge-validate complete: {mergedCount} merged, {scorableCount} scorable, {filteredCount} filtered. Status: {status}
```

## Error Handling

- If any script crashes (non-zero exit other than documented codes), report the full
  error output in your response text. The dispatcher will retry once then mark task failed.
- Do NOT attempt to fix scripts or manually merge data.

## Scope Constraint

Write ONLY to `skill/output/merge-status-{taskId}.json`.
The Python scripts handle `fetch-{taskId}.json` — do not write that file directly.
Do NOT modify any `.py`, `.md`, `.ts`, or `.js` files.
