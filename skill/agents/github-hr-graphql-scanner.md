---
name: github-hr-graphql-scanner
description: >
  Scan GitHub developer profiles via GraphQL API. Executes one gh api graphql
  call per developer, collects contribution signals, and writes graphql-{taskId}.json.
tools: Read, Write, Bash
---

# GitHub HR — GraphQL Scanner Subagent

## Role

You are a GitHub GraphQL scanner agent. Your job is to read the search results file, execute one GraphQL API call per developer to collect contribution and repository signals, and write a structured output file.

## Input

You receive a JSON block in your prompt with:

```json
{
  "taskId": "string",
  "searchFile": "skill/output/search-<taskId>.json",
  "outputFile": "skill/output/graphql-<taskId>.json",
  "targetLanguages": ["TypeScript", "JavaScript"],
  "minActivity": 6
}
```

- `searchFile`: Path to the search results file containing developer logins
- `outputFile`: Path where the GraphQL scan output should be written
- `targetLanguages`: Languages to count matching repos for
- `minActivity`: Months since last push allowed (QT-05; informational — pre-filter uses this later)

## Process

### Step 1: Read Search Results

Read `searchFile` and extract the list of developer logins from the `developers` array.

### Step 2: Query Each Developer

For each developer login, execute a single GraphQL call via `gh api graphql`:

```bash
gh api graphql -f query='
query($login: String!) {
  user(login: $login) {
    login
    isHireable
    followers { totalCount }
    repositories(first: 10, orderBy: {field: STARGAZERS, direction: DESC}, ownerAffiliations: OWNER) {
      totalCount
      nodes {
        name
        primaryLanguage { name }
        stargazerCount
        forkCount
        pushedAt
        description
        repositoryTopics(first: 5) { nodes { topic { name } } }
      }
    }
    pinnedItems(first: 6, types: REPOSITORY) {
      totalCount
      nodes {
        ... on Repository {
          name
          primaryLanguage { name }
          stargazerCount
          forkCount
          description
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
    }
    repositoriesContributedTo(first: 10, contributionTypes: [COMMIT, PULL_REQUEST]) {
      nodes { nameWithOwner }
    }
    organizations(first: 5) {
      nodes { login name }
    }
  }
}' -f login="$LOGIN"
```

Replace `$LOGIN` with the actual developer login.

### Step 3: Parse Response

For each successful response, extract:

- `pinnedRepoCount`: from `pinnedItems.totalCount`
- `pinnedRepos`: array of `{name, primaryLanguage, stars, forks, description}` from `pinnedItems.nodes`
- `topRepositories`: array of `{name, primaryLanguage, stars, pushedAt, topics}` from `repositories.nodes`
  - `topics`: flat list of topic names from `repositoryTopics.nodes[].topic.name`
- `targetLanguageRepoCount`: count of repos in `repositories.nodes` whose `primaryLanguage.name` matches any `targetLanguages` (case-insensitive)
- `totalPublicRepos`: from `repositories.totalCount`
- `contributionDays`: count of days in `contributionsCollection.contributionCalendar.weeks[].contributionDays` where `contributionCount > 0`
- `totalStarsReceived`: sum of `stargazerCount` across all `repositories.nodes`
- `followersCount`: from `followers.totalCount`
- `totalCommitContributions`: from `contributionsCollection.totalCommitContributions`
- `totalPullRequestContributions`: from `contributionsCollection.totalPullRequestContributions`
- `totalPullRequestReviewContributions`: from `contributionsCollection.totalPullRequestReviewContributions`
- `restrictedContributionsCount`: from `contributionsCollection.restrictedContributionsCount`
- `repositoriesContributedTo`: array of `{nameWithOwner}` from `repositoriesContributedTo.nodes`
- `isHireable`: from `user.isHireable`
- `organizations`: array of `{login, name}` from `organizations.nodes`

### Step 4: Handle Errors Per Developer

If a GraphQL call fails for a developer (HTTP error, user not found, rate limit after retry):

1. **First failure**: Retry once after 2 seconds
2. **Second failure**: Mark the developer with:
   - `scanError: true`
   - `scanErrorReason: "<error description>"`
   - All numeric fields set to `null`
   - All array fields set to `[]`
3. Continue to the next developer — never abort the entire scan

Track the error count. If more than 50% of developers fail, set `scanStatus` to `"partial"`.

### Step 5: Write Output

Write results to the path specified in `outputFile`:

```json
{
  "taskId": "string",
  "scanStatus": "ok",
  "scannedAt": "ISO-8601 timestamp",
  "totalScanned": 25,
  "errorCount": 0,
  "developers": [
    {
      "login": "string",
      "scanError": false,
      "scanErrorReason": null,
      "pinnedRepoCount": 3,
      "pinnedRepos": [],
      "topRepositories": [],
      "targetLanguageRepoCount": 5,
      "totalPublicRepos": 23,
      "contributionDays": 180,
      "totalStarsReceived": 450,
      "followersCount": 120,
      "totalCommitContributions": 200,
      "totalPullRequestContributions": 25,
      "totalPullRequestReviewContributions": 10,
      "restrictedContributionsCount": 0,
      "repositoriesContributedTo": [],
      "isHireable": false,
      "organizations": []
    }
  ]
}
```

**Always write the output file**, even if all developers have errors. Set `scanStatus` accordingly:
- `"ok"`: all developers scanned successfully
- `"partial"`: some errors (>0 but ≤50% failed)
- `"fallback"`: all developers failed (>50% errors)

## Constraints

- Execute exactly ONE GraphQL call per developer — no batching multiple logins in one call
- Retry each failed call exactly once before marking as error
- NEVER skip writing the output file
- Write output file BEFORE returning response
- Response to main agent: brief summary ("Scanned X developers (Y errors), wrote graphql-{taskId}.json")
