# GitHub Search Strategies — Reference Document

> **Consumers:** This file is read by `jd-parse/SKILL.md` (Step 1.5) at runtime.
> The location alias map below is also the source of truth for `skill/scripts/build_strategies.py`.
> If you update aliases here, update the `LOCATION_ALIASES` dict in `build_strategies.py` to match.

---

# Operational Guide

## Search via GitHub MCP

Use these MCP tools in sequence:

### Step 1: Search Users Directly

Use `search_users` with GitHub search qualifiers:

```
query: "language:{lang} location:{location} followers:>=2"
sort: "repositories"
order: "desc"
perPage: 100
```

> **Do NOT sort by `followers`.** Follower count is a fame signal, not a code-quality
> signal — sorting by it biases location searches toward celebrity accounts and
> silently demotes placeable local developers (ADR-021, B2a). For location-specific
> tiers the pipeline issues `sort=repositories` purely as a debiasing lever to
> displace GitHub's celebrity-biased default ("best match") order; `sort` is never
> trusted as a quality ranking (D-DESIGN-5).

Run for EVERY combination of (language x location alias). Example:
- Task params: languages=["python"], locations=["italy"]
- Queries to run:
  - `language:python location:italy followers:>=2`
  - `language:python location:italia followers:>=2`
  - `language:python location:rome followers:>=2`
  - `language:python location:roma followers:>=2`
  - `language:python location:milan followers:>=2`
  - `language:python location:milano followers:>=2`
  - (continue for all aliases)

Deduplicate results by `login`.

### Step 2: Rank & Select Top 25

From deduplicated results:
1. Order by priorityTier provenance, then by repository count — never by followers (followers is a fame signal, not a quality signal — ADR-021)
2. Filter: must have >= 2 public repos
3. Take top N (from task.params.maxResults, default 25)

### Step 3: Fetch Developer Data

For each selected developer, use MCP tools:

1. `search_repositories` with `query: "user:{login} fork:false" sort: "stars" order: "desc" perPage: 3`
   → Get top 3 non-fork repos

2. For each repo:
   a. `get_file_contents` with `owner: {login}, repo: {repo_name}, path: "README.md"`
      → Get README (skip if 404)

   b. `get_repository_tree` with `owner: {login}, repo: {repo_name}, recursive: true`
      → Get file tree, select top 3 source files by relevance:
      - Prefer: main entry point (main.py, index.ts, app.py, etc.)
      - Prefer: files in src/ or lib/ directories
      - Prefer: test files (test_*.py, *.test.ts, etc.)
      - Skip: config files, lock files, generated code, node_modules, vendor

   c. `get_file_contents` for each of the 3 selected source files
      → Read first 500 lines of each

   d. `list_commits` with `owner: {login}, repo: {repo_name}, perPage: 20`
      → Get last 20 commits with messages and dates

### Step 4: Save Pre-Fetch Data

Save all collected data to `skill/output/fetch-{task_id}.json`.
Format: array of developer objects with nested repo data.
See design doc Section 3.3 for exact schema.

## Location Alias Map

When the task specifies a location, also search all aliases:

| Location | Aliases |
|---|---|
| italy | italia, rome, roma, milan, milano, turin, torino, naples, napoli, florence, firenze, bologna, venice, venezia, genoa, genova, palermo, bari, catania |
| germany | deutschland, berlin, munich, münchen, munchen, hamburg, frankfurt, cologne, köln, koln, stuttgart, düsseldorf, dusseldorf |
| france | paris, lyon, marseille, toulouse, nice, nantes, strasbourg, bordeaux, lille |
| spain | españa, espana, madrid, barcelona, valencia, seville, sevilla, bilbao, malaga |
| uk | united kingdom, england, london, manchester, birmingham, leeds, glasgow, edinburgh, bristol, liverpool |
| netherlands | holland, amsterdam, rotterdam, the hague, den haag, utrecht, eindhoven |
| portugal | lisboa, lisbon, porto |
| poland | polska, warsaw, warszawa, krakow, kraków, wroclaw, wrocław, gdansk, gdańsk |
| switzerland | schweiz, suisse, svizzera, zurich, zürich, geneva, genève, bern, basel |

For locations NOT in this map, search with the exact string provided by the recruiter.

## Rate Limit Budget

- **Search API limit: 30 requests/minute** — this is the rate that actually
  governs this pipeline, since every `search_users` call counts against it.
- The 5,000 req/hour figure is the *core* REST limit (PAT-authenticated) — it
  applies to non-search endpoints (`search_repositories` for file/commit
  fetches), NOT to `search_users`. Do not budget search calls against it.
- Estimated per 25-developer task: ~650 requests (mostly core REST fetches).
- If rate limited: pause 60s, retry. After 3 retries → skip developer.

## Important: Search API Limit

GitHub Search API returns max 1,000 results per query. If a query would return more:
- Narrow by adding date ranges: `created:2024-01-01..2025-01-01`
- Or by follower ranges: `followers:10..100`, `followers:>100`
