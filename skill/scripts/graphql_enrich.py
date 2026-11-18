#!/usr/bin/env python3
"""GraphQL enrichment via gh CLI with batched alias queries.

Replaces github-hr-graphql-scanner agent AND REST profile calls from fetcher.
Collects profile + contributions + repos + orgs + social + flags in one call per batch.
Uses GraphQL alias batching: 5 users per API call instead of 1.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"
TOO_HEAVY = re.compile(r"\bHTTP 50[24]\b|Resource limits for this query exceeded")

# GraphQL fragment with ALL fields (profile + expanded data)
USER_FIELDS_FRAGMENT = """
fragment UserFields on User {
  login
  name
  bio
  location
  company
  createdAt
  websiteUrl
  avatarUrl
  followers { totalCount }
  following { totalCount }
  repositories(privacy: PUBLIC) { totalCount }
  isHireable
  hasSponsorsListing
  isGitHubStar
  isDeveloperProgramMember
  isCampusExpert
  socialAccounts(first: 5) { nodes { provider url } }
  pullRequests(states: [MERGED, OPEN, CLOSED]) { totalCount }
  topRepositories(first: 10, orderBy: {field: STARGAZERS, direction: DESC}) {
    nodes {
      name
      nameWithOwner
      primaryLanguage { name }
      stargazerCount
      forkCount
      pushedAt
      description
      isArchived
      repositoryTopics(first: 5) { nodes { topic { name } } }
      languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
        edges { size node { name } }
      }
      defaultBranchRef {
        target {
          ... on Commit {
            history { totalCount }
          }
        }
      }
      pullRequests(states: MERGED) { totalCount }
      releases { totalCount }
      issues(states: OPEN) { totalCount }
      watchers { totalCount }
    }
  }
  pinnedItems(first: 6, types: REPOSITORY) {
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
    totalCommitContributions
    totalPullRequestContributions
    totalPullRequestReviewContributions
    restrictedContributionsCount
    contributionCalendar {
      totalContributions
      weeks {
        contributionDays { contributionCount date }
      }
    }
    commitContributionsByRepository(maxRepositories: 10) {
      repository { nameWithOwner }
      contributions { totalCount }
    }
  }
  repositoriesContributedTo(first: 10, contributionTypes: COMMIT) {
    nodes { nameWithOwner }
  }
  organizations(first: 5) { nodes { login name } }
}
"""


def build_batch_query(logins: list[str]) -> str:
    """Build a batched GraphQL query using aliases for multiple users."""
    aliases = []
    for i, login in enumerate(logins):
        aliases.append(f'  u{i}: user(login: "{login}") {{ ...UserFields }}')
    query_body = "{\n" + "\n".join(aliases) + "\n}\n" + USER_FIELDS_FRAGMENT
    return query_body


def run_graphql_batch(logins: list[str]) -> dict:
    """Execute a batched GraphQL query for multiple users.

    GitHub answers a too-heavy batch either from its gateway with 502/504 (gh prints
    "gh: HTTP 502") or from GraphQL with "Resource limits for this query exceeded.",
    so such a batch is halved and each half retried, down to single users.
    """
    query = build_batch_query(logins)
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
        if result.returncode != 0 and len(logins) > 1 and TOO_HEAVY.search(result.stderr):
            mid = len(logins) // 2
            print(f"  [graphql] {result.stderr.strip()[:200]}: splitting batch {len(logins)} -> {mid}+{len(logins) - mid}")
            left, right = run_graphql_batch(logins[:mid]), run_graphql_batch(logins[mid:])
            return {**left, **{f"u{int(k[1:]) + mid}": v for k, v in right.items()}}
        if result.returncode != 0:
            print(f"  [graphql] WARNING: batch query failed: {result.stderr.strip()[:200]}")
            return {}
        return json.loads(result.stdout).get("data", {})
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"  [graphql] ERROR: {e}")
        return {}


def extract_developer(login: str, user_data: dict, target_languages: list[str]) -> dict:
    """Transform raw GraphQL user data into enriched developer record."""
    if not user_data:
        return {"login": login, "scanError": True}

    dev = {
        "login": login,
        "scanError": False,
        # Profile fields (replaces REST profile call)
        "name": user_data.get("name"),
        "bio": user_data.get("bio"),
        "location": user_data.get("location"),
        "company": user_data.get("company"),
        "avatarUrl": user_data.get("avatarUrl"),
        "websiteUrl": user_data.get("websiteUrl"),
        "createdAt": user_data.get("createdAt"),
        "followers": (user_data.get("followers") or {}).get("totalCount", 0),
        "following": (user_data.get("following") or {}).get("totalCount", 0),
        "publicRepos": (user_data.get("repositories") or {}).get("totalCount", 0),
        "isHireable": user_data.get("isHireable", False),
        # Flags
        "hasSponsorsListing": user_data.get("hasSponsorsListing", False),
        "isGitHubStar": user_data.get("isGitHubStar", False),
        "isDeveloperProgramMember": user_data.get("isDeveloperProgramMember", False),
        "isCampusExpert": user_data.get("isCampusExpert", False),
        # Lifetime PRs
        "lifetimePullRequests": (user_data.get("pullRequests") or {}).get("totalCount", 0),
    }

    # Social accounts
    social_nodes = (user_data.get("socialAccounts") or {}).get("nodes", [])
    dev["socialAccounts"] = [{"provider": s.get("provider", ""), "url": s.get("url", "")} for s in social_nodes]

    # Organizations
    org_nodes = (user_data.get("organizations") or {}).get("nodes", [])
    dev["organizations"] = [{"login": o.get("login", ""), "name": o.get("name")} for o in org_nodes]

    # Repositories contributed to
    contrib_nodes = (user_data.get("repositoriesContributedTo") or {}).get("nodes", [])
    dev["repositoriesContributedTo"] = [n.get("nameWithOwner", "") for n in contrib_nodes if n]

    # Contributions collection
    cc = user_data.get("contributionsCollection") or {}
    dev["totalCommitContributions"] = cc.get("totalCommitContributions", 0)
    dev["totalPullRequestContributions"] = cc.get("totalPullRequestContributions", 0)
    dev["totalPullRequestReviewContributions"] = cc.get("totalPullRequestReviewContributions", 0)
    dev["restrictedContributionsCount"] = cc.get("restrictedContributionsCount", 0)

    # Contribution days
    calendar = cc.get("contributionCalendar") or {}
    contribution_days = 0
    for week in calendar.get("weeks", []):
        for day in week.get("contributionDays", []):
            if day.get("contributionCount", 0) > 0:
                contribution_days += 1
    dev["contributionDays"] = contribution_days

    # Commits by repo (from contributionsCollection)
    ccbr = cc.get("commitContributionsByRepository", [])
    dev["commitsByRepo"] = [
        {"repo": c.get("repository", {}).get("nameWithOwner", ""), "contributions": (c.get("contributions") or {}).get("totalCount", 0)}
        for c in ccbr
    ]

    # Top repositories processing
    top_repos_raw = (user_data.get("topRepositories") or {}).get("nodes", []) or []
    top_repos = []
    language_bytes_agg = {}  # aggregate across repos
    commits_per_repo = []
    merged_prs_by_repo = []
    releases_by_repo = []
    open_issues_by_repo = []
    watchers_by_repo = []
    total_stars = 0
    target_lang_repo_count = 0
    target_langs_lower = [t.lower() for t in target_languages]

    for repo in top_repos_raw:
        if not repo:
            continue
        repo_name = repo.get("nameWithOwner") or repo.get("name", "")
        primary_lang = (repo.get("primaryLanguage") or {}).get("name")
        stars = repo.get("stargazerCount", 0)
        total_stars += stars

        # Check target language
        if primary_lang and primary_lang.lower() in target_langs_lower:
            target_lang_repo_count += 1

        top_repos.append({
            "name": repo.get("name", ""),
            "nameWithOwner": repo_name,
            "primaryLanguage": primary_lang,
            "stars": stars,
            "forks": repo.get("forkCount", 0),
            "pushedAt": repo.get("pushedAt"),
            "description": repo.get("description"),
            "topics": [t.get("topic", {}).get("name", "") for t in (repo.get("repositoryTopics") or {}).get("nodes", [])],
        })

        # Language bytes (aggregate cross-repo)
        for edge in (repo.get("languages") or {}).get("edges", []):
            lang_name = (edge.get("node") or {}).get("name", "")
            lang_bytes = edge.get("size", 0)
            if lang_name:
                language_bytes_agg[lang_name] = language_bytes_agg.get(lang_name, 0) + lang_bytes

        # Per-repo metrics
        history = ((repo.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}
        commit_count = history.get("totalCount", 0)
        if commit_count > 0:
            commits_per_repo.append({"repo": repo_name, "totalCount": commit_count})

        merged_pr_count = (repo.get("pullRequests") or {}).get("totalCount", 0)
        if merged_pr_count > 0:
            merged_prs_by_repo.append({"repo": repo_name, "count": merged_pr_count})

        release_count = (repo.get("releases") or {}).get("totalCount", 0)
        if release_count > 0:
            releases_by_repo.append({"repo": repo_name, "count": release_count})

        issue_count = (repo.get("issues") or {}).get("totalCount", 0)
        if issue_count > 0:
            open_issues_by_repo.append({"repo": repo_name, "count": issue_count})

        watcher_count = (repo.get("watchers") or {}).get("totalCount", 0)
        if watcher_count > 0:
            watchers_by_repo.append({"repo": repo_name, "count": watcher_count})

    dev["topRepositories"] = top_repos
    dev["totalStarsReceived"] = total_stars
    dev["targetLanguageRepoCount"] = target_lang_repo_count
    dev["languageBytes"] = [{"language": k, "bytes": v} for k, v in sorted(language_bytes_agg.items(), key=lambda x: x[1], reverse=True)]
    dev["commitsPerRepo"] = commits_per_repo
    dev["mergedPullRequestsByRepo"] = merged_prs_by_repo
    dev["releasesByRepo"] = releases_by_repo
    dev["openIssuesByRepo"] = open_issues_by_repo
    dev["watchersByRepo"] = watchers_by_repo

    # Pinned repos
    pinned_nodes = (user_data.get("pinnedItems") or {}).get("nodes", []) or []
    dev["pinnedRepoCount"] = len(pinned_nodes)
    dev["pinnedRepos"] = [
        {
            "name": p.get("name", ""),
            "primaryLanguage": (p.get("primaryLanguage") or {}).get("name"),
            "stars": p.get("stargazerCount"),
            "forks": p.get("forkCount"),
            "description": p.get("description"),
        }
        for p in pinned_nodes if p
    ]

    return dev


def main():
    parser = argparse.ArgumentParser(description="GraphQL enrichment with batched alias queries")
    parser.add_argument("--task-id", required=True, help="Task ID")
    parser.add_argument("--target-languages", nargs="*", default=[], help="Target languages for repo count")
    parser.add_argument("--batch-size", type=int, default=3, help="Users per GraphQL call")
    parser.add_argument("--search-file", help="Override search input file")
    parser.add_argument("--output-file", help="Override output file name")
    args = parser.parse_args()

    import pipeline_logger as plog
    plog.init(args.task_id)
    plog.start_timer("graphql")

    search_file = args.search_file or f"search-{args.task_id}.json"
    search_path = OUTPUT_DIR / search_file
    if not search_path.exists():
        plog.log("graphql", f"Search file not found: {search_path}", level="error")
        print(f"[graphql] Search file not found: {search_path}", file=sys.stderr)
        sys.exit(1)

    with open(search_path) as f:
        search_data = json.load(f)

    logins = [d["login"] for d in search_data.get("developers", [])]
    n_batches = (len(logins) + args.batch_size - 1) // args.batch_size
    plog.log("graphql", f"GraphQL started: {len(logins)} developers, {n_batches} batches")
    print(f"[graphql] Enriching {len(logins)} developers in batches of {args.batch_size}")

    developers = []
    # Process in batches
    for i in range(0, len(logins), args.batch_size):
        batch = logins[i:i + args.batch_size]
        batch_num = i // args.batch_size + 1
        print(f"  [graphql] Batch {batch_num}: {batch}")

        data = run_graphql_batch(batch)
        batch_errors = 0
        for j, login in enumerate(batch):
            user_data = data.get(f"u{j}")
            dev = extract_developer(login, user_data, args.target_languages)
            developers.append(dev)
            status = "OK" if not dev.get("scanError") else "ERROR"
            if dev.get("scanError"):
                batch_errors += 1
            print(f"    {login}: {status}")

        if batch_errors > 0:
            plog.log("graphql", f"Batch {batch_num}/{n_batches}: {len(batch) - batch_errors}/{len(batch)} OK",
                     level="warn", metadata={"batch": batch_num, "errors": batch_errors})

    # If any failed in batch, retry individually
    failed = [d for d in developers if d.get("scanError")]
    if failed:
        print(f"  [graphql] Retrying {len(failed)} failed developers individually...")
        for dev in failed:
            login = dev["login"]
            data = run_graphql_batch([login])
            user_data = data.get("u0")
            if user_data:
                idx = next(i for i, d in enumerate(developers) if d["login"] == login)
                developers[idx] = extract_developer(login, user_data, args.target_languages)
                print(f"    {login}: RECOVERED")
            else:
                print(f"    {login}: STILL FAILED (scanError=true)")

    output_name = args.output_file or f"graphql-{args.task_id}.json"
    output = {"developers": developers}
    out_path = OUTPUT_DIR / output_name
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    ok_count = sum(1 for d in developers if not d.get("scanError"))
    err_count = sum(1 for d in developers if d.get("scanError"))

    duration = plog.end_timer("graphql")
    plog.log("graphql", f"GraphQL complete: {ok_count} enriched, {err_count} errors",
             level="warn" if err_count > 0 else "info",
             metadata={"duration_ms": duration, "output_count": ok_count, "errors": err_count})
    print(f"[graphql] Wrote {len(developers)} developers to {out_path.name} ({ok_count} OK, {err_count} errors)")


if __name__ == "__main__":
    main()
