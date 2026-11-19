---
name: github-hr-run
description: >
  Process pending recruiter tasks. Pure dispatcher — loads task from Convex,
  dispatches subagents for ALL processing, reads decision files for routing,
  and handles Pass 2 loop logic. Zero inline Python except convex_client.py calls.
---

# Process Pending Tasks

## Arguments

- `--task <TASK_ID>`: Process a single specific task by its Convex ID. **Recommended.**
- `--priority-only`: Only process tasks with `priority: true`
- No flag: Process ALL pending tasks

## Prerequisites

- GitHub CLI signed in (`gh auth status`); search and fetch scripts call `gh api`
- `skill/scripts/.env` must have valid CONVEX_SITE_URL and API_SECRET
- Python venv with `requests` and `python-dotenv` installed

## CRITICAL: Dispatcher Rules

1. **NEVER execute GitHub fetching or AI scoring in the main context.**
   ALL processing runs in subagents. This agent is a PURE DISPATCHER.

2. **If a subagent fails:** retry once, then mark task failed. NEVER do the work yourself.

3. **File-based communication only.** Subagents write JSON to `skill/output/`.
   Dispatcher reads those files to make routing decisions.

4. **Subagent batch size limits:**
   - Fetch: max 5 developers per batch
   - Scorer: max 6 per batch (adaptive — see Phase 4)
   - Ranker: max 8 per cluster

5. **The run is unattended.** Nobody reads this session until it ends (the local worker or the
   cron started it). NEVER ask a question, offer options, or wait for a reply, and never end the
   turn before Phase 9. The only stops are the "mark task failed and STOP" paths in this file.
   On doubt about data quality or a surprising number, log a `warn` pipeline event that
   describes it, continue with the files on disk, and repeat it in the Phase 9 summary. Never
   edit `.py`, `.md` or config files during a run.

## Execution Flow

### Phase 0: Checkpoint Check (Resume Support)

```bash
cd "$(git rev-parse --show-toplevel)"
```

Before starting, check for a checkpoint file from a previous interrupted run:

Read `skill/output/checkpoint-{TASK_ID}.json` (if it exists).

If the checkpoint file exists:
- First run Phase 1's claim for the task. A refused claim stops the resume like any other
  refused claim, before you touch the checkpoint: another run may own it.
- Parse it: `{ taskId, lastCompletedPhase, timestamp, pass, metadata }`
- Log: `"Resuming task {TASK_ID} from phase {next_phase} (last completed: {lastCompletedPhase})"`
- Validate that expected output files for completed phases still exist
- If output files are missing, delete checkpoint and restart from Phase 1
- Otherwise, SKIP directly to the next phase after `lastCompletedPhase`

If no checkpoint exists, proceed normally from Phase 1.

**After EACH phase completion**, write/update the checkpoint:
```bash
cat > skill/output/checkpoint-{TASK_ID}.json << 'CHECKPOINT'
{
  "taskId": "{TASK_ID}",
  "lastCompletedPhase": "{current_phase}",
  "timestamp": {unix_timestamp_ms},
  "pass": {current_pass_number},
  "metadata": {
    "batchCount": {N},
    "completedBatches": [0, 1, ...],
    "scoredCount": {M},
    "completedScoreBatches": [0, 1, ...]
  }
}
CHECKPOINT
```

**Metadata fields by phase:**
- Phase 3.2: `batchCount` + `completedBatches` (all fetch batch indices that completed, including previously skipped)
- Phase 4.1: `batchCount` + `completedBatches` (preserved from 3.2) + `scoredCount` + `completedScoreBatches` (all score batch indices that completed)
- Other phases: include whichever metadata fields are available (carry forward from previous checkpoint)

### Phase 1: Load Task

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate
```

If `--task <TASK_ID>`:
```bash
python skill/scripts/convex_client.py task <TASK_ID>
```

If `--priority-only`:
```bash
python -c "
from skill.scripts.convex_client import get_priority_tasks
import json; print(json.dumps(get_priority_tasks(), indent=2))
"
```

Otherwise:
```bash
python skill/scripts/convex_client.py pending
```

If no pending tasks, print "No pending tasks." and exit.

**Claim the task** before any other work on it (the pipeline log below, Phase 2, a resume):
```bash
python skill/scripts/convex_client.py claim <TASK_ID>
```
- Exit 0: this run holds the task. Go on.
- Any other exit: another run holds the task, or it is not pending, or it is gone. Do NOT work
  on it and do NOT mark it failed. With `--task`, print the command's output and stop. In queue
  mode, go to the next task.

Parse the task JSON. Set `mode = task.mode` ("jd" or "manual").

**Log pipeline event:**
```bash
python -c "
from skill.scripts.convex_client import log_pipeline_event
log_pipeline_event('<TASK_ID>', '1', 'Task loaded: mode=<mode>', 'info', {'mode': '<mode>', 'maxResults': <task.params.maxResults or 25>})
"
```

### Phase 2: JD Parsing (if mode == "jd" AND no jdProfile)

**Resume branch (mode == "jd" AND `jdProfile` already present):** Phase 2 already
ran on a prior attempt. Skip parsing and rebuild the local profile file from the
persisted `task.jdProfile`, so local-file consumers (e.g. feedback_check's
`locationHard`) work on any machine — Convex is the source of truth (JD-02 #24):
```bash
python -c "
from skill.scripts.convex_client import reconstruct_jd_profile_file
reconstruct_jd_profile_file('<TASK_ID>')
"
```
Then skip the dispatch below and continue at Phase 3.0.

**Fresh branch (no `jdProfile`):**

**Dispatch:** `github-hr-jd-parser` subagent

```
You are the GitHub HR JD Parser Subagent. Read skill/agents/github-hr-jd-parser.md for your full instructions.

Input:
{
  "taskId": "<TASK_ID>",
  "jobDescription": "<task.jobDescription>",
  "outputFile": "skill/output/jd-profile-<TASK_ID>.json"
}
```

Launch: `Agent(prompt=<above>, subagent_type="general-purpose")`

Verify: `skill/output/jd-profile-<TASK_ID>.json` exists.

**Retry on failure:** If the subagent fails or the output file is missing:
1. Log warn-level pipeline event before retrying:
```bash
python -c "
from skill.scripts.convex_client import log_pipeline_event
log_pipeline_event('<TASK_ID>', '2', 'Phase 2 failed, retrying (attempt 2/2)', 'warn', {})
"
```
2. Re-dispatch the subagent (attempt 2)
3. If attempt 2 also fails:
   a. Log error-level pipeline event:
   ```bash
   python -c "
   from skill.scripts.convex_client import log_pipeline_event
   log_pipeline_event('<TASK_ID>', '2', 'Phase 2 failed after retry: JD parsing subagent failed on attempt 2', 'error', {})
   "
   ```
   b. Log task failure event:
   ```bash
   python -c "
   from skill.scripts.convex_client import log_pipeline_event
   log_pipeline_event('<TASK_ID>', '2', 'Task failed at phase 2: JD parsing failed after retry', 'error', {})
   "
   ```
   c. Mark task as failed and STOP

Reload task from Convex to get populated `jdProfile`.

**Write checkpoint:** `lastCompletedPhase: "2"`

### Phase 3.0: Strategy Generation

**If mode == "manual":**

**Direct Bash call** to `build_strategies.py`:

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/build_strategies.py \
  --task-id <TASK_ID> \
  --languages <task.params.languages joined by space> \
  --locations <task.params.locations joined by space> \
  --min-followers 2
```

**Optional params** — append ONLY if present (non-null, non-empty) in task.params:
- `--languages`: when `task.params.languages` is empty, drop the flag. A location-only search is
  valid: the strategies then carry no `language:` qualifier. The same holds for every
  `--target-languages` flag below (Phases 2.5 and 2.7): omit it when the task has no languages.
- `--country <task.params.country>` (if task.params.country is set)
- `--city <task.params.city>` (if task.params.city is set)
- `--keywords <task.params.keywords joined by space>` (if task.params.keywords is non-empty)

**Retry on failure:** If the script exits with a non-zero code:
1. Log warn-level pipeline event before retrying:
```bash
python -c "
from skill.scripts.convex_client import log_pipeline_event
log_pipeline_event('<TASK_ID>', '3.0', 'Phase 3.0 failed, retrying (attempt 2/2)', 'warn', {})
"
```
2. Re-run the same Bash command above (attempt 2)
3. If attempt 2 also exits non-zero:
   a. Log error-level pipeline event:
   ```bash
   python -c "
   from skill.scripts.convex_client import log_pipeline_event
   log_pipeline_event('<TASK_ID>', '3.0', 'Phase 3.0 failed after retry: strategy generation exited non-zero on attempt 2', 'error', {})
   "
   ```
   b. Log task failure event:
   ```bash
   python -c "
   from skill.scripts.convex_client import log_pipeline_event
   log_pipeline_event('<TASK_ID>', '3.0', 'Task failed at phase 3.0: strategy generation failed after retry', 'error', {})
   "
   ```
   c. Mark task as failed and STOP:
   ```bash
   python -c "
   from skill.scripts.convex_client import update_task_status
   update_task_status('<TASK_ID>', 'failed', 'Phase 3.0: strategy generation failed after retry')
   "
   ```

Read: `skill/output/strategies-<TASK_ID>.json` → `searchStrategies`

**If mode == "jd":**

Use `task.jdProfile.searchStrategies` directly → `searchStrategies`

**Write checkpoint** (only on success — failure path STOPs above):
```bash
cat > skill/output/checkpoint-<TASK_ID>.json << CHECKPOINT
{
  "taskId": "<TASK_ID>",
  "lastCompletedPhase": "3.0",
  "timestamp": $(date +%s000),
  "pass": 1,
  "metadata": {}
}
CHECKPOINT
```

**Log pipeline event:**
```bash
python -c "
from skill.scripts.convex_client import log_pipeline_event
log_pipeline_event('<TASK_ID>', '3.0', 'Strategies generated: <len(searchStrategies)> strategies', 'info', {'strategyCount': <len(searchStrategies)>})
"
```

### Phase 3.1: Search (SCRIPT — replaces searcher agent)

Determine the search output file name based on pass number:
- Pass 1 (or unset): `search-<TASK_ID>.json`
- Pass 2: `search-<TASK_ID>-pass2.json`

Write `searchStrategies` to a temp file for the script:
```bash
cat > skill/output/strategies-<TASK_ID>.json << 'EOF'
<searchStrategies JSON>
EOF
```

**Direct Bash call** to `github_search.py`:

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

# GDPR exclusion list (Art. 21): logins of developers who asked not to be indexed. Fetch it and
# union it with excludeLogins so an erased person is never even fetched from GitHub. This is an
# optimisation, not the guarantee — `upsertDeveloper` refuses an excluded login regardless, so a
# failure here cannot cause a re-index. Empty output is normal and must NOT abort the run.
# `source .venv/bin/activate` does NOT export these — they live in skill/scripts/.env and are
# normally read by python-dotenv INSIDE python. Without this `set -a` the curl below runs with an
# empty URL and an empty token, and the seed is silently always empty (measured 2026-08-02).
set -a; . skill/scripts/.env; set +a
# `json.load` also guards the shape: an error body ({"error": ...}) would otherwise be joined into
# a bogus "error,detail" list. A non-list, a failed curl or a non-200 all degrade to "".
GDPR_EXCLUDED=$(curl -sf -H "Authorization: Bearer $API_SECRET" \
  "$CONVEX_SITE_URL/api/excluded-logins" | python -c \
  'import json,sys; d=json.load(sys.stdin); print(",".join(d) if isinstance(d,list) else "")' 2>/dev/null || echo "")

python skill/scripts/github_search.py \
  --task-id <TASK_ID> \
  --strategies skill/output/strategies-<TASK_ID>.json \
  --max-results <task.params.maxResults or 25> \
  --exclude-logins <comma-separated excludeLogins, unioned with $GDPR_EXCLUDED, or ""> \
  --output-file <search output file name>
```

Verify: the pass-specific search output file exists (`skill/output/<search output file name>`).

**Retry on failure:** If the script exits non-zero, retry once. If still fails, mark task failed and STOP.

**Write checkpoint:** `lastCompletedPhase: "3.1"`

### Phase 2.5: GraphQL Enrichment (SCRIPT — replaces graphql-scanner agent)

**Direct Bash call** to `graphql_enrich.py`:

**Pass 1:**
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/graphql_enrich.py \
  --task-id <TASK_ID> \
  --target-languages <task.params.languages joined by space> \
  --batch-size 5
```

Verify: `skill/output/graphql-<TASK_ID>.json` exists.

**Pass 2:**
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/graphql_enrich.py \
  --task-id <TASK_ID> \
  --target-languages <task.params.languages joined by space> \
  --search-file search-<TASK_ID>-pass2.json \
  --output-file graphql-<TASK_ID>-pass2.json \
  --batch-size 5
```

Verify: `skill/output/graphql-<TASK_ID>-pass2.json` exists.

**Fallback on failure:** If the script exits non-zero, log a warning and continue — all candidates become survivors in Phase 2.7.

**Write checkpoint:** `lastCompletedPhase: "2.5"`

### Phase 2.7: Pre-filter

**Direct Bash call** to `prefilter.py`:

**Pass 1:**
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/prefilter.py \
  --task-id <TASK_ID> \
  --min-activity <task.params.minActivity or 6> \
  --target-languages <task.params.languages joined by space> \
  --output-dir skill/output
```

Verify: `skill/output/prefilter-<TASK_ID>.json` exists and exit code == 0.

**Pass 2:**
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/prefilter.py \
  --task-id <TASK_ID> \
  --min-activity <task.params.minActivity or 6> \
  --target-languages <task.params.languages joined by space> \
  --output-dir skill/output \
  --graphql-file graphql-<TASK_ID>-pass2.json \
  --output-file prefilter-<TASK_ID>-pass2.json
```

Verify: `skill/output/prefilter-<TASK_ID>-pass2.json` exists and exit code == 0.

**Read survivor count:** Parse the pass-specific prefilter file → `survivorCount`.

**Log pipeline event:**
```bash
python -c "
from skill.scripts.convex_client import log_pipeline_event
log_pipeline_event('<TASK_ID>', '2.7', 'Pre-filter complete: <survivorCount> survivors, <discardedCount> discarded', 'info', {'survivors': <survivorCount>, 'discarded': <discardedCount>})
"
```

**Fallback on failure:** If prefilter.py exits non-zero, log a warning and continue — all candidates become survivors (no filtering).

**Write checkpoint:** `lastCompletedPhase: "2.7"`

### Phase 2.8: Pre-Score Gate (NEW — ceiling-based elimination)

**Direct Bash call** to `pre_score_gate.py`:

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/pre_score_gate.py \
  --task-id <TASK_ID> \
  --max-results <task.params.maxResults or 25> \
  --mode <jd if task.mode == "jd" else manual>
```

`--mode jd` selects the `jd_weights` profile (JD-05) so the gate ceiling is
consistent with the deterministic rank of Phase 4.5.

Verify: `skill/output/score-gate-<TASK_ID>.json` exists.

Read output: `scorableCount` and `eliminatedCount`.

**Log pipeline event:**
```bash
python -c "
from skill.scripts.convex_client import log_pipeline_event
log_pipeline_event('<TASK_ID>', '2.8', 'Pre-score gate: <scorableCount> scorable, <eliminatedCount> eliminated', 'info', {'scorable': <scorableCount>, 'eliminated': <eliminatedCount>})
"
```

**Note:** If pre-score gate file doesn't exist (e.g., first run without prefilter), code_sample.py falls back to prefilter survivors directly.

**Write checkpoint:** `lastCompletedPhase: "2.8"`

### Phase 3.2: Code Sample (SCRIPT — replaces fetcher agent)

Determine survivors input file:
- **Pass 1:** If `skill/output/score-gate-<TASK_ID>.json` exists: use `score-gate-<TASK_ID>.json`; otherwise: use `prefilter-<TASK_ID>.json`
- **Pass 2:** Use `prefilter-<TASK_ID>-pass2.json`

**Direct Bash call** to `code_sample.py`:

**Pass 1:**
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/code_sample.py \
  --task-id <TASK_ID> \
  --survivors <survivors file name> \
  --repos-per-dev 7 \
  --parallel 5
```

Verify: `skill/output/fetch-<TASK_ID>.json` exists.

**Pass 2:**
```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/code_sample.py \
  --task-id <TASK_ID> \
  --survivors prefilter-<TASK_ID>-pass2.json \
  --repos-per-dev 7 \
  --parallel 5 \
  --output-file fetch-<TASK_ID>-pass2.json
```

Verify: `skill/output/fetch-<TASK_ID>-pass2.json` exists.

**Retry on failure:** If the script exits non-zero, retry once. If still fails, mark task failed and STOP.

**Write checkpoint:** `lastCompletedPhase: "3.2"`

### Phase 3.3: Validate (SCRIPT — replaces merge-validator agent)

**Note:** With `code_sample.py`, fetch output is already a single file. Validation only.

**Direct Bash call:**

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/validate_fetch.py <TASK_ID>
```

If validation fails, log warning and continue with available data.

**Write checkpoint:** `lastCompletedPhase: "3.3"`

### Phase 4.1: Score (parallel)

Determine the fetch file path based on pass number:
- Pass 1 (or unset): `skill/output/fetch-<TASK_ID>.json`
- Pass 2: `skill/output/fetch-<TASK_ID>-pass2.json`

Read the pass-specific fetch file → scorable developer list.

If the file does not exist, mark the task as failed with reason: "Missing fetch data for Pass {passNumber}. Ensure Phase 3 completed for this pass." and STOP.

**GraphQL data enrichment (optional, Pass 1 only):**

If `skill/output/graphql-<TASK_ID>.json` exists:
1. Read the graphql file → `graphqlData`
2. Build a map keyed by login: for each developer in `graphqlData.developers` where `scanError` is NOT true:
   ```
   graphqlMap[dev.login] = {
     "contributionDays": dev.contributionDays,
     "pinnedRepoCount": dev.pinnedRepoCount,
     "totalStarsReceived": dev.totalStarsReceived,
     "targetLanguageRepoCount": dev.targetLanguageRepoCount
   }
   ```
3. Developers with `scanError: true` are EXCLUDED from graphqlMap (scored using repo content only)
4. Log: `"GraphQL enrichment: <len(graphqlMap)> developers with contribution data"`

If graphql file does NOT exist:
- Set `graphqlMap = null` (scoring proceeds without contribution data)
- Log: `"No graphql scan file found, scoring without contribution data"`

**Adaptive batch sizing:**

| Scorable devs | Batch size | Max batches |
|---|---|---|
| ≤ 30 | 3 | ≤ 10 |
| 31-40 | 4 | 8-10 |
| 41-50 | 5 | 9-10 |
| > 50 | 6 | 9+ |

**Skip completed batches (resume support):**

Determine the file name prefix based on pass number:
- Pass 1 (or unset): `score-<TASK_ID>-batch-{i}.json`
- Pass 2: `score-<TASK_ID>-pass2-batch-{i}.json`

For each batch index `i` (0 to batchCount-1), check if the output file exists and is valid:

```bash
python -c "
import json, os
# Use pass2 naming when passNumber == 2
path = 'skill/output/score-<TASK_ID>-pass2-batch-{i}.json' if <passNumber> == 2 else 'skill/output/score-<TASK_ID>-batch-{i}.json'
if os.path.exists(path) and os.path.getsize(path) > 10:
    try:
        with open(path) as f:
            data = json.load(f)
            print(f'VALID: {len(data.get(\"developers\", []))} developers')
    except json.JSONDecodeError:
        os.remove(path)
        print('MISSING')
else:
    print('MISSING')
"
```

- If output is `VALID`: skip this batch (already complete)
- If output is `MISSING`: add to pending dispatch list
- If JSON parse fails (truncated file from crash): delete the file and add to pending list

Build `pendingBatches` list. If empty → skip to Phase 4.2 (all batches already complete).

**Log skip summary** (if any batches were skipped):
```bash
python -c "
from skill.scripts.convex_client import log_pipeline_event
log_pipeline_event('<TASK_ID>', '4.1', 'Score batch skip check: <skippedCount> complete, <pendingCount> pending', 'info', {'skipped': <skippedCount>, 'pending': <pendingCount>, 'deleted': <deletedCount>})
"
```

**Dispatch:** Only `len(pendingBatches)` × `github-hr-scorer` subagents **in parallel** for pending batch indices.

For each batch `i` in `pendingBatches`:

Determine `outputFile` based on pass number:
- Pass 1 (or unset): `skill/output/score-<TASK_ID>-batch-<i>.json`
- Pass 2: `skill/output/score-<TASK_ID>-pass2-batch-<i>.json`

```
You are the GitHub HR Scorer Subagent. Read skill/agents/github-hr-scorer.md for your full instructions.

Input:
{
  "taskId": "<TASK_ID>",
  "batchIndex": <i>,
  "outputFile": "<outputFile>",
  "scoringRubric": <task.jdProfile.scoringRubric if mode=jd else null>,
  "targetCountry": <task.params.country or null>,
  "graphqlData": <graphqlMap or null — see Phase 4.1 enrichment above>,
  "developers": [<developer slice from fetch JSON>]
}
```

**Note:** `graphqlData` is a map keyed by login. If null or absent, the scorer uses repository content only. If present, the scorer uses it as INFORMATIONAL CONTEXT in `scoreComment` only — never in score dimension calculations.

**Note (QT-07):** the `developers` slice is passed from the fetch JSON **as-is** — `code_sample.py` already emits the canonical scorer-input shape (`topRepos[*].{fullName, directoryListing, dependencyFile, sourceFiles, commits}`). Do NOT remap, rename or reshape any field in the main context.

Launch ALL pending batches in a single message.
If N > 10, split into multiple message turns (max 10 parallel agents per turn).
Wait for all to complete.

**Retry on failure:** If any scorer batch subagent fails:
1. Log warn-level pipeline event before retrying:
```bash
python -c "
from skill.scripts.convex_client import log_pipeline_event
log_pipeline_event('<TASK_ID>', '4.1', 'Phase 4.1 failed, retrying (attempt 2/2)', 'warn', {})
"
```
2. Re-dispatch only the failed batch(es) (attempt 2)
3. If attempt 2 also fails:
   a. Log error-level pipeline event:
   ```bash
   python -c "
   from skill.scripts.convex_client import log_pipeline_event
   log_pipeline_event('<TASK_ID>', '4.1', 'Phase 4.1 failed after retry: scorer batch(es) failed on attempt 2', 'error', {})
   "
   ```
   b. Log task failure event:
   ```bash
   python -c "
   from skill.scripts.convex_client import log_pipeline_event
   log_pipeline_event('<TASK_ID>', '4.1', 'Task failed at phase 4.1: scoring failed after retry', 'error', {})
   "
   ```
   c. Mark task as failed and STOP

**Write checkpoint:** `lastCompletedPhase: "4.1", metadata: { batchCount: N, completedBatches: [...], scoredCount: M, completedScoreBatches: [0, 1, ..., scoreBatchCount-1] }`

The `completedScoreBatches` array MUST include ALL score batch indices that are now complete — both previously-skipped batches AND newly-dispatched batches. Carry forward `batchCount` and `completedBatches` from the Phase 3.2 checkpoint. `scoredCount` is the total number of developers scored across all batches.

**Log pipeline event:**
```bash
python -c "
from skill.scripts.convex_client import log_pipeline_event
log_pipeline_event('<TASK_ID>', '4.1', 'Scoring complete: <scoredCount> developers scored', 'info', {'scored': <scoredCount>, 'batches': <batchCount>})
"
```

### Phase 4.5: Deterministic Ranking (NEW — SCRIPT)

**Direct Bash call** to `deterministic_rank.py`:

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/deterministic_rank.py <TASK_ID>
```

Verify: `skill/output/deterministic-rank-<TASK_ID>.json` exists.

**Write checkpoint:** `lastCompletedPhase: "4.5"`

### Phase 5: Triage + AI Ranking (hybrid)

**Step 1:** Triage clustering (SCRIPT):
```bash
python skill/scripts/triage_clusters.py <TASK_ID>
```

**Step 2:** For each cluster in `triage-<TASK_ID>.json`, dispatch `github-hr-ranker` subagent **only for ambiguous clusters** (size >= 2). Isolated developers keep their `deterministicRank` as `normalizedScore`.

For forcedAI clusters, always dispatch the ranker.

**Scale, by design:** triage clusters on `deterministicRank` (Phase 4.5), a weighted blend in
which code quality is one term, so `normalizedScore` lands on the deterministicRank scale, not
on the Pass 1 `score` scale. A Pass 1 score of 86 that becomes a normalizedScore of 44 in a
[34, 40] cluster is the intended result, not a bug: `score`, `objectiveScore`,
`normalizedScore` and `matchConfidence` are different fields. Do not report it as an error,
do not edit the triage or ranker files, and proceed to Step 3.

**Dispatch per cluster:** `github-hr-ranker` subagent (same as before)

**Parallelization limit:** Dispatch ranker subagents in batches of max 5 parallel
agents per turn. If N clusters > 5, split into multiple message turns
(e.g., 5+5+5+...+remaining), waiting for each batch to complete before
dispatching the next. This is stricter than Phase 4.1 (max 10) because each
ranker subagent receives heavier context per cluster (full developer profiles
for up to MAX_CLUSTER_SIZE=8 devs vs. 1 developer per scorer invocation).
Prevents Claude Code parallelism limit exhaustion that caused 77% of clusters
to fail in the 309-dev task (E-13).

**Step 3:** Merge normalized:
```bash
python skill/scripts/merge_normalized.py <TASK_ID>
```

Verify: `skill/output/normalized-<TASK_ID>.json` exists.

**Write checkpoint:** `lastCompletedPhase: "5"`

### Phase 6: Feedback Check (SCRIPT — replaces feedback-analyzer agent)

**Skip if:** `mode != "jd"`

**Direct Bash call** to `feedback_check.py`:

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/feedback_check.py \
  --task-id <TASK_ID> \
  --pass-number <passNumber> \
  --jd-profile jd-profile-<TASK_ID>.json \
  --original-strategies strategies-<TASK_ID>.json
```

Read: `skill/output/feedback-<TASK_ID>.json`

**Decision routing:**
- `decision == "continue"` → Continue to Phase 7
- `decision == "pass2"` AND `passNumber == 1` →
  1. Set `searchStrategies = feedback.refinedStrategies`
  2. Set `excludeLogins = pass1Logins`
  3. Set `passNumber = 2`
  4. GOTO Phase 3.1 (search with refined strategies, excludeLogins)
  5. Phase 2.5: GraphQL enrich pass2 developers
  6. Phase 2.7: Prefilter pass2 (with `--graphql-file` and `--output-file` overrides)
  7. Phase 3.2: Code sample pass2 developers
  8. Phase 4.1: Score new developers (pass2 batch naming)
  9. Phase 4.5: Deterministic rank (reads all passes)
  10. Phase 5: Triage + merge (reads all passes)
  11. Re-run feedback_check with `--pass-number 2`
  12. If decision still "pass2" → IGNORE (max 2 passes, hard limit)

**Write checkpoint:** `lastCompletedPhase: "6"`

### Phase 7: Push Results (SCRIPT — replaces result-pusher agent)

**Direct Bash call** to `push_results.py`:

```bash
cd "$(git rev-parse --show-toplevel)"
source skill/scripts/.venv/bin/activate

python skill/scripts/push_results.py <TASK_ID> --max-results <task.params.maxResults>
```

Read: `skill/output/result-<TASK_ID>.json`
If `totalPushed == 0`: log warning.

**Retry on failure:** If the script exits non-zero, retry once. If still fails, mark task failed and STOP.

**Write checkpoint:** `lastCompletedPhase: "7"`

### Phase 8: Enrich (post-push)

**Dispatch:** `github-hr-enricher` subagent (COMPOSITE)

The enricher now dispatches `github-hr-enricher-worker` sub-subagents internally
(max 5 parallel per batch) for context-isolated hrSummary generation.

**Fill-only semantics (ADR-004):** The enricher NEVER overwrites existing
objectiveScore, poolCategory, or hrSummary — only fills missing fields.

```
You are the GitHub HR Enricher Subagent. Read skill/agents/github-hr-enricher.md for your full instructions.

Input:
{
  "taskId": "<TASK_ID>",
  "resultFile": "skill/output/result-<TASK_ID>.json"
}
```

Launch: `Agent(prompt=<above>, subagent_type="general-purpose")`

**Retry on failure:** If the subagent fails:
1. Log warn-level pipeline event before retrying:
```bash
python -c "
from skill.scripts.convex_client import log_pipeline_event
log_pipeline_event('<TASK_ID>', '8', 'Phase 8 failed, retrying (attempt 2/2)', 'warn', {})
"
```
2. Re-dispatch the subagent (attempt 2)
3. If attempt 2 also fails:
   a. Log error-level pipeline event:
   ```bash
   python -c "
   from skill.scripts.convex_client import log_pipeline_event
   log_pipeline_event('<TASK_ID>', '8', 'Phase 8 failed after retry: enricher subagent failed on attempt 2', 'error', {})
   "
   ```
   b. Continue (enrichment is non-critical — task is NOT marked failed)

Enrichment is supplementary — failures here do NOT fail the task.

**Write checkpoint:** `lastCompletedPhase: "8"`

**Log pipeline event:**
```bash
python -c "
from skill.scripts.convex_client import log_pipeline_event
log_pipeline_event('<TASK_ID>', '8', 'Enrichment complete', 'info', {'enriched': <enrichedCount>})
"
```

### Phase 9: Summary

Read `skill/output/result-<TASK_ID>.json` and print leaderboard summary:

```
=== Task <TASK_ID> Complete ===
Mode: <mode>
Developers found: <totalProfilesFetched>
Developers scored: <totalScored>
Developers pushed: <totalPushed>
Top 5:
  1. <login> — normalizedScore: <score>
  2. ...
```

**Cleanup:** Delete the checkpoint file (task completed successfully):
```bash
rm -f skill/output/checkpoint-<TASK_ID>.json
```

## Error Handling

- `gh` not signed in or GitHub API unreachable → mark task "failed" with error message
- Subagent timeout/crash → log warn-level event, retry 1x, then mark task "failed"
- Convex write failure → save to `skill/output/failed-<TASK_ID>.json`
- Zero search results → complete the task with an empty result list: `complete_task('<TASK_ID>', [])`
  (`update_task_status` cannot set `completed`)
- Critical subagent (searcher, fetcher, pusher) failure → mark task "failed"
- Non-critical subagent (score-validator, enricher) failure → continue pipeline
- **Pipeline logging is fire-and-forget:** `log_pipeline_event()` uses try/except with
  5s timeout and no retries. If POST /api/pipeline-log returns 500 or is unreachable,
  a warning is printed to stderr and the dispatcher proceeds. Logging failure never
  marks a task as failed or blocks pipeline progression.
