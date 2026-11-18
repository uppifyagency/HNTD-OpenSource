# Fetch Output Schema — Forma Canonica

> Questo schema descrive la forma **post-normalizzazione** — quella che `push_results.py`
> garantisce dopo `normalize_profile()`. Non e' cio' che Claude DEVE produrre
> (non puo' essere forzato), e' cio' che il sistema GARANTISCE dopo il passaggio di normalizzazione.

## Table of Contents

- [Developer Profile — Forma Canonica](#developer-profile--forma-canonica)
- [Mappatura Alias Noti](#mappatura-alias-noti)
- [Score Batch — Output Phase 2](#score-batch--output-phase-2)
- [Push Shape — Input per Convex (post-normalizzazione)](#push-shape--input-per-convex-post-normalizzazione)
- [Derivazioni](#derivazioni)

## Developer Profile — Forma Canonica

```jsonc
{
  // Identity — sempre presenti (dalla search + fetch)
  "githubId": 12345678,              // number (int) — user.id from gh api users/{login}
  "login": "torvalds",               // string — user.login

  // Profile — popolati dal fetch (gh api users/{login}), null se assenti
  "name": "Linus Torvalds",          // string | null
  "bio": "...",                       // string | null
  "location": "Portland, OR",        // string | null
  "company": "@linux-foundation",    // string | null
  "email": null,                     // string | null
  "avatarUrl": "https://...",         // string | null
  "followers": 198000,               // number | null — null = non fetchato
  "following": 0,                    // number | null
  "publicRepos": 7,                  // number | null
  "blog": "https://...",             // string | null
  "hireable": true,                  // boolean | null
  "twitterUsername": "handle",       // string | null — from twitter_username
  "githubCreatedAt": "2011-09-03T...", // string (ISO 8601) | null — from created_at

  // Repos — array di repo con dati per scoring
  "topRepos": [                      // NOME CANONICO: sempre "topRepos"
    {
      "name": "linux",               // string
      "fullName": "torvalds/linux",  // string — per derivare URL
      "stars": 175000,               // number
      "forks": 52000,                // number
      "language": "C",               // string | null
      "description": "Linux kernel", // string | null
      "updatedAt": "2026-03-02T...", // string (ISO 8601) | null
      "topics": ["kernel", "os"],    // string[] | null — from MCP search_repositories
      "pushedAt": "2026-03-02T...",  // string (ISO 8601) | null — from gh api repos/{o}/{r}
      "license": "GPL-2.0",         // string | null — from license.spdx_id

      // Smart Profiling fields (new)
      "languages": {"C": 4500000, "Shell": 2000},  // object — byte counts from /languages API
      "directoryListing": ["src/", "test/", "pom.xml"],  // string[] — root dir contents
      "dependencyFile": {"path": "pom.xml", "content": "..."}, // object | null

      // Dati per scoring (strippati prima del push a Convex)
      "sourceFiles": [...],          // array
      "commits": [...]               // NOME CANONICO: sempre "commits"
    }
  ]
}
```

## Mappatura Alias Noti

| Campo canonico | Alias storici trovati nei dati | Azione normalizer |
|---|---|---|
| `topRepos` | `repos` | Rinomina key |
| `commits` | `recentCommits` | Rinomina key dentro ogni repo |
| `fullName` | — (assente se c'e' `url`) | Deriva da `url` se mancante |
| `updatedAt` | — (non esisteva nei task 1-2) | `null` se assente |
| `avatarUrl` | `avatar_url` | Rinomina key |
| `profileUrl` | `html_url`, `profile_url` | Derivato: `https://github.com/{login}` |
| `twitterUsername` | `twitter_username` | Rinomina key (snake → camel) |
| `githubCreatedAt` | `created_at` | Rinomina key (ISO string in fetch, ms in push) |
| `publicRepos` | `public_repos` | Rinomina key (snake → camel) |
| `pushedAt` | `pushed_at` | Rinomina key dentro ogni repo (ISO → ms in push) |
| `topics` | — | Diretto da MCP search_repositories |
| `license` | `license.spdx_id` | Estratto da oggetto nested |
| `languages` | — (new field) | Object with byte counts per language |
| `directoryListing` | — (new field) | Array of filenames from root dir |
| `dependencyFile` | — (new field) | Object with path + content, or null |

## Score Batch — Output Phase 2

```jsonc
{
  "scores": [
    {
      "login": "torvalds",
      "score": 92,
      "niceToHaveBonus": 4,
      "scoreBreakdown": {
        "codeQuality": 19,
        "architecture": 18,
        "testing": 12,
        "documentation": 15,
        "complexity": 15,
        "consistency": 13
      },
      "scoreComment": "Exceptional systems programmer...",
      "scoreModel": "claude-sonnet-4-6",  // il subagent sceglie il model
      "topRepo": "linux"
    }
  ]
}
```

## Push Shape — Input per Convex (post-normalizzazione)

```jsonc
{
  "githubId": "12345678",            // STRING — Convex schema richiede v.string()
  "login": "torvalds",
  "name": "Linus Torvalds",          // opzionale — strippato se null
  "location": "Portland, OR",        // opzionale
  "bio": "...",                       // opzionale
  "blog": "https://...",             // opzionale
  "followers": 198000,               // number — default 0 se null
  "following": 0,                    // number — default 0 se null
  "publicRepos": 7,                  // number — default 0 se null
  "hireable": true,                  // opzionale — boolean | null
  "twitterUsername": "handle",       // opzionale — from twitter_username
  "githubCreatedAt": 1315008000000,  // opzionale — ms timestamp from created_at
  "profileUrl": "https://github.com/torvalds",  // DERIVATO da login
  "avatarUrl": "https://...",         // opzionale
  "topLanguages": ["C", "Assembly"], // DERIVATO da topRepos[].language
  "lastPushAt": 1709251200000,       // opzionale — dal commit piu' recente
  "topRepos": [
    {
      "name": "linux",
      "url": "https://github.com/torvalds/linux", // DERIVATO da fullName
      "stars": 175000,
      "forks": 52000,
      "language": "C",
      "description": "Linux kernel",
      "lastCommitAt": 1709251200000,
      "topics": ["kernel", "os"],    // opzionale — max 20
      "pushedAt": 1709251200000,     // opzionale — ms timestamp from pushed_at
      "license": "GPL-2.0"          // opzionale — from license.spdx_id
    }
  ],
  "score": 92,
  "scoreComment": "Exceptional...",
  "scoreModel": "claude-sonnet-4-6",
  "scoreBreakdown": { ... },
  "scoredAt": "<now_ms>",
  "indexedAt": "<now_ms>",
  "updatedAt": "<now_ms>"
}
```

## Derivazioni

| Campo push | Derivato da | Logica |
|---|---|---|
| `githubId` (string) | `id` (number) | `str(profile.get("githubId") or profile.get("id"))` |
| `profileUrl` | `login` | `f"https://github.com/{login}"` |
| `topLanguages` | `topRepos[].language` | Unique, order-preserving, min `["Unknown"]` |
| `lastPushAt` | `topRepos[].commits[0].date` | `max()` dei primi commit, ISO -> ms |
| `topRepos[].url` | `topRepos[].fullName` | `f"https://github.com/{fullName}"` |
| `topRepos[].lastCommitAt` | `topRepos[].commits[0].date` | Primo commit, ISO -> ms |
| `twitterUsername` | `twitter_username` | Rinomina (snake → camel) |
| `githubCreatedAt` | `created_at` | ISO 8601 → ms timestamp |
| `topRepos[].pushedAt` | `pushed_at` | ISO 8601 → ms timestamp |
| `topRepos[].topics` | `topics` | Diretto, max 20 elementi |
| `topRepos[].license` | `license.spdx_id` | Estratto da oggetto nested |
