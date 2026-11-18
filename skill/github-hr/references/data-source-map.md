# GitHub Data Source Map — Empirically Verified

> Last tested: 2026-03-04. All field lists verified against live API responses.

## Table of Contents

- [1. Search Stage (Phase 3.1)](#1-search-stage-phase-31)
- [2. Fetch Stage (Phase 3.2)](#2-fetch-stage-phase-32)
- [3. Pipeline Field Flow](#3-pipeline-field-flow)
- [4. Convex Developer Schema — Field Origins](#4-convex-developer-schema--field-origins)

## 1. Search Stage (Phase 3.1)

### MCP `search_users`

Returns per user:
| Field | Type | Example |
|-------|------|---------|
| `login` | string | `"octo-example"` |
| `id` | number | `36746429` |
| `profile_url` | string | `"https://github.com/octo-example"` |
| `avatar_url` | string | `"https://avatars.githubusercontent.com/u/36746429?v=4"` |

**That's it.** No followers, no public_repos, no bio, no location. Those come from the Fetch stage.

### CLI `gh api search/users` (alternative)

Returns same 4 fields plus:
| Field | Type | Notes |
|-------|------|-------|
| `type` | string | `"User"` or `"Organization"` — useful for filtering orgs |
| `score` | float | GitHub's internal search relevance score |
| `node_id` | string | GraphQL node ID |

**Still no followers/public_repos.** The search endpoint returns minimal user cards.

---

## 2. Fetch Stage (Phase 3.2)

### CLI `gh api users/{login}` — Full User Profile

| Field | Type | Schema Name | Example |
|-------|------|-------------|---------|
| `id` | number | `githubId` (→ string) | `36746429` |
| `login` | string | `login` | `"octo-example"` |
| `name` | string\|null | `name` | `"Octo Example"` |
| `email` | string\|null | `email` | `null` |
| `bio` | string\|null | `bio` | `"Freelance Web Developer..."` |
| `location` | string\|null | `location` | `"Italy"` |
| `company` | string\|null | `company` | `null` |
| `blog` | string | `blog` | `"https://www.example.org"` |
| `followers` | number | `followers` | `247` |
| `following` | number | `following` | `201` |
| `public_repos` | number | `publicRepos` | `50` |
| `public_gists` | number | — (not stored) | `0` |
| `hireable` | boolean\|null | `hireable` | `null` |
| `twitter_username` | string\|null | `twitterUsername` | `"ste_bartoletti"` |
| `avatar_url` | string | `avatarUrl` | `"https://avatars..."` |
| `html_url` | string | `profileUrl` | `"https://github.com/..."` |
| `created_at` | string (ISO) | `githubCreatedAt` (→ ms) | `"2018-02-22T21:18:38Z"` |
| `updated_at` | string (ISO) | — (not stored) | `"2026-02-24T03:53:28Z"` |
| `type` | string | — (not stored) | `"User"` |

### MCP `search_repositories` — User's Repos

| Field | Type | Schema Name | Example |
|-------|------|-------------|---------|
| `id` | number | — | `622690706` |
| `name` | string | `name` | `"notivue"` |
| `full_name` | string | `fullName` | `"octo-example/sample-repo"` |
| `description` | string\|null | `description` | `"Toast notification system..."` |
| `html_url` | string | `url` (derived) | `"https://github.com/..."` |
| `language` | string\|null | `language` | `"TypeScript"` |
| `stargazers_count` | number | `stars` | `861` |
| `forks_count` | number | `forks` | `13` |
| `open_issues_count` | number | — | `5` |
| `topics` | string[] | `topics` | `["vue", "toast", "nuxt"]` |
| `created_at` | string (ISO) | — | `"2023-04-02T..."` |
| `updated_at` | string (ISO) | — | `"2026-02-28T..."` |
| `private` | boolean | — | `false` |
| `fork` | boolean | — | `false` |
| `archived` | boolean | — | `false` |
| `default_branch` | string | — | `"main"` |

### CLI `gh api repos/{owner}/{repo}` — Additional Repo Fields

| Field | Type | Schema Name | Notes |
|-------|------|-------------|-------|
| `pushed_at` | string (ISO) | `pushedAt` (→ ms) | Last push date (more accurate than updated_at for activity) |
| `license.spdx_id` | string\|null | `license` | `"MIT"`, `"Apache-2.0"`, etc. |
| `homepage` | string\|null | — | Project website |
| `size` | number | — | Repo size in KB |
| `subscribers_count` | number | — | Watchers |

### MCP `list_commits` — Recent Commits

| Field | Type | Schema Name | Example |
|-------|------|-------------|---------|
| `sha` | string | `sha` | `"5d5b8e85..."` |
| `html_url` | string | `url` | `"https://github.com/.../commit/..."` |
| `commit.message` | string | `message` | `"feat: add feature"` |
| `commit.author.date` | string (ISO) | `date` | `"2024-09-01T21:27:03Z"` |
| `commit.author.name` | string | — | `"octo-example"` |
| `commit.author.email` | string | — | `"octo@example.com"` |
| `author.login` | string | — | `"octo-example"` |

### MCP `get_file_contents` — Source Code

Returns file content (for README, source files) or directory listing.

---

## 3. Pipeline Field Flow

| Pipeline Stage | Data Source | Key Fields Collected |
|----------------|------------|---------------------|
| Search (3.1) | MCP search_users | login, id, avatarUrl |
| Fetch Profile (3.2) | CLI gh api users/{login} | ALL profile fields: name, bio, location, company, blog, followers, following, publicRepos, hireable, twitterUsername, githubCreatedAt |
| Fetch Repos (3.2) | MCP search_repositories | name, fullName, description, language, stars, forks, topics |
| Fetch Repo Details (3.2) | CLI gh api repos/{o}/{r} | pushedAt, license |
| Fetch README (3.2) | MCP get_file_contents | readme text |
| Fetch Source (3.2) | MCP get_file_contents | sourceFiles[].path, sourceFiles[].content |
| Fetch Commits (3.2) | MCP list_commits | commits[].sha, .message, .date |
| Score (4) | Local JSON | score, scoreBreakdown, scoreComment, matchConfidence |
| Rank (5) | Local JSON | normalizedScore, rankComment |

---

## 4. Convex Developer Schema — Field Origins

| Convex Field | Source | Derivation |
|-------------|--------|-----------|
| `githubId` (string) | profile `id` (number) | `str(id)` |
| `login` | profile | Direct |
| `name` | profile | Direct |
| `email` | profile | Direct |
| `location` | profile | Direct |
| `company` | profile | Direct |
| `bio` | profile | Direct |
| `blog` | profile | Direct |
| `followers` | profile | Direct (default 0) |
| `following` | profile | Direct (default 0) |
| `publicRepos` | profile `public_repos` | Rename |
| `hireable` | profile | Direct |
| `twitterUsername` | profile `twitter_username` | Rename |
| `githubCreatedAt` | profile `created_at` | ISO → ms timestamp |
| `profileUrl` | profile `html_url` or derived | `https://github.com/{login}` |
| `avatarUrl` | profile `avatar_url` | Rename |
| `topLanguages` | repos | Unique languages from topRepos, order-preserving |
| `lastPushAt` | commits | Max commit date across all repos → ms |
| `topRepos[].name` | repo | Direct |
| `topRepos[].url` | repo `fullName` | `https://github.com/{fullName}` |
| `topRepos[].stars` | repo `stargazers_count` | Rename |
| `topRepos[].forks` | repo `forks_count` | Rename |
| `topRepos[].language` | repo | Direct |
| `topRepos[].description` | repo | Direct |
| `topRepos[].lastCommitAt` | repo commits[0].date | ISO → ms |
| `topRepos[].topics` | repo | Direct (max 20) |
| `topRepos[].pushedAt` | repo `pushed_at` | ISO → ms |
| `topRepos[].license` | repo `license.spdx_id` | Extract from nested object |
| `score` | scorer | Direct |
| `scoreComment` | scorer | Direct |
| `scoreModel` | scorer | Direct |
| `scoreBreakdown` | scorer | Direct (fixed keys in manual mode) |
| `scoredAt` | push time | `Date.now()` |
| `matchConfidence` | scorer (JD mode) | Direct |
| `matchReason` | scorer (JD mode) | Direct |
| `fromPass` | scorer (Pass 2) | Direct |
| `normalizedScore` | ranker | Direct |
| `rankComment` | ranker | Direct |
| `indexedAt` | push time | `Date.now()` |
| `updatedAt` | push time | `Date.now()` |
