---
name: github-hr-jd-parse
description: Parse a raw job description into a structured JD Profile (Phase 0.5)
---

# github-hr-jd-parse

Parse a raw job description into a structured JD Profile with search parameters and a dynamic scoring rubric.

## Usage

Called by `/github-hr run` for tasks with `mode: "jd"` and no existing `jdProfile`.
Can also be called standalone: `/github-hr jd-parse <TASK_ID>`

## Input

- Task with `mode: "jd"` and `jobDescription` field populated
- Task ID for file naming

## Process

### Step 1: Load task data

```bash
python -c "
from skill.scripts.convex_client import get_pending_tasks
import json
tasks = get_pending_tasks()
task = next(t for t in tasks if t['_id'] == '<TASK_ID>')
print(json.dumps(task, indent=2))
"
```

Verify `task.mode === "jd"` and `task.jobDescription` is non-empty.

### Step 1.5: Load search strategy reference

Read the location alias map and search patterns:
```bash
cat skill/github-hr/references/search-strategies.md
```

Use the **Location Alias Map** from this file when generating `searchStrategies`:
- For each location extracted from the JD, look up ALL aliases in the map
- Generate at least one strategy per major alias (country name + top 3 cities in both English and local spelling)
- Example: JD says "Bologna, Italy" → generate strategies with: italy, italia, bologna, rome, roma, milan, milano (from the alias table)

### Step 2: Analyze the job description

Read the `jobDescription` text and extract a structured JD Profile.

**Extraction rules:**

1. **languages**: Extract ALL programming languages AND frameworks mentioned.
   - Include both explicit ("Java", "React") and implicit ("frontend framework" → infer from context).
   - Normalize: "JS" → "JavaScript", "TS" → "TypeScript", "Node" → "Node.js".

2. **locations**: Extract cities, regions, nations.
   - "sede di Bologna" → ["Bologna", "Italy"]
   - "remote" → ["Remote"]
   - Always include the country if a city is mentioned.

3. **keywords**: Extract technical domain keywords.
   - Include: tools, patterns, methodologies, domain terms ("MES", "microservizi", "REST API").
   - Exclude: soft skills ("team working", "proattività"), benefits, company info.

4. **senioritySignals**: Extract seniority indicators.
   - "esperienza con...", "3+ anni", "laurea in...", "senior", "junior".

5. **roleType**: Classify as one of: frontend, backend, fullstack, devops, data, other.
   - If JD mentions both frontend AND backend responsibilities → "fullstack".

6. **scoringRubric.dimensions**: Generate 4-6 scoring dimensions.
   - Each dimension has: name, weight (0-100, sum MUST = 100), description, signals.
   - Dimensions must be DERIVED from the JD, not generic.
   - Example: if JD emphasizes "responsive design" → create a "Frontend Mastery" dimension with "responsive CSS" in signals.

7. **scoringRubric.mustHave**: Technologies explicitly required in "Requirements" section.
   - Use OR groups for alternatives: "React OR Angular OR Vue.js".

8. **scoringRubric.niceToHave**: Technologies in "Nice to have" / "Completano il profilo" sections.

9. **scoringRubric.dealBreakers**: Rarely used. Only if JD explicitly excludes something.

10. **searchStrategies**: Generate 5-8 GitHub search strategies covering multiple angles.
    - Each strategy has: `query` (GitHub search syntax), `priority` (1=highest), `rationale`.
    - **Mandatory alias coverage:** For each location, the generated strategies MUST include at minimum:
      a. The country in English (e.g., "italy")
      b. The country in local language (e.g., "italia")
      c. The specific city from the JD (e.g., "bologna")
      d. At least 2 major cities from the alias map (e.g., "milan", "milano", "rome", "roma")
    - **Reference:** Use the Location Alias Map from `skill/github-hr/references/search-strategies.md` (loaded in Step 1.5)
    - Include primary language AND secondary/alternative languages from JD.
    - Include framework/tool-specific queries if JD mentions specific frameworks.
    - Order by expected relevance (priority 1 = most likely to find best candidates).

### Step 3: Validate the JD Profile

- Verify `dimensions` weights sum to exactly 100.
- Verify at least 1 language extracted.
- Verify at least 1 location extracted.
- Verify 4-6 dimensions present.
- Verify 5-8 `searchStrategies` generated with valid GitHub search syntax.

### Step 4: Save the JD Profile

Save to local file:
```
skill/output/jd-profile-<TASK_ID>.json
```

Push to Convex:
```bash
python -c "
from skill.scripts.convex_client import update_jd_profile
import json
jd_profile = json.load(open('skill/output/jd-profile-<TASK_ID>.json'))
update_jd_profile('<TASK_ID>', jd_profile)
"
```
If this write raises `ClaimLost` (HTTP 409 `claim_lost`), another run holds the search now: stop at once and report it. Do not retry, do not mark the task failed, do not reset it.

### Step 5: Log summary

```
JD Profile v1 generated:
  Languages: JavaScript, React, Angular, Vue.js, Java, C#, Python, Node.js
  Locations: Bologna, Italy
  Role: fullstack
  Keywords: MES, REST API, microservizi, MySQL, PostgreSQL, MongoDB
  Dimensions: 5 (Frontend Mastery 25pt, Backend Architecture 25pt, ...)
  Must-have: 3 groups
  Nice-to-have: 5 items
  Search strategies: 6
```

## Output Schema

```json
{
  "extractedParams": {
    "languages": ["string"],
    "locations": ["string"],
    "keywords": ["string"],
    "senioritySignals": ["string"],
    "roleType": "frontend|backend|fullstack|devops|data|other"
  },
  "scoringRubric": {
    "dimensions": [
      {
        "name": "string",
        "weight": 0-100,
        "description": "string",
        "signals": ["string"]
      }
    ],
    "mustHave": ["string"],
    "niceToHave": ["string"],
    "dealBreakers": ["string"]
  },
  "searchStrategies": [
    {
      "query": "language:typescript location:italy",
      "priority": 1,
      "rationale": "Primary language + country-level location"
    },
    {
      "query": "language:javascript location:italia",
      "priority": 2,
      "rationale": "Alternative language + Italian spelling"
    }
  ],
  "version": 1
}
```
